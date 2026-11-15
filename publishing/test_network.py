"""Offline coverage for transport diagnostics and safe read-only retries."""
import io
import ssl
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import network_check as n
import push_reel as p


class NetworkTests(unittest.TestCase):
    def client(self):
        return p.Meta({'META_ACCESS_TOKEN': 'private-token', 'META_API_VERSION': 'v27.0'})

    def test_permission_denied_is_specific_redacted_and_not_retried(self):
        api = self.client()
        failure = URLError(PermissionError(13, 'https://proxy/?access_token=private-token'))
        with patch.object(api.opener, 'open', side_effect=failure) as send, \
                patch.object(p.time, 'sleep') as sleep:
            with self.assertRaises(p.PushError) as caught:
                api.graph('123', {'fields': 'id'})
        self.assertIn('access_denied', str(caught.exception))
        self.assertIn('errno=13', str(caught.exception))
        self.assertNotIn('private-token', str(caught.exception))
        self.assertNotIn('https://', str(caught.exception))
        self.assertEqual(send.call_count, 1)
        sleep.assert_not_called()

    def test_temporary_get_timeout_is_retried_and_recovers(self):
        api = self.client()
        with patch.object(api.opener, 'open', side_effect=[URLError(TimeoutError()), io.StringIO('{"id":"123"}')]) as send, \
                patch.object(p.time, 'sleep') as sleep:
            self.assertEqual(api.graph('123')['id'], '123')
        self.assertEqual(send.call_count, 2)
        sleep.assert_called_once_with(1)

    def test_get_retries_are_bounded(self):
        api = self.client()
        with patch.object(api.opener, 'open', side_effect=URLError(TimeoutError())) as send, \
                patch.object(p.time, 'sleep') as sleep:
            with self.assertRaisesRegex(p.PushError, 'network timeout'):
                api.graph('123')
        self.assertEqual(send.call_count, 3)
        self.assertEqual([item.args[0] for item in sleep.call_args_list], [1, 3])

    def test_post_timeout_is_never_blindly_repeated(self):
        api = self.client()
        with patch.object(api.opener, 'open', side_effect=URLError(TimeoutError())) as send, \
                patch.object(p.time, 'sleep') as sleep:
            with self.assertRaises(p.PushError):
                api.graph('123/media_publish', {'creation_id': '456'}, post=True)
        self.assertEqual(send.call_count, 1)
        sleep.assert_not_called()

    def test_tls_failure_is_not_retried(self):
        api = self.client()
        with patch.object(api.opener, 'open', side_effect=URLError(ssl.SSLCertVerificationError('private details'))) as send:
            with self.assertRaisesRegex(p.PushError, 'network tls'):
                api.graph('123')
        self.assertEqual(send.call_count, 1)

    def test_http_rejection_is_not_a_transport_failure(self):
        api = self.client()
        failure = HTTPError('https://graph.facebook.com/', 401, 'Unauthorized', {}, io.BytesIO(b'{"error":{"code":190}}'))
        with patch.object(api.opener, 'open', side_effect=failure) as send:
            with self.assertRaisesRegex(p.PushError, 'HTTP 401'):
                api.graph('123')
        self.assertEqual(send.call_count, 1)

    def test_diagnostic_http_error_proves_reachability_without_credentials(self):
        failure = HTTPError('https://graph.facebook.com/', 400, 'Bad Request', {}, io.BytesIO(b''))
        with patch.object(n.socket, 'getaddrinfo'), patch.object(n.request, 'build_opener') as opener:
            opener.return_value.open.side_effect = failure
            result = n.probe('graph.facebook.com')
        self.assertTrue(result['reachable'])
        self.assertEqual(result['http_status'], 400)
        req = opener.return_value.open.call_args.args[0]
        self.assertFalse(req.has_header('Authorization'))
        self.assertIsNone(req.data)

    def test_diagnostic_identifies_os_denial(self):
        with patch.object(n.socket, 'getaddrinfo'), patch.object(n.request, 'build_opener') as opener:
            opener.return_value.open.side_effect = URLError(PermissionError(13, 'sensitive details'))
            result = n.probe('rupload.facebook.com')
        self.assertFalse(result['reachable'])
        self.assertEqual(result['failure']['category'], 'access_denied')
        self.assertNotIn('sensitive details', str(result))


if __name__ == '__main__':
    unittest.main()
