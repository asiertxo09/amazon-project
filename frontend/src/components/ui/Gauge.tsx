const RADIUS = 54;
const CIRCUMFERENCE = Math.PI * RADIUS; // semicircle arc length

interface GaugeProps {
  value: number; // 0-100
  label: string;
  sublabel?: string;
  colorClass?: string;
}

export function Gauge({ value, label, sublabel, colorClass = "text-amazon" }: GaugeProps) {
  const clamped = Math.max(0, Math.min(100, value));
  const offset = CIRCUMFERENCE * (1 - clamped / 100);

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 120 66" className="w-48">
        <path
          d="M 6 60 A 54 54 0 0 1 114 60"
          fill="none"
          stroke="currentColor"
          strokeWidth="10"
          strokeLinecap="round"
          className="text-slate-200"
        />
        <path
          d="M 6 60 A 54 54 0 0 1 114 60"
          fill="none"
          stroke="currentColor"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={offset}
          className={colorClass}
        />
        <text x="60" y="54" textAnchor="middle" className="fill-navy-light text-2xl font-bold">
          {clamped}
        </text>
      </svg>
      <p className="-mt-1 text-sm font-semibold text-navy-light">{label}</p>
      {sublabel && <p className="text-xs text-slate-500">{sublabel}</p>}
    </div>
  );
}
