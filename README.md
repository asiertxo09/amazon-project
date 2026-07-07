# Enterprise Opportunity Copilot (EOC)

A **copilot, not an autopilot**: it does the multi-day reconciliation work an Amazon Shipping
Business Developer would otherwise do by hand, and hands back a structured, evidence-backed
recommendation for a human to decide on — every number traceable, every contradiction in the
source material surfaced rather than silently resolved.

Built for the *Amazon Shipping / IE University Industry Challenge 2026*.

## Value Proposition

Turn a raw, messy opportunity — a formal RFQ, a pile of CRM notes, an email thread, a pasted
brief — into a complete, defensible commercial recommendation in seconds instead of days:

- **One input, nine outputs.** Executive summary, opportunity score, risk assessment, three
  guardrail-compliant pricing scenarios, commercial strategy, follow-up actions, a trained
  win-probability model, a client-ready pitch deck, and a full source list — generated together,
  from one shared analysis, not nine separate manual steps.
- **Consistent, not vibes-based.** Pricing comes from a deterministic cost engine and financial
  guardrails, not an LLM guessing at numbers; win probability comes from a classifier trained on
  historical outcomes, not a prompt.
- **Honest about ambiguity.** When the source material contradicts itself, the copilot says so
  instead of picking a number and moving on — the single biggest difference between something a
  Business Developer can actually trust and something that looks confident but isn't.
- **Traceable end to end.** Every claim in the output cites the document (and slide/section) it
  came from, so a human reviewer can verify the reasoning before it reaches a client or leadership.

## The Amazon Problem We Solve

Amazon Shipping is Amazon's last-mile delivery service for external businesses, and the last-mile
component of the newer Amazon Supply Chain Services (ASCS) offering. Spain alone generates an
estimated 1.3–1.5 billion parcels a year, in a last-mile market worth €4B+ — and Amazon Shipping's
Enterprise Business Development team is actively growing its book of business across Spain and
Portugal against that opportunity.

The bottleneck isn't demand, it's **decision-making throughput**. Qualifying a single enterprise
opportunity today means a Business Developer manually reading and reconciling RFQs, discovery-call
notes, emails, CRM records, service-capability docs, pricing workbooks, and historical
win/loss data — by hand, across Sales, Pricing, Operations and Finance — before a recommendation
can even reach leadership. Industry estimates put **30–40% of enterprise BD time** on this
gathering-and-reconciling work rather than selling, and preparing the analysis behind one
opportunity can take several days, inside deal cycles that already run months to years.

Compounding this: opportunities never arrive in one clean format. A tender document, a fragmentary
CRM/email pack, a call transcript, a spreadsheet — sometimes several of these at once, sometimes
containing figures that don't agree with each other. A manual process has no consistent way to
flag that, price around it, or move fast without cutting corners on rigor.

**The Enterprise Opportunity Copilot exists to remove that bottleneck**: same rigor a good BD
would apply, in seconds instead of days, with the underlying reasoning left visible rather than
hidden inside one person's judgment call.

## Project Description

EOC is a two-service application — a FastAPI analysis backend and a React frontend — built around
one shared contract: the backend does all the reasoning and returns a single structured JSON
object; the frontend is a pure renderer with no business logic of its own.

**Two ways in:**
- Pick one of two challenge opportunities as a live demo — **Tecnomania** (a clean, structured
  electronics-retailer RFQ) or **Pink Papaya** (a fragmentary discovery pack that deliberately
  stress-tests contradiction-handling: conflicting daily-volume figures, and the two co-founders
  disagreeing on whether France coverage is a hard requirement).
- Or paste a freeform opportunity brief of your own — the same pipeline runs end to end on
  arbitrary text, not just the two canned cases.

**What comes back**, rendered across a dashboard and a dedicated pitch-deck view:

| # | Output | What it is |
|---|--------|------------|
| 1 | Executive Summary | 3–5 sentence framing of the opportunity |
| 2 | Opportunity Score | Strong / Moderate / Weak, with rationale |
| 3 | Risk Assessment | Operational, Commercial, and Financial risks with severity and evidence |
| 4 | Pricing Scenarios | Aggressive → Balanced → Conservative, all guardrail-compliant |
| 5 | Commercial Strategy | Recommended positioning and negotiation approach |
| 6 | Follow-Up Actions | Concrete questions/validations before proceeding |
| 7 | Win Probability | Model output + top contributing factors |
| 8 | Client Pitch Deck | A client-ready, presentable proposal document |
| 9 | Sources Used | Every document/dataset the analysis actually drew on |

**End-to-end flow:**

