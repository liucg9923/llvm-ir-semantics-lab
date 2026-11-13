# FTD community checkpoint supplement to protocol v2

Requested by the project owner after the official Meta access request remained pending: use `second-state/llm-compiler-7b-ftd-GGUF` as the dedicated compiler-model entrant. This is FTD, not the previously planned foundation checkpoint. The public community repository also offers an F16 file. F16 was selected before any inference because the cloud GPU and disk can hold it, avoiding the extra Q4/Q5 quantization confound against the existing Qwen FP16 run.

Pinned source: revision `3255d79430715ef149898cbb88cfeb7cb3b061a1`, file `llm-compiler-7b-ftd-f16.gguf`, size 13,478,104,960 bytes, SHA-256 `b1f75d4f55656dbc7b2052f06d1eb1eaf99ed5d7aaf306f520e72136bd98f829`. The upstream identity is the community publisher's attribution; bitwise equality to the gated upstream checkpoint is not independently established. Neither model weights nor login credentials are published.

The original dataset lock, experiment settings, task prompts, examples, task pipelines and optimization goals remain unchanged. New model/runtime descriptors have a separate supplement lock. Both LLMs receive the exact same task-prompt text; Qwen uses its checkpoint chat template, FTD uses the already planned `<s>[INST] ... [/INST]` template with one BOS. FTD is evaluated as a direct IR generator in this fixed interface. Its advertised downstream training targets include pass selection and disassembly, so this is not a reproduction of the paper's code-size/pass-selection benchmark and cannot identify a pure specialization effect.

Runtime: pinned llama.cpp b4514 on CUDA, F16 weights and KV cache, all layers on GPU, one slot, 6144 context (4096 prompt + 2048 output), explicit greedy decoding, repetition penalty 1, no grammar constraints, no repair and no extra stop strings. EOS is required as in the HF adapter. Native prediction timing has a soft limit after the first newline; the HTTP guard adds 30 seconds. Backend kernels, tokenizer and timing behavior differ from Transformers even though both profiles use FP16.

Plan: one six-case development run for loading/tokenization/interface checks, then one 24-case formal run, then the same predefined 12 cases with one independent self-review and one tool-feedback attempt. Development outputs are not formal scores. Do not select a prompt, quantization or checkpoint based on formal results. Preserve all candidates and failures.

The shared runner changes only to add the GGUF backend. The oracle implementation remains unchanged. Reaccept all 90 fixtures and rerun the exact existing LLVM/Qwen/identity raw candidates under the new receipt, without new model calls; compare their statuses, constraints and optimization outcomes with the published v2 records. All formal scores in the new comparison use the same evaluator code hash.

Official card: https://huggingface.co/facebook/llm-compiler-7b-ftd
Community conversion: https://huggingface.co/second-state/llm-compiler-7b-ftd-GGUF
Pinned runtime: https://github.com/ggml-org/llama.cpp/tree/ec7f3ac9ab33e46b136eb5ab6a76c4d81f57c7f1
