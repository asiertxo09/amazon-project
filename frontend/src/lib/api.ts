import type { AnalyzeRequest, OpportunityResult } from "../types/contract";
import exampleResult from "../../fixtures/example_result.json";

const API_BASE_URL = (import.meta.env.VITE_API_URL ?? "").replace(/\/+$/, "");

export class AnalyzeError extends Error {}

/**
 * Result of a successful analyze() call, tagged with whether it came from
 * the live backend or the bundled fixture (PLAN.md §4: "Swap the fixture
 * for the live Render URL in Phase 4. Keep the fixture around after that as
 * a fallback demo path in case the live backend hiccups during judging.").
 */
export interface AnalyzeOutcome {
  result: OpportunityResult;
  source: "live" | "fixture";
}

async function callBackend(request: AnalyzeRequest): Promise<OpportunityResult> {
  const res = await fetch(`${API_BASE_URL}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new AnalyzeError(detail?.detail ?? `Analyze request failed (${res.status})`);
  }
  return res.json();
}

/**
 * Demo requests degrade to the bundled fixture when no live backend is
 * configured yet (Phase 0-3) or the live call fails — Tecnomania only, since
 * that's the one fixture shape committed for both tracks to build against.
 * Pasted-text requests always need the real pipeline; there's no honest
 * client-side stand-in for it.
 */
export async function analyze(request: AnalyzeRequest): Promise<AnalyzeOutcome> {
  if (API_BASE_URL) {
    try {
      return { result: await callBackend(request), source: "live" };
    } catch (err) {
      if (!request.demo) throw err;
      // fall through to fixture below
    }
  }

  if (request.demo === "tecnomania") {
    return { result: exampleResult as OpportunityResult, source: "fixture" };
  }

  throw new AnalyzeError(
    API_BASE_URL
      ? "Live backend is unreachable and no offline demo data exists for this opportunity."
      : "No backend configured yet (set VITE_API_URL) and no offline demo data exists for this opportunity.",
  );
}
