"""Push a local Reel using Facebook Login's resumable-upload API. Stdlib only."""
import argparse
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import socket
import ssl
import sqlite3
import subprocess
import sys
import time
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parent


class PushError(Exception):
    pass


def network_failure(exc):
    """Classify transport errors without exposing URLs, credentials or proxy data."""
    reason = exc.reason if isinstance(exc, error.URLError) else exc
    winerror = getattr(reason, 'winerror', None)
    errno = getattr(reason, 'errno', None)
    if isinstance(reason, PermissionError) or winerror == 10013 or errno in (1, 13):
        category, retryable = 'access_denied', False
        message = 'The operating system denied network access for this process.'
    elif isinstance(reason, ssl.SSLError):
        category, retryable = 'tls', False
        message = 'TLS negotiation or certificate verification failed.'
    elif isinstance(reason, (TimeoutError, socket.timeout)):
        category, retryable = 'timeout', True
        message = 'The connection timed out.'
    elif isinstance(reason, socket.gaierror):
        category = 'dns'
        retryable = errno == getattr(socket, 'EAI_AGAIN', None)
        message = 'Hostname resolution failed.'
    else:
        category, retryable = 'connection', isinstance(reason, ConnectionError)
        message = 'The network connection failed.'
    return {'category': category, 'exception': type(reason).__name__,
            'winerror': winerror, 'errno': errno, 'retryable': retryable, 'message': message}


def safe_diagnostic(value, token):
    """Keep useful Meta messages while removing credentials and signed URLs."""
    text = str(value)
    for secret in (token, parse.quote(token, safe='')):
        if secret:
            text = text.replace(secret, '[REDACTED]')
    text = re.sub(r'https?://[^\s\"<>]+', '[URL REDACTED]', text)
    text = re.sub(r'(?i)((?:access_token|authorization|appsecret_proof|client_secret)'
                  r'[\s\"\x27:=]+)[^\s,}\"\x27]+', r'\1[REDACTED]', text)
    text = re.sub(r'[A-Za-z0-9_\-]{64,}', '[OPAQUE VALUE REDACTED]', text)
    return text[:1500]


def meta_error_details(payload):
    """Graph errors and rupload debug_info have different envelopes."""
    if not isinstance(payload, dict):
        return {}
    detail = payload.get('error') or payload.get('debug_info') or payload
    if not isinstance(detail, dict):
        return {'message': str(detail)}
    fields = ('code', 'error_subcode', 'type', 'message', 'error_user_title',
              'error_user_msg', 'fbtrace_id', 'is_transient', 'retriable')
    return {key: detail[key] for key in fields if key in detail}


def load_env(path):
    if not path.exists():
        return
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            raise PushError('Invalid .env line: expected KEY=value.')
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip().strip('\"\''))


def configuration():
    names = ('META_API_VERSION', 'INSTAGRAM_ACCOUNT_ID', 'META_ACCESS_TOKEN')
    values = {key: os.environ.get(key, '').strip() for key in names}
    missing = [key for key in names if not values[key]]
    if missing:
        raise PushError('Set these values in publishing/.env: ' + ', '.join(missing))
    if not re.fullmatch(r'v\d+\.\d+', values['META_API_VERSION']):
        raise PushError('META_API_VERSION must look like vNN.0; use your Meta app version.')
    if not values['INSTAGRAM_ACCOUNT_ID'].isdigit():
        raise PushError('INSTAGRAM_ACCOUNT_ID must be the numeric API account ID, not @username.')
    return values


