# Submission form — Vireo Audio Support Tickets (Task 1 V3)

*(`submission-form.md` was referenced in the brief but not present in the delivered pack.
Rebuilt from the exact questions listed in the assignment text.)*

## What did you build, and what business outcome does it move? State the number and the money.

A command-line tool (`run.py`) that reads Vireo's ticket export and produces (1) a weekly
digest of what customers are complaining about — structured category counts plus
AI-extracted specific issues from the free text — and (2) a Tier-1 agent leaderboard.

The number it moves: **repeat-contact rate**, defined exactly as Vireo's own policy doc
does (§10) — a customer contacting again about the same issue within 30 days of
resolution. Measured on the 18-month export (after fixing a data bug — see below):
**13.08%** of resolved/closed tickets, at an average cost of Rs 260 per repeat contact.
At Vireo's stated volume of 650 tickets/week, that's **~Rs 287,550/quarter**. Cutting the
rate to 8% is worth **~Rs 111,640/quarter**. This also directly answers Neha Kulkarni's
anecdote in the email thread about customers saying "I already told your colleague this"
— that phrasing shows up explicitly in under 1% of tickets, but the structured repeat
rate is ~19x that. Most of it is silent.

## What does one run cost, and what would a month cost at Vireo's volume (~650 tickets/week)?

**Rule mode (default): Rs 0.** Pure keyword matching, no API calls, runs fully offline.

**LLM mode (Groq, `openai/gpt-oss-20b`):** measured directly, not estimated. A real,
complete run over one week of 203 tickets (9 batches of ~25) used **12,562 prompt +
6,037 completion tokens = 18,599 tokens total**, and took **156 seconds** end to end,
zero fallbacks. Scaled linearly to Vireo's stated 650 tickets/week (~3.2x): **~59,600
tokens/week, ~258,000 tokens/month**, about **8-9 minutes of runtime/week**.

We ran this entirely on Groq's **free tier**, which costs Rs 0 — but the free tier caps
this model at **8,000 tokens/minute** (confirmed via a live 429 response from the API,
not documentation), so the tool paces itself against that budget and backs off
automatically on a 429 (see `src/classify.py`). That's a real constraint we hit and
instrumented around during this build, not a guess.

If Vireo wants it to run faster than that, or wants headroom, Groq's paid tier removes
the throttle at what is a very low per-token rate for a 20B open-weight model — we did
not commit to a specific number here on purpose, since Arjun's explicit ask was no
surprise bill, and we'd rather point you at Groq's own current pricing page at the time
you'd actually turn it on than quote a number that could be stale by November.

**No paid calls were made against any metered account for this submission** — Groq's free
tier covered everything above.

## How do you know it works? Sample size, how you checked, error rate, kind of case it gets wrong.

There's no hand-labeled ground truth in the pack, but the ticket's own `category` field is
the closest thing to one: the intake bot sets it, and the agent corrects it on closure —
a real human judgment call already sitting in the data. We validated the theme classifier
against that field on a stratified random sample (proportional to category share, minimum
5 per category so rare categories aren't ignored):

- **Rule mode** (keyword matching): n=220, **41% accuracy**.
- **LLM mode** (Groq): n=90, **57% accuracy**.

Where it gets it wrong, in order of frequency: (1) the model refuses to predict "Other" —
0% accuracy on tickets truly tagged "Other" by agents, because "Other" is a genuine
catch-all and the model reasonably tries to find a more specific bucket instead; (2)
**Delivery & Shipping vs. Returns & Refunds** confusion — a package that never arrived
gets tagged either way depending on the agent, and the model inherits that same real
ambiguity, not a bug so much as an inconsistency already present in how humans tag it.

Because of this, **the digest never uses the classifier to override the category field** —
category counts always come from the agent's own tag. The classifier is only used for
(a) the extra per-ticket "specific issue" one-liner layered under each category, which we
spot-checked by hand on ~40 tickets and found directionally right and often genuinely
more useful than the category alone, and (b) repeat-contact-language flagging, which is
cross-checked against, not a replacement for, the structured repeat-contact metric.

Full validation script and reports: `validation/validate.py`,
`validation/validation_report_rule.md`, `validation/validation_report_llm.md`.

## Did you change, narrow, or push back on the client's ask? What, when, and why.

- **Cost-per-contact number**: Arjun quoted Rs 180, Priya corrected to Rs 290 "per the
  policy doc." We used the policy doc's channel-level table (chat 210 / email 260 /
  voice 520 / social 240, blended 290) since it's the number Priya herself cited as the
  source of truth, and it's the only one with a documented source in the pack.
- **Leaderboard scope**: Neha asked that Escalations & Warranty (Tier 2) not be ranked on
  ticket count, "their cases take days by design." We excluded them from the ranked table
  entirely and gave them a separate panel measured on median resolution days, matching
  what policy §6 already prescribes ("Tier 2 agents are not to be compared with Tier 1 on
  volume metrics") — this wasn't just Neha's preference, it's already written policy.
- **"Tickets closed" definition**: took this to mean *attendance* (resolved + closed
  status, policy §10's own term), not literally status=="closed" (which in this data
  specifically means auto-closed after 72 hours with no reply). Using the narrower literal
  reading would have made the leaderboard mostly about which agents' customers went quiet,
  which isn't what anyone actually wants measured.
- **CSAT**: treated legacy rows' `csat_score == 0` as "no response" (matching README +
  policy §8), not as a real zero score, since the current helpdesk uses a genuine blank for
  the same thing and averaging the legacy 0s in would silently drag every historical CSAT
  average down.

## What is wrong with what you are handing us? Be specific.

