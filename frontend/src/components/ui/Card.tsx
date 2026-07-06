import type { ReactNode } from "react";

interface CardProps {
  title: string;
  eyebrow?: string;
  children: ReactNode;
  className?: string;
  actions?: ReactNode;
}

export function Card({ title, eyebrow, children, className = "", actions }: CardProps) {
  return (
    <section className={`rounded-xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          {eyebrow && (
            <p className="text-xs font-semibold uppercase tracking-wide text-amazon-dark">{eyebrow}</p>
          )}
          <h2 className="text-lg font-semibold text-navy-light">{title}</h2>
        </div>
        {actions}
      </div>
      {children}
    </section>
  );
}
