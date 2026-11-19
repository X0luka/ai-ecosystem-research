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

    def test_auto_route_failure_retry_and_unmatched(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            meta = dict(coverage_targets={'papers':'限定论文清单'}, coverage_routes={'papers':['https://example.org/list']},
                        window_start=self.window[0], window_end=self.window[1])
            (run/'run.json').write_text(json.dumps(meta), encoding='utf-8')
            flow.initialize(run)
            store = flow.Store(run)
            self.addCleanup(store.close)
            def begin(key, url, **extra):
                return store.apply('begin', dict(id=key,tool='http',purpose='inspect',url=url,**extra))
            self.assertEqual(begin('A','https://example.org/list?page=1')['coverage_targets'], ['papers'])
            store.apply('finish', dict(id='A',status='failed',error='403'))
            self.assertEqual(audit.export(run)['targets']['papers']['status'],'failed')
            self.assertEqual(begin('B','https://other.example/list',parent_id='A')['coverage_targets'], ['papers'])
            store.apply('finish', dict(id='B',status='ok'), b'entries')
            store.apply('coverage-review',dict(id='B',target='papers',window=self.window,material='original',
                        excerpt='entries',alternative_for='A',impact='limited to the scoped list',complete=True))
            self.assertEqual(audit.export(run)['targets']['papers']['status'],'verified')
            self.assertNotIn('coverage_targets', begin('C','https://example.org/listing'))
            store.close()

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
