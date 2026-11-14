"""Capture the actual working tree and create a factual sampleERP brief."""
import hashlib
import json
from pathlib import Path
import shutil
import time

import push_reel as p

EXTENSIONS = {'.html', '.css', '.js', '.mjs', '.cjs', '.json', '.md', '.txt',
              '.svg', '.png', '.jpg', '.jpeg', '.webp', '.woff', '.woff2'}
EXCLUDED = {'node_modules', '.git', 'dist', 'build', 'coverage', 'publishing', 'renders'}


def configuration(root):
    path = root / 'project_source.json'
    if not path.is_file():
        return {'enabled': False}
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    if value.get('enabled'):
        project = Path(value['project_path'])
        if not project.is_dir() or not (project / 'index.html').is_file():
            raise p.PushError('Configured product project/index.html was not found.')
    return value


def scan(project):
    project = Path(project).resolve()
    files = {}
    total = 0
    for path in sorted(project.rglob('*')):
        relative = path.relative_to(project)
        if any(part.startswith('.') or part in EXCLUDED for part in relative.parts):
            continue
        if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
            raise p.PushError('Product source contains a link/junction; snapshot refused.')
        if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
            continue
        if any(word in path.name.lower() for word in ('secret', 'credential', 'token', 'password')):
            continue
        total += path.stat().st_size
        if total > 100_000_000 or len(files) >= 2000:
            raise p.PushError('Product source snapshot exceeds the configured size/file limit.')
        files[relative.as_posix()] = p.file_digest(path)
    digest = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    return {'fingerprint': digest, 'files': files}


def assert_current(config, manifest):
    if scan(config['project_path'])['fingerprint'] != manifest['fingerprint']:
        raise p.PushError('Product project changed since generation. Regenerate from the latest working tree.')


def capture(config, project):
    source = Path(config['project_path']).resolve()
    for attempt in range(3):
        manifest = scan(source)
        folder = project / 'reference-source' / (manifest['fingerprint'][:16] + '-' + str(time.time_ns()))
        folder.mkdir(parents=True)
        for relative, digest in manifest['files'].items():
            target = folder / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / relative, target)
            if p.file_digest(target) != digest:
                break
        else:
            if scan(source)['fingerprint'] == manifest['fingerprint']:
                manifest['reference_directory'] = str(folder.relative_to(project))
                return manifest
        time.sleep(0.2)
    raise p.PushError('Product source is changing during capture. Wait for a stable save before retrying.')


def assert_snapshot(project, manifest):
    folder = project / manifest['reference_directory']
    for relative, digest in manifest['files'].items():
        if p.file_digest(folder / relative) != digest:
            raise p.PushError('The read-only product snapshot was changed by the author; review blocked.')


def brief(config, manifest, slot, history):
    number = int(slot.strftime('%Y%m%d%H%M'))
    topic_index = 0 if slot.hour == 18 else 1 if slot.hour == 19 else number % len(config['topics'])
    topic = config['topics'][topic_index % len(config['topics'])]
    styles = ['light editorial layout with green accents and a left-to-right causal sequence',
              'dark navy layout with warm orange highlights and close-up detail reveals',
              'warm off-white layout with blue highlights and a top-to-bottom narrative']
    style = styles[(slot.day + slot.hour) % len(styles)]
    return f'''Create a NEW {config['target_duration_seconds']}-second vertical Reel about {config['brand']}.
Language: {config['language']}. Edition: {slot.isoformat()}.
Selected subject: {topic}. Visual direction: {style}.
This is a sample/demo advertisement, not a production-software claim.

CURRENT PRODUCT WORKING-TREE FINGERPRINT: {manifest['fingerprint']}
AUTHORITATIVE SOURCE: {manifest['reference_directory']}/ in this project workspace.
Read its README.txt and actual HTML/JS/CSS before making any claim. The source code
is authoritative if the README is stale. Inspect the current app in an isolated
browser profile; capture real, current product screens when showing product UI.
Never edit the original app or the read-only reference snapshot. Do not reuse old
captures from previous promos. If the chosen feature no longer exists, select a
different real feature and document why in SPEC.md.

Tell one clear story in three purposeful scenes. Show the actual current workflow,
not an invented dashboard. Keep related items, pointer contacts, stock values and
state transitions consistent. Use current source values, not remembered values.
State on the end card/caption that this is a sampleERP demonstration. Do not claim
real payments, secure production authorization, accounting, multi-user sync, or
integrations unless the CURRENT code actually implements them.
Use a NEW hook, shot sequence, camera movement and callout arrangement. The topic
may repeat, but do not reproduce a previous film or merely change its caption.
No voiceover or paid generated media is required. Use existing locally available
assets and sound if suitable, otherwise a short silent motion-graphics Reel.

RECENT VIDEO HISTORY (avoid reproducing these):
{json.dumps(history, ensure_ascii=True)}

The visual reviewer must verify source freshness, faithful UI, object matching,
and novelty as well as normal legibility/continuity/motion checks.
'''
