# Figure notes

All plots use the full fixed task set, with no exclusions. Initial comparisons have 24 cases per entrant/control and 12 declared opportunities. In each of L0/L1/L2 the corresponding denominators are 8 and 4. The feedback display uses the same predeclared 12 cases (6 opportunities) for each LLM, and shows all statuses and regressions.

FTD is the community F16 GGUF conversion of LLM Compiler 7B-FTD, run with llama.cpp. Qwen is the HF FP16 checkpoint run with Transformers. These are different checkpoint families, training objectives and runtime implementations; the comparison does not isolate specialization as a causal effect. The identity row is a no-change control, not a fourth competitor.

Panels a/b/c in the main figure separate entry legality, semantic correctness and verified useful optimization. Neither legal syntax nor an unchanged program proves useful optimization. Counts are descriptive, not estimates from a random sample of programs. There are no repeated independent seeds, confidence intervals or p-values.

The paired display shows actual task-level changes rather than comparing unlike denominators. Color is supplemented by text in every cell; * denotes verified goal completion. The two model panels share the same status encoding and task order.

The Python/Matplotlib exports are sized for classroom slides, with editable SVG/PDF text and 300 dpi PNG files. Source-data JSON files accompany each figure. All fonts are >=11 pt at the native export size. These exports do not claim a specific journal submission format.
