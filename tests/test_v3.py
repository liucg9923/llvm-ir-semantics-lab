import unittest
from pathlib import Path
from unittest.mock import patch
from irsem.v3.extract import extract
from irsem.v3.control import gate
from irsem.v3.selection import require_selection
ROOT=Path(__file__).resolve().parents[1]

class V3Controls(unittest.TestCase):
 def test_nested_single_container_is_formatting_only(self):
  ir='define i32 @f(i32 %x) {\n ret i32 %x\n}\n'
  got,form=extract('Answer:\n```llvm\n<code>\n'+ir+'</code>\n```')
  self.assertEqual(got,ir);self.assertEqual(form,['fence','code_tag'])
 def test_multiple_candidates_are_never_selected_by_quality(self):
  with self.assertRaises(ValueError):extract('<code>define i32 @f(){ret i32 0}</code><code>define i32 @f(){ret i32 1}</code>')
 def records(self):
  ids=['dev_l0_xor_self','dev_l0_and_all','dev_l1_select_equal','dev_l1_unreachable','dev_l2_forward','dev_l2_alloca']
  return [{'task_id':x,'level':'L'+str(i//2),'determinate':True,'verified':False} for i,x in enumerate(ids)]
 def test_refutations_can_pass_interface_gate(self):
  g=gate(ROOT,self.records(),[{'error':None}]*6)
  self.assertTrue(g['passed']);self.assertEqual(g['verified'],0)
 def test_zero_coverage_blocks_formal_comparison(self):
  r=self.records()
  for x in r:x['determinate']=False
  self.assertFalse(gate(ROOT,r,[{'error':None}]*6)['passed'])
 def test_scalar_l2_does_not_substitute_for_pointer_coverage(self):
  r=self.records();r[4]['determinate']=False
  self.assertFalse(gate(ROOT,r,[{'error':None}]*6)['passed'])
 def test_bare_passed_flag_is_not_evidence(self):
  data={'protocol_sha256':'same','primary_passed':True,'primary_evidence':[]}
  with patch('irsem.v3.selection.read_json',return_value=data),patch('irsem.v3.selection.require_frozen',return_value={'sha256':'same'}):
   with self.assertRaisesRegex(ValueError,'Both independently'):require_selection(ROOT)