def inspect_video(path):
    if not path.is_file() or path.suffix.lower() not in ('.mp4', '.mov'):
        raise PushError('Video must be an existing MP4 or MOV file.')
    size = path.stat().st_size
    if not 0 < size <= 1_000_000_000:
        raise PushError('Video must be nonempty and no larger than 1 GB.')
    probe = shutil.which('ffprobe')
    if not probe:
        raise PushError('ffprobe is required. Install FFmpeg and put ffprobe on PATH.')
    result = subprocess.run([probe, '-v', 'error', '-show_streams', '-show_format',
                             '-of', 'json', str(path)], capture_output=True, text=True,
                            timeout=60)
    if result.returncode:
        raise PushError('ffprobe could not read the video.')
    data = json.loads(result.stdout)
    streams = data.get('streams', [])
    videos = [s for s in streams if s['codec_type'] == 'video']
    if len(videos) != 1:
        raise PushError('Expected exactly one video stream.')
    video = videos[0]
    duration = float(data['format']['duration'])
    fps = float(Fraction(video.get('avg_frame_rate', '0/1')))
    width, height = int(video['width']), int(video['height'])
    if not math.isfinite(duration) or not 3 <= duration <= 900:
        raise PushError('Expected a Reel between 3 seconds and 15 minutes.')
    if video['codec_name'] not in ('h264', 'hevc') or video.get('pix_fmt') != 'yuv420p':
        raise PushError('Expected H.264/HEVC video with yuv420p pixels.')
    if not 23 <= fps <= 60 or width > 1920 or height <= 0:
        raise PushError('Expected 23–60 fps and video width at most 1920 pixels.')
    if not 0.01 <= width / height <= 10:
        raise PushError('Video aspect ratio is outside the supported range.')
    audio = [s for s in streams if s['codec_type'] == 'audio']
    for stream in audio:
        if (stream['codec_name'] != 'aac' or int(stream['sample_rate']) > 48000
                or int(stream['channels']) not in (1, 2)):
            raise PushError('Expected AAC audio, at most 48 kHz, mono or stereo.')
    return {'width': width, 'height': height, 'duration_seconds': duration,
            'fps': fps, 'bytes': size, 'audio': bool(audio)}


def file_digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def parse_at(value):
    if not value:
        return None
    try:
        target = datetime.fromisoformat(value)
    except ValueError as exc:
        raise PushError('Use an ISO time such as 2026-11-14T18:00:00+05:00.') from exc
    if target.tzinfo is None:
        raise PushError('--at must include a timezone offset, for example +05:00.')
    return target.astimezone(timezone.utc)


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Meta:
    def __init__(self, config):
        self.token = config['META_ACCESS_TOKEN']
        self.base = 'https://graph.facebook.com/' + config['META_API_VERSION']
        self.opener = request.build_opener(NoRedirect())

    def send(self, req, timeout=60):
        # Only repeat read requests. A lost POST response may have taken effect.
        attempts = 3 if req.get_method() == 'GET' else 1
        for index in range(attempts):
            try:
                return self.send_once(req, timeout)
            except TransportError as exc:
                if exc.detail['retryable'] and index + 1 < attempts:
                    print('Temporary Meta read connection failure; retrying', index + 2, 'of', attempts)
                    time.sleep((1, 3)[index])
                    continue
                raise PushError(str(exc)) from None

    def send_once(self, req, timeout):
        try:
            with self.opener.open(req, timeout=timeout) as response:
                result = json.load(response)
        except error.HTTPError as exc:
            # Never print raw response bodies, request URLs, or credentials.
            detail = {}
            try:
                detail = meta_error_details(json.loads(exc.read(65536)))
            except (ValueError, AttributeError):
                pass
            finally:
                exc.close()
            stage = 'upload' if parse.urlsplit(req.full_url).hostname == 'rupload.facebook.com' else 'Graph'
            summary = safe_diagnostic(json.dumps(detail, ensure_ascii=True), self.token)
            raise PushError(f'Meta {stage} HTTP {exc.code}: {summary}. '
                            'Saved state was retained.') from None
        except (error.URLError, TimeoutError, socket.timeout, OSError) as exc:
            detail = network_failure(exc)
            raise TransportError(detail) from None
        except ValueError:
            raise PushError('Meta returned an unreadable response. Saved state was retained.') from None
        if not isinstance(result, dict) or result.get('error'):
            raise PushError('Unexpected Meta response. Saved state was retained.')
        return result

    def graph(self, path, params=None, post=False):
        query = parse.urlencode(params or {})
        url = f'{self.base}/{path}'
        body = query.encode() if post else None
        if query and not post:
            url += '?' + query
        headers = {'Authorization': 'Bearer ' + self.token}
        return self.send(request.Request(url, data=body, headers=headers,
                                        method='POST' if post else 'GET'))

    def upload(self, uri, video):
        parsed = parse.urlsplit(uri)
        if (parsed.scheme != 'https' or parsed.hostname != 'rupload.facebook.com'
                or parsed.username or parsed.password or parsed.port not in (None, 443)):
            raise PushError('Meta returned an unexpected upload host; upload refused.')
        size = video.stat().st_size
        with video.open('rb') as stream:
            return self.send(request.Request(uri, data=stream, method='POST', headers={
                'Authorization': 'OAuth ' + self.token, 'offset': '0',
                'file_size': str(size), 'Content-Length': str(size),
                'Content-Type': 'application/octet-stream',
            }), timeout=600)


