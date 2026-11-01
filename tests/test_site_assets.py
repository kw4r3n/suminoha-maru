"""Packaging regressions use tiny fixtures, never installed fonts."""
import json
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import zipfile
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_site_assets as assets


class LicenseIndex(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.texts = []
        self.in_pre = False

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.append(dict(attrs)['href'])
        if tag == 'pre':
            self.in_pre = True
            self.texts.append('')

    def handle_endtag(self, tag):
        if tag == 'pre':
            self.in_pre = False

    def handle_data(self, data):
        if self.in_pre:
            self.texts[-1] += data


class SiteAssetsTest(unittest.TestCase):
    def test_unicode_ranges_compact_and_disjoint_boundaries(self):
        self.assertEqual(assets.unicode_ranges({0x10000, 65, 67, 66, 90}), 'U+41-43,U+5A,U+10000')
        self.assertEqual(assets.unicode_ranges(set()), '')

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for key, folder, prefix, label, version in assets.PACKAGES:
            base = self.root / 'fonts' / folder
            base.mkdir(parents=True)
            original = ROOT / 'fonts' / folder
            rows = json.loads((original / 'manifest.json').read_text())
            # Include the rollback entry in the manifest to test exclusion.
            for row in rows:
                name = row['file']
                for extension, hash_key in (('.ttf', 'sha256'), ('.woff2', 'woff2_sha256')):
                    filename = Path(name).with_suffix(extension).name
                    data = filename.encode()
                    (base / filename).write_bytes(data)
                    row[hash_key] = assets.sha256(data)
                shutil.copytree(original / 'licenses' / Path(name).stem,
                                base / 'licenses' / Path(name).stem)
            (base / 'manifest.json').write_text(json.dumps(rows))

    def test_complete_reproducible_archives_and_rollback_excluded(self):
        output = self.root / 'site'
        first = assets.build(self.root, output)
        self.assertEqual(first, assets.build(self.root, output))
        for row in first:
            path = output / row['url']
            self.assertEqual(assets.sha256(path.read_bytes()), row['sha256'])
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                readme = archive.read(next(n for n in names if n.endswith('/README.txt'))).decode()
                self.assertNotIn('暫定', readme)
                self.assertIn(f'バージョン：{row["version"]}', readme)
                self.assertEqual(sum(n.endswith('.ttf') for n in names), 4)
                self.assertFalse(any(n.endswith('.woff2') for n in names))
                if row['id'] == 'code35':
                    self.assertFalse(any('Gothic' in n for n in names))
                sums = archive.read(next(n for n in names if n.endswith('/SHA256SUMS'))).decode()
                parent = names[0].split('/')[0]
                for line in sums.splitlines():
                    digest, name = line.split('  ', 1)
                    self.assertEqual(digest, assets.sha256(archive.read(f'{parent}/{name}')))

    def test_bad_hash_prevents_all_output(self):
        path = self.root / 'fonts/code12/SuminohaMaruCode12NF-Regular.ttf'
        path.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            assets.build(self.root, self.root / 'site')
        self.assertFalse((self.root / 'site').exists())

    def test_license_index_contains_exact_text_and_safe_original_links(self):
        extra = self.root / 'fonts/gothic/licenses/SuminohaMaruGothic-Regular/extra & <notice>.txt'
        extra.write_text('License <script>not executable</script> & attribution', encoding='utf-8')
        output = self.root / 'site'
        assets.build(self.root, output)
        index = (output / 'licenses/index.html').read_text()
        self.assertNotIn('<script>not executable</script>', index)
        self.assertIn('extra &amp; &lt;notice&gt;.txt', index)
        parser = LicenseIndex()
        parser.feed(index)
        originals = [link for link in parser.links if link.startswith('../fonts/')]
        expected = list((output / 'fonts').rglob('licenses/*/*'))
        self.assertEqual(len(originals), len(expected))
        self.assertEqual(len(originals), len(parser.texts))
        for link, text in zip(originals, parser.texts):
            path = output / 'licenses' / unquote(unescape(link))
            self.assertEqual(path.read_text(encoding='utf-8'), text)

    def test_missing_tracking_notice_prevents_all_output(self):
        path = self.root / 'fonts/gothic/licenses/SuminohaMaruGothic-Regular/Tracking-NOTICE.txt'
        path.unlink()
        with self.assertRaises(AssertionError):
            assets.build(self.root, self.root / 'site')
        self.assertFalse((self.root / 'site').exists())


if __name__ == '__main__':
    unittest.main()
