import { Link, useLocation } from "react-router-dom";
import { BarChart3, Gem, History, LogOut, Settings, Sparkles, User } from "lucide-react";
import { FalCreditsWidget } from "@/components/FalCreditsWidget";
import { useAuth } from "@/hooks/useAuth";

type Props = {
  subtitle?: string;
  children: React.ReactNode;
};

export function AppLayout({ subtitle = "Production Suite", children }: Props) {
  const { user, logout, isAdmin } = useAuth();
  const location = useLocation();

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-40 border-b border-jewel-border bg-jewel-surface/90 backdrop-blur-md">
        <div className="mx-auto flex h-[3.75rem] max-w-[1600px] w-full items-center justify-between gap-3 px-4 sm:px-6 lg:px-8">
          {/* Brand + credits status (left) — balance sits with identity, not after Admin */}
          <div className="flex min-w-0 items-center gap-3">
            <Link to="/" className="flex min-w-0 items-center gap-3 hover:opacity-90 transition-opacity">
              <div
                className="grid size-9 shrink-0 place-items-center rounded-jewel-md text-white"
                style={{ backgroundColor: "var(--jewel-accent)" }}
              >
                <Gem className="size-4" />
              </div>
              <div className="min-w-0">
                <h1 className="truncate text-[15px] font-semibold text-jewel-ink leading-none">
                  Jewel AI Studio
                </h1>
                <p className="mt-1 truncate text-[10px] font-semibold uppercase tracking-[0.08em] text-jewel-ink-muted">
                  {subtitle}
                </p>
              </div>
            </Link>
            {user && (
              <div className="hidden sm:block">
                <FalCreditsWidget />
              </div>
            )}
          </div>

          {/* Primary nav + account (right) */}
          <nav className="flex shrink-0 items-center gap-0.5 sm:gap-1" aria-label="Primary">
            <NavLink to="/" active={location.pathname === "/"} label="Studio">
              <Sparkles className="size-3.5" />
              <span className="hidden sm:inline">Studio</span>
            </NavLink>
            <NavLink to="/history" active={location.pathname === "/history"} label="History">
              <History className="size-3.5" />
              <span className="hidden sm:inline">History</span>
            </NavLink>
            <NavLink to="/rates" active={location.pathname === "/rates"} label="Rates">
              <BarChart3 className="size-3.5" />
              <span className="hidden sm:inline">Rates</span>
            </NavLink>
            {isAdmin && (
              <NavLink to="/admin" active={location.pathname === "/admin"} label="Admin">
                <Settings className="size-3.5" />
                <span className="hidden sm:inline">Admin</span>
              </NavLink>
            )}

            <div className="ml-1 hidden h-5 w-px bg-slate-200 sm:block" aria-hidden />

            {/* Mobile: credits near account actions */}
            {user && (
              <div className="sm:hidden">
                <FalCreditsWidget />
              </div>
            )}

            {user ? (
              <div className="ml-1 flex items-center gap-1">
                <span className="hidden max-w-[140px] truncate px-2 text-[12px] text-slate-500 lg:inline">
                  {user.email}
                </span>
                <button
                  type="button"
                  onClick={() => void logout()}
                  aria-label="Logout"
                  className="inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-[13px] font-medium text-slate-600 hover:bg-slate-100"
                >
                  <LogOut className="size-3.5" />
                  <span className="hidden sm:inline">Logout</span>
                </button>
              </div>
            ) : (
              <Link
                to="/login"
                aria-label="Login"
                className="ml-1 inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-[13px] font-medium text-slate-600 hover:bg-slate-100"
              >
                <User className="size-3.5" /> Login
              </Link>
            )}
          </nav>
        </div>
      </header>
      {children}
    </div>
  );
}

function NavLink({
  to,
  active,
  label,
  children,
}: {
  to: string;
  active: boolean;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <Link
      to={to}
      aria-label={label}
      className={`inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-[13px] font-medium transition-colors ${
        active ? "ui-nav-active" : "text-jewel-ink-muted hover:bg-jewel-muted hover:text-jewel-ink"
      }`}
    >
      {children}
    </Link>
  );
}
