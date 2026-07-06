"""Narrow-scope RAG store over the Service Description + pricing guardrails
(PLAN.md §3b). No hosted vector DB — a plain numpy array with cosine
similarity, embedded once at process startup via sentence-transformers
(CPU, no external API). Grounds the gap/feasibility agent's citations for
"Sources Used".
"""
import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

DATA_DIR = Path(__file__).resolve().parent / "data"
MODEL_NAME = "all-MiniLM-L6-v2"


def _build_passages() -> list[dict]:
    passages: list[dict] = []

    service_text = (DATA_DIR / "service_description.txt").read_text(encoding="utf-8")
    for block in service_text.split("--- slide ")[1:]:
        slide_num, _, rest = block.partition(" ---\n")
        lines = [l.strip() for l in rest.split("\n") if l.strip()]
        for i in range(0, len(lines), 2):
            chunk = " ".join(lines[i : i + 2])
            passages.append({"doc": "Service_description.pptx", "detail": f"slide {slide_num}", "text": chunk})

    pricing = json.loads((DATA_DIR / "pricing_tables.json").read_text(encoding="utf-8"))
    g = pricing["guardrails"]
    guardrail_lines = [
        f"Region multiplier: Balearic Islands x{pricing['region_multiplier']['balearic_islands']}, "
        f"peninsula x{pricing['region_multiplier']['peninsula']}.",
        f"Premium add-ons: OTP +EUR{pricing['premium_addons_eur']['otp']}/parcel, "
        f"SOD +EUR{pricing['premium_addons_eur']['sod']}/parcel.",
        f"Fixed overhead: ${pricing['fixed_overhead_usd_per_parcel']}/parcel at "
        f"{pricing['usd_to_eur_fx_rate']} EUR/USD FX rate.",
        f"Finance guardrails: minimum contribution margin {g['minimum_contribution_margin_pct']}%, "
        f"target {g['target_contribution_margin_pct']}%, VP approval required below "
        f"{g['vp_approval_required_below_pct']}%, automatic no-go below {g['automatic_no_go_below_pct']}%.",
    ]
    for line in guardrail_lines:
        passages.append({"doc": "PL_Industry_Challenge.xlsx", "detail": "pricing guardrails (Read Me)", "text": line})

    return passages


class RAGStore:
    def __init__(self) -> None:
        self._model = SentenceTransformer(MODEL_NAME)
        self._passages = _build_passages()
        texts = [p["text"] for p in self._passages]
        self._embeddings = np.array(self._model.encode(texts, normalize_embeddings=True))

    def search(self, query: str, k: int = 5) -> list[dict]:
        q_emb = self._model.encode([query], normalize_embeddings=True)[0]
        scores = self._embeddings @ q_emb
        top_idx = np.argsort(-scores)[:k]
        return [{**self._passages[i], "score": float(scores[i])} for i in top_idx]


_store: RAGStore | None = None


def get_store() -> RAGStore:
    global _store
    if _store is None:
        _store = RAGStore()
    return _store
