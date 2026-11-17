"""Behavior tests: restart, duplicate events, captured bytes and writing gates."""
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import research_flow as flow


def seed(run):
    flow.initialize(run)
    s = flow.Store(run)
    s.apply('begin', {'id': 'A1', 'tool': 'test', 'url': 'https://example.org/project',
                      'purpose': 'Read original source'})
    s.apply('finish', {'id': 'A1', 'status': 'ok'}, b'Original source: documented behavior.')
    s.apply('candidate', {'id': 'P1', 'entity_id': 'project', 'name': 'Example project',
                         'canonical_url': 'https://example.org/project', 'event_key': 'release-v1',
                         'event_type': 'update', 'decision': 'selected', 'reason': 'Relevant release',
                         'discovery_capture_ids': ['A1']})
    s.apply('evidence', {'id': 'E1', 'candidate_id': 'P1', 'capture_id': 'A1',
                        'claim': 'A documented behavior', 'title': 'Original source',
                        'publisher': 'Example author', 'evidence_type': 'primary_artifact',
                        'locator': 'Section 1'})
    s.apply('claim', {'id': 'C1', 'claim': 'A documented behavior', 'kind': 'fact',
                     'evidence_ids': ['E1'], 'quantitative': False,
                     'support_review': 'Section 1 explicitly describes this behavior.'})
    s.prewrite()
    (Path(run) / 'report.md').write_text('<!-- claim:C1 -->\nA documented behavior\n<!-- /claim:C1 -->', encoding='utf-8')
    return s


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.run = Path(self.temp.name)
        self.s = seed(self.run)

    def tearDown(self):
        self.s.close()
        self.temp.cleanup()

    def test_full_workflow(self):
        self.assertEqual(flow.check_writing(self.run), [])
        self.assertEqual((self.run / 'captures/A1.bin').read_bytes(),
                         b'Original source: documented behavior.')

    def test_restart_keeps_pending_capture(self):
        self.s.apply('begin', {'id': 'A2', 'tool': 'browser', 'url': 'https://example.org/next',
                               'purpose': 'Check a contradiction', 'parent_id': 'A1'})
        self.s.close()
        self.s = flow.Store(self.run)
        self.assertEqual(self.s.get('captures', 'A2')['status'], 'started')
        with self.assertRaises(ValueError):
            self.s.prewrite()
        self.s.apply('finish', {'id': 'A2', 'status': 'failed', 'error': 'Browser unavailable'})
        self.s.prewrite()
        self.assertEqual(flow.check_writing(self.run), [])

    def test_capture_id_does_not_overwrite(self):
        before = self.s.get('captures', 'A1')
        with self.assertRaises(ValueError):
            self.s.apply('finish', {'id': 'A1', 'status': 'ok'}, b'changed')
        self.assertEqual(self.s.get('captures', 'A1'), before)

    def test_failed_capture_cannot_support_evidence(self):
        self.s.apply('begin', {'id': 'A2', 'tool': 'http', 'url': 'https://example.org/no', 'purpose': 'Check'})
        self.s.apply('finish', {'id': 'A2', 'status': 'failed', 'error': '404'})
        e = dict(self.s.get('evidence', 'E1'), id='E2', capture_id='A2')
        with self.assertRaises(ValueError):
            self.s.apply('evidence', e)

    def test_no_retrospective_time_override(self):
        e = dict(self.s.get('evidence', 'E1'), id='E2', retrieved_at='1900-01-01')
        out = self.s.apply('evidence', e)
        self.assertEqual(out['retrieved_at'], self.s.get('captures', 'A1')['finished_at'])

    def test_duplicate_event_rejected_but_new_event_allowed(self):
        c = self.s.get('candidates', 'P1')
        with self.assertRaises(ValueError):
            self.s.apply('candidate', dict(c, id='P2'))
        self.s.apply('candidate', dict(c, id='P2', event_key='release-v2', decision='watch'))
        self.assertEqual(len(self.s.rows('candidates')), 2)

    def test_decision_history_and_receipt_invalidated(self):
        c = self.s.get('candidates', 'P1')
        self.s.apply('candidate', dict(c, decision='deferred', reason='Need independent test'))
        history = self.s.db.execute("SELECT payload FROM events WHERE kind='candidate'").fetchall()
        self.assertEqual([json.loads(x[0])['decision'] for x in history], ['selected', 'deferred'])
        self.assertTrue(flow.check_writing(self.run))
        with self.assertRaises(ValueError):
            self.s.prewrite()

    def test_selected_candidate_cannot_be_omitted(self):
        c = self.s.get('candidates', 'P1')
        self.s.apply('candidate', dict(c, id='P2', event_key='release-v2'))
        with self.assertRaises(ValueError):
            self.s.prewrite()

    def test_discovery_summary_not_core_evidence(self):
        self.s.apply('evidence', dict(self.s.get('evidence', 'E1'), id='E2', evidence_type='discovery_only'))
        with self.assertRaises(ValueError):
            self.s.apply('claim', dict(self.s.get('claims', 'C1'), id='C2', evidence_ids=['E2']))

    def test_unknown_reference_and_empty_review(self):
        for change in [{'evidence_ids': ['missing']}, {'support_review': ''}]:
            with self.assertRaises(ValueError):
                self.s.apply('claim', dict(self.s.get('claims', 'C1'), id='C2', **change))

    def test_numbers_require_scope(self):
        c = dict(self.s.get('claims', 'C1'), id='C2', quantitative=True)
        with self.assertRaises(ValueError):
            self.s.apply('claim', c)
        self.s.apply('claim', dict(c, metric_scope='Two saved snapshots; counts, not adoption.'))

    def test_modified_body_and_exports_rejected(self):
        (self.run / 'evidence.json').write_text('[]')
        self.assertTrue(flow.check_writing(self.run))
        self.s.prewrite()
        self.s.db.execute("UPDATE bodies SET content=? WHERE id='A1'", (b'changed',))
        self.s.db.commit()
        self.assertTrue(flow.check_writing(self.run))

    def test_missing_unknown_changed_or_duplicate_report_claim(self):
        for text in ['No markers', '<!-- claim:X -->A documented behavior',
                     '<!-- claim:C1 -->Unsupported text',
                     '<!-- claim:C1 -->A documented behavior\n<!-- claim:C1 -->other']:
            (self.run / 'report.md').write_text(text)
            self.assertTrue(flow.check_writing(self.run), text)

    def test_appended_words_inside_claim_are_rejected(self):
        (self.run / 'report.md').write_text('<!-- claim:C1 -->A documented behavior is false<!-- /claim:C1 -->')
        self.assertTrue(flow.check_writing(self.run))

    def test_claim_revision_preserves_old_statement_and_invalidates_receipt(self):
        old = self.s.get('claims', 'C1')
        new = self.s.apply('claim', dict(old, claim='A revised documented behavior'))
        self.assertEqual(new['revision'], 2)
        self.assertTrue(flow.check_writing(self.run))
        self.s.prewrite()
        self.assertTrue(flow.check_writing(self.run))
        (self.run / 'report.md').write_text('<!-- claim:C1 -->A revised documented behavior<!-- /claim:C1 -->')
        self.assertEqual(flow.check_writing(self.run), [])
        history = self.s.db.execute("SELECT payload FROM events WHERE kind='claim'").fetchall()
        self.assertEqual([json.loads(x[0])['claim'] for x in history],
                         ['A documented behavior', 'A revised documented behavior'])

    def test_claim_marker_in_table_cell(self):
        (self.run / 'report.md').write_text('| Project | Fact |\n|---|---|\n| Example | <!-- claim:C1 -->A documented behavior<!-- /claim:C1 --> |')
        self.assertEqual(flow.check_writing(self.run), [])

    def test_withdraw_claim_preserves_history_but_removes_from_report(self):
        self.s.apply('claim', dict(self.s.get('claims', 'C1'), id='C2', claim='Replacement statement'))
        self.s.apply('withdraw-claim', {'id': 'C1', 'reason': 'Original wording was too broad'})
        self.s.prewrite()
        self.assertFalse(self.s.get('claims', 'C1')['active'])
        self.assertEqual([c['id'] for c in self.s.public_rows('claims')], ['C2'])
        self.assertTrue(flow.check_writing(self.run))
        (self.run / 'report.md').write_text('<!-- claim:C2 -->Replacement statement<!-- /claim:C2 -->')
        self.assertEqual(flow.check_writing(self.run), [])

    def test_legacy_is_not_silently_upgraded(self):
        with self.assertRaises(ValueError):
            flow.initialize(self.run)
        with tempfile.TemporaryDirectory() as legacy:
            p = Path(legacy)
            (p / 'report.md').write_text('Historical report')
            self.assertTrue(flow.check_writing(p))
            with self.assertRaises(ValueError):
                flow.initialize(p)
            self.assertEqual((p / 'report.md').read_text(), 'Historical report')

    def test_real_http_success_failure_and_retry(self):
        calls = []
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                calls.append(self.path)
                self.send_response(404 if self.path == '/missing' else 200)
                self.end_headers()
                self.wfile.write(b'Local fixture response')
            def log_message(self, *_):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = 'http://127.0.0.1:' + str(server.server_port)
            flow.fetch(self.s, {'id': 'A2', 'url': base + '/ok', 'purpose': 'Integration fixture'})
            with self.assertRaises(Exception):
                flow.fetch(self.s, {'id': 'A2', 'url': base + '/ok', 'purpose': 'Duplicate'})
            self.assertEqual(calls, ['/ok'])
            with self.assertRaises(Exception):
                flow.fetch(self.s, {'id': 'A3', 'url': base + '/missing', 'purpose': 'Failure fixture'})
            self.assertEqual(self.s.get('captures', 'A3')['status'], 'failed')
            flow.fetch(self.s, {'id': 'A4', 'url': base + '/ok', 'purpose': 'Retry', 'parent_id': 'A3'})
            self.assertEqual(self.s.get('captures', 'A4')['parent_id'], 'A3')
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
