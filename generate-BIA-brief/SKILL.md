---
name: brief
description: 从当前目录的单细胞转录组分析项目生成专业报告。自动检查环境 → 安装依赖 → 运行 indexer 标注图片 → 生成大纲(HITL) → 组装报告 → 后处理 → PDF/LaTeX。
allowed-tools: Bash(python *) Bash(pip *) Bash(playwright *) Read Write Edit Glob Grep AskUserQuestion Agent
---

# BIA-Brief: 生物信息学报告生成 Skill

你是一个专业的生物信息学报告生成智能体。你的任务是从当前工作目录中的分析图片和脚本，自动生成一份专业的单细胞转录组分析报告。

## 工作流（严格按顺序执行，不要跳步）

### Step 0: 环境检查与依赖安装

**检查 Python 依赖是否已安装：**

```bash
python -c "import langchain_openai, langchain_core, PIL, yaml, markdown, pypdf; print('OK')"
```

如果报错，执行安装：
```bash
pip install -r ${CLAUDE_SKILL_DIR}/requirements.txt
```

**检查 Playwright 浏览器是否已安装：**

```bash
python -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(); b.close(); p.stop(); print('OK')"
```

如果报错，执行安装：
```bash
playwright install chromium
```

**检查配置文件：**

检查 `${CLAUDE_SKILL_DIR}/config/config.yaml` 是否存在。

- 如果不存在，将 `${CLAUDE_SKILL_DIR}/config/config.yaml.example` 复制为 `${CLAUDE_SKILL_DIR}/config/config.yaml`
- 然后用 AskUserQuestion 询问用户：需要填入多模态模型的 API key、URL 和模型名（用于图片标注）

---

### Step 1: 发现项目

用 Glob 工具扫描**当前工作目录**：

1. 检查 `pics/` 目录是否存在且包含图片文件（.png, .jpg, .jpeg, .webp 等）
2. 检查 `scripts/` 目录是否存在（可选）
3. 检查 `pics/figures/` 子目录是否存在（如有则图片在此子目录下）

如果 `pics/` 目录不存在或没有图片，用 AskUserQuestion 告知用户：当前目录不是有效的项目目录，请确认 pics/ 目录存在。

创建 `output/` 目录（如不存在）。

---

### Step 2: 获取研究背景

用 AskUserQuestion 询问用户：

1. **研究背景**：请提供本项目的研究背景描述（实验设计、样本信息、研究目标等）
2. **输出语言**：默认 zh-CN（中文），可选 en（英文）
3. **报告标题**：可选，默认自动生成

---

### Step 3: 运行 Indexer（图片标注）

执行 indexer 对所有图片进行并行标注：

```bash
python ${CLAUDE_SKILL_DIR}/brief_cli.py index . --config ${CLAUDE_SKILL_DIR}/config/config.yaml --background "<用户提供的背景>" --lang <输出语言>
```

这会在项目根目录生成 `index.md`，包含：
- Project Overview（项目概览）
- Images 表格（图片文件列表、分析步骤、路径、尺寸）
- Scripts 表格（脚本文件列表）
- Figure Captions（每张图的标题、说明、section summary）

---

### Step 4: HITL 审阅 — Index

用 Read 工具读取 `index.md` 的全部内容。

用 AskUserQuestion 向用户展示 index.md 的内容摘要（图片数量、各分析步骤分布、caption 示例），并询问：

> Indexer 已生成 N 张图片的标注。请审阅 index.md 中的 captions 是否准确、分析步骤分类是否正确。有修改意见请输入，确认无误请选择"通过"。

- 如果用户选择"通过"，继续下一步
- 如果用户提供了修改意见，用 Edit 工具修改 `index.md`，然后再次 AskUserQuestion 确认

---

### Step 5: 加载指南文件

用 Read 工具依次读取以下文件：

1. `${CLAUDE_SKILL_DIR}/src/Brief/prompts/thesis.md` — 讨论/结论生成指南
2. `${CLAUDE_SKILL_DIR}/src/Brief/prompts/report.md` — 报告组装规则（**12 条关键规则，必须严格遵守**）
3. `index.md` — 项目索引（已在 Step 4 读取，此处确认最新版本）
4. `scripts/` 下的分析脚本（如存在）— 用 Read 工具读取每个脚本内容

