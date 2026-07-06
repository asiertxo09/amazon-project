import type { Source } from "../types/contract";
import { Card } from "./ui/Card";

export function SourcesPanel({ sources }: { sources: Source[] }) {
  return (
    <Card title="Sources Used" eyebrow="Output 9 of 9">
      <p className="mb-3 text-xs text-slate-500">
        Every claim in this analysis traces back to a document, dataset, or external source below.
      </p>
      <ul className="space-y-2">
        {sources.map((source, i) => (
          <li key={i} className="flex items-start gap-3 rounded-lg bg-slate-50 p-3">
            <span className="mt-0.5 shrink-0 rounded bg-navy px-1.5 py-0.5 font-mono text-[10px] font-semibold text-white">
              {i + 1}
            </span>
            <div>
              <p className="text-sm font-medium text-navy-light">{source.doc}</p>
              <p className="text-xs text-slate-600">{source.detail}</p>
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}
