import type { OpportunityScore, ServiceableVolume } from "../../types/contract";
import { Card } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { Gauge } from "../ui/Gauge";

const LABEL_COLOR: Record<OpportunityScore["label"], string> = {
  Strong: "text-emerald-500",
  Moderate: "text-amber-500",
  Weak: "text-red-500",
};

export function OpportunityScoreCard({
  score,
  volume,
}: {
  score: OpportunityScore;
  volume: ServiceableVolume;
}) {
  return (
    <Card title="Opportunity Score" eyebrow="Output 2 of 9">
      <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-start">
        <Gauge value={score.value} label={score.label} colorClass={LABEL_COLOR[score.label]} />
        <div className="flex-1">
          <p className="text-sm text-slate-700">{score.rationale}</p>

          <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
            <div className="rounded-lg bg-slate-50 p-3">
              <p className="text-xs text-slate-500">Declared daily volume</p>
              <p className="font-semibold text-navy-light">
                {volume.declared_daily_volume.toLocaleString()}
              </p>
            </div>
            <div className="rounded-lg bg-slate-50 p-3">
              <p className="text-xs text-slate-500">Serviceable daily volume</p>
              <p className="font-semibold text-navy-light">
                {volume.serviceable_daily_volume.toLocaleString()}
              </p>
            </div>
            <div className="col-span-2 rounded-lg bg-slate-50 p-3">
              <p className="text-xs text-slate-500">Geo-fit</p>
              <p className="font-semibold text-navy-light">{(volume.geo_fit_pct * 100).toFixed(0)}%</p>
            </div>
          </div>

          {volume.exclusions.length > 0 && (
            <div className="mt-4">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Exclusions
              </p>
              <ul className="space-y-1.5">
                {volume.exclusions.map((ex) => (
                  <li key={ex.reason} className="flex items-center justify-between gap-3 text-sm">
                    <span className="text-slate-700">{ex.reason}</span>
                    <Badge>-{(ex.volume_impact_pct * 100).toFixed(1)}%</Badge>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
