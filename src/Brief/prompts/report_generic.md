# Generic Report Body Generation Rules

Generate only the analysis body for a custom BIA-Brief template.

- Read `index.md` before drafting.
- Follow the section structure implied by the selected template and the
  available evidence. Do not copy a single-cell section structure unless the
  project evidence supports it.
- Use every indexed figure at most once and place each figure immediately
  after its explanatory paragraph.
- Use the dynamic figure start specified in the user message.
- Derive the report title from `project_info.md` when present.
- State methods, parameters, counts, trends, and statistics only when they are
  present in project files or index captions.
- Do not invent citations, biological interpretations, or missing results.
- Avoid subjective wording and Python function-call syntax in prose.
- Write the body and title to the exact paths supplied by the user message.
- Do not generate a new cover, table of contents, abstract, conclusion,
  discussion, or reference block.
