#!/usr/bin/env python3
"""A clean second build must match every distributable byte; keep only hashes."""
import hashlib,json,pathlib,tempfile
from build import ROOT,build

def main():
    with tempfile.TemporaryDirectory(prefix='morimo-repeat-') as tmp:
        out=pathlib.Path(tmp);build(out);results=[]
        for p in sorted((ROOT/'inputs/dist').iterdir()):
            if p.suffix not in ['.ttf','.woff2'] and p.name!='build-summary.json':continue
            a=hashlib.sha256(p.read_bytes()).hexdigest();b=hashlib.sha256((out/p.name).read_bytes()).hexdigest()
            results.append(dict(file=p.name,bytes=p.stat().st_size,sha256=a,repeat_sha256=b,equal=a==b))
        assert results and all(r['equal'] for r in results),results
    (ROOT/'reports/reproducibility.json').write_text(json.dumps(dict(builds='dist + independent temporary rebuild',results=results),indent=2)+'\n')
    (ROOT/'inputs/dist/SHA256SUMS').write_text(''.join(r['sha256']+'  '+r['file']+'\n' for r in results))
    print('PASS: second clean build matches all ten fonts and build summary byte-for-byte')
if __name__=='__main__':main()
