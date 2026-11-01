#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def verify():
 for folder in ['nerd-symbols']:
  p=ROOT/'sources'/folder;j=json.loads((p/'lock.json').read_text())
  files={x['name']:x['sha256'] for x in j} if isinstance(j,list) else j['files']
  for name,expected in files.items():assert hashlib.sha256((p/name).read_bytes()).hexdigest()==expected,(folder,name)
 return True
if __name__=='__main__':assert verify();print('Pinned extra sources: all hashes match')
