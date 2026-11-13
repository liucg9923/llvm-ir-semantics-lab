# Run artifacts

All runs except this README are ignored by Git by default. A run contains a
manifest, exact prompts, raw outputs, generation metadata, per-task verifier
logs, counterexamples and aggregate results. A partially generated run remains
explicitly incomplete; never replace missing entries with successes.

`mode=fixture` and `mode=smoke` are infrastructure checks, not model benchmark
results. The publishing workflow should select and inspect artifacts, preserve
model-specific terms, and exclude credentials/caches/weights.
