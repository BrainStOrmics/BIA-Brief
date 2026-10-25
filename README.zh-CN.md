# BIA-Brief Report Skill

本目录封装的是 `bia-brief-report` Agent Skill。它教 agent 如何把一个生物信息学项目
——一个装着分析图、脚本和元数据的文件夹——变成一份成稿报告，输出 Markdown、PDF
和 LaTeX 三种格式。

Skill 只包含工作流说明。报告引擎是 `bia-brief` Python 包，需要单独安装，版本固定为 0.2.6。

有两种用法：

- **让 agent 去做。** 把本目录装进 agent 的 skills 目录，然后说
  `$bia-brief-report 生成我这个项目的报告`。agent 会读 `SKILL.md` 并替你调用命令行。
- **自己敲命令。** 装好运行时后直接调 `bia-brief-project`。这里的一切都不依赖 agent。

English version: [README.md](README.md)

## 开始前需要准备什么

- Python 3.10 或更新版本
- 一个兼容 OpenAI 协议的接口地址和 API key，分别用于**文本**模型和**视觉**模型
  ——报告引擎会用视觉模型读你的图，判断它们属于哪个分析步骤并生成图注
- Playwright 的 Chromium，用来渲染 PDF
- 一个包含 `figures/` 或 `pics/` 的项目文件夹
- 能访问模型接口的网络。每跑一次报告都会调用模型若干次，因此会消耗 API 额度。

## 安装

用支持 Agent Skills 的 skill 管理器安装本目录，或直接把它复制进 agent 的 skills 目录。
然后在将要生成报告的环境里安装版本固定的运行时：

```powershell
python -m pip install "bia-brief @ git+https://github.com/BrainStOrmics/BIA-Brief.git@v0.2.6"
playwright install chromium
```

运行时尚未发布到 PyPI，因此唯一可用的安装来源是不可变的 Git tag。
`pip install "bia-brief==0.2.6"` 目前会以 `No matching distribution found` 失败。
等版本发布到 PyPI 后，可以改用更短的写法：

```powershell
python -m pip install "bia-brief==0.2.6"
```

## 一次性配置模型

在同一个环境里运行一次配置向导：

```powershell
bia-brief-setup
```

它会依次问六项：文本模型接口地址、文本模型名称、文本模型 API key、视觉模型接口地址、
视觉模型名称、视觉模型 API key。视觉模型那几项默认沿用文本模型的值，所以同一个模型
兼顾两种角色时，在视觉提示处直接回车即可。API key 的输入不会回显。

配置保存到 `~/.bia-brief/config.yaml`，之后的运行会自动复用。查找顺序：

1. 显式传入的 `--config <path>`
2. `BIA_BRIEF_CONFIG`
3. `~/.bia-brief/config.yaml`
4. 直接从源码检出目录运行时使用的遗留配置

**不要把密钥贴进对话。** 通过 `bia-brief-setup` 输入密钥，把生成的用户配置保存在
Git 之外，仅在确实需要使用另一份配置时才传 `--config`。

## 准备项目

一个文件夹对应一份报告：

