# Enterprise Opportunity Copilot — Build Plan

Hackathon window: **July 6 10:00 → July 7 13:00** (~27h, 20+ left). 2 builders. This file is the
single source of truth both tracks build against — update it, don't fork it.

## 0. Non-negotiables from the brief

- MVP must generate all **9 outputs** for **both** opportunities (Tecnomania + Pink Papaya):
  Executive Summary, Opportunity Score, Risk Assessment, 3 Pricing Scenarios (aggressive→conservative,
  guardrail-compliant), Commercial Strategy, Follow-Up Actions, Client Pitch Deck, Win Probability, Sources Used.
- Win-probability logic must **generalize** — trained on the 360-row historical dataset, not
  hardcoded to these 2 cases.
- Must surface ambiguity/contradictions (esp. Pink Papaya) rather than silently resolving it.
- Rubric weight: AI Solution Quality 20 + MVP Functionality 20 + Amazon Relevance 20 = 60/100.
  **A working pipeline beats a polished mockup.** Polish (Innovation 15, Pitch Clarity 10) is last.

## 1. Architecture

Two deployed services, one contract between them:

```
Lovable frontend (React)  <-- HTTPS -->  FastAPI backend (Render)
  - opportunity picker/upload               - /analyze endpoint
  - 9-output dashboard                      - ingestion + RAG + pricing engine
  - pitch-deck / proposal view               - ML win-prob model
                                             - LLM agents (Groq, NVIDIA fallback)
```

Backend does all the reasoning and returns **one JSON object** (the Contract, §2). Frontend is a
renderer — it should never need business logic, only display logic. This is what lets both tracks
build in parallel: Person B builds the entire UI against a hardcoded fixture matching the Contract,
before the backend is even running.

## 2. The Contract (build this first, in Phase 0)

`backend/schemas/opportunity_result.py` (Pydantic) mirrored in `frontend/fixtures/example_result.json`.
Minimum shape — extend only if a phase genuinely needs a new field, don't pre-design extra fields:

```json
{
  "opportunity_id": "TCM-RFQ-2026-LM-01",
  "company_name": "Tecnomania S.L.U.",
  "executive_summary": "string, 3-5 sentences",
  "opportunity_score": {"value": 0, "label": "Strong/Moderate/Weak", "rationale": "string"},
  "serviceable_volume": {
    "declared_daily_volume": 8000,
    "serviceable_daily_volume": 6100,
    "geo_fit_pct": 0.76,
    "exclusions": [{"reason": "Portugal out of coverage", "volume_impact_pct": 0.12}]
  },
  "risk_assessment": [
    {"category": "Operational/Commercial/Financial", "risk": "string", "severity": "Low/Med/High", "evidence": "string"}
  ],
  "pricing_scenarios": [
    {"name": "Aggressive", "margin_pct": 15.0, "avg_price_per_parcel_eur": 0.0, "rationale": "string", "tradeoffs": "string"}
  ],
  "commercial_strategy": "string",
  "follow_up_actions": ["string"],
  "win_probability": {"value_pct": 0, "model": "logreg_v1", "top_factors": [{"factor": "geo_fit_pct", "direction": "+"}]},
  "pitch_deck_url_or_markdown": "string",
  "sources_used": [{"doc": "Service_description.pptx", "detail": "slide 6, weight/size limits"}],
  "assumptions_and_open_questions": ["string"]
}
```

Keep field names stable once both tracks start coding against them — renaming mid-hackathon is the
single biggest risk to parallelism.

## 3. Backend track (Person A)

### 3a. Data foundation

**Ingestion — two separate paths, not one generic pipeline:**
- *Static challenge docs* (Service Description, Pricing Workbook, Historical Opportunities, the 2
  opportunity packs): parsed **once, offline**, with the `python-docx`/`python-pptx`/`openpyxl` scripts
  already proven in this session, then cached as plain text/JSON/CSV fixtures committed to the repo:
  `backend/data/service_description.txt`, `backend/data/pricing_tables.json`,
  `backend/data/historical_opportunities.csv`, `backend/data/tecnomania.txt`, `backend/data/pink_papaya.txt`.
  The running service **never** re-parses Office files at request time — it loads cached text/JSON.
