"""Regenerate current fonts from upstream sources; discard all intermediate fonts."""
import argparse
import ctypes
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from check_repository_layout import check_licenses

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ('code35', 'code12', 'gothic')
FONT_SUFFIXES = {'.ttf', '.otf', '.woff', '.woff2', '.ttc'}
STAGES = (
    'build', 'code_extras', 'build_grid_small', 'build_code_small',
    'build_prose', 'build_prose_zen', 'build_prose_restore', 'build_prose_kana',
    'build_practical_refinement', 'build_prose_equal', 'build_code_features',
    'build_code_zen', 'build_code_latin_size', 'build_code_common_size',
    'build_code_topdown', 'build_code_jp_size', 'build_code_ratio23',
    'build_terminal_addons', 'code_ratio35', 'build_han_companions',
    'build_han_compat', 'build_han_spacefix', 'build_prose_han',
    'build_suminoha', 'build_code12', 'build_prose_tracking',
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_workspace(root, work):
    def ignore(folder, names):
        return [name for name in names
                if Path(name).suffix.lower() in FONT_SUFFIXES or name == '__pycache__']
    shutil.copytree(root / 'scripts', work / 'scripts', ignore=ignore)
    shutil.copytree(root / 'inputs', work / 'inputs', ignore=ignore)
    # Source verifiers read these files; generated fonts never enter this directory.
    (work / 'sources').symlink_to((root / 'sources').resolve(), target_is_directory=True)
    shutil.copy2(root / 'sources.lock.json', work / 'sources.lock.json')


def stage_code(module):
    if module == 'code_extras':
        return 'import code_extras; code_extras.main()'
    if module == 'code_ratio35':
        return ('from pathlib import Path; import code_ratio35; '
                'code_ratio35.build(Path.cwd(), Path("inputs/terminal-ratio35"))')
    return f'import runpy; runpy.run_module({module!r}, run_name="__main__")'


def run_stages(work):
    env = os.environ | {'PYTHONPATH': str(work / 'scripts'), 'PYTHONDONTWRITEBYTECODE': '1'}
    for module in STAGES:
        print(f'生成: {module}', flush=True)
        result = subprocess.run([sys.executable, '-c', stage_code(module)], cwd=work,
                                env=env, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(f'{module} failed:\n{result.stdout}\n{result.stderr}')
    for script, args in [('check_suminoha.py', []),
                         ('check_code12.py', ['.', 'fonts/code12']),
                         ('check_prose_tracking.py', [])]:
        print(f'検証: {script}', flush=True)
        subprocess.run([sys.executable, str(work / 'scripts' / script), *args],
                       cwd=work, env=env, check=True)


def verify_workspace(work, recipe):
    for name, digest in (recipe['intermediates'] | recipe['outputs']).items():
        path = Path(name)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError(f'Invalid recipe path: {name}')
        if sha(work / path) != digest:
            raise ValueError(f'Regenerated font hash mismatch: {name}')


def normalize_notices(folder):
    for name in ['Base-NOTICES.txt', 'Prose-NOTICES.txt']:
        path = folder / name
        if not path.exists():
            continue
        copyrights = {line for line in path.read_text().splitlines()
                      if line.lstrip().casefold().startswith(('copyright ', '©'))}
        # OFL bodies also contain wrapped lines beginning with "copyright".
        copyrights.update(line for source in sorted(folder.glob('*OFL*'))
                          for line in source.read_text().splitlines()
                          if re.match(r'^\s*(?:copyright\s+(?:\(c\)\s*)?|©\s*)\d{4}\b', line, re.I))
        if not copyrights:
            raise ValueError(f'Missing copyright attribution: {path}')
        path.write_text('墨羽 / Suminoha Maru — 派生フォントの帰属表示\n\n'
                        + '\n'.join(sorted(copyrights))
                        + '\n\n適用されるライセンスと派生元の通知は、このディレクトリに同梱しています。\n')


def select_current(root, work, output):
    for package in PACKAGES:
        source = work / 'fonts' / package
        target = output / package
        target.mkdir(parents=True)
        rows = json.loads((source / 'manifest.json').read_text())
        if package == 'code35':
            rows = [r for r in rows if r['kind'] == 'code']
        for row in rows:
            for name in [row['file'], str(Path(row['file']).with_suffix('.woff2'))]:
                shutil.copy2(source / name, target / name)
            notices = source / 'licenses' / row['postscript']
            check_licenses(notices, row['family'], tracking=package == 'gothic')
            destination = target / 'licenses' / row['postscript']
            shutil.copytree(notices, destination)
            normalize_notices(destination)
        (target / 'manifest.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
        shutil.copy2(root / 'fonts' / package / 'README.md', target / 'README.md')
        validation = json.loads((source / 'validation.json').read_text())
        validation.pop('installed', None)
        if package == 'code35':
            validation.pop('prose', None)
            validation['fonts'] = [r for r in validation['fonts'] if 'Code 35' in r['family']]
        (target / 'validation.json').write_text(json.dumps(validation, indent=2) + '\n')
        (target / 'reproducibility.json').write_text(json.dumps({
            'method': 'Upstream rebuild compared with pinned current output hashes',
            'files': {name: sha(target / name) for row in rows
                      for name in [row['file'], str(Path(row['file']).with_suffix('.woff2'))]},
        }, indent=2) + '\n')
    shutil.copy2(root / 'fonts' / 'README.md', output / 'README.md')
    sys.path.insert(0, str(root / 'scripts'))
    from make_suminoha_companion_config import make
    make(output / 'code12' / '68-suminoha-companions.conf')


def exchange_directories(first, second):
    libc = ctypes.CDLL(None, use_errno=True)
    exchange = libc.renameat2
    exchange.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    exchange.restype = ctypes.c_int
    # Linux RENAME_EXCHANGE atomically swaps two complete trees on one filesystem.
    if exchange(-100, os.fsencode(first), -100, os.fsencode(second), 2):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def publish_tree(staged, output):
    if output.is_symlink():
        raise ValueError('Output must not be a symlink')
    if output.exists() and not {p.name for p in output.iterdir()} <= {*PACKAGES, 'README.md'}:
        raise ValueError('Output contains unrelated files')
    if output.exists():
        exchange_directories(staged, output)
    else:
        staged.rename(output)


def rebuild(root, output):
    if sys.flags.optimize:
        raise RuntimeError('Run without -O: source and font checks require assertions')
    from check_repository_layout import check_source_pins
    check_source_pins(root)
    from build_prose_kana import library
    library()  # Reject an unavailable or changed native build tool before the long build.
    recipe = json.loads((root / 'inputs/build-recipe.json').read_text())
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='suminoha-build-') as temporary:
        work = Path(temporary)
        prepare_workspace(root, work)
        run_stages(work)
        verify_workspace(work, recipe)
        # Stage on the output filesystem so replacement and rollback use renames.
        with tempfile.TemporaryDirectory(prefix='.suminoha-output-', dir=output.parent) as staging:
            selected = Path(staging) / 'fonts'
            selected.mkdir()
            select_current(root, work, selected)
            publish_tree(selected, output)
    print('完了: 現行24ファイルを生成し、中間フォントを削除しました。')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'fonts')
    args = parser.parse_args()
    rebuild(ROOT, args.out.absolute())
