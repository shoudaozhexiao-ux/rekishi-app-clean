import importlib.util,json,random
from pathlib import Path
spec=importlib.util.spec_from_file_location('legacy',Path(__file__).with_name('legacy_history.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
rng=random.Random(1025)
words=[w for theme in m.THEMES.values() for w in theme['words']]
cases=[]
for year in (2026,2027,2030):
 for _ in range(15):
  earlier={'year':year-61,'events':['・'.join(rng.sample(words,3)) for _ in range(20)]}
  later={'year':year-1,'events':['・'.join(rng.sample(words,3)) for _ in range(20)]}
  history={'year':year-60,'events':['・'.join(rng.sample(words,3)) for _ in range(25)]}
  cases.append({'year':year,'earlier':earlier,'later':later,'history':history,'pairs':m.compare_events(earlier,later),'forecasts':m.forecast_from_history(year,history)})
Path(__file__).with_name('parity.json').write_text(json.dumps(cases,ensure_ascii=False))
print('Generated 45 parity cases from original Python implementation')
