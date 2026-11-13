# Run artifacts

All runs except this README are ignored by Git by default. A run contains a
manifest, exact prompts, raw outputs, generation metadata, per-task verifier
logs, counterexamples and aggregate results. A partially generated run remains
explicitly incomplete; never replace missing entries with successes.

`mode=fixture` and `mode=smoke` are infrastructure checks, not model benchmark
results. The publishing workflow should select and inspect artifacts, preserve
model-specific terms, and exclude credentials/caches/weights.

当前三方补充实验：[compiler-ftd-v1](published/compiler-ftd-v1/README.md)。原 Qwen 发布版保留，不覆盖。

当前受控重跑：[controlled-v3](published/controlled-v3/README.md)。历史版本保留，不能跨协议直接计算能力提升率。
