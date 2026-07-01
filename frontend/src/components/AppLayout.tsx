import { Link, useLocation } from "react-router-dom";
import { Gem, History, LogOut, Settings, Sparkles, User } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

type Props = {
  subtitle?: string;
  children: React.ReactNode;
};

export function AppLayout({ subtitle = "Production Suite", children }: Props) {
  const { user, logout } = useAuth();
  const location = useLocation();

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur shadow-sm">
        <div className="mx-auto flex h-16 max-w-[1600px] w-full items-center justify-between px-6 lg:px-8">
          <Link to="/" className="flex items-center gap-3 hover:opacity-90 transition-opacity">
            <div className="grid size-9 place-items-center rounded-xl bg-blue-600 text-white shadow-md shadow-blue-500/10">
              <Gem className="size-4" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-slate-900 leading-none tracking-tight">Jewel AI Studio</h1>
              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mt-1">{subtitle}</p>
            </div>
          </Link>
          <nav className="flex items-center gap-1">
            <NavLink to="/" active={location.pathname === "/"}>
              <Sparkles className="size-4" /> Studio
            </NavLink>
            <NavLink to="/history" active={location.pathname === "/history"}>
              <History className="size-4" /> History
            </NavLink>
            <NavLink to="/admin" active={location.pathname === "/admin"}>
              <Settings className="size-4" /> Admin
            </NavLink>
            {user ? (
              <button
                type="button"
                onClick={logout}
                className="ml-1 inline-flex h-8 items-center gap-1.5 rounded-lg px-3 text-[13px] font-semibold text-slate-600 hover:bg-slate-50"
              >
                <LogOut className="size-4" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            ) : (
              <Link
                to="/login"
                className="ml-1 inline-flex h-8 items-center gap-1.5 rounded-lg px-3 text-[13px] font-semibold text-slate-600 hover:bg-slate-50"
              >
                <User className="size-4" /> Login
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
      className={`inline-flex h-8 items-center gap-1.5 rounded-lg px-3 text-[13px] font-semibold transition-colors ${
        active ? "bg-blue-50 text-blue-700" : "text-slate-600 hover:bg-slate-50"
      }`}
    >
      {children}
    </Link>
  );
}
