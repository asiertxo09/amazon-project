import type { WinProbability } from "../../types/contract";
import { Card } from "../ui/Card";
import { Gauge } from "../ui/Gauge";

export function WinProbabilitySection({ winProbability }: { winProbability: WinProbability }) {
  return (
    <Card title="Win Probability" eyebrow="Output 8 of 9">
      <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-start">
        <Gauge value={winProbability.value_pct} label="Win chance" sublabel={winProbability.model} />
        <div className="flex-1">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Top contributing factors
          </p>
          <ul className="space-y-1.5">
            {winProbability.top_factors.map((f) => (
              <li key={f.factor} className="flex items-center gap-2 text-sm text-slate-700">
                <span
                  className={`flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold ${
                    f.direction === "+"
                      ? "bg-emerald-100 text-emerald-700"
                      : "bg-red-100 text-red-700"
                  }`}
                >
                  {f.direction}
                </span>
                <code className="text-xs text-slate-500">{f.factor}</code>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Card>
  );
}
