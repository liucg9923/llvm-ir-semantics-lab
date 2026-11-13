# Provenance and implementation notes

This campaign supplements, rather than overwrites, experiment-v2. The owner explicitly selected the community FTD repository. The file is F16, not Q4/Q5; the original official foundation model was not run. Hugging Face metadata confirms the community repository is ungated and pins the file hash. A matching community hash proves which file was used, not bitwise identity to the gated upstream original.

Source download was first attempted through the official endpoint and then an unauthenticated public mirror. Both sequential transfers were deliberately stopped for throughput, with their terminated statuses retained. The range transfer resumes the accumulated prefix, validates every HTTP Content-Range and finally verifies the entire file SHA-256. Aborted transfer stages are infrastructure records, not model failures.

The `[INST]` compiler-emulation template family is documented in Appendix B.1 of the original paper (https://arxiv.org/html/2407.02524v1). The shared evaluation prompt adds fixed constraints and two fixed developer examples. This is a fixed-interface transfer experiment, not an official benchmark reproduction. No prompt tuning was based on formal FTD results.

All compilation, weight storage, model inference, evaluation and plotting happen on the cloud host. The Mac is used only to issue SSH commands, inspect bounded outputs and publish reviewed artifacts with its existing GitHub authentication. No model weights or environment was installed on the Mac.

The native test suite was also run via unittest, matching the GitHub CI discovery mechanism. Native tests run on the cloud host; GitHub CI deliberately skips them and checks code, dataset/supplement integrity and evidence checksums without GPU or model credentials.

## Post-hoc diagnostics, outside formal denominators

After the dev and formal outputs showed example contamination and contract failures, a separate six-case development-only diagnostic removed the few-shot examples while preserving RULES, Current task, task_request, model/runtime and decoding settings. No formal prompt or score was changed. This is an exploratory prompt-sensitivity observation, not a tuned replacement benchmark.

A single exact initial FTD output for l0_add_fold was replayed natively under the same sandbox, without removing attributes, metadata or target settings. Its function has the same integer signature and no external calls. Input 0 gave source 9 and candidate 11. This post-hoc concrete counterexample is stored separately; the formal pipeline still labels this candidate contract_violation because it stops before semantic evaluation when the declared contract fails. It must not be silently counted as an extra formal refutation.

The last three slow download chunks were retried through fresh range connections. The final complete-file SHA-256 matched. The aborted download stage and successful resumed stage remain in the infrastructure log.
