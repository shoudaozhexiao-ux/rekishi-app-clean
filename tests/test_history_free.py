import unittest
from unittest.mock import patch

from history_free import (
    EventParser, ServiceError, fetch_history, compare_events, forecast_from_history, year_ranges,
)


def history(year, events, scope='world'):
    return {'year': year, 'events': events, 'scope': scope}


class HistoryTests(unittest.TestCase):
    def test_only_real_events_section_and_nested_dates(self):
        parser = EventParser()
        parser.feed('''<h2>概要</h2><ul><li>除外される情報</li></ul>
            <h2>できごと</h2><ul><li>1月<ul><li>1日 - 鉄道が開通<sup>[1]</sup></li></ul></li>
            <li>2月1日 - 映画が公開</li></ul><h2>フィクションのできごと</h2>
            <ul><li>架空の出来事は除外</li></ul>''')
        self.assertEqual(parser.events, ['1月 1日 - 鉄道が開通', '2月1日 - 映画が公開'])

    @patch('history_free.read_json')
    def test_scope_sources_and_refetch_without_cache(self, read):
        read.return_value = {'parse': {'text': '<h2>出来事</h2><ul><li>1月1日 - 鉄道が開通</li></ul>', 'revid': 10}}
        japan = fetch_history(1966, 'japan')
        self.assertEqual(japan['title'], '1966年の日本')
        world = fetch_history(1966, 'world')
        self.assertEqual(world['title'], '1966年')
        self.assertEqual(read.call_count, 2)
        self.assertTrue(world['revision_url'].endswith('oldid=10'))

    @patch('history_free.read_json')
    def test_sample_covers_end_of_year(self, read):
        html = '<h2>出来事</h2><ul>' + ''.join(f'<li>出来事番号{i:03d} - 説明文</li>' for i in range(100)) + '</ul>'
        read.return_value = {'parse': {'text': html}}
        result = fetch_history(1966)
        self.assertEqual(len(result['events']), 36)
        self.assertIn('000', result['events'][0])
        self.assertIn('099', result['events'][-1])

    @patch('history_free.read_json', return_value={'error': {}})
    def test_missing_history_never_invented(self, read):
        with self.assertRaises(ServiceError):
            fetch_history(1966)


class ComparisonTests(unittest.TestCase):
    def test_ranges_roll_forward_and_never_compare_with_current_year(self):
        for year in (2026, 2027, 2030):
            years, forecast = year_ranges(year)
            self.assertEqual(len(years), 20)
            self.assertEqual(years[0], year - 80)
            self.assertEqual(years[-1], year - 61)
            self.assertEqual(forecast, year - 60)
            self.assertTrue(all(y + 60 < year for y in years))

    def test_exact_sixty_years_shared_theme_and_no_duplicate_pair(self):
        past = history(1965, ['鉄道が開通した', '映画を公開した'])
        later = history(2025, ['鉄道の新路線が開通', '新しい映画が公開'])
        pairs = compare_events(past, later)
        self.assertEqual(len(pairs), 2)
        self.assertIn('交通・インフラ', pairs[0]['themes'])
        self.assertEqual(len({p['later'] for p in pairs}), 2)
        with self.assertRaises(ValueError):
            compare_events(past, history(2026, later['events']))

    def test_unrelated_events_not_forced_into_pairs(self):
        self.assertEqual(compare_events(history(1965, ['映画が公開']), history(2025, ['銀行が合併'])), [])

    def test_forecast_uses_only_sixty_year_old_evidence_and_current_year(self):
        for year in (2026, 2027):
            japan = history(year - 60, ['鉄道が開通', '新幹線を整備', '映画を公開'], 'japan')
            results = forecast_from_history(year, japan)
            self.assertEqual(results[0]['theme'], '交通・インフラ')
            self.assertEqual(results[0]['year'], year)
            self.assertIn(str(year), results[0]['prediction'])
            self.assertTrue(all(event in japan['events'] for result in results for event in result['evidence']))
        with self.assertRaises(ValueError):
            forecast_from_history(2026, history(1965, ['鉄道が開通']))

    def test_no_classifiable_evidence_means_no_forecast(self):
        self.assertEqual(forecast_from_history(2026, history(1966, ['分類できない文章'])), [])


if __name__ == '__main__':
    unittest.main()
