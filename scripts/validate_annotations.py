from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class OntologyProfile:
    classes: set[str]
    parents: dict[str, set[str]]
    object_properties: dict[str, dict[str, str]]
    data_properties: set[str]


def clean_cell(value: str) -> str:
    return value.strip().replace("\\|", "|")


def split_row(line: str) -> list[str]:
    return [clean_cell(cell) for cell in line.strip().strip("|").split("|")]


def parse_profile(path: Path) -> OntologyProfile:
    classes: set[str] = set()
    parents: dict[str, set[str]] = {}
    object_properties: dict[str, dict[str, str]] = {}
    data_properties: set[str] = set()
    section = ""

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            section = line.removeprefix("## ").strip()
            section = {
                "类": "Classes",
                "对象属性": "Object Properties",
                "数据属性": "Data Properties",
                "已有实例": "Named Individuals",
                "注释属性": "Annotation Properties",
            }.get(section, section)
            continue
        if not line.startswith("|") or line.startswith("|---"):
            continue

        cells = split_row(line)
        if cells and cells[0] in {"Class", "Property", "Individual"}:
            continue
        if section == "Classes" and cells:
            classes.add(cells[0])
            parent_values = set()
            if len(cells) >= 3 and cells[2] != "-":
                parent_values = {part.strip() for part in re.split(r",|;", cells[2]) if part.strip()}
            parents[cells[0]] = parent_values
        elif section == "Object Properties" and len(cells) >= 4:
            object_properties[cells[0]] = {"domain": cells[2], "range": cells[3]}
        elif section == "Data Properties" and cells:
            data_properties.add(cells[0])

    return OntologyProfile(classes=classes, parents=parents, object_properties=object_properties, data_properties=data_properties)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            item["_line"] = line_number
            rows.append(item)
        except json.JSONDecodeError as exc:
            rows.append({"_line": line_number, "_parse_error": str(exc), "raw": line})
    return rows


def entity_index(item: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entity.get("id", ""): entity for entity in item.get("entities", []) if isinstance(entity, dict)}


def ancestors(value: str, parents: dict[str, set[str]]) -> set[str]:
    seen = {value}
    pending = list(parents.get(value, set()))
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        pending.extend(parents.get(current, set()))
    return seen


def compatible(value: str, expected: str, profile: OntologyProfile) -> bool:
    if not expected or expected == "-":
        return True
    options = {part.strip() for part in re.split(r",|;", expected) if part.strip()}
    return bool(ancestors(value, profile.parents) & options)


def validate_item(item: dict[str, Any], profile: OntologyProfile, min_confidence: float) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    line = str(item.get("_line", "?"))
    if "_parse_error" in item:
        return [{"severity": "error", "line": line, "issue": "invalid_json", "detail": item["_parse_error"]}]

    text = item.get("text", "")
    entities = entity_index(item)

    for entity in item.get("entities", []):
        entity_id = entity.get("id", "?")
        class_name = entity.get("class", "")
        surface = entity.get("text", "")
        if class_name not in profile.classes:
            findings.append({"severity": "error", "line": line, "issue": "unknown_class", "detail": f"{entity_id}: {class_name}"})
        if surface and surface not in text:
            findings.append({"severity": "warning", "line": line, "issue": "surface_not_in_text", "detail": f"{entity_id}: {surface}"})
        if float(entity.get("confidence", 1.0) or 0.0) < min_confidence and item.get("status") == "accepted":
            findings.append({"severity": "warning", "line": line, "issue": "low_confidence_entity_accepted", "detail": entity_id})

    for relation in item.get("relations", []):
        predicate = relation.get("predicate", "")
        subject_id = relation.get("subject", "")
        object_id = relation.get("object", "")
        if predicate not in profile.object_properties:
            findings.append({"severity": "error", "line": line, "issue": "unknown_object_property", "detail": predicate})
            continue
        subject = entities.get(subject_id)
        obj = entities.get(object_id)
        if not subject or not obj:
            findings.append({"severity": "error", "line": line, "issue": "relation_endpoint_missing", "detail": f"{subject_id} --{predicate}--> {object_id}"})
            continue
        prop = profile.object_properties[predicate]
        if not compatible(subject.get("class", ""), prop["domain"], profile):
            findings.append({"severity": "warning", "line": line, "issue": "domain_mismatch", "detail": f"{subject.get('class')} not in {predicate} domain {prop['domain']}"})
        if not compatible(obj.get("class", ""), prop["range"], profile):
            findings.append({"severity": "warning", "line": line, "issue": "range_mismatch", "detail": f"{obj.get('class')} not in {predicate} range {prop['range']}"})
        if float(relation.get("confidence", 1.0) or 0.0) < min_confidence and item.get("status") == "accepted":
            findings.append({"severity": "warning", "line": line, "issue": "low_confidence_relation_accepted", "detail": f"{subject_id} --{predicate}--> {object_id}"})

    for attribute in item.get("attributes", []):
        predicate = attribute.get("predicate", "")
        if predicate not in profile.data_properties:
            findings.append({"severity": "error", "line": line, "issue": "unknown_data_property", "detail": predicate})

    return findings


def write_report(findings: list[dict[str, str]], output: Path, language: str = "zh") -> None:
    errors = sum(1 for finding in findings if finding["severity"] == "error")
    warnings = sum(1 for finding in findings if finding["severity"] == "warning")
    zh = language == "zh"
    if zh:
        lines = [
            "# 审核报告",
            "",
            "## 统计摘要",
            "",
            f"- 错误: {errors}",
            f"- 警告: {warnings}",
            "",
            "## 问题列表",
            "",
            "| 严重程度 | 行号 | 问题 | 详情 |",
            "|---|---:|---|---|",
        ]
    else:
        lines = [
            "# Audit Report",
            "",
            "## Summary",
            "",
            f"- Errors: {errors}",
            f"- Warnings: {warnings}",
            "",
            "## Findings",
            "",
            "| Severity | Line | Issue | Detail |",
            "|---|---:|---|---|",
        ]
    for finding in findings:
        detail = str(finding["detail"]).replace("|", "\\|")
        lines.append(f"| {finding['severity']} | {finding['line']} | {finding['issue']} | {detail} |")
    if not findings:
        message = "未发现机械校验问题。" if zh else "No mechanical validation issues found."
        lines.append(f"| note | - | no_findings | {message} |")
    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ontology-guided annotation JSONL against ontology_profile.md.")
    parser.add_argument("ontology_profile", type=Path)
    parser.add_argument("annotation_jsonl", type=Path)
    parser.add_argument("--output", type=Path, default=Path("audit_report.md"))
    parser.add_argument("--min-confidence", type=float, default=0.75)
    parser.add_argument("--language", choices=["zh", "en"], default="zh", help="Report language. Defaults to Chinese.")
    args = parser.parse_args()

    profile = parse_profile(args.ontology_profile)
    items = load_jsonl(args.annotation_jsonl)
    findings: list[dict[str, str]] = []
    for item in items:
        findings.extend(validate_item(item, profile, args.min_confidence))
    write_report(findings, args.output, language=args.language)
    print(f"Wrote {args.output} with {len(findings)} findings")
    return 1 if any(finding["severity"] == "error" for finding in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
