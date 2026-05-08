# 训练数据导出

本目录由 `export_training_data.py` 生成。

## 文件

- `canonical_accepted.jsonl`: 人工审核通过后的规范标注数据，作为源数据。
- `llm_finetune.jsonl`: 面向 LLM 指令微调的 messages 格式。
- `relation_extraction.jsonl`: 面向关系抽取任务的三元组样本。
- `ner_spans.jsonl`: 面向 NER/BERT 转换的 span 样本，可继续转换为 BIO/BILOU。

## 数量

- accepted examples: 1
- relation examples: 2
- ner examples: 1

待审核和拒绝数据不会自动进入训练数据。请先处理 `pending_review.jsonl` 和 `rejected_or_negative.jsonl`。
