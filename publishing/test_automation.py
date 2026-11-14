from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import automation as a
import install_task


OPTIONS = {'daily_time': '18:00', 'utc_offset': '+05:00', 'catch_up_minutes': 60,
           'max_attempts': 3, 'retry_minutes': 5}
CONFIG = {'INSTAGRAM_ACCOUNT_ID': '123', 'META_ACCESS_TOKEN': 'test-token',
          'META_API_VERSION': 'v27.0'}
NOW = datetime(2026, 11, 14, 13, 0, tzinfo=timezone.utc)


class AutomationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data = self.root / '.state' / 'automation'
        self.patches = [patch.object(a, 'ROOT', self.root), patch.object(a, 'DATA', self.data)]
        for item in self.patches:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in reversed(self.patches)])
        self.addCleanup(self.tmp.cleanup)
        self.queue = a.Queue(self.data)
        self.addCleanup(self.queue.db.close)

    def add_item(self, item_id='one', digest='a', created='2026-11-01', account='123'):
        video = self.root / (item_id + '.mp4')
        video.write_bytes(b'video')
        with self.queue.db:
            self.queue.db.execute('INSERT INTO items (id,account,digest,video,caption,created) VALUES (?,?,?,?,?,?)',
                                  (item_id, account, digest, str(video), 'caption', created))
        return video

    def test_due_time_uses_tashkent_not_host_timezone(self):
        self.assertEqual(a.due_slot(NOW, OPTIONS), '2026-11-14T18:00:00+05:00')
        self.assertIsNone(a.due_slot(NOW.replace(hour=12, minute=59), OPTIONS))
        self.assertIsNone(a.due_slot(NOW.replace(hour=14), OPTIONS))

    def test_slot_keeps_first_item_across_repeated_runs(self):
        self.add_item('two', 'b', '2026-11-02')
        self.add_item('one', 'a', '2026-11-01')
        slot = a.due_slot(NOW, OPTIONS)
        self.assertEqual(self.queue.claim('123', slot)['id'], 'one')
        self.queue.update('one', status='published')
        self.assertEqual(self.queue.claim('123', slot)['id'], 'one')
        self.assertEqual(self.queue.claim('123', '2026-11-15T18:00:00+05:00')['id'], 'two')

    def test_empty_slot_does_not_publish_a_late_arriving_item(self):
        slot = a.due_slot(NOW, OPTIONS)
        self.assertIsNone(self.queue.claim('123', slot))
        self.add_item()
        self.assertIsNone(self.queue.claim('123', slot))

    def test_account_queues_are_separate(self):
        self.add_item(account='999')
        self.assertIsNone(self.queue.claim('123', a.due_slot(NOW, OPTIONS)))

    def test_enqueue_snapshots_input_and_rejects_duplicate(self):
        video = self.root / 'source.mp4'
        video.write_bytes(b'original')
        caption = self.root / 'caption.txt'
        caption.write_text('first caption')
        with patch.object(a.p, 'inspect_video'):
            item_id = a.enqueue(video, caption, '123')
            with self.assertRaises(a.p.PushError):
                a.enqueue(video, caption, '123')
        row = self.queue.db.execute('SELECT * FROM items WHERE id=?', (item_id,)).fetchone()
        video.write_bytes(b'changed')
        caption.write_text('changed')
        self.assertEqual(Path(row['video']).read_bytes(), b'original')
        self.assertEqual(row['caption'], 'first caption')

    def test_previously_published_video_is_not_enqueued(self):
        video = self.root / 'source.mp4'
        video.write_bytes(b'original')
        caption = self.root / 'caption.txt'
        caption.write_text('caption')
        with patch.object(a.p, 'inspect_video'), \
                patch.object(a, 'published_state', return_value={'phase': 'published'}):
            with self.assertRaises(a.p.PushError):
                a.enqueue(video, caption, '123')
        self.assertEqual(self.queue.db.execute('SELECT count(*) FROM items').fetchone()[0], 0)

    def test_outside_window_does_not_create_api_or_claim_slot(self):
        self.add_item()
        with patch.object(a.p, 'Meta', side_effect=AssertionError('no API')):
            self.assertEqual(a.run_live(CONFIG, OPTIONS, NOW.replace(hour=10)), 0)
        self.assertEqual(self.queue.db.execute('SELECT count(*) FROM slots').fetchone()[0], 0)

    def test_already_published_state_is_reconciled_without_api(self):
        self.add_item()
        item = self.queue.claim('123', a.due_slot(NOW, OPTIONS))
        job = a.publisher_job('123', 'a')
        store = a.p.State(self.root / '.state')
        store.save(job, {'phase': 'published', 'permalink': 'https://www.instagram.com/reel/test/'})
        store.db.close()
        with patch.object(a.p, 'Meta', side_effect=AssertionError('no API')):
            self.assertEqual(a.process_item(self.queue, item, CONFIG, OPTIONS, NOW), 0)
        status = self.queue.db.execute('SELECT status FROM items WHERE id=?', ('one',)).fetchone()[0]
        self.assertEqual(status, 'published')

    def test_publisher_success_marks_daily_slot_item(self):
        video = self.add_item(digest=a.p.hashlib.sha256(b'video').hexdigest())
        item = self.queue.claim('123', a.due_slot(NOW, OPTIONS))
        with patch.object(a.p, 'Meta') as client, \
                patch.object(a.p, 'push', return_value={'phase': 'published', 'permalink': 'link'}) as push:
            client.return_value.graph.return_value = {'username': 'test'}
            self.assertEqual(a.process_item(self.queue, item, CONFIG, OPTIONS, NOW), 0)
        push.assert_called_once()
        self.assertEqual(push.call_args.args[3], video)
        self.assertEqual(self.queue.claim('123', a.due_slot(NOW, OPTIONS))['status'], 'published')

    def test_failure_does_not_take_second_video_for_same_slot(self):
        self.add_item('one', a.p.hashlib.sha256(b'video').hexdigest())
        self.add_item('two', 'different', '2026-11-02')
        item = self.queue.claim('123', a.due_slot(NOW, OPTIONS))
        with patch.object(a.p, 'Meta') as client:
            client.return_value.graph.side_effect = a.p.PushError('network failed test-token')
            self.assertEqual(a.process_item(self.queue, item, CONFIG, OPTIONS, NOW), 1)
        retry = self.queue.claim('123', a.due_slot(NOW, OPTIONS))
        self.assertEqual(retry['id'], 'one')
        self.assertEqual(retry['attempts'], 1)
        self.assertNotIn('test-token', retry['error'])

    def test_attempt_limit_prevents_api_calls(self):
        self.add_item()
        slot = a.due_slot(NOW, OPTIONS)
        self.queue.claim('123', slot)
        self.queue.update('one', attempts=3)
        item = self.queue.claim('123', slot)
        with patch.object(a.p, 'Meta', side_effect=AssertionError('no API')):
            self.assertEqual(a.process_item(self.queue, item, CONFIG, OPTIONS, NOW), 1)
        self.assertEqual(self.queue.claim('123', slot)['status'], 'needs_attention')

    def test_offline_preview_does_not_claim_or_publish(self):
        with patch.object(a, 'settings', return_value=OPTIONS), patch.object(a.p, 'load_env'), \
                patch.object(a.p, 'configuration', return_value=CONFIG), \
                patch.object(a.p, 'Meta', side_effect=AssertionError('no API')):
            self.assertEqual(a.main(['run']), 0)
        self.assertEqual(self.queue.db.execute('SELECT count(*) FROM slots').fetchone()[0], 0)

    def test_task_definition_is_daily_limited_and_windowless(self):
        tree = install_task.task_xml(self.root, Path('C:/Python315/pythonw.exe'),
                                     'S-1-5-21-test', OPTIONS, NOW.astimezone(a.TZ).date())
        root = tree.getroot()
        ns = {'t': install_task.NS}
        self.assertEqual(root.find('.//t:StartBoundary', ns).text,
                         '2026-11-14T18:00:00+05:00')
        self.assertEqual(root.find('.//t:DaysInterval', ns).text, '1')
        self.assertEqual(root.find('.//t:LogonType', ns).text, 'InteractiveToken')
        self.assertEqual(root.find('.//t:RunLevel', ns).text, 'LeastPrivilege')
        self.assertEqual(root.find('.//t:MultipleInstancesPolicy', ns).text, 'IgnoreNew')
        self.assertEqual(root.find('.//t:RestartOnFailure/t:Count', ns).text, '2')
        self.assertIn('run --live --log', root.find('.//t:Arguments', ns).text)


if __name__ == '__main__':
    unittest.main()
