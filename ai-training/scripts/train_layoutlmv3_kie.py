#!/usr/bin/env python3
"""
LayoutLMv3 KIE Training — reads from field_tokens.csv
Builds on lilt_cord_warmstart (which is actually LayoutLMv3) weights.

Designed to run on CPU. Use tmux — this will take hours.

Usage:
    python train_layoutlmv3_kie.py \
        --tokens-csv ~/.LINUXPRACTICE/ai-training/data/processed/sroie_field_tokens.csv \
        --output-dir ~/.LINUXPRACTICE/ai-training/models/layoutlmv3_kie_v1

    # Resume if interrupted:
    python train_layoutlmv3_kie.py \
        --tokens-csv ... \
        --output-dir ... \
        --resume
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
from collections import defaultdict
from pathlib import Path

import torch
import numpy as np
from torch.utils.data import Dataset
from transformers import (
    LayoutLMv3TokenizerFast,
    LayoutLMv3ForTokenClassification,
    Trainer,
    TrainingArguments,
    DataCollatorForTokenClassification,
    EarlyStoppingCallback,
)

try:
    import evaluate
    SEQEVAL = evaluate.load("seqeval")
except Exception:
    SEQEVAL = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_WARMSTART = os.path.expanduser(
    "~/.LINUXPRACTICE/ai-training/models/lilt_cord_warmstart"
)
BASE_MODEL  = "microsoft/layoutlmv3-base"  # fallback if warmstart missing
MAX_SEQ_LEN = 512
BATCH_SIZE  = 1
GRAD_ACCUM  = 8
EPOCHS      = 5
LR          = 5e-5
WARMUP      = 100
VAL_SPLIT   = 0.1

# ── Label set ─────────────────────────────────────────────────────────────────

KNOWN_LABELS = [
    "O",
    "company",
    "document_date",
    "due_date",
    "grand_total",
    "bill_to",
    "invoice_number",
    "document_type",
    "account_number",
    "gst_number",
    "pst_number",
]

def build_label_maps(extra_labels: list[str]) -> tuple[dict, dict]:
    all_labels = list(dict.fromkeys(KNOWN_LABELS + extra_labels))
    label2id = {l: i for i, l in enumerate(all_labels)}
    id2label  = {i: l for i, l in enumerate(all_labels)}
    return label2id, id2label

# ── CSV loading ───────────────────────────────────────────────────────────────

def load_field_tokens(csv_path: Path) -> tuple[dict[str, list], list[str]]:
    tasks: dict[str, list] = defaultdict(list)
    all_labels: set[str] = set()

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text  = (row.get("text") or "").strip()
            label = (row.get("label") or "O").strip() or "O"
            if not text:
                continue
            try:
                x = float(row.get("x", 0))
                y = float(row.get("y", 0))
                w = float(row.get("w", 0))
                h = float(row.get("h", 0))
            except ValueError:
                continue
            task_id = row.get("task_id") or row.get("filename") or "unknown"
            tasks[task_id].append({"text": text, "x": x, "y": y, "w": w, "h": h, "label": label})
            all_labels.add(label)

    log.info(f"Loaded {len(tasks)} tasks, {sum(len(v) for v in tasks.values())} tokens")
    log.info(f"Labels found: {sorted(all_labels)}")
    return dict(tasks), sorted(all_labels)


def to_layoutlm_box(x: float, y: float, w: float, h: float) -> list[int]:
    """Convert normalized 0.0–1.0 x,y,w,h to LayoutLMv3's [x0,y0,x1,y1] 0–1000."""
    x0 = max(0, min(1000, int(x * 1000)))
    y0 = max(0, min(1000, int(y * 1000)))
    x1 = max(0, min(1000, int((x + w) * 1000)))
    y1 = max(0, min(1000, int((y + h) * 1000)))
    if x1 < x0: x1 = x0
    if y1 < y0: y1 = y0
    return [x0, y0, x1, y1]

# ── Dataset ───────────────────────────────────────────────────────────────────

class FieldTokenDataset(Dataset):
    def __init__(
        self,
        tasks: dict[str, list],
        tokenizer,
        label2id: dict[str, int],
        max_len: int = MAX_SEQ_LEN,
    ):
        self.tokenizer = tokenizer
        self.label2id  = label2id
        self.max_len   = max_len
        self.items     = list(tasks.values())

    def __len__(self):
        return len(self.items)

    def __getitem__(self, idx: int) -> dict:
        token_dicts = self.items[idx]

        words  = [t["text"] for t in token_dicts]
        boxes  = [to_layoutlm_box(t["x"], t["y"], t["w"], t["h"]) for t in token_dicts]
        labels = [self.label2id.get(t["label"], 0) for t in token_dicts]

        encoding = self.tokenizer(
            words,
            boxes=boxes,
            max_length=self.max_len,
            padding="max_length",
            truncation=True,
        )

        # Align word-level labels to subword tokens
        word_ids       = encoding.word_ids()
        aligned_labels = []
        prev_word_id   = None
        for word_id in word_ids:
            if word_id is None:
                aligned_labels.append(-100)
            elif word_id != prev_word_id:
                aligned_labels.append(labels[word_id])
            else:
                aligned_labels.append(-100)
            prev_word_id = word_id

        return {
            "input_ids":      torch.tensor(encoding["input_ids"],      dtype=torch.long),
            "attention_mask": torch.tensor(encoding["attention_mask"],  dtype=torch.long),
            "bbox":           torch.tensor(encoding["bbox"],            dtype=torch.long),
            "labels":         torch.tensor(aligned_labels,              dtype=torch.long),
        }

