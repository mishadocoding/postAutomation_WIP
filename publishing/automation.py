"""Local daily Instagram publishing queue. No generation; stdlib only."""
import argparse
from contextlib import closing, redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import uuid

import push_reel as p

ROOT = Path(__file__).resolve().parent
DATA = ROOT / '.state' / 'automation'


def settings():
    data = json.loads((ROOT / 'schedule.json').read_text(encoding='utf-8-sig'))
    if data.get('mode', 'queue') not in ('queue', 'generate'):
        raise p.PushError('Schedule mode must be queue or generate.')
    if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', data['daily_time']):
        raise p.PushError('Invalid daily_time in schedule.json.')
    # This deployment explicitly uses Tashkent's fixed UTC+05:00 offset.
    if data['utc_offset'] != '+05:00':
        raise p.PushError('This schedule is configured for Tashkent (+05:00).')
    for key in ('catch_up_minutes', 'max_attempts', 'retry_minutes'):
        if type(data[key]) is not int or not 1 <= data[key] <= 120:
            raise p.PushError(f'Invalid {key} in schedule.json.')
    for value in data.get('sample_slots', []):
        p.parse_at(value)
    for value in data.get('excluded_slots', []):
        p.parse_at(value)
    for slot, key in data.get('run_aliases', {}).items():
        p.parse_at(slot)
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:_\d{4})?', key):
            raise p.PushError('Invalid rescheduled run alias.')
    if type(data.get('prepare_minutes', 0)) is not int or not 0 <= data.get('prepare_minutes', 0) <= 120:
        raise p.PushError('prepare_minutes must be between 0 and 120.')
    if 'poll_minutes' in data and (type(data['poll_minutes']) is not int or not 1 <= data['poll_minutes'] <= 59):
        raise p.PushError('poll_minutes must be between 1 and 59.')
    return data


TZ = timezone(timedelta(hours=5), 'Tashkent')


def slot_candidates(now, config, prepare=False):
    local = now.astimezone(TZ)
    hour, minute = map(int, config['daily_time'].split(':'))
    slots = {local.replace(hour=hour, minute=minute, second=0, microsecond=0)}
    slots.update(p.parse_at(value).astimezone(TZ) for value in config.get('sample_slots', []))
    slots.difference_update(p.parse_at(value).astimezone(TZ) for value in config.get('excluded_slots', []))
    lead = timedelta(minutes=config.get('prepare_minutes', 0) if prepare else 0)
    return [slot.isoformat() for slot in sorted(slots)
            if slot - lead <= local < slot + timedelta(minutes=config['catch_up_minutes'])]


def due_slot(now, config):
    candidates = slot_candidates(now, config)
    return candidates[-1] if candidates else None


