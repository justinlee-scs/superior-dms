# ai-training

Separate training workspace for public-dataset warm-starts (CORD first), isolated from production `dms`.

## 1) Setup

```bash
cd /home/justinlee/.LINUXPRACTICE/ai-training
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 2) Convert CORD -> DMS LiLT format

This produces `field_tokens.csv` with columns expected by `dms/scripts/training/train_lilt.py`:
`text,x,y,w,h,label,task_id,image_path`

```bash
source .venv/bin/activate
python scripts/prepare_hf_lilt_data.py \
  --dataset naver-clova-ix/cord-v2 \
  --split train \
  --max-samples 3000 \
  --output-csv data/processed/cord_field_tokens.csv \
  --image-dir data/raw/cord_images
```

## 3) Train warm-start LiLT with DMS trainer

```bash
source .venv/bin/activate
python /home/justinlee/.LINUXPRACTICE/dms/scripts/training/train_lilt.py \
  --input data/processed/cord_field_tokens.csv \
  --output models/lilt_cord_warmstart \
  --epochs 2 \
  --batch-size 2
```

## 4) Push/use model in DMS

Option A: copy to DMS output models folder.
Option B: upload to HF and set in DMS `.env`:

```env
LILT_MODEL_NAME=<your-hf-repo>
HF_TOKEN=<token>
```

## Notes

- This workspace is intentionally separate so production app files stay clean.
- Start with CORD; add DocILE/RVL-CDIP converters later using same output CSV schema.
