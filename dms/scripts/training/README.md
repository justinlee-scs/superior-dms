# Training Pipeline (CPU)

This folder contains scripts to turn Label Studio exports into datasets and train CPU-friendly models.

## 1) Export from Label Studio

```bash
python scripts/training/export_labelstudio.py \
  --output output/labelstudio_export.json
```

Environment variables:
- `LABEL_STUDIO_URL`
- `LABEL_STUDIO_API_TOKEN`
- `LABEL_STUDIO_PROJECT_ID`

Optional: sync project/company tags into Label Studio choices:

```bash
python scripts/labelstudio_sync_tags.py
```

## 2) Prepare datasets

```bash
python scripts/training/prepare_labelstudio.py \
  --input output/labelstudio_export.json \
  --output-dir output/training
```

Outputs:
- `output/training/doc_class.jsonl`
- `output/training/tags.jsonl`
- `output/training/handwriting.jsonl`
- `output/training/trocr.jsonl` (image_path,text)
- `output/training/field_tokens.jsonl` (token-level field labels)

If you already have a flattened annotation export like `ai-training/data/processed/annotations.json`,
you can convert it into the same training formats with:

```bash
python ai-training/scripts/prepare_sroie_invoice_warmstart_json.py \
  --input-json ai-training/data/processed/annotations.json \
  --output-dir ai-training/data/processed/dms_annotated \
  --image-root ai-training/eval-docs
```

That converter produces:
- `doc_class.jsonl`
- `tags.jsonl`
- `field_tokens.jsonl`
- `parser_report.json`

For a quick smoke test, add `--max-documents 5`.

To compare OCR text against Docling layout text, pass:

```bash
python ai-training/scripts/prepare_sroie_invoice_warmstart_json.py \
  --input-json ai-training/data/processed/annotations.json \
  --output-dir ai-training/data/processed/dms_annotated_docling \
  --image-root ai-training/eval-docs \
  --text-parser docling
```

Use `--text-parser auto` to try Docling first and fall back to OCR when Docling
cannot run in the current environment. If you have local Docling artifacts,
you can point the converter at them with `--docling-artifacts-path /path/to/artifacts`.

Due date tagging (recommended):
- Add a free-text field in Label Studio named `due_date`.
- Enter dates as `due_date:YYYY-MM-DD` (example: `due_date:2024-03-15`).
- `prepare_labelstudio.py` will normalize this into a tag and include it in `tags.jsonl`.

Example Label Studio config snippet:
```xml
<TextArea name="due_date" toName="ocr_text" label="Due date (format: due_date:YYYY-MM-DD)" rows="1" />
```

If you label illegible regions, enter `[illegible]` in the transcription.
Those rows are automatically excluded from TrOCR training/evaluation.

Optional: export PDFs to page images for handwritten OCR labeling:

```bash
python scripts/training/export_pdf_images.py \
  --input-dir /abs/path/to/pdfs \
  --output-dir output/training/ocr_images \
  --tasks output/training/ocr_tasks.json
```

## 2b) Generate ready-to-import Label Studio tasks (recommended)

```bash
bash scripts/training/generate_labelstudio_tasks.sh /abs/path/to/pdfs
```

This creates:
- `output/training/text_tasks.json` (Project A import)
- `output/training/ocr_tasks.json` (Project B import, Label Studio local-files URLs by default)

Default mode (recommended with docker-compose) does not require an OCR image HTTP server.
If you explicitly set `LS_TASK_IMAGE_MODE=localhost`, start the OCR image server before importing OCR tasks:

```bash
bash scripts/training/run_ocr_server.sh
```

## 3) Train models (CPU)

Document classifier:

```bash
python scripts/training/train_doc_classifier.py \
  --input output/training/doc_class.jsonl \
  --output output/models/doc_classifier.joblib
```

Tagger (multi-label):

```bash
python scripts/training/train_tagger.py \
  --input output/training/tags.jsonl \
  --output output/models/tagger.joblib
```

Handwriting classifier:

```bash
python scripts/training/train_handwriting.py \
  --input output/training/handwriting.jsonl \
  --output output/models/handwriting.pt
```

TrOCR fine-tune (CPU, slow):

```bash
python scripts/training/train_trocr.py \
  --input output/training/trocr.jsonl \
  --output output/models/trocr

Field extractor (token classifier):

```bash
python scripts/training/build_field_dataset.py \
  --input output/labelstudio_export.json \
  --output output/training/field_tokens.jsonl

python scripts/training/train_field_extractor.py \
  --input output/training/field_tokens.jsonl \
  --output output/models/field_extractor.joblib
```
```

## 3b) Or run everything

```bash
SKIP_TROCR=true bash scripts/training/run_training_pipeline.sh
```

Remove `SKIP_TROCR=true` to include TrOCR training (slow on CPU).

## 4) Wire models into the app

```bash
export DOC_CLASS_MODEL_PATH=/abs/path/output/models/doc_classifier.joblib
export HANDWRITING_MODEL_PATH=/abs/path/output/models/handwriting.pt
export OCR_PROVIDER=trocr_hf
export TROCR_MODEL_PATH=/abs/path/output/models/trocr
```

## 6) How training works

Label Studio does not train models by itself. You export labeled data and run the training scripts:
- `train_doc_classifier.py` for document type
- `train_tagger.py` for tags
- `train_handwriting.py` for handwriting detection
- `train_trocr.py` for OCR (handwriting)

These scripts produce model files in `output/models/`. You then point the app at them with env vars.

## 5) Evaluate models

```bash
python scripts/training/eval_doc_classifier.py \
  --input output/training/doc_class.jsonl \
  --model output/models/doc_classifier.joblib

python scripts/training/eval_tagger.py \
  --input output/training/tags.jsonl \
  --model output/models/tagger.joblib

python scripts/training/eval_tagger_thresholds.py \
  --input output/training/tags.jsonl \
  --model output/models/tagger.joblib \
  --output output/training/tag_thresholds.jsonl

python scripts/training/eval_handwriting.py \
  --input output/training/handwriting.jsonl \
  --model output/models/handwriting.pt

python scripts/training/eval_trocr.py \
  --input output/training/trocr.jsonl \
  --model output/models/trocr \
  --max-samples 50
```
