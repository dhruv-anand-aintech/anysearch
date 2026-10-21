import importlib.util
import json
import unittest
import tempfile
import subprocess
from unittest.mock import patch
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
check=module('check','scripts/check_search_research.py')
change=module('change','scripts/generate_matrix_changelog.py')
data=module('data','docs/tools/search_matrix/data_utils.py')
class PipelineTests(unittest.TestCase):
    def test_review_expiry_and_future_dates(self):
        audit=json.loads((ROOT/'docs/tools/search_matrix/research.json').read_text())
        self.assertEqual(check.validate_research(audit,today=date(2026,10,21)),[])
        self.assertTrue(check.validate_research(audit,today=date(2027,1,1)))
        self.assertTrue(check.validate_research(audit,today=date(2026,1,1)))
    def test_new_provider_has_cell_target(self):
        row={'name':'DeepSeek','links':{'slug':'deepseek'},'requires_key':{'support':'unknown'}}
        items=change.changes_for_pair(None,row,row,{})
        self.assertEqual(items,[{'summary':'DeepSeek added to the comparison','target':'cell-deepseek-requires-key'}])
    def test_evidence_not_fabricated_as_product_history(self):
        row={'name':'X','links':{'slug':'x'},'evidence':{'checked_at':'2026-10-21'}}
        self.assertEqual(change.changes_for_pair({**row,'evidence':{}},row,row,{}),[])
    def test_untracked_provider_is_in_changelog(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); matrix=root/'matrix';(matrix/'data').mkdir(parents=True)
            def git(*args):
                subprocess.run(['git',*args],cwd=root,check=True,capture_output=True)
            git('init');git('config','user.email','test@example.invalid');git('config','user.name','Test')
            (matrix/'schema.json').write_text('{"properties":{}}')
            git('add','.');git('commit','-m','fixture')
            (matrix/'data/new.json').write_text(json.dumps({'name':'New','links':{'slug':'new'},'requires_key':{'support':'unknown'}}))
            with patch.object(change,'ROOT',root), patch('sys.argv',['changelog','--matrix-dir','matrix']):change.main()
            history=json.loads((matrix/'changelog.json').read_text())
            self.assertEqual(history['entry_count'],1)
            self.assertEqual(history['entries'][0]['items'][0]['target'],'cell-new-requires-key')
    def test_generated_coverage_and_comparison_only(self):
        rows=json.loads((ROOT/'docs/tools/search_matrix/bundle.json').read_text())
        self.assertTrue(any(r['links']['slug']=='deepseek' and r['comparison_only'] for r in rows))
        for row in rows:
            self.assertRegex(row['checked_at']['value'],r'^\d{4}-\d{2}-\d{2}$')
            self.assertTrue(row['evidence']['source_urls'])
        self.assertEqual(json.loads((ROOT/'docs/tools/search_matrix/updated.json').read_text())['updated_at'],'2026-10-21T00:00:00Z')
if __name__=='__main__':unittest.main()
