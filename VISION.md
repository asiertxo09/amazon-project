# From Hackathon Demo to Game-Changer: The Opportunity Copilot, Unconstrained

This is an exploratory doc, not a build plan. PLAN.md describes what we built in 27 hours: a
reactive pipeline that takes one submitted RFQ and returns a scored, priced, risk-assessed
proposal. Everything below asks: what is this *actually* if nobody was watching the clock or the
budget?

## 1. What the hackathon version really is

Strip away the demo framing and the system is a **decision-support pipeline with three real
engines** (deterministic pricing, a trained classifier, an LLM narrative/extraction layer) chained
behind one contract. It only reacts — a human has to bring it a document. It only sees two
companies' worth of ground truth. It forgets everything the moment the response is returned. It
never touches a real system of record.

The most ambitious version of this isn't "a better version of the same pipeline" — it's removing
each of those four constraints one at a time: **reactive → proactive, narrow → continuously
learning, stateless → stateful/relational, isolated → integrated into how Amazon Shipping's
commercial org actually works day to day.**

## 2. The real goal, unconstrained

Not "score an RFQ." The goal becomes: **compress the entire enterprise logistics sales cycle** —
prospecting, qualification, pricing, negotiation, contracting, fulfillment, renewal, expansion —
into one continuously-learning system that a commercial team supervises rather than operates.
Amazon Shipping stops being the thing being sold *into* this tool and becomes the thing this tool
is *built for*: an internal product with its own roadmap, or eventually a licensable one.

## 3. The most ambitious features, if time/budget weren't real

Roughly in order of how much they change the shape of the product (not just its polish):

1. **Proactive opportunity discovery.** Right now a prospect has to walk in with an RFQ. The
   ambitious version watches for signal *before* that happens: new company registrations,
   warehouse/fulfillment-center openings, logistics-role job postings (hiring a "Head of Last
   Mile" is a strong buying signal), import/export customs filings, funding rounds, and even
   negative public sentiment toward a prospect's *current* carrier (review complaints, forum
   threads). The pipeline flips from "analyze what's handed to you" to "tell the sales team who to
   call this week and why."

2. **A live capacity/cost digital twin instead of static lookup tables.** The pricing engine today
   is a lookup table with hand-set guardrails. The real version simulates against actual network
   state: current fleet/driver capacity by region, live fuel indices, real linehaul cost telemetry,
   warehouse throughput headroom. Pricing a deal becomes "can we actually absorb this volume
   without degrading existing SLAs," not just "is it geographically in scope."

3. **A negotiation copilot, not just a proposal generator.** A live-call assistant (with consent
   and clear disclosure) that listens to a sales call, and — grounded in the exact same pricing
   guardrails and risk model — prompts the account exec in real time: "they just brought up a
   competitor quote 8% below yours; here's the lowest margin-safe counter." This is the single
   biggest leap from "reporting tool" to "commercial weapon."

4. **A causal, not correlational, win model.** Logistic regression on 360 rows tells you
   *correlation* between geo-fit and winning. It cannot answer "if we discount 2% more, does win
   probability actually rise, and by how much." That needs an uplift/causal-inference layer
   (double ML, or even a controlled experimentation program on real pricing offers) so pricing
   recommendations are actionable, not just descriptive.

