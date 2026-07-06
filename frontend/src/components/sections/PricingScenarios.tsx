import type { PricingScenario } from "../../types/contract";
import { Card } from "../ui/Card";
import { Badge } from "../ui/Badge";

const SCENARIO_ACCENT: Record<PricingScenario["name"], string> = {
  Aggressive: "border-amazon",
  Balanced: "border-navy-light",
  Conservative: "border-emerald-400",
};

export function PricingScenarios({ scenarios }: { scenarios: PricingScenario[] }) {
  return (
    <Card title="Pricing Scenarios" eyebrow="Output 4 of 9">
      <div className="grid gap-4 sm:grid-cols-3">
        {scenarios.map((s) => (
          <div key={s.name} className={`rounded-lg border-t-4 bg-slate-50 p-4 ${SCENARIO_ACCENT[s.name]}`}>
            <div className="mb-2 flex items-center justify-between">
              <p className="font-semibold text-navy-light">{s.name}</p>
              <Badge>{s.margin_pct.toFixed(1)}% margin</Badge>
            </div>
            <p className="text-2xl font-bold text-navy-light">
              €{s.avg_price_per_parcel_eur.toFixed(2)}
              <span className="text-sm font-normal text-slate-500"> / parcel</span>
            </p>
            <p className="mt-3 text-sm text-slate-700">{s.rationale}</p>
            <p className="mt-2 text-xs text-slate-500">
              <span className="font-semibold">Tradeoffs: </span>
              {s.tradeoffs}
            </p>
          </div>
        ))}
      </div>
    </Card>
  );
}
