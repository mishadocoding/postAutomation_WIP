"""Offline contract tests: no credentials, uploads or real posts."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import io
import json
import sqlite3
from urllib.error import HTTPError

import push_reel as p


class FakeMeta:
    def __init__(self, publish_error=False, status='FINISHED', link_error=False):
        self.calls = []
        self.publish_error = publish_error
        self.status = status
        self.link_error = link_error

    def graph(self, path, params=None, post=False):
        self.calls.append((path, params, post))
        if path == '123/media':
            return {'id': 'container', 'uri': 'https://rupload.facebook.com/upload'}
        if path == 'container':
            return {'status_code': self.status}
        if path == '123/media_publish':
            if self.publish_error:
                raise p.PushError('simulated lost response')
            return {'id': 'media'}
        if path == 'media':
            if self.link_error:
                raise p.PushError('link lookup failed')
            return {'permalink': 'https://www.instagram.com/reel/test/'}
        raise AssertionError(path)

    def upload(self, uri, video):
        self.calls.append(('upload', uri, False))
        return {'success': True}


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.store = p.State(self.folder)

    def tearDown(self):
        self.store.db.close()
        self.tmp.cleanup()

    def push(self, api):
        return p.push(api, self.store, 'job', Path('test.mp4'), 'caption', '123', True, 1)

    def test_success_and_repeat_does_not_publish_twice(self):
        api = FakeMeta()
        self.assertEqual(self.push(api)['phase'], 'published')
        count = len(api.calls)
        self.push(api)
        self.assertEqual(len(api.calls), count)
        self.assertEqual(api.calls[-2][0], '123/media_publish')

    def test_uncertain_publish_never_repeats_post(self):
        with self.assertRaises(p.PushError):
            self.push(FakeMeta(publish_error=True))
        self.assertEqual(self.store.get('job')['phase'], 'publishing')
        retry = FakeMeta()
        with self.assertRaises(p.PushError):
            self.push(retry)
        self.assertEqual([call[0] for call in retry.calls], ['container'])

    def test_uncertain_publish_can_be_confirmed_by_container(self):
        self.store.save('job', {'phase': 'publishing', 'container_id': 'container'})
        self.assertEqual(self.push(FakeMeta(status='PUBLISHED'))['phase'], 'published')

    def test_processing_resumes_existing_container(self):
        self.store.save('job', {'phase': 'processing', 'container_id': 'container'})
        api = FakeMeta()
        self.push(api)
        self.assertFalse(any(call[0] in ('123/media', 'upload') for call in api.calls))

    def test_meta_rejection_does_not_publish(self):
        api = FakeMeta(status='ERROR')
        with self.assertRaises(p.PushError):
            self.push(api)
        self.assertFalse(any(call[0] == '123/media_publish' for call in api.calls))

    def test_lost_permalink_keeps_published_state(self):
        self.assertEqual(self.push(FakeMeta(link_error=True))['phase'], 'published')
        self.assertEqual(self.store.get('job')['media_id'], 'media')

    def test_interrupted_upload_is_not_replayed(self):
        self.store.save('job', {'phase': 'uploading', 'container_id': 'container'})
        api = FakeMeta()
        with self.assertRaises(p.PushError):
            self.push(api)
        self.assertEqual(api.calls, [])

    def test_timezone_required(self):
        with self.assertRaises(p.PushError):
            p.parse_at('2026-11-14T12:00:00')
        self.assertEqual(p.parse_at('2026-11-14T12:00:00+05:00').hour, 7)

    def test_upload_refuses_untrusted_hosts(self):
        api = p.Meta({'META_ACCESS_TOKEN': 'secret', 'META_API_VERSION': 'v99.0'})
        with self.assertRaises(p.PushError):
            api.upload('https://example.com/upload', Path('test.mp4'))

    def test_dry_run_never_creates_api_client(self):
        video = self.folder / 'test.mp4'
        video.write_bytes(b'fake bytes')
        caption = self.folder / 'caption.txt'
        caption.write_text('caption')
        with patch.object(p, 'inspect_video', return_value={'duration_seconds': 25}), \
                patch.object(p, 'Meta', side_effect=AssertionError('network forbidden')):
            self.assertEqual(p.main(['--video', str(video), '--caption-file', str(caption)]), 0)

    def test_wait_timeout_retains_processing_state(self):
        api = FakeMeta(status='IN_PROGRESS')
        with patch.object(p.time, 'monotonic', side_effect=[0, 2]):
            with self.assertRaises(p.PushError):
                self.push(api)
        self.assertEqual(self.store.get('job')['phase'], 'processing')

    def test_account_check_only_makes_read_requests(self):
        with patch.object(p, 'load_env'), \
                patch.object(p, 'configuration', return_value={'INSTAGRAM_ACCOUNT_ID': '123'}), \
                patch.object(p, 'Meta') as client, \
                patch.object(p, 'State', side_effect=AssertionError('no posting state')):
            client.return_value.graph.side_effect = [
                {'id': '123', 'username': 'test'},
                {'data': [{'quota_usage': 0, 'config': {'quota_total': 100}}]},
            ]
            self.assertEqual(p.main(['--check-account']), 0)
            self.assertEqual(client.return_value.graph.call_count, 2)
            for call in client.return_value.graph.call_args_list:
                self.assertFalse(call.kwargs.get('post', False))
            client.return_value.upload.assert_not_called()

    def test_account_check_cannot_be_combined_with_publish(self):
        with patch.object(p, 'Meta') as client:
            with self.assertRaises(p.PushError):
                p.main(['--check-account', '--publish'])
            client.assert_not_called()

    def test_upload_error_reports_debug_info_and_redacts_token(self):
        secret = 'secret-example-token'
        api = p.Meta({'META_ACCESS_TOKEN': secret, 'META_API_VERSION': 'v27.0'})
        payload = {'debug_info': {'type': 'ProcessingFailedError', 'retriable': False,
                   'message': 'unauthorized user request token=' + secret}}
        failure = HTTPError('https://rupload.facebook.com/upload', 400, 'Bad Request', {},
                            io.BytesIO(json.dumps(payload).encode()))
        with patch.object(api.opener, 'open', side_effect=failure):
            with self.assertRaises(p.PushError) as result:
                api.send(p.request.Request('https://rupload.facebook.com/upload'))
        self.assertIn('ProcessingFailedError', str(result.exception))
        self.assertIn('unauthorized user request', str(result.exception))
        self.assertNotIn(secret, str(result.exception))

    def test_graph_error_preserves_code_and_redacts_signed_url(self):
        detail = p.meta_error_details({'error': {'code': 190, 'error_subcode': 463,
            'message': 'Expired https://example.com/?access_token=secret', 'access_token': 'secret'}})
        self.assertEqual(detail['error_subcode'], 463)
        self.assertNotIn('access_token', detail)
        text = p.safe_diagnostic(json.dumps(detail), 'secret')
        self.assertNotIn('https://example.com', text)
        self.assertNotIn('secret', text)

    def test_inspect_job_only_reads_and_leaves_state_unchanged(self):
        job = 'a' * 64
        self.store.save(job, {'phase': 'uploading', 'account_id': '123', 'container_id': 'container'})
        original = self.store.get(job)
        # Match the production folder structure without touching real saved jobs.
        root = self.folder / 'publisher'
        (root / '.state').mkdir(parents=True)
        copied = sqlite3.connect(root / '.state' / 'posts.sqlite3')
        self.store.db.backup(copied)
        copied.close()
        with patch.object(p, 'ROOT', root), patch.object(p, 'load_env'), \
                patch.object(p, 'configuration', return_value={'INSTAGRAM_ACCOUNT_ID': '123'}), \
                patch.object(p, 'Meta') as client, \
                patch.object(p, 'State', side_effect=AssertionError('read-only required')):
            client.return_value.token = 'test-secret'
            client.return_value.graph.return_value = {'status_code': 'IN_PROGRESS'}
            self.assertEqual(p.main(['--inspect-job', job]), 0)
            client.return_value.upload.assert_not_called()
            client.return_value.graph.assert_called_once_with(
                'container', {'fields': 'status_code,status,video_status'})
        with p.closing(sqlite3.connect(root / '.state' / 'posts.sqlite3')) as db:
            raw = db.execute('SELECT payload FROM posts WHERE job=?', (job,)).fetchone()[0]
        self.assertEqual(json.loads(raw), original)

    def test_inspect_job_refuses_publish_flag(self):
        with patch.object(p, 'Meta') as client:
            with self.assertRaises(p.PushError):
                p.main(['--inspect-job', 'a' * 64, '--publish'])
            client.assert_not_called()

    def recovery_fixture(self, transferred=0, remote_status='IN_PROGRESS'):
        video = self.folder / 'recovery.mp4'
        video.write_bytes(b'original video bytes')
        config = {'INSTAGRAM_ACCOUNT_ID': '123', 'META_API_VERSION': 'v27.0'}
        job = p.hashlib.sha256(f'123:{p.file_digest(video)}'.encode()).hexdigest()
        self.store.save(job, {'phase': 'uploading', 'container_id': '456',
                             'account_id': '123', 'video': str(video)})
        api = Mock()
        api.token = 'secret-token'
        api.graph.return_value = {'status_code': remote_status, 'video_status': {
            'uploading_phase': {'status': 'error', 'bytes_transferred': transferred,
                                'source_file_size': 0}}}
        api.upload.return_value = {'success': True}
        return video, config, job, api

    def test_zero_byte_retry_uses_existing_container_and_never_publishes(self):
        video, config, job, api = self.recovery_fixture()
        with patch.object(p, 'inspect_video'):
            result = p.retry_upload(api, self.store, job, config)
        self.assertEqual(result['phase'], 'processing')
        api.upload.assert_called_once_with(
            'https://rupload.facebook.com/ig-api-upload/v27.0/456', video)
        api.graph.assert_called_once_with('456', {'fields': 'status_code,status,video_status'})
        self.assertEqual(self.store.get(job)['container_id'], '456')

    def test_partial_upload_cannot_be_retried_at_zero(self):
        _, config, job, api = self.recovery_fixture(transferred=5)
        before = self.store.get(job)
        with patch.object(p, 'inspect_video'), self.assertRaises(p.PushError):
            p.retry_upload(api, self.store, job, config)
        api.upload.assert_not_called()
        self.assertEqual(self.store.get(job), before)

    def test_already_processed_upload_is_not_repeated(self):
        _, config, job, api = self.recovery_fixture(remote_status='FINISHED')
        with patch.object(p, 'inspect_video'):
            self.assertEqual(p.retry_upload(api, self.store, job, config)['phase'], 'processing')
        api.upload.assert_not_called()

    def test_retry_refuses_changed_local_video(self):
        video, config, job, api = self.recovery_fixture()
        video.write_bytes(b'changed file')
        with patch.object(p, 'inspect_video'), self.assertRaises(p.PushError):
            p.retry_upload(api, self.store, job, config)
        api.graph.assert_not_called()
        api.upload.assert_not_called()

    def test_retry_failure_keeps_container_and_saves_redacted_error(self):
        _, config, job, api = self.recovery_fixture()
        api.upload.side_effect = p.PushError('rejected secret-token')
        with patch.object(p, 'inspect_video'), self.assertRaises(p.PushError):
            p.retry_upload(api, self.store, job, config)
        state = self.store.get(job)
        self.assertEqual(state['phase'], 'uploading')
        self.assertEqual(state['container_id'], '456')
        self.assertNotIn('secret-token', state['last_upload_error'])

    def test_retry_and_publish_flags_cannot_be_combined(self):
        with patch.object(p, 'Meta') as client:
            with self.assertRaises(p.PushError):
                p.main(['--retry-upload', 'a' * 64, '--publish'])
            client.assert_not_called()

    def test_expired_container_is_not_retried(self):
        _, config, job, api = self.recovery_fixture(remote_status='EXPIRED')
        with patch.object(p, 'inspect_video'), self.assertRaises(p.PushError):
            p.retry_upload(api, self.store, job, config)
        api.upload.assert_not_called()

    def test_preparation_upload_does_not_publish(self):
        api = FakeMeta()
        state = p.push(api, self.store, 'job', Path('test.mp4'), 'caption', '123', True, 1,
                       prepare_only=True)
        self.assertEqual(state['phase'], 'processing')
        self.assertFalse(any(call[0] == '123/media_publish' for call in api.calls))

    def test_source_freshness_guard_runs_before_publish(self):
        api = FakeMeta()
        def changed():
            raise p.PushError('Product was updated during upload')
        with self.assertRaises(p.PushError):
            p.push(api, self.store, 'job', Path('test.mp4'), 'caption', '123', True, 1,
                   before_publish=changed)
        self.assertEqual(self.store.get('job')['phase'], 'processing')
        self.assertFalse(any(call[0] == '123/media_publish' for call in api.calls))


if __name__ == '__main__':
    unittest.main()
