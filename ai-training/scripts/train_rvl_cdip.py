#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from datasets import load_dataset
from huggingface_hub import HfApi, hf_hub_url
from transformers import (
    AutoImageProcessor,
    AutoModelForImageClassification,
    Trainer,
    TrainingArguments,
)
from transformers.models.auto.configuration_auto import AutoConfig

try:
    import evaluate
except Exception:
    evaluate = None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", default="rvl_cdip", help="HF dataset id")
    p.add_argument(
        "--dataset-parquet-repo",
        default="chainyo/rvl-cdip",
        help="HF dataset repo that has Parquet conversion files.",
    )
    p.add_argument("--model", default="google/vit-base-patch16-224")
    p.add_argument(
        "--output",
        default="/home/justinlee/.LINUXPRACTICE/ai-training/models/rvl_cdip_layoutlmv3",
    )
    p.add_argument("--train-split", default="train")
    p.add_argument("--eval-split", default="test")
    p.add_argument("--max-train", type=int, default=20000)
    p.add_argument("--max-eval", type=int, default=2000)
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--batch-size", type=int, default=2)
    p.add_argument("--lr", type=float, default=2e-5)
    args = p.parse_args()

    try:
        ds = load_dataset(args.dataset)
    except RuntimeError as exc:
        message = str(exc)
        if "Dataset scripts are no longer supported" not in message:
            raise

        print(
            f"Falling back to parquet loader from '{args.dataset_parquet_repo}' "
            "because script-based datasets are unsupported in this datasets version."
        )
        api = HfApi()
        files = api.list_repo_files(
            repo_id=args.dataset_parquet_repo,
            repo_type="dataset",
            revision="refs/convert/parquet",
        )

        split_files: dict[str, list[str]] = {"train": [], "test": [], "validation": []}
        for f in files:
            if not f.endswith(".parquet"):
                continue
            lower = f.lower()
            if (
                "/train/" in lower
                or "-train-" in lower
                or "partial-train/" in lower
                or "/partial_train/" in lower
            ):
                split = "train"
            elif (
                "/test/" in lower
                or "-test-" in lower
                or "partial-test/" in lower
                or "/partial_test/" in lower
            ):
                split = "test"
            elif (
                "/validation/" in lower
                or "-validation-" in lower
                or "/val/" in lower
                or "-val-" in lower
                or "partial-val/" in lower
                or "/partial_val/" in lower
            ):
                split = "validation"
            else:
                continue
            split_files[split].append(
                hf_hub_url(
                    repo_id=args.dataset_parquet_repo,
                    filename=f,
                    repo_type="dataset",
                    revision="refs/convert/parquet",
                )
            )

        data_files = {k: v for k, v in split_files.items() if v}
        if "train" not in data_files:
            raise RuntimeError(
                "Could not find parquet train split files in "
                f"{args.dataset_parquet_repo}@refs/convert/parquet"
            )
        ds = load_dataset("parquet", data_files=data_files)
    train_ds = ds[args.train_split]
    eval_ds = ds[args.eval_split]

    if args.max_train > 0:
        train_ds = train_ds.select(range(min(args.max_train, len(train_ds))))
    if args.max_eval > 0:
        eval_ds = eval_ds.select(range(min(args.max_eval, len(eval_ds))))

    label_feature = train_ds.features["label"]
    label_names = label_feature.names
    num_labels = len(label_names)
    label2id = {n: i for i, n in enumerate(label_names)}
    id2label = {i: n for i, n in enumerate(label_names)}

    cfg = AutoConfig.from_pretrained(args.model)
    if getattr(cfg, "model_type", "") == "layoutlmv3":
        raise ValueError(
            "layoutlmv3 is not compatible with AutoModelForImageClassification in this script. "
            "Use an image classification backbone (e.g. google/vit-base-patch16-224, "
            "microsoft/resnet-50) for RVL-CDIP classification."
        )

    processor = AutoImageProcessor.from_pretrained(args.model)
    model = AutoModelForImageClassification.from_pretrained(
        args.model,
        num_labels=num_labels,
        label2id=label2id,
        id2label=id2label,
        ignore_mismatched_sizes=True,
    )

    def preprocess(batch):
        images = [img.convert("RGB") for img in batch["image"]]
        enc = processor(images=images, return_tensors="np")
        enc["labels"] = np.array(batch["label"])
        return enc

    train_ds = train_ds.map(preprocess, batched=True, remove_columns=train_ds.column_names)
    eval_ds = eval_ds.map(preprocess, batched=True, remove_columns=eval_ds.column_names)

    metric = evaluate.load("accuracy") if evaluate else None

    def compute_metrics(eval_pred):
        if metric is None:
            return {}
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=-1)
        return metric.compute(predictions=preds, references=labels)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.lr,
        num_train_epochs=args.epochs,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_steps=50,
        fp16=False,
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        compute_metrics=compute_metrics,
    )

    trainer.train()
    trainer.save_model(str(output_dir))
    processor.save_pretrained(str(output_dir))
    print(f"Saved model to: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
