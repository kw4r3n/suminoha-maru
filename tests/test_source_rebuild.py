"""Build isolation, pin validation, and failed replacement must preserve current fonts."""
import hashlib
import json
import os
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import rebuild_fonts as rebuild


class SourceRebuildTests(unittest.TestCase):
    def test_public_notices_preserve_copyrights_and_original_licenses(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            license_text = (b'Copyright 2020 Original Authors\n\nOriginal license terms.\n'
                            b'Copyright Holder. This is license prose, not attribution.\n')
            (folder / 'Base-OFL.txt').write_bytes(license_text)
            notice = folder / 'Base-NOTICES.txt'
            notice.write_text('Preview of installed prototype.\nCopyright 2021 Other Authors\n'
                              ' Copyright (C) 2022 Additional Authors\nCopyright Undated Authors\n')
            rebuild.normalize_notices(folder)
            text = notice.read_text()
            self.assertIn('Copyright 2020 Original Authors', text)
            self.assertIn('Copyright 2021 Other Authors', text)
            self.assertIn(' Copyright (C) 2022 Additional Authors', text)
            self.assertIn('Copyright Undated Authors', text)
            self.assertNotIn('installed', text)
            self.assertNotIn('Copyright Holder.', text)
            self.assertEqual((folder / 'Base-OFL.txt').read_bytes(), license_text)
            rebuild.normalize_notices(folder)
            self.assertEqual(notice.read_text(), text)

    def test_public_notice_without_attribution_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / 'Prose-NOTICES.txt').write_text('Prototype only')
            with self.assertRaisesRegex(ValueError, 'Missing copyright'):
                rebuild.normalize_notices(folder)

    def test_real_ofl_prose_is_not_copied_as_attribution(self):
        root = Path(__file__).resolve().parents[1]
        original = root / 'fonts/code35/licenses/SuminohaMaruCode35NF-Regular/Base-OFL.txt'
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / 'Base-OFL.txt').write_bytes(original.read_bytes())
            notice = folder / 'Base-NOTICES.txt'
            notice.write_text('Preview of installed prototype.\n')
            rebuild.normalize_notices(folder)
            self.assertIn('Copyright 2022 The Maple Mono Project Authors', notice.read_text())
            self.assertNotIn('COPYRIGHT HOLDER', notice.read_text())
            self.assertNotIn('copyright statement(s)', notice.read_text())

    def test_workspace_never_copies_generated_fonts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'repo'
            work = Path(temporary) / 'work'
            for name in ['scripts', 'inputs', 'sources']:
                (root / name).mkdir(parents=True)
            (root / 'sources.lock.json').write_text('{}')
            (root / 'inputs/font.ttf').write_bytes(b'intermediate')
            (root / 'inputs/font.WOFF2').write_bytes(b'intermediate')
            (root / 'inputs/recipe.json').write_text('{}')
            (root / 'sources/upstream.ttf').write_bytes(b'upstream')
            work.mkdir()
            rebuild.prepare_workspace(root, work)
            self.assertFalse((work / 'inputs/font.ttf').exists())
            self.assertFalse((work / 'inputs/font.WOFF2').exists())
            self.assertTrue((work / 'inputs/recipe.json').is_file())
            self.assertEqual((work / 'sources/upstream.ttf').read_bytes(), b'upstream')
            self.assertFalse((work / 'fonts').exists())

    def test_corrupt_build_and_external_recipe_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            (work / 'current.ttf').write_bytes(b'changed')
            recipe = {'intermediates': {}, 'outputs': {'current.ttf': hashlib.sha256(b'expected').hexdigest()}}
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                rebuild.verify_workspace(work, recipe)
            recipe['outputs'] = {'../outside.ttf': 'unused'}
            with self.assertRaisesRegex(ValueError, 'Invalid recipe path'):
                rebuild.verify_workspace(work, recipe)

    def test_failed_exchange_preserves_previous_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / 'fonts'
            (output / 'code35').mkdir(parents=True)
            (output / 'code35/current.ttf').write_bytes(b'original')
            staged = root / 'staging' / 'fonts'
            staged.mkdir(parents=True)
            with patch.object(rebuild, 'exchange_directories', side_effect=OSError('replacement failed')):
                with self.assertRaisesRegex(OSError, 'replacement failed'):
                    rebuild.publish_tree(staged, output)
            self.assertEqual((output / 'code35/current.ttf').read_bytes(), b'original')

    def test_publish_exchanges_complete_directories(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old = root / 'fonts'
            new = root / 'staged'
            for folder, value in [(old, b'original'), (new, b'rebuilt')]:
                (folder / 'code35').mkdir(parents=True)
                (folder / 'code35/current.ttf').write_bytes(value)
            rebuild.publish_tree(new, old)
            self.assertEqual((old / 'code35/current.ttf').read_bytes(), b'rebuilt')
            self.assertEqual((new / 'code35/current.ttf').read_bytes(), b'original')

    def test_current_companion_config_selects_each_family_and_han_part(self):
        from fontTools.ttLib import TTFont
        from make_suminoha_companion_config import make
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            config = work / 'companions.conf'
            make(config)
            self.assertEqual(config.read_bytes(), (root / 'fonts/code12/68-suminoha-companions.conf').read_bytes())
            main = work / 'fonts.conf'
            main.write_text(f'<fontconfig><dir>{root / "fonts"}</dir><cachedir>{work / "cache"}</cachedir><include>{config}</include></fontconfig>')
            env = os.environ | {'FONTCONFIG_FILE': str(main)}
            for package in rebuild.PACKAGES:
                folder = root / 'fonts' / package
                rows = json.loads((folder / 'manifest.json').read_text())
                for row in rows:
                    with TTFont(folder / row['file']) as font:
                        cp = min(set(font.getBestCmap()) - {32, 160, 0x3000})
                    for name in [rows[0]['family'], rows[0]['japanese_family']]:
                        path = Path(subprocess.check_output(['fc-match', f'{name}:charset={cp:x}', '-f', '%{file}'], env=env, text=True))
                        self.assertEqual(rebuild.sha(path), row['sha256'], (name, hex(cp)))

    def test_failed_stage_cleans_workspace_and_keeps_current_fonts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / 'fonts'
            (output / 'code35').mkdir(parents=True)
            (output / 'code35/current.ttf').write_bytes(b'original')
            (root / 'inputs').mkdir()
            (root / 'inputs/build-recipe.json').write_text(json.dumps({'intermediates': {}, 'outputs': {}}))
            workspaces = []
            with patch('check_repository_layout.check_source_pins'), \
                 patch('build_prose_kana.library'), \
                 patch.object(rebuild, 'prepare_workspace', side_effect=lambda _, work: workspaces.append(work)), \
                 patch.object(rebuild, 'run_stages', side_effect=RuntimeError('stage failed')):
                with self.assertRaisesRegex(RuntimeError, 'stage failed'):
                    rebuild.rebuild(root, output)
            self.assertTrue(workspaces)
            self.assertTrue(all(not work.exists() for work in workspaces))
            self.assertEqual((output / 'code35/current.ttf').read_bytes(), b'original')


if __name__ == '__main__':
    unittest.main()
