import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { analyze, type AnalyzeOutcome } from "../lib/api";
import type { AnalyzeRequest, OpportunityResult } from "../types/contract";

interface OpportunityContextValue {
  result: OpportunityResult | null;
  source: AnalyzeOutcome["source"] | null;
  isLoading: boolean;
  error: string | null;
  runAnalysis: (request: AnalyzeRequest) => Promise<boolean>;
  reset: () => void;
}

const OpportunityContext = createContext<OpportunityContextValue | null>(null);

export function OpportunityProvider({ children }: { children: ReactNode }) {
  const [result, setResult] = useState<OpportunityResult | null>(null);
  const [source, setSource] = useState<AnalyzeOutcome["source"] | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runAnalysis = useCallback(async (request: AnalyzeRequest) => {
    setIsLoading(true);
    setError(null);
    try {
      const outcome = await analyze(request);
      setResult(outcome.result);
      setSource(outcome.source);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong analyzing this opportunity.");
      return false;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setSource(null);
    setError(null);
  }, []);

  const value = useMemo(
    () => ({ result, source, isLoading, error, runAnalysis, reset }),
    [result, source, isLoading, error, runAnalysis, reset],
  );

  return <OpportunityContext.Provider value={value}>{children}</OpportunityContext.Provider>;
}

export function useOpportunity(): OpportunityContextValue {
  const ctx = useContext(OpportunityContext);
  if (!ctx) throw new Error("useOpportunity must be used within an OpportunityProvider");
  return ctx;
}
