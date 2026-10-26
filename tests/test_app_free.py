import runpy
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

from history_free import ServiceError


class FakeStreamlit(types.ModuleType):
    def __init__(self):
        super().__init__('streamlit')
        self.sidebar = self
        self.year = 2026
        self.displayed = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def __getattr__(self, name):
        if name in ('text_input', 'select_slider'):
            return lambda *a, **k: k['value']
        if name == 'radio':
            return lambda *a, **k: k['options'][k['index']]
        if name == 'columns':
            return lambda *a, **k: [self, self]
        if name in ('spinner', 'expander'):
            return lambda *a, **k: self
        if name in ('secrets', 'session_state'):
            raise AssertionError('No key or paid AI configuration should be used')
        return lambda *a, **k: self.displayed.append((name, a))


class AppTests(unittest.TestCase):
    def setUp(self):
        self.st = FakeStreamlit()
        component = types.ModuleType('streamlit.components.v1')
        component.declare_component = lambda *a, **k: lambda **kw: self.st.year
        components = types.ModuleType('streamlit.components')
        components.v1 = component
        self.st.components = components
        self.modules = {
            'streamlit': self.st, 'streamlit.components': components,
            'streamlit.components.v1': component, 'feedparser': types.ModuleType('feedparser'),
        }

    @staticmethod
    def history(year, scope):
        return {
            'year': year, 'scope': scope, 'events': [f'{year}年の鉄道が開通'],
            'title': f'{year}年', 'revision_url': 'https://example.com/source',
            'retrieved_at': '2026-01-01T00:00:00Z',
        }

    def execute(self):
        with patch.dict(sys.modules, self.modules), \
                patch('urllib.request.urlopen', side_effect=URLError('offline')):
            runpy.run_path(str(Path(__file__).parents[1] / 'app.py'))

    @patch('history_free.fetch_history')
    def test_correct_four_sources_no_keys_and_updates_each_display(self, fetch):
        fetch.side_effect = self.history
        self.execute()
        self.assertEqual({call.args for call in fetch.call_args_list}, {
            (1965, 'world'), (2025, 'world'), (1966, 'japan'), (1966, 'world'),
        })
        self.assertTrue(any(name == 'markdown' and 'chronicle-table' in args[0] for name, args in self.st.displayed))
        self.assertEqual(len([1 for name, args in self.st.displayed if name == 'markdown' and '<article class="forecast-sheet">' in args[0]]), 2)
        self.execute()
        self.assertEqual(fetch.call_count, 8)

    @patch('history_free.fetch_history')
    def test_browser_rollover_moves_comparison_and_forecast(self, fetch):
        fetch.side_effect = self.history
        self.st.year = 2027
        self.execute()
        self.assertEqual({call.args for call in fetch.call_args_list}, {
            (1966, 'world'), (2026, 'world'), (1967, 'japan'), (1967, 'world'),
        })
        forecasts = [args[0] for name, args in self.st.displayed if name == 'markdown' and '<article class="forecast-sheet">' in args[0]]
        self.assertTrue(forecasts)
        self.assertTrue(all('2027年' in text for text in forecasts))

    @patch('history_free.fetch_history')
    def test_one_failed_source_does_not_disable_other_forecast(self, fetch):
        def response(year, scope):
            if scope == 'japan':
                raise ServiceError('日本の資料を取得できません')
            return self.history(year, scope)
        fetch.side_effect = response
        self.execute()
        self.assertIn(('error', ('日本の資料を取得できません',)), self.st.displayed)
        self.assertEqual(len([1 for name, args in self.st.displayed if name == 'markdown' and '<article class="forecast-sheet">' in args[0]]), 1)


if __name__ == '__main__':
    unittest.main()
