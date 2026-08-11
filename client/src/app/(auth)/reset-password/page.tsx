"use client";

import { useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { authApi } from "@/features/auth/api/auth.api";

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token");

  const [newPassword, setNewPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");
  const [errMsg, setErrMsg] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) {
      setErrMsg("Missing reset token.");
      return;
    }
    setMsg("");
    setErrMsg("");
    setLoading(true);

    try {
      const res = await authApi.resetPassword(token, newPassword);
      setMsg(res.message);
      setTimeout(() => router.push("/login"), 2000);
    } catch (err: any) {
      setErrMsg(err.response?.data?.detail || err.message || "Failed to reset password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-md border border-border p-8 rounded-xl bg-card shadow-sm">
        <h2 className="text-xl font-bold text-center mb-1">Set New Password</h2>
        <p className="text-xs text-muted-foreground text-center mb-6">
          Enter your new password below.
        </p>

        {msg && (
          <div className="mb-4 p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 text-xs rounded-lg text-center">
            {msg} Redirecting to login...
          </div>
        )}

        {errMsg && (
          <div className="mb-4 p-3 bg-destructive/10 border border-destructive/20 text-destructive text-xs rounded-lg text-center">
            {errMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-xs font-medium mb-1">New Password</label>
            <input
              type="password"
              required
              minLength={8}
              placeholder="••••••••"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <button
            type="submit"
            disabled={loading || !token}
            className="w-full py-2.5 bg-primary text-primary-foreground font-medium rounded-lg text-sm hover:opacity-90 disabled:opacity-50"
          >
            {loading ? "Updating Password..." : "Reset Password"}
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

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center bg-background">
        <p className="text-sm text-muted-foreground">Loading...</p>
      </div>
    }>
      <ResetPasswordForm />
    </Suspense>
  );
}
