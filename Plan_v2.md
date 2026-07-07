# Plan_v2 — Production Delivery Plan: Opportunity Copilot, Stages 1–4

This plan converts VISION.md into an actionable, full-delivery roadmap. It supersedes PLAN.md
(the 27-hour hackathon plan) as the working document. Scope decisions locked with the product
owner on 2026-07-07:

| Decision | Choice |
|---|---|
| Scope | **Full VISION (Stages 1–4)**: production hardening → proactive discovery → negotiation copilot → guardrailed autonomy + causal pricing |
| Infrastructure | **Render / managed-simple**: Render web services + managed Postgres; no AWS migration unless scale forces it. Docker images keep the option open. |
| LLM providers | **Groq (paid tier) primary, NVIDIA NIM fallback** — keep the existing OpenAI-compatible adapter; providers stay swappable by config |

---

## 0. Current state (audited 2026-07-07)

**What exists and works conceptually** (commit `16c76cc`):

- `backend/` — FastAPI, single `POST /analyze`: extraction → gap/feasibility → deterministic
  pricing engine (`pricing.py`) → logistic-regression win model (`ml/win_model.py`) → narrative
  agents → synthesis → pitch deck. Pydantic Contract in `schemas/opportunity_result.py`.
  LLM adapter (`agents/llm_client.py`) with Groq/NVIDIA config swap + `instructor` structured
  outputs. Narrow numpy/sentence-transformers RAG (`rag.py`). 9 pytest test files.
- `frontend/` — React 19 + Vite 8 + Tailwind 4 + TypeScript, oxlint. Opportunity picker,
  9-section dashboard, pitch-deck view, sources panel. Renders the Contract; fixture fallback.
- `render.yaml` — single web service, free plan.

**Production-readiness gaps found in the audit** (these drive Phase 1):

