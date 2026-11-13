import os,unittest,tempfile,signal
from pathlib import Path
from irsem.tasks import load_tasks
from irsem.differential import compare
from irsem.evaluate import tool
from irsem.toolchain import configure
from irsem.common import run_process
from irsem.sandbox import C_SETUP
ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(os.environ.get('IRSEM_NATIVE_TESTS')=='1','Set IRSEM_NATIVE_TESTS=1 on the Linux validator host')
class NativeTests(unittest.TestCase):
    def test_known_references_match_and_mutants_have_observable_counterexamples(self):
        configure(ROOT)
        for task in load_tasks(ROOT):
            for variant,expected in [('reference','match'),('mutant','mismatch')]:
                with self.subTest(task=task.id,variant=variant):
                    result=compare(task,task.text(variant),tool('clang'),kind='audit',allow_execution=True)
                    self.assertEqual(result['status'],expected,result)

    def test_seccomp_blocks_network_creation(self):
        configure(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); src=p/'probe.c'; exe=p/'probe'
            src.write_text(C_SETUP+'\n#include <sys/socket.h>\nint main(void){irsem_sandbox(); return socket(AF_INET,SOCK_STREAM,0);}\n')
            build=run_process([tool('clang'),str(src),'-lseccomp','-o',str(exe)])
            self.assertEqual(build.returncode,0,build.stderr)
            result=run_process([str(exe)],5)
            self.assertEqual(result.returncode,-signal.SIGSYS)
