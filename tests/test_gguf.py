import tempfile,unittest
from pathlib import Path
from irsem.gguf import completion_payload,check_supplement
from irsem.common import digest,write_json

class GGUFProtocolTests(unittest.TestCase):
    def test_sampler_is_explicit_greedy_and_no_hidden_penalties(self):
        cfg={'max_new_tokens':2048,'seed':20261112,'max_generation_seconds':120}
        r=completion_payload([1,42],cfg)
        self.assertEqual(r['prompt'],[1,42]);self.assertEqual(r['temperature'],0)
        self.assertEqual(r['samplers'],['temperature']);self.assertEqual(r['repeat_penalty'],1)
        self.assertEqual(r['presence_penalty'],0);self.assertEqual(r['frequency_penalty'],0)
        self.assertEqual(r['stop'],[]);self.assertFalse(r['ignore_eos']);self.assertFalse(r['cache_prompt'])
        self.assertEqual(r['n_predict'],2048);self.assertEqual(r['t_max_predict_ms'],120000)

    def test_supplement_rejects_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'configs/compiler-ftd.json';p.parent.mkdir();p.write_text('{}')
            write_json(root/'configs/compiler-ftd.lock.json',{'files':{'configs/compiler-ftd.json':digest(p)}})
            check_supplement(root);p.write_text('{"changed":true}')
            with self.assertRaisesRegex(ValueError,'changed since freeze'):check_supplement(root)
