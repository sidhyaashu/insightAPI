"use client";

import { useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  IconLock,
  IconEye,
  IconEyeOff,
  IconArrowLeft,
  IconSparkles,
  IconCheck,
  IconAlertTriangle,
} from "@tabler/icons-react";
import { authApi } from "@/features/auth/api/auth.api";

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token");

  const [newPassword, setNewPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");
  const [errMsg, setErrMsg] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) {
      setErrMsg("Missing or invalid password reset token.");
      return;
    }
    setMsg("");
    setErrMsg("");
    setLoading(true);

    try {
      const res = await authApi.resetPassword(token, newPassword);
      setMsg(res.message || "Password updated successfully. Redirecting to login...");
      setTimeout(() => router.push("/login"), 2000);
    } catch (err: any) {
      setErrMsg(err.response?.data?.detail || err.message || "Failed to reset password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4 font-sans select-none">
      <div className="w-full max-w-md border border-border/80 p-8 rounded-2xl shadow-xl bg-card text-card-foreground space-y-6">
        {/* Header */}
        <div className="text-center space-y-1">
          <div className="inline-flex items-center justify-center size-11 rounded-2xl bg-primary/10 text-primary border border-primary/20 shadow-xs mb-2">
            <IconSparkles className="size-6" />
          </div>
          <h2 className="text-xl font-bold tracking-tight text-foreground">Set New Password</h2>
          <p className="text-xs text-muted-foreground">
            Enter your new secure password below to complete the reset.
          </p>
        </div>

        {msg && (
          <div className="p-3.5 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs rounded-xl flex items-center gap-2.5 animate-in fade-in">
            <IconCheck className="size-4 shrink-0" />
            <span>{msg}</span>
          </div>
        )}

        {errMsg && (
          <div className="p-3.5 bg-destructive/10 border border-destructive/30 text-destructive text-xs rounded-xl flex items-start gap-2.5 animate-in fade-in">
            <IconAlertTriangle className="size-4 shrink-0 mt-0.5" />
            <span>{errMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-xs font-semibold text-foreground mb-1.5 flex items-center gap-1.5">
              <IconLock className="size-3.5 text-muted-foreground" /> New Password
            </label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                required
                minLength={8}
                placeholder="••••••••"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 pr-10 border border-border/80 rounded-xl bg-muted/20 text-foreground text-xs focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition-colors font-mono"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground cursor-pointer transition-colors p-1"
                title={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <IconEyeOff className="size-4" /> : <IconEye className="size-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || !token}
            className="w-full py-2.5 bg-primary hover:bg-primary/90 text-primary-foreground font-semibold rounded-xl text-xs transition-all shadow-xs disabled:opacity-50 mt-1 cursor-pointer flex items-center justify-center gap-2"
          >
            {loading ? "Updating Password..." : "Reset Password"}
          </button>
        </form>

        <div className="text-center pt-2">
          <Link
            href="/login"
            className="text-xs text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 transition-colors cursor-pointer font-medium"
          >
            <IconArrowLeft className="size-3.5" />
            <span>Back to Sign In</span>
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-background">
          <p className="text-xs font-mono text-muted-foreground">Loading password reset form...</p>
        </div>
      }
    >
      <ResetPasswordForm />
    </Suspense>
  );
}
