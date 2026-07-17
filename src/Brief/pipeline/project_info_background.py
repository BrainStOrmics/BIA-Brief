"""Normalize project_info.md into a stable report-generation background."""

from __future__ import annotations

import re
from pathlib import Path


_FIELD_ORDER = [
    "项目名称",
    "报告名称",
    "合同编号",
    "物种",
    "参考基因组",
    "样本数量",
    "测序技术",
    "项目简介",
]


def _clean_line(line: str) -> str:
    """Strip common markdown/artifact prefixes while preserving Chinese content."""
    return line.strip().lstrip("/").lstrip("#").strip()


def _split_field_value(value: str) -> list[str]:
    """Split a field that may contain multiple inline values."""
    parts = [part.strip() for part in re.split(r"[，,;；]\s*|\s{2,}", value) if part.strip()]
    return parts or [value.strip()]


def parse_project_info(text: str) -> dict[str, list[str]]:
    """Parse a project_info.md payload into normalized fields."""
    fields: dict[str, list[str]] = {key: [] for key in _FIELD_ORDER}
    fields["样本ID"] = []
    fields["补充说明"] = []

    in_sample_ids = False
    for raw_line in text.splitlines():
        line = _clean_line(raw_line)
        if not line:
            continue

        match = re.match(r"^(项目名称|报告名称|合同编号|物种|参考基因组|样本数量|测序技术|项目简介|样本ID)\s*[:：]\s*(.*)$", line)
        if match:
            key, value = match.groups()
            value = value.strip()
            if key == "样本ID":
                in_sample_ids = True
                if value:
                    fields["样本ID"].extend(_split_field_value(value))
            else:
                fields[key] = _split_field_value(value) if value else []
                in_sample_ids = False
            continue

        if in_sample_ids:
            fields["样本ID"].append(line)
            continue

        if re.fullmatch(r"[A-Z]{2,5}\d{6,}", line):
            fields["样本ID"].append(line)
        else:
            fields["补充说明"].append(line)

    return fields


def _first_value(fields: dict[str, list[str]], key: str) -> str:
    values = fields.get(key, [])
    return values[0].strip() if values else ""


def build_project_background(project_path: str | Path, project_id: str | None = None) -> str:
    """Build a standardized factual background from project_info.md."""
    project_root = Path(project_path)
    info_path = project_root / "project_info.md"
    if not info_path.is_file():
        fallback_name = project_id or project_root.name
        return f"项目 {fallback_name} 的背景信息缺失，请结合项目文件、图像和脚本完成单细胞报告生成。"

    text = info_path.read_text(encoding="utf-8", errors="replace")
    fields = parse_project_info(text)

    project_name = _first_value(fields, "项目名称") or project_root.name
    report_name = _first_value(fields, "报告名称")
    contract_no = _first_value(fields, "合同编号")
    species = _first_value(fields, "物种")
    genome = _first_value(fields, "参考基因组")
    sample_count = _first_value(fields, "样本数量")
    sequencing_tech = _first_value(fields, "测序技术")
    project_intro = _first_value(fields, "项目简介")
    sample_ids = fields.get("样本ID", [])

    parts: list[str] = [f"项目名称为{project_name}。"]
    if report_name:
        parts.append(f"报告名称为{report_name}。")
    if contract_no:
        parts.append(f"合同编号为{contract_no}。")

    sample_scope_bits: list[str] = []
    if species:
        sample_scope_bits.append(f"研究物种为{species}")
    if genome:
        sample_scope_bits.append(f"参考基因组为{genome}")
    if sample_count:
        sample_scope_bits.append(f"样本数量为{sample_count}")
    if sample_scope_bits:
        parts.append("；".join(sample_scope_bits) + "。")
    if sequencing_tech:
        parts.append(f"测序技术为{sequencing_tech}。")

    if sample_ids:
        parts.append(f"样本编号包括{'、'.join(sample_ids)}。")

    if project_intro:
        parts.append(f"项目说明：{project_intro}。")
    else:
        # Auto-generate a concise background from available metadata
        hints = []
        if species:
            hints.append(f"研究对象为{species}")
        if sample_count:
            hints.append(f"样本量为{sample_count}")
        if sequencing_tech:
            hints.append(f"采用{sequencing_tech}技术")
        if hints:
            parts.append(f"本项目{'，'.join(hints)}进行单细胞转录组测序分析。")
        else:
            parts.append("本项目进行单细胞转录组测序分析。")

    parts.append(
        "后续分析将围绕单细胞转录组数据的细胞异质性、细胞亚群鉴定、特征基因表达谱和相关生物学机制展开，"
        "并结合项目图像和脚本生成标准化报告。"
    )

    return "".join(parts)
