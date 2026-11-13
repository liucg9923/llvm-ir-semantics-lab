# Evidence bundle

The archive includes the immutable generated candidates and per-case evaluations, the revalidated prior outputs, toolchain acceptance, infrastructure stages, configurations, source code, figures, post-hoc diagnostic records and a complete per-file SHA-256 manifest. It excludes weights, credentials, caches and environment installations.

`FILES.sha256.json` is embedded in the archive. Verify without extraction with `scripts/verify_evidence.py`; `ARCHIVE.sha256` additionally identifies the entire compressed file. Aborted download stages document transport recovery and are not model failures.
