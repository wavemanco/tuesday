"""Dump an eval (prompt, files, expectations with clause expansion), masked.
usage: python3 dump_eval.py <skill> <id> [exp_numbers comma-separated | all] [--no-input]"""
import sys, json, re
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))  # helpers sit beside this script
from mask import mprint

skill, eid = sys.argv[1], int(sys.argv[2])
which = sys.argv[3] if len(sys.argv) > 3 else 'all'
noinput = '--no-input' in sys.argv
d = json.load(open(f'/var/tmp/tuesday-measure/1a5/frozen/cases/candidate/{skill}.evals.json'))
e = [x for x in d['evals'] if x['id'] == eid][0]
cl = d['clauses']


def expand(t):
    return re.sub(r'\{\{(\w+)\}\}', lambda m: '<<CLAUSE ' + m.group(1) + ': ' + cl[m.group(1)] + ' >>', t)


print('keys:', list(e.keys()))
if not noinput:
    mprint('PROMPT:\n' + str(e.get('prompt')))
    for f in e.get('files', []) or []:
        if isinstance(f, dict):
            mprint('FILE:', json.dumps({k: v for k, v in f.items()}, ensure_ascii=False, indent=1))
        else:
            mprint('FILE:', f)
    for k in e:
        if k not in ('prompt', 'files', 'expectations', 'id'):
            mprint(f'{k}:', json.dumps(e[k], ensure_ascii=False)[:3000])
for i, x in enumerate(e['expectations'], 1):
    if which == 'all' or str(i) in which.split(','):
        mprint(f'\n#{i}: ' + expand(x if isinstance(x, str) else json.dumps(x)))
