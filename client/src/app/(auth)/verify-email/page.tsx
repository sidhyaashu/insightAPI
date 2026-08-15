"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  IconCheck,
  IconAlertTriangle,
  IconSparkles,
  IconMail,
  IconRefresh,
  IconArrowRight,
  IconArrowLeft,
} from "@tabler/icons-react";
import { authApi } from "@/features/auth/api/auth.api";

function VerifyEmailForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token");

  const [status, setStatus] = useState<"verifying" | "success" | "error">("verifying");
  const [msg, setMsg] = useState("");
  const [resendEmail, setResendEmail] = useState("");
  const [resendLoading, setResendLoading] = useState(false);
  const [resendMsg, setResendMsg] = useState("");
  const [resendErrMsg, setResendErrMsg] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMsg("Missing verification token in URL.");
      return;
    }

    async function doVerify() {
      try {
        const res = await authApi.verifyEmail(token!);
        setStatus("success");
        setMsg(res.message || "Your email address has been confirmed successfully.");
      } catch (err: any) {
        setStatus("error");
        setMsg(err.response?.data?.detail || err.message || "Failed to verify email token. The link may have expired.");
      }
    }

    doVerify();
  }, [token]);

  const handleResend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resendEmail) return;
    setResendLoading(true);
    setResendMsg("");
    setResendErrMsg("");

    try {
      const res = await authApi.resendVerification(resendEmail);
      setResendMsg(res.message || "Verification email sent. Please check your inbox.");
    } catch (err: any) {
      setResendErrMsg(err.response?.data?.detail || "Failed to resend verification email.");
    } finally {
      setResendLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4 font-sans select-none">
      <div className="w-full max-w-md border border-border/80 p-8 rounded-2xl bg-card text-card-foreground text-center shadow-xl space-y-6">
        {status === "verifying" && (
          <div className="space-y-3 py-6">
            <div className="size-10 rounded-full border-2 border-primary border-t-transparent animate-spin mx-auto" />
            <h3 className="text-lg font-bold text-foreground">Verifying Your Email...</h3>
            <p className="text-xs text-muted-foreground">Please wait while we validate your token with the security gateway.</p>
          </div>
        )}

        {status === "success" && (
          <div className="space-y-4 py-2 animate-in fade-in">
            <div className="inline-flex items-center justify-center size-14 rounded-2xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 shadow-xs">
              <IconCheck className="size-8" />
            </div>
            <h3 className="text-xl font-bold tracking-tight text-foreground">Email Verified!</h3>
            <p className="text-xs text-muted-foreground leading-relaxed max-w-xs mx-auto">{msg}</p>
            <div className="pt-2">
              <Link
                href="/login"
                className="w-full py-2.5 bg-primary hover:bg-primary/90 text-primary-foreground font-semibold rounded-xl text-xs transition-all shadow-xs inline-flex items-center justify-center gap-2 cursor-pointer"
              >
                <span>Proceed to Sign In</span>
                <IconArrowRight className="size-4" />
              </Link>
            </div>
          </div>
        )}

        {status === "error" && (
          <div className="space-y-4 py-2 animate-in fade-in">
            <div className="inline-flex items-center justify-center size-14 rounded-2xl bg-destructive/10 text-destructive border border-destructive/30 shadow-xs">
              <IconAlertTriangle className="size-8" />
            </div>
            <h3 className="text-xl font-bold tracking-tight text-destructive">Verification Failed</h3>
            <p className="text-xs text-muted-foreground leading-relaxed max-w-xs mx-auto">{msg}</p>

            {/* Resend Verification Box */}
            <div className="border border-border/80 rounded-xl p-4 bg-muted/20 text-left space-y-3 mt-4">
              <div className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                <IconMail className="size-3.5 text-primary" />
                Resend Verification Link
              </div>

              {resendMsg && (
                <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs rounded-lg flex items-center gap-2">
                  <IconCheck className="size-3.5 shrink-0" />
                  <span>{resendMsg}</span>
                </div>
              )}

              {resendErrMsg && (
                <div className="p-2.5 bg-destructive/10 border border-destructive/30 text-destructive text-xs rounded-lg flex items-center gap-2">
                  <IconAlertTriangle className="size-3.5 shrink-0" />
                  <span>{resendErrMsg}</span>
                </div>
              )}

              <form onSubmit={handleResend} className="space-y-2.5">
                <input
                  type="email"
                  required
                  placeholder="Enter your email address"
                  value={resendEmail}
                  onChange={(e) => setResendEmail(e.target.value)}
                  className="w-full px-3 py-2 border border-border/80 rounded-lg bg-background text-foreground text-xs focus:outline-none focus:ring-2 focus:ring-primary/40 font-mono"
                />
                <button
                  type="submit"
                  disabled={resendLoading}
                  className="w-full py-2 bg-muted hover:bg-accent text-foreground font-semibold rounded-lg text-xs border border-border/80 transition-colors cursor-pointer flex items-center justify-center gap-1.5 disabled:opacity-50"
                >
                  <IconRefresh className={`size-3.5 ${resendLoading ? "animate-spin" : ""}`} />
                  <span>{resendLoading ? "Sending..." : "Resend Email"}</span>
                </button>
              </form>
            </div>

            <div className="pt-2">
              <Link
                href="/login"
                className="text-xs text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 transition-colors cursor-pointer font-medium"
              >
                <IconArrowLeft className="size-3.5" />
                <span>Back to Sign In</span>
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-background">
          <p className="text-xs font-mono text-muted-foreground">Loading email verification...</p>
        </div>
      }
    >
      <VerifyEmailForm />
    </Suspense>
  );
}
