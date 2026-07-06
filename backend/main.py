"""FastAPI entrypoint. Single POST /analyze endpoint (PLAN.md §3e)."""
import asyncio
import json
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.agents.llm_client import LLMNotConfiguredError
from backend.agents.pipeline import run_pipeline
from backend.schemas.opportunity_result import AnalyzeRequest, OpportunityResult

logger = logging.getLogger(__name__)

app = FastAPI(title="Enterprise Opportunity Copilot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ROOT_DIR = Path(__file__).resolve().parent.parent
FIXTURE_PATH = ROOT_DIR / "frontend" / "fixtures" / "example_result.json"
DEMO_TEXT_PATHS = {
    "tecnomania": Path(__file__).resolve().parent / "data" / "tecnomania.txt",
    "pink_papaya": Path(__file__).resolve().parent / "data" / "pink_papaya.txt",
}
PIPELINE_TIMEOUT_SECONDS = 90


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/analyze", response_model=OpportunityResult)
async def analyze(request: AnalyzeRequest) -> OpportunityResult:
    if not request.demo and not (request.opportunity_text and request.opportunity_text.strip()):
        raise HTTPException(status_code=400, detail="Provide either 'demo' or a non-empty 'opportunity_text'")

    if request.demo:
        opportunity_text = DEMO_TEXT_PATHS[request.demo].read_text(encoding="utf-8")
        opportunity_id = request.demo
    else:
        opportunity_text = request.opportunity_text
        opportunity_id = None

    try:
        return await asyncio.wait_for(
            run_pipeline(opportunity_text, opportunity_id=opportunity_id),
            timeout=PIPELINE_TIMEOUT_SECONDS,
        )
    except LLMNotConfiguredError as exc:
        if request.demo:
            # Fixture fallback keeps the demo path alive if LLM keys aren't set
            # (e.g. local dev without secrets) rather than hard-failing.
            logger.warning("LLM not configured (%s); serving fixture for demo=%s", exc, request.demo)
            fixture = json.loads(FIXTURE_PATH.read_text())
            return OpportunityResult(**fixture)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Analysis timed out — please retry.") from exc
