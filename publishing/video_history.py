"""Exact and decoded-frame duplicate checks, including already published videos."""
from contextlib import closing
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess

import push_reel as p


def signatures(video):
    media = p.inspect_video(video)
    ffmpeg = shutil.which('ffmpeg')
    result = subprocess.run([ffmpeg, '-v', 'error', '-i', str(video), '-vf',
                             f"fps={16 / media['duration_seconds']},scale=9:8:flags=area,format=gray",
                             '-frames:v', '16', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'],
                            capture_output=True, timeout=90)
    data = result.stdout
    if result.returncode or len(data) != 16 * 72:
        raise p.PushError('Could not produce complete decoded novelty fingerprints.')
    hashes = []
    for start in range(0, len(data), 72):
        frame = data[start:start + 72]
        value = 0
        for row in range(8):
            for col in range(8):
                value = (value << 1) | int(frame[row * 9 + col] > frame[row * 9 + col + 1])
        hashes.append(f'{value:016x}')
    return hashes


def distance(left, right):
    if len(left) != len(right) or not left:
        raise p.PushError('Incompatible visual fingerprint lengths.')
    return sum((int(x, 16) ^ int(y, 16)).bit_count() for x, y in zip(left, right)) / (64 * len(left))


class History:
    def __init__(self, root):
        self.root = root
        folder = root / '.state' / 'generation'
        folder.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(folder / 'history.sqlite3')
        self.db.row_factory = sqlite3.Row
        self.db.execute('CREATE TABLE IF NOT EXISTS videos ('
                        'account TEXT, owner TEXT, digest TEXT, fingerprint TEXT, context TEXT, '
                        'status TEXT, PRIMARY KEY(account,owner))')
        self.db.commit()

    def import_published(self, account):
        path = self.root / '.state' / 'posts.sqlite3'
        if not path.is_file():
            return
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
            rows = db.execute('SELECT job,payload FROM posts').fetchall()
        for job, raw in rows:
            state = json.loads(raw)
            if state.get('account_id') != account or state.get('phase') != 'published':
                continue
            owner = 'legacy:' + job
            if self.db.execute('SELECT 1 FROM videos WHERE account=? AND owner=?', (account, owner)).fetchone():
                continue
            video = Path(state.get('video', ''))
            if not video.is_file():
                raise p.PushError('A published video is missing locally; cannot complete duplicate screening.')
            digest = p.file_digest(video)
            if self.db.execute('SELECT 1 FROM videos WHERE account=? AND digest=?', (account, digest)).fetchone():
                continue
            self.record(account, owner, digest, signatures(video),
                        'Previously published Reel: ' + str(state.get('permalink', state.get('media_id', ''))), 'published')

    def recent(self, account):
        return [dict(row) for row in self.db.execute('SELECT owner,context,status FROM videos WHERE account=? '
                                                    'ORDER BY rowid DESC LIMIT 8', (account,))]

    def check(self, account, owner, digest, fingerprint):
        compared = 0
        closest = None
        for row in self.db.execute('SELECT * FROM videos WHERE account=? AND owner<>?', (account, owner)):
            compared += 1
            if row['digest'] == digest:
                raise p.PushError('Exact duplicate of a previous approved/published video. Create a new film.')
            score = distance(json.loads(row['fingerprint']), fingerprint)
            closest = score if closest is None else min(closest, score)
            if score <= 0.04:
                raise p.PushError('Video is visually too similar to a previous film, even if re-encoded. '
                                  'Change the hook, composition and shot sequence.')
        return {'ok': True, 'compared_videos': compared, 'closest_distance': closest,
                'rejection_distance': 0.04, 'exact_hash_unique': True,
                'method': '16 normalized decoded-frame difference hashes'}

    def record(self, account, owner, digest, fingerprint, context, status='approved'):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO videos VALUES (?,?,?,?,?,?)',
                            (account, owner, digest, json.dumps(fingerprint), context[:5000], status))
