import json, os
base='/var/tmp/tuesday-measure/1a2/runs'
screens=[
 ('JU7 canned','part-4','job-underwriter-7.canned.run{}',[1,2,3]),
 ('JU8 canned','part-4','job-underwriter-8.canned.run{}',[2,3,4]),
 ('MI9 canned','part-5','mock-interview-9.canned.run{}',[1,2,3]),
 ('MI10','part-5','mock-interview-10.run{}',[1,2,3,5]),
 ('MI11','part-5','mock-interview-11.run{}',[1,2,3,5]),
 ('MI12','part-5','mock-interview-12.run{}',[1,2,3,5]),
 ('MI13','part-5','mock-interview-13.run{}',[2,3,4]),
]
missing=[]; detail={}
res={}
for model in ['haiku','sonnet']:
  for name,part,pat,outs in screens:
    pooled=0
    for inst in ['alone','tuesday']:
      d=os.path.join(base,model,inst,part)
      n=0; fails=[]
      for r in range(5):
        stem=pat.format(r)
        ok=True; why=[]
        for gi in (1,2):
          f=os.path.join(d,f'{stem}.grade-{gi}.json')
          if not os.path.exists(f):
            missing.append(f); ok=False; why.append(f'g{gi} missing'); continue
          g=json.load(open(f))
          vs={}
          for v in g['verdicts']:
            vs.setdefault(v['n'],[]).append(v['verdict'])
          for o in outs:
            vv=vs.get(o)
            if vv is None: ok=False; why.append(f'g{gi} n{o} absent')
            elif len(vv)>1: why.append(f'g{gi} n{o} dup{vv}'); ok = ok and all(x=='PASS' for x in vv)
            elif vv[0]!='PASS': ok=False; why.append(f'g{gi} n{o} {vv[0]}')
        if ok: n+=1
        else: fails.append((r,why))
      res[(model,name,inst)]=n; pooled+=n
      detail[(model,name,inst)]=fails
    res[(model,name,'pooled')]=pooled
print('| model | screen | alone /5 | tuesday /5 | pooled /10 |')
for model in ['haiku','sonnet']:
  for name,_,_,outs in screens:
    print(f"| {model} | {name} (outs {','.join(map(str,outs))}) | {res[(model,name,'alone')]} | {res[(model,name,'tuesday')]} | {res[(model,name,'pooled')]} |")
print('MISSING:',missing)
for k,v in detail.items():
  if v: print(k, v)
