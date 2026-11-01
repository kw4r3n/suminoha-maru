"""Install the current prose revision without changing application settings."""
import json,hashlib,os,shutil,subprocess,tempfile
from pathlib import Path
from check_repository_layout import check_licenses
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'fonts/gothic';HOME=Path.home();FONT=HOME/'.local/share/fonts'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def install():
 m=json.loads((OUT/'manifest.json').read_text());assert (OUT/'validation.json').exists() and (OUT/'reproducibility.json').exists();controls=[]
 for folder in ['fonts/code35','fonts/code12']:
  for r in json.loads((ROOT/folder/'manifest.json').read_text()):
   if folder=='fonts/code35' and r['kind']=='prose':continue
   p=FONT/r['postscript'].removesuffix('-Regular')/r['file'];assert sha(p)==r['sha256'];controls.append({'file':str(p),'sha256':sha(p)})
 config={str(p):sha(p) for p in (HOME/'.config/fontconfig').rglob('*') if p.is_file()};config[str(HOME/'.config/kdeglobals')]=sha(HOME/'.config/kdeglobals');prepared=[];installed=[]
 for r in m:check_licenses(OUT/'licenses'/r['postscript'],r['family'],tracking=True)
 try:
  for r in m:
   src=OUT/r['file'];dest=FONT/r['postscript'].removesuffix('-Regular')/r['file'];assert sha(src)==r['sha256'];assert sha(dest) in [r['source_sha256'],r['sha256']],dest
   shutil.copytree(OUT/'licenses'/r['postscript'],dest.parent/'licenses',dirs_exist_ok=True)
   scan=subprocess.check_output(['fc-scan','-f','%{family}|%{fontversion}|%{postscriptname}',str(src)],text=True)
   installed.append({'file':str(dest),'sha256':r['sha256'],'scan':scan})
   if sha(dest)==r['sha256']:continue
   fd,tmp=tempfile.mkstemp(prefix='.tracking-008-',suffix='.tmp',dir=dest.parent);os.close(fd);tmp=Path(tmp);prepared.append((tmp,dest));shutil.copyfile(src,tmp);shutil.copymode(src,tmp);assert sha(tmp)==r['sha256']
  # Finish license copies and font scans before replacing any active font.
  for tmp,dest in prepared:os.replace(tmp,dest)
 finally:
  for tmp,_ in prepared:tmp.unlink(missing_ok=True)
 for item in installed:assert sha(Path(item['file']))==item['sha256']
 subprocess.run(['fc-cache','-f']+[str(Path(x['file']).parent) for x in installed],check=True)
 for c in controls:assert sha(Path(c['file']))==c['sha256']
 for p,h in config.items():assert sha(Path(p))==h,p
 r={'version':'0.008','installed':installed,'atomic_inode_replacement':True,'code_fonts_unchanged':controls,'fontconfig_and_KDE_hashes_unchanged':config,'no_app_restart_or_signals':True};(ROOT/'reports/prose-tracking-installation.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps(r,ensure_ascii=False),flush=True)
if __name__=='__main__':install()
