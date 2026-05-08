from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


def load_json(path: Path | None) -> Any:
    if not path or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path | None) -> list[dict[str, Any]]:
    if not path or not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_text(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def count_labels(rows: list[dict[str, Any]]) -> tuple[int, int, int]:
    entities = sum(len(row.get("entities", [])) for row in rows)
    relations = sum(len(row.get("relations", [])) for row in rows)
    attributes = sum(len(row.get("attributes", [])) for row in rows)
    return entities, relations, attributes


def labels_text(language: str) -> dict[str, str]:
    zh = language == "zh"
    return {
        "title": "本体标注结果审核" if zh else "Ontology Annotation Review",
        "summary": "摘要" if zh else "Summary",
        "document_blocks": "文档块" if zh else "Document Blocks",
        "accepted": "已接受" if zh else "Accepted",
        "pending": "待审核" if zh else "Pending Review",
        "rejected": "已拒绝/负例" if zh else "Rejected/Negative",
        "audit": "审核报告" if zh else "Audit Report",
        "feedback": "反馈导出" if zh else "Feedback Export",
        "entities": "实体" if zh else "Entities",
        "relations": "关系三元组" if zh else "Relation Triples",
        "attributes": "属性" if zh else "Attributes",
        "source": "来源" if zh else "Source",
        "confidence": "置信度" if zh else "Confidence",
        "class": "本体类" if zh else "Class",
        "span": "位置" if zh else "Span",
        "accept": "接受" if zh else "Accept",
        "modify": "修改" if zh else "Modify",
        "reject": "拒绝" if zh else "Reject",
        "defer": "暂缓" if zh else "Defer",
        "note": "备注" if zh else "Note",
        "download": "导出反馈 JSON" if zh else "Export Feedback JSON",
        "copy_prompt": "复制反馈提示词" if zh else "Copy Feedback Prompt",
        "no_data": "暂无数据" if zh else "No data",
        "page": "页" if zh else "page",
    }


def confidence_text(value: dict[str, Any], labels: dict[str, str]) -> str:
    conf = value.get("confidence")
    if conf is None:
        return ""
    return f"<span class='confidence'>{labels['confidence']} {esc(conf)}</span>"


def entity_lookup(item: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entity.get("id", ""): entity for entity in item.get("entities", []) if isinstance(entity, dict)}


def render_entities(entities: list[dict[str, Any]], labels: dict[str, str]) -> str:
    if not entities:
        return f"<span class='muted'>{labels['no_data']}</span>"
    rows = []
    for entity in entities:
        mention = esc(entity.get("text", ""))
        class_name = esc(entity.get("class", ""))
        start = entity.get("start")
        end = entity.get("end")
        span = f"{start}-{end}" if start is not None and end is not None else "-"
        rows.append(
            "<div class='entity-row'>"
            f"<span class='mention'>{mention}</span>"
            "<span class='arrow'>→</span>"
            f"<span class='class-name'>{class_name}</span>"
            f"<span class='meta'>{labels['span']} {esc(span)}</span>"
            f"{confidence_text(entity, labels)}"
            "</div>"
        )
    return "".join(rows)


def render_relations(item: dict[str, Any], labels: dict[str, str]) -> str:
    relations = item.get("relations", [])
    if not relations:
        return f"<span class='muted'>{labels['no_data']}</span>"
    entities = entity_lookup(item)
    rows = []
    for relation in relations:
        subject = entities.get(relation.get("subject", ""), {})
        obj = entities.get(relation.get("object", ""), {})
        subject_text = subject.get("text") or relation.get("subject", "")
        subject_class = subject.get("class", "")
        object_text = obj.get("text") or relation.get("object", "")
        object_class = obj.get("class", "")
        predicate = relation.get("predicate", "")
        rows.append(
            "<div class='triple-row'>"
            f"<span class='triple-node'>{esc(subject_text)}<small>{esc(subject_class)}</small></span>"
            f"<span class='predicate'>{esc(predicate)}</span>"
            f"<span class='triple-node'>{esc(object_text)}<small>{esc(object_class)}</small></span>"
            f"{confidence_text(relation, labels)}"
            "</div>"
        )
    return "".join(rows)


def render_attributes(item: dict[str, Any], labels: dict[str, str]) -> str:
    attributes = item.get("attributes", [])
    if not attributes:
        return f"<span class='muted'>{labels['no_data']}</span>"
    entities = entity_lookup(item)
    rows = []
    for attr in attributes:
        entity = entities.get(attr.get("entity", ""), {})
        entity_text = entity.get("text") or attr.get("entity", "")
        rows.append(
            "<div class='attribute-row'>"
            f"<span class='mention'>{esc(entity_text)}</span>"
            f"<span class='predicate'>{esc(attr.get('predicate', ''))}</span>"
            f"<span class='class-name'>{esc(attr.get('value', ''))}</span>"
            f"{confidence_text(attr, labels)}"
            "</div>"
        )
    return "".join(rows)


def render_annotation_card(item: dict[str, Any], index: int, labels: dict[str, str], pending: bool = False) -> str:
    item_id = esc(item.get("id", f"item-{index}"))
    text = esc(item.get("text", ""))
    source = item.get("source", {})
    source_text = esc(json.dumps(source, ensure_ascii=False))

    controls = ""
    if pending:
        controls = f"""
        <div class="decision" data-item-id="{item_id}">
          <label><input type="radio" name="decision-{index}" value="accept"> {labels['accept']}</label>
          <label><input type="radio" name="decision-{index}" value="modify"> {labels['modify']}</label>
          <label><input type="radio" name="decision-{index}" value="reject"> {labels['reject']}</label>
          <label><input type="radio" name="decision-{index}" value="defer" checked> {labels['defer']}</label>
          <textarea placeholder="{labels['note']}"></textarea>
        </div>
        """

    return f"""
    <article class="card">
      <div class="card-head">
        <strong>{item_id}</strong>
        <span class="muted">{labels['source']}: {source_text}</span>
      </div>
      <p class="source-text">{text}</p>
      <div class="row"><b>{labels['entities']}</b><div>{render_entities(item.get("entities", []), labels)}</div></div>
      <div class="row"><b>{labels['relations']}</b><div>{render_relations(item, labels)}</div></div>
      <div class="row"><b>{labels['attributes']}</b><div>{render_attributes(item, labels)}</div></div>
      {controls}
    </article>
    """


def render_document_blocks(document_profile: dict[str, Any] | None, labels: dict[str, str]) -> str:
    if not document_profile:
        return f"<p class='muted'>{labels['no_data']}</p>"
    blocks = document_profile.get("blocks", [])[:30]
    if not blocks:
        return f"<p class='muted'>{labels['no_data']}</p>"
    cards = []
    for block in blocks:
        cards.append(
            f"""
            <article class="block">
              <strong>{esc(block.get('block_id'))}</strong>
              <span class="muted">{labels['source']}: {esc(block.get('source'))} · {labels['page']} {esc(block.get('page'))}</span>
              <p>{esc(block.get('text'))}</p>
            </article>
            """
        )
    return "\n".join(cards)


def build_html(
    document_profile: dict[str, Any] | None,
    accepted: list[dict[str, Any]],
    pending: list[dict[str, Any]],
    rejected: list[dict[str, Any]],
    audit_report: str,
    language: str,
) -> str:
    labels = labels_text(language)
    accepted_counts = count_labels(accepted)
    pending_counts = count_labels(pending)
    rejected_counts = count_labels(rejected)

    accepted_html = "\n".join(render_annotation_card(item, i, labels) for i, item in enumerate(accepted)) or f"<p class='muted'>{labels['no_data']}</p>"
    pending_html = "\n".join(render_annotation_card(item, i, labels, pending=True) for i, item in enumerate(pending)) or f"<p class='muted'>{labels['no_data']}</p>"
    rejected_html = "\n".join(render_annotation_card(item, i, labels) for i, item in enumerate(rejected)) or f"<p class='muted'>{labels['no_data']}</p>"
    audit_html = f"<pre>{esc(audit_report)}</pre>" if audit_report else f"<p class='muted'>{labels['no_data']}</p>"

    return f"""<!doctype html>
<html lang="{language}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{labels['title']}</title>
  <style>
    :root {{
      --bg: #f7f7f4;
      --panel: #ffffff;
      --text: #242424;
      --muted: #666;
      --line: #d9d7cf;
      --accent: #2f6f73;
      --accent-soft: #e5f0ef;
      --warn: #8a5a00;
      --mention: #f3efe3;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Arial, "Microsoft YaHei", sans-serif;
      color: var(--text);
      background: var(--bg);
      line-height: 1.55;
    }}
    header {{
      padding: 28px 32px 18px;
      border-bottom: 1px solid var(--line);
      background: #fff;
    }}
    h1 {{ margin: 0; font-size: 28px; }}
    h2 {{ margin: 0 0 14px; font-size: 20px; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 24px; }}
    nav {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin: 0 0 18px;
    }}
    nav a {{
      color: var(--accent);
      background: var(--accent-soft);
      text-decoration: none;
      padding: 7px 10px;
      border-radius: 6px;
      font-size: 14px;
    }}
    section {{
      margin: 0 0 24px;
      padding: 20px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
    }}
    .stat {{
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 12px;
      background: #fbfbfa;
    }}
    .stat strong {{ display: block; font-size: 24px; }}
    .muted {{ color: var(--muted); font-size: 13px; }}
    .card, .block {{
      border: 1px solid var(--line);
      border-radius: 7px;
      padding: 14px;
      margin: 12px 0;
      background: #fff;
    }}
    .card-head {{
      display: flex;
      justify-content: space-between;
      gap: 14px;
      flex-wrap: wrap;
      border-bottom: 1px solid var(--line);
      padding-bottom: 8px;
    }}
    .source-text {{
      margin: 12px 0;
      padding: 10px;
      background: #f3f3ee;
      border-radius: 5px;
    }}
    .row {{
      display: grid;
      grid-template-columns: 100px 1fr;
      gap: 10px;
      margin: 12px 0;
      align-items: start;
    }}
    .entity-row, .triple-row, .attribute-row {{
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      padding: 7px 0;
      border-bottom: 1px solid #eeeeea;
    }}
    .mention {{
      padding: 2px 7px;
      background: var(--mention);
      border: 1px solid #ded5bd;
      border-radius: 5px;
      font-weight: 600;
    }}
    .class-name {{
      padding: 2px 7px;
      background: var(--accent-soft);
      color: #174a4d;
      border-radius: 5px;
    }}
    .predicate {{
      padding: 2px 8px;
      border: 1px solid var(--accent);
      color: var(--accent);
      border-radius: 999px;
      font-size: 13px;
    }}
    .triple-node {{
      padding: 5px 8px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fbfbfa;
      font-weight: 600;
    }}
    .triple-node small {{
      display: block;
      color: var(--muted);
      font-weight: 400;
      font-size: 12px;
    }}
    .arrow, .meta, .confidence {{
      color: var(--muted);
      font-size: 13px;
    }}
    .decision {{
      margin-top: 12px;
      padding: 12px;
      border-left: 4px solid var(--warn);
      background: #fff8e8;
    }}
    .decision label {{ margin-right: 14px; white-space: nowrap; }}
    textarea {{
      display: block;
      width: 100%;
      min-height: 68px;
      margin-top: 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px;
      font: inherit;
      resize: vertical;
    }}
    button {{
      border: 1px solid var(--accent);
      background: var(--accent);
      color: white;
      border-radius: 6px;
      padding: 8px 12px;
      cursor: pointer;
      margin-right: 8px;
    }}
    pre {{
      overflow: auto;
      white-space: pre-wrap;
      background: #f3f3ee;
      border-radius: 6px;
      padding: 12px;
    }}
  </style>
</head>
<body>
  <header>
    <h1>{labels['title']}</h1>
    <p class="muted">{labels['feedback']}</p>
  </header>
  <main>
    <nav>
      <a href="#summary">{labels['summary']}</a>
      <a href="#documents">{labels['document_blocks']}</a>
      <a href="#accepted">{labels['accepted']}</a>
      <a href="#pending">{labels['pending']}</a>
      <a href="#rejected">{labels['rejected']}</a>
      <a href="#audit">{labels['audit']}</a>
    </nav>
    <section id="summary">
      <h2>{labels['summary']}</h2>
      <div class="stats">
        <div class="stat"><strong>{len(document_profile.get('blocks', []) if document_profile else [])}</strong><span>{labels['document_blocks']}</span></div>
        <div class="stat"><strong>{len(accepted)}</strong><span>{labels['accepted']} · {labels['entities']} {accepted_counts[0]} · {labels['relations']} {accepted_counts[1]}</span></div>
        <div class="stat"><strong>{len(pending)}</strong><span>{labels['pending']} · {labels['entities']} {pending_counts[0]} · {labels['relations']} {pending_counts[1]}</span></div>
        <div class="stat"><strong>{len(rejected)}</strong><span>{labels['rejected']} · {labels['entities']} {rejected_counts[0]} · {labels['relations']} {rejected_counts[1]}</span></div>
      </div>
    </section>
    <section id="documents">
      <h2>{labels['document_blocks']}</h2>
      {render_document_blocks(document_profile, labels)}
    </section>
    <section id="accepted">
      <h2>{labels['accepted']}</h2>
      {accepted_html}
    </section>
    <section id="pending">
      <h2>{labels['pending']}</h2>
      {pending_html}
      <button onclick="downloadFeedback()">{labels['download']}</button>
      <button onclick="copyPrompt()">{labels['copy_prompt']}</button>
    </section>
    <section id="rejected">
      <h2>{labels['rejected']}</h2>
      {rejected_html}
    </section>
    <section id="audit">
      <h2>{labels['audit']}</h2>
      {audit_html}
    </section>
  </main>
  <script>
    function collectFeedback() {{
      return Array.from(document.querySelectorAll('.decision')).map(function(el) {{
        const checked = el.querySelector('input[type="radio"]:checked');
        const note = el.querySelector('textarea').value;
        return {{
          item_id: el.dataset.itemId,
          decision: checked ? checked.value : 'defer',
          note: note
        }};
      }});
    }}
    function downloadFeedback() {{
      const payload = {{
        generated_at: new Date().toISOString(),
        reviews: collectFeedback()
      }};
      const blob = new Blob([JSON.stringify(payload, null, 2)], {{type: 'application/json'}});
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'feedback.json';
      link.click();
      URL.revokeObjectURL(url);
    }}
    function copyPrompt() {{
      const payload = collectFeedback();
      const prompt = 'Please revise the pending ontology-guided annotations using this reviewer feedback:\\n' + JSON.stringify(payload, null, 2);
      navigator.clipboard.writeText(prompt).catch(function() {{
        const area = document.createElement('textarea');
        area.value = prompt;
        document.body.appendChild(area);
        area.select();
        document.execCommand('copy');
        area.remove();
      }});
    }}
  </script>
</body>
</html>"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a static HTML review page for ontology-guided annotation results.")
    parser.add_argument("--document-profile", type=Path)
    parser.add_argument("--accepted", type=Path)
    parser.add_argument("--pending", type=Path)
    parser.add_argument("--rejected", type=Path)
    parser.add_argument("--audit-report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--language", choices=["zh", "en"], default="zh")
    args = parser.parse_args()

    html_text = build_html(
        document_profile=load_json(args.document_profile),
        accepted=load_jsonl(args.accepted),
        pending=load_jsonl(args.pending),
        rejected=load_jsonl(args.rejected),
        audit_report=load_text(args.audit_report),
        language=args.language,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_text, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
