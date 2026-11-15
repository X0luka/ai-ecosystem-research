import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

script=Path(__file__).resolve().parents[1]/'skills/ai-ecosystem-research/scripts/build-portal.py'
spec=importlib.util.spec_from_file_location('portal',script)
portal=importlib.util.module_from_spec(spec);spec.loader.exec_module(portal)

class PortalTests(unittest.TestCase):
    def test_ready_selection_legacy_and_relocation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'research'
            def report(name,end,ready):
                p=root/'runs'/name;p.mkdir(parents=True)
                (p/'report-dark.html').write_text('report')
                (p/'run.json').write_text(json.dumps({'mode':'weekly','window_start':'2030-01-01','window_end':end}))
                (p/'acceptance.json').write_text(json.dumps({'artifact_status':'ready' if ready else 'draft','delivery_ready':ready}))
            report('older','2030-01-08',True)
            report('newer draft','2030-01-15',False)
            monthly=root/'runs'/'legacy';monthly.mkdir();(monthly/'report-dark.html').write_text('monthly')
            (root/'portal-legacy.json').write_text(json.dumps({'runs/legacy/report-dark.html':{'mode':'monthly','delivered':True,'date':'2029-12-31','title':'<script>example</script>','label':'历史交付'}}))
            rows,warnings=portal.build(root);html=(root/'index.html').read_text(encoding='utf-8')
            self.assertFalse(warnings)
            self.assertIn('href="runs/older/report-dark.html"',html.split('历史报告')[0])
            self.assertNotIn('href="runs/newer%20draft/report-dark.html"',html.split('<h3>历史报告')[0])
            self.assertIn('&lt;script&gt;',html)
            self.assertNotIn('<script>example',html)
            copied=Path(tmp)/'relocated';shutil.copytree(root,copied)
            portal.build(copied)
            self.assertEqual(html,(copied/'index.html').read_text(encoding='utf-8'))
            report('latest','2030-01-22',True);portal.build(root)
            self.assertIn('href="runs/latest/report-dark.html"',(root/'index.html').read_text(encoding='utf-8').split('<h3>历史报告')[0])
    def test_invalid_acceptance_is_not_promoted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'runs'/'bad';p.mkdir(parents=True)
            (p/'report-dark.html').write_text('bad')
            (p/'run.json').write_text('{"mode":"weekly"}')
            (p/'acceptance.json').write_text('broken')
            rows,warnings=portal.build(root)
            self.assertEqual(rows,[]);self.assertTrue(warnings)

if __name__=='__main__':unittest.main()
