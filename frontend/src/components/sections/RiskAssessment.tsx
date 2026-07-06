import type { RiskItem } from "../../types/contract";
import { Card } from "../ui/Card";
import { SeverityBadge } from "../ui/Badge";

export function RiskAssessment({ risks }: { risks: RiskItem[] }) {
  return (
    <Card title="Risk Assessment" eyebrow="Output 3 of 9">
      <ul className="divide-y divide-slate-100">
        {risks.map((risk, i) => (
          <li key={i} className="flex flex-col gap-1 py-3 first:pt-0 last:pb-0">
            <div className="flex items-center justify-between gap-3">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {risk.category}
              </span>
              <SeverityBadge severity={risk.severity} />
            </div>
            <p className="text-sm font-medium text-navy-light">{risk.risk}</p>
            <p className="text-xs text-slate-500">Evidence: {risk.evidence}</p>
          </li>
        ))}
      </ul>
    </Card>
  );
}
