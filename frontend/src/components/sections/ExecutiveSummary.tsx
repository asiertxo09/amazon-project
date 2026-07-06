import { Card } from "../ui/Card";

export function ExecutiveSummary({ text }: { text: string }) {
  return (
    <Card title="Executive Summary" eyebrow="Output 1 of 9">
      <p className="leading-relaxed text-slate-700">{text}</p>
    </Card>
  );
}
