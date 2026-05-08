# Ontology-Guided Annotation

面向本体约束的信息抽取与训练数据标注 Skill。

这个 skill 用于把 OWL/RDF/Turtle 本体和 PDF、图片、DOCX、HTML、文本等非结构化材料结合起来，生成可人工审核的信息抽取结果，并进一步导出为 LLM 微调、关系抽取、NER/BERT 等任务可用的训练数据。

它的设计目标不是“一次性让 AI 自动标完所有数据”，而是建立一个可复核、可迭代、可教学使用的标注流水线：AI 负责读取本体、抽取候选、生成批次、做机械审核和可视化；用户负责审核本体 profile、确认模糊标注、把高质量结果沉淀为训练数据。

## 适用场景

- 基于已有 OWL 本体做实体、关系、属性抽取。
- 从 PDF、扫描图片、网页、DOCX、TXT 中构建标注数据。
- 为 BERT 系列模型准备 NER 或关系抽取训练数据。
- 为 LLM 微调准备结构化抽取样本。
- 传统文化、文化遗产、食品、生物、教育、制造、档案等任意领域的本体标注任务。

## 核心特性

- **本体读取**：从 OWL/RDF/XML 中提取类、对象属性、数据属性、domain/range、label、comment、restriction 和已有实例。
- **人工审核优先**：自动生成 `ontology_profile.md` 后，要求用户先审核本体约束，再进入标注。
- **多格式文档读取**：支持 `.txt`、`.md`、`.csv`、`.html`、`.docx`、`.pdf`、`.png`、`.jpg` 等输入。
- **小批量交互标注**：不确定的实体、关系、属性不会硬标，而是进入 `pending_review` 或用户确认问题。
- **质量审核**：检查类/属性是否存在、domain/range 是否匹配、证据是否充分、低置信度项是否误接受。
- **HTML 可视化审核**：生成静态网页，清楚展示“原文实体 -> 本体类”和“实体-关系-实体”三元组。
- **训练数据导出**：将审核通过的 accepted 数据导出为 canonical、LLM fine-tuning、relation extraction、NER span 等格式。
- **中文优先**：默认生成中文报告、中文审核问题和中文 HTML；需要英文时可传 `--language en`。

## 工作流

整个 skill 分为六个角色：

1. **Ontology Reader**  
   读取 OWL/RDF/Turtle 本体，生成 `ontology_profile.md`。

2. **Document Reader**  
   读取 PDF、图片、DOCX、HTML、TXT 等材料，生成 `document_profile.json`。

3. **Interactive Annotator**  
   小批量标注实体、类、关系和属性；不确定项交给用户确认。

4. **Quality Auditor**  
   审核标注结果是否符合本体约束和证据要求，生成 `audit_report.md`。

5. **Data Integrator**  
   整合 accepted、pending、rejected 数据，并导出训练数据。

6. **Result Visualizer**  
   生成静态 HTML 审核页面，支持用户对 pending 项做接受、修改、拒绝或暂缓反馈。

## 目录结构

```text
ontology-guided-annotation/
  SKILL.md
  README.md
  requirements.txt
  scripts/
    build_ontology_profile.py
    extract_document.py
    validate_annotations.py
    visualize_results.py
    export_training_data.py
  references/
    document_reader.md
    annotation_workflow.md
    audit_and_integration.md
    visualization.md
    output_schema.md
  evals/
    evals.json
  examples/
    generic/
      document_profile.json
      accepted.jsonl
      pending_review.jsonl
      rejected_or_negative.jsonl
      audit_report.md
      review_dashboard.html
```

## 安装依赖

基础的 OWL profile 生成主要使用 Python 标准库。文档抽取和 OCR 需要额外依赖：

```bash
pip install -r requirements.txt
```

如果需要 OCR 图片或扫描 PDF，还需要本机安装 Tesseract OCR。中文 OCR 通常还需要安装中文语言包，并在运行时指定语言，例如：

```bash
--ocr-lang chi_sim+eng
```

## 快速开始

### 1. 读取本体并生成 ontology_profile.md

