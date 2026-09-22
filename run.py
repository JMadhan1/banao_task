"""CLI entrypoint. See README.md for setup.

Usage:
    python run.py digest --week 2026-06-08 [--mode rule|llm] [--out reports/digest.md]
    python run.py leaderboard --week 2026-06-08 [--out reports/leaderboard.md]
    python run.py business-case
"""
from __future__ import annotations

import argparse
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252 and
    # mangle the em-dashes/curly quotes in the generated markdown otherwise

from dotenv import load_dotenv

load_dotenv()

import pandas as pd

from src.load import load_tickets
from src.metrics import repeat_contact_analysis, agent_leaderboard
from src.digest import build_weekly_digest, digest_to_markdown


def cmd_digest(args):
    tickets = load_tickets()
    d = build_weekly_digest(tickets, args.week, mode=args.mode)
    md = digest_to_markdown(d)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Wrote {args.out}")
    else:
        print(md)


def cmd_leaderboard(args):
    tickets = load_tickets()
    board = agent_leaderboard(tickets, args.week)
    out = board["leaderboard"].to_string(index=False)
    print(f"Week {board['week_start']} to {board['week_end']}\n")
    print(out)
    if len(board["tier2_panel"]):
        print("\nTier 2 (Escalations & Warranty) — not ranked, shown separately:")
        print(board["tier2_panel"].to_string(index=False))
    if args.out:
        board["leaderboard"].to_csv(args.out, index=False)
        print(f"\nWrote {args.out}")


def cmd_business_case(args):
    tickets = load_tickets()
    result = repeat_contact_analysis(tickets)
    by_cat = result.pop("by_category")
    print(json.dumps(result, indent=2, default=str))
    print("\nBy category:")
    print(by_cat.to_string())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    pd_ = sub.add_parser("digest", help="Generate the weekly complaint digest")
    pd_.add_argument("--week", required=True, help="Week start date, YYYY-MM-DD")
    pd_.add_argument("--mode", choices=["rule", "llm"], default="rule")
    pd_.add_argument("--out", default=None)
    pd_.set_defaults(func=cmd_digest)

    pl = sub.add_parser("leaderboard", help="Agent leaderboard for one week")
    pl.add_argument("--week", required=True)
    pl.add_argument("--out", default=None)
    pl.set_defaults(func=cmd_leaderboard)

    pb = sub.add_parser("business-case", help="Repeat-contact rate & savings estimate")
    pb.set_defaults(func=cmd_business_case)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
