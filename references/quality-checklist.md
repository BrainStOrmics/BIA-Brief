# Completion checklist

Confirm all of the following before reporting success:

## Files

- `report.md`, `report.pdf`, and `report.tex` exist.
- The PDF has at least one page and is not empty.
- The final PDF has been copied to `deliverables/` unless `--no-delivery-copy`
  was explicitly requested, and its file name matches the `报告名称` field in
  `project_info.md`.

## Content

- The report has a title, table of contents, methods, and analysis results.
- Figures referenced in the report exist and render without broken paths.
- Every figure in the report has a caption that describes what the figure
  shows, and the caption follows the figure.
- Figure numbering is continuous and starts at 图2 — 图1 is the static
  workflow figure supplied by the template.

## Visual

- Open the PDF and scroll through it; no page is blank or half-rendered.
- Figures sit on the page background without a visible white plate around
  them. A rectangle edge around every figure means the runtime is older than
  0.2.2, which used a `RGB(253, 253, 253)` sheet instead of pure white.
- The page background and the bottom wave decoration are present.
- Chinese characters render as characters, not boxes or mojibake.
