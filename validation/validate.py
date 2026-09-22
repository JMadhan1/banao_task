"""How do we know the theme classifier works?

There is no hand-labeled ground truth in this data pack. But there IS the closest thing
to one already sitting in tickets.csv: the `category` field is set by the intake bot at
creation and then *corrected by the agent on closure* (README, line 17). That agent
correction is a human judgment call about what the ticket was actually about — which is
exactly what our classifier is trying to predict from the customer's opening message.

So the validation here is: on a stratified random sample, does the classifier's
prediction from customer_message agree with the agent's final category tag? This is
reproducible by anyone with the CSV (no manual labeling step to redo), and it directly
measures the thing the digest actually reports (category rollups).

Usage:
    python -m validation.validate --mode rule --n 220
    python -m validation.validate --mode llm --n 100   # costs Groq tokens, see README
"""
from __future__ import annotations

import argparse
import sys

import pandas as pd

from src.classify import rule_classify, llm_classify_batch
from src.load import load_tickets


def stratified_sample(tickets: pd.DataFrame, n: int, seed: int = 7) -> pd.DataFrame:
    """~proportional to each category's share, min 5 per category so rare categories
    (Account & Login, Product Enquiry) still get evaluated, not just steamrolled by
    Delivery & Shipping's volume."""
    cats = tickets["category"].value_counts(normalize=True)
    parts = []
    remaining = n
    for i, (cat, share) in enumerate(cats.items()):
        k = max(5, round(share * n))
        pool = tickets[tickets["category"] == cat]
        k = min(k, len(pool))
        parts.append(pool.sample(n=k, random_state=seed))
    sample = pd.concat(parts).sample(frac=1, random_state=seed)  # shuffle
    return sample.head(n) if len(sample) > n else sample


def run(mode: str, n: int) -> None:
    tickets = load_tickets()
    sample = stratified_sample(tickets, n)

    if mode == "llm":
        payload = [
            {"ticket_id": r.ticket_id, "customer_message": r.customer_message}
            for r in sample.itertuples()
        ]
        results, usage = llm_classify_batch(payload)
        preds = sample["ticket_id"].map(lambda t: results.get(t, {}).get("category", "Other"))
        print(f"Groq usage for this validation run: {usage}")
    else:
        preds = sample["customer_message"].apply(rule_classify)

    truth = sample["category"].reset_index(drop=True)
    preds = pd.Series(preds).reset_index(drop=True)

    correct = (preds == truth)
    accuracy = correct.mean()

    confusion = (
        pd.DataFrame({"true": truth, "pred": preds})
        .value_counts()
        .rename("n")
        .reset_index()
    )
    errors = confusion[confusion["true"] != confusion["pred"]].sort_values("n", ascending=False)

    print(f"\nMode: {mode}  |  Sample size: {len(sample)}  |  Accuracy: {accuracy:.1%}\n")
    print("Top confusions (true category -> predicted category, count):")
    print(errors.head(10).to_string(index=False))

    per_cat = (
        pd.DataFrame({"true": truth, "correct": correct})
        .groupby("true")["correct"]
        .agg(["mean", "count"])
        .rename(columns={"mean": "accuracy", "count": "n"})
        .sort_values("accuracy")
    )
    print("\nAccuracy by true category:")
    print(per_cat.to_string())

    report_path = f"validation/validation_report_{mode}.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Classifier validation — mode={mode}, n={len(sample)}\n\n")
        f.write(
            "Ground truth: the ticket's own `category` field (bot-tagged at intake, "
            "agent-corrected at closure — the closest thing to a human judgment call "
            "already in the data). Prediction: classifier run on `customer_message` "
            "alone, blind to the stored category.\n\n"
        )
        f.write(f"**Overall accuracy: {accuracy:.1%}**\n\n")
        f.write("## Accuracy by true category\n\n")
        f.write(per_cat.to_markdown() + "\n\n")
        f.write("## Top confusions\n\n")
        f.write(errors.head(15).to_markdown(index=False) + "\n")
    print(f"\nWrote {report_path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["rule", "llm"], default="rule")
    p.add_argument("--n", type=int, default=220)
    args = p.parse_args()
    run(args.mode, args.n)
