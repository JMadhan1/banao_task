# Vireo Audio — Support Ticket Digest & Leaderboard

A small tool that turns 18 months of support tickets into (1) a weekly digest of what
customers are actually complaining about and (2) a Tier-1 agent leaderboard — built for
Priya Raman / Vireo Audio's support desk. See [`memo/memo_to_priya.md`](memo/memo_to_priya.md)
for the business case in plain English, and [`PROGRESS.md`](PROGRESS.md) for every
decision this build made and why (read that first if you're picking this up cold).

## What this is (and isn't)

It is a command-line tool that reads the CSV export and writes a markdown report. It is
**not** a platform, a dashboard, or a scheduled job — Priya asked for "keep it simple, I
don't need a platform" (see `data/raw/email-thread.txt`), so this respects that.

## Setup (clean machine)

Requires Python 3.10+.

```bash
pip install -r requirements.txt
```

The AI-assisted theme extraction is optional. Without an API key the tool runs fully
offline in `rule` mode (keyword-based, zero cost, deterministic). To enable the richer
`llm` mode, copy `.env.example` to `.env` and add a [Groq](https://console.groq.com) API
key (Groq, not OpenAI/Anthropic — chosen because it's free-tier-friendly and fast; see
the memo for why cost mattered here):

```bash
cp .env.example .env
# edit .env: GROQ_API_KEY=gsk_...
```

`.env` is gitignored — never commit a real key.

## Run it

```bash
# The business case: current repeat-contact rate and what fixing it is worth
python run.py business-case

# Weekly complaint digest (rule mode: free, offline)
python run.py digest --week 2026-06-08 --mode rule --out reports/digest.md

# Weekly complaint digest (llm mode: needs GROQ_API_KEY, adds specific-issue extraction
# and better repeat-contact-language detection on top of the same structured rollup)
python run.py digest --week 2026-06-08 --mode llm --out reports/digest.md

# Agent leaderboard for one week (Tier 1 only — see memo for why)
python run.py leaderboard --week 2026-06-08
```

`--week` is any Monday-ish start date; the tool takes the following 7 days. Two sample
outputs for the week of 2026-06-08 are already committed under `reports/` (one per mode)
so you can see the shape of the output without running anything. There's also a styled
HTML version of the same week at `reports/digest_dashboard.html` — open it directly in a
browser, or use `python -m http.server` and navigate to it.

## How to know it's working

```bash
python -m validation.validate --mode rule --n 220
python -m validation.validate --mode llm --n 90     # costs a handful of Groq calls
```

This checks the theme classifier against the ticket's own `category` field — set by the
intake bot and *corrected by the agent on closure* (README §"category"), which is the
closest thing to a human-labeled ground truth already sitting in the data. Results are
written to `validation/validation_report_<mode>.md`. Headline numbers as of this build:
rule mode 41% accuracy, llm mode 57% — both well short of perfect, and the memo explains
why that's fine (the digest's category counts never depend on the classifier; only the
extra per-ticket "specific issue" text does — see `PROGRESS.md` decision log).

## Project layout

```
data/raw/          the untouched data pack (tickets, agents, orders, customers, products,
                    the policy PDF, the email thread) — read from here, never written to
src/load.py         loading + the legacy-duplicate-ticket fix (see PROGRESS.md item 0)
src/metrics.py      repeat-contact business case, agent leaderboard, SLA breach panel
src/classify.py     rule-based keyword tagger + optional Groq LLM theme extraction
src/digest.py       assembles the weekly digest
run.py              CLI entrypoint
validation/         accuracy check against the agent's own category tags
reports/            sample output, already generated and committed
memo/               the one-page memo to Priya
PROGRESS.md         decision log — read this if continuing this work
```

## What's deliberately not here

No web UI, no database, no scheduler, no auth. This runs on-demand from a terminal. If
Vireo wants it running automatically every Monday morning, that's a follow-on ask, not a
default — see the memo.
