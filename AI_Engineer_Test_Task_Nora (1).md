# AI Engineer — Test Task

**Role:** AI / Backend Engineer (WhatsApp AI agent for real estate)
**Time budget:** ~1–2 focused days. Please do not spend more than 2 working days.
**Deliverable:** A GitHub repository (link) + a 3–5 minute screen-recording demo (Loom or similar).

---

## 1. Context (read this first)

We build **Nora** — an AI assistant that lives on a real estate agency's WhatsApp number. When a buyer messages (day or night, in any language), Nora must reply within seconds, qualify the lead, answer questions **only** from the agency's real property inventory, and hand a clean, structured lead record back to the system.

This task is a **deliberately small slice** of that product. It is designed to show us how you build an LLM agent over real data — clean code, correct retrieval, sensible prompts, and **no hallucinations**. You will **not** build the full product, connect to WhatsApp, or use any paid telephony account. Everything is mocked with simple JSON in / JSON out.

> The single most important thing we are evaluating: **the agent must never invent a property, price, or fact that is not in the data we give you.** A confident wrong answer loses a real client. Treat the hallucination guard as the headline feature, not an afterthought.

---

## 2. What you will build

A small **FastAPI** service exposing one endpoint, `POST /webhook`, that simulates an incoming WhatsApp message and returns Nora's reply plus a structured lead record.

The agent must, on each message:

1. **Detect the buyer's language** and reply in that same language (English, Hindi/Hinglish, or Arabic at minimum).
2. **Answer property questions using RAG** over the inventory we provide (`sample_properties.json`), backed by a vector store (**ChromaDB** preferred — it is our production choice).
3. **Qualify the lead** by gathering 5 things across the conversation: budget, property type, location, timeline, and purpose (live vs invest). It must remember earlier turns in the same conversation.
4. **Score the lead** as `hot` / `warm` / `cold` (rules in §5).
5. **Auto-flag Golden Visa**: if the buyer's budget is **AED 2,000,000 or more**, set `golden_visa_eligible: true` AND proactively mention UAE Golden Visa eligibility in the reply.
6. **Enforce the hallucination guard**: if no property in the inventory matches, say so honestly and offer to take their details — do **not** fabricate a listing. `matched_property_ids` must only ever contain IDs that exist in the data.

You may use **any LLM provider** (OpenAI GPT-4o is our production model and is preferred, but Gemini, Claude, or a local model are all acceptable). Use your own API key for the demo. Do not hardcode keys — read them from environment variables.

Conversation memory may be in-memory or Redis (Redis is a small bonus, not required).

---

## 3. The API contract (build exactly this)

### Request — `POST /webhook`

```json
{
  "client_id": "nora_demo",
  "from": "+919876543210",
  "message": { "type": "text", "text": "Hi, looking for a 2BHK in Marina, budget around 1.8M AED" },
  "timestamp": "2026-06-09T02:17:00Z"
}
```

- A conversation is identified by `client_id` + `from`. Multiple requests with the same pair belong to the same buyer and must share memory.
- You only need to support `"type": "text"`. (Voice notes are a bonus — see §7.)

### Response

```json
{
  "reply": "Hello! Dubai Marina is a great choice. I have a 2BHK there within your budget — shall I send the brochure? Is this for investment or to live in?",
  "language": "en",
  "lead": {
    "phone": "+919876543210",
    "budget_aed": 1800000,
    "property_type": "2BHK",
    "location": "Dubai Marina",
    "timeline": null,
    "purpose": null,
    "qualification": "warm",
    "golden_visa_eligible": false,
    "matched_property_ids": ["MAR-201", "MAR-205"]
  }
}
```

Rules for the `lead` object:
- Fields that are not yet known are `null`. They fill in as the conversation progresses across turns.
- `budget_aed` is an integer in AED (convert "1.8M" → 1800000).
- `qualification` is one of `"hot" | "warm" | "cold"`.
- `matched_property_ids` is a list of IDs **from the inventory only**. Empty list `[]` if nothing matches.

---

## 4. The data

Use the attached **`sample_properties.json`** (8 Dubai properties). Each record looks like:

```json
{
  "id": "MAR-201",
  "name": "Marina Vista Tower A",
  "type": "apartment",
  "bhk": "2BHK",
  "price_min_aed": 1750000,
  "price_max_aed": 1950000,
  "location": "Dubai Marina",
  "status": "ready",
  "amenities": ["sea view", "pool", "gym", "covered parking"],
  "rera": "RERA-DXB-44213",
  "payment_plan": "ready - full payment or mortgage",
  "rental_yield_pct": 7.0,
  "files": ["marina_vista_brochure.pdf", "marina_vista_floorplan.pdf"]
}
```

