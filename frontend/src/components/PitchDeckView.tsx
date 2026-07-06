import { Navigate } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { useOpportunity } from "../context/OpportunityContext";
import { SourcesPanel } from "./SourcesPanel";

export function PitchDeckView() {
  const { result } = useOpportunity();

  if (!result) return <Navigate to="/" replace />;

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-amazon-dark">
            Output 7 of 9 — Client Pitch Deck
          </p>
          <h1 className="text-2xl font-bold text-navy-light">{result.company_name}</h1>
        </div>
        <button
          type="button"
          onClick={() => window.print()}
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-navy-light transition hover:bg-slate-50 print:hidden"
        >
          Export / Print
        </button>
      </div>

      <article className="prose prose-slate max-w-none rounded-xl border border-slate-200 bg-white p-8 shadow-sm prose-headings:text-navy-light prose-h1:text-3xl prose-h2:mt-6 prose-h2:border-b prose-h2:border-slate-100 prose-h2:pb-2">
        <ReactMarkdown>{result.pitch_deck_url_or_markdown}</ReactMarkdown>
      </article>

      <div className="mt-6 print:hidden">
        <SourcesPanel sources={result.sources_used} />
      </div>
    </div>
  );
}
