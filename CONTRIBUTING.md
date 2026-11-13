# Contributing

This is an educational experiment, not a general LLVM optimizer benchmark.

1. Keep examples original and document their defined input domain and provenance.
2. Add paired cases and an independently reasoned reference/mutant when extending tasks.
3. Run core tests, LLVM syntax checks, native counterexample tests and Alive2 acceptance.
4. Do not select/remove cases based on a model's success or failure. Changing tasks or
   prompts creates a new frozen dataset version and requires new runs.
5. Preserve raw responses and all failure/unknown categories. Do not repair model IR
   before scoring or discard cases that did not parse.
6. Never commit access credentials, model weights, caches or third-party outputs under
   the project's permissive license. See THIRD_PARTY_NOTICES.md.

Use `make unit` for small code changes. Use `IRSEM_NATIVE_TESTS=1 make unit` on the
Linux validator host for execution checks, then `make accept` for the full oracle check.
Record both the project revision/source hash and dataset lock hash when publishing results.