```
opportunity text (demo case or pasted brief)
        │
        ▼
 extraction agent  ──────────► structured requirements, captures conflicting figures explicitly
        │
        ▼
 gap/feasibility agent (RAG-grounded on Service Description + guardrails)
        │                          │
        ▼                          ▼
 deterministic pricing engine   trained win-probability classifier
        │                          │
        ▼                          ▼
 risk & pricing narrative     win-probability narrative
        │                          │
        └───────────┬──────────────┘
                     ▼
      synthesis agent + pitch-deck agent
                     │
                     ▼
        one JSON "Contract" object
                     │
                     ▼
        React frontend (dashboard + pitch-deck view)
```

## AI Solution Summary

The design principle throughout: **use the right tool for each part of the reasoning, and never
let one layer quietly paper over another's uncertainty.**

- **Deterministic where correctness is non-negotiable.** The pricing engine (`backend/pricing.py`)
  is pure Python — cost lookup tables by volume tier × weight band, FX-converted fixed overhead,
  region multipliers, premium add-ons, and hard financial guardrails (minimum contribution margin,
  VP-approval threshold, automatic no-go floor). No LLM touches a price.
- **A real trained model, not a prompt, for win probability.** `backend/ml/win_model.py` is a
  scikit-learn logistic-regression pipeline trained on the 360-row historical opportunities
  dataset, reporting holdout AUC/accuracy honestly rather than overselling a small dataset. Its
  "top factors" explanation comes directly from the model's own standardized coefficients, so the
  explanation is the model, not a separate LLM guess about what mattered.
