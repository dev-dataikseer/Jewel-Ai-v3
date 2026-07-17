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
      <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/90 backdrop-blur-md">
        <div className="mx-auto flex h-[3.75rem] max-w-[1600px] w-full items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
          <Link to="/" className="flex min-w-0 items-center gap-3 hover:opacity-90 transition-opacity">
            <div className="grid size-9 shrink-0 place-items-center rounded-xl bg-blue-600 text-white shadow-sm shadow-blue-600/20">
              <Gem className="size-4" />
            </div>
            <div className="min-w-0">
              <h1 className="truncate text-[15px] font-semibold text-slate-900 leading-none">
                Jewel AI Studio
              </h1>
              <p className="mt-1 truncate text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">
                {subtitle}
              </p>
            </div>
          </Link>

          <nav className="flex items-center gap-0.5 sm:gap-1" aria-label="Primary">
            <NavLink to="/" active={location.pathname === "/"}>
              <Sparkles className="size-3.5" />
              <span className="hidden sm:inline">Studio</span>
            </NavLink>
            <NavLink to="/history" active={location.pathname === "/history"}>
              <History className="size-3.5" />
              <span className="hidden sm:inline">History</span>
            </NavLink>
            <NavLink to="/rates" active={location.pathname === "/rates"}>
              <BarChart3 className="size-3.5" />
              <span className="hidden sm:inline">Rates</span>
            </NavLink>
            {isAdmin && (
              <NavLink to="/admin" active={location.pathname === "/admin"}>
                <Settings className="size-3.5" />
                <span className="hidden sm:inline">Admin</span>
              </NavLink>
            )}

            <div className="ml-1 hidden h-5 w-px bg-slate-200 sm:block" aria-hidden />

            {user && (
              <div className="ml-1">
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
                  onClick={logout}
                  className="inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-[13px] font-medium text-slate-600 hover:bg-slate-100"
                >
                  <LogOut className="size-3.5" />
                  <span className="hidden sm:inline">Logout</span>
                </button>
              </div>
            ) : (
              <Link
                to="/login"
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
  children,
}: {
  to: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      to={to}
      className={`inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-[13px] font-medium transition-colors ${
        active
          ? "bg-blue-50 text-blue-700"
          : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
      }`}
    >
      {children}
    </Link>
  );
}