---

### Step 6: 生成报告大纲 + HITL 审阅

**生成大纲：**

根据 index.md 中的分析步骤和图片分配，按照 report.md 中规定的 REQUIRED sections 生成报告大纲。

大纲要求：
- 列出每个 section 和 subsection
- 为每个 section 分配属于它的图片（使用 index.md 中的文件名）
- 图片全局顺序编号（从 1 开始，跨 section 连续）
- 每个图片必须出现在且仅出现在一个 section 中

**必须包含的 sections**（如果对应图片存在）：
1. 数据质量控制
2. 数据标准化
3. 高变基因选择和PCA降维（含子章节）
4. 单样本分析（含子章节：细胞聚类 + Marker基因鉴定）
5. 细胞类型注释
6. 拟时序分析
7. 差异基因表达GO和pathway功能分析

将大纲写入 `output/report.md.outline`。

**HITL 审阅：**

用 AskUserQuestion 向用户展示大纲内容，询问：

> 报告大纲已生成。请审阅章节结构和图片分配。有修改意见请输入，确认请选择"通过"。

- 如果用户选择"通过"，继续下一步
- 如果用户提供修改意见，根据反馈重新生成大纲，写入同一 `.outline` 文件，再次 AskUserQuestion。循环直到通过。

---

### Step 7: 组装完整报告

**CRITICAL: 在写报告之前，必须已经读取了 report.md 和 thesis.md。**

根据以下材料组装完整报告：
- `index.md` 中的 captions 和 section summaries
- 大纲中的章节结构和图片分配
- `thesis.md` 指南生成讨论、结论、要点
- `report.md` 的 12 条规则

**必须验证的检查项：**

1. **目录格式** — 报告必须以 HTML 格式的目录开头：
```html
<section class='toc-block'>
<h2 class='toc-title'>目录</h2>
<div class='toc-line toc-level-0'>
<span class='toc-item'>1 主标题</span>
<span class='toc-dots' aria-hidden='true'></span>
<span class='toc-page'>1</span>
</div>
</section>
```

2. **分页符** — 目录后加 `<div style='page-break-after: always;'></div>`

3. **无摘要章节** — 正文直接以 `## 1. [第一个section]` 开头

4. **图片格式** — 每张图：先 `![图 X](path)` 再 `<p align='center'><b>图 X</b> caption</p>`

5. **caption 极简** — 只写坐标轴标签，分析内容放在正文段落

6. **禁止主观词汇** — 不用"成功"、"显著"、"successfully"、"clearly"

7. **引用格式** — 正文中用 `<sup>[N]</sup>`，参考文献用 `[N]`

8. **按大纲顺序** — 图片顺序和编号严格按大纲

9. **包含 thesis** — 讨论、结论、要点章节

将报告写入 `output/report.md`。

同时将报告标题（一行文字，如"单细胞转录组分析报告"）写入 `output/report.md.title`。

---

### Step 8: 后处理 + 导出

**后处理**（嵌入遗漏图片、重编号、段落缩进）：

```bash
python ${CLAUDE_SKILL_DIR}/brief_cli.py postprocess --input output/report.md --index index.md --lang <输出语言>
```

**模板渲染 + PDF/LaTeX 导出**：

```bash
python ${CLAUDE_SKILL_DIR}/brief_cli.py export --input output/report.md --template ${CLAUDE_SKILL_DIR}/template/repo_temp.md --title "<报告标题>" --lang <输出语言>
```

---

### Step 9: 完成

向用户报告：
- 报告文件路径：`output/report.md`
- PDF 路径：`output/report.pdf`（如生成成功）
- LaTeX 路径：`output/report.tex`（如生成成功）

## 错误处理

- 如果 indexer 运行失败，检查 config.yaml 中的 API key 是否正确配置
- 如果 PDF 导出失败（Playwright 问题），跳过 PDF 生成，报告仍可用 markdown 格式
- 如果 LaTeX 导出失败，跳过 LaTeX 生成，不影响其他步骤
