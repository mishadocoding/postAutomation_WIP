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


NOW = datetime(2026, 11, 14, 13, 0, tzinfo=timezone.utc)
OPTIONS = {'mode': 'generate', 'daily_time': '18:00', 'utc_offset': '+05:00',
           'catch_up_minutes': 60, 'max_attempts': 3, 'retry_minutes': 5}
CONFIG = {'INSTAGRAM_ACCOUNT_ID': '123', 'META_ACCESS_TOKEN': 'secret'}
GEN = {'max_attempts': 3, 'run_budget_minutes': 90}


def valid_check():
    report = {'ok': True, 'browserSkipped': False}
    for key in ('lint', 'runtime', 'layout', 'motion', 'contrast', 'craft', 'audio'):
        report[key] = {'ok': True, 'errorCount': 0, 'warningCount': 0}
    report['layout']['samples'] = [0, 1, 2]
    report['motion'].update(enabled=True, samples=60, specPath='index.motion.json')
    report['contrast']['checked'] = 3
    return report


def valid_review(evidence):
    return {'verdict': 'pass', 'video_sha256': evidence['video_sha256'],
            'reviewed_images': evidence['images'], 'checks': {key: True for key in g.CHECKS},
            'findings': [], 'uncertainties': []}


class FakeRunner:
    def __init__(self, fail_reviews=0, blocked=False):
        self.fail_reviews = fail_reviews
        self.blocked = blocked
        self.authors = []
        self.reviews = 0

    def author(self, project, attempt, brief, feedback, previous_images):
        self.authors.append(feedback)
        (project / 'index.html').write_text('<html>source</html>')
        (project / 'caption.txt').write_text('approved caption')
        return {'status': 'blocked' if self.blocked else 'ready', 'summary': 'test'}

    def check(self, project, attempt):
        g.write_json(attempt / 'check.json', valid_check())

    def render(self, project, attempt):
        video = attempt / 'video.mp4'
        video.write_bytes(b'final-video')
        image = attempt / 'sheet-001.jpg'
        image.write_bytes(b'frame-evidence')
        evidence = {'video_sha256': g.p.file_digest(video), 'images': ['sheet-001.jpg'],
                    'image_hashes': {'sheet-001.jpg': g.p.file_digest(image)}}
        g.write_json(attempt / 'evidence.json', evidence)
        return video, [image], evidence

    def review(self, project, attempt, brief, images, evidence):
        self.reviews += 1
        result = valid_review(evidence)
        if self.reviews <= self.fail_reviews:
            result['verdict'] = 'fail'
            result['findings'] = [{'severity': 'P1', 'time_seconds': 2.0,
                                   'problem': 'Pointer misses button', 'fix': 'Share a contact anchor'}]
        return result

    def screen(self, project, attempt, video, evidence, config, owner, product, manifest):
        evidence.update(source_freshness={'ok': True}, novelty={'ok': True, 'compared_videos': 0})
        g.write_json(attempt / 'evidence.json', evidence)
        return ['0123456789abcdef'] * 16


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.runs = self.root / '.state' / 'generation'
        clock = Mock(wraps=datetime)
        clock.now.return_value = NOW
        self.patches = [patch.object(g, 'ROOT', self.root), patch.object(g, 'RUNS', self.runs),
                        patch.object(g, 'load_settings', return_value=GEN), patch.object(g, 'datetime', clock)]
        for item in self.patches:
            item.start()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(lambda: [item.stop() for item in reversed(self.patches)])

    def brief(self):
        folder = self.root / 'briefs'
        folder.mkdir()
        (folder / '2026-11-14.md').write_text('Approved facts, assets, and caption')

    def run_pipeline(self, runner):
        return g.run_slot(CONFIG, OPTIONS, NOW, lambda *args: runner)

    def test_no_brief_means_no_generation_or_publication(self):
        factory = Mock(side_effect=AssertionError('must not start AI'))
        with patch.object(g, 'publish_approved', side_effect=AssertionError('must not publish')):
            self.assertEqual(g.run_slot(CONFIG, OPTIONS, NOW, factory), 0)
        factory.assert_not_called()
        state = json.loads((self.runs / '123' / '2026-11-14' / 'run.json').read_text())
        self.assertEqual(state['phase'], 'awaiting_brief')

    def test_before_daily_time_means_no_run(self):
        self.assertEqual(g.run_slot(CONFIG, OPTIONS, NOW.replace(hour=12),
                                    Mock(side_effect=AssertionError('no AI'))), 0)

    def test_failed_review_repairs_before_publication(self):
        self.brief()
        runner = FakeRunner(fail_reviews=1)
        with patch.object(g, 'publish_approved', return_value={'phase': 'published', 'media_id': 'm'}) as publish:
            self.assertEqual(self.run_pipeline(runner), 0)
        self.assertEqual(len(runner.authors), 2)
        self.assertIn('Pointer misses button', runner.authors[1])
        publish.assert_called_once()
        self.assertEqual(publish.call_args.args[1].name, 'attempt-02')

    def test_exhausted_repairs_stop_without_publication(self):
        self.brief()
        runner = FakeRunner(fail_reviews=99)
        with patch.object(g, 'publish_approved') as publish:
            self.assertEqual(self.run_pipeline(runner), 1)
            publish.assert_not_called()
        self.assertEqual(len(runner.authors), 3)
        state = json.loads((self.runs / '123' / '2026-11-14' / 'run.json').read_text())
        self.assertEqual(state['phase'], 'needs_attention')

    def test_failed_publication_reuses_approved_video_not_new_generation(self):
        self.brief()
        runner = FakeRunner()
        with patch.object(g, 'publish_approved', side_effect=g.p.PushError('network failure')):
            self.assertEqual(self.run_pipeline(runner), 1)
        with patch.object(g, 'publish_approved', return_value={'phase': 'published', 'media_id': 'm'}):
            factory = Mock(side_effect=AssertionError('must not generate again'))
            self.assertEqual(g.run_slot(CONFIG, OPTIONS, NOW, factory), 0)
        self.assertEqual(len(runner.authors), 1)

    def test_published_day_does_not_generate_or_publish_twice(self):
        self.brief()
        runner = FakeRunner()
        with patch.object(g, 'publish_approved', return_value={'phase': 'published'}) as publish:
            self.assertEqual(self.run_pipeline(runner), 0)
            self.assertEqual(self.run_pipeline(runner), 0)
            publish.assert_called_once()
        self.assertEqual(len(runner.authors), 1)

    def approval_fixture(self):
        project = self.root / 'project'
        project.mkdir()
        attempt = self.root / 'attempt-01'
        attempt.mkdir()
        runner = FakeRunner()
        runner.author(project, attempt, 'brief', '', [])
        runner.check(project, attempt)
        video, images, evidence = runner.render(project, attempt)
        review = valid_review(evidence)
        g.write_json(attempt / 'review.json', review)
        g.approve(project, attempt, video, 'brief', evidence, review)
        return project, attempt, video

    def test_approval_binds_exact_video(self):
        project, attempt, video = self.approval_fixture()
        video.write_bytes(b'different-video')
        with self.assertRaises(g.p.PushError):
            g.verify_approval(project, attempt, 'brief')

    def test_approval_binds_source_and_caption(self):
        project, attempt, _ = self.approval_fixture()
        (project / 'caption.txt').write_text('unreviewed claim')
        with self.assertRaises(g.p.PushError):
            g.verify_approval(project, attempt, 'brief')

    def test_approval_binds_reviewed_images(self):
        project, attempt, _ = self.approval_fixture()
        (attempt / 'sheet-001.jpg').write_bytes(b'changed evidence')
        with self.assertRaises(g.p.PushError):
            g.verify_approval(project, attempt, 'brief')

    def test_uncertain_review_and_missing_images_block(self):
        evidence = {'video_sha256': 'hash', 'images': ['one.jpg', 'two.jpg']}
        review = valid_review(evidence)
        review['uncertainties'] = ['item identity unknown']
        with self.assertRaises(g.p.PushError):
            g.validate_review(review, evidence)
        review = valid_review(evidence)
        review['reviewed_images'] = ['one.jpg']
        with self.assertRaises(g.p.PushError):
            g.validate_review(review, evidence)

    def test_passing_verdict_with_unverified_check_is_rejected(self):
        evidence = {'video_sha256': 'hash', 'images': ['one.jpg']}
        review = valid_review(evidence)
        review['checks']['item_matching'] = False
        with self.assertRaises(g.p.PushError):
            g.validate_review(review, evidence)

    def test_browser_skipped_or_unasserted_motion_blocks(self):
        check = valid_check()
        check['browserSkipped'] = True
        with self.assertRaises(g.p.PushError):
            g.validate_check(check)
        check = valid_check()
        check['motion']['samples'] = 0
        with self.assertRaises(g.p.PushError):
            g.validate_check(check)

    def test_check_parser_accepts_progress_but_no_forged_empty_report(self):
        check = valid_check()
        self.assertEqual(g.extract_report('progress\n' + json.dumps(check) + '\n'), check)
        with self.assertRaises(g.p.PushError):
            g.extract_report('{"ok":true}')

    def test_generator_environment_omits_instagram_secrets(self):
        with patch.dict(g.os.environ, {'META_ACCESS_TOKEN': 'secret', 'INSTAGRAM_ACCOUNT_ID': '123'}):
            env = g.clean_environment()
        self.assertNotIn('META_ACCESS_TOKEN', env)
        self.assertNotIn('INSTAGRAM_ACCOUNT_ID', env)

    def test_timed_out_command_retains_redacted_diagnostics(self):
        runner = g.Runner.__new__(g.Runner)
        runner.config = {'command_timeout_seconds': 1, 'node_executable': g.sys.executable}
        runner.deadline = g.time.monotonic() + 10
        log = self.root / 'timeout.log'
        program = 'import time; print("last progress secret-token", flush=True); time.sleep(30)'
        with patch.dict(g.os.environ, {'META_ACCESS_TOKEN': 'secret-token'}):
            with self.assertRaisesRegex(g.p.PushError, 'timed out.*timeout.log'):
                runner.command([g.sys.executable, '-c', program], self.root, log)
        self.assertIn('last progress [REDACTED]', log.read_text())
        self.assertNotIn('secret-token', log.read_text())

    def test_daily_task_has_generation_runtime_budget(self):
        tree = install_task.task_xml(self.root, Path('pythonw.exe'), 'sid', OPTIONS, NOW.date())
        ns = {'t': install_task.NS}
        self.assertEqual(tree.getroot().find('.//t:ExecutionTimeLimit', ns).text, 'PT105M')

    def test_generation_mode_does_not_fall_back_to_unreviewed_queue(self):
        with patch.object(g, 'run_slot', return_value=0) as generated, \
                patch.object(a, 'Queue', side_effect=AssertionError('queue bypass forbidden')):
            self.assertEqual(a.run_live(CONFIG, OPTIONS, NOW), 0)
            generated.assert_called_once_with(CONFIG, OPTIONS, NOW)

    def test_generation_test_never_calls_publisher_and_cannot_be_used_by_live_run(self):
        self.brief()
        runner = FakeRunner()
        with patch.object(g, 'publish_approved', side_effect=AssertionError('test must not publish')):
            self.assertEqual(g.run_slot(CONFIG, OPTIONS, NOW, lambda *args: runner, publish=False), 0)
        test_state = self.runs / 'test-123' / '2026-11-14' / 'run.json'
        self.assertEqual(json.loads(test_state.read_text())['phase'], 'reviewed')
        self.assertFalse((self.runs / '123' / '2026-11-14' / 'run.json').exists())

    def test_manual_test_recheck_never_authors_or_publishes(self):
        self.brief()
        self.assertEqual(g.run_slot(CONFIG, OPTIONS, NOW, lambda *args: FakeRunner(), publish=False), 0)
        runner = FakeRunner()
        with patch.object(g, 'publish_approved', side_effect=AssertionError('must not publish')):
            self.assertEqual(g.recheck_test(CONFIG, OPTIONS, '2026-11-14', lambda *args: runner), 0)
        self.assertEqual(runner.authors, [])
        state = json.loads((self.runs / 'test-123' / '2026-11-14' / 'run.json').read_text())
        self.assertEqual(state['phase'], 'reviewed')
        self.assertTrue(state['attempt'].startswith('recheck-'))

    def test_manual_test_recheck_retains_rejected_review_and_hold(self):
        self.brief()
        self.assertEqual(g.run_slot(CONFIG, OPTIONS, NOW, lambda *args: FakeRunner(), publish=False), 0)
        with self.assertRaises(g.p.PushError):
            g.recheck_test(CONFIG, OPTIONS, '2026-11-14', lambda *args: FakeRunner(fail_reviews=1))
        run_dir = self.runs / 'test-123' / '2026-11-14'
        state = json.loads((run_dir / 'run.json').read_text())
        self.assertEqual(state['phase'], 'needs_attention')
        self.assertTrue((run_dir / state['attempt'] / 'review.json').is_file())

    def test_timeline_duration_is_parsed_from_actual_root(self):
        index = self.root / 'index.html'
        index.write_text('<html><div data-composition-id="main" data-width="1080" '
                         'data-height="1920" data-duration="25"></div></html>')
        self.assertEqual(g.composition_duration(index), 25)

    def test_missing_motion_spec_or_contrast_checks_blocks(self):
        report = valid_check()
        report['motion']['specPath'] = None
        with self.assertRaises(g.p.PushError):
            g.validate_check(report)

    def test_crash_after_publication_is_reconciled_before_source_refresh(self):
        self.brief()
        with patch.object(g, 'publish_approved', return_value={'phase': 'published'}):
            self.assertEqual(self.run_pipeline(FakeRunner()), 0)
        run_dir = self.runs / '123' / '2026-11-14'
        state_path = run_dir / 'run.json'
        state = json.loads(state_path.read_text())
        state['phase'] = 'approved'
        g.write_json(state_path, state)
        approval = json.loads((run_dir / state['attempt'] / 'approval.json').read_text())
        job = a.publisher_job('123', approval['video_sha256'])
        store = g.p.State(self.root / '.state')
        store.save(job, {'phase': 'published', 'media_id': 'already-public'})
        store.db.close()
        with patch.object(g.project_source, 'configuration', side_effect=AssertionError('must not refresh')):
            self.assertEqual(self.run_pipeline(FakeRunner()), 0)
        self.assertEqual(json.loads(state_path.read_text())['media_id'], 'already-public')

    def test_interrupted_process_does_not_consume_a_repair_attempt(self):
        self.brief()
        run_dir = self.runs / '123' / '2026-11-14'
        (run_dir / 'attempt-01').mkdir(parents=True)
        g.write_json(run_dir / 'run.json', {'phase': 'generating', 'attempt_count': 1, 'attempt': 'attempt-01'})
        with patch.object(g, 'publish_approved', return_value={'phase': 'published'}):
            self.assertEqual(self.run_pipeline(FakeRunner()), 0)
        self.assertEqual(json.loads((run_dir / 'run.json').read_text())['attempt_count'], 1)
        report = valid_check()
        report['contrast']['checked'] = 0
        with self.assertRaises(g.p.PushError):
            g.validate_check(report)


if __name__ == '__main__':
    unittest.main()
