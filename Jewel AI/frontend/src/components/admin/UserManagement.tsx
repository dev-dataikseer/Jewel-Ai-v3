import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { UserCog, UserPlus } from "lucide-react";
import { FacetMark } from "@/components/ui/FacetMark";
import { api } from "@/lib/api";
import type { User } from "@/types";
import { useAuth } from "@/hooks/useAuth";

type UserRow = User & { is_active?: boolean; created_at?: string };

export function UserManagement() {
  const queryClient = useQueryClient();
  const { user: me, refetch: refetchMe } = useAuth();
  const [createForm, setCreateForm] = useState({ email: "", password: "", name: "" });
  const [accountForm, setAccountForm] = useState({
    email: me?.email || "",
    name: me?.name || "",
    currentPassword: "",
    newPassword: "",
  });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editPassword, setEditPassword] = useState("");
  const [creditDraft, setCreditDraft] = useState<Record<string, string>>({});

  const { data: users = [], isLoading } = useQuery({
    queryKey: ["admin", "users"],
    queryFn: async () => {
      const res = await api.get<{ items: UserRow[] } | UserRow[]>("/users", { params: { limit: 100 } });
      const data = res.data;
      return Array.isArray(data) ? data : data.items || [];
    },
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["admin", "users"] });

  const creditMutation = useMutation({
    mutationFn: async ({ id, amount }: { id: string; amount: number }) => {
      await api.post(`/users/${id}/credits`, { amount });
    },
    onSuccess: () => {
      invalidate();
      toast.success("Credits added");
    },
    onError: (err: { friendlyMessage?: string }) =>
      toast.error(err.friendlyMessage || "Credit top-up failed"),
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      await api.post("/users", {
        email: createForm.email.trim(),
        password: createForm.password,
        name: createForm.name.trim() || undefined,
        role: "user",
      });
    },
    onSuccess: () => {
      setCreateForm({ email: "", password: "", name: "" });
      invalidate();
      toast.success("User created");
    },
    onError: (err: { friendlyMessage?: string }) => toast.error(err.friendlyMessage || "Failed to create user"),
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, body }: { id: string; body: Record<string, unknown> }) => {
      await api.patch(`/users/${id}`, body);
    },
    onSuccess: () => {
      setEditingId(null);
      setEditPassword("");
      invalidate();
      toast.success("User updated");
    },
    onError: (err: { friendlyMessage?: string }) => toast.error(err.friendlyMessage || "Update failed"),
  });

  const accountMutation = useMutation({
    mutationFn: async () => {
      await api.patch("/users/me", {
        email: accountForm.email.trim() || undefined,
        name: accountForm.name.trim() || undefined,
        current_password: accountForm.currentPassword || undefined,
        password: accountForm.newPassword || undefined,
      });
    },
    onSuccess: async () => {
      setAccountForm((f) => ({ ...f, currentPassword: "", newPassword: "" }));
      await refetchMe();
      toast.success("Account updated");
    },
    onError: (err: { friendlyMessage?: string }) => toast.error(err.friendlyMessage || "Account update failed"),
  });

  const onCreate = (e: FormEvent) => {
    e.preventDefault();
    if (createForm.password.length < 6) {
      toast.error("Password must be at least 6 characters");
      return;
    }
    createMutation.mutate();
  };

  const onAccount = (e: FormEvent) => {
    e.preventDefault();
    if (accountForm.newPassword && accountForm.newPassword.length < 6) {
      toast.error("New password must be at least 6 characters");
      return;
    }
    if (accountForm.newPassword && !accountForm.currentPassword) {
      toast.error("Enter your current password to set a new one");
      return;
    }
    accountMutation.mutate();
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      <div className="ui-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <UserCog className="size-4 text-blue-600" />
          <h2 className="text-sm font-semibold text-slate-800">My account</h2>
        </div>
        <form onSubmit={onAccount} className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl">
          <input
            type="email"
            placeholder="Email"
            value={accountForm.email}
            onChange={(e) => setAccountForm({ ...accountForm, email: e.target.value })}
            className="h-10 rounded-lg border border-slate-200 px-3 text-sm"
          />
          <input
            placeholder="Display name"
            value={accountForm.name}
            onChange={(e) => setAccountForm({ ...accountForm, name: e.target.value })}
            className="h-10 rounded-lg border border-slate-200 px-3 text-sm"
          />
          <input
            type="password"
            placeholder="Current password (required to change password)"
            value={accountForm.currentPassword}
            onChange={(e) => setAccountForm({ ...accountForm, currentPassword: e.target.value })}
            className="h-10 rounded-lg border border-slate-200 px-3 text-sm md:col-span-2"
          />
          <input
            type="password"
            placeholder="New password (optional)"
            value={accountForm.newPassword}
            onChange={(e) => setAccountForm({ ...accountForm, newPassword: e.target.value })}
            className="h-10 rounded-lg border border-slate-200 px-3 text-sm md:col-span-2"
          />
          <button
            type="submit"
            disabled={accountMutation.isPending}
            className="h-10 rounded-lg bg-[var(--jewel-accent)] text-xs font-bold text-white md:col-span-2 flex items-center justify-center gap-2"
          >
            {accountMutation.isPending && <FacetMark variant="spin" size={14} className="text-white" />}
            Save My Account
          </button>
        </form>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[340px_1fr] gap-6">
        <form onSubmit={onCreate} className="ui-card p-6 space-y-3 h-fit">
          <div className="flex items-center gap-2 mb-1">
            <UserPlus className="size-4 text-blue-600" />
            <h2 className="text-sm font-semibold text-slate-800">Create user</h2>
          </div>
          <input
            type="email"
            required
            placeholder="Email"
            value={createForm.email}
            onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-200 px-3 text-sm"
          />
          <input
            placeholder="Name (optional)"
            value={createForm.name}
            onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-200 px-3 text-sm"
          />
          <input
            type="password"
            required
            minLength={6}
            placeholder="Password (min 6 chars)"
            value={createForm.password}
            onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })}
            className="h-10 w-full rounded-lg border border-slate-200 px-3 text-sm"
          />
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="h-10 w-full rounded-lg bg-[var(--jewel-accent)] text-xs font-bold text-white flex items-center justify-center gap-2"
          >
            {createMutation.isPending && <FacetMark variant="spin" size={14} className="text-white" />}
            Add Studio User
          </button>
        </form>

        <div className="ui-card p-6">
          <h2 className="text-sm font-semibold text-slate-800 mb-4">All users</h2>
          {isLoading ? (
            <p className="text-sm text-slate-500">Loading…</p>
          ) : (
            <div className="space-y-2 max-h-[520px] overflow-y-auto">
              {users.map((u) => (
                <div
                  key={u.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-100 bg-slate-50/50 p-3"
                >
                  <div>
                    <p className="font-semibold text-sm text-slate-800">{u.email}</p>
                    <p className="text-[11px] text-slate-500">
                      {u.name || "—"} · {u.role}
                      {typeof u.credits === "number" ? ` · ${u.credits} credits` : ""}
                      {u.id === me?.id ? " (you)" : ""}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 min-w-[18rem] justify-end">
                    <input
                      type="number"
                      min={1}
                      placeholder="+credits"
                      value={creditDraft[u.id] || ""}
                      onChange={(e) =>
                        setCreditDraft((d) => ({ ...d, [u.id]: e.target.value }))
                      }
                      className="h-8 w-24 rounded-lg border border-slate-200 px-2 text-xs font-mono-data"
                    />
                    <button
                      type="button"
                      className="h-8 px-2 rounded-lg ui-btn-secondary text-[11px] font-semibold"
                      disabled={creditMutation.isPending}
                      onClick={() => {
                        const amount = Number(creditDraft[u.id] || 0);
                        if (!amount || amount < 1) {
                          toast.error("Enter a positive credit amount");
                          return;
                        }
                        creditMutation.mutate({ id: u.id, amount });
                        setCreditDraft((d) => ({ ...d, [u.id]: "" }));
                      }}
                    >
                      Top up
                    </button>
                    {editingId === u.id ? (
                      <input
                        type="password"
                        placeholder="New password"
                        value={editPassword}
                        onChange={(e) => setEditPassword(e.target.value)}
                        className="h-8 w-36 rounded-lg border border-slate-200 px-2 text-xs"
                      />
                    ) : null}
                    <button
                      type="button"
                      disabled={editingId === u.id ? updateMutation.isPending : false}
                      onClick={() => {
                        if (editingId === u.id) {
                          updateMutation.mutate({
                            id: u.id,
                            body: editPassword ? { password: editPassword } : {},
                          });
                        } else {
                          setEditingId(u.id);
                        }
                      }}
                      className="h-8 px-2 rounded-lg border border-slate-200 text-[11px] font-semibold"
                    >
                      {editingId === u.id ? "Save" : "Reset password"}
                    </button>
                    <button
                      type="button"
                      disabled={editingId !== u.id}
                      onClick={() => {
                        setEditingId(null);
                        setEditPassword("");
                      }}
                      className="h-8 px-2 rounded-lg border border-slate-200 text-[11px] disabled:opacity-40"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      disabled={u.id === me?.id || u.role === "admin"}
                      onClick={() => updateMutation.mutate({ id: u.id, body: { is_active: false } })}
                      className="h-8 px-2 rounded-lg border border-rose-200 text-[11px] font-semibold text-rose-600 disabled:opacity-40"
                      title={
                        u.id === me?.id
                          ? "Cannot deactivate yourself"
                          : u.role === "admin"
                            ? "Cannot deactivate admins here"
                            : undefined
                      }
                    >
                      Deactivate
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