5. **Contract-lifecycle and expansion intelligence.** The moment a deal is won today, this system's
   job is done. The ambitious version keeps watching: actual shipped volume vs. contracted volume,
   SLA breach patterns, renewal timing — and auto-drafts the upsell/cross-sell play (e.g., "this
   Peninsula-only B2C account's actual shipments are 40% B2B-shaped, propose the B2B tier the
   moment it's launched").

6. **A red-team/adversarial reviewer agent** that tries to break every generated pitch before a
   human sees it — same instinct as a code-review pass, aimed at sales narratives instead of code:
   "this pricing rationale ignores that Pink Papaya's own numbers contradict each other; don't let
   the exec quote a number that isn't defensible."

7. **Guardrailed autonomous action**, not just narration. Within hard, human-set bounds (margin
   floor, geographic scope, contract length), let the system actually draft and send a revised
   quote in response to a counter-offer email — escalating to a human the moment it's outside
   guardrails. This is the step that turns it from "copilot" into genuine leverage: the system
   handles the 80% of negotiation that's mechanical, humans handle the 20% that's judgment.

8. **A continuous learning loop.** Every closed deal — won *and* lost, with a labeled *reason*
   (price, coverage, service level, timing — not just a binary outcome) — feeds back into
   retraining. The 360-row static CSV becomes a live, growing, self-correcting dataset instead of a
   one-time training snapshot.

## 4. Technologies I'd bring in

- **Orchestration**: keep resisting LangChain-style overhead for the linear stuff, but once
  workflows span days (a negotiation thread, a renewal cycle) a durable-execution engine
  (Temporal, or AWS Step Functions if staying in-ecosystem) earns its keep — these need to survive
  restarts and resume mid-conversation, which a plain `asyncio` pipeline doesn't do.
- **Streaming ingestion**: Kafka/Kinesis for real-time volume/cost telemetry and CDC (change data
  capture) out of Salesforce/CRM, instead of the batch-CSV-at-training-time approach today.
- **Storage, layered by shape of data** (see §6 for the full picture):
  - Postgres/Aurora for the relational core (opportunities, deals, contracts, accounts).
  - S3 for raw ingested artifacts (documents, audio, images, call recordings).
  - A vector store (pgvector to start, dedicated service like OpenSearch/Pinecone once the RAG
    corpus grows past a few thousand passages) for semantic retrieval over service descriptions,
    contract templates, and the growing library of past proposals.
  - A feature store (Feast, or a lean homegrown one) so training and real-time inference use
    exactly the same feature computation — avoids train/serve skew, which the current
    train-once-from-a-CSV setup doesn't have to worry about yet but will the moment features come
    from live systems.
  - A knowledge graph (Neo4j, or a graph layer over Postgres) once the object of analysis is really
    a *network* — companies, stakeholders, deals, competitors, signals — not a flat table. Pink
    Papaya's "Lucía vs. Marta disagree on France" is exactly the kind of fact a graph represents
    naturally and a flat JSON blob doesn't.
- **ML**: graduate from logistic regression to gradient-boosted ensembles as row count grows from
  hundreds to tens of thousands, with the causal/uplift layer from §3.4 sitting alongside it, not
  replacing the interpretable model — you want both "why" and "what if."
- **Multimodal ingestion**: speech-to-text (Whisper/AWS Transcribe) for call recordings, a
  vision-capable model for warehouse/product photos (rough dimension and packaging estimation from
  images), OCR for scanned paperwork.
- **LLM layer**: multi-provider routing by cost/latency/complexity (small model for narration tasks
  like today's win-prob narrator, frontier model reserved for extraction/negotiation reasoning),
  and eventually a distilled/fine-tuned small model for the highest-volume narrow tasks once enough
  real examples exist to distill from.
- **Governance, because this is Amazon**: full audit trail of every LLM decision (replayable, not
  just logged), human-in-the-loop approval gates wired to the guardrail thresholds, and strict
  data-residency/PII handling — especially once real call audio and real customer PII are in scope,
  which changes the compliance posture completely from "processing two fictional RFQs."

## 5. What more information would actually move the needle

- **Real internal systems**: actual TMS/routing capacity data (not a lookup table), the real cost
  structure, the live CRM pipeline, real contract templates and legal constraints, real
  renewal/churn history.
- **Labeled loss reasons.** This is the single highest-leverage missing field. "Won/Lost" without
  "lost because price, not because coverage" caps how much the win model can ever explain or act
  on — right now every lost deal looks the same to the classifier.
- **External signal feeds**: customs/import-export filings, company registries, macro e-commerce
  growth indices by region, competitor public rate cards and service complaints, regulatory
  constraints per country as international coverage expands beyond Spain/Balearics.
- **Real capacity constraints** — genuine fleet/warehouse feasibility, not just "is this postcode
  in our coverage polygon."
- **Ground-truth on pricing elasticity** — actual A/B'd pricing outcomes, which is what would let
  the causal model in §3.4 be trained on real experiments instead of only observational data.

## 6. Information flow, end to end

```
 SIGNAL DETECTION            QUALIFICATION              COMMERCIAL ACTION
 ───────────────             ─────────────              ─────────────────
 public/web signals      →   extraction + gap/     →    pricing + risk       →   pitch / negotiation
 CRM inbound leads            feasibility agents         + win-probability        copilot
 customs/registry feeds       (today's pipeline,          (causal + capacity
                              extended with real          twin, not lookup
                              capacity data)               tables)
        │                          │                            │
        └──────────────┬───────────┴──────────────┬─────────────┘
                        ▼                          ▼
                 knowledge graph            feature store / vector store
                 (companies, people,        (RAG corpus, ML features,
                 deals, signals)            comparable-deal retrieval)
                        │                          │
                        └────────────┬─────────────┘
                                     ▼
                          CONTRACT + FULFILLMENT MONITORING
                          (shipped vs. contracted volume,
                          SLA adherence, renewal timing)
                                     │
                                     ▼
                          FEEDBACK INTO TRAINING
                          (labeled win/loss + reason,
                          pricing-elasticity experiments)
                                     │
                                     └── loops back to qualification/pricing
```

The critical difference from today: the loop actually closes. Every stage writes back into the
knowledge graph and feature store, so the system a year from now has genuinely learned something
the hackathon version structurally cannot — it only ever sees the two documents you hand it.

## 7. More formats worth ingesting

- **Audio**: sales call recordings and voicemails (with consent) — the richest untapped signal for
  "named pain points," which right now only exist if someone typed them into an RFQ.
- **Images/video**: warehouse photos or a site-visit video, for a rough automated read on parcel
  size/weight profile and operational maturity — surprisingly informative and never captured today.
- **Full email threads**, not a single pasted document — most of the real contradictions (like
  Pink Papaya's Lucía/Marta disagreement) live in *who said what to whom over time*, which a single
  flattened text blob erases.
- **Direct EDI/API feeds from a prospect's own OMS/WMS** — real live volume data instead of a
  self-reported "we ship about 3,800/day," which removes an entire class of the
  ambiguity-and-contradiction problem at the source.
- **Spreadsheets/ERP exports** for existing shipping cost/volume history, which is far more
  reliable ground truth than prose descriptions.
- **Public web signals**: job postings, LinkedIn hiring activity, news of new fulfillment centers —
  feeds directly into §3.1's proactive discovery.

## 8. Storage & retrieval, concretely

Four layers, each doing one job:

1. **Raw ingestion (S3 + Glue/ETL)** — every artifact in its original form (PDF, audio, image,
   email export), immutable, timestamped, source-tagged. Nothing is ever only a working file.
2. **Curated structured store (Postgres/Aurora)** — the relational core: accounts, opportunities,
   contracts, pricing scenarios, decisions, and the audit trail of every agent action against them.
   This is what today's Pydantic `OpportunityResult` should ultimately be *rows in*, not a
   one-off JSON blob per request.
3. **Semantic + relational retrieval**:
   - a vector index (pgvector to start) over the growing corpus of service descriptions, contract
     templates, and past proposals, replacing today's ~50-passage in-memory numpy array once the
     corpus is genuinely large;
   - a knowledge graph over companies/people/deals/signals, because the interesting questions
     ("which stakeholders at this account disagree, and about what") are graph queries, not
     similarity search.
4. **Feature store** for ML — the same `geo_fit_pct`/`pain_severity`/etc. features computed once
   and shared between training and real-time inference, so the model serving a live pricing
   decision never drifts from the model that was validated offline.

## 9. A plausible staged path there

- **Stage 0 (what exists now)**: reactive, single-document analysis, static training data, no
  memory between requests.
- **Stage 1**: same shape, but wired to real Amazon systems (actual cost/capacity data, real
  CRM pipeline) and a continuous feedback loop with labeled loss reasons.
- **Stage 2**: proactive discovery — the system finds prospects, not just scores the ones handed to
  it.
- **Stage 3**: negotiation copilot embedded directly in the live sales workflow.
- **Stage 4**: guardrailed autonomous commercial action — and, if the product is good enough at
  this point, it stops being an internal tool and becomes something Amazon could license to other
  logistics/carrier businesses as its own product line. That's the literal "game-changer company"
  version: not a better hackathon demo, but a new revenue line built on infrastructure Amazon
  Shipping already needed internally anyway.

## 10. Open questions worth answering before chasing any of this

- Would Amazon actually allow real customer call audio/PII to be processed by third-party LLM
  providers (Groq/NVIDIA/etc.), or does this require staying entirely inside AWS-native models
  (Bedrock) for compliance reasons?
- Is the ambition here "better internal tooling for Amazon Shipping" or "a genuinely new product
  Amazon could sell" — those imply very different architectures (single-tenant vs. multi-tenant
  from day one).
- What's the actual organizational appetite for *autonomous* pricing/negotiation actions vs.
  advisory-only output forever? This changes whether §3.7 is worth building at all.
- Who owns "loss reason" labeling in practice — is there a real workflow (e.g., a mandatory CRM
  field on deal close) that could realistically backfill the single most valuable missing dataset
  field, or would it need to be built from scratch?
