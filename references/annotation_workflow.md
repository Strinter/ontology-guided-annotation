# Annotation Workflow

Annotation is done in small reviewed batches. The target is training data, so consistency and provenance matter more than annotating everything quickly.

## Batch Protocol

1. Load `ontology_profile.md` and the reviewed user notes.
2. Load `document_profile.json`.
3. Select 5-20 blocks for the first batch. Use smaller batches when the ontology is new or the source is noisy.
4. Annotate only classes, relations, and attributes that are supported by source evidence.
5. Save accepted, pending, and rejected labels separately.
6. Ask the user about unresolved decisions before using the batch as training data.

## Label Status

Use one of these statuses:

- `accepted`: high confidence, ontology-compatible, evidence is clear.
- `needs_user_review`: plausible but ambiguous, low confidence, or policy-dependent.
- `rejected`: considered but not appropriate; keep useful rejected examples as negative training examples.

## User Questions

Ask focused questions with options. A good question includes:

- source block id
- exact text span
- 2-4 options
- one recommended option if there is a clear best guess
- a short reason for each option

Example:

```text
Block p1-b3: how should "hot" be labeled?
1. Hot, class under Spiciness - describes spice level.
2. Domain-specific quality - only if the ontology models this as a separate quality.
3. no entity - if this is just marketing language.
Recommended: 1.
```

## Positive Examples

Positive examples should include:

- entity spans with class labels
- relation triples where the source states the relation
- attributes where the source states literal values
- evidence and confidence

## Negative Examples

Keep useful negatives. They help train models not to over-label.

Good negative examples:

- A domain term that is not in the ontology.
- A word like "hot" used as marketing copy rather than a `Spiciness` value.
- A component/material/place mention where the relation to the target entity is not stated.

## Generic Example

Text:

```text
Example item A is made with material B and comes from place C.
```

Likely labels:

- `Example item A` -> the ontology class for the target object or work.
- `material B` -> the ontology class for material, ingredient, component, or medium.
- `place C` -> the ontology class for place, origin, region, or location.
- `Example item A hasMaterial material B` if the ontology declares a material relation.
- `Example item A hasOrigin/placeOfOrigin place C` if the source explicitly states origin.

Potential review question:

- Should the generic descriptor be labeled as a class mention, or ignored because a more specific entity mention is already present?
