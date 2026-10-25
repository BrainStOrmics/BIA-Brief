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

Use `scRNA` for the stable single-cell workflow. `dnbc4` and `standard` select
the DNBelab C4 single-cell layout; `standard` is retained as a compatibility
alias. The `spatial` body profile is experimental and requires manual review.
Pass an explicit template path only when the project requires a custom
template; custom paths use the generic body profile.