Load this into your vector store at startup (a small seed script is fine). The agent must ground every property fact (price, payment plan, RERA number, yield, location) in these records — never from the model's general knowledge.

---

## 5. Lead scoring rules (implement these so results are predictable)

Score after each message based on what is known so far:

- **`hot`** — budget is known **and** property type/location is known **and** there is at least one matching property **and** the buyer shows clear intent (a timeline within ~3 months, or explicit "ready to buy" / serious investment intent).
- **`warm`** — budget known and some criteria known, but timeline/intent is still soft or unknown.
- **`cold`** — vague enquiry, just browsing, or no budget given.

You may refine the wording, but the behavior above must be visible in your output for our test cases (§6).

---

## 6. Test conversations we will run (make these work)

We will paste these messages to your `/webhook` and check both the reply and the `lead` object. Make sure they behave sensibly.

1. **Match + budget + qualifies:**
   `"Hi, looking for a 2BHK in Marina, budget around 1.8M AED, want to buy in the next 2 months"`
   → matches MAR-201/MAR-205, fills budget/type/location/timeline, `qualification: hot`, `golden_visa_eligible: false`.

2. **Golden Visa trigger:**
   `"Interested in a 3BHK in Downtown, budget about 3.8 million AED"`
   → matches DT-335, `golden_visa_eligible: true`, and the **reply must mention the Golden Visa** proactively.

3. **Hallucination guard (no match):**
   `"Do you have a 5BHK villa on Palm Jumeirah for 500,000 AED?"`
   → there is no such property. The reply must **not** invent one. `matched_property_ids: []`. It should honestly say nothing matches and offer to take details / notify the buyer.

4. **Language switch (Hindi/Hinglish):**
   `"Bhai JVC me 1BHK chahiye, budget 850000 AED tak"`
   → reply in Hindi/Hinglish, matches JVC-118, fills budget/type/location.

5. **Multi-turn memory:**
   Message A: `"I want something in Business Bay"` → then Message B (same `from`): `"budget is 1M AED, for investment"`
   → by message B the lead has location (Business Bay) **and** budget **and** purpose=invest, and matches BB-410.

---

## 7. Optional bonus (only if you have time — not required to pass)

Pick **at most one**. We would rather have the core done cleanly than bonuses done sloppily.

- **Voice note support:** accept `"type": "audio"` with an `audio_url`, transcribe with Whisper (or any STT), then process as text.
- **Redis-backed memory** with a TTL instead of in-memory.
- **Payment-plan explainer:** when a buyer asks "what's the payment plan?", explain that property's plan in plain language from the data (e.g. 20/60/20).
- **Cost fallback:** route simple FAQ replies to a cheaper model and explain your threshold logic.

Do not attempt all of these. One, done well, with a note on why, beats four half-built ones.

---

## 8. What to deliver

A **GitHub repo** (public, or private with access shared) containing:

1. **Working code** — the FastAPI service, agent logic, RAG, and the seed script for the vector store.
2. **`README.md`** with:
   - exact local setup steps (we should be able to run it from scratch),
   - the environment variables required (`.env.example`, no real keys committed),
   - which LLM provider/model you used and why,
   - a short "Design decisions & trade-offs" section (5–10 lines) — especially **how you prevent hallucinations**,
   - what you would do next / what you cut for time.
3. **`Dockerfile`** so `docker build` + `docker run` brings the service up (or clear instructions if you chose not to dockerize).
4. **At least 4 automated tests** (pytest) covering, at minimum: a successful property match, the hallucination/no-match case, the Golden Visa flag, and language detection.
5. **A 3–5 minute screen recording** (Loom or similar) where you send the 5 test messages from §6 and talk through your code briefly. Put the link in the README.

### How to submit
Reply to this email with: (a) the repo link, (b) the demo video link, and (c) roughly how many hours you spent. That's it.

---

## 9. How we evaluate (so you know what matters)

In priority order:

1. **Correctness on the §6 test cases** — especially the hallucination guard.
2. **Code quality & structure** — readable, modular, sensible separation (routing / agent / RAG / memory), proper async, no secrets in code.
3. **RAG done right** — real retrieval grounding answers, not the LLM answering from memory.
4. **Prompt quality** — does Nora sound like a sharp, helpful Dubai real-estate assistant, and does she stay grounded?
5. **README & reproducibility** — can we run it on the first try?
6. **Tests.**

We are not grading on UI, scale, or feature count. A small, correct, honest agent beats a large one that confidently makes things up.

Good luck — we are genuinely excited to see how you build.
