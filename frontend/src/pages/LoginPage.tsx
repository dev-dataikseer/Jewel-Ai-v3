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
    <div className="min-h-screen flex flex-col items-center justify-center px-4 bg-gradient-to-b from-slate-50 to-blue-50/30">
      <div className="w-full max-w-md">
        <div className="flex flex-col items-center mb-8">
          <div className="grid size-12 place-items-center rounded-2xl bg-blue-600 text-white shadow-lg shadow-blue-500/20 mb-4">
            <Gem className="size-6" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900">Jewel AI Studio</h1>
          <p className="text-sm text-slate-500 mt-1">Sign in to access the generation workspace</p>
        </div>

        <form
          onSubmit={onSubmit}
          className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-4"
        >
          <div>
            <label className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-slate-500">
              Email
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="h-11 w-full rounded-lg border border-slate-200 px-3 text-sm outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="admin@jewel.ai"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-slate-500">
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="h-11 w-full rounded-lg border border-slate-200 px-3 text-sm outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="h-11 w-full rounded-xl bg-blue-600 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60 flex items-center justify-center gap-2"
          >
            {submitting && <Loader2 className="size-4 animate-spin" />}
            Sign In
          </button>
        </form>

      </div>
    </div>
  );
}
