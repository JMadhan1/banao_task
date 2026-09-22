"""Theme extraction from customer_message free text.

Two modes:
  - "rule": zero-cost keyword tagger. Deterministic, always available, the default.
  - "llm":  Groq API (OpenAI-compatible), only used if GROQ_API_KEY is set in the
            environment. Batches many tickets into one prompt to keep call count (and
            cost) down, and asks for strict JSON so parsing doesn't silently drift.

The category taxonomy matches tickets.csv's own `category` column on purpose: agents
already re-tag that field on closure, which makes it the closest thing to a gold label
we have (see validation/validate.py) and keeps the digest talking Priya's own language
instead of inventing a new one.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
import urllib.error

CATEGORIES = [
    "Delivery & Shipping",
    "Billing & Payments",
    "Returns & Refunds",
    "Connectivity",
    "Charging & Battery",
    "App & Firmware",
    "Audio Quality",
    "Warranty & Repair",
    "Product Enquiry",
    "Account & Login",
    "Other",
]

# Keyword rules, checked in order — first match wins. Order matters: more specific
# categories are listed before "Other"-prone generic ones.
_RULES: list[tuple[str, list[str]]] = [
    ("Delivery & Shipping", ["delivery", "courier", "shipment", "shipping", "tracking",
                             "not delivered", "delayed", "reverse pickup", "pickup"]),
    ("Returns & Refunds", ["return", "refund", "money back", "replacement", "exchange",
                            "dead on arrival", "doa"]),
    ("Billing & Payments", ["payment", "invoice", "charged", "deducted", "upi", "refund to",
                            "duplicate payment", "coupon", "price adjust", "billing"]),
    ("Connectivity", ["bluetooth", "pairing", "won't connect", "disconnect", "connectivity",
                       "range", "cutting out"]),
    ("Charging & Battery", ["battery", "charging", "charge", "backup", "drain", "won't turn on",
                             "not switching on", "power"]),
    ("App & Firmware", ["app", "firmware", "update", "software", "bug", "crash"]),
    ("Audio Quality", ["sound", "audio", "mic", "microphone", "noise cancel", "static",
                        "distortion", "one side"]),
    ("Warranty & Repair", ["warranty", "repair", "rma", "broken", "damaged", "defect", "faulty"]),
    ("Account & Login", ["login", "log in", "account", "password", "otp", "sign in"]),
    ("Product Enquiry", ["which model", "difference between", "before i buy", "considering",
                          "planning to buy", "enquiry", "inquiry"]),
]

REPEAT_LANGUAGE_PATTERNS = [
    "already told", "already raised", "already explained", "already reported",
    "second time", "again about this", "spoke to", "told your colleague",
    "told the support", "as i said before", "as i mentioned earlier", "once again",
]


def rule_classify(message: str) -> str:
    if not isinstance(message, str) or not message.strip():
        return "Other"
    text = message.lower()
    for category, keywords in _RULES:
        if any(kw in text for kw in keywords):
            return category
    return "Other"


def has_repeat_language(message: str) -> bool:
    if not isinstance(message, str):
        return False
    text = message.lower()
    return any(p in text for p in REPEAT_LANGUAGE_PATTERNS)


GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-20b"  # cheap, fast, available on this account's Groq key


def _groq_call(prompt: str, api_key: str, model: str = GROQ_MODEL, max_tokens: int = 4000) -> str:
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": max_tokens,
            "reasoning_effort": "low",  # gpt-oss models: keep this a classifier, not a thinker
            "response_format": {"type": "json_object"},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        GROQ_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "vireo-support-digest/0.1",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            retry_after = float(e.headers.get("retry-after", 20))
            raise RateLimited(retry_after) from e
        raise
    return payload["choices"][0]["message"]["content"], payload.get("usage", {})


class RateLimited(Exception):
    def __init__(self, retry_after_s: float):
        self.retry_after_s = retry_after_s
        super().__init__(f"rate limited, retry after {retry_after_s}s")


def llm_classify_batch(
    tickets: list[dict], batch_size: int = 25, api_key: str | None = None
) -> tuple[dict[str, dict], dict]:
    """tickets: list of {"ticket_id": ..., "customer_message": ...}

    Returns (results keyed by ticket_id -> {category, theme, repeat_language}, usage totals).
    Falls back silently to rule mode per-ticket if the API key is missing or a call fails,
    so a flaky network never breaks the whole digest.
    """
    api_key = api_key or os.environ.get("GROQ_API_KEY")
    results: dict[str, dict] = {}
    usage_totals = {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0, "fallback_n": 0}

    if not api_key:
        for t in tickets:
            msg = t.get("customer_message", "")
            results[t["ticket_id"]] = {
                "category": rule_classify(msg),
                "theme": "(rule mode — no GROQ_API_KEY set)",
                "repeat_language": has_repeat_language(msg),
            }
        usage_totals["fallback_n"] = len(tickets)
        return results, usage_totals

    for i in range(0, len(tickets), batch_size):
        batch = tickets[i : i + batch_size]
        items = [
            {"ticket_id": t["ticket_id"], "message": (t.get("customer_message") or "")[:500]}
            for t in batch
        ]
        prompt = (
            "You are tagging customer support tickets for a consumer-audio brand "
            "(earbuds, headphones, speakers, watches). For each ticket below, return JSON "
            f'with key "results": a list of objects '
            '{"ticket_id": str, "category": one of ' + json.dumps(CATEGORIES) + ", "
            '"theme": a 4-8 word plain-English root cause specific to this ticket '
            '(not just the category name), '
            '"repeat_language": true if the customer explicitly says they already '
            "contacted support about this before, false otherwise}.\n\n"
            f"Tickets:\n{json.dumps(items, ensure_ascii=False)}"
        )
        try:
            for attempt in range(4):
                try:
                    content, usage = _groq_call(prompt, api_key)
                    break
                except RateLimited as rl:
                    if attempt == 3:
                        raise
                    time.sleep(rl.retry_after_s + 1)
                except Exception:
                    if attempt == 3:
                        raise
                    time.sleep(1.5 * (attempt + 1))
            parsed = json.loads(content)
            for r in parsed.get("results", []):
                tid = r.get("ticket_id")
                if tid:
                    results[tid] = {
                        "category": r.get("category", "Other"),
                        "theme": r.get("theme", ""),
                        "repeat_language": bool(r.get("repeat_language", False)),
                    }
            usage_totals["prompt_tokens"] += usage.get("prompt_tokens", 0)
            usage_totals["completion_tokens"] += usage.get("completion_tokens", 0)
            # This Groq account's free tier caps this model at 8000 tokens/minute
            # (checked via a live 429 response). Pace proactively so we don't rely on
            # hitting the limit and waiting out retry-after every single batch.
            total = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
            time.sleep(max(1.0, total / 8000 * 60))
            usage_totals["calls"] += 1
        except Exception as e:  # network hiccup, malformed JSON, whatever — never break the digest
            for t in batch:
                msg = t.get("customer_message", "")
                results[t["ticket_id"]] = {
                    "category": rule_classify(msg),
                    "theme": f"(fallback — batch call failed: {type(e).__name__})",
                    "repeat_language": has_repeat_language(msg),
                }
            usage_totals["fallback_n"] += len(batch)
        time.sleep(0.2)  # be polite to the free-tier rate limit

    # fill in anything missed by a partial/odd LLM response
    for t in tickets:
        if t["ticket_id"] not in results:
            msg = t.get("customer_message", "")
            results[t["ticket_id"]] = {
                "category": rule_classify(msg),
                "theme": "(fallback — missing from LLM response)",
                "repeat_language": has_repeat_language(msg),
            }
            usage_totals["fallback_n"] += 1

    return results, usage_totals