- *User-submitted opportunities* (the "paste your own" generalization path): **plain-text paste only**
  for the MVP. No live docx/pdf parsing at request time — that's exactly the kind of fragile feature
  that breaks mid-demo. Revisit only if Phase 5 buffer allows.
- Reuse the extraction scripts already proven in this session (`python-docx`/`python-pptx`/`openpyxl`
  in a venv) to parse: Service Description (capabilities/limits), Pricing Workbook (cost tables +
  guardrails), Historical Opportunities (360 rows), and the two opportunity packs.
- **Pricing engine** (`backend/pricing.py`), pure deterministic Python, no LLM:
  - Lookup tables: First Mile, Middle Mile, Home Delivery cost — each indexed by (daily volume tier ×
    weight band, 20 bands from 0-0.25kg to 27-30kg).
  - Fixed overhead: $0.17/parcel ÷ 1.16 EUR/USD FX.
  - Region multiplier: Balearic Islands ×1.35 (peninsula = ×1). Everything else (Portugal, Canary,
    Ceuta/Melilla) is **not serviceable** per the Service Description — exclude, don't price.
  - Premium add-ons: OTP +€0.35, SOD +€0.10.
  - Guardrails: min contribution margin 13% (below → "VP approval required"), target 21%, below 9% →
    automatic no-go. All 3 pricing scenarios must respect the 13% floor.
  - Serviceable-volume filter (mirrors the historical dataset's own logic): exclude PUDO-only demand,
    international (non-ES-peninsula/Balearic), B2B/business-address demand, oversized (>15kg or
    >80×80×60cm) — Amazon Shipping is home-delivery, B2C, ES+Balearic only, ≤15kg/≤80×80×60cm.
  - Unit-test against 2-3 hand-computed cases before trusting agent output built on top of it.
- **ML win-probability model** (`backend/ml/win_model.py`):
  - Train on the 360-row Historical Opportunities sheet. Target = `outcome` (Won/Lost).
  - Features: `geo_fit_pct`, `daily_volume_serviceable`, `avg_weight_kg`, `oversized_pct`,
    `requires_intl/pudo/b2b/weekend_need`, `pain_severity`, `price_vs_incumbent_pct`,
    `competitive_intensity`, `sales_cycle_touches`, `decision_time_days`, `contract_length_months`,
    `industry`, `lead_source` (one-hot).
  - Start with **logistic regression** (interpretable coefficients feed the "top factors" explainability
    requirement directly) or a shallow gradient-boosted tree if regression underfits. Report holdout
    AUC/accuracy — this number goes in the project doc as evidence the model generalizes.
  - This model is **not** an LLM prompt — it's a real trained classifier. The LLM narrates its output,
    it doesn't replace it.

### 3b. LLM agent layer (Groq primary, NVIDIA NIM as fallback — both OpenAI-SDK compatible, so swap
by changing `base_url`/`model`, not by rewriting call sites)
- **Extraction agent**: raw opportunity text → structured JSON (volumes, geography split, weight
  profile, stated requirements, named pain points). Must explicitly capture *conflicting* figures
  (e.g. Pink Papaya's "3,500-4,000/day" vs "3,800/day" vs France 18-25%) rather than picking one silently.
- **Gap/feasibility agent**: cross-check structured requirements against Service Description capabilities
  (RAG over the capability doc) → produces the `exclusions` list and serviceable volume inputs for §3a.
- **Risk + pricing narrative agent**: wraps pricing engine + guardrail output into risk assessment,
  3 scenario rationale/tradeoffs.
- **Win-probability narrative agent**: wraps ML model output into plain-language "why this score."
- **Synthesis agent**: executive summary, commercial strategy, follow-up questions, assumptions.
- **Pitch-deck agent**: renders a client-ready proposal. Fastest credible option under time pressure:
  populate an HTML template → export to PDF (or clean Markdown the frontend renders nicely). Skip
  PPTX generation unless time allows in Phase 5 — it's not worth the library overhead this cycle.
- **RAG store (scoped narrowly)**: embed only Service Description (~9 slides) + Pricing guardrails
  text (~1 page) — a few thousand tokens, chunked into ~20-30 short passages. Use `sentence-transformers`
  (`all-MiniLM-L6-v2`, CPU, no external API) to embed once at process startup, held as a plain `numpy`
  array with cosine similarity. **No hosted vector DB** (FAISS/Chroma/Pinecone) — over-engineering at
  this scale. This is what grounds the gap/feasibility agent's citations for "Sources Used."
  The **Historical Opportunities dataset is not RAG** — it's tabular. Use
  `sklearn.neighbors.NearestNeighbors` on standardized numeric features to retrieve the top-k most
  similar past deals (with real outcomes) for the win-probability narrative's "comparable customer
  profiles" claim. The two opportunity documents themselves (Tecnomania, Pink Papaya) are small enough
  (~2-4k words) to pass whole into the LLM context for extraction — no chunking/retrieval needed there.

### 3c. Orchestration & libraries — explicitly **not LangChain**

LangChain's abstraction overhead and debugging opacity is a net time cost, not a feature, for a
27-hour build with a linear pipeline. Instead:
- `groq` official Python SDK as primary client; `openai` SDK pointed at NVIDIA's OpenAI-compatible
  endpoint (`https://integrate.api.nvidia.com/v1`) as fallback — both expose the same
  `.chat.completions.create` shape, so one tiny adapter class picks the client from config
  (`LLM_PROVIDER=groq|nvidia`). Swapping providers under a rate limit is a config change, not a rewrite.
- `instructor` (patches an OpenAI-compatible client) for schema-enforced Pydantic outputs — this
  replaces LangChain's output parsers with something much thinner and directly produces the Contract's
  sub-objects. Fallback if a given model's tool-calling is flaky: `response_format={"type":"json_object"}`
  + manual `pydantic` validation + one retry on parse failure.
- Orchestration is a plain `backend/agents/pipeline.py`: one `async def run_pipeline(opportunity_text)
  -> OpportunityResult` calling each agent function in sequence, independent steps (e.g. RAG passage
  retrieval + historical nearest-neighbor lookup) run concurrently via `asyncio.gather`. No orchestration
  framework — fully debuggable mid-demo, zero extra dependency-version risk.

### 3d. Model-to-task mapping

| Task | Model tier | Why |
|---|---|---|
| Extraction (raw text → structured JSON) | Largest available Groq model (e.g. `llama-3.3-70b-versatile`) | Accuracy matters most — must catch contradictions (Pink Papaya's conflicting volume/geo figures), not smooth over them |
| Gap/feasibility, risk, pricing narrative, synthesis | Same large model | Judged reasoning quality; grounded by the pricing engine + RAG passages, not free-floating |
| Win-probability narrative | Small/fast model (e.g. `llama-3.1-8b-instant`) | Only narrates a number the ML model already computed — low complexity, keeps pipeline latency down |
| Pitch-deck agent | Large model | Client-facing tone/quality is the most visible output to judges |

NVIDIA NIM is the fallback tier-for-tier — same mapping, swap `base_url`/model name only. Confirm exact
current model names against the `groq` model list / NVIDIA catalog at build time; names above are
best-known at time of writing, not guaranteed current.

### 3e. API
- Single `POST /analyze` taking either raw pasted text/files or a `{"demo": "tecnomania"|"pink_papaya"}`
  shortcut, returning the Contract JSON. Deploy to Render early (Phase 0) even as a stub — proving the
  deploy pipeline works on day one avoids last-minute deploy failure.

## 4. Frontend track (Person B, on Lovable)

- Build against `frontend/fixtures/example_result.json` from Phase 0 — don't wait on backend.
- Screens: opportunity picker (Tecnomania / Pink Papaya / paste-your-own) → dashboard with the 9
  outputs as clearly labeled sections/tabs → dedicated "Client Pitch Deck" view that looks genuinely
  presentable (this is the one output a judge might actually screenshot) → a "Sources" panel showing
  citations per claim (traceability is explicitly graded).
  - Opportunity score as a gauge/badge, pricing scenarios as a comparison table, win-probability with
    top contributing factors, risk items with severity badges.
- Swap the fixture for the live Render URL in Phase 4. Keep the fixture around after that as a fallback
  demo path in case the live backend hiccups during judging.

## 5. Phased roadmap

| Phase | Time | Backend (A) | Frontend (B) | Exit criteria |
|---|---|---|---|---|
| 0 | ~1h | Scaffold FastAPI, deploy stub `/analyze` to Render, define Contract | Scaffold Lovable app, commit fixture JSON | Stub endpoint reachable by public URL; fixture agreed |
| 1 | ~3-4h | Pricing engine + guardrails, unit-tested; ML model trained + holdout metric | Dashboard skeleton wired to fixture, all sections render | Pricing engine passes hand-computed test cases; model AUC recorded |
| 2 | ~4-5h | Extraction + gap/feasibility agents, tested against both opportunities incl. ambiguity capture | Pitch-deck view + sources panel built | Both opportunities produce structured JSON with flagged contradictions |
| 3 | ~4-5h | Synthesis/risk/pricing-narrative/win-prob-narrative agents; full `/analyze` returns real Contract | UI polish, gauge/table components finalized | `/analyze` returns complete, schema-valid output for both opportunities |
| 4 | ~2-3h | — | Point frontend at live Render URL | End-to-end demo works live, both opportunities, no fixture |
| 5 | ~2-3h | Error handling for demo robustness (timeouts, malformed input) | Same | 30s pitch video recorded, project doc PDF written, final deploy smoke-tested cold |
| buffer | ~2h | | | |

## 6. Risks / fallbacks

- **Groq/NVIDIA free-tier rate limits mid-demo** → keep both wired behind one interface; if one
  throttles during judging, flip `base_url`.
- **360 rows is small for ML** → keep the model simple (logistic regression, regularized) rather than
  a deep model that overfits; report holdout metrics honestly in the project doc, don't oversell.
- **Lovable's generated backend (if any) conflicts with the Python backend** → keep Lovable frontend-only,
  all business logic in the Render FastAPI service. Don't let Lovable own data/ML logic.
- **Running out of time on pitch-deck polish** → an honest, clearly-labeled Markdown/HTML proposal
  beats a half-broken PPTX. Cut scope here first, not on the reasoning pipeline.

## 7. Dev workflow: ecc skills & agents per phase

Each person runs their own Claude Code session against their track. Concrete tool/skill mapping,
not generic "use agents".

### 7a. Claude model tiers for the *build process* (distinct from §3d, which is the runtime
Groq/NVIDIA pipeline the deployed app calls — this section is about which Claude model drives
the two of you while coding):

- **Haiku 4.5** — execution/search subtasks, dispatched as background subagents so the main
  session isn't blocked: codebase/file search (`Explore` agent), running the offline ingestion
  scripts, running test suites, web search for datasets/benchmarks (§8b), boilerplate scaffolding.
  Cheap and fast; use liberally, throughput matters more than depth here.
- **Sonnet 5** — the default driver for each person's main session: implementing the pricing
  engine, ML feature engineering, agent prompts, frontend/backend logic. Most of the actual
  build reasoning happens at this tier.
- **Opus 4.8 / Fable 5** — reserved for orchestration and validation, not routine coding:
  resolving cross-track integration decisions (Contract mismatches, scope-cut calls under time
  pressure), the phase-exit `/code-review` passes at Phase 4 integration and the Phase 5 final
  joint review (override the reviewer agent's `model` param to `opus`), validating the pricing
  engine math and ML methodology for correctness, and adjudicating ambiguous business-logic
  judgment calls (e.g. how to interpret Pink Papaya's contradictions) — these need careful
  reasoning over raw throughput.

- **Backend session**: `ecc:python-patterns` / `ecc:fastapi-patterns` / `ecc:mle-workflow` while
  building each module. `pytest` unit tests for the pricing engine and ML model — both are
  deterministic, no LLM in the loop, so they're fast and should run on every save.
- **Phase-exit gate**: run `/code-review` (medium effort) before merging each phase's branch —
  catches correctness/simplification issues before they compound into the next phase.
- **Integration checkpoint (Phase 3/4)**: run the `/verify` skill against the live `/analyze`
  endpoint — actually exercise both demo opportunities end-to-end, not just unit tests, since the
  real risk is the LLM-agent pipeline breaking in ways unit tests won't catch.
- **Frontend session (Lovable)**: Claude Code's role is mainly the Contract fixture (§2) and, if the
  Lovable project is ever exported/ejected to a local repo, `ecc:react-reviewer` on that code.
- **Joint supervision (Phase 5, ~30 min)**: one final pass with `ecc:code-reviewer` (or
  `agent-skills:code-reviewer`) across the integrated result — the one point where both tracks get a
  unified review before submission.

## 8. Synthetic data & external dataset strategy

### 8a. Synthetic data — for validation/stress-testing, not fabricated training labels
Don't fabricate synthetic (feature, label) rows and blend them into the 360-row training set as if
real — that's circular, and undermines the "the ML model must generalize" credibility the brief
explicitly grades. Legitimate uses instead:
1. **Class balance**: if Won/Lost is imbalanced in the 360 rows, use `imbalanced-learn`'s SMOTE on the
   *training split only* (never the holdout) — a standard, named technique, not ad hoc fabrication.
2. **Model stress-testing**: generate a handful of synthetic edge-case feature vectors (e.g. extreme
   pain_severity + low competitive_intensity + full geo fit) and confirm win-probability output moves
   monotonically/sensibly as each variable is perturbed. This is a validation line item ("sanity-checked
   monotonicity on N synthetic edge cases") for the project doc, not additional training data.
3. **Pipeline regression fixtures**: use the large-tier LLM to draft 2-3 additional synthetic
   opportunity documents (a third fictional company, same style as Tecnomania/Pink Papaya) with a
   hand-written ground-truth answer key. Use these as regression tests proving the extraction/gap-check
   pipeline generalizes beyond the 2 given cases rather than memorizing them.

### 8b. External dataset / market intelligence search
Time-boxed, delegated to a Haiku-tier search subagent (WebSearch/WebFetch) early in Phase 1 — not a
deep research project:
- Pull 3-5 credible public sources on the Spanish/Iberian last-mile parcel market (national postal
  regulator statistics, Eurostat e-commerce figures, industry reports) to give the executive summary
  and win-probability narrative real macro-context citations beyond the (fictional) challenge documents.
- Save as `backend/data/market_intelligence.json` — a short list of `{source, stat, url}` entries —
  cited alongside internal documents in the "Sources Used" output. This directly serves the brief's
  explicit call-out: "Sources Used ... including ... any additional sources, datasets, benchmarks,
  historical opportunities, market intelligence ... incorporated into the analysis."
- Cap it at one focused search pass. The internal challenge documents remain the primary evidence base
  — external market stats are supporting color, not a research deliverable in themselves.

## 9. Task assignment: Asier & Charles

Default split (swap if your actual skill fit runs the other way — the split is by track, not by name):
- **Asier — Backend/ML/LLM track** (§3): pricing engine, ML win-probability model, LLM agent layer,
  RAG, API, Render deployment.
- **Charles — Frontend track** (§4): Lovable app, dashboard UI, pitch-deck view, sources panel.

| Phase | Asier | Charles |
|---|---|---|
| 0 (~1h) | Scaffold FastAPI, write Contract Pydantic models (§2), stub `/analyze` returning fixture data, deploy stub to Render, share the URL | Scaffold Lovable app, commit `frontend/fixtures/example_result.json` matching the Contract, build the opportunity-picker screen shell |
| — sync — | Both confirm the Contract JSON shape is final before diverging further | |
| 1 (~3-4h) | Offline-parse challenge docs into `backend/data/*` fixtures (reuse this session's extraction scripts); build `pricing.py` + unit tests; train `win_model.py`, record holdout AUC | Build dashboard skeleton, all 9 output sections rendering against the fixture; opportunity-score gauge + pricing-scenario comparison table components |
| 2 (~4-5h) | Build extraction + gap/feasibility agents (§3b), RAG embedding setup; test both against Tecnomania and Pink Papaya, confirm ambiguity capture works | Build pitch-deck view + sources/citations panel; wire risk-severity badges |
| 3 (~4-5h) | Build synthesis/risk-pricing-narrative/win-prob-narrative/pitch-deck agents; wire full `/analyze` (§3c orchestration, §3d models); confirm schema-valid output for both opportunities | UI polish pass; finalize components against real (non-fixture) shapes seen so far |
| 4 (~2-3h) | On call to fix backend issues surfaced by live integration; add error handling for malformed input/timeouts | Point frontend at the live Render URL, run both opportunities end-to-end live |
| 5 (~2-3h) | Run `ecc:code-reviewer` joint review pass (opus tier, §7a) | Proofread the client-ready pitch-deck output for tone/typos before recording |
| 5 (both) | Record the 30s pitch video together; write the project doc PDF; final deploy smoke-tested cold | |
| buffer (~2h) | Whoever's ahead picks up synthetic-data stress tests (§8a) or the market-intelligence search (§8b) | |
