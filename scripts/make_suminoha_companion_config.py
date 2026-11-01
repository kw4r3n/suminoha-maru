from pathlib import Path

def make(out):
 lines=['<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd"><fontconfig>', '<!-- Exact-family companion selection only; no generic/default rules. -->']
 for en,jp in [('Suminoha Maru Gothic','墨羽 丸ゴシック'),('Suminoha Maru Code 35 NF','墨羽 丸コード 35 NF'),('Suminoha Maru Code 12 NF','墨羽 丸コード 12 NF')]:
  companions=[en+' Han '+p for p in ['JP','RareA','RareB']]
  entries=[(en,companions),(jp,companions)]
  for part in ['JP','RareA','RareB']:
   tail=[en]+[x for x in companions if not x.endswith(' '+part)]
   entries.extend([(en+' Han '+part,tail),(jp+' 漢字 '+part,tail)])
  for name,tail in entries:
   edits=''
   if ' Han ' in name or ' 漢字 ' in name:
    edits='<edit name="family" mode="prepend" binding="strong"><string>'+tail[0]+'</string></edit>'
    tail=tail[1:]
   edits+='<edit name="family" mode="append" binding="strong">'+''.join('<string>'+x+'</string>' for x in tail)+'</edit>'
   lines.append('<match target="pattern"><test name="family" qual="first" compare="eq"><string>'+name+'</string></test>'+edits+'</match>')
 lines.append('</fontconfig>');out.write_text('\n'.join(lines)+'\n')
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=Path(__file__).resolve().parents[1]/'fonts/code12/68-suminoha-companions.conf');a=p.parse_args();make(a.out)
