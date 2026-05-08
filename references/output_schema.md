# Output Schemas

Use these schemas as conventions, not as a substitute for user review.

## Annotation JSONL

Each line is one training example:

```json
{
  "id": "ann-0001",
  "source": {
    "document_id": "doc-001",
    "block_id": "p1-b1",
    "path": "source.pdf",
    "page": 1
  },
  "text": "The source text span for this example.",
  "entities": [
    {
      "id": "e1",
      "text": "surface form",
      "class": "OntologyClassName",
      "start": 0,
      "end": 12,
      "confidence": 0.9,
      "evidence": "short reason"
    }
  ],
  "relations": [
    {
      "subject": "e1",
      "predicate": "objectPropertyName",
      "object": "e2",
      "confidence": 0.85,
      "evidence": "short reason"
    }
  ],
  "attributes": [
    {
      "entity": "e1",
      "predicate": "dataPropertyName",
      "value": "literal value",
      "datatype": "xsd:string",
      "confidence": 0.8
    }
  ],
  "status": "accepted | needs_user_review | rejected"
}
```

In the HTML review page, `entities[].text` is displayed as the extracted source mention and `entities[].class` is displayed as the ontology class. Relations are displayed as triples by resolving `relations[].subject` and `relations[].object` against entity ids.

Do not put only ontology class names in `entities[].text`. For example, use `"text": "夏威夷披萨", "class": "Pizza"` rather than `"text": "Pizza", "class": "Pizza"` unless the original source literally says "Pizza".

## Training Exports

After review, `export_training_data.py` creates:

```text
training_data/
  canonical_accepted.jsonl
  llm_finetune.jsonl
  relation_extraction.jsonl
  ner_spans.jsonl
  README.md
```

Only reviewed `accepted` data should enter these exports. `needs_user_review` examples must stay pending until resolved.

## Review Item

```json
{
  "id": "q-0001",
  "source": {"document_id": "doc-001", "block_id": "p1-b1"},
  "issue": "ambiguous_class",
  "text": "surface form",
  "options": [
    {"label": "ClassA", "reason": "why this may be right"},
    {"label": "ClassB", "reason": "why this may be right"},
    {"label": "no label", "reason": "why it may be excluded"}
  ],
  "recommended_option": "ClassA"
}
```
