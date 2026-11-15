from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import automation as a
import scheduled_posts as s


CONFIG = {'INSTAGRAM_ACCOUNT_ID': '123', 'META_ACCESS_TOKEN': 'secret', 'META_API_VERSION': 'v27.0'}
OPTIONS = {'mode': 'generate', 'daily_time': '18:00', 'utc_offset': '+05:00',
           'catch_up_minutes': 60, 'max_attempts': 3, 'retry_minutes': 5,
           'poll_minutes': 2, 'notifications': True}


class ScheduledFileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patches = [patch.object(a, 'ROOT', self.root), patch.object(a, 'DATA', self.root / 'data'),
                        patch.object(a, 'settings', return_value=OPTIONS)]
        for item in self.patches: item.start()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(lambda: [item.stop() for item in reversed(self.patches)])
        self.target = datetime.now(timezone.utc) + timedelta(minutes=10)
        self.video = self.root / 'video.mp4'
        self.video.write_bytes(b'unique ready video')
        self.caption = self.root / 'caption.txt'
        self.caption.write_text('Caption')

    def queue_file(self):
        with patch.object(a.p, 'inspect_video'), patch.object(a.p, 'Meta', side_effect=AssertionError('no network on registration')):
            item = a.enqueue(self.video, self.caption, '123', self.target.isoformat())
        self.queue = a.Queue(a.DATA)
        self.addCleanup(self.queue.db.close)
        return item

    def test_registration_snapshots_file_and_does_not_use_daily_fifo(self):
        self.queue_file()
        self.assertIsNone(self.queue.claim('123', self.target.isoformat()))
        row = self.queue.db.execute('SELECT * FROM items').fetchone()
        self.assertEqual(Path(row['video']).read_bytes(), b'unique ready video')

    def test_future_target_does_not_call_meta(self):
        self.queue_file()
        with patch.object(a.p, 'Meta', side_effect=AssertionError('early publication')):
            self.assertIsNone(s.run_due(self.queue, CONFIG, OPTIONS, self.target - timedelta(seconds=1)))

    def test_due_file_runs_in_generation_mode_and_records_worker_publication(self):
        self.queue_file()
        def publish(api, store, job, *args, **kwargs):
            kwargs['before_publish']()
            state = store.get(job)
            self.assertEqual(state['execution']['source'], 'scheduled_file_worker')
            state.update(phase='published', permalink='https://www.instagram.com/reel/test/')
            store.save(job, state)
            return state
        clock = Mock(wraps=datetime)
        clock.now.return_value = self.target
        with patch.object(a.p, 'Meta') as api, patch.object(a.p, 'push', side_effect=publish) as pushed, \
                patch.object(s, 'datetime', clock), patch.object(s.notifications, 'send') as notify:
            api.return_value.graph.return_value = {'username': 'test'}
            self.assertEqual(a.run_live(CONFIG, OPTIONS, self.target), 0)
            self.assertEqual(a.run_live(CONFIG, OPTIONS, self.target), 0)
            self.assertEqual(pushed.call_count, 1)
            self.assertEqual(notify.call_count, 1)
        row = self.queue.db.execute('SELECT * FROM scheduled_files').fetchone()
        self.assertIsNotNone(row['completed_at'])
        self.assertIn('scheduled_file_worker', row['executed_by'])

    def test_expired_file_is_held_without_api(self):
        self.queue_file()
        with patch.object(a.p, 'Meta', side_effect=AssertionError('late publication')), patch.object(s.notifications, 'send'):
            self.assertEqual(s.run_due(self.queue, CONFIG, OPTIONS, self.target + timedelta(hours=1)), 1)
        self.assertEqual(self.queue.db.execute('SELECT status FROM items').fetchone()[0], 'needs_attention')

    def test_maintenance_holds_scheduled_files(self):
        self.queue_file()
        with patch.object(a.p, 'Meta', side_effect=AssertionError('maintenance')):
            self.assertEqual(a.run_live(CONFIG, dict(OPTIONS, maintenance=True), self.target), 0)

    def test_duplicate_poll_is_coalesced_and_later_poll_runs(self):
        instant = datetime(2026, 11, 15, 10, 0, tzinfo=timezone.utc)
        with patch.object(a, 'run_live', return_value=0) as live:
            a.run_single_worker(CONFIG, OPTIONS, instant)
            a.run_single_worker(CONFIG, OPTIONS, instant + timedelta(seconds=48))
            self.assertEqual(live.call_count, 1)
            a.run_single_worker(CONFIG, OPTIONS, instant + timedelta(minutes=2))
            self.assertEqual(live.call_count, 2)


if __name__ == '__main__': unittest.main()
