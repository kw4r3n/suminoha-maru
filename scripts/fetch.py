#!/usr/bin/env python3
"""Fetch only pinned upstream inputs; refuse hash drift on later runs."""
import hashlib, json, pathlib, re, subprocess, sys, urllib.parse, tempfile, zipfile
ROOT = pathlib.Path(__file__).resolve().parents[1]
COMMIT = 'e7db6ca603fd4862010383ff17ffd6cc4ffac1c0'
FAMILIES = {'comfortaa':None, 'kiwimaru':'Regular',
            'nunito':None, 'zenmarugothic':'Regular'}

def get(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists(): return
    subprocess.run(['curl','--fail','--silent','--show-error','--location','--retry','2',
                    '--max-time','90',url,'--output',str(path)],check=True)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    lock = ROOT/'sources.lock.json'
    if lock.exists():
        entries = json.loads(lock.read_text())['files']
        for item in entries:
            path=ROOT/item['path']
            if not path.exists():
                if 'archive_member' in item:
                    with tempfile.TemporaryDirectory(prefix='morimo-fetch-') as tmp:
                        archive=pathlib.Path(tmp)/'source.zip';get(item['url'],archive)
                        if sha(archive)!=item['archive_sha256']: raise ValueError('Archive hash mismatch')
                        path.parent.mkdir(parents=True,exist_ok=True)
                        with zipfile.ZipFile(archive) as z: path.write_bytes(z.read(item['archive_member']))
                else: get(item['url'],path)
            if sha(path)!=item['sha256']: raise ValueError(f'Hash mismatch: {path}')
        print(f'Verified {len(entries)} pinned inputs')
        return
    if '--lock-initial-inputs' not in sys.argv:
        raise SystemExit('Missing lockfile; only maintainer bootstrap may use --lock-initial-inputs')
    entries=[]
    for family,style in FAMILIES.items():
        base=f'https://raw.githubusercontent.com/google/fonts/{COMMIT}/ofl/{family}/'
        directory=ROOT/'sources'/family
        for filename in ['METADATA.pb','OFL.txt']:
            path=directory/filename; url=base+filename
            get(url,path)
            entries.append(dict(path=str(path.relative_to(ROOT)),url=url,sha256=sha(path)))
        metadata=(directory/'METADATA.pb').read_text()
        names=re.findall(r'filename: "([^"]+)"', metadata)
        names=[n for n in names if 'Italic' not in n and 'ital,' not in n]
        if style: names=[n for n in names if f'-{style}.ttf' in n]
        assert len(names)==1,(family,names)
        filename=names[0]; url=base+urllib.parse.quote(filename)
        path=directory/filename; get(url,path)
        entries.append(dict(path=str(path.relative_to(ROOT)),url=url,sha256=sha(path)))
        print(f'{family}: {filename}, {path.stat().st_size} bytes')
    lock.write_text(json.dumps(dict(repository='https://github.com/google/fonts',commit=COMMIT,
                                    files=entries),indent=2)+'\n')
    main()

if __name__=='__main__': main()
