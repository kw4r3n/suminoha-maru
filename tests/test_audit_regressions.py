"""Regression checks use fake installed fonts and never change the user's environment."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import check_repository_layout as layout
import install_prose_tracking_local as installer


class AuditRegressions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'home'
        self.fonts = self.home / '.local/share/fonts'
        self.out = self.root / 'fonts/gothic'
        self.out.mkdir(parents=True)
        (self.root / 'reports').mkdir()
        (self.home / '.config/fontconfig').mkdir(parents=True)
        (self.home / '.config/kdeglobals').write_text('unchanged')
        for package in ['code35', 'code12']:
            folder = self.root / 'fonts' / package
            folder.mkdir()
            (folder / 'manifest.json').write_text('[]')
        self.rows = []
        for i, row in enumerate(json.loads((ROOT / 'fonts/gothic/manifest.json').read_text())):
            old, new = f'old-{i}'.encode(), f'new-{i}'.encode()
            row = {**row, 'source_sha256': hashlib.sha256(old).hexdigest(),
                   'sha256': hashlib.sha256(new).hexdigest()}
            dest = self.fonts / row['postscript'].removesuffix('-Regular') / row['file']
            dest.parent.mkdir(parents=True)
            dest.write_bytes(old)
            (self.out / row['file']).write_bytes(new)
            shutil.copytree(ROOT / 'fonts/gothic/licenses' / row['postscript'],
                            self.out / 'licenses' / row['postscript'])
            self.rows.append(row)
        (self.out / 'manifest.json').write_text(json.dumps(self.rows))
        for name in ['validation.json', 'reproducibility.json']:
            (self.out / name).write_text('{}')
        self.addCleanup(patch.stopall)
        for name, value in [('ROOT', self.root), ('OUT', self.out),
                            ('HOME', self.home), ('FONT', self.fonts)]:
            patch.object(installer, name, value).start()
        self.scan = patch.object(installer.subprocess, 'check_output', return_value='fixture scan').start()
        self.cache = patch.object(installer.subprocess, 'run').start()

    def assert_unchanged(self):
        for i, row in enumerate(self.rows):
            path = self.fonts / row['postscript'].removesuffix('-Regular') / row['file']
            self.assertEqual(path.read_bytes(), f'old-{i}'.encode())
        self.assertFalse(list(self.fonts.rglob('.tracking-008-*')))
        self.assertFalse((self.root / 'reports/prose-tracking-installation.json').exists())
        self.cache.assert_not_called()

    def test_missing_license_stops_before_replacement(self):
        (self.out / 'licenses' / self.rows[-1]['postscript'] / 'Tracking-NOTICE.txt').unlink()
        with self.assertRaises(AssertionError):
            installer.install()
        self.assert_unchanged()
        self.scan.assert_not_called()

    def test_license_copy_failure_cleans_staged_fonts(self):
        original = shutil.copytree
        def copy(src, dest, **kwargs):
            if Path(src).name == self.rows[-1]['postscript']:
                raise OSError('injected license copy failure')
            return original(src, dest, **kwargs)
        with patch.object(installer.shutil, 'copytree', side_effect=copy):
            with self.assertRaisesRegex(OSError, 'license copy failure'):
                installer.install()
        self.assert_unchanged()

    def test_scan_failure_stops_before_replacement(self):
        self.scan.side_effect = OSError('injected scan failure')
        with self.assertRaisesRegex(OSError, 'scan failure'):
            installer.install()
        self.assert_unchanged()

    def test_success_replaces_all_four_and_writes_receipt(self):
        with contextlib.redirect_stdout(io.StringIO()):
            installer.install()
        for i, row in enumerate(self.rows):
            path = self.fonts / row['postscript'].removesuffix('-Regular') / row['file']
            self.assertEqual(path.read_bytes(), f'new-{i}'.encode())
            layout.check_licenses(path.parent / 'licenses', row['family'], tracking=True)
        receipt = json.loads((self.root / 'reports/prose-tracking-installation.json').read_text())
        self.assertEqual(len(receipt['installed']), 4)
        self.assertFalse(list(self.fonts.rglob('.tracking-008-*')))
        self.cache.assert_called_once()

    def test_empty_and_incomplete_license_directories_fail(self):
        row = self.rows[0]
        folder = self.out / 'licenses' / row['postscript']
        shutil.rmtree(folder)
        folder.mkdir()
        with self.assertRaises(AssertionError):
            layout.check_licenses(folder, row['family'], tracking=True)
        for name in ['Prose-OFL.txt', 'Prose-NOTICES.txt', 'Tracking-NOTICE.txt']:
            (folder / name).write_text('fixture')
        layout.check_licenses(folder, row['family'], tracking=True)
        (folder / 'Prose-OFL.txt').write_bytes(b'')
        with self.assertRaises(AssertionError):
            layout.check_licenses(folder, row['family'], tracking=True)

    def test_retained_repository_integrity_and_preservation_paths(self):
        with contextlib.redirect_stdout(io.StringIO()):
            layout.check()
        files = list((ROOT / 'inputs/preservation').glob('*.json'))
        self.assertEqual(len(files), 5)
        for path in files:
            self.assertTrue(json.loads(path.read_text()))

    def test_build_baselines_reject_changed_files_and_external_paths(self):
        fixtures = self.root / 'inputs/build-baselines'
        fixtures.mkdir(parents=True)
        for name in ['grid-small', 'code-small']:
            folder = self.root / 'inputs' / name
            folder.mkdir()
            (folder / 'font.ttf').write_bytes(b'pinned font')
            fixture = {'repeat': {'font.ttf': hashlib.sha256(b'pinned font').hexdigest()}}
            (fixtures / (name + '.json')).write_text(json.dumps(fixture))
        layout.check_build_baselines(self.root)
        (self.root / 'inputs/grid-small/font.ttf').write_bytes(b'changed')
        with self.assertRaises(AssertionError):
            layout.check_build_baselines(self.root)
        (fixtures / 'grid-small.json').write_text(json.dumps({'repeat': {'../outside.ttf': 'unused'}}))
        with self.assertRaises(AssertionError):
            layout.check_build_baselines(self.root)

    def test_missing_intermediate_requires_its_exact_recipe_pin(self):
        (self.root / 'inputs').mkdir(exist_ok=True)
        name = 'inputs/generated/font.ttf'
        digest = hashlib.sha256(b'generated font').hexdigest()
        (self.root / 'inputs/build-recipe.json').write_text(json.dumps({'intermediates': {name: digest}}))
        layout.check_pin(self.root, name, digest)
        with self.assertRaises(AssertionError):
            layout.check_pin(self.root, name, 'changed')
        with self.assertRaises(AssertionError):
            layout.check_pin(self.root, 'inputs/unknown/font.ttf', digest)
        with self.assertRaises(AssertionError):
            layout.check_pin(self.root, '../outside.ttf', digest)


if __name__ == '__main__':
    unittest.main()
