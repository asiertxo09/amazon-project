import { Card } from "../ui/Card";

export function FollowUpActions({ actions }: { actions: string[] }) {
  return (
    <Card title="Follow-Up Actions" eyebrow="Output 6 of 9">
      <ol className="space-y-2">
        {actions.map((action, i) => (
          <li key={i} className="flex gap-3 text-sm text-slate-700">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amazon/20 text-xs font-bold text-amazon-dark">
              {i + 1}
            </span>
            {action}
          </li>
        ))}
      </ol>
    </Card>
  );
}
