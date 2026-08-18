"use client";

import { useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { IconSparkles } from "@tabler/icons-react";
import { useAppDispatch } from "@/store";
import { setCredentials } from "@/features/auth/store/authSlice";
import { authApi } from "@/features/auth/api/auth.api";

function CallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const dispatch = useAppDispatch();

  useEffect(() => {
    async function processCallback() {
      const code = searchParams.get("code");
      const state = searchParams.get("state");
      const provider = searchParams.get("provider") || sessionStorage.getItem("oauth_provider") || "google";

      if (!code) {
        router.replace("/login?error=missing_code");
        return;
      }

      try {
        const tokens = await authApi.exchangeOAuthCode(code, provider, state);
        if (tokens.user && tokens.access_token) {
          dispatch(setCredentials({ user: tokens.user, accessToken: tokens.access_token }));
          router.replace("/chat");
        } else {
          router.replace("/login?error=invalid_token");
        }
      } catch (err: any) {
        console.error("OAuth Exchange Error:", err);
        router.replace(`/login?error=${encodeURIComponent(err.response?.data?.detail || err.message || "auth_failed")}`);
      }
    }

    processCallback();
  }, [searchParams, dispatch, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4 font-sans select-none">
      <div className="w-full max-w-sm border border-border/80 p-8 rounded-2xl shadow-xl bg-card text-center space-y-4">
        <div className="size-10 rounded-full border-2 border-primary border-t-transparent animate-spin mx-auto" />
        <div className="space-y-1">
          <h3 className="text-base font-bold text-foreground">Completing Authentication...</h3>
          <p className="text-xs text-muted-foreground">Exchanging OAuth credentials with security gateway.</p>
        </div>
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-background">
          <p className="text-xs font-mono text-muted-foreground">Loading authentication session...</p>
        </div>
      }
    >
      <CallbackContent />
    </Suspense>
  );
}