class TransportError(PushError):
    def __init__(self, detail):
        self.detail = detail
        codes = ', '.join(f'{key}={detail[key]}' for key in ('winerror', 'errno') if detail[key] is not None)
        suffix = f' ({codes})' if codes else ''
        super().__init__(f"Meta network {detail['category']}{suffix}: {detail['message']} "
                         'No complete Meta HTTP response was received. Saved state was retained. '
                         'Run network_check.py under the Windows account used by the scheduled task.')


class State:
    def __init__(self, folder):
        folder.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(folder / 'posts.sqlite3')
        self.db.execute('CREATE TABLE IF NOT EXISTS posts '
                        '(job TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        self.db.commit()

    def get(self, job):
        row = self.db.execute('SELECT payload FROM posts WHERE job=?', (job,)).fetchone()
        return json.loads(row[0]) if row else {}

    def save(self, job, state):
        state['updated_at'] = datetime.now(timezone.utc).isoformat()
        self.db.execute('INSERT OR REPLACE INTO posts VALUES (?, ?)',
                        (job, json.dumps(state)))
        self.db.commit()


@contextmanager
def process_lock(folder):
    """OS releases this advisory lock on process exit, including crashes."""
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / 'publisher.lock').open('a+b') as stream:
        stream.seek(0)
        stream.write(b'0')
        stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise PushError('Another publisher is running. Wait for it to finish.') from None
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def push(api, store, job, video, caption, account, share_to_feed, wait_seconds, before_publish=None, prepare_only=False):
    state = store.get(job)
    if state.get('phase') == 'published':
        print('Already published:', state.get('permalink') or state.get('media_id'))
        return state
    if state.get('phase') in ('creating', 'uploading'):
        raise PushError('A previous create/upload was interrupted. Do not delete saved state '
                        'or automatically repeat it; inspect the container/account first.')
    if state.get('phase') == 'publishing':
        remote = api.graph(state['container_id'], {'fields': 'status_code'})
        if remote.get('status_code') == 'PUBLISHED':
            state['phase'] = 'published'
            store.save(job, state)
            print('Instagram confirms the previous attempt was published. Check the profile for its link.')
            return state
        raise PushError('Previous publish result is uncertain. Check Instagram before retrying. '
                        'The script will not repeat media_publish automatically.')
    if not state or state.get('phase') == 'queued':
        # Commit before each side effect so crashes cannot silently repeat publishing.
        state.update(phase='creating', account_id=account, video=str(video),
                     caption=caption, share_to_feed=share_to_feed)
        store.save(job, state)
        created = api.graph(f'{account}/media', {
            'media_type': 'REELS', 'upload_type': 'resumable', 'caption': caption,
            'share_to_feed': str(share_to_feed).lower(),
        }, post=True)
        if not created.get('id') or not created.get('uri'):
            raise PushError('Meta did not return a container ID and upload URI.')
        state.update(container_id=created['id'], upload_uri=created['uri'], phase='uploading')
        store.save(job, state)
        print('Uploading video to Meta...')
        result = api.upload(created['uri'], video)
        if result.get('success') is not True:
            raise PushError('Meta did not acknowledge the upload; inspect saved state.')
        state['phase'] = 'processing'
        store.save(job, state)
    deadline = time.monotonic() + wait_seconds
    while True:
        remote = api.graph(state['container_id'], {'fields': 'status_code'})
        status = remote.get('status_code')
        print('Instagram container:', status)
        if status == 'FINISHED':
            break
        if status == 'PUBLISHED':
            state['phase'] = 'published'
            store.save(job, state)
            print('Instagram reports this container is already published.')
            return state
        if status in ('ERROR', 'EXPIRED'):
            raise PushError(f'Container is {status}. Inspect it in Meta before creating a replacement.')
        if status != 'IN_PROGRESS':
            raise PushError('Unexpected processing status; publish was not attempted.')
        if time.monotonic() >= deadline:
            raise PushError('Processing wait expired. Run the same command again to resume polling.')
        time.sleep(min(10, max(0, deadline - time.monotonic())))
    if prepare_only:
        print('Video uploaded and processed. Publication is held for its scheduled time.')
        return state
    if before_publish:
        before_publish()
    state['phase'] = 'publishing'
    store.save(job, state)
    published = api.graph(f'{account}/media_publish', {'creation_id': state['container_id']}, post=True)
    if not published.get('id'):
        raise PushError('Publish response has no media ID. Check Instagram; do not blindly repeat.')
    state.update(phase='published', media_id=published['id'])
    store.save(job, state)
    try:
        state['permalink'] = api.graph(state['media_id'], {'fields': 'permalink'}).get('permalink')
        store.save(job, state)
    except PushError:
        print('Published successfully; permalink lookup failed. Media ID:', state['media_id'])
    print('Published:', state.get('permalink') or state['media_id'])
    return state


