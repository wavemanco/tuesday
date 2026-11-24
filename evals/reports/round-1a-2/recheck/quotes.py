import json,re
d=json.load(open('/var/tmp/tuesday-measure/1a2/frozen/cases/candidate/mock-interview.evals.json'))
e=[x for x in d['evals'] if x['id']==12][0]
src=e['prompt']+' '+' '.join(json.dumps(f,ensure_ascii=False) for f in (e.get('files') or []))
m=re.search(r"'(Dear Aoife.*?office manager\.)'",src,re.S)
invite=m.group(1)
def norm(s):
    s=s.lower()
    for a,b in [('’',"'"),('‘',"'"),('“','"'),('”','"'),('–','-'),('—','-')]: s=s.replace(a,b)
    return re.sub(r'\s+',' ',s).strip()
N=norm(invite)
base='/var/tmp/tuesday-measure/1a2/runs/haiku/tuesday/part-5/'
for stem in ['mock-interview-12.run2','mock-interview-12.run1']:
    md=open(base+stem+'.md').read()
    para=md.split('\n\n')[0]
    print('==',stem)
    quotes=re.findall(r'["“]([^"”]+)["”]',para)
    for q in quotes:
        frags=[f.strip(' .,;:') for f in re.split(r'\.\.\.|…',q) if f.strip(' .,;:')]
        res=[]
        pos=0; ok=True
        for f in frags:
            i=N.find(norm(f),pos)
            res.append((f, i>=0))
            if i<0: ok=False
            else: pos=i
        print(repr(q),'->','WORD-FOR-WORD' if ok else 'NOT', res)
