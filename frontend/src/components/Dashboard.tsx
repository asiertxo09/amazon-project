import { Navigate, Link } from "react-router-dom";
import { useOpportunity } from "../context/OpportunityContext";
import { ExecutiveSummary } from "./sections/ExecutiveSummary";
import { OpportunityScoreCard } from "./sections/OpportunityScoreCard";
import { RiskAssessment } from "./sections/RiskAssessment";
import { PricingScenarios } from "./sections/PricingScenarios";
import { CommercialStrategy } from "./sections/CommercialStrategy";
import { FollowUpActions } from "./sections/FollowUpActions";
import { WinProbabilitySection } from "./sections/WinProbabilitySection";
import { AssumptionsOpenQuestions } from "./sections/AssumptionsOpenQuestions";
import { SourcesPanel } from "./SourcesPanel";

export function Dashboard() {
  const { result, source } = useOpportunity();

  if (!result) return <Navigate to="/" replace />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {result.opportunity_id}
          </p>
          <h1 className="text-2xl font-bold text-navy-light">{result.company_name}</h1>
        </div>
        <div className="flex items-center gap-3">
          {source === "fixture" && (
            <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800 ring-1 ring-inset ring-amber-600/20">
              Showing example data — live backend not connected
            </span>
          )}
          <Link
            to="/pitch-deck"
            className="rounded-lg bg-amazon px-4 py-2 text-sm font-semibold text-navy transition hover:bg-amazon-dark"
          >
            View Client Pitch Deck →
          </Link>
        </div>
      </div>

      <ExecutiveSummary text={result.executive_summary} />

      <div className="grid gap-6 lg:grid-cols-2">
        <OpportunityScoreCard score={result.opportunity_score} volume={result.serviceable_volume} />
        <WinProbabilitySection winProbability={result.win_probability} />
      </div>

      <PricingScenarios scenarios={result.pricing_scenarios} />

      <div className="grid gap-6 lg:grid-cols-2">
        <RiskAssessment risks={result.risk_assessment} />
        <div className="space-y-6">
          <CommercialStrategy text={result.commercial_strategy} />
          <FollowUpActions actions={result.follow_up_actions} />
        </div>
      </div>

      <AssumptionsOpenQuestions items={result.assumptions_and_open_questions} />

      <SourcesPanel sources={result.sources_used} />
    </div>
  );
}
