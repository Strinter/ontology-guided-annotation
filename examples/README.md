# Examples

These files are domain-neutral examples for testing the visualization workflow.

They are not a recommended ontology or annotation policy. Replace `DomainItem`, `Material`, `Place`, `hasMaterial`, and `hasOrigin` with classes and properties from the user's reviewed ontology profile.

Generate a review dashboard:

```bash
python ontology-guided-annotation/scripts/visualize_results.py \
  --document-profile ontology-guided-annotation/examples/generic/document_profile.json \
  --accepted ontology-guided-annotation/examples/generic/accepted.jsonl \
  --pending ontology-guided-annotation/examples/generic/pending_review.jsonl \
  --rejected ontology-guided-annotation/examples/generic/rejected_or_negative.jsonl \
  --audit-report ontology-guided-annotation/examples/generic/audit_report.md \
  --output ontology-guided-annotation/examples/generic/review_dashboard.html
```
