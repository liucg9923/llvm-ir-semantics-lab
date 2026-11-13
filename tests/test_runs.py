import json,os,shutil,tempfile,unittest
from pathlib import Path
from irsem.tasks import freeze
from irsem.runs import generate,evaluate_run
from irsem.report import report
ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(os.environ.get('IRSEM_NATIVE_TESTS')=='1','Requires cloud validator tools')
class RunIntegrationTests(unittest.TestCase):
    def test_missing_generation_is_in_denominator_and_fixture_stays_labeled(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            for name in ['tasks','configs']: shutil.copytree(ROOT/name,p/name)
            freeze(p)
            out=p/'run'
            generate(p,out,'identity',split='dev',smoke=True)
            removed=out/'candidates/dev_l0_xor_self/generation.json'; removed.unlink()
            rows=evaluate_run(p,out)
            self.assertEqual(len(rows),6)
            self.assertTrue(all(r['unchanged'] for r in rows if r['status']!='generation_error'))
            self.assertEqual(sum(r['status']=='generation_error' for r in rows),1)
            summary=report([out],p/'report')
            self.assertEqual(sum(s['n'] for s in summary),6)
            self.assertTrue(all(s['mode']=='fixture' for s in summary))
            self.assertEqual(sum(s['effective_optimizations'] for s in summary),0)
