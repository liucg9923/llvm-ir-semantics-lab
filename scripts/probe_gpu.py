"""Tiny dependency/CUDA probe. Does not download or load an LLM."""
import json
from importlib.metadata import version
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
if not torch.cuda.is_available(): raise SystemExit('CUDA unavailable')
a=torch.ones((256,256),device='cuda',dtype=torch.float16)
b=a@a
torch.cuda.synchronize()
assert float(b[0,0])==256.0
print(json.dumps({'torch':torch.__version__,'transformers':version('transformers'),
 'accelerate':version('accelerate'),'cuda':torch.version.cuda,
 'gpu':torch.cuda.get_device_name(0),'vram_bytes':torch.cuda.get_device_properties(0).total_memory,
 'tiny_cuda_check':'passed','model_inference_tested':False},indent=2))
