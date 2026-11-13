# Figure contract

Question: on the same bounded IR tasks, which generated transformations are legal, preserve semantics, and achieve the requested optimization; how do independent self-review and tool feedback change the same cases?

Evidence architecture: main quantitative grid separates legal syntax (entry check), validated semantics (correctness), and verified goal completion (usefulness). The paired-case figure exposes every predeclared repair/regression, with matched denominators, rather than hiding changes behind aggregate percentages.

Data: all 24 initial cases, all 12 feedback cases per model, no exclusions, no fabricated values. Identity is a control. Use fixed case order and exact numerator/denominator labels. Model and runtime differences are disclosed. No population generalization, statistical confidence intervals or pure-specialization claim.

Reuse: structural adaptation of the project's existing Python plots. The measured FTD row replaces the former pending placeholder; feedback expands to matched panels for both LLMs. Font, palette and export conventions remain consistent.

Backend/export: Python/Matplotlib, slide-sized canvases, editable SVG/PDF plus PNG at 300 dpi, >=11pt text. Measure comparable panel rectangles at 1.5pt tolerance before export. Run PDF font and collision checks and visually inspect each panel and the assembled figures after final rendering. Source-data tables and QA records accompany the figures.