```bash
python scripts/build_ontology_profile.py path/to/ontology.owl \
  --output work/ontology_profile.md \
  --language zh
```

生成后，请先人工审核 `ontology_profile.md`，确认：

- 哪些类可以直接参与标注。
- 哪些类只是抽象类、分组类或推理辅助类。
- 对象属性的 domain/range 是否适合作为标注约束。
- 是否需要补充同义词、别名、领域规则。

### 2. 抽取文档为 document_profile.json

```bash
python scripts/extract_document.py path/to/source.pdf \
  --output work/document_profile.json \
  --ocr-lang chi_sim+eng
```

`document_profile.json` 会把文档切成稳定文本块，并保留来源、页码、抽取方式和 OCR 置信度等信息。

### 3. 生成并审核标注批次

标注数据采用 JSONL，每行是一个训练样本。实体必须保留原文片段：

```json
{
  "id": "ann-0001",
  "text": "夏威夷披萨以菠萝、奶酪、番茄酱以及火腿为配料。",
  "entities": [
    {"id": "e1", "text": "夏威夷披萨", "class": "Pizza", "start": 0, "end": 5, "confidence": 0.92},
    {"id": "e2", "text": "菠萝", "class": "PineappleTopping", "start": 6, "end": 8, "confidence": 0.88}
  ],
  "relations": [
    {"subject": "e1", "predicate": "hasTopping", "object": "e2", "confidence": 0.86}
  ],
  "status": "accepted"
}
```

注意：`entities[].text` 是原文中抽到的实体片段，`entities[].class` 才是本体类。

### 4. 机械审核标注结果

```bash
python scripts/validate_annotations.py work/ontology_profile.md work/annotation_batch_001.jsonl \
  --output work/audit_report.md \
  --language zh
```

审核会检查：

- 类是否存在。
- 对象属性和数据属性是否存在。
- domain/range 是否大致匹配。
- 实体 span 是否能在原文中找到。
- 低置信度 accepted 项是否需要复核。

### 5. 生成 HTML 审核页面

```bash
python scripts/visualize_results.py \
  --document-profile work/document_profile.json \
  --accepted dataset/accepted.jsonl \
  --pending dataset/pending_review.jsonl \
  --rejected dataset/rejected_or_negative.jsonl \
  --audit-report work/audit_report.md \
  --output work/review_dashboard.html \
  --language zh
```

HTML 页面会展示：

- 文档块摘要。
- 已接受标注。
- 待审核标注。
- 拒绝或负例数据。
- 审核报告。
- 可导出的用户反馈 JSON。

实体会显示为：

```text
原文片段 -> 本体类
```

关系会显示为：

```text
主语实体 --关系--> 宾语实体
```

### 6. 导出训练数据

用户确认 pending 项并完成审核后，导出训练数据：

```bash
python scripts/export_training_data.py \
  --accepted dataset/accepted.jsonl \
  --output-dir training_data \
  --language zh
```

输出：

```text
training_data/
  canonical_accepted.jsonl
  llm_finetune.jsonl
  relation_extraction.jsonl
  ner_spans.jsonl
  README.md
```

其中：

- `canonical_accepted.jsonl`：最终规范抽取结果，作为源数据。
- `llm_finetune.jsonl`：messages 格式，适合 LLM 微调。
- `relation_extraction.jsonl`：一行一个实体-关系-实体样本。
- `ner_spans.jsonl`：实体 span 格式，可继续转换为 BIO/BILOU。

`pending_review.jsonl` 和 `rejected_or_negative.jsonl` 不会自动进入训练数据。

## 输出语言

默认输出中文：

```bash
--language zh
```

如需英文：

```bash
--language en
```

JSON 字段名保持英文，以便程序稳定读取。

## 注意事项

- 自动生成的 `ontology_profile.md` 不是最终真理，必须人工审核。
- OCR 结果可能有误，低置信度内容不应直接进入 accepted 数据。
- 关系必须有原文证据，不能只因为本体中存在该关系就自动标注。
- 可视化 HTML 是审核辅助工具，JSONL 才是规范数据源。
- 训练数据导出只应使用审核通过的 accepted 数据。