# ── Metrics ───────────────────────────────────────────────────────────────────

def make_compute_metrics(id2label: dict[int, str]):
    def compute_metrics(eval_pred):
        if SEQEVAL is None:
            return {}
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=-1)

        true_preds, true_labels = [], []
        for pred_seq, label_seq in zip(preds, labels):
            p_row, l_row = [], []
            for p, l in zip(pred_seq, label_seq):
                if l == -100:
                    continue
                p_row.append(id2label.get(int(p), "O"))
                l_row.append(id2label.get(int(l), "O"))
            true_preds.append(p_row)
            true_labels.append(l_row)

        result = SEQEVAL.compute(predictions=true_preds, references=true_labels)
        return {
            "f1":        result["overall_f1"],
            "precision": result["overall_precision"],
            "recall":    result["overall_recall"],
            "accuracy":  result["overall_accuracy"],
        }
    return compute_metrics

# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tokens-csv",     required=True)
    parser.add_argument("--output-dir",     required=True)
    parser.add_argument("--warmstart-from", default="")
    parser.add_argument("--epochs",         type=int,   default=EPOCHS)
    parser.add_argument("--lr",             type=float, default=LR)
    parser.add_argument("--max-len",        type=int,   default=MAX_SEQ_LEN)
    parser.add_argument("--val-split",      type=float, default=VAL_SPLIT)
    parser.add_argument("--resume",         action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Load data ─────────────────────────────────────────────────────────────
    tasks, found_labels = load_field_tokens(Path(args.tokens_csv))

    task_ids = list(tasks.keys())
    np.random.seed(42)
    np.random.shuffle(task_ids)
    split_idx   = max(1, int(len(task_ids) * (1 - args.val_split)))
    train_tasks = {t: tasks[t] for t in task_ids[:split_idx]}
    val_tasks   = {t: tasks[t] for t in task_ids[split_idx:]}
    log.info(f"Train tasks: {len(train_tasks)} | Val tasks: {len(val_tasks)}")

    # ── Label maps ────────────────────────────────────────────────────────────
    label2id, id2label = build_label_maps(found_labels)
    log.info(f"Label set ({len(label2id)}): {list(label2id.keys())}")
    (output_dir / "label_map.json").write_text(
        json.dumps({"label2id": label2id, "id2label": {str(k): v for k, v in id2label.items()}}, indent=2)
    )

    # ── Model source ──────────────────────────────────────────────────────────
    warmstart = args.warmstart_from or (
        DEFAULT_WARMSTART if Path(DEFAULT_WARMSTART).exists() else BASE_MODEL
    )
    log.info(f"Loading from: {warmstart}")

    tokenizer = LayoutLMv3TokenizerFast.from_pretrained(warmstart)
    model = LayoutLMv3ForTokenClassification.from_pretrained(
        warmstart,
        num_labels=len(label2id),
        id2label=id2label,
        label2id=label2id,
        ignore_mismatched_sizes=True,  # handles classifier head size change
    )

    # ── Datasets ──────────────────────────────────────────────────────────────
    train_ds = FieldTokenDataset(train_tasks, tokenizer, label2id, args.max_len)
    val_ds   = FieldTokenDataset(val_tasks,   tokenizer, label2id, args.max_len)

    # ── Training ──────────────────────────────────────────────────────────────
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRAD_ACCUM,
        learning_rate=args.lr,
        warmup_steps=WARMUP,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="loss",
        greater_is_better=False,
        logging_steps=10,
        save_total_limit=2,
        fp16=False,
        use_cpu=True,
        report_to="none",
        dataloader_num_workers=0,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        processing_class=tokenizer,
        data_collator=DataCollatorForTokenClassification(tokenizer),
        compute_metrics=make_compute_metrics(id2label),
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
    )

    resume_from = None
    if args.resume:
        checkpoints = sorted(output_dir.glob("checkpoint-*"), key=lambda p: int(p.name.split("-")[1]))
        if checkpoints:
            resume_from = str(checkpoints[-1])
            log.info(f"Resuming from {resume_from}")
        else:
            log.warning("--resume passed but no checkpoints found, starting fresh")

    log.info("Starting training on CPU — this will take a while. Detach tmux with Ctrl+B D.")
    trainer.train(resume_from_checkpoint=resume_from)

    log.info(f"Saving best model to {output_dir}")
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    log.info("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())