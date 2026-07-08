import re
t=open('content/v60-vs-kalita-wave-budget-pour-over-dripper.md',encoding='utf-8').read()
for l in t.splitlines()[:8]:
    if l.startswith('title:'): print('TITLE len', len(l.split('title:',1)[1].strip().strip('"')))
    if l.startswith('description:'): print('DESC len', len(l.split('description:',1)[1].strip()))
body=t.split('---',2)[2]
print('WORD count', len(re.findall(r"[A-Za-z0-9']+", body)))
print('internal', re.findall(r'\]\((?!aff:)([a-z0-9-]+\.html)\)', body))
print('aff', re.findall(r'\]\(aff:([A-Z0-9]+)\)', body))
