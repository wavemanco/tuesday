import json,sys,os
run_dir,stem=sys.argv[1],sys.argv[2]
m=json.load(open(os.path.join(run_dir,stem+'.meta.json')))
print('graded_invocation',m.get('graded_invocation'),'response_file',m.get('response_file'),'artifacts',m.get('artifacts'))
for i,inv in enumerate(m['invocations']):
    print('=== INV',i,'outcome',inv.get('outcome'),'nudged',inv.get('nudged'))
    for f in inv.get('files') or []:
        print('FILE',json.dumps(f,ensure_ascii=False))
    for tc in inv.get('tool_calls') or []:
        s=json.dumps(tc.get('input'),ensure_ascii=False)
        print('TC',tc.get('name'),s[:int(sys.argv[3]) if len(sys.argv)>3 else 300])