def retry_upload(api, store, job, config):
    """Recover a confirmed zero-byte failure on the same container; never publish."""
    state = store.get(job)
    if not state or state.get('account_id') != config['INSTAGRAM_ACCOUNT_ID']:
        raise PushError('No matching saved job for the configured Instagram account.')
    if state.get('phase') != 'uploading' or not state.get('container_id'):
        raise PushError('Upload retry is only available for a saved uploading job.')
    video = Path(state['video'])
    inspect_video(video)
    expected = hashlib.sha256(
        f"{config['INSTAGRAM_ACCOUNT_ID']}:{file_digest(video)}".encode()).hexdigest()
    if job != expected:
        raise PushError('Local video has changed since this job was created; retry refused.')
    remote = api.graph(state['container_id'], {'fields': 'status_code,status,video_status'})
    status = remote.get('status_code')
    if status == 'PUBLISHED':
        state['phase'] = 'published'
        store.save(job, state)
        print('Meta reports this container is already published. No upload attempted.')
        return state
    if status == 'FINISHED':
        state['phase'] = 'processing'
        store.save(job, state)
        print('Meta already has the processed video. No upload or publication attempted.')
        return state
    upload = (remote.get('video_status') or {}).get('uploading_phase') or {}
    if (status != 'IN_PROGRESS' or upload.get('status') != 'error'
            or upload.get('bytes_transferred') != 0
            or upload.get('source_file_size') not in (0, video.stat().st_size)):
        raise PushError('Meta has not confirmed an active container with a failed zero-byte upload. '
                        'Inspect the job; this command will not overwrite an uncertain upload.')
    uri = state.get('upload_uri')
    if not uri:
        # Earlier script versions did not retain the returned URI. Meta documents
        # this exact upload path for the existing container and API version.
        if not str(state['container_id']).isdigit():
            raise PushError('Invalid saved container ID.')
        uri = (f"https://rupload.facebook.com/ig-api-upload/"
               f"{config['META_API_VERSION']}/{state['container_id']}")
    print('Retrying file upload to the existing container. This will not publish.')
    state['upload_attempts'] = state.get('upload_attempts', 1) + 1
    store.save(job, state)
    try:
        result = api.upload(uri, video)
        if result.get('success') is not True:
            detail = safe_diagnostic(json.dumps(meta_error_details(result)), api.token)
            raise PushError('Meta did not acknowledge the upload: ' + detail)
    except PushError as exc:
        state['last_upload_error'] = safe_diagnostic(str(exc), api.token)
        store.save(job, state)
        raise
    state['phase'] = 'processing'
    state.pop('last_upload_error', None)
    store.save(job, state)
    print('Upload accepted. No publication attempted. Use --inspect-job to check processing.')
    return state


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', type=Path)
    parser.add_argument('--caption-file', type=Path)
    parser.add_argument('--check-account', action='store_true',
                        help='Read account identity and publishing allowance; never upload or publish')
    parser.add_argument('--inspect-job', metavar='JOB_ID',
                        help='Read saved job and Meta container status; never upload or publish')
    parser.add_argument('--retry-upload', metavar='JOB_ID',
                        help='Retry a confirmed zero-byte upload on the same container; never publish')
    parser.add_argument('--publish', action='store_true', help='Upload and publish; otherwise offline dry run')
    parser.add_argument('--at', help='Wait until an ISO datetime with offset; PC must remain awake')
    parser.add_argument('--reels-only', action='store_true', help='Do not also share to profile feed')
    parser.add_argument('--wait-seconds', type=int, default=600)
    args = parser.parse_args(argv)
    if args.retry_upload:
        if (args.check_account or args.inspect_job or args.publish or args.video
                or args.caption_file or args.at or args.reels_only):
            raise PushError('Use --retry-upload by itself; it cannot publish or start another job.')
        if not re.fullmatch(r'[a-f0-9]{64}', args.retry_upload):
            raise PushError('Job ID must be the 64-character hash printed by the publisher.')
        load_env(ROOT / '.env')
        config = configuration()
        folder = ROOT / '.state'
        if not (folder / 'posts.sqlite3').is_file():
            raise PushError('No saved publishing database exists.')
        with process_lock(folder):
            store = State(folder)
            try:
                retry_upload(Meta(config), store, args.retry_upload, config)
            finally:
                store.db.close()
        return 0
    if args.inspect_job:
        if (args.check_account or args.publish or args.video or args.caption_file
                or args.at or args.reels_only):
            raise PushError('Use --inspect-job by itself; it never uploads or publishes.')
        if not re.fullmatch(r'[a-f0-9]{64}', args.inspect_job):
            raise PushError('Job ID must be the 64-character hash printed by the publisher.')
        load_env(ROOT / '.env')
        config = configuration()
        database = ROOT / '.state' / 'posts.sqlite3'
        if not database.is_file():
            raise PushError('No saved publishing database exists.')
        with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as db:
            row = db.execute('SELECT payload FROM posts WHERE job=?', (args.inspect_job,)).fetchone()
        if not row:
            raise PushError('No saved job matches that ID.')
        state = json.loads(row[0])
        if state.get('account_id') != config['INSTAGRAM_ACCOUNT_ID']:
            raise PushError('Saved job account does not match the configured account.')
        summary = {key: state.get(key) for key in ('phase', 'container_id', 'media_id', 'updated_at')}
        print(json.dumps({'saved_job': summary}, indent=2))
        if state.get('container_id'):
            api = Meta(config)
            result = api.graph(state['container_id'], {'fields': 'status_code,status,video_status'})
            print(safe_diagnostic(json.dumps({'container': result}, indent=2), api.token))
        print('Read-only inspection complete. No upload or publication was attempted.')
        return 0
    if args.check_account:
        if args.publish or args.video or args.caption_file or args.at or args.reels_only:
            raise PushError('Use --check-account by itself; it cannot be combined with a posting job.')
        load_env(ROOT / '.env')
        config = configuration()
        api = Meta(config)
        account = config['INSTAGRAM_ACCOUNT_ID']
        identity = api.graph(account, {'fields': 'id,username'})
        print('Account access OK:', identity.get('username', account))
        quota = api.graph(f'{account}/content_publishing_limit', {'fields': 'config,quota_usage'})
        print(json.dumps({'publishing_allowance': quota.get('data', [])}, indent=2))
        print('Read-only check complete. No upload or publication was attempted.')
        return 0
    if not args.video or not args.caption_file:
        raise PushError('--video and --caption-file are required unless using --check-account.')
    if args.wait_seconds < 1:
        raise PushError('--wait-seconds must be positive.')
    video = args.video.resolve()
    details = inspect_video(video)
    if not args.caption_file.is_file():
        raise PushError('Caption file does not exist.')
    caption = args.caption_file.read_text(encoding='utf-8-sig').strip()
    if not caption or len(caption) > 2200:
        raise PushError('Caption must contain 1–2200 characters.')
    target = parse_at(args.at)
    digest = file_digest(video)
    print(json.dumps({'mode': 'PUBLISH' if args.publish else 'DRY RUN (no network calls)',
                      'video': str(video), 'media': details, 'caption': caption,
                      'scheduled_utc': target.isoformat() if target else None}, indent=2))
    if not args.publish:
        print('Local checks passed. Account access has not been tested.')
        return 0
    load_env(ROOT / '.env')
    config = configuration()
    account = config['INSTAGRAM_ACCOUNT_ID']
    # One file per account: caption or scheduling changes cannot bypass duplicate detection.
    job = hashlib.sha256(f'{account}:{digest}'.encode()).hexdigest()
    print('Job:', job)
    folder = ROOT / '.state'
    with process_lock(folder):
        store = State(folder)
        try:
            previous = store.get(job)
            if previous and (previous.get('caption') != caption or
                             previous.get('share_to_feed') != (not args.reels_only)):
                # Legacy/incomplete state can omit metadata; don't mutate an existing job.
                if 'caption' in previous:
                    raise PushError('This file already has a job with different caption/feed settings.')
            if not previous:
                previous = {'phase': 'queued', 'caption': caption,
                            'share_to_feed': not args.reels_only,
                            'scheduled_utc': target.isoformat() if target else None}
                store.save(job, previous)
            saved_target = parse_at(previous.get('scheduled_utc'))
            if saved_target and previous.get('phase') == 'queued':
                print('Waiting until', saved_target.isoformat(), '— keep this PC awake and online.')
                while datetime.now(timezone.utc) < saved_target:
                    remaining = (saved_target - datetime.now(timezone.utc)).total_seconds()
                    time.sleep(min(30, max(0, remaining)))
            # Account read verifies that the configured ID and token can access the target.
            identity = Meta(config).graph(account, {'fields': 'id,username'})
            print('Target account:', identity.get('username', account))
            push(Meta(config), store, job, video, caption, account,
                 not args.reels_only, args.wait_seconds)
        finally:
            store.db.close()
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print('Stopped. Any in-flight operation remains recorded; do not delete state.', file=sys.stderr)
        sys.exit(130)
    except (PushError, OSError, ValueError, KeyError, ZeroDivisionError,
            sqlite3.Error, subprocess.TimeoutExpired) as exc:
        # Unexpected local errors get their type only, avoiding accidental secret logging.
        message = str(exc) if isinstance(exc, PushError) else f'Local failure ({type(exc).__name__}).'
        print('ERROR:', message, file=sys.stderr)
        sys.exit(1)
