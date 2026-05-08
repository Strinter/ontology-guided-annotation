# Audit and Integration

The quality auditor checks each batch before the data integrator merges it into the training dataset.

## Audit Checks

Run these checks for every batch:

- Class names exist in `ontology_profile.md`.
- Object property names exist in `ontology_profile.md`.
- Data property names exist in `ontology_profile.md`.
- Object property subject class is compatible with declared domain when a domain exists.
- Object property object class is compatible with declared range when a range exists.
- Data property values have reasonable datatypes when range is declared.
- Entity spans exactly match source text.
- Relations have textual evidence, not just ontology inference.
- Low-confidence OCR blocks are not accepted without review.
- Similar mentions are labeled consistently.

## Severity

Use these severity levels in `audit_report.md`:

- `error`: invalid class/property, broken span, impossible domain/range, or missing evidence.
- `warning`: low confidence, ambiguous class, missing optional metadata, or weak OCR.
- `note`: acceptable but worth documenting for future batches.

## Audit Report Format

```markdown
# Audit Report

## Summary
- Accepted examples:
- Pending examples:
- Rejected examples:
- Errors:
- Warnings:

## Findings
| ID | Severity | Item | Issue | Recommendation |
|---|---|---|---|---|
| f-001 | error | ann-0003 | class does not exist | ask user or remap label |
```

## Integration Rules

After audit and user review:

- Write accepted examples to `dataset/accepted.jsonl`.
- Write unresolved examples to `dataset/pending_review.jsonl`.
- Write rejected or negative examples to `dataset/rejected_or_negative.jsonl`.
- Keep `dataset/decisions.md` for recurring annotation decisions.
- Export accepted examples to `training_data/` for downstream model training.
- Generate `review.md` after every integration.

## Review.md Format

```markdown
# Review

## Ready For Training
- Number of accepted examples:
- Covered classes:
- Covered relations:

## Needs User Decision
- [block id] question

## Low Confidence
- [annotation id] reason

## Conflicts
- [annotation id] issue

## Next Batch Recommendation
- suggested source files or blocks
```

## Training Data Notes

For BERT-style models, downstream users may need task-specific conversions:

- NER: BIO/BILOU sequence labels.
- Relation extraction: sentence-level pairs with subject/object spans.
- Attribute extraction: span classification or seq2seq examples.
- LLM fine-tuning: instruction/input/output JSON examples.

Keep the canonical annotation JSONL as the source of truth, then derive model-specific formats from it.

Use the bundled exporter after pending items are resolved:

```bash
python ontology-guided-annotation/scripts/export_training_data.py \
  --accepted dataset/accepted.jsonl \
  --output-dir training_data \
  --language zh
```

The exporter creates:

- `canonical_accepted.jsonl`: reviewed extraction results and the source of truth.
- `llm_finetune.jsonl`: messages-style examples for LLM fine-tuning.
- `relation_extraction.jsonl`: one row per subject-predicate-object relation.
- `ner_spans.jsonl`: text plus entity spans for later BIO/BILOU conversion.
