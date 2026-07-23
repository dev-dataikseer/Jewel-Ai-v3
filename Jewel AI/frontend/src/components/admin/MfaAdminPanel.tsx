import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { KeyRound, Loader2, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";

type EnrollResponse = {
  secret: string;
  otpauth_url: string;
  backup_codes: string[];
};

export function MfaAdminPanel() {
  const queryClient = useQueryClient();
  const [enroll, setEnroll] = useState<EnrollResponse | null>(null);
  const [otp, setOtp] = useState("");
  const [confirmedCodes, setConfirmedCodes] = useState<string[] | null>(null);

  const enrollMutation = useMutation({
    mutationFn: async () => (await api.post<EnrollResponse>("/auth/mfa/enroll")).data,
    onSuccess: (data) => {
      setEnroll(data);
      setConfirmedCodes(null);
      toast.message("Scan the secret in your authenticator, then confirm with a code");
    },
    onError: (err: { friendlyMessage?: string }) =>
      toast.error(err.friendlyMessage || "Could not start MFA enroll"),
  });

  const confirmMutation = useMutation({
    mutationFn: async () =>
      (
        await api.post<{ ok: boolean; backup_codes: string[] }>("/auth/mfa/confirm", {
          otp,
          backup_codes: enroll?.backup_codes || [],
        })
      ).data,
    onSuccess: (data) => {
      setConfirmedCodes(data.backup_codes || enroll?.backup_codes || []);
      void queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
      toast.success("MFA enabled — store backup codes offline");
    },
    onError: (err: { friendlyMessage?: string }) =>
      toast.error(err.friendlyMessage || "Invalid code"),
  });

  return (
    <div className="ui-card p-5 space-y-4">
      <div className="flex items-center gap-2">
        <ShieldCheck className="size-4 text-[var(--jewel-accent)]" />
        <h3 className="text-sm font-semibold text-jewel-ink">Admin MFA (TOTP)</h3>
      </div>
      <p className="text-xs text-jewel-ink-muted leading-relaxed">
        Optional for admin accounts. Save backup codes if you enable it; break-glass recovery is
        documented in ops docs.
      </p>
      {!enroll && (
        <button
          type="button"
          className="ui-btn-primary"
          disabled={enrollMutation.isPending}
          onClick={() => enrollMutation.mutate()}
        >
          {enrollMutation.isPending ? (
            <Loader2 className="size-3.5 animate-spin" />
          ) : (
            <KeyRound className="size-3.5" />
          )}
          Enroll authenticator
        </button>
      )}
      {enroll && !confirmedCodes && (
        <div className="space-y-3">
          <p className="text-[11px] font-mono break-all bg-jewel-muted rounded-lg p-2">
            Secret: {enroll.secret}
          </p>
          <p className="text-[11px] text-jewel-ink-muted break-all">URI: {enroll.otpauth_url}</p>
          <ul className="text-[11px] font-mono grid grid-cols-2 gap-1">
            {enroll.backup_codes.map((c) => (
              <li key={c} className="rounded bg-slate-50 px-2 py-1">
                {c}
              </li>
            ))}
          </ul>
          <input
            className="ui-input"
            value={otp}
            onChange={(e) => setOtp(e.target.value)}
            placeholder="Confirm with 6-digit code"
          />
          <button
            type="button"
            className="ui-btn-primary"
            disabled={confirmMutation.isPending || otp.length < 6}
            onClick={() => confirmMutation.mutate()}
          >
            {confirmMutation.isPending ? <Loader2 className="size-3.5 animate-spin" /> : null}
            Confirm & enable MFA
          </button>
        </div>
      )}
      {confirmedCodes && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-900">
          MFA is on. Keep these backup codes safe:
          <ul className="mt-2 font-mono grid grid-cols-2 gap-1">
            {confirmedCodes.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
