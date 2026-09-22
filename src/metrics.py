"""Core metrics: repeat-contact business case, agent leaderboard, SLA breach panel.

All money figures are INR. Cost table and definitions come straight from
support-policy.pdf (see docstrings for section references) rather than being invented.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.load import (
    CHANNEL_COST_INR,
    FIRST_RESPONSE_TARGET_MIN,
    BREACH_CREDIT_INR,
    latest_agent_roster,
)

REPEAT_WINDOW_DAYS = 30


def find_repeat_contacts(tickets: pd.DataFrame) -> pd.DataFrame:
    """Flag repeat contacts per policy §10: same customer, same issue, contacts again
    within 30 days of resolution. "Same issue" has no direct field in this export, so we
    proxy it as (customer_id, category) — the nearest available field, and a documented
    limitation (a customer with two genuinely different problems in the same category
    within 30 days will be over-counted; a mis-tagged repeat will be missed).

    Returns one row per repeat-contact PAIR: the original ticket_id, the repeat ticket_id,
    the channel and cost of the repeat contact, and the category.
    """
    att = tickets[tickets["is_attendance"] & tickets["resolved_at"].notna()].copy()
    att = att.sort_values(["customer_id", "category", "created_at"])

    rows = []
    for (_cust, _cat), g in att.groupby(["customer_id", "category"], sort=False):
        if len(g) < 2:
            continue
        g = g.sort_values("created_at")
        created = g["created_at"].to_numpy()
        resolved = g["resolved_at"].to_numpy()
        channel = g["channel"].to_numpy()
        tid = g["ticket_id"].to_numpy()
        for i in range(len(g) - 1):
            if pd.isna(resolved[i]):
                continue
            window_end = resolved[i] + np.timedelta64(REPEAT_WINDOW_DAYS, "D")
            if resolved[i] < created[i + 1] <= window_end:
                rows.append(
                    {
                        "orig_ticket_id": tid[i],
                        "repeat_ticket_id": tid[i + 1],
                        "category": _cat,
                        "orig_resolved_at": resolved[i],
                        "repeat_channel": channel[i + 1],
                        "repeat_cost_inr": CHANNEL_COST_INR.get(channel[i + 1], 290),
                    }
                )
    return pd.DataFrame(rows)


def repeat_contact_analysis(
    tickets: pd.DataFrame,
    current_weekly_volume: int = 650,
    target_rate: float = 0.08,
    censor_days: int = 30,
) -> dict:
    """The business-case number for the memo.

    Excludes the last `censor_days` of resolved tickets from the rate calculation: a
    ticket resolved 5 days ago hasn't had its full 30-day repeat-contact window play out,
    so including it understates the true rate (visible in the raw monthly trend — the
    most recent month always looks artificially clean).
    """
    att = tickets[tickets["is_attendance"] & tickets["resolved_at"].notna()].copy()
    max_date = tickets["created_at"].max()
    cutoff = max_date - pd.Timedelta(days=censor_days)
    stable = att[att["resolved_at"] <= cutoff]

    repeats = find_repeat_contacts(tickets)
    stable_ids = set(stable["ticket_id"])
    stable_repeats = repeats[repeats["orig_ticket_id"].isin(stable_ids)]

    current_rate = len(stable_repeats) / len(stable) if len(stable) else 0.0
    avg_repeat_cost = (
        stable_repeats["repeat_cost_inr"].mean() if len(stable_repeats) else 290.0
    )

    weekly_repeats_now = current_weekly_volume * current_rate
    weekly_cost_now = weekly_repeats_now * avg_repeat_cost
    quarterly_cost_now = weekly_cost_now * 13

    weekly_repeats_target = current_weekly_volume * target_rate
    weekly_cost_target = weekly_repeats_target * avg_repeat_cost
    quarterly_cost_target = weekly_cost_target * 13

    by_category = (
        stable_repeats.groupby("category")
        .agg(repeat_contacts=("repeat_ticket_id", "count"), cost_inr=("repeat_cost_inr", "sum"))
        .sort_values("repeat_contacts", ascending=False)
    )

    return {
        "window_days": REPEAT_WINDOW_DAYS,
        "stable_attendance_n": int(len(stable)),
        "stable_repeat_n": int(len(stable_repeats)),
        "current_rate": current_rate,
        "avg_repeat_cost_inr": float(avg_repeat_cost),
        "current_weekly_volume": current_weekly_volume,
        "target_rate": target_rate,
        "quarterly_cost_now_inr": float(quarterly_cost_now),
        "quarterly_cost_target_inr": float(quarterly_cost_target),
        "quarterly_savings_inr": float(quarterly_cost_now - quarterly_cost_target),
        "by_category": by_category,
    }


def agent_leaderboard(tickets: pd.DataFrame, week_start: str, week_end: str | None = None) -> dict:
    """Tickets closed (attendance = resolved+closed) per agent for one week.

    Escalations & Warranty (Tier 2) agents are excluded from the ranked table per policy
    §6 ("Tier 2 agents are not to be compared with Tier 1 on volume metrics") and Neha
    Kulkarni's explicit request in email-thread.txt. They appear in a separate,
    unranked panel instead, measured on median resolution days as the policy prescribes.
    """
    start = pd.Timestamp(week_start)
    end = pd.Timestamp(week_end) if week_end else start + pd.Timedelta(days=7)

    att = tickets[
        tickets["is_attendance"]
        & (tickets["resolved_at"] >= start)
        & (tickets["resolved_at"] < end)
    ].copy()

    roster = latest_agent_roster()
    att = att.merge(roster, on="agent_id", how="left")

    breaches = att.copy()
    breaches["target_min"] = breaches["channel"].map(FIRST_RESPONSE_TARGET_MIN)
    breaches["response_min"] = (
        breaches["first_response_at"] - breaches["created_at"]
    ).dt.total_seconds() / 60
    breaches["breached"] = breaches["response_min"] > breaches["target_min"]

    tier1 = att[att["tier"] == 1]
    board = (
        tier1.groupby(["agent_id", "name", "team", "site"])
        .agg(
            tickets_closed=("ticket_id", "count"),
            avg_csat=("csat_score", "mean"),
            breaches=("ticket_id", lambda s: breaches.loc[s.index, "breached"].sum()),
        )
        .reset_index()
        .sort_values("tickets_closed", ascending=False)
    )
    board["breach_credit_inr"] = board["breaches"] * BREACH_CREDIT_INR

    tier2 = att[att["tier"] == 2]
    tier2_panel = (
        tier2.groupby(["agent_id", "name", "team"])
        .agg(
            cases_resolved=("ticket_id", "count"),
            median_resolution_days=(
                "resolved_at",
                lambda s: (
                    (att.loc[s.index, "resolved_at"] - att.loc[s.index, "created_at"])
                    .dt.total_seconds()
                    / 86400
                ).median(),
            ),
        )
        .reset_index()
    )

    return {
        "week_start": str(start.date()),
        "week_end": str(end.date()),
        "leaderboard": board,
        "tier2_panel": tier2_panel,
    }
