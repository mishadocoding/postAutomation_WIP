"""Dated finished-file posts, consumed by the existing background worker."""
from datetime import datetime, timedelta, timezone
import getpass
import json
import os
import sys

import automation as a
import notifications


def run_due(queue, config, options, now):
    rows = queue.db.execute('SELECT s.*,i.status FROM scheduled_files s JOIN items i ON i.id=s.item_id '
                            'WHERE s.account=? ORDER BY s.at', (config['INSTAGRAM_ACCOUNT_ID'],)).fetchall()
    for scheduled in rows:
        target = a.p.parse_at(scheduled['at'])
        if scheduled['status'] in ('published', 'needs_attention') or now < target:
            continue
        print('Scheduled file target:', target.astimezone(a.TZ).isoformat(), 'item:', scheduled['item_id'], flush=True)
        if now >= target + timedelta(minutes=options['catch_up_minutes']):
            queue.update(scheduled['item_id'], status='needs_attention', error='One-off publication window elapsed.')
            notify(queue, scheduled['item_id'], 'needs_attention', None, options)
            return 1
        execution = {'source': 'scheduled_file_worker', 'user': getpass.getuser(),
                     'pid': os.getpid(), 'python': sys.executable, 'target': scheduled['at'],
                     'started_at': datetime.now(timezone.utc).isoformat()}
        with queue.db:
            queue.db.execute('UPDATE scheduled_files SET started_at=COALESCE(started_at,?),executed_by=? WHERE item_id=?',
                             (execution['started_at'], json.dumps(execution), scheduled['item_id']))
            queue.db.execute("UPDATE items SET status='assigned' WHERE id=? AND status='queued'", (scheduled['item_id'],))
        item = dict(queue.db.execute('SELECT * FROM items WHERE id=?', (scheduled['item_id'],)).fetchone())
        def ensure_due():
            current = a.settings()
            if current.get('maintenance'):
                raise a.p.PushError('Scheduled publication held for maintenance.')
            actual = datetime.now(timezone.utc)
            if actual < target or actual >= target + timedelta(minutes=current['catch_up_minutes']):
                raise a.p.PushError('One-off publication is outside its authorized time window.')
        result = a.process_item(queue, item, config, options, now,
                                execution=execution, before_publish=ensure_due)
        updated = queue.db.execute('SELECT * FROM items WHERE id=?', (item['id'],)).fetchone()
        if updated['status'] == 'published':
            state = a.published_state(a.publisher_job(config['INSTAGRAM_ACCOUNT_ID'], item['digest']))
            attributed = state.get('execution', {}).get('source') == 'scheduled_file_worker'
            print('Scheduled file publication confirmed.' if attributed else
                  'Publication found in existing history; not counted as a new worker publication.', flush=True)
            print('Permalink:', updated['permalink'], flush=True)
            with queue.db:
                queue.db.execute('UPDATE scheduled_files SET completed_at=? WHERE item_id=?',
                                 (datetime.now(timezone.utc).isoformat(), item['id']))
        notify(queue, item['id'], updated['status'], updated['permalink'], options)
        return result
    return None


def notify(queue, item_id, status, permalink, options):
    if status not in ('published', 'needs_attention') or not options.get('notifications'):
        return
    row = queue.db.execute('SELECT notified_status FROM scheduled_files WHERE item_id=?', (item_id,)).fetchone()
    if row['notified_status'] == status:
        return
    notifications.send(a.ROOT, 'Instagram published' if status == 'published' else 'Instagram held',
                       'Scheduled file post published.' if status == 'published' else 'Scheduled file post needs attention.',
                       permalink)
    with queue.db:
        queue.db.execute('UPDATE scheduled_files SET notified_status=? WHERE item_id=?', (status, item_id))
