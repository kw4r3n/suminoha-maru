"""Source-derived finite witnesses and semantic GSUB graph inventory; not an exhaustive language grammar."""
import itertools,json,unicodedata as ud,hashlib

def subtables(f,index):
 l=f['GSUB'].table.LookupList.Lookup[index]
 for st in l.SubTable:yield (st.ExtensionLookupType,st.ExtSubTable) if l.LookupType==7 else (l.LookupType,st)

def source_witnesses(f):
 words={}
 for cp,n in sorted(f.getBestCmap().items(),key=lambda x:(not(32<=x[0]<127),x[0])):
  if n not in words and (32<=cp<127 or ud.category(chr(cp))[0] in 'PS'):words[n]=chr(cp)
 for _ in range(12):
  count=len(words)
  for i in range(len(f['GSUB'].table.LookupList.Lookup)):
   for typ,st in subtables(f,i):
    if typ==1:
     for a,b in st.mapping.items():
      if a in words and b not in words:words[b]=words[a]
    if typ==3:
     for a,bb in st.alternates.items():
      if a in words:
       for b in bb:words.setdefault(b,words[a])
    if typ==4:
     for a,ll in st.ligatures.items():
      for l in ll:
       if all(n in words for n in [a]+l.Component):words.setdefault(l.LigGlyph,''.join(words[n] for n in [a]+l.Component))
  if count==len(words):break
 def combine(sets):
  opts=[list(dict.fromkeys(words[n] for n in ss if n in words))[:3] for ss in sets]
  if any(not x for x in opts):return []
  if not opts:return []
  if len(opts)>80:return []
  values={''.join(x[0] for x in opts)}
  for pos,opt in enumerate(opts):
   for value in opt[1:]:v=[x[0] for x in opts];v[pos]=value;values.add(''.join(v))
  if __import__('math').prod(map(len,opts))<=64:values|={''.join(x) for x in itertools.product(*opts)}
  return [x for x in values if 0<len(x)<=80]
 per_lookup={}
 for i in range(len(f['GSUB'].table.LookupList.Lookup)):
  examples=set()
  for typ,st in subtables(f,i):
   if typ==1:examples|={words[a] for a in st.mapping if a in words}
   if typ==3:examples|={words[a] for a in st.alternates if a in words}
   if typ==4:
    for a,ll in st.ligatures.items():
     for l in ll:examples.update(combine([[n] for n in [a]+l.Component]))
   if typ==6 and st.Format==3:examples.update(combine([c.glyphs for c in list(reversed(st.BacktrackCoverage))+st.InputCoverage+st.LookAheadCoverage]))
   if typ==6 and st.Format==1:
    for first,rules in zip(st.Coverage.glyphs,st.ChainSubRuleSet):
     if rules:
      for rule in rules.ChainSubRule:examples.update(combine([[x] for x in list(reversed(rule.Backtrack))+[first]+rule.Input+rule.LookAhead]))
  per_lookup[i]=examples
 def refs(index):
  seen=set();stack=[index]
  while stack:
   i=stack.pop()
   if i in seen:continue
   seen.add(i)
   def walk(v):
    if isinstance(v,list):
     for x in v:walk(x)
    elif hasattr(v,'__dict__'):
     for k,x in vars(v).items():
      if k=='LookupListIndex' and isinstance(x,int):stack.append(x)
      else:walk(x)
   for _,st in subtables(f,i):walk(st)
  return seen
 by_feature={}
 for rec in f['GSUB'].table.FeatureList.FeatureRecord:
  allix=set().union(*(refs(i) for i in rec.Feature.LookupListIndex));by_feature[rec.FeatureTag]=set().union(*(per_lookup[i] for i in allix))
 return words,by_feature

def feature_graphs(f):
 lookups=f['GSUB'].table.LookupList.Lookup;cache={}
 def lookup(i):
  if i not in cache:cache[i]=normalize(lookups[i])
  return cache[i]
 def normalize(v):
  if isinstance(v,(str,int,float,type(None),bool)):return v
  if isinstance(v,(list,tuple)):return [normalize(x) for x in v]
  if isinstance(v,dict):return {k:normalize(x) for k,x in sorted(v.items())}
  if hasattr(v,'__dict__'):
   result={}
   for k,x in sorted(vars(v).items()):
    if k.endswith('Count') or k in ['sortCoverageLast','FeatureParams']:continue
    if k=='LookupListIndex':result[k]=[lookup(i) for i in x] if isinstance(x,list) else lookup(x)
    else:result[k]=normalize(x)
   return result
  raise TypeError(type(v))
 result={}
 for rec in f['GSUB'].table.FeatureList.FeatureRecord:
  data=[lookup(i) for i in rec.Feature.LookupListIndex];result[rec.FeatureTag]=hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()
 return result