- **LLM agents for extraction, reasoning, and narrative** — never for arithmetic. A small pipeline
  of focused agents (`backend/agents/`), each with one job:
  - **Extraction** — raw text → structured requirements, explicitly capturing *conflicting* figures
    (e.g. Pink Papaya's "3,500–4,000/day" vs. "3,800/day") instead of picking one silently.
  - **Gap/Feasibility** — cross-checks requirements against Amazon Shipping's actual service
    capabilities, grounded by the RAG store below, producing exclusions and serviceable volume.
  - **Risk & Pricing Narrative** and **Win-Probability Narrative** — turn the deterministic
    pricing engine's and ML model's raw output into plain-language rationale.
  - **Synthesis** — executive summary, commercial strategy, follow-up actions, open assumptions.
  - **Pitch Deck** — renders the client-facing proposal.
- **Narrow, grounded RAG** (`backend/rag.py`) — `sentence-transformers` (`all-MiniLM-L6-v2`) embeds
  the Service Description and pricing guardrails once at startup into a plain in-memory `numpy`
  array with cosine similarity. No hosted vector database — the corpus is a few thousand tokens,
  so anything heavier would be over-engineering. This is what grounds every feasibility claim in a
  citable source for "Sources Used."
- **Schema-enforced outputs, not free-text parsing.** `instructor` patches the LLM client so every
  agent call returns a validated Pydantic object directly — no brittle regex/JSON-parsing layer
  between the model and the Contract.
- **Provider-agnostic by design, deliberately not a framework.** `groq` (primary) and the `openai`
  SDK pointed at NVIDIA NIM (fallback) expose the same `chat.completions` shape, so switching
  providers under a rate limit is a one-line config change (`LLM_PROVIDER=groq|nvidia`), not a
  rewrite. Orchestration is a plain `async def run_pipeline(...)` (`backend/agents/pipeline.py`)
  with independent steps run concurrently via `asyncio.gather` — explicitly **not LangChain**,
  which would add debugging opacity without adding capability at this pipeline's scale.
- **Deterministic guardrails around the LLM layer itself.** The orchestrator applies sanity checks
  independent of what any agent claims — e.g. correcting an unconverted annual/monthly total back
  to a daily figure, and hard-capping serviceable volume at what the prospect actually declared —
  so a single LLM misjudgment can't silently inflate the final recommendation.
- **Ambiguity is a feature of the output, not a bug to hide.** The Pink Papaya case exists
  specifically to prove this: the copilot surfaces the founders' disagreement on France and the
  conflicting volume figures as named risks and open questions, rather than resolving them itself.

## Technology Stack

### Backend

| Layer | Technology | Purpose |
|---|---|---|
| Language / runtime | Python 3.12 | |
| Web framework | FastAPI + Uvicorn (ASGI) | Single `POST /analyze` endpoint, `GET /health` |
| Data contracts | Pydantic v2 + `pydantic-settings` | The shared Contract schema; typed, validated env config |
| Package management | [uv](https://docs.astral.sh/uv/) with committed `uv.lock` | Reproducible installs, single lockfile for runtime + dev |
| LLM clients | `groq` (official SDK, primary), `openai` SDK against NVIDIA NIM's OpenAI-compatible endpoint (fallback) | One interface, provider swap via config only |
| Structured LLM output | `instructor` | Patches the LLM client so agent calls return validated Pydantic models directly |
| Retrieval | `sentence-transformers` (`all-MiniLM-L6-v2`) + plain `numpy` cosine similarity | Narrow-scope RAG over the Service Description + pricing guardrails |
| Machine learning | `scikit-learn` (logistic regression pipeline), `pandas`, `numpy`, `imbalanced-learn` (SMOTE, training split only), `joblib` (model persistence) | Win-probability classifier trained on the 360-row historical dataset |
| Offline document ingestion | `python-docx`, `python-pptx`, `openpyxl` | One-time parsing of challenge documents into cached text/JSON/CSV fixtures — never re-parsed at request time |
| Testing | `pytest`, `pytest-asyncio`, `pytest-cov`, `httpx` (API test client) | Unit tests for pricing/ML (deterministic, no LLM in the loop) plus pipeline/agent tests |
| Code quality | `ruff` (lint + format), `mypy` (strict on `schemas/`, `pricing.py`, `ml/`), `pre-commit` | Exactly what CI runs |
| Containerization | Docker (multi-stage `backend/Dockerfile`) | |
| Deployment | [Render](https://render.com) (Docker web service, `render.yaml`) | Health-checked at `/health`, deployed via CI-triggered deploy hook |

### Frontend

| Layer | Technology | Purpose |
|---|---|---|
| Language | TypeScript | |
| UI framework | React 19 | |
| Build tool | Vite 8 (`@vitejs/plugin-react`) | Dev server + production bundling |
| Routing | React Router 7 | Opportunity picker (`/`) → Dashboard (`/dashboard`) → Pitch Deck (`/pitch-deck`) |
| Styling | Tailwind CSS 4 (`@tailwindcss/vite`), `@tailwindcss/typography` | Utility-first styling; `typography` plugin renders the pitch-deck prose |
| Markdown rendering | `react-markdown` | Renders the backend's Markdown pitch deck as a formatted client proposal |
| State | React Context (`OpportunityContext`) | Holds the current analysis result; no external state library needed for this scope |
| Linting | `oxlint` | |
| Type checking | `tsc -b` (project references, no emit) | |
| Deployment | Static build (`render.yaml` static site) or Docker + nginx (`docker-compose`) | |

### Cross-cutting / infrastructure

- **Contract-first integration**: one shared JSON shape — Pydantic on the backend
  (`backend/schemas/opportunity_result.py`), mirrored TypeScript types on the frontend
  (`frontend/src/types/contract.ts`) — so the frontend never needs business logic, only display
  logic, and both sides can build in parallel against a committed fixture.
- **Local full stack**: Docker Compose (`docker-compose.yml`) — Postgres 16 (provisioned for future
  persistence), the FastAPI backend, and the built frontend.
- **CI/CD**: GitHub Actions (`.github/workflows/ci.yml`) — lint → typecheck → test → build images on
  every push/PR to `master`; a green suite on `master` triggers a Render deploy hook.

## Getting Started

### Backend

```bash
# Install the pinned toolchain (runtime + dev extras)
uv sync --extra dev

# Run the API (loads secrets from .env; copy .env.example first)
uv run uvicorn backend.main:app --reload --env-file .env

# Quality gates (these are exactly what CI runs)
uv run ruff check backend           # lint
uv run ruff format --check backend  # format
uv run mypy backend                 # types (strict on schemas/, pricing.py, ml/)
uv run pytest --cov=backend         # tests + coverage
```

Optional local git hooks mirroring CI:

```bash
uv run pre-commit install
```

All environment-driven settings are declared in `backend/config.py` (`Settings`) and documented in
`.env.example`. Nothing reads `os.environ` directly; pass `--env-file .env` locally.

### Frontend

```bash
cd frontend
npm ci
npm run dev        # dev server
npm run lint       # oxlint
npm run typecheck  # tsc -b (no emit)
npm run build      # production bundle
```

The frontend degrades gracefully with no backend configured: the Tecnomania and Pink Papaya demo
cards fall back to bundled fixtures (`frontend/fixtures/`) so the UI is fully explorable offline.

### Full stack via Docker

```bash
docker compose up --build
# backend  → http://localhost:8000  (health: /health)
# frontend → http://localhost:5173
# postgres → localhost:5432
```

See `VISION.md` for the unconstrained product direction beyond this MVP, and `Plan_v2.md` for the
delivery roadmap.
