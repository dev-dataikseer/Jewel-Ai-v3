import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import axios from "axios";
import { useAuth } from "@/hooks/useAuth";
import { BrandMark } from "@/components/ui/BrandMark";
import { FacetMark } from "@/components/ui/FacetMark";

export function LoginPage() {
  const { login, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [backupCode, setBackupCode] = useState("");
  const [mfaRequired, setMfaRequired] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  if (!isLoading && isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await login({
        email,
        password,
        otp: otp || undefined,
        backup_code: backupCode || undefined,
      });
      toast.success("Signed in");
      navigate("/");
    } catch (err: unknown) {
      const ax = axios.isAxiosError(err) ? err : null;
      const detail = String(ax?.response?.data?.detail || "");
      const mfa =
        detail.toLowerCase().includes("mfa") ||
        ax?.response?.headers?.["x-mfa-required"] === "1";
      if (ax?.response?.status === 401 && mfa) {
        setMfaRequired(true);
        toast.message("Enter your authenticator code or a backup code");
      } else {
        const message =
          (err as { friendlyMessage?: string })?.friendlyMessage || "Invalid credentials";
        toast.error(message);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 bg-[var(--jewel-bg)]">
      <div className="w-full max-w-md">
        <div className="flex flex-col items-center mb-10 text-center">
          <div
            className="mb-5 grid place-items-center rounded-2xl p-1"
            style={{
              boxShadow: "0 0 0 8px color-mix(in srgb, var(--jewel-accent) 12%, transparent), 0 12px 40px color-mix(in srgb, var(--jewel-accent) 18%, transparent)",
            }}
          >
            <BrandMark size={56} className="rounded-2xl" />
          </div>
          <h1 className="text-3xl font-semibold text-jewel-ink tracking-tight leading-none">
            Jewel AI Studio
          </h1>
          <p className="mt-3 text-sm text-jewel-ink-muted leading-relaxed max-w-sm">
            Sign in to access the generation workspace
          </p>
        </div>

        <form onSubmit={onSubmit} className="ui-card ui-facet-cut p-7 space-y-5" style={{ boxShadow: "var(--jewel-shadow-card)" }}>
          <div className="space-y-2">
            <label htmlFor="login-email" className="ui-label mb-0">
              Email
            </label>
            <input
              id="login-email"
              type="email"
              required
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="ui-input h-11"
              placeholder="admin@jewelai.com"
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="login-password" className="ui-label mb-0">
              Password
            </label>
            <input
              id="login-password"
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="ui-input h-11"
            />
          </div>
          {mfaRequired && (
            <>
              <div className="space-y-2">
                <label htmlFor="login-otp" className="ui-label mb-0">
                  Authenticator code
                </label>
                <input
                  id="login-otp"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                  className="ui-input h-11 font-mono-data"
                  placeholder="6-digit code"
                />
              </div>
              <div className="space-y-2">
                <label htmlFor="login-backup" className="ui-label mb-0">
                  Or backup code
                </label>
                <input
                  id="login-backup"
                  type="text"
                  value={backupCode}
                  onChange={(e) => setBackupCode(e.target.value)}
                  className="ui-input h-11 font-mono-data"
                  placeholder="One-time backup code"
                />
              </div>
            </>
          )}
          <button
            type="submit"
            disabled={submitting}
            aria-busy={submitting}
            className="ui-btn-primary w-full mt-1 h-11 transition-transform hover:-translate-y-px hover:shadow-md"
          >
            {submitting ? <FacetMark variant="spin" size={16} className="text-white" /> : null}
            {submitting ? "Signing in…" : mfaRequired ? "Verify & sign in" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
