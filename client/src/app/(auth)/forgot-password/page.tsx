"use client";

import { useState } from "react";
import Link from "next/link";
import {
  IconMail,
  IconArrowLeft,
  IconSparkles,
  IconCheck,
  IconAlertTriangle,
} from "@tabler/icons-react";
import { authApi } from "@/features/auth/api/auth.api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");
  const [errMsg, setErrMsg] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg("");
    setErrMsg("");
    setLoading(true);

    try {
      const res = await authApi.forgotPassword(email);
      setMsg(res.message);
    } catch (err: any) {
      setErrMsg(err.response?.data?.detail || err.message || "Failed to request password reset.");
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
          <h2 className="text-xl font-bold tracking-tight text-foreground">Reset Your Password</h2>
          <p className="text-xs text-muted-foreground">
            Enter your registered email address and we&apos;ll send you password reset instructions.
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
              <IconMail className="size-3.5 text-muted-foreground" /> Email Address
            </label>
            <input
              type="email"
              required
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3.5 py-2.5 border border-border/80 rounded-xl bg-muted/20 text-foreground text-xs focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition-colors font-mono"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-primary hover:bg-primary/90 text-primary-foreground font-semibold rounded-xl text-xs transition-all shadow-xs disabled:opacity-50 mt-1 cursor-pointer flex items-center justify-center gap-2"
          >
            {loading ? "Sending..." : "Send Password Reset Link"}
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
