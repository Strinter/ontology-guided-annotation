# Visualization

Use the visualization role after annotation, audit, or integration has produced JSONL/Markdown outputs that are hard to inspect directly.

## Default Output

Generate a single static HTML file. It should be simple, readable, and suitable for academic review. Avoid decorative or marketing-style design.

Run:

```bash
python ontology-guided-annotation/scripts/visualize_results.py \
  --document-profile work/document_profile.json \
  --accepted dataset/accepted.jsonl \
  --pending dataset/pending_review.jsonl \
  --rejected dataset/rejected_or_negative.jsonl \
  --audit-report work/audit_report.md \
  --output work/review_dashboard.html
```

Use `--language en` only when the user asks for English. Chinese is the default.

## Page Sections

The HTML page should show:

- Summary counts for document blocks, accepted items, pending items, and rejected items.
- A preview of extracted document blocks.
- Accepted annotation examples with entities, relations, attributes, and source text.
- Pending review items with interactive decision controls.
- Rejected or negative examples.
- The audit report.

## Feedback Loop

The pending review section supports:

- accept
- modify
- reject
- defer
- free-text note

The reviewer can export `feedback.json` or copy a feedback prompt. The next annotation pass should read that feedback and update pending labels instead of starting from scratch.

## Guardrails

The HTML page is a review aid, not the source of truth. Keep JSONL files as canonical data. Treat exported feedback as reviewer decisions that still need to be integrated by Role 5.
