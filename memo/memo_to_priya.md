To: Priya Raman, Head of Customer Experience — Vireo Audio
From: Kabir Nanda's team
Re: The tickets thing — what we built and what it's worth

## The one number that matters

**13% of your resolved tickets are a customer contacting you again about the same
problem within 30 days — costing roughly Rs 2.9 lakh a quarter at your current volume.
Cutting that to 8% is worth about Rs 1.1 lakh a quarter.** That's the number this tool is
built to move, and it's the same thing Neha flagged anecdotally: customers who say "I
already told your colleague this." It turns out that's not noise — it's real, and mostly
silent. Only 1 in 150 customers actually *says* it out loud; the other repeat contacts
just show up as a second ticket with no complaint about the first one. Delivery &
Shipping and Billing & Payments account for over a third of it.

A live sample of the digest below is viewable here: https://claude.ai/artifact/62W5g5udm1Zi1mJmbMyahK
(private link — ask us to share it with your team if you want others to open it).

## What we built

A small tool, not a platform (you said you didn't want one). It reads your ticket
export and produces two things on request:

1. **A weekly digest** — what people are complaining about, in plain categories you
   already use, plus AI-extracted specifics ("cancel button greyed out in app," "courier
   marked delivered but no receipt") pulled straight from customer messages, so you're
   not just seeing "Delivery & Shipping: 39 tickets" but *why*.
2. **An agent leaderboard** — tickets closed per week, Tier 1 only. Per Neha's note, your
   Escalations & Warranty team is deliberately left off the ranked table — they're shown
   separately, measured on resolution days, which is how the policy doc already says
   they should be judged.

## What it costs

Nothing, if you run it in the default mode — pure keyword matching, zero API calls. The
AI-assisted mode (specific-issue extraction, better "already told you" detection) uses
Groq, run here entirely on its free tier: **Rs 0 spent**, measured at ~258,000 tokens and
about 8-9 minutes of runtime a month at your volume. The free tier does rate-limit — a
full week's digest takes a few minutes to grind through, not instant — which is a fair
trade for zero bill risk. No per-ticket charge, no surprise in November. If you ever want
it faster, upgrading is a small, checkable cost at the time you'd turn it on, not a number
we're guessing at today.

## How we know it works, and where it doesn't

We checked the AI's category guesses against what your own agents actually tagged the
ticket as when they closed it — the closest thing to a real answer key already in your
data. It agrees about 57% of the time. That sounds low, but the digest's headline numbers
(the category counts, the repeat-contact rate) never depend on the AI — they use your
agents' own tags. The AI is only used for the extra layer of specific detail underneath,
which we spot-checked by hand and found genuinely useful, if occasionally too specific or
too generic. Treat it as a research assistant's first pass, not a source of truth.

## One thing we found that you didn't ask about

653 tickets in your export are silently duplicated — filed once under the old system and
once under the new one, with the resolution time off by exactly 5.5 hours on the old
copy (a timezone conversion that didn't happen during migration). We fixed it before
computing anything above; every number in this memo is post-fix. Worth telling your IT
admin, since it'll affect any other reporting run off the same export.

## What we didn't build

No automatic weekly email, no dashboard, no dedupe of every possible cost-per-contact
disagreement (Arjun's Rs 180 vs. the policy doc's Rs 290 — we used the policy doc's
number, since that's what you cited as the source of truth). Those are quick follow-ons,
not blockers, and we'd rather hand you something real than something broader and unfinished.
