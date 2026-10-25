# Spatial Report Body Generation Rules

## Scope

Generate only the analysis body defined below. The template supplies the cover,
table of contents, project information, sequencing results, methods, help,
FAQ, and references.

Use the exact heading order:

```text
### 4 数据质控与标准化
### 5 降维聚类与空间域识别
#### 5.1 降维与聚类
#### 5.2 空间域识别
### 6 空间表达与细胞类型注释
#### 6.1 空间表达模式
#### 6.2 细胞类型注释
### 7 空间邻域与细胞通讯
### 8 差异表达与功能富集
```

Omit sections 6-8 only when the project index contains no supporting figures
or analysis output. Never replace missing evidence with invented results.

## Evidence Rules

- Read `index.md` before writing.
- Every figure must come from the Images table and appear exactly once.
- Use the figure path from the Images table.
- Figure 1 is the static workflow figure supplied by the template. Dynamic
  figures start at 图2 and follow document order.
- Put the figure immediately after the paragraph that explains it.
- Use concise captions in the form `图N 标题。`.
- Do not list left, middle, and right panels one by one unless the index
  explicitly provides that panel structure.
- State spatial resolution, coordinates, neighborhood distances, cluster
  counts, marker genes, and statistics only when they are present in project
  files.
- Avoid subjective wording such as “成功”, “显著”, “clearly”, or “successfully”.
- Do not use Python function-call syntax in prose.

## Section Expectations

### 4 数据质控与标准化

Describe tissue and spot/cell quality filtering, library quality, and
normalization supported by the index. Reference the methods section when the
template provides it.

### 5 降维聚类与空间域识别

Describe dimensionality reduction, clustering, and spatial-domain methods only
when supported by figures or scripts. Distinguish transcriptional clusters
from spatial domains.

### 6 空间表达与细胞类型注释

Describe spatial expression patterns and annotation evidence. Do not assign
cell types without marker or reference support in the project data.

### 7 空间邻域与细胞通讯

Include this section only when neighborhood, colocalization, ligand-receptor,
or cell-communication results are indexed. If the workflow cannot support a
claim, omit it rather than making a generic statement.

### 8 差异表达与功能富集

Include this section only when differential-expression or enrichment figures
are indexed. Report thresholds and pathways only when present in the source.

## Output

Start with the first retained section heading. Do not add a title page, table
of contents, abstract, conclusion, discussion, or references. Write the body
and title to the exact paths supplied by the user message.
