import { Card } from "../ui/Card";

export function CommercialStrategy({ text }: { text: string }) {
  return (
    <Card title="Commercial Strategy" eyebrow="Output 5 of 9">
      <p className="leading-relaxed text-slate-700">{text}</p>
    </Card>
  );
}
