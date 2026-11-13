# Licenses and provenance

Project code, prompts, and the authored development/test LLVM IR examples are
licensed under Apache-2.0. The `mutant.ll` files are deliberately incorrect,
human-authored validator fixtures, not observed model outputs.

Dependencies retain their own licenses. LLVM uses Apache-2.0 WITH LLVM-exception;
Alive2 uses MIT; Z3 uses MIT. See the upstream repositories for notices.

## Models

- `Qwen/Qwen2.5-Coder-7B-Instruct`: Apache-2.0, subject to its upstream files.
- `facebook/llm-compiler-7b`: Meta LLM Compiler License Agreement, not this
  repository's Apache-2.0 license. Access currently requires Meta approval.

Built with LLM Compiler (the project includes an adapter for that model).
Official terms: https://huggingface.co/facebook/llm-compiler-7b

The Meta terms restrict using its materials, outputs or results to improve other
large language models. Do not relabel Meta model outputs as unrestricted training
data. No weights, access credentials, or third-party training datasets are
included here. Raw model outputs remain local under the ignored `results/`
directory until their provenance and applicable release terms are reviewed.
Do not use one model's generated answers as the other model's few-shot examples.
All shared few-shot answers here were authored as development fixtures.

## Presentation draft

The classroom PPTX includes cited third-party research figures in its older background slides. Those materials retain their original rights and are not relicensed under this project's Apache-2.0 license. See slides/README.md and the slide notes for context.
