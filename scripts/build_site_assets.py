"""Package current, hash-verified fonts for the public static website."""
import argparse
import hashlib
from html import escape
import io
import json
from pathlib import Path
import sys
import tempfile
import zipfile
from urllib.parse import quote

from fontTools.ttLib import TTFont

from check_repository_layout import check_licenses

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = (
    ('prose', 'gothic', 'SuminohaMaruGothic', '本文', 'v1'),
    ('code12', 'code12', 'SuminohaMaruCode12NF', 'Code12', 'v1'),
    ('code35', 'code35', 'SuminohaMaruCode35NF', 'Code35', 'v1'),
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def package_files(root, folder, prefix, tracking):
    """Validate every source before creating output; exclude rollback prose."""
    base = root / 'fonts' / folder
    rows = json.loads((base / 'manifest.json').read_text())
    selected = [row for row in rows if row['file'].startswith(prefix)]
    expected = {f'{prefix}{part}-Regular.ttf' for part in ('', 'HanJP', 'HanRareA', 'HanRareB')}
    if {row['file'] for row in selected} != expected:
        raise ValueError(f'Incomplete package: {prefix}')
    files = {}
    for row in selected:
        ttf = row['file']
        license_dir = base / 'licenses' / Path(ttf).stem
        check_licenses(license_dir, row['family'], tracking=tracking)
        for name, key in ((ttf, 'sha256'), (ttf.replace('.ttf', '.woff2'), 'woff2_sha256')):
            data = (base / name).read_bytes()
            if sha256(data) != row[key]:
                raise ValueError(f'Font hash mismatch: {base / name}')
            files[name] = data
        for path in sorted(license_dir.iterdir()):
            if path.is_file():
                files[f'licenses/{Path(ttf).stem}/{path.name}'] = path.read_bytes()
    return files


def write_atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(data)
            stream.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def unicode_ranges(points):
    """Compact disjoint cmap coverage for lazy browser loading."""
    ranges = []
    for point in sorted(points):
        if ranges and ranges[-1][1] + 1 == point:
            ranges[-1][1] = point
        else:
            ranges.append([point, point])
    return ','.join(f'U+{a:X}' if a == b else f'U+{a:X}-{b:X}' for a, b in ranges)


def build_font_styles(root, output):
    rules = []
    for key, folder, prefix, label, version in PACKAGES:
        covered = set()
        for part in ('', 'HanJP', 'HanRareA', 'HanRareB'):
            filename = f'{prefix}{part}-Regular'
            with TTFont(root / 'fonts' / folder / f'{filename}.ttf', lazy=True) as font:
                points = set(font.getBestCmap()) - covered
            covered.update(points)
            rules.append(f'''@font-face {{
  font-family: "Suminoha {key}";
  src: url("{key}/{filename}.woff2") format("woff2");
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  unicode-range: {unicode_ranges(points)};
}}''')
    write_atomic(output / 'fonts' / 'fonts.css', ('\n\n'.join(rules) + '\n').encode())


def build(root, output):
    if sys.flags.optimize:
        raise RuntimeError('Run without -O: license checks require assertions.')
    packages = [(p, package_files(root, p[1], p[2], p[0] == 'prose')) for p in PACKAGES]
    catalog = []
    license_sections = []
    for (key, folder, prefix, label, version), files in packages:
        file_version = version.replace('.', '_')
        archive_name = f'{prefix}-{file_version}-TTF.zip'
        readme = f'''{label} / {prefix}
バージョン：{version}

Regular・横組み用。
primaryと同じ用途のHan JP / RareA / RareBを組み合わせて使用してください。
直接ファイルを読み込む場合は primary → Han JP → Han RareA → Han RareB の順です。
各フォントのライセンス・帰属表示は licenses/ に同梱しています。
本文用フォントは字間をフォント内で調整済みです。追加の字間は0を基準にしてください。
Code12の欧文：漢字は1：2、Code35は3：5です。
Code35は一般的な1：2端末用フォントではありません。
NFは限定されたアイコン集合で、完全なNerd Fontsではありません。
IVS・地域別漢字・縦組み・全Unicode・すべての端末での動作は保証しません。
補助漢字には、主書体と字形・濃さが異なる字が含まれます。
'''
        buffer = io.BytesIO()
        archive_files = {name: data for name, data in files.items() if not name.endswith('.woff2')}
        archive_files['README.txt'] = readme.encode('utf-8')
        archive_files['SHA256SUMS'] = ''.join(f'{sha256(data)}  {name}\n' for name, data in sorted(archive_files.items())).encode()
        with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, data in sorted(archive_files.items()):
                info = zipfile.ZipInfo(f'{prefix}-{file_version}/{name}', date_time=(2026, 10, 31, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, data)
        zipped = buffer.getvalue()
        write_atomic(output / 'downloads' / archive_name, zipped)
        for name, data in files.items():
            if name.endswith('.woff2') or name.startswith('licenses/'):
                write_atomic(output / 'fonts' / key / name, data)
        faces = []
        for suffix, face_label in (('', '主書体'), ('HanJP', '補助漢字 JP'), ('HanRareA', '補助漢字 RareA'), ('HanRareB', '補助漢字 RareB')):
            directory = f'licenses/{prefix}{suffix}-Regular/'
            links = ''.join(
                f'<li><details><summary>{escape(name.removeprefix(directory))}</summary>'
                f'<pre>{escape(files[name].decode("utf-8"))}</pre>'
                f'<a href="../fonts/{key}/{quote(name)}">原文ファイル</a></details></li>'
                for name in sorted(files) if name.startswith(directory))
            faces.append(f'<div class="license-face"><h3>{face_label}</h3><ul>{links}</ul></div>')
        license_sections.append(f'<section class="section" aria-labelledby="license-{key}"><h2 id="license-{key}">{escape(label)} <small>バージョン {version}</small></h2>{"".join(faces)}</section>')
        catalog.append({'id': key, 'label': label, 'version': version,
                        'url': f'downloads/{archive_name}', 'bytes': len(zipped), 'sha256': sha256(zipped)})
    write_atomic(output / 'downloads' / 'manifest.json', (json.dumps(catalog, ensure_ascii=False, indent=2) + '\n').encode())
    index = f'''<!doctype html>
<html lang="ja">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ライセンス・帰属表示 — 墨羽 / Suminoha Maru</title>
<link rel="stylesheet" href="../fonts/fonts.css"><link rel="stylesheet" href="../style.css"></head>
<body><main class="license-page"><div class="section"><a href="../index.html#downloads">紹介ページへ戻る</a>
<h1>ライセンス・帰属表示</h1><p>各配布ZIPに含まれるライセンスと帰属表示の原文です。用途と書体ごとに確認できます。</p></div>
{''.join(license_sections)}</main></body></html>
'''
    write_atomic(output / 'licenses' / 'index.html', index.encode())
    return catalog


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'site')
    args = parser.parse_args()
    for package in build(ROOT, args.out):
        print(f"{package['label']}: {package['url']} ({package['bytes']:,} bytes)")
    build_font_styles(ROOT, args.out)
