"""Read-only integrity check for the organized font packages and pinned inputs."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check_source_pins(root):
    locks = [(root / 'sources.lock.json', root),
             (root / 'sources/japanese-medium.lock.json', root)]
    locks += [(root / 'sources' / name / 'lock.json', root / 'sources' / name)
              for name in ['notosans', 'han', 'terminal-addons', 'nerd-symbols']]
    for lock, folder in locks:
        data = json.loads(lock.read_text())
        rows = data['files'] if isinstance(data, dict) else data
        if isinstance(rows, dict):
            rows = [{'name': name, 'sha256': digest} for name, digest in rows.items()]
        for row in rows:
            name = Path(row.get('path', row.get('name', '')))
            assert name.parts and not name.is_absolute() and '..' not in name.parts, name
            assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == row['sha256'], name


def check_pin(root, name, digest):
    relative = Path(name)
    assert relative.parts and not relative.is_absolute() and '..' not in relative.parts, name
    path = root / relative
    if path.exists():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, path
    else:
        # Intermediate source paths describe temporary build outputs, never retained fonts.
        recipe = json.loads((root / 'inputs/build-recipe.json').read_text())
        assert recipe['intermediates'].get(str(relative)) == digest, relative


def check_licenses(folder, family, tracking=False):
    required = set()
    if ' Han ' in family:
        required.update(['NOTICES.txt', 'Noto-OFL.txt', 'Plangothic-OFL.txt',
                         'Plangothic-README.md', 'Unicode-LICENSE.txt'])
    elif 'Gothic' not in family:
        required.update(['Base-NOTICES.txt', 'Base-OFL.txt', 'Devicons-LICENSE.txt',
                         'Nerd-LICENSE', 'Nerd-octicons-LICENSE.txt',
                         'Nerd-powerline-LICENSE.txt', 'Nerd-powerline-extra-LICENSE.txt',
                         'NotoEmoji-OFL.txt', 'NotoMath-OFL.txt', 'NotoSans-OFL.txt',
                         'NotoSymbols-OFL.txt'])
    if 'Gothic' in family:
        required.update(['Prose-NOTICES.txt', 'Prose-OFL.txt'])
    if tracking:
        required.add('Tracking-NOTICE.txt')
    for name in required:
        path = folder / name
        assert path.is_file() and path.stat().st_size > 0, path


def check_build_baselines(root):
    for name in ['grid-small', 'code-small']:
        rows = json.loads((root / 'inputs/build-baselines' / (name + '.json')).read_text())['repeat']
        assert rows, name
        for filename, digest in rows.items():
            assert Path(filename).name == filename, filename
            path = root / 'inputs' / name / filename
            check_pin(root, str(path.relative_to(root)), digest)


def check():
    fonts = 0
    for package in ['code35', 'code12', 'gothic']:
        folder = ROOT / 'fonts' / package
        assert not (ROOT / package).exists(), package
        for row in json.loads((folder / 'manifest.json').read_text()):
            paths = [(ROOT / row['source'], row['source_sha256']),
                     (folder / row['file'], row['sha256']),
                     ((folder / row['file']).with_suffix('.woff2'), row['woff2_sha256'])]
            for path, digest in paths:
                check_pin(ROOT, str(path.relative_to(ROOT)), digest)
            check_licenses(folder / 'licenses' / row['postscript'], row['family'],
                           tracking=package == 'gothic')
            fonts += 2
    check_source_pins(ROOT)
    manifests = list((ROOT / 'inputs' / 'preservation').glob('*.json'))
    assert len(manifests) == 5, 'Missing preservation fixtures'
    for manifest in manifests:
        rows = json.loads(manifest.read_text())
        assert rows, manifest
        for name, digest in rows.items():
            assert not Path(name).is_absolute(), (manifest, name)
            check_pin(ROOT, name, digest)
    check_build_baselines(ROOT)
    recipe = json.loads((ROOT / 'inputs/build-recipe.json').read_text())
    for name, digest in recipe['outputs'].items():
        path = ROOT / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, path
    font_suffixes = {'.ttf', '.otf', '.woff', '.woff2', '.ttc'}
    assert not any(p.suffix.lower() in font_suffixes for p in (ROOT / 'inputs').rglob('*')), 'Retained intermediate font'
    actual = {str(p.relative_to(ROOT)) for p in (ROOT / 'fonts').rglob('*')
              if p.suffix.lower() in font_suffixes}
    assert actual == set(recipe['outputs']), 'Unexpected or missing current font'
    for parent in ['fonts', 'inputs']:
        for path in (ROOT / parent).rglob('*'):
            assert not path.is_symlink() or path.exists(), path
    for path in (ROOT / 'scripts').glob('*.py'):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                name = node.module.split('.')[0]
                if name.startswith(('build', 'check_', 'render_', 'code_')) or name in {'hb', 'samples', 'validate', 'fetch', 'refinement'}:
                    assert (path.parent / (name + '.py')).is_file(), (path, name)
    print(f'PASS: {fonts} font hashes, source pins, licenses, symlinks and local imports')


if __name__ == '__main__':
    check()
