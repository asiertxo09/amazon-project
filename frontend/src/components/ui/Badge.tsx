import type { ReactNode } from "react";
import type { RiskSeverity } from "../../types/contract";

const SEVERITY_STYLES: Record<RiskSeverity, string> = {
  Low: "bg-emerald-100 text-emerald-800 ring-emerald-600/20",
  Med: "bg-amber-100 text-amber-800 ring-amber-600/20",
  High: "bg-red-100 text-red-800 ring-red-600/20",
};

export function SeverityBadge({ severity }: { severity: RiskSeverity }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${SEVERITY_STYLES[severity]}`}>
      {severity}
    </span>
  );
}

export function Badge({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ring-slate-500/20 bg-slate-100 text-slate-700 ${className}`}>
      {children}
    </span>
  );
}
