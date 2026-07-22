import { Link, useLocation } from "react-router-dom";
import {
  ChevronDown,
  History,
  Settings,
  Sparkles,
  User,
} from "lucide-react";
import { BrandMark } from "@/components/ui/BrandMark";
import { FalCreditsWidget } from "@/components/FalCreditsWidget";
import { OfflineBanner } from "@/components/OfflineBanner";
import { useAuth } from "@/hooks/useAuth";

type Props = {
  subtitle?: string;
  footerModel?: string | null;
  children: React.ReactNode;
};

export function AppLayout({
  subtitle = "AI Creative Suite",
  footerModel,
  children,
}: Props) {
  const { user, logout, isAdmin } = useAuth();
  const location = useLocation();

  return (
    <div className="h-dvh max-h-dvh flex flex-col overflow-hidden bg-[var(--jewel-bg)]">
      <OfflineBanner />
      <header className="shrink-0 z-40 bg-white border-b border-[var(--jewel-border)]">
        <div className="mx-auto flex h-[3.75rem] w-full items-center justify-between gap-2 sm:gap-3 px-3 sm:px-6 lg:px-8 min-w-0">
          <div className="flex min-w-0 items-center gap-3 sm:gap-6">
            <Link to="/" className="flex min-w-0 items-center gap-2.5 hover:opacity-90 transition-opacity">
              <BrandMark size={36} className="shrink-0 rounded-[10px] shadow-sm" />
              <div className="min-w-0 hidden xs:flex sm:flex flex-col justify-center">
                <p className="truncate text-[15px] font-bold text-[var(--jewel-ink)] leading-none">
                  Jewel AI Studio
                </p>
                <p className="mt-1 truncate text-[11px] font-medium text-[var(--jewel-ink-muted)] leading-none">
                  {subtitle}
                </p>
              </div>
            </Link>
          </div>

          <nav className="flex min-w-0 shrink items-center gap-0.5 sm:gap-1 h-full overflow-x-auto" aria-label="Primary">
            <NavLink to="/" active={location.pathname === "/"} label="Studio">
              <Sparkles className="size-3.5 stroke-[1.75]" />
              <span className="hidden sm:inline">Studio</span>
            </NavLink>
            <NavLink to="/history" active={location.pathname === "/history"} label="History">
              <History className="size-3.5 stroke-[1.75]" />
              <span className="hidden sm:inline">History</span>
            </NavLink>
            {isAdmin && (
              <NavLink to="/admin" active={location.pathname.startsWith("/admin")} label="Admin">
                <Settings className="size-3.5 stroke-[1.75]" />
                <span className="hidden sm:inline">Admin</span>
              </NavLink>
            )}
          </nav>

          <div className="flex items-center gap-2 sm:gap-3 shrink-0">
            {user && (
              <div className="hidden md:block">
                <FalCreditsWidget />
              </div>
            )}

            <div className="hidden sm:block h-6 w-px bg-[var(--jewel-border)]" />

            {user ? (
              <button
                type="button"
                className="flex items-center gap-2 hover:opacity-80 transition-opacity shrink-0"
                onClick={() => void logout()}
                aria-label="Account menu — sign out"
              >
                <div className="size-8 rounded-full bg-[var(--jewel-accent-soft)] flex items-center justify-center text-[var(--jewel-accent)] font-bold text-[13px] border border-[color-mix(in_srgb,var(--jewel-accent)_25%,transparent)]">
                  {user.email?.[0]?.toUpperCase() || "U"}
                </div>
                <div className="hidden xl:flex flex-col items-start">
                  <span className="text-[13px] font-bold text-[var(--jewel-ink)] leading-none max-w-[9rem] truncate">
                    {user.email}
                  </span>
                  <span className="text-[11px] text-[var(--jewel-ink-muted)] mt-1 leading-none">
                    {isAdmin ? "Studio Admin" : "User"}
                  </span>
                </div>
                <ChevronDown className="size-3.5 text-[var(--jewel-ink-faint)] ml-0.5 hidden sm:block" />
              </button>
            ) : (
              <Link to="/login" className="ui-btn-ghost h-8 px-2.5 text-[13px]">
                <User className="size-3.5 stroke-[1.75]" /> Login
              </Link>
            )}
          </div>
        </div>
      </header>

      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">{children}</div>

      <footer className="ui-footer-bar shrink-0">
        <div className="flex items-center gap-1.5">
          <span className="ui-status-dot ui-status-dot--ok" />
          All systems operational
        </div>
        <div className="hidden sm:block h-3 w-px bg-[var(--jewel-border)]" />
        <div className="hidden sm:flex items-center gap-1.5">
          <span className="ui-status-dot ui-status-dot--ok" />
          API: Healthy
        </div>
        {footerModel ? (
          <>
            <div className="hidden md:block h-3 w-px bg-[var(--jewel-border)]" />
            <div className="hidden md:block truncate">Model: {footerModel}</div>
          </>
        ) : null}
        <div className="hidden sm:block h-3 w-px bg-[var(--jewel-border)]" />
        <div>v4.2.0</div>
      </footer>
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
      aria-current={active ? "page" : undefined}
      className={`relative inline-flex h-full items-center gap-1.5 px-3 text-[13px] transition-colors ${
        active
          ? "ui-nav-active"
          : "text-[var(--jewel-ink-muted)] hover:text-[var(--jewel-ink)] font-medium"
      }`}
    >
      {children}
      {active ? <span className="ui-nav-facet" aria-hidden /> : null}
    </Link>
  );
}
