# Document Reader

The document reader turns heterogeneous source files into `document_profile.json`. Annotation should use `document_profile.json`, not the raw files directly, because every label needs stable provenance.

## Tool Selection

Use the simplest reliable path first:

| Input | First choice | Fallback |
|---|---|---|
| `.txt`, `.md`, `.csv` | Python text reader | manual encoding selection |
| `.html`, `.htm` | BeautifulSoup if installed, otherwise built-in HTML stripping | browser-rendered extraction if content is dynamic |
| `.docx` | `python-docx` | pandoc or manual zip/XML extraction |
| text PDF | PyMuPDF (`fitz`) text extraction | pdfplumber or pypdf |
| scanned PDF | render pages with PyMuPDF, then OCR | ask user to provide page images |
| `.png`, `.jpg`, `.jpeg` | OCR | multimodal inspection when OCR is weak |

## Integrated PDF/OCR Policy

This skill should be self-contained for students. Do not require users to install separate `pdf` or `ocr-document-processor` skills.

If those skills are present locally, their workflow can be used as background guidance, but do not copy proprietary files from them. For distributable classroom use, keep our own extraction script and document the dependencies openly.

Use `scripts/extract_document.py` as the default local extractor:

```bash
python ontology-guided-annotation/scripts/extract_document.py source.pdf --output work/document_profile.json --ocr-lang eng
```

For Chinese or multilingual OCR, pass the installed Tesseract language codes:

```bash
python ontology-guided-annotation/scripts/extract_document.py scan.png --output work/document_profile.json --ocr-lang chi_sim+eng
```

## Provenance Requirements

Every block should preserve:

- `document_id`
- `block_id`
- `source`
- `page` when available
- `text`
- `layout_type`
- `confidence`
- `extraction_method`

For OCR outputs, keep lower confidence visible. Do not silently rewrite or normalize uncertain OCR text if it changes the source evidence.

## Block Granularity

Prefer paragraph-sized blocks. If a PDF page has no paragraph separation, split on blank lines or short line groups.

Avoid very large blocks because they make span offsets unreliable and make user review harder.

## Scanned Material Caveats

Flag blocks for review when:

- OCR confidence is below the configured threshold.
- The page is rotated, blurred, handwritten, or has dense tables.
- The text mixes multiple languages or unusual symbols.
- Ingredient lists or names are split across columns.

The downstream annotator should not accept labels from weak OCR without evidence review.
