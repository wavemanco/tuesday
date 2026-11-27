"""Positive/negative controls for scan.py (prints no IBAN characters):
 - runs() on the eval-12 prompt must find one 22-char run
 - per stream: whole-IBAN count in the raw file text and in non-assistant events; whether a user prompt event exists;
   thinking blocks' total text length (to show whether thinking text was scannable); Skill calls made."""
import json, os, sys, collections
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))  # helpers sit beside this script
from scan import runs, ROOT
ev12 = [x for x in json.load(open('/var/tmp/tuesday-measure/1a5/frozen/cases/candidate/mock-interview.evals.json'))['evals'] if x['id'] == 12][0]
print('control: runs in eval-12 prompt =', runs(ev12['prompt']))
for model in ('haiku', 'sonnet'):
    for inst in ('alone', 'tuesday'):
        rd = os.path.join(ROOT, model, inst, 'part-5')
        for r in range(5):
            stem = f'mock-interview-12.run{r}'
            meta = json.load(open(os.path.join(rd, stem + '.meta.json')))
            for ai, inv in enumerate(meta['invocations']):
                raw = open(os.path.join(rd, inv['stream'])).read()
                rawhits = sum(1 for line in raw.split('\n') for k in runs(line) if k == 22)
                nonasst, think_len, skills, userstr = 0, 0, [], 0
                for line in raw.split('\n'):
                    try:
                        ev = json.loads(line)
                    except Exception:
                        continue
                    if ev.get('type') == 'assistant':
                        for b in ev['message'].get('content', []) or []:
                            if b.get('type') == 'thinking':
                                think_len += len(b.get('thinking', ''))
                            if b.get('type') == 'tool_use' and b.get('name') == 'Skill':
                                skills.append((b['input'] or {}).get('skill'))
                    else:
                        if ev.get('type') == 'user' and isinstance(ev.get('message', {}).get('content'), str):
                            userstr += 1
                        nonasst += sum(1 for k in runs(json.dumps(ev, ensure_ascii=False)) if k == 22)
                print(f'{model}/{inst}/{stem} a{ai}: raw-file whole hits={rawhits} non-assistant whole hits={nonasst} '
                      f'user-string events={userstr} thinking chars={think_len} Skill={skills}')
