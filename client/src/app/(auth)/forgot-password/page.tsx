"use client";

import { useState } from "react";
import Link from "next/link";
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
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-md border border-border p-8 rounded-xl bg-card shadow-sm">
        <h2 className="text-xl font-bold text-center mb-1">Reset Your Password</h2>
        <p className="text-xs text-muted-foreground text-center mb-6">
          Enter your registered email address and we'll send you password reset instructions.
        </p>

        {msg && (
          <div className="mb-4 p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 text-xs rounded-lg text-center">
            {msg}
          </div>
        )}

        {errMsg && (
          <div className="mb-4 p-3 bg-destructive/10 border border-destructive/20 text-destructive text-xs rounded-lg text-center">
            {errMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-xs font-medium mb-1">Email Address</label>
            <input
              type="email"
              required
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-primary text-primary-foreground font-medium rounded-lg text-sm hover:opacity-90 disabled:opacity-50"
          >
            {loading ? "Sending..." : "Send Password Reset Link"}
          </button>
        </form>

        <div className="text-center mt-6">
          <Link href="/login" className="text-xs text-muted-foreground hover:text-foreground underline">
            &larr; Back to Login
          </Link>
        </div>
      </div>
    </div>
  );
}
