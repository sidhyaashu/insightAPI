"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { authApi } from "@/features/auth/api/auth.api";

function VerifyEmailForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token");

  const [status, setStatus] = useState<"verifying" | "success" | "error">("verifying");
  const [msg, setMsg] = useState("");

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
        setMsg(res.message);
      } catch (err: any) {
        setStatus("error");
        setMsg(err.response?.data?.detail || err.message || "Failed to verify email token.");
      }
    }

    doVerify();
  }, [token]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-md border border-border p-8 rounded-xl bg-card text-center shadow-sm">
        {status === "verifying" && (
          <div>
            <h3 className="text-lg font-semibold mb-2">Verifying Your Email...</h3>
            <p className="text-sm text-muted-foreground">Please wait while we confirm your token.</p>
          </div>
        )}

        {status === "success" && (
          <div>
            <div className="text-4xl mb-3">✅</div>
            <h3 className="text-xl font-bold mb-2 text-foreground">Email Verified!</h3>
            <p className="text-sm text-muted-foreground mb-6">{msg}</p>
            <Link href="/login" className="bg-primary text-primary-foreground text-sm font-medium px-6 py-2.5 rounded-lg inline-block">
              Proceed to Sign In &rarr;
            </Link>
          </div>
        )}

        {status === "error" && (
          <div>
            <div className="text-4xl mb-3">⚠️</div>
            <h3 className="text-xl font-bold mb-2 text-destructive">Verification Failed</h3>
            <p className="text-sm text-muted-foreground mb-6">{msg}</p>
            <Link href="/login" className="border border-input text-foreground text-sm font-medium px-6 py-2.5 rounded-lg inline-block hover:bg-accent">
              Back to Login
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center bg-background">
        <p className="text-sm text-muted-foreground">Loading...</p>
      </div>
    }>
      <VerifyEmailForm />
    </Suspense>
  );
}
