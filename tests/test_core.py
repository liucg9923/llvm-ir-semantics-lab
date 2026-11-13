import unittest,tempfile,shutil
from pathlib import Path
from irsem.common import ProcessResult,run_process
from irsem.ir import extract_ir,contract_errors,goal_met
from irsem.tasks import load_tasks,freeze,check_lock
from irsem.evaluate import alive_status,combine_status
from irsem.differential import input_cases
from irsem.report import summarize

ROOT=Path(__file__).resolve().parents[1]
TASKS={t.id:t for t in load_tasks(ROOT)}

class CoreTests(unittest.TestCase):
    def test_output_extraction_is_unambiguous(self):
        src=TASKS['l0_add_fold'].text()
        self.assertEqual(extract_ir('<code>'+src+'</code>'),src)
        self.assertEqual(extract_ir('```llvm\n'+src+'```'),src)
        for bad in ['no result','<code>'+src,'<code>'+src+'</code><code>unfinished','```llvm\n'+src+'```\n```llvm\n'+src+'```']:
            with self.assertRaises(ValueError): extract_ir(bad)

    def test_input_contract_cannot_be_strengthened(self):
        src=TASKS['l2_mayalias'].text()
        self.assertTrue(contract_errors(src,src.replace('ptr noundef','ptr noalias noundef')))
        self.assertTrue(contract_errors(src,src.replace('@f(', '@other(')))
        self.assertTrue(contract_errors(src,src.replace('x86_64-pc-linux-gnu','aarch64-linux-gnu')))
        self.assertFalse(contract_errors(src,src.replace('%p','%renamed')))
        noalias=src.replace('ptr noundef','ptr noalias noundef')
        self.assertFalse(contract_errors(noalias,noalias.replace('noalias noundef','noundef noalias')))

    def test_calls_and_loops_are_out_of_scope(self):
        src=TASKS['l0_add_fold'].text()
        loop=src.replace('  ret i32 %r','  br label %entry')
        self.assertTrue(any('Loops' in e for e in contract_errors(src,loop)))
        self.assertTrue(contract_errors(src,src.replace('  ret i32 %r','  call void @g()\n  ret i32 %r')))

    def test_alive2_requires_exact_coverage_not_exit_zero(self):
        def result(a,b,c,d,rc=0):
            return ProcessResult([],rc,f'Summary:\n  {a} correct transformations\n  {b} incorrect transformations\n  {c} failed-to-prove transformations\n  {d} Alive2 errors\n','',0)
        self.assertEqual(alive_status(result(1,0,0,0)),'verified')
        self.assertEqual(alive_status(result(0,1,0,0)),'refuted')
        self.assertEqual(alive_status(result(0,0,1,0)),'unknown')
        self.assertEqual(alive_status(result(0,0,0,0)),'tool_error')
        self.assertEqual(alive_status(result(1,0,0,0,1)),'tool_error')
        self.assertEqual(alive_status(ProcessResult([],None,'','',1,True)),'unknown')
        self.assertEqual(alive_status(ProcessResult([],0,'Transformation seems to be correct!','',0)),'tool_error')

    def test_all_authored_sources_references_and_mutants_follow_contract(self):
        for task in TASKS.values():
            for variant in ['source','reference','mutant']:
                with self.subTest(task=task.id,variant=variant):
                    self.assertEqual(contract_errors(task.text(),task.text(variant)),[])

    def test_identity_never_meets_an_opportunity_goal(self):
        for task in TASKS.values():
            if task.spec['role']=='opportunity':
                with self.subTest(task=task.id):
                    self.assertFalse(goal_met(task,task.text()))
                    self.assertTrue(goal_met(task,task.text('reference')))

    def test_inputs_obey_noalias_and_holdout_is_disjoint(self):
        for task in TASKS.values():
            with self.subTest(task=task.id):
                d=set(input_cases(task,'diagnostic')); h=set(input_cases(task,'holdout'))
                self.assertTrue(d); self.assertTrue(h); self.assertFalse(d & h)
                self.assertEqual(h,set(input_cases(task,'holdout')))
                if task.spec['noalias']: self.assertTrue(all(x[2]==0 for x in d|h))
                elif task.spec['abi']=='memory': self.assertEqual({x[2] for x in d|h},{0,1})
        self.assertIn((255,),input_cases(TASKS['l0_wrap'],'audit'))

    def test_report_denominators_include_failures_and_unknowns(self):
        rows=[dict(level='L0',arm='initial',role='opportunity',status=s,syntax_valid=s!='invalid_ir',
                   unchanged=s=='verified',effective_optimization=False) for s in ['verified','refuted','unknown','invalid_ir']]
        summary=summarize(rows)[0]
        self.assertEqual(summary['n'],4); self.assertEqual(summary['opportunities'],4)
        self.assertEqual(summary['effective_optimizations'],0); self.assertEqual(summary['refuted'],1)

    def test_lock_detects_case_and_config_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            shutil.copytree(ROOT/'tasks',p/'tasks'); shutil.copytree(ROOT/'configs',p/'configs')
            freeze(p); check_lock(p)
            f=p/'tasks/test/l0_wrap/source.ll'; f.write_text(f.read_text()+'; changed\n')
            with self.assertRaises(ValueError): check_lock(p)

    def test_formal_counterexample_survives_native_execution_failure(self):
        self.assertEqual(combine_status('refuted','execution_error'),'refuted')
        self.assertEqual(combine_status('refuted','match'),'refuted')
        self.assertEqual(combine_status('verified','mismatch'),'oracle_conflict')
        self.assertEqual(combine_status('unknown','match'),'tested_only')
        self.assertEqual(combine_status('verified','not_run'),'verification_only')

    def test_timeout_is_not_success(self):
        import sys
        r=run_process([sys.executable,'-c','import time; time.sleep(5)'],timeout=0.05)
        self.assertTrue(r.timed_out); self.assertNotEqual(r.returncode,0)

if __name__=='__main__': unittest.main()
