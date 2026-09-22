# Progress tracker — Vireo Audio support-ticket tool (Task 1 V3)

Read this first if you are picking this up cold. It says what is decided, what is built,
and what is left. Update the checkboxes as you go. Do not re-litigate a decision marked
DECIDED without a reason.

## Decisions already made (DECIDED — do not redo the analysis, just build on it)

0. **MAJOR DATA FIX (found during build, not in the original scope — see "found that nobody
   asked for" below)**: 653 ticket_ids in tickets.csv are duplicated — once under
   `source_system=helpdesk`, once under `legacy_fd`. Verified: always pre-migration
   (created before 2025-09-14), identical `created_at`, and for 618 of the 653 pairs the
   `resolved_at` differs by *exactly* 5.5 hours — the legacy_fd copy is still in UTC
   (policy §9 says legacy resolution timestamps were reconstructed from a UTC event log;
   the helpdesk copy got converted to IST, the legacy_fd copy did not). Fixed in
   `src/load.py::_dedupe_reimported_legacy_tickets` — keeps the helpdesk copy, drops the
   legacy_fd duplicate, whenever both exist. **All numbers below are POST-fix.** If you
   see a rate of ~12.35% anywhere in old notes, that was the pre-fix (duplicated,
   inflated-denominator) number — the corrected rate is 13.08%. Don't mix the two.

1. **Business goal**: repeat-contact rate. Policy §10 defines a repeat contact as the same
   customer contacting again about the same issue within 30 days of resolution, costed at
   the channel's contact cost. We proxy "same issue" as `customer_id + category` (documented
   limitation — no ticket-linking field exists). Computed on the deduplicated 18-month
   tickets.csv:
   - Stable rate (excluding the last 30 days of data, which are right-censored — a ticket
     resolved on 20 June 2026 hasn't had its full 30-day repeat window play out yet):
     **13.08%** of attendance (resolved+closed tickets). n = 10,484 stable attendances,
     1,371 flagged repeats.
   - Average cost per repeat contact (channel mix of the repeats themselves): **Rs 260**.
   - At Vireo's stated current volume of 650 tickets/week: ~85 repeat contacts/week,
     **~Rs 287,550/quarter**.
   - Target: cut to 8% → **~Rs 111,640/quarter saved**. This is the headline number for the
     memo. Source calc: `python run.py business-case`, logic in
     `src/metrics.py::repeat_contact_analysis`.
   - This also directly answers Neha Kulkarni's anecdote in email-thread.txt ("customers
     who open with 'I already told your colleague this'") — explicit phrasing like that
     appears in only ~0.7% of tickets, but the structured repeat-contact rate is ~19x that
     — most repeat contact is silent, customers don't always say it out loud.

2. **Leaderboard**: tickets closed/week per agent = attendance (resolved+closed), joined
   agent_id → agents.csv (latest roster row per agent_id for team/tier). **Escalations &
   Warranty (Tier 2) agents are excluded from the ranked leaderboard** per Neha's explicit
   request ("please don't rank my warranty team on ticket counts, their cases take days by
   design"). They still get a separate, unranked panel measured on resolution days, per
   policy §6.

3. **Weekly digest** = structured category rollup (reliable field, agent-corrected on
   closure) + AI-assisted theme/sub-issue extraction on customer_message free text, run only
   over the current week's tickets (~650/week), not the full history. Two modes:
   - `rule` mode: zero-cost keyword tagger. Always available, deterministic, the fallback.
   - `llm` mode: Groq API (key in `.env`, gitignored — **never commit it, never print it in
     full in any script/log output**), cheap open-weight model, batched prompts, strict JSON
     schema output. Optional — degrades to `rule` mode if GROQ_API_KEY is unset.

4. **Validation approach**: the agent's closing `category` tag is the closest thing to a
   gold label already in the data (bot sets it at intake, agent corrects it on closure).
   Validate the theme classifier against a stratified random sample of that field (n=200),
   report accuracy + confusion matrix + the most common failure mode. This does not require
   any new hand-labeling and is reproducible by anyone re-running `validation/validate.py`.

5. **Cost per contact conflict** (Arjun said Rs 180, Priya corrected to Rs 290 blended per
   the policy doc): went with the **policy doc's Rs 290 blended / per-channel table**
   (chat 210, email 260, voice 520, social 240) since it's the documented source of truth
   Priya herself cited. Noted as a decision in the memo, not silently resolved.

6. **CSAT**: blank = no response, excluded from averages. For `source_system == legacy_fd`,
   a score of 0 also means no response (README + policy §8) — excluded too, not treated as
   a real 0.

## Build checklist

- [x] Explore data, read README/policy/email thread
- [x] Compute repeat-contact business case numbers
- [x] Set up repo skeleton (git init, data/raw/, src/, reports/, memo/, validation/, .env gitignored)
- [x] `src/load.py` — load + clean tickets/agents/orders/customers/products, **+ the
      duplicate-legacy-ticket dedupe fix** (see item 0 above)
- [x] `src/metrics.py` — repeat-contact analysis, leaderboard, SLA breach panel
- [x] `src/classify.py` — rule-based + Groq-based theme classifier. Groq model note:
      the API key's account only has `openai/gpt-oss-20b` / `-120b`, `whisper-*`, and a
      couple of niche models available (checked via `/openai/v1/models`) — no
      `llama-3.x` text models on this account. Using `openai/gpt-oss-20b` with
      `reasoning_effort: "low"` (Groq-specific param) to stop it from burning completion
      tokens on chain-of-thought for what is just a classification task. Also: Groq's
      Cloudflare front-end 403s any request without a real `User-Agent` header — fixed,
      but worth knowing if this breaks again on a different network.
- [x] `src/digest.py` — weekly digest generator (markdown; HTML/artifact version pending)
- [x] `run.py` — CLI entrypoint (`python run.py digest --week 2026-06-08`, `python run.py leaderboard --week ...`, `python run.py business-case`) — all three smoke-tested and working
- [x] `validation/validate.py` — classifier accuracy check against agent category tags.
      Results: rule mode 41% (n=220), llm mode 57% (n=90). Reports written to
      `validation/validation_report_{rule,llm}.md`.
- [x] `requirements.txt`
- [x] `README.md` (root, run-from-clean-machine instructions)
- [x] `memo/memo_to_priya.md` — one-page, non-technical, links the HTML dashboard artifact
- [x] `submission-form.md` — filled in (not included in the pack; template built from the
      brief's own questions). **Two fields still need the human user's own input**:
      "Honest hours spent" and the Google Drive / GitHub links — an AI assistant cannot
      truthfully fill those in.
- [x] Sample output committed to `reports/`: `digest_2026-06-08_rule.md`,
      `digest_2026-06-08_llm.md`, `digest_data.json`, `digest_dashboard.html` (styled,
      also published as a Claude Artifact — link in the memo)
- [x] git commits at each milestone
- [ ] Screen recording — **this cannot be done by an AI assistant; the user must record
      their own screen**. Flagged clearly in the final summary. Not blocking the rest.
- [ ] GitHub push — **only after explicit user confirmation** (publishing action). Repo is
      committed locally regardless.

## Real numbers discovered while testing the Groq integration (worth knowing before touching src/classify.py)

- This Groq account's key only has access to `openai/gpt-oss-20b`, `openai/gpt-oss-120b`,
  `whisper-*`, and a couple of niche models — checked live via `/openai/v1/models`, not
  assumed. No `llama-3.x` chat models on this account.
- Groq's Cloudflare front-end 403s (error 1010) any request with urllib's default
  `User-Agent` — fixed by sending a real one.
- This model is capped at **8,000 tokens/minute on the free tier** (confirmed via a live
  429 response, not docs). `src/classify.py` now paces itself against that budget after
  each call and does retry-after-aware backoff on a 429. A full real week (203 tickets, 9
  batches) ran clean end to end: 12,562 prompt + 6,037 completion tokens, 156 seconds,
  zero fallbacks.
- `reasoning_effort: "low"` is a Groq-specific param for gpt-oss models — without it the
  model burns a large chunk of `max_tokens` on chain-of-thought before ever emitting the
  JSON, which was truncating results in early tests.

## Known limitations / things intentionally left out (for the memo's "what's wrong" section)

- Repeat-contact "same issue" proxy (customer_id + category) will under- or over-count vs.
  a true linked-ticket ID — nearest available proxy given the schema.
- Last 30 days of tickets are right-censored for repeat-contact purposes — excluded from the
  rate calculation, noted wherever the rate is reported.
- Legacy (pre-14-Sep-2025, `source_system == legacy_fd`) resolution timestamps were
  reconstructed from a UTC event log per policy §9 — treated as IST like everything else
  per the README's instruction ("timestamps are as displayed in the helpdesk"), but this is
  a known soft spot, flagged, not fixed.
- The duplicate-ticket fix (item 0) only catches EXACT ticket_id collisions across source
  systems. If any legacy ticket was re-imported with a *different* ticket_id (not just
  duplicated under the same one), it would not be caught — no way to detect that from this
  export.
- Weekly digest LLM mode: smoke-tested on real tickets (25-ticket batch), works, but not yet
  run end-to-end through `run.py digest --mode llm` for a full week — do that before
  claiming it's fully verified. Groq call costs ~1300 prompt + ~600-900 completion tokens
  per 25-ticket batch on gpt-oss-20b.
