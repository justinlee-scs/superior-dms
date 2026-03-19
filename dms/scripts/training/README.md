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

## 2) Prepare datasets

```bash
python scripts/training/prepare_labelstudio.py \
  --input output/labelstudio_export.json \
  --output-dir output/training
```

Outputs:
- `output/training/doc_class.csv` (text,label)
- `output/training/tags.csv` (text,tags)
- `output/training/handwriting.csv` (image_path,label)
- `output/training/trocr.jsonl` (image_path,text)

## 3) Train models (CPU)

Document classifier:

```bash
python scripts/training/train_doc_classifier.py \
  --input output/training/doc_class.csv \
  --output output/models/doc_classifier.joblib
```

Tagger (multi-label):

```bash
python scripts/training/train_tagger.py \
  --input output/training/tags.csv \
  --output output/models/tagger.joblib
```

Handwriting classifier:

```bash
python scripts/training/train_handwriting.py \
  --input output/training/handwriting.csv \
  --output output/models/handwriting.pt
```

TrOCR fine-tune (CPU, slow):

```bash
python scripts/training/train_trocr.py \
  --input output/training/trocr.jsonl \
  --output output/models/trocr
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

## 5) Evaluate models

```bash
python scripts/training/eval_doc_classifier.py \
  --input output/training/doc_class.csv \
  --model output/models/doc_classifier.joblib

python scripts/training/eval_tagger.py \
  --input output/training/tags.csv \
  --model output/models/tagger.joblib

python scripts/training/eval_handwriting.py \
  --input output/training/handwriting.csv \
  --model output/models/handwriting.pt

python scripts/training/eval_trocr.py \
  --input output/training/trocr.jsonl \
  --model output/models/trocr \
  --max-samples 50
```
