# BIA-Brief Report Skill

本目录封装的是 `bia-brief-report` Agent Skill。它教 agent 如何检查一个生物信息学项目，
并调用已安装的 BIA-Brief 运行时，生成并校验 Markdown、PDF 与 LaTeX 报告。

Skill 只包含工作流说明；报告引擎需要单独安装，即版本固定为 0.2.2 的 `bia-brief` Python 包。

English version: [README.md](README.md)

## 快速开始

```powershell
python -m pip install "bia-brief @ git+https://github.com/BrainStOrmics/BIA-Brief.git@v0.2.2"
playwright install chromium
bia-brief-setup
bia-brief-project <project-id-or-path>
```

只在首次配置模型、或更换服务商时才需要运行 `bia-brief-setup`。之后的项目与批量命令
都会复用已保存的配置。

## 目录结构

```text
bia-brief-skill/
|-- SKILL.md                    # agent 指令与报告工作流
|-- agents/openai.yaml          # 可选的 Codex/OpenAI 展示元数据
|-- assets/config.yaml.example  # 模型配置结构示例
|-- references/
|   |-- project-structure.md     # 输入布局与模板选择指引
|   |-- quality-checklist.md     # 产物验收检查项
|   `-- troubleshooting.md       # 常见故障与处理办法
`-- scripts/check_bia_brief.py  # 本地安装自检脚本
```

## 安装

用支持 Agent Skills 的 skill 管理器安装本目录，或直接把它复制进 agent 的 skills 目录。
然后在将要生成报告的环境里安装版本固定的运行时：

```powershell
python -m pip install "bia-brief @ git+https://github.com/BrainStOrmics/BIA-Brief.git@v0.2.2"
playwright install chromium
```

运行时尚未发布到 PyPI，因此唯一可用的安装来源是不可变的 Git tag。
`pip install "bia-brief==0.2.2"` 目前会以 `No matching distribution found` 失败。
等版本发布到 PyPI 后，可以改用更短的写法：

```powershell
python -m pip install "bia-brief==0.2.2"
```

## 一次性模型配置

在同一个环境里运行一次配置向导：

```powershell
bia-brief-setup
```

它会把文本模型与视觉模型配置保存到 `~/.bia-brief/config.yaml`，并且不会回显 API key。
之后的报告命令会自动找到这个文件。只有在使用另一份配置时，才需要用 `BIA_BRIEF_CONFIG`
或 `--config`。

配置查找顺序：

1. 显式传入的 `--config <path>`
2. `BIA_BRIEF_CONFIG`
3. `~/.bia-brief/config.yaml`
4. 直接从源码检出目录运行时使用的遗留配置

## 使用方法

```powershell
bia-brief-doctor --project <project-path>
bia-brief-project <project-id-or-path>
bia-brief-batch project_a project_b
```

项目目录应包含 `figures/` 或 `pics/`；`project_info.md`、`scripts/` 和 `tables/` 属于可选，
但能补足报告上下文。

每次成功运行会在项目的 output 目录产出 `report.md`、`report.pdf` 和 `report.tex`。
除非使用 `--no-delivery-copy`，PDF 还会额外复制到仓库级的 `deliverables/` 目录。

宣布成功之前，请检查生成的 PDF，确认正文主要章节、图片和目录都存在。详细的验收检查项
见 `references/quality-checklist.md`。

## Agent 兼容性

核心的 `SKILL.md` 遵循 Agent Skills 布局（`name`、`description` 加 Markdown 指令），
因此任何实现了该约定的 agent 都能加载这套工作流。但它并非对所有 agent 自动可用：
agent 需要支持 skill 发现机制，或者由你显式把这个目录交给它。

| 宿主类型 | Skill 加载方式 | 运行时要求 | 说明 |
|---|---|---|---|
| Codex/OpenAI | 从 skills 目录自动加载 | Python、运行时包、Chromium、模型配置 | 支持 `$bia-brief-report` 与 `agents/openai.yaml` |
| 其他兼容 Agent Skills 的 agent | 通常安装后自动加载 | 同上 | 加载 `SKILL.md`；若不支持可忽略 `agents/openai.yaml` |
| 不支持 Skill 的普通 agent | 不自动加载 | 同上 | 把本目录交给它，并明确要求它读取 `SKILL.md` |

报告运行时本身可以跨 agent 使用，但每个宿主仍然需要 Python 3.10+、版本固定的运行时包、
Playwright Chromium、对项目目录的文件系统访问权限，以及兼容 OpenAI 的文本与视觉模型端点。

示例统一使用 PowerShell，因为维护用的回归环境是 Windows。在 POSIX 系统上，请改用对应
shell 的等价的激活与路径写法；该 Python 包同时支持 Windows 与 POSIX 的审批计时器。

## 发布来源

Skill 的维护分支是 `codex/bia-brief-skill`。运行时发行版可从不可变的 `v0.2.2` Git tag 获取：

```text
https://github.com/BrainStOrmics/BIA-Brief/tree/codex/bia-brief-skill
https://github.com/BrainStOrmics/BIA-Brief/tree/v0.2.2
```

`v0.2.2` 是第一个报告页面采用纯白底色的版本，图片不会再呈现为贴在略深页面上的白色矩形。
请安装该版本或更新版本；`v0.2.1` 及更早版本仍使用旧的页面背景。

## 安全边界

不要把 API key 粘贴进 agent 对话。通过 `bia-brief-setup` 输入密钥，把生成的用户配置
保存在 Git 之外，仅在确实需要使用另一份配置时才传 `--config`。
