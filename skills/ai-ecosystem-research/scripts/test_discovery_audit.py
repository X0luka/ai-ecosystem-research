import json
import tempfile
import unittest
from pathlib import Path

import discovery_audit as audit
import research_flow as flow


class AuditTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.run = Path(tmp.name)
        self.window = ['2030-01-01', '2030-01-08']
        meta = dict(window_start=self.window[0], window_end=self.window[1])
        (self.run / 'run.json').write_text(json.dumps(meta))
        flow.initialize(self.run)
        self.store = flow.Store(self.run)
        self.addCleanup(self.store.close)

    def channel(self):
        audit.export(self.run)
        return json.loads((self.run / 'discovery-audit.json').read_text(encoding='utf-8'))['targets']['papers']

    def begin(self, key, **kwargs):
        data = dict(id=key, url='https://example.org/list', tool='http', purpose='test', coverage_targets=['papers'])
        self.store.apply('begin', dict(data, **kwargs))

    def review(self, key, **kwargs):
        self.store.apply('coverage-review', dict(dict(id=key, target='papers', window=self.window,
            material='original', excerpt='entries', complete=True, impact='Scoped source list checked'), **kwargs))

    def test_gap_failure_and_alternative(self):
        self.assertEqual(self.channel()['status'], 'unattempted')
        self.begin('A')
        self.store.apply('finish', dict(id='A', status='failed', error='timeout'))
        self.assertEqual(self.channel()['status'], 'failed')
        self.begin('B', parent_id='A', url='https://alternate.example/list')
        self.store.apply('finish', dict(id='B', status='ok'), b'entries')
        self.review('B', alternative_for='A')
        item = self.channel()
        self.assertEqual(item['status'], 'verified')
        self.assertEqual(item['attempts'][0]['reason'], 'timeout')
        self.assertEqual(item['attempts'][1]['review']['alternative_for'], 'A')

    def test_duplicate_and_wrong_window(self):
        for key in ['A', 'B']:
            self.begin(key)
            self.store.apply('finish', dict(id=key, status='ok'), b'entries')
            self.review(key, window=['2020-01-01','2020-01-08'])
        self.assertEqual(self.channel()['status'], 'partial')
        self.assertEqual(self.channel()['attempts'][1]['duplicate_of'], 'A')

    def test_search_overclaim(self):
        self.begin('A', tool='web', query='{"search_query":[{"q":"papers"}]}')
        self.store.apply('finish', dict(id='A', status='ok'), b'entries')
        self.review('A')
        self.assertEqual(self.channel()['status'], 'partial')

    def test_legacy_unknown(self):
        self.store.db.execute('DROP TABLE coverage_plan')
        self.store.db.commit()
        self.assertEqual(self.channel()['status'], 'unknown')

    def test_explicit_non_discovery_and_unclassified_requests(self):
        self.begin('A', coverage_targets=[])
        self.assertEqual(self.channel()['status'], 'unattempted')
        self.store.apply('begin', dict(id='B', tool='http', url='https://example.org', purpose='unclassified'))
        self.assertEqual(self.channel()['status'], 'unknown')

    def test_incomplete_original_and_missing_excerpt(self):
        self.begin('A')
        self.store.apply('finish', dict(id='A', status='ok'), b'entries')
        with self.assertRaises(ValueError):
            self.review('A', excerpt='missing')
        self.review('A', complete=False)
        self.assertEqual(self.channel()['status'], 'partial')


if __name__ == '__main__':
    unittest.main()
