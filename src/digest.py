"""Weekly digest generator: what people are complaining about, this week, in one page."""
from __future__ import annotations

import re

import pandas as pd

from src.classify import llm_classify_batch, rule_classify, has_repeat_language
from src.metrics import agent_leaderboard, find_repeat_contacts


def _redact(text: str) -> str:
    """Light PII scrub for quotes going into a digest a manager will read/forward."""
    if not isinstance(text, str):
        return ""
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[email]", text)
    text = re.sub(r"\b\d{10}\b", "[phone]", text)
    text = re.sub(r"\b[A-Z]{2}\d{6,}\b", "[order ref]", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def build_weekly_digest(
    tickets: pd.DataFrame, week_start: str, week_end: str | None = None, mode: str = "rule"
) -> dict:
    start = pd.Timestamp(week_start)
    end = pd.Timestamp(week_end) if week_end else start + pd.Timedelta(days=7)

    week = tickets[(tickets["created_at"] >= start) & (tickets["created_at"] < end)].copy()

    usage = {}
    if mode == "llm":
        payload = [
            {"ticket_id": r.ticket_id, "customer_message": r.customer_message}
            for r in week.itertuples()
        ]
        llm_results, usage = llm_classify_batch(payload)
        week["theme_category"] = week["ticket_id"].map(lambda t: llm_results.get(t, {}).get("category", "Other"))
        week["theme"] = week["ticket_id"].map(lambda t: llm_results.get(t, {}).get("theme", ""))
        week["repeat_language"] = week["ticket_id"].map(lambda t: llm_results.get(t, {}).get("repeat_language", False))
    else:
        week["theme_category"] = week["customer_message"].apply(rule_classify)
        week["theme"] = ""
        week["repeat_language"] = week["customer_message"].apply(has_repeat_language)

    # structured category rollup (agent-assigned, the reliable field)
    cat_counts = week["category"].value_counts()

    # csat this week, blanks already excluded at load time
    avg_csat = week["csat_score"].mean()

    # refund exposure this week
    refund_total = week["refund_amount_inr"].fillna(0).sum()

    # repeat-contact pairs whose REPEAT leg lands in this week
    all_repeats = find_repeat_contacts(tickets)
    repeats_this_week = all_repeats[
        all_repeats["repeat_ticket_id"].isin(week["ticket_id"])
    ]

    # top verbatim quotes + (llm mode) specific themes per top category (lightly redacted)
    top_categories = cat_counts.head(3).index.tolist()
    quotes = {}
    themes_by_cat = {}
    for cat in top_categories:
        cat_rows = week[week["category"] == cat]
        sample = cat_rows["customer_message"].dropna().head(3)
        quotes[cat] = [_redact(q)[:220] for q in sample]
        if mode == "llm":
            themes = [t for t in cat_rows["theme"] if t and not t.startswith("(")]
            # de-dup near-identical themes by lowercase first-40-chars key, keep order
            seen, uniq = set(), []
            for t in themes:
                key = t.lower()[:40]
                if key not in seen:
                    seen.add(key)
                    uniq.append(t)
            themes_by_cat[cat] = uniq[:6]

    board = agent_leaderboard(tickets, week_start, week_end)

    return {
        "week_start": str(start.date()),
        "week_end": str(end.date()),
        "n_tickets": int(len(week)),
        "category_counts": cat_counts.to_dict(),
        "avg_csat": None if pd.isna(avg_csat) else round(float(avg_csat), 2),
        "refund_total_inr": float(refund_total),
        "repeat_contacts_this_week": int(len(repeats_this_week)),
        "repeat_language_flagged": int(week["repeat_language"].sum()),
        "top_quotes": quotes,
        "themes_by_cat": themes_by_cat,
        "leaderboard": board["leaderboard"],
        "tier2_panel": board["tier2_panel"],
        "mode": mode,
        "llm_usage": usage,
    }


def digest_to_markdown(d: dict) -> str:
    lines = [
        f"# Vireo Audio — Weekly Support Digest",
        f"**Week: {d['week_start']} to {d['week_end']}**  ({d['n_tickets']} tickets created)\n",
        "## What people are complaining about",
    ]
    total = sum(d["category_counts"].values()) or 1
    for cat, n in sorted(d["category_counts"].items(), key=lambda kv: -kv[1]):
        pct = 100 * n / total
        lines.append(f"- **{cat}**: {n} tickets ({pct:.0f}%)")

    lines.append("\n## Repeat contacts (customers we made contact us twice)")
    lines.append(
        f"- {d['repeat_contacts_this_week']} repeat contacts landed this week "
        f"(policy definition: same customer/issue, within 30 days of resolution)."
    )
    lines.append(
        f"- {d['repeat_language_flagged']} tickets this week explicitly say "
        f'something like "I already told you this" — the tip of the iceberg, not the '
        f"whole problem."
    )

    lines.append("\n## Customer voice (redacted quotes, top categories)")
    for cat, qs in d["top_quotes"].items():
        lines.append(f"\n**{cat}**")
        themes = d.get("themes_by_cat", {}).get(cat)
        if themes:
            lines.append("Specific issues AI picked out this week: " + "; ".join(themes))
        for q in qs:
            lines.append(f"> {q}")

    lines.append("\n## CSAT & refunds")
    lines.append(f"- Average CSAT this week: {d['avg_csat']} (blanks excluded, per policy)")
    lines.append(f"- Refunds raised this week: Rs {d['refund_total_inr']:,.0f}")

    lines.append("\n## Agent leaderboard — Tier 1 (tickets closed this week)")
    lines.append("| Rank | Agent | Team | Site | Closed | Avg CSAT | Breaches |")
    lines.append("|---|---|---|---|---|---|---|")
    for i, row in enumerate(d["leaderboard"].itertuples(), start=1):
        csat = "-" if pd.isna(row.avg_csat) else f"{row.avg_csat:.1f}"
        lines.append(
            f"| {i} | {row.name} | {row.team} | {row.site} | {row.tickets_closed} | {csat} | {row.breaches} |"
        )

    if len(d["tier2_panel"]):
        lines.append(
            "\n*Escalations & Warranty (Tier 2) — not ranked on volume by policy; shown "
            "separately, measured on resolution days:*"
        )
        lines.append("| Agent | Cases resolved | Median days to resolve |")
        lines.append("|---|---|---|")
        for row in d["tier2_panel"].itertuples():
            md = "-" if pd.isna(row.median_resolution_days) else f"{row.median_resolution_days:.1f}"
            lines.append(f"| {row.name} | {row.cases_resolved} | {md} |")

    if d["mode"] == "llm" and d["llm_usage"]:
        u = d["llm_usage"]
        lines.append(
            f"\n*Theme extraction: Groq API, {u.get('calls', 0)} calls, "
            f"{u.get('prompt_tokens', 0)} prompt + {u.get('completion_tokens', 0)} "
            f"completion tokens, {u.get('fallback_n', 0)} tickets fell back to rule mode.*"
        )

    return "\n".join(lines)
