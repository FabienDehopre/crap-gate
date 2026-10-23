import json,sys,collections
d=json.load(open(sys.argv[1]))
ms=d.get('methods') or d.get('results') or d
if isinstance(ms,dict): print(list(ms.keys())[:20]); sys.exit()
tot=len(ms); na=[m for m in ms if m.get('crap') is None]
print(f"{sys.argv[1].split('/')[-1]}: methods={tot} scored={tot-len(na)} NA={len(na)} fail30={sum(1 for m in ms if (m.get('crap') or 0)>30)}")
by=collections.Counter(('libs' if '/libs/' in '/'+m['src'] else 'src', m.get('crap') is None) for m in ms)
print('  ',dict(by))
