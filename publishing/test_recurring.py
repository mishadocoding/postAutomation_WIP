from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import automation as a
import generation as g
import install_task
import notifications as n
import project_source as s
import push_reel as p
import video_history as v
from test_generation import FakeRunner, CONFIG, GEN, OPTIONS


class RecurringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def source(self):
        folder = self.root / 'app'
        folder.mkdir()
        (folder / 'index.html').write_text('<h1>Current app</h1>')
        (folder / 'app.js').write_text('const stock = 10;')
        (folder / '.env').write_text('secret=nevercopy')
        return folder

    def test_unsaved_to_git_working_tree_change_updates_fingerprint(self):
        folder = self.source()
        first = s.scan(folder)
        (folder / 'app.js').write_text('const stock = 11;')
        self.assertNotEqual(first['fingerprint'], s.scan(folder)['fingerprint'])
        self.assertNotIn('.env', first['files'])

    def test_capture_is_consistent_and_stale_source_is_rejected(self):
        folder = self.source()
        project = self.root / 'video'
        project.mkdir()
        config = {'project_path': str(folder)}
        manifest = s.capture(config, project)
        s.assert_snapshot(project, manifest)
        s.assert_current(config, manifest)
        (folder / 'app.js').write_text('new feature')
        with self.assertRaises(p.PushError):
            s.assert_current(config, manifest)

    def test_edited_source_snapshot_is_rejected(self):
        folder = self.source()
        project = self.root / 'video'
        project.mkdir()
        manifest = s.capture({'project_path': str(folder)}, project)
        (project / manifest['reference_directory'] / 'app.js').write_text('fake product')
        with self.assertRaises(p.PushError):
            s.assert_snapshot(project, manifest)

    def test_two_todays_slots_and_preparation_window(self):
        options = dict(OPTIONS, prepare_minutes=50,
                       sample_slots=['2026-11-14T18:00:00+05:00', '2026-11-14T19:00:00+05:00'])
        early = datetime.fromisoformat('2026-11-14T17:20:00+05:00')
        self.assertEqual(a.slot_candidates(early, options, prepare=True), ['2026-11-14T18:00:00+05:00'])
        self.assertIsNone(a.due_slot(early, options))
        self.assertEqual(a.due_slot(datetime.fromisoformat('2026-11-14T19:00:00+05:00'), options),
                         '2026-11-14T19:00:00+05:00')
        tomorrow = datetime.fromisoformat('2026-11-15T19:10:00+05:00')
        self.assertEqual(a.slot_candidates(tomorrow, options, prepare=True), [])

    def test_same_day_slots_have_distinct_run_keys(self):
        self.assertEqual(g.run_key('2026-11-14T18:00:00+05:00', OPTIONS), '2026-11-14')
        self.assertEqual(g.run_key('2026-11-14T19:00:00+05:00', OPTIONS), '2026-11-14_1900')

    def test_visual_distance_ignores_file_bytes(self):
        hashes = ['0123456789abcdef'] * 16
        self.assertEqual(v.distance(hashes, hashes), 0)
        self.assertEqual(v.distance(['0' * 16] * 16, ['f' * 16] * 16), 1)

    def test_reencoded_visual_duplicate_is_rejected(self):
        history = v.History(self.root)
        self.addCleanup(history.db.close)
        fingerprint = ['0123456789abcdef'] * 16
        history.record('123', 'old-slot', 'old-file-hash', fingerprint, 'old story')
        with self.assertRaises(p.PushError):
            history.check('123', 'new-slot', 'different-file-hash', fingerprint)
        history.check('123', 'old-slot', 'old-file-hash', fingerprint)

    def test_exact_duplicate_is_rejected_even_if_fingerprint_differs(self):
        history = v.History(self.root)
        self.addCleanup(history.db.close)
        history.record('123', 'old', 'same-hash', ['0' * 16] * 16, 'story')
        with self.assertRaises(p.PushError):
            history.check('123', 'new', 'same-hash', ['f' * 16] * 16)

    def test_notification_payload_is_data_not_executable_code(self):
        with patch.object(n.subprocess, 'Popen') as spawn:
            process = Mock()
            process.returncode = 0
            spawn.return_value = process
            self.assertTrue(n.send(self.root, 'Published', 'hello $(unsafe)', 'https://www.instagram.com/reel/test/'))
        args = spawn.call_args.args[0]
        self.assertNotIn('hello $(unsafe)', args[-1])
        payload = json.loads(process.communicate.call_args.args[0])
        self.assertEqual(payload['message'], 'hello $(unsafe)')

    def test_notification_is_sent_once_per_kind(self):
        state = {}
        path = self.root / 'state.json'
        with patch.object(n, 'send') as send:
            g.notify_once(state, path, {'notifications': True}, 'published', 'success')
            g.notify_once(state, path, {'notifications': True}, 'published', 'success')
            send.assert_called_once()

    def test_poll_task_checks_every_two_minutes(self):
        options = dict(OPTIONS, poll_minutes=2, prepare_minutes=50)
        tree = install_task.task_xml(self.root, Path('pythonw.exe'), 'sid', options, datetime(2026, 11, 14).date())
        ns = {'t': install_task.NS}
        self.assertEqual(tree.getroot().find('.//t:Repetition/t:Interval', ns).text, 'PT2M')
        self.assertEqual(tree.getroot().find('.//t:StartBoundary', ns).text, '2026-11-14T00:00:00+05:00')

    def test_prepared_video_is_not_published_early(self):
        early = datetime.fromisoformat('2026-11-14T17:20:00+05:00')
        root = self.root
        (root / 'briefs').mkdir()
        (root / 'briefs' / '2026-11-14.md').write_text('brief')
        options = dict(OPTIONS, prepare_minutes=50)
        runner = FakeRunner()
        with patch.object(g, 'ROOT', root), patch.object(g, 'RUNS', root / '.state' / 'generation'), \
                patch.object(g, 'load_settings', return_value=GEN), patch.object(g, 'datetime') as clock, \
                patch.object(g, 'publish_approved', return_value={'phase': 'processing'}) as publish:
            clock.now.return_value = early.astimezone(timezone.utc)
            self.assertEqual(g.run_slot(CONFIG, options, early, lambda *args: runner), 0)
            self.assertTrue(publish.call_args.kwargs['prepare_only'])
            state = json.loads((root / '.state' / 'generation' / '123' / '2026-11-14' / 'run.json').read_text())
            self.assertEqual(state['phase'], 'approved')

    def test_rescheduled_old_slot_is_excluded_while_19_remains(self):
        options = dict(OPTIONS, prepare_minutes=50,
                       sample_slots=['2026-11-14T18:30:00+05:00', '2026-11-14T19:00:00+05:00'],
                       excluded_slots=['2026-11-14T18:00:00+05:00'],
                       run_aliases={'2026-11-14T18:30:00+05:00': '2026-11-14'})
        now = datetime.fromisoformat('2026-11-14T18:27:00+05:00')
        candidates = a.slot_candidates(now, options, prepare=True)
        self.assertNotIn('2026-11-14T18:00:00+05:00', candidates)
        self.assertEqual(candidates, ['2026-11-14T18:30:00+05:00', '2026-11-14T19:00:00+05:00'])
        self.assertEqual(g.run_key(candidates[0], options), '2026-11-14')
        with patch.object(g, 'ROOT', self.root):
            (self.root / 'schedule.json').write_text(json.dumps(options))
            with self.assertRaises(p.PushError):
                g.assert_slot_active('2026-11-14T18:00:00+05:00', now)
            g.assert_slot_active('2026-11-14T18:30:00+05:00', now)


if __name__ == '__main__':
    unittest.main()
