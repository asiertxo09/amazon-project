import { Link, useLocation } from "react-router-dom";
import { useOpportunity } from "../../context/OpportunityContext";

export function TopBar() {
  const { result } = useOpportunity();
  const location = useLocation();

  const navLink = (to: string, label: string) => {
    const active = location.pathname === to;
    return (
      <Link
        to={to}
        className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
          active ? "bg-amazon text-navy" : "text-white/80 hover:bg-white/10 hover:text-white"
        }`}
      >
        {label}
      </Link>
    );
  };

  return (
    <header className="bg-navy text-white">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
        <Link to="/" className="flex items-center gap-2 text-lg font-semibold tracking-tight">
          <span className="rounded bg-amazon px-2 py-0.5 text-navy">EOC</span>
          Enterprise Opportunity Copilot
        </Link>
        {result && (
          <nav className="flex items-center gap-1">
            {navLink("/dashboard", "Dashboard")}
            {navLink("/pitch-deck", "Pitch Deck")}
          </nav>
        )}
      </div>
    </header>
  );
}
