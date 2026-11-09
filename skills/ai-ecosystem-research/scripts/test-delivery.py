"""Contract tests for the delivery gate, using disposable research fixtures."""
import importlib.util,json,tempfile,unittest,copy
from pathlib import Path
spec=importlib.util.spec_from_file_location('gate',Path(__file__).with_name('check-delivery.py'))
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)

class DeliveryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.run=Path(self.tmp.name)
  self.a={'mode':'weekly','artifact_status':'ready','delivery_ready':True,'unresolved':[],
   'requirements':[{'id':i,'status':'pass','evidence':'review.md'} for i in gate.REQUIRED|{'nine_layers','rankings'}]}
  self.e=[{'id':'E1','claim':'A documented behavior','url':'https://example.org/source','title':'Source','publisher':'Author','retrieved_at':'2000-01-01','evidence_type':'primary','locator':'Section 1'}]
  self.c=[{'claim':'A documented behavior','evidence_ids':['E1']}]
  for n in ['report.md','report-dark.html','coverage.md']:(self.run/n).write_text('fixture')
 def tearDown(self):self.tmp.cleanup()
 def result(self):
  for n,x in [('acceptance.json',self.a),('evidence.json',self.e),('report-claims.json',self.c)]:
   (self.run/n).write_text(json.dumps(x))
  return gate.check(self.run)
 def test_valid_weekly(self):self.assertEqual(self.result(),[])
 def test_draft_rejected(self):self.a['artifact_status']='draft';self.assertTrue(self.result())
 def test_empty_acceptance_rejected(self):self.a={};self.assertTrue(self.result())
 def test_missing_semantic_review(self):self.a['requirements']=[r for r in self.a['requirements'] if r['id']!='semantic_review'];self.assertTrue(self.result())
 def test_unknown_evidence(self):self.c[0]['evidence_ids']=['missing'];self.assertTrue(self.result())
 def test_unread_cannot_be_excused(self):self.a['unresolved']=[{'type':'not_read','blocking':False,'attempts':['x'],'impact':'x'}];self.assertTrue(self.result())
 def test_real_source_limit(self):self.a['unresolved']=[{'type':'unavailable_history','blocking':False,'attempts':['archive checked'],'impact':'no historical delta'}];self.assertEqual(self.result(),[])
 def test_duplicate_evidence(self):self.e*=2;self.assertTrue(self.result())
 def test_bad_record_types(self):self.e=[None];self.c=[None];self.assertTrue(self.result())
 def test_monthly_needs_longitudinal_review(self):self.a['mode']='monthly';self.assertTrue(self.result())
 def test_valid_monthly(self):
  self.a['mode']='monthly';self.a['requirements'] += [{'id':i,'status':'pass','evidence':'review.json'} for i in ['longitudinal_review','judgment_revision']]
  (self.run/'review.json').write_text('[{"review_status":"reviewed"}]');self.assertEqual(self.result(),[])
 def test_deep_dive_does_not_require_rankings(self):
  self.a['mode']='deep-dive';self.a['requirements']=[r for r in self.a['requirements'] if r['id'] not in ['nine_layers','rankings']]+[{'id':'research_question','status':'pass','evidence':'review.md'}];self.assertEqual(self.result(),[])

if __name__=='__main__':unittest.main()
