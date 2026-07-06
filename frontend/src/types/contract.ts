/**
 * Mirrors backend/schemas/opportunity_result.py (PLAN.md §2, the Contract).
 * Keep field names in sync with the backend — this is the shared shape both
 * tracks build against.
 */

export type ScoreLabel = "Strong" | "Moderate" | "Weak";

export interface OpportunityScore {
  value: number;
  label: ScoreLabel;
  rationale: string;
}

export interface Exclusion {
  reason: string;
  volume_impact_pct: number;
}

export interface ServiceableVolume {
  declared_daily_volume: number;
  serviceable_daily_volume: number;
  geo_fit_pct: number;
  exclusions: Exclusion[];
}

export type RiskCategory = "Operational" | "Commercial" | "Financial";
export type RiskSeverity = "Low" | "Med" | "High";

export interface RiskItem {
  category: RiskCategory;
  risk: string;
  severity: RiskSeverity;
  evidence: string;
}

export type PricingScenarioName = "Aggressive" | "Balanced" | "Conservative";

export interface PricingScenario {
  name: PricingScenarioName;
  margin_pct: number;
  avg_price_per_parcel_eur: number;
  rationale: string;
  tradeoffs: string;
}

export type FactorDirection = "+" | "-";

export interface TopFactor {
  factor: string;
  direction: FactorDirection;
}

export interface WinProbability {
  value_pct: number;
  model: string;
  top_factors: TopFactor[];
}

export interface Source {
  doc: string;
  detail: string;
}

export interface OpportunityResult {
  opportunity_id: string;
  company_name: string;
  executive_summary: string;
  opportunity_score: OpportunityScore;
  serviceable_volume: ServiceableVolume;
  risk_assessment: RiskItem[];
  pricing_scenarios: PricingScenario[];
  commercial_strategy: string;
  follow_up_actions: string[];
  win_probability: WinProbability;
  pitch_deck_url_or_markdown: string;
  sources_used: Source[];
  assumptions_and_open_questions: string[];
}

export type DemoId = "tecnomania" | "pink_papaya";

export interface AnalyzeRequest {
  demo?: DemoId;
  opportunity_text?: string;
  company_name?: string;
}
