"""Pinned, local-only llama.cpp completion adapter for the community FTD checkpoint."""
from __future__ import annotations
import atexit,json,socket,subprocess,time,urllib.request,urllib.error
from pathlib import Path
from .common import digest,read_json,run_process


def check_supplement(root):
    lock=read_json(root/'configs/compiler-ftd.lock.json')
    for name,sha in lock['files'].items():
        if digest(root/name)!=sha:raise ValueError('FTD supplement changed since freeze: '+name)
    return lock


def completion_payload(tokens,cfg):
    return {'prompt':tokens,'n_predict':cfg['max_new_tokens'],'temperature':0.0,
        'seed':cfg['seed'],'top_k':1,'top_p':1.0,'min_p':0.0,'typical_p':1.0,
        'repeat_penalty':1.0,'repeat_last_n':0,'presence_penalty':0.0,
        'frequency_penalty':0.0,'dry_multiplier':0.0,'mirostat':0,
        'samplers':['temperature'],'stop':[],'ignore_eos':False,
        'cache_prompt':False,'stream':False,'return_tokens':True,
        't_max_predict_ms':int(cfg['max_generation_seconds']*1000)}


class GGUFModel:
    def __init__(self,spec,config):
        self.root=Path(__file__).resolve().parents[2];self.config=config;self.spec=spec;self.proc=None
        lock=check_supplement(self.root)
        if spec!=read_json(self.root/'configs/compiler-ftd.json'):raise ValueError('FTD model differs from frozen supplement')
        if config['dtype']!='float16' or config['do_sample'] is not False or config['repetition_penalty']!=1.0:
            raise ValueError('GGUF adapter requires the frozen FP16 greedy profile')
        report=read_json(self.root/'results/model-downloads/compiler-ftd-verified.json')
        if report['status']!='complete' or report['model']!=spec:raise ValueError('Checkpoint has not been verified')
        model=self.root/'.cache/huggingface/hub'/('models--'+spec['id'].replace('/','--'))/'snapshots'/spec['revision']/spec['filename']
        if model.stat().st_size!=spec['size'] or digest(model)!=spec['sha256']:raise ValueError('Checkpoint hash mismatch')
        runtime=read_json(self.root/'configs/llama-cpp.json');build=read_json(self.root/'results/campaign-ftd-v1/llama-build.json')
        if build['spec']!=runtime:raise ValueError('Runtime config differs from build receipt')
        binary=self.root/'.build/llama.cpp/build/bin/llama-server'
        if digest(binary)!=build['binary_sha256']:raise ValueError('llama-server binary changed')
        for path,sha in build['libraries'].items():
            if digest(self.root/path)!=sha:raise ValueError('Runtime library changed: '+path)
        free=run_process(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],10)
        if free.returncode or int(free.stdout.strip().splitlines()[0])<22000:raise ValueError('Need at least 22000MiB free GPU memory')
        with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        self.base=f'http://127.0.0.1:{port}'
        self.http=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        cmd=[str(binary),'--model',str(model),'--host','127.0.0.1','--port',str(port),
             '--ctx-size',str(runtime['context_size']),'--parallel','1','--n-gpu-layers',str(runtime['gpu_layers']),
             '--threads',str(runtime['threads']),'--batch-size',str(runtime['batch_size']),
             '--ubatch-size',str(runtime['ubatch_size']),'--cache-type-k','f16','--cache-type-v','f16',
             '--no-context-shift','--no-cont-batching']
        self.proc=subprocess.Popen(cmd,cwd=self.root,stdout=None,stderr=None)
        atexit.register(self.close)
        deadline=time.monotonic()+180
        while True:
            if self.proc.poll() is not None:raise ValueError('llama-server exited during startup; inspect stage log')
            try:
                if self._request('/health',None,2).get('status')=='ok':break
            except (OSError,ValueError):pass
            if time.monotonic()>deadline:self.close();raise ValueError('llama-server startup timed out')
            time.sleep(0.5)
        properties=self._request('/props',None,10)
        self.info={'model':spec,'dtype':'float16','quantization':None,'backend':'llama.cpp',
            'runtime':runtime,'runtime_build':build,'supplement_lock':lock,
            'server_properties':properties,'checkpoint_sha256':spec['sha256'],
            'gpu':run_process(['nvidia-smi','--query-gpu=name,driver_version','--format=csv,noheader'],10).stdout.strip(),
            'input_template':'<s>[INST] {prompt} [/INST]',
            'effective_generation_settings':completion_payload([],config),
            'time_limit_note':'llama.cpp prediction-phase soft limit after first newline; HTTP guard adds 30s. Not identical timing semantics to HF max_time.'}

    def _request(self,path,data,timeout):
        req=urllib.request.Request(self.base+path,data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json'})
        with self.http.open(req,timeout=timeout) as response:return json.load(response)

    def close(self):
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:self.proc.kill();self.proc.wait()

    def generate(self,prompt):
        wire='<s>[INST] '+prompt+' [/INST]'
        try:
            tokens=self._request('/tokenize',{'content':wire,'add_special':False},10)['tokens']
            # Llama BOS=1. Exactly one explicit BOS; token-array completions insert none.
            if not tokens or tokens[0]!=1 or tokens.count(1)!=1:raise ValueError('Unexpected BOS tokenization')
            if len(tokens)>self.config['max_input_tokens']:raise ValueError('Prompt exceeds frozen token budget')
            payload=completion_payload(tokens,self.config);start=time.monotonic()
            response=self._request('/completion',payload,self.config['max_generation_seconds']+30)
            elapsed=time.monotonic()-start
        except (OSError,urllib.error.URLError) as e:raise ValueError('Local GGUF inference transport error: '+str(e)) from e
        return {'raw':response.get('content',''),'prompt_tokens':len(tokens),
            'output_tokens':response.get('tokens_predicted'),'seconds':elapsed,
            'error':None if response.get('stop_type')=='eos' else 'generation_stopped_without_eos',
            'wire_prompt':wire,'input_token_ids':tokens,'output_token_ids':response.get('tokens',[]),
            'server_response':{k:v for k,v in response.items() if k not in {'content','prompt','tokens'}},
            'note':'Native completion API with exact token IDs, no chat-template inference, no grammar constraints, no repair.'}
