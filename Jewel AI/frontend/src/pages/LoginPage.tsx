import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Gem, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/hooks/useAuth";

export function LoginPage() {
  const { login, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (!isLoading && isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await login({ email, password });
      toast.success("Signed in");
      navigate("/");
    } catch (err: unknown) {
      const message =
        (err as { friendlyMessage?: string })?.friendlyMessage || "Invalid credentials";
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 bg-slate-50">
      <div className="w-full max-w-md">
        <div className="flex flex-col items-center mb-8 text-center">
          <div className="grid size-12 place-items-center rounded-2xl bg-blue-600 text-white shadow-sm shadow-blue-600/25 mb-4">
            <Gem className="size-6" />
          </div>
          <h1 className="text-2xl font-semibold text-slate-900 tracking-tight">
            Jewel AI Studio
          </h1>
          <p className="text-sm text-slate-500 mt-1.5 leading-relaxed">
            Sign in to access the generation workspace
          </p>
        </div>

        <form onSubmit={onSubmit} className="ui-card p-6 space-y-4 shadow-soft">
          <div>
            <label htmlFor="login-email" className="ui-label">
              Email
            </label>
            <input
              id="login-email"
              type="email"
              required
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="ui-input"
              placeholder="admin@jewelai.com"
            />
          </div>
          <div>
            <label htmlFor="login-password" className="ui-label">
              Password
            </label>
            <input
              id="login-password"
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="ui-input"
            />
          </div>
          <button type="submit" disabled={submitting} className="ui-btn-primary w-full mt-2">
            {submitting ? <Loader2 className="size-4 animate-spin" /> : null}
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
