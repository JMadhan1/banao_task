"""Load and lightly clean the Vireo Audio support data pack."""
from __future__ import annotations

import pathlib

import pandas as pd

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"

CHANNEL_COST_INR = {"chat": 210, "email": 260, "voice": 520, "social": 240}
BLENDED_COST_INR = 290
TRANSFER_COST_INR = 305
BREACH_CREDIT_INR = 350
GOODWILL_CAP_INR = 500

FIRST_RESPONSE_TARGET_MIN = {
    "chat": 15,
    "voice": 120,
    "social": 240,
    "email": 480,
}


def _dedupe_reimported_legacy_tickets(df: pd.DataFrame) -> pd.DataFrame:
    """README/policy §9: "a subset of legacy tickets was re-imported during
    reconciliation and may appear in exports under both source systems."

    Verified in this export: 653 ticket_ids appear twice, always one `helpdesk` row and
    one `legacy_fd` row, always pre-migration (created before 2025-09-14, the go-live
    date), with identical created_at. Of those, 618 pairs have a `resolved_at` that
    differs by *exactly* 5.5 hours — the legacy_fd copy's resolved_at was never
    converted from the event log's UTC to IST (policy §9: "Resolution timestamps for
    migrated tickets were reconstructed from the legacy event log, which stores UTC"),
    while the helpdesk copy has the corrected IST value. Keeping both would double-count
    every one of these tickets in every downstream metric (attendance, leaderboard,
    repeat-contact rate) and would silently corrupt handle-time/repeat-contact windows
    for the ~5% of tickets affected by up to 5.5 hours.

    Fix: keep the `helpdesk` copy and drop `legacy_fd` whenever both exist for the same
    ticket_id. This is not a guess — the two rows are the same ticket by every field
    except resolved_at, and the helpdesk copy is the reconciled one per policy §9.
    """
    dup_ids = df["ticket_id"][df["ticket_id"].duplicated(keep=False)].unique()
    if len(dup_ids) == 0:
        return df
    dup_mask = df["ticket_id"].isin(dup_ids)
    keep_dup = df[dup_mask & (df["source_system"] == "helpdesk")]
    # ticket_ids duplicated with no helpdesk copy at all (shouldn't happen, but don't
    # silently drop data if it does) fall back to keeping the first row.
    missing = set(dup_ids) - set(keep_dup["ticket_id"])
    if missing:
        fallback = df[dup_mask & df["ticket_id"].isin(missing)].drop_duplicates("ticket_id", keep="first")
        keep_dup = pd.concat([keep_dup, fallback])
    return pd.concat([df[~dup_mask], keep_dup]).sort_values("ticket_id").reset_index(drop=True)


def load_tickets() -> pd.DataFrame:
    df = pd.read_csv(
        DATA_DIR / "tickets.csv",
        parse_dates=["created_at", "first_response_at", "resolved_at"],
    )
    df = _dedupe_reimported_legacy_tickets(df)
    # Policy §8 / README: legacy rows use 0 for "no response" on csat_score, current
    # helpdesk uses a genuine blank. Normalize both to NaN so averages are correct.
    legacy = df["source_system"] == "legacy_fd"
    df.loc[legacy & (df["csat_score"] == 0), "csat_score"] = pd.NA
    df["csat_score"] = pd.to_numeric(df["csat_score"], errors="coerce")
    df["is_attendance"] = df["status"].isin(["resolved", "closed"])
    return df


def load_agents() -> pd.DataFrame:
    df = pd.read_csv(
        DATA_DIR / "agents.csv",
        parse_dates=["from_date", "to_date"],
    )
    return df


def latest_agent_roster() -> pd.DataFrame:
    """One row per agent_id: the most recent assignment (highest from_date).

    An agent keeps the same agent_id across site/shift changes (policy §7), so for
    reporting purposes (which team/tier is this agent on *now*) we take their latest row.
    """
    agents = load_agents()
    agents = agents.sort_values("from_date")
    latest = agents.groupby("agent_id", as_index=False).last()
    return latest[["agent_id", "name", "site", "team", "shift", "tier"]]


def load_customers() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "customers.csv", parse_dates=["signup_date"])


def load_products() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "products.csv", parse_dates=["launch_date"])


def load_orders() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "orders.csv", parse_dates=["order_date"])
