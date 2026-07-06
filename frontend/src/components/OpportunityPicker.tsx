import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useOpportunity } from "../context/OpportunityContext";
import type { DemoId } from "../types/contract";

const DEMOS: { id: DemoId; name: string; blurb: string }[] = [
  {
    id: "tecnomania",
    name: "Tecnomania S.L.U.",
    blurb: "Mid-size Spanish electronics retailer — peninsula + Balearic B2C parcel volume.",
  },
  {
    id: "pink_papaya",
    name: "Pink Papaya",
    blurb: "Opportunity with conflicting declared figures — stress-tests ambiguity handling.",
  },
];

export function OpportunityPicker() {
  const { runAnalysis, isLoading, error } = useOpportunity();
  const navigate = useNavigate();
  const [pastedText, setPastedText] = useState("");
  const [activeDemo, setActiveDemo] = useState<DemoId | null>(null);

  async function handleDemo(id: DemoId) {
    setActiveDemo(id);
    const ok = await runAnalysis({ demo: id });
    if (ok) navigate("/dashboard");
  }

  async function handlePasteSubmit() {
    setActiveDemo(null);
    const ok = await runAnalysis({ opportunity_text: pastedText });
    if (ok) navigate("/dashboard");
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold text-navy-light">Analyze an opportunity</h1>
        <p className="mt-2 text-slate-600">
          Pick one of the two challenge opportunities, or paste your own opportunity brief to
          generate the full 9-output analysis.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {DEMOS.map((demo) => (
          <button
            key={demo.id}
            type="button"
            disabled={isLoading}
            onClick={() => handleDemo(demo.id)}
            className="rounded-xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:border-amazon hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60"
          >
            <p className="font-semibold text-navy-light">{demo.name}</p>
            <p className="mt-1 text-sm text-slate-600">{demo.blurb}</p>
            {isLoading && activeDemo === demo.id && (
              <p className="mt-3 text-sm font-medium text-amazon-dark">Analyzing…</p>
            )}
          </button>
        ))}
      </div>

      <div className="my-6 flex items-center gap-3 text-xs font-medium uppercase tracking-wide text-slate-400">
        <div className="h-px flex-1 bg-slate-200" />
        or paste your own
        <div className="h-px flex-1 bg-slate-200" />
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <textarea
          value={pastedText}
          onChange={(e) => setPastedText(e.target.value)}
          rows={8}
          placeholder="Paste the opportunity brief text here (RFQ, client email, requirements doc, etc.)"
          className="w-full resize-y rounded-lg border border-slate-200 p-3 text-sm text-navy-light placeholder:text-slate-400 focus:border-amazon focus:outline-none"
        />
        <div className="mt-3 flex justify-end">
          <button
            type="button"
            disabled={isLoading || pastedText.trim().length === 0}
            onClick={handlePasteSubmit}
            className="rounded-lg bg-navy px-4 py-2 text-sm font-semibold text-white transition hover:bg-navy-light disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isLoading && activeDemo === null && pastedText ? "Analyzing…" : "Analyze opportunity"}
          </button>
        </div>
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}
    </div>
  );
}
