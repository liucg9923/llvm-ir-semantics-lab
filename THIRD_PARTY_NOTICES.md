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

## Report fonts and current model outputs

Report fonts are derived from Google Fonts Noto Sans SC, distributed under SIL Open Font License 1.1. Source revision and hashes are recorded in configs/report-fonts.json. Font software is not relicensed as Apache-2.0; documents generated using the fonts are not subject to the font-license inheritance requirement.

The current published LLM records are Qwen outputs on the project's authored IR examples, with exact prompts and model revision retained for evaluation provenance. Qwen's upstream model license is Apache-2.0. The earlier experiment-v2 bundle contains no Meta outputs. The later compiler-ftd-v1 bundle includes evaluation outputs from the community F16 GGUF conversion, with its provenance and Meta terms retained; it contains no model weights.

## Community FTD experiment

Built with LLM Compiler. The community checkpoint `second-state/llm-compiler-7b-ftd-GGUF` attributes its source to `facebook/llm-compiler-7b-ftd`. Model materials and associated outputs/results are subject to the [Meta LLM Compiler License Agreement](https://huggingface.co/facebook/llm-compiler-7b-ftd), not an unrestricted training-data grant under this project's Apache-2.0 code license. The published records are for inspecting and reproducing this evaluation; do not use them to improve other large language models contrary to the Meta terms.

LLM Compiler is licensed under the LLM Compiler License, Copyright © Meta Platforms, Inc. All Rights Reserved.

The source file, community revision and exact hash are recorded in configs/compiler-ftd.json. No weights are redistributed, and the original gated checkpoint is not claimed to have been downloaded. llama.cpp is MIT licensed; its pinned source is linked in configs/llama-cpp.json.