- The repeat-contact "same issue" proxy is `customer_id + category`, not a true linked-
  ticket ID (none exists in the export). A customer with two unrelated problems in the
  same category within 30 days gets over-counted as a repeat; a genuine repeat that got
  re-tagged to a different category gets missed. This is the single biggest source of
  noise in the headline number.
- The last 30 days of tickets are excluded from the repeat-contact rate calculation
  because they're right-censored (a ticket resolved 5 days ago hasn't had its full
  30-day window play out) — correct to exclude, but it does mean the rate is always
  running about a month behind "now."
- LLM-mode theme extraction: 57% agreement with agent category tags on a 90-ticket
  sample is honest but not great. Treat the "specific issue" text as a fast first pass a
  human skims, not a source of truth.
- The rule-mode keyword classifier (41% accuracy) is genuinely weak — kept only as a
  zero-cost fallback when no API key is configured, not recommended as the primary mode.
- Groq's free-tier rate limit (8,000 TPM on this model, confirmed live) means the LLM-mode
  digest takes 10-15 minutes to run for a full week — fine for a weekly job, not fine if
  someone expects it instantly.
- No automated test suite — validated by direct inspection and the accuracy check above,
  not unit tests. Given the 5-hour cap, we prioritized a working, checked pipeline over
  test coverage.

## What did you deliberately leave out, and why that rather than something else?

Left out: any scheduling/automation (cron, email delivery), a web UI or dashboard hosting,
multi-week trend charts, and per-agent breach-credit cost rollups (the data supports it —
`transfers` and first-response breach timing are both in the export — but Priya's ask was
specifically "digest + leaderboard," and Arjun's was "no surprise bill," so we built the
two things asked for well rather than five things adequately. The breach/SLA-credit
angle is a natural next feature (Rs 350/breach, reported against the resolving agent per
policy §3) but wasn't asked for and would have doubled the surface area to test in the
time available.

## Anything you built or found that nobody asked for?

**Found**: 653 ticket_ids in the export are silently duplicated — filed once under
`source_system=helpdesk` and once under `legacy_fd`, always for tickets created before
the 14-Sep-2025 migration. For 618 of those pairs, the `legacy_fd` copy's `resolved_at` is
off by *exactly* 5.5 hours from the `helpdesk` copy — the legacy copy was never converted
from the event log's UTC to IST (policy §9 explains why this data exists; it doesn't
mention it wasn't fully fixed). Left unhandled, this double-counts ~5.5% of historical
tickets in every metric and skews handle-time/repeat-contact windows by up to 5.5 hours
for that slice. Fixed in `src/load.py` by keeping the helpdesk copy and dropping the
duplicate. All numbers in this submission are post-fix; worth flagging to Vireo's IT admin
(Sameer) since it will affect any other reporting run off the same export.

**Built, not asked for**: an SLA-breach column on the leaderboard (breach count is
"reported against the resolving agent" per policy §3, so it was nearly free to add once
the leaderboard existed) — included as an extra column, not a ranking factor.

## What did you use AI for? Which tools, where they helped, where they wasted your time, what you threw away.

- **Claude (this session)** — wrote the full pipeline (`src/`, `run.py`,
  `validation/validate.py`), read and cross-referenced the PDF policy doc, README, and
  email thread to ground every decision above, and found the duplicate-ticket data bug by
  noticing `llm_classify_batch` was silently returning fewer results than tickets sent in
  a smoke test — investigated why (duplicate ticket_ids), not assumed it was a bug in the
  batching code.
- **Groq (`openai/gpt-oss-20b`)** — the digest's theme-extraction/LLM mode itself. Free
  tier, Rs 0 spent. Wasted time: the first model choice (`llama-3.1-8b-instant`) doesn't
  exist on this account's Groq key — had to query `/v1/models` to find what was actually
  available. Also lost time to Groq's Cloudflare front-end silently 403-ing requests with
  no `User-Agent` header, and to the free tier's 8,000 TPM limit on this model, discovered
  only by hitting a live 429 mid-run — both are now handled in code (real `User-Agent`,
  retry-after-aware backoff), not just worked around by hand.
- **Discarded**: an earlier version of the classifier tried to have the LLM *replace* the
  category field outright. Dropped once validation showed only ~57% agreement — the
  digest now always trusts the agent's own category tag and uses the LLM only for the
  texture underneath it (see "how do you know it works").

Screen recording: *[link — see note in "someone picks this up on Monday" below; recording
the assistant's own screen was done outside this document]*.

## Your Public Google Drive Link

*[fill in before submitting — upload this repo/folder and paste the shareable link here]*

## Someone picks this up on Monday and you are unreachable. The three things they need to know.

1. **`PROGRESS.md` is the map.** Every non-obvious decision (the repeat-contact proxy, the
   Tier-2 exclusion, the CSAT-zero handling, the duplicate-ticket fix) is written down
   there with the reasoning, not just in code comments. Read it before changing anything.
2. **The classifier is not the source of truth for categories — the data is.** Don't be
   tempted to raise the LLM's role because 57% "feels low"; the design deliberately keeps
   category counts on the agent's own tag and only uses AI for texture underneath. If you
   want a better classifier, that's a real project (more training signal, maybe fine-
   tuning), not a prompt tweak.
3. **Groq's free tier will 429 you if you run digests back-to-back** (8,000 TPM on
   `openai/gpt-oss-20b`, confirmed live, not documented) — the code already backs off
   correctly, so don't "fix" the pacing logic in `src/classify.py` without understanding
   why it's there first.

## Honest hours spent.

*[fill in — track your own wall-clock time]*

## Github Repo Link

*[fill in after pushing — see README.md for setup instructions]*
