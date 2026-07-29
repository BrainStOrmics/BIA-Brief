# Project structure

Use one project directory per report:

```text
<project>/
├── project_info.md        required metadata when available
├── figures/ or pics/      required analysis figures
├── scripts/               optional analysis scripts
├── tables/                optional supporting tables
└── output/                generated artifacts
```

Use `scRNA`, `spatial`, or `standard` as the template key. Pass an explicit
template path only when the project requires a custom template.
