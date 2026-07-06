export function AssumptionsOpenQuestions({ items }: { items: string[] }) {
  if (items.length === 0) return null;

  return (
    <section className="rounded-xl border border-amber-300 bg-amber-50 p-5">
      <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold text-amber-900">
        <span aria-hidden>⚠️</span> Assumptions &amp; Open Questions
      </h2>
      <p className="mb-3 text-xs text-amber-800">
        Ambiguities and contradictions in the source material are surfaced here rather than
        silently resolved.
      </p>
      <ul className="list-disc space-y-1.5 pl-5 text-sm text-amber-900">
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </section>
  );
}