1. **Test suite does not run**: collection fails (missing `httpx` and unpinned deps installed
   ad hoc into system Python; `pytest.ini` sets `asyncio_mode` but pytest-asyncio isn't active).
   No lockfile anywhere in the backend — `requirements.txt` is unpinned names only.
2. **No persistence**: every analysis is discarded after the response (VISION §1 "stateless").
   No audit trail of LLM decisions (VISION §4 governance).
3. **Synchronous 90-second request**: `POST /analyze` holds the connection open with a 90s
   timeout — will not survive Render's/browsers' proxy timeouts under load; no job queue.
4. **No auth, no rate limiting, CORS `allow_origins=["*"]`** on a service that spends paid LLM
   tokens per request.
5. **No CI/CD, no linting/typing gates in the repo** (ruff/mypy absent; frontend has oxlint but
   no test runner), no Docker, model binary (`win_model.joblib`) gitignored but no versioned
   artifact story, secrets hygiene OK (`.env` gitignored).
6. **No LLM observability**: no retries/backoff, no token/cost tracking, no eval harness —
   prompt regressions are invisible.
7. **Frontend has zero tests** and no error-boundary/loading-state hardening for slow analyses.

---

## 1. Model strategy (two distinct mappings — do not conflate)

### 1a. Runtime LLM models (what the deployed product calls, per agent task)

Provider adapter stays as-is: `LLM_PROVIDER=groq|nvidia`, OpenAI-compatible, `instructor` for
schema enforcement. Model names below are best-known current catalog names — **verify against
the live Groq/NVIDIA catalogs at implementation time of each phase; names drift.**

| Runtime task | Tier | Groq (primary) | NVIDIA NIM (fallback) | Why |
|---|---|---|---|---|
| Extraction (doc/email/transcript → structured JSON, contradiction capture) | Large | `llama-3.3-70b-versatile` (evaluate `openai/gpt-oss-120b` / `moonshotai/kimi-k2-instruct` in the Phase 1 eval harness) | `meta/llama-3.1-70b-instruct` | Highest accuracy need; must surface conflicts, not smooth them |
| Gap/feasibility, risk + pricing narrative, synthesis | Large | same as extraction | same | Judged reasoning quality, grounded by pricing engine + RAG |
| Win-probability narrative | Small | `llama-3.1-8b-instant` | `meta/llama-3.1-8b-instruct` | Narrates a number the ML model computed; latency + cost |
| Pitch-deck generation | Large | same as extraction | same | Client-facing quality |
| **Phase 2** signal classification (is this job posting a buying signal?) | Small | `llama-3.1-8b-instant` | 8B | High volume, narrow task — cost dominates |
| **Phase 2** prospect brief generation | Large | 70B-class | 70B | Sales-facing quality |
| **Phase 3** call transcription | ASR | `whisper-large-v3-turbo` (Groq-hosted) | AWS Transcribe or local `faster-whisper` | Groq hosts Whisper — same account, real-time-capable |
| **Phase 3** live negotiation suggestions | Large, latency-critical | fastest 70B-class on Groq at build time | 70B | Sub-2s turnaround needed on-call; Groq's inference speed is the reason we're keeping it |
| **Phase 4** red-team reviewer agent | Large | 70B-class, *different model family than the generator* (e.g. kimi-k2 reviews llama output) | swap families | A reviewer of the same family shares blind spots |
| **Phase 4** counter-quote drafting (guardrailed autonomy) | Large | 70B-class | 70B | Outbound customer-facing text; always behind human approval gate |

Routing rule (implemented Phase 1, task **P1-C3**): every agent call site declares a *tier*, never
a model name; the adapter maps tier→model per provider. Adding a third provider or a
distilled/fine-tuned small model later (VISION §4) is a config table entry.

### 1b. Development models (which Claude model drives each build task)

Same philosophy as PLAN.md §7a, updated for the current model lineup:

| Dev model | Use for | Concretely in this plan |
|---|---|---|
| **Haiku 4.5** (`claude-haiku-4-5`) | Cheap, fast execution subtasks — dispatched as background subagents | Codebase search (`Explore`), running test suites, dependency upgrades, scaffolding boilerplate (Alembic migrations, Vitest configs, Dockerfiles), doc lookups, market/signal-source research in Phase 2 |
| **Sonnet 5** (`claude-sonnet-5`) | Default driver for implementation | All routine tasks below unless marked otherwise: CRUD/API endpoints, React components, connector implementations, test writing, prompt drafting |
| **Opus 4.8 / Fable 5** (`claude-opus-4-8` / `claude-fable-5`) | Architecture, correctness-critical logic, reviews, judgment calls | Tasks tagged **[OPUS]** below: DB schema + audit-trail design, job-queue/durable-workflow architecture, causal-inference methodology (P4), guardrail/autonomy policy logic, entity-resolution design, phase-exit `/code-review` passes, security review before each production deploy |

Standing rules:
- Every phase exits through a `/code-review` (high effort) + `ecc:security-reviewer` pass driven
  at Opus/Fable tier.
- ML tasks additionally get an `ecc:mle-reviewer` pass (train/serve skew, leakage, eval hygiene).
- LLM-prompt changes never merge without the eval harness (P1-C4) green.

---

## 2. Phase 1 — Production hardening (VISION Stage 1)

Goal: the existing pipeline becomes a real service — reproducible, persistent, observable,
authenticated, tested, deployable on every merge. Everything later builds on this.

### Workstream A — Engineering foundations

| ID | Task | Libraries / tools | Testing / acceptance | Dev model |
|---|---|---|---|---|
| P1-A1 | Adopt **uv** for the backend: `pyproject.toml` + `uv.lock`, pin every dependency, split `dev` extras (pytest, ruff, mypy). Kill the unpinned `requirements.txt` (keep a generated one only if Render needs it). | `uv`, `pyproject.toml` | Fresh clone + `uv sync` + `uv run pytest` passes on a clean machine and in CI | Sonnet 5 |
| P1-A2 | **Fix the test suite**: add `httpx` (starlette TestClient), configure `pytest-asyncio` properly, get all 9 existing test files collecting and passing; add coverage reporting. | `pytest`, `pytest-asyncio`, `pytest-cov`, `httpx` | `uv run pytest` green; coverage baseline recorded; ≥80% on `pricing.py`, `win_model.py`, `schemas/` | Sonnet 5 |
| P1-A3 | **Lint + type gates**: ruff (lint+format) and mypy (strict on `schemas/`, `pricing.py`, `ml/`) for backend; keep oxlint + add `tsc --noEmit` gate for frontend; pre-commit hooks. | `ruff`, `mypy`, `pre-commit`, `oxlint` | CI fails on violations; repo passes clean | Sonnet 5 (Haiku 4.5 for mechanical fix-ups) |
| P1-A4 | **Dockerize** backend (multi-stage, uv-based, non-root) and frontend (build → static). Compose file for local dev with Postgres. | Docker, docker-compose | `docker compose up` serves the full stack locally; image builds in CI | Sonnet 5 |
| P1-A5 | **CI/CD on GitHub Actions**: lint → typecheck → test → build images → deploy to Render on merge to `main` (Render deploy hook or `render.yaml` autodeploy). Separate preview environment per PR if budget allows. | GitHub Actions, Render deploy hooks | Merge to main auto-deploys; a red suite blocks deploy | Sonnet 5 |
| P1-A6 | **Secrets & config**: single `Settings` object (pydantic-settings), no bare `os.environ` reads scattered through code; document every env var in `.env.example`; Render env groups. | `pydantic-settings` | mypy-checked config; app fails fast with a clear message on missing config | Sonnet 5 |

### Workstream B — Persistence, API surface, async jobs

| ID | Task | Libraries / tools | Testing / acceptance | Dev model |
|---|---|---|---|---|
| P1-B1 | **[OPUS]** Design the relational core (VISION §8.2): `accounts`, `opportunities`, `analyses` (the Contract as rows, not a blob — plus a JSONB column for full-fidelity replay), `pricing_scenarios`, `llm_calls` (audit trail: prompt, model, tokens, latency, response hash — replayable per VISION §4), `deal_outcomes` (won/lost + **labeled loss reason** — VISION §5's highest-leverage field). Alembic migrations from day one. | Render managed **PostgreSQL 16**, `SQLAlchemy 2.x` (async), `Alembic`, `asyncpg` | Schema reviewed by `ecc:database-reviewer`; migration up/down tested in CI against a service container | **Opus/Fable** design, Sonnet 5 implementation |
| P1-B2 | **Async job model**: `POST /analyses` returns `202 + analysis_id`; worker executes the pipeline; `GET /analyses/{id}` polls status/result; SSE endpoint for progress. Replaces the 90s synchronous request. | **Procrastinate** (Postgres-backed queue — no Redis to run on Render's simple plan; swap to ARQ+Redis only if throughput demands) | Integration test: enqueue → worker completes → result persisted + retrievable; timeout/retry paths tested | **[OPUS]** architecture, Sonnet 5 implementation |
| P1-B3 | **AuthN/Z + abuse protection**: API-key auth for service callers + session auth for the UI (start with `fastapi-users` or signed-JWT + a simple users table; SSO/OIDC deferred to Phase 3 when it becomes sales-team-facing), per-key rate limiting, CORS locked to the deployed frontend origin. | `fastapi-users` or `pyjwt` + `passlib`, `slowapi` | Unauthenticated requests rejected in tests; rate-limit test; CORS verified from deployed origin | Sonnet 5, **[OPUS]** security review |
| P1-B4 | **API versioning + contract tests**: mount under `/v1`; OpenAPI schema published; property-based contract testing so the frontend Contract can never silently drift. | `schemathesis`, FastAPI OpenAPI | `schemathesis run` green in CI; frontend `contract.ts` generated from OpenAPI (`openapi-typescript`) instead of hand-mirrored | Sonnet 5 |
| P1-B5 | **Observability**: structured JSON logs, error tracking, traces + metrics (request latency, queue depth, per-agent LLM latency/tokens/cost). | `structlog`, **Sentry**, **OpenTelemetry** SDK → Grafana Cloud free tier (or Logfire) | Dashboards show a full pipeline run end-to-end; alert on error rate + queue backlog | Sonnet 5 |

### Workstream C — LLM layer hardening

| ID | Task | Libraries / tools | Testing / acceptance | Dev model |
|---|---|---|---|---|
| P1-C1 | **Paid-tier accounts + failover**: move Groq to paid tier; implement automatic provider failover (Groq 429/5xx → NVIDIA) with circuit breaker, not just manual config swap. | existing adapter + `tenacity` (retry/backoff), simple circuit-breaker state | Chaos test: mock 429s → pipeline completes via fallback; failover visible in metrics | Sonnet 5 |
| P1-C2 | **Per-agent budgets**: timeout, max retries, and token ceilings per agent call; total pipeline budget; graceful degradation messages persisted with the analysis. | `tenacity`, config in Settings | Tests for timeout/degradation paths; no unbounded retries | Sonnet 5 |
| P1-C3 | **Tier-based routing table** (§1a): call sites declare `tier`, adapter maps tier→provider model; per-call audit row written to `llm_calls` (P1-B1). | existing `llm_client.py` extension | Unit tests for routing; every LLM call in a pipeline run has an audit row | Sonnet 5 |
| P1-C4 | **LLM eval harness** — the gate for all prompt/model changes: golden-fixture tests for both demo opportunities + the 3 synthetic regression companies (PLAN.md §8a.3), assertions on structured-output fields (e.g. Pink Papaya contradictions MUST be captured), plus LLM-as-judge scoring for narrative quality. Runs in CI nightly + on prompt changes. | **promptfoo** (or pytest-based harness + `deepeval`), fixtures in `backend/data/eval/` | Baseline scores recorded; CI fails on regression > threshold; used to evaluate the §1a candidate models | **[OPUS]** harness design + judge rubric, Sonnet 5 implementation |
| P1-C5 | **RAG upgrade**: move the numpy in-memory store to **pgvector** in the same Postgres (VISION §8.3 says pgvector to start) — needed anyway once Phase 2 grows the corpus; keep `sentence-transformers` embeddings. | `pgvector`, `sqlalchemy`, existing `sentence-transformers` | Retrieval parity test vs current numpy results on the existing corpus; latency budget met | Sonnet 5 |

### Workstream D — ML hardening + the feedback loop

| ID | Task | Libraries / tools | Testing / acceptance | Dev model |
|---|---|---|---|---|
| P1-D1 | **Reproducible training pipeline**: one command retrains from the canonical dataset, records metrics (holdout AUC/accuracy + **calibration** — the UI shows probabilities, so calibrate with `CalibratedClassifierCV`), and writes a versioned artifact. | `scikit-learn`, `joblib`, **MLflow** (self-hosted lite or just file-versioned artifacts + a `models` DB table — start with the table, adopt MLflow when experiments multiply) | `uv run python -m backend.ml.train` reproduces published metrics; model version stamped into every prediction's audit row | Sonnet 5, **[OPUS]** methodology review via `ecc:mle-reviewer` |
| P1-D2 | **Close the loop** (VISION §3.8): outcome-capture API + UI (`deal_outcomes` from P1-B1) with **mandatory labeled loss reason** (price / coverage / service level / timing / other); scheduled retraining job (Procrastinate cron) that retrains when N new labeled outcomes exist, evaluates against holdout, and requires human approval to promote. | Procrastinate scheduled tasks, P1-D1 pipeline | E2E test: label outcomes → retrain job produces candidate → promotion gate works; no auto-promote | Sonnet 5, **[OPUS]** promotion-gate logic |
| P1-D3 | **Monotonicity + drift checks**: port PLAN.md §8a.2 synthetic edge-case sanity checks into the test suite; log feature distributions of live predictions for drift monitoring. | pytest, `evidently` (or hand-rolled distribution checks first) | Monotonicity suite green in CI; drift metric visible in dashboards | Sonnet 5 |

### Workstream E — Frontend production hardening

| ID | Task | Libraries / tools | Testing / acceptance | Dev model |
|---|---|---|---|---|
| P1-E1 | **Test infrastructure**: Vitest + React Testing Library; component tests for all 9 dashboard sections against the fixture; MSW for API mocking. | `vitest`, `@testing-library/react`, `msw` | CI gate; every section renders all Contract edge cases (empty exclusions, no_go guardrail status, degraded-agent messages) | Sonnet 5 |
| P1-E2 | **Async-job UX**: replace the single blocking call with submit → progress (SSE from P1-B2) → result; error boundaries; retry affordance; analysis history list (now that results persist). | `react-router-dom` (already in), native `EventSource` | Component + integration tests for pending/progress/failed/complete states | Sonnet 5 |
| P1-E3 | **E2E suite**: Playwright against the compose stack — both demo opportunities end-to-end (with LLM mocked at the network edge for determinism) + one live smoke tagged `@live` run nightly against real providers. | `@playwright/test` | Both flows green in CI; nightly live smoke alerting | Sonnet 5 |
| P1-E4 | **Auth UI, a11y and polish pass**: login, API-key management screen; keyboard/screen-reader audit of the dashboard; loading skeletons. | existing stack, `ecc:a11y-architect` review | axe-core checks in Playwright green; a11y findings resolved | Sonnet 5 |
| P1-E5 | Deploy frontend as a **Render static site** (or Cloudflare Pages), environment-based API URL, remove fixture-fallback path from production builds (keep for local dev). | Vite envs | Deployed frontend hits deployed `/v1` API; fixture code excluded from prod bundle | Haiku 4.5 |

**Phase 1 exit criteria**
- Clean clone → `uv sync` → tests green; CI enforces lint/type/test/eval gates; merge → auto-deploy.
- An analysis submitted from the deployed UI is queued, executed, persisted, and retrievable with
  a full replayable LLM audit trail; auth required; provider failover proven.
- Win/loss outcomes with labeled reasons can be recorded and drive a gated retraining job.
- `/code-review` (high, Opus tier) + `ecc:security-reviewer` + `ecc:mle-reviewer` passes complete.

---

## 3. Phase 2 — Proactive opportunity discovery (VISION Stage 2)

Goal: the system finds and qualifies prospects instead of waiting for an RFQ (VISION §3.1).
Pipeline flips to: signal ingestion → entity resolution → signal scoring → auto-generated
prospect brief → sales queue in the UI.

| ID | Task | Libraries / tools | Testing / acceptance | Dev model |
|---|---|---|---|---|
| P2-1 | **[OPUS]** Signal-source survey & legal check (time-boxed, 1 week): rank candidate feeds for Spain/Iberia — company registries (BORME), job boards (logistics-role postings), funding news, import/export data, carrier-complaint forums — by signal value, ToS/legality of automated access, and cost. Output: ranked source list with an ingestion decision per source (official API > licensed data vendor > scraping only where ToS-compatible). | WebSearch/WebFetch research (Haiku subagents), legal review checklist | Written source register with go/no-go per source, reviewed before any connector is built | **Opus/Fable** judgment, Haiku 4.5 research legwork |
| P2-2 | **Connector framework**: one `SignalConnector` interface (fetch → normalize → `raw_signals` table), per-source scheduled jobs, retries, dedup by content hash, raw payloads archived (VISION §8.1 — object storage: Render disk first, Cloudflare R2/S3 when volume demands). | `httpx`, `pydantic`, Procrastinate cron; per-source parsers (`feedparser`, `beautifulsoup4` where permitted) | Each connector has fixture-based parser tests + a recorded-response integration test (`vcrpy`); dedup tested | Sonnet 5 |
| P2-3 | **[OPUS]** Entity resolution: map signals to companies (name normalization, registry IDs, fuzzy matching with human-confirm queue for low-confidence matches). This is the make-or-break data-quality task. | `rapidfuzz`, `recordlinkage` (or `splink` if volume grows), Postgres | Labeled test set of ~200 match/no-match pairs; precision ≥95% on auto-accepted matches | **Opus/Fable** design, Sonnet 5 implementation |
| P2-4 | **Signal classification + scoring**: small-model LLM pass (§1a) classifies each normalized signal (buying-signal type, strength, rationale); deterministic scoring aggregates per company over a time window into a prospect score. | tier-routed LLM (small), eval fixtures | Eval-harness suite (P1-C4 pattern) with a hand-labeled signal set; precision/recall targets recorded; scoring unit-tested | Sonnet 5 |
| P2-5 | **Knowledge-graph-lite** (VISION §4/§8.3): `entities` + `relationships` tables in Postgres (companies, people, deals, signals; typed edges like `stakeholder_of`, `disagrees_with`, `competitor_of`). Recursive-CTE queries. **Neo4j deferred** until a query genuinely can't be expressed — revisit at Phase 3 exit. | SQLAlchemy, Postgres recursive CTEs | Graph queries tested (e.g. "stakeholders of X who disagree"); extraction agent extended to emit stakeholder edges — eval-tested on Pink Papaya's Lucía/Marta case | **[OPUS]** schema design, Sonnet 5 implementation |
| P2-6 | **Prospect briefs + sales queue UI**: large-model brief per qualified prospect (who, why now, which signals, suggested first move — grounded in the signal rows, citations required); frontend queue view with triage (pursue / dismiss-with-reason → feeds the learning loop); one-click "run full analysis" into the Phase 1 pipeline. | existing agent framework; React queue views | Brief eval fixtures (citation-grounding assertions); Playwright flow: signal → queue → triage → full analysis | Sonnet 5 |
| P2-7 | **Discovery metrics**: precision of surfaced prospects (accepted vs dismissed rate), signal-source yield, time-to-first-touch. Dashboard panel. | OTel metrics + Grafana | Metrics visible; dismissal reasons queryable | Haiku 4.5 |

**Phase 2 exit criteria**: ≥3 legally-cleared live connectors running on schedule; entity
resolution at target precision; a sales user sees a ranked prospect queue with cited briefs and
can promote one into a full Phase 1 analysis; triage decisions are captured for learning.

---

## 4. Phase 3 — Negotiation copilot (VISION Stage 3)

Goal: move from pre-call analysis to in-workflow assistance — email threads first (higher
coverage, lower risk), then live calls. Both grounded in the *same* pricing guardrails and risk
model as the pipeline.

| ID | Task | Libraries / tools | Testing / acceptance | Dev model |
|---|---|---|---|---|
| P3-1 | **[OPUS]** Durable negotiation workflows: a negotiation spans days/weeks and must survive restarts (VISION §4). Adopt **Temporal Cloud** (managed — consistent with Render-simple infra; self-hosting Temporal is not) for `NegotiationWorkflow`: state machine over offers/counters/approvals with full history. Fallback decision if Temporal Cloud is out of budget: Postgres-backed state machine + Procrastinate — decide in the design spike. | `temporalio` Python SDK, Temporal Cloud | Workflow replay tests (Temporal's test framework); kill-worker-mid-negotiation chaos test resumes correctly | **Opus/Fable** architecture spike + decision, Sonnet 5 implementation |
| P3-2 | **Email-thread ingestion** (VISION §7): connect a shared mailbox (Gmail API / MS Graph), parse threads preserving who-said-what-when, feed the extraction agent thread-aware (contradiction detection across senders/time — the Lucía/Marta case done properly). | `google-api-python-client` or `msgraph-sdk`, `mailparser` | Fixture threads with known contradictions; eval-harness assertions on attribution ("who said the 18% figure") | Sonnet 5 |
| P3-3 | **Counter-offer analysis agent**: given a negotiation state + incoming counter (email), compute margin-safe response envelope from the deterministic pricing engine, draft a recommended reply with rationale; **advisory-only in this phase** — a human sends everything. | existing pricing engine + tier-routed large model | Golden negotiation scenarios: proposed counters NEVER breach the 13% floor (property-based test over random states — hard invariant, tested exhaustively) | **[OPUS]** guardrail logic, Sonnet 5 agent |
| P3-4 | **Live-call assistant (spike → build)**: consent-first recording (explicit disclosure flow, per-participant consent stored), streaming STT via Groq `whisper-large-v3-turbo`, rolling transcript buffer, low-latency prompt producing short structured nudges ("competitor quote 8% below — lowest margin-safe counter: €X"). WebSocket to a side-panel UI. Timebox a 2-week feasibility spike on latency before committing to full build. | `websockets`/FastAPI WS, Groq audio API, tier-routed fast model | Latency budget: transcript→nudge < 3s p90 on recorded test calls; nudge quality eval on scripted mock-negotiation recordings; consent flow legally reviewed | **[OPUS]** spike + latency architecture, Sonnet 5 UI/plumbing |
| P3-5 | **PII/compliance hardening** (VISION §4 — now real customer data): PII detection/redaction before LLM calls where feasible, data-retention policy + deletion endpoints (GDPR), DPAs with Groq/NVIDIA verified for real customer data (**flag: if paid-tier DPAs are insufficient for call audio, escalate — this is the VISION §10 Bedrock question returning; decide with counsel, not in code**), audit-trail extension to conversational data. | `presidio` (MS PII toolkit), policy docs | Redaction unit tests; deletion e2e test; documented DPA review sign-off before any real call audio flows | **Opus/Fable** for the compliance design, Sonnet 5 implementation |
| P3-6 | **SSO** for the sales team (deferred from P1-B3): OIDC against the org IdP; role model (rep / manager / approver). | `authlib` OIDC | Role-gated routes tested; approver role wired to P1-D2/P4 gates | Sonnet 5 |

**Phase 3 exit criteria**: a negotiation tracked as a durable workflow from first email to
close; counter-offer drafts provably guardrail-safe; live-call assistant demoed on scripted
calls within latency budget; consent + retention + DPA posture documented and reviewed.

---

## 5. Phase 4 — Causal pricing + guardrailed autonomy (VISION Stage 4)

Goal: pricing recommendations become causally grounded ("what happens if we discount 2% more"),
and the mechanical 80% of negotiation can execute autonomously inside hard human-set bounds.

| ID | Task | Libraries / tools | Testing / acceptance | Dev model |
|---|---|---|---|---|
| P4-1 | **[OPUS]** Causal/uplift layer (VISION §3.4): double-ML / uplift modeling on accumulated labeled outcomes to estimate price elasticity of win probability; sits **alongside** the interpretable logistic model, not replacing it. Honest gate: requires enough labeled outcomes from P1-D2 — if volume is insufficient at phase start, ship the experimentation framework (P4-2) first and defer estimation. | `econml` (or `doubleml`), `scikit-learn` | Methodology reviewed (`ecc:mle-reviewer` at Opus tier); refutation/sensitivity tests (placebo treatments, subset stability); documented assumptions | **Opus/Fable** methodology, Sonnet 5 pipeline code |
| P4-2 | **Pricing experimentation framework** (VISION §5 ground truth): randomized scenario-anchor assignment within guardrails for comparable deals, experiment registry, power analysis before launch, results feeding P4-1. Requires explicit commercial-org sign-off — surfaces VISION §10's "appetite" question as a concrete proposal document. | `statsmodels`, experiment tables in Postgres | Simulated A/B validates the analysis pipeline end-to-end before any real experiment; sign-off doc | **[OPUS]** design, Sonnet 5 implementation |
| P4-3 | **Red-team reviewer agent** (VISION §3.6): adversarial pass over every generated pitch/brief/counter-draft before a human sees it — checks numeric claims against the pricing engine + source data, flags indefensible statements. Different model family from the generator (§1a). | tier-routed LLM, deterministic numeric cross-checker | Eval set of seeded-flaw pitches: catch rate ≥ target, false-positive rate bounded; runs as mandatory pipeline stage | **[OPUS]** rubric, Sonnet 5 implementation |
| P4-4 | **[OPUS]** Guardrailed autonomous counter-quotes (VISION §3.7): within hard bounds (margin floor, geo scope, contract length, discount-delta cap, message templates), the Temporal workflow may auto-send a revised quote in response to a counter-offer email; **anything** outside bounds → human escalation; every autonomous action logged, reversible where possible, and rate-limited per account. Rollout: shadow mode (drafts only, humans compare) → supervised (one-click approve) → autonomous for the narrowest bound set. | Temporal workflow + P3-3 engine + P3-2 email send | Property-based tests: no reachable state lets an out-of-bounds send occur (this is the load-bearing test of the whole phase); shadow-mode agreement metrics before each rollout step; kill switch tested | **Opus/Fable** policy engine + review, Sonnet 5 plumbing |
| P4-5 | **Contract-lifecycle intelligence** (VISION §3.5): ingest shipped-volume/SLA feeds for won deals (CSV/API import first), detect contracted-vs-actual drift and renewal windows, auto-draft expansion plays through the standard pipeline + red-team gate. | Procrastinate jobs, pandas, existing agents | Fixture-based drift-detection tests; expansion briefs pass red-team gate; renewal alerts fire on schedule | Sonnet 5 |
| P4-6 | **Multi-tenant readiness decision** (VISION §10: internal tool vs licensable product): revisit with real usage data. If licensing is pursued: tenant-id column strategy + row-level security in Postgres, per-tenant model artifacts and rate limits. Explicitly a decision checkpoint, not assumed work. | Postgres RLS | Decision memo; if go: RLS enforced in tests (cross-tenant leakage suite) | **Opus/Fable** decision + design |

**Phase 4 exit criteria**: causal estimates (or a running experimentation program generating the
data for them) inform scenario pricing; red-team gate mandatory on all outbound artifacts;
autonomous sends live in at least supervised mode with a proven-impossible out-of-bounds path;
lifecycle monitoring produces renewal/expansion plays.

---

## 6. Testing strategy (cross-phase summary)

| Layer | Framework | Gate |
|---|---|---|
| Backend unit (pricing, ML, schemas, scoring) | `pytest` + `pytest-cov`, property-based via `hypothesis` for pricing/guardrail invariants | CI, ≥80% on core modules; guardrail invariants are hard failures |
| API contract | `schemathesis` against OpenAPI; frontend types generated via `openapi-typescript` | CI on every PR |
| DB / migrations | Alembic up+down in CI against Postgres service container | CI |
| LLM behavior | Eval harness (P1-C4): golden fixtures + structured-output assertions + LLM-as-judge; per-agent suites grow each phase | CI on prompt/model changes + nightly; regression > threshold blocks merge |
| ML | Reproducible-training check, holdout AUC + calibration, monotonicity suite, drift monitoring; causal refutation tests in P4 | CI + retraining promotion gate |
| Frontend unit/component | `vitest` + React Testing Library + `msw` | CI |
| E2E | Playwright: mocked-LLM deterministic suite per PR; nightly `@live` smoke against real providers | CI / nightly |
| Load | `k6` against staging: queue-depth behavior, p95 latency, provider-failover under load | Before each phase's production release |
| Security | `ecc:security-reviewer` pass + dependency audit (`pip-audit`, `npm audit`) per phase exit; secrets scanning in CI | Phase-exit gate |
| Chaos/resilience | Provider-outage simulation (P1-C1), worker-kill mid-job (P1-B2), Temporal replay (P3-1) | Phase-exit gate |

## 7. Milestone map & sequencing

Phases are sequential; workstreams within a phase parallelize across two tracks (backend/ML vs
frontend/integration), same split that worked in the hackathon. Suggested checkpoints
(calendar-free — durations depend on staffing; order is the commitment):

1. **M1 — “It's a real service”** = Phase 1 exit. Nothing else starts until CI + persistence +
   auth + eval harness exist; every later phase depends on them.
2. **M2 — “It finds deals”** = Phase 2 exit. Requires P2-1 legal clearance before any connector code.
3. **M3 — “It sits in the deal”** = Phase 3 exit. P3-4 live-call build is go/no-go after its spike;
   email-first delivery de-risks the phase.
4. **M4 — “It acts, safely”** = Phase 4 exit. P4-1 gated on data volume from P1-D2; P4-4 gated on
   shadow-mode metrics; P4-6 is a decision checkpoint.

Standing risks carried from VISION §10 (owner: product) — tracked, not blocking start:
DPA/compliance ceiling of third-party LLM providers for real customer data (bites in P3-5);
organizational appetite for autonomy (bites in P4-2/P4-4); loss-reason labeling discipline
(mitigated by making it mandatory in P1-D2's UI — this is the plan's single highest-leverage task).