```text
<project>/
|-- project_info.md        项目元数据；强烈建议提供
|-- figures/ or pics/      分析图；必需
|-- scripts/               分析脚本；可选
|-- tables/                辅助表格；可选
`-- output/                生成的产物
```

`figures/` 和 `pics/` 都接受。索引器按 `<project>/pics/figures/`、`<project>/pics/`、
`<project>/figures/` 的顺序查找。报告背景文字就是从 `project_info.md` 组装出来的；
不提供它报告照样能跑，只是叙述性上下文会单薄一些。

`project` 参数既接受路径也接受 id。id 会相对于**当前工作目录**下的 `projects/` 目录
解析，所以 `bia-brief-project my_project` 找的是 `./projects/my_project`。直接传一个
已存在的路径优先级更高，在仓库之外使用也更稳妥。

输入布局与模板选择详见 [references/project-structure.md](references/project-structure.md)。

## 运行第一份报告

先检查环境和项目结构：

```powershell
bia-brief-doctor --project <项目路径>
```

它会检查六个 Python 依赖、打包好的模板，以及项目里是否有 `figures/` 或 `pics/` 目录。
然后生成报告：

```powershell
bia-brief-project <项目id或路径>
```

整个过程要几分钟，分四个阶段：

1. **索引器**扫描图片、读取脚本，写出带图注和段落摘要的 `index.md`。
2. agent 起草大纲。
3. agent 把报告正文写入 `output/report.md`。
4. 嵌入图片、渲染模板，导出 PDF 和 LaTeX。

其中有两个阶段会停下来等人审阅：索引器产物，以及大纲。默认两者都自动批准，
不会停下来等你；加 `--interactive-review` 可以逐个自己审。大纲审阅时输入的
非空修改意见会返回给 Agent，并用于修订同一份大纲。

如果想在正式跑之前先看背景文字，可以只打印它然后退出：

```powershell
bia-brief-project <项目id或路径> --print-background
```

## 查看结果

每次成功运行会在项目的 output 目录产出：

```text
output/report.md          报告源文件
output/report.pdf         成稿报告
output/report.tex         LaTeX 源文件
output/report.md.outline  经审阅的大纲
output/report.md.title    agent 拟定的标题
```

索引器写出的 `index.md` 在项目根目录，不在 `output/` 下。

PDF 还会被复制到仓库级的 `deliverables/` 目录，文件名取自 `project_info.md` 里的
`报告名称` 字段。加 `--no-delivery-copy` 可跳过这一步。

宣布成功之前，请打开 PDF 确认正文主要章节、图片和目录都存在。详细的验收检查项见
[references/quality-checklist.md](references/quality-checklist.md)。

## 出问题时

| 现象 | 可能原因 |
|---|---|
| PDF 导出失败 | 未安装 Playwright Chromium（`playwright install chromium`） |
| Doctor 提示项目缺失 | 项目缺少 `figures/` 或 `pics/` 目录 |
| `pip install "bia-brief==0.2.6"` 失败 | 该版本尚未发布到 PyPI，改用上面的 Git tag 命令 |
| 找不到模板 | 模板别名或路径错误 —— 使用 `templates/scRNA/report.md`、`templates/spatial/report.md` 或 `templates/standard/report.md` |
| PDF 中中文乱码 | 缺少中文字体 —— 确保已安装 `ctex` LaTeX 包或系统 CJK 字体 |
| 索引器没有返回结果 | 视觉模型不可用 —— 检查 `config.yaml` 里的 API key 和接口地址 |
| Windows 下 GBK 编码错误 | 设置 `PYTHONIOENCODING=utf-8` 或使用 UTF-8 终端 |
| agent 没有提供这个 skill | 目录没装进 agent 的 skills 目录，或该 agent 不支持 skill 发现 |

更多情况见 [references/troubleshooting.md](references/troubleshooting.md)。

## 进阶选项

| 选项 | 作用 |
|---|---|
| `--template <key>` | 选择 `scRNA`（默认）、`dnbc4`、`standard`（DNBelab C4 兼容别名）或 `spatial`（实验性） |
| `--print-background` | 打印组装好的背景后退出，不生成报告（需要已有模型配置） |
| `--interactive-review` | 在索引器和大纲两处停下来等人工审阅，而不是自动批准 |
| `--no-delivery-copy` | 不把 PDF 复制进 `deliverables/` |
| `--config <path>` | 本次运行使用指定的模型配置 |
| `--project-id <id>` | 覆盖回退标题和元数据使用的项目 id，不显示在封面 |
| `--runner-config <path>` | 使用指定的运行配置 |
| `--lang <代码>` | 报告语言，默认 `zh-CN` |

批量模式按顺序跑多个项目：

```powershell
bia-brief-batch project_a project_b
bia-brief-batch --all
```

`--all` 会扫遍 `projects/` 目录下的所有项目，使用前请确认范围。加 `--stop-on-failure`
可以在第一个错误处停下。

## 给集成者

Skill 是一个文档包，本节说明它的内部结构。

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

Skill 的维护分支是 `codex/bia-brief-skill`。运行时发行版可从不可变的 `v0.2.6` Git tag 获取：

```text
https://github.com/BrainStOrmics/BIA-Brief/tree/codex/bia-brief-skill
https://github.com/BrainStOrmics/BIA-Brief/tree/v0.2.6
```

`v0.2.2` 是第一个报告页面采用纯白底色的版本，图片不会再呈现为贴在略深页面上的白色矩形。
请安装该版本或更新版本；`v0.2.1` 及更早版本仍使用旧的页面背景。
