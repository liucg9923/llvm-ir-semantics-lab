# Excluded during validator preflight

These authored files were originally considered for the main set. The pinned
Alive2 historical version reported `Unsupported attribute: noalias` for the
source and reference. No model results had been collected at this point.

The main case now uses explicitly adjacent nonoverlapping locations (`l2_disjoint`)
instead of an unsupported parameter attribute. This preserves a provable alias
comparison without silently discarding semantic assumptions. These files are
not in tasks/manifest.json and must not enter the main denominator.
