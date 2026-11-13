from __future__ import annotations
from pathlib import Path
import time,platform
from importlib.metadata import version
from .common import run_process


class HFModel:
    def __init__(self,spec,config):
        if config['dtype']!='float16' or config['do_sample'] is not False:
            raise ValueError('v1 supports only the declared FP16 greedy profile')
        import torch
        from transformers import AutoTokenizer,AutoModelForCausalLM,GenerationConfig
        if not torch.cuda.is_available(): raise ValueError('CUDA is required for this FP16 inference profile')
        if torch.cuda.get_device_properties(0).total_memory < 22*1024**3:
            raise ValueError('FP16 profile requires >=22 GiB reported VRAM. Do not silently change quantization.')
        if torch.cuda.mem_get_info(0)[0] < 20*1024**3:
            raise ValueError('Less than 20 GiB free VRAM; stop competing jobs before model loading')
        self.torch=torch; self.spec=spec; self.config=config
        torch.manual_seed(config['seed']); torch.cuda.manual_seed_all(config['seed'])
        torch.backends.cudnn.benchmark=False
        self.tokenizer=AutoTokenizer.from_pretrained(spec['id'],revision=spec['revision'],trust_remote_code=False)
        self.model=AutoModelForCausalLM.from_pretrained(spec['id'],revision=spec['revision'],
             trust_remote_code=False,torch_dtype=torch.float16,device_map={'':'cuda:0'},attn_implementation='sdpa')
        self.model.eval()
        resolved=getattr(self.model.config,'_commit_hash',None)
        if resolved and resolved!=spec['revision']: raise ValueError('Resolved model revision differs from lock')
        driver=run_process(['nvidia-smi','--query-gpu=driver_version','--format=csv,noheader'],10).stdout.strip()
        eos=self.model.generation_config.eos_token_id or self.tokenizer.eos_token_id
        pad=self.tokenizer.pad_token_id if self.tokenizer.pad_token_id is not None else (eos[0] if isinstance(eos,list) else eos)
        self.generation_config=GenerationConfig(do_sample=False,num_beams=config['num_beams'],
            repetition_penalty=config['repetition_penalty'],no_repeat_ngram_size=config['no_repeat_ngram_size'],
            max_new_tokens=config['max_new_tokens'],bos_token_id=self.model.generation_config.bos_token_id,
            eos_token_id=eos,pad_token_id=pad,use_cache=True)
        self.info={'effective_generation_config':self.generation_config.to_dict(),'model':spec,'dtype':'float16','quantization':None,'torch':torch.__version__,
                   'transformers':version('transformers'),'cuda':torch.version.cuda,
                   'gpu':torch.cuda.get_device_name(0),'driver':driver,'resolved_revision':resolved,'python':platform.python_version()}

    def generate(self,prompt):
        torch=self.torch; tok=self.tokenizer; cfg=self.config
        if self.spec['template']=='chat':
            wire=tok.apply_chat_template([{'role':'user','content':prompt}],tokenize=False,add_generation_prompt=True)
        else: wire='<s>[INST] '+prompt+' [/INST]'
        inputs=tok(wire,return_tensors='pt',add_special_tokens=False).to('cuda:0')
        n=inputs['input_ids'].shape[1]
        if n>cfg['max_input_tokens']: raise ValueError('Prompt exceeds frozen token budget')
        eos=self.generation_config.eos_token_id
        torch.cuda.synchronize(); start=time.monotonic()
        with torch.inference_mode():
            output=self.model.generate(**inputs,generation_config=self.generation_config,
                max_time=cfg['max_generation_seconds'])
        torch.cuda.synchronize(); elapsed=time.monotonic()-start
        ids=output[0,n:].tolist()
        text=tok.decode(ids,skip_special_tokens=True)
        ended=bool(ids and (ids[-1] in eos if isinstance(eos,list) else ids[-1]==eos))
        return {'raw':text,'prompt_tokens':n,'output_tokens':len(ids),'seconds':elapsed,
                'error':None if ended else 'generation_stopped_without_eos',
                'note':'Generation max_time is a soft per-step limit; token limit is also enforced.'}