class Queue:
    def __init__(self, folder):
        folder.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(folder / 'queue.sqlite3')
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS items (
                id TEXT PRIMARY KEY, account TEXT NOT NULL, digest TEXT NOT NULL,
                video TEXT NOT NULL, caption TEXT NOT NULL, created TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued', attempts INTEGER NOT NULL DEFAULT 0,
                next_attempt TEXT, error TEXT, permalink TEXT,
                UNIQUE(account, digest));
            CREATE TABLE IF NOT EXISTS slots (
                account TEXT NOT NULL, slot TEXT NOT NULL, item_id TEXT,
                PRIMARY KEY(account, slot));
        ''')
        self.db.commit()

    def claim(self, account, slot):
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            existing = self.db.execute('SELECT item_id FROM slots WHERE account=? AND slot=?',
                                       (account, slot)).fetchone()
            if existing:
                if not existing['item_id']:
                    return None
                row = self.db.execute('SELECT * FROM items WHERE id=?', (existing['item_id'],)).fetchone()
                return dict(row) if row else None
            row = self.db.execute("SELECT * FROM items WHERE account=? AND status='queued' "
                                  'ORDER BY created,id LIMIT 1', (account,)).fetchone()
            self.db.execute('INSERT INTO slots VALUES (?,?,?)',
                            (account, slot, row['id'] if row else None))
            if not row:
                return None
            self.db.execute("UPDATE items SET status='assigned' WHERE id=?", (row['id'],))
            result = dict(row)
            result['status'] = 'assigned'
            return result

    def update(self, item_id, **values):
        allowed = {'status', 'attempts', 'next_attempt', 'error', 'permalink'}
        if not values or not set(values) <= allowed:
            raise ValueError('Invalid queue update')
        with self.db:
            self.db.execute('UPDATE items SET ' + ','.join(f'{key}=?' for key in values) + ' WHERE id=?',
                            (*values.values(), item_id))


def publisher_job(account, digest):
    return hashlib.sha256(f'{account}:{digest}'.encode()).hexdigest()


def published_state(job):
    path = ROOT / '.state' / 'posts.sqlite3'
    if not path.exists():
        return {}
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
        row = db.execute('SELECT payload FROM posts WHERE job=?', (job,)).fetchone()
    return json.loads(row[0]) if row else {}


def enqueue(video, caption_file, account):
    video = video.resolve()
    p.inspect_video(video)
    caption = caption_file.read_text(encoding='utf-8-sig').strip()
    if not caption or len(caption) > 2200:
        raise p.PushError('Caption must contain 1–2200 characters.')
    digest = p.file_digest(video)
    job = publisher_job(account, digest)
    if published_state(job).get('phase') == 'published':
        raise p.PushError('This video was already published to this account; it was not queued again.')
    with p.process_lock(DATA), closing(Queue(DATA).db) as db:
        if db.execute('SELECT id FROM items WHERE account=? AND digest=?', (account, digest)).fetchone():
            raise p.PushError('This video is already in the queue/history for this account.')
        item_id = uuid.uuid4().hex[:12]
        assets = DATA / 'assets'
        assets.mkdir(exist_ok=True)
        snapshot = assets / (item_id + video.suffix.lower())
        shutil.copyfile(video, snapshot)
        if p.file_digest(snapshot) != digest:
            raise p.PushError('Video changed while being copied. Nothing was queued.')
        now = datetime.now(timezone.utc).isoformat()
        with db:
            db.execute('INSERT INTO items (id,account,digest,video,caption,created) VALUES (?,?,?,?,?,?)',
                       (item_id, account, digest, str(snapshot), caption, now))
    print('Queued:', item_id, 'for Instagram account', account)
    print('The worker will take the oldest queued video at the next daily posting slot.')
    return item_id


def process_item(queue, item, config, options, now):
    """Runs only for an assigned due slot, with local publisher locking."""
    job = publisher_job(config['INSTAGRAM_ACCOUNT_ID'], item['digest'])
    with p.process_lock(ROOT / '.state'):
        store = p.State(ROOT / '.state')
        try:
            state = store.get(job)
            if state.get('phase') == 'published':
                queue.update(item['id'], status='published', permalink=state.get('permalink'), error=None)
                print('Already published; queue reconciled:', item['id'])
                return 0
            if item['status'] in ('published', 'needs_attention'):
                print('Slot already handled:', item['status'])
                return 0 if item['status'] == 'published' else 1
            if item['attempts'] >= options['max_attempts']:
                queue.update(item['id'], status='needs_attention')
                print('Retry limit reached; inspect item:', item['id'])
                return 1
            if item['next_attempt'] and p.parse_at(item['next_attempt']) > now:
                print('Retry is not due yet.')
                return 0
            attempts = item['attempts'] + 1
            queue.update(item['id'], attempts=attempts, next_attempt=None)
            try:
                video = Path(item['video'])
                if p.file_digest(video) != item['digest']:
                    raise p.PushError('Queued video snapshot was changed; restore it before retrying.')
                api = p.Meta(config)
                identity = api.graph(config['INSTAGRAM_ACCOUNT_ID'], {'fields': 'id,username'})
                print('Target account:', identity.get('username', config['INSTAGRAM_ACCOUNT_ID']))
                if state.get('phase') == 'uploading':
                    p.retry_upload(api, store, job, config)
                result = p.push(api, store, job, video, item['caption'],
                                config['INSTAGRAM_ACCOUNT_ID'], True, 480)
                if result.get('phase') != 'published':
                    raise p.PushError('Publisher did not confirm publication.')
                queue.update(item['id'], status='published', permalink=result.get('permalink'), error=None)
                return 0
            except (p.PushError, OSError, ValueError) as exc:
                # Never dump raw local/network exceptions into unattended logs.
                message = str(exc) if isinstance(exc, p.PushError) else type(exc).__name__
                message = p.safe_diagnostic(message, config['META_ACCESS_TOKEN'])
                phase = store.get(job).get('phase')
                blocked = phase in ('creating', 'publishing') or attempts >= options['max_attempts']
                queue.update(item['id'], status='needs_attention' if blocked else 'assigned',
                             error=message,
                             next_attempt=(now + timedelta(minutes=options['retry_minutes'])).isoformat())
                print('Item requires attention.' if blocked else 'Attempt failed; retry retained for this slot.')
                print('ERROR:', message)
                return 1
        finally:
            store.db.close()


def run_live(config, options, now):
    if options.get('maintenance'):
        print('Automation is in maintenance: no generation, upload or publication attempted.')
        return 0
    if options.get('mode') == 'generate':
        import generation
        return generation.run_slot(config, options, now)
    slot = due_slot(now, options)
    if not slot:
        print('Outside the daily posting/catch-up window. No post attempted.')
        return 0
    with p.process_lock(DATA):
        queue = Queue(DATA)
        try:
            item = queue.claim(config['INSTAGRAM_ACCOUNT_ID'], slot)
            if not item:
                print('Daily slot has an empty queue; no post.')
                return 0
            print('Slot:', slot, 'Item:', item['id'])
            return process_item(queue, item, config, options, now)
        finally:
            queue.db.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    add = sub.add_parser('add', help='Copy a finished video and caption into the daily queue')
    add.add_argument('--video', type=Path, required=True)
    add.add_argument('--caption-file', type=Path, required=True)
    sub.add_parser('status', help='Show queue status without contacting Meta')
    reset = sub.add_parser('retry', help='Requeue a failed item for a future daily slot')
    reset.add_argument('item_id')
    run = sub.add_parser('run', help='Process the daily slot; offline preview unless --live')
    run.add_argument('--live', action='store_true')
    run.add_argument('--log', action='store_true', help='Write output to the daily log file')
    args = parser.parse_args(argv)
    options = settings()
    p.load_env(ROOT / '.env')
    config = p.configuration()
    if args.command == 'add':
        if options.get('mode') == 'generate':
            raise p.PushError('Finished-video queue is inactive in generation mode. Add a dated brief under briefs/.')
        enqueue(args.video, args.caption_file, config['INSTAGRAM_ACCOUNT_ID'])
        return 0
    if args.command == 'status':
        print('Schedule:', options['daily_time'], 'Tashkent (+05:00), one video per day.')
        print('Mode:', options.get('mode', 'queue'))
        print('Maintenance:', 'ON — scheduled publishing held for validation' if options.get('maintenance') else 'off')
        if options.get('mode') == 'generate':
            import generation
            import project_source
            date = datetime.now(TZ).date().isoformat()
            brief = ROOT / 'briefs' / (date + '.md')
            product = project_source.configuration(ROOT)
            if product.get('enabled'):
                manifest = project_source.scan(product['project_path'])
                print('Automatic brief source:', product['project_path'])
                print('Current working-tree version:', manifest['fingerprint'][:16])
            else:
                print('Daily brief:', 'FOUND' if brief.is_file() else 'MISSING — no generation/post until supplied')
            print('Sample targets:', ', '.join(options.get('sample_slots', [])) or 'none')
            folder = generation.RUNS / config['INSTAGRAM_ACCOUNT_ID']
            for run_file in sorted(folder.glob(date + '*/run.json')):
                print('Live run:', run_file.parent.name)
                print(p.safe_diagnostic(run_file.read_text(), config['META_ACCESS_TOKEN']))
            tests = generation.RUNS / ('test-' + config['INSTAGRAM_ACCOUNT_ID'])
            latest_tests = sorted(tests.glob('*/run.json'), key=lambda item: item.stat().st_mtime)
            if latest_tests:
                latest = latest_tests[-1]
                print('Latest no-publish test:', latest.parent.name)
                print(p.safe_diagnostic(latest.read_text(), config['META_ACCESS_TOKEN']))
            print('The finished-video queue below is inactive while mode=generate.')
        with closing(Queue(DATA).db) as db:
            rows = db.execute('SELECT id,status,attempts,error,permalink FROM items '
                              'WHERE account=? ORDER BY created', (config['INSTAGRAM_ACCOUNT_ID'],)).fetchall()
        for row in rows:
            print(p.safe_diagnostic(json.dumps(dict(row)), config['META_ACCESS_TOKEN']))
        if not rows:
            print('Queue is empty.')
        return 0
    if args.command == 'retry':
        with p.process_lock(DATA), closing(Queue(DATA).db) as db:
            row = db.execute('SELECT * FROM items WHERE id=? AND account=?',
                             (args.item_id, config['INSTAGRAM_ACCOUNT_ID'])).fetchone()
            if not row or row['status'] != 'needs_attention':
                raise p.PushError('Only a needs_attention item can be requeued.')
            if published_state(publisher_job(row['account'], row['digest'])).get('phase') in ('creating', 'publishing', 'published'):
                raise p.PushError('Publisher state needs reconciliation first. Inspect the publisher job.')
            with db:
                db.execute("UPDATE items SET status='queued',attempts=0,next_attempt=NULL,error=NULL WHERE id=?",
                           (args.item_id,))
                db.execute('UPDATE slots SET item_id=NULL WHERE item_id=?', (args.item_id,))
                # Keep consumed slots intact: a requeued item is considered on a later day.
        print('Requeued for a future daily slot:', args.item_id)
        return 0
    now = datetime.now(timezone.utc)
    if not args.live:
        print('OFFLINE PREVIEW. Schedule:', options['daily_time'], 'Tashkent (+05:00)')
        print('Mode:', options.get('mode', 'queue'))
        print('Due slot:', due_slot(now, options) or 'none right now')
        if options.get('mode') == 'generate':
            print('Preparation candidates:', ', '.join(slot_candidates(now, options, prepare=True)) or 'none')
        print('No slot claimed, no upload, no publication. Use status to inspect the queue.')
        return 0
    if args.log:
        logs = DATA / 'logs'
        logs.mkdir(parents=True, exist_ok=True)
        log = logs / (now.astimezone(TZ).date().isoformat() + '.log')
        with log.open('a', encoding='utf-8', buffering=1) as stream, \
                redirect_stdout(stream), redirect_stderr(stream):
            print('\nWorker started:', now.astimezone(TZ).isoformat())
            try:
                return run_live(config, options, now)
            except Exception as exc:
                message = str(exc) if isinstance(exc, p.PushError) else type(exc).__name__
                print('ERROR:', p.safe_diagnostic(message, config['META_ACCESS_TOKEN']))
                return 1
    return run_live(config, options, now)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except (p.PushError, OSError, ValueError, KeyError, sqlite3.Error) as exc:
        print('ERROR:', str(exc) if isinstance(exc, p.PushError) else type(exc).__name__, file=sys.stderr)
        sys.exit(1)
