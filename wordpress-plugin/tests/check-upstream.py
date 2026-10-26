"""Smoke-test only public, fixed upstream endpoints; no credentials used."""
import json
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from xml.etree import ElementTree
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent))
from legacy_history import EventParser
params={'action':'parse','page':'1966年の日本','prop':'text|revid','format':'json','formatversion':2,'redirects':1,'disableeditsection':1}
headers={'User-Agent':'GozaiHistory/1.0 (https://gozaigozai.com/ai-rekishi/)'}
with urlopen(Request('https://ja.wikipedia.org/w/api.php?'+urlencode(params),headers=headers),timeout=25) as r:
 data=json.load(r)
parser=EventParser();parser.feed(data['parse']['text'])
assert parser.events and data['parse']['revid']
with urlopen(Request('https://news.google.com/rss/search?'+urlencode({'q':'人工知能','hl':'ja','gl':'JP','ceid':'JP:ja'}),headers=headers),timeout=25) as r:
 rss=ElementTree.fromstring(r.read())
assert rss.find('channel') is not None
print('PASS: current Wikipedia event section and Google News RSS are reachable from CI')
