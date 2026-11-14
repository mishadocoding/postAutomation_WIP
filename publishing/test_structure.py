import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import generation as g
import project_source as s
import structure_check as c


class StructureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        (self.root / 'compositions').mkdir()
        (self.root / 'index.html').write_text('<html><body><div id="root" data-composition-id="main">'
            '<div id="result" data-composition-src="compositions/result.html"></div></div></body></html>')

    def scene(self, body):
        (self.root / 'compositions' / 'result.html').write_text(body)

    def test_reproduces_the_real_premature_scene_root_close(self):
        self.scene('<template><div id="root"><p id="result-title">Title</p></div>'
                   '<div id="result-panel">Panel</div></div>'
                   '<script>tl.to("#result-panel",{opacity:1});</script></template>')
        result = c.validate(self.root)
        self.assertFalse(result['ok'])
        messages = [item['message'] for item in result['findings']]
        self.assertTrue(any('outside the scene root' in message for message in messages))
        self.assertTrue(any('Animation target #result-panel' in message for message in messages))

    def test_correct_root_structure_and_animation_targets_pass(self):
        self.scene('<template><style>#root{inset:0}</style><div id="root">'
                   '<div id="result-panel"><img id="photo" src="assets/p.png"></div></div>'
                   '<script>tl.to("#result-panel",{opacity:1});</script></template>')
        self.assertTrue(c.validate(self.root)['ok'])

    def test_missing_mounted_scene_is_rejected(self):
        self.assertFalse(c.validate(self.root)['ok'])

    def test_duplicate_ids_are_rejected(self):
        self.scene('<template><div id="root"><div id="same"></div><div id="same"></div></div></template>')
        self.assertTrue(any('Duplicate element id' in item['message'] for item in c.validate(self.root)['findings']))

    def test_unchanged_source_snapshot_is_reused_in_repairs(self):
        source = self.root / 'source'
        source.mkdir()
        (source / 'index.html').write_text('original app')
        project = self.root / 'project'
        project.mkdir()
        manifest = self.root / 'manifest.json'
        product = {'project_path': str(source)}
        first = g.stable_source_snapshot(product, project, manifest)
        with patch.object(s, 'capture', side_effect=AssertionError('unchanged source must not be recaptured')):
            second = g.stable_source_snapshot(product, project, manifest)
        self.assertEqual(first, second)
        (source / 'index.html').write_text('updated app')
        third = g.stable_source_snapshot(product, project, manifest)
        self.assertNotEqual(first['fingerprint'], third['fingerprint'])

    def test_repair_feedback_deduplicates_and_uses_real_browser_crops(self):
        attempt = self.root / 'attempt'
        attempt.mkdir()
        image = attempt / 'crop.png'
        image.write_bytes(b'fixture')
        finding = {'severity': 'error', 'code': 'missing', 'selector': '#panel', 'message': 'Missing panel'}
        crop = {'severity': 'P2', 'time_seconds': 5.5, 'problem': 'Cropped UI text',
                'fix': 'Reposition the screenshot'}
        g.write_json(attempt / 'check.json', {'layout': {'findings': [finding, finding, crop]},
                     'snapshots': {'findingFiles': [str(image)], 'files': []}})
        feedback, images = g.repair_feedback(attempt, self.root, g.p.PushError('failed'))
        self.assertEqual(feedback.count('Missing panel'), 1)
        self.assertIn('Cropped UI text', feedback)
        self.assertEqual(images, [image.resolve()])


if __name__ == '__main__':
    unittest.main()
