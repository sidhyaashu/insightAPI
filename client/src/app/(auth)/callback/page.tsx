"use client";

import { useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
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
      const provider = searchParams.get("provider") || sessionStorage.getItem("oauth_provider") || "google";

      if (!code) {
        router.replace("/login?error=missing_code");
        return;
      }

      try {
        const tokens = await authApi.exchangeOAuthCode(code, provider);
        if (tokens.user && tokens.access_token) {
          dispatch(setCredentials({ user: tokens.user, accessToken: tokens.access_token }));
          router.replace("/chat");
        } else {
          router.replace("/login?error=invalid_token");
        }
      } catch (err: any) {
        console.error("OAuth Exchange Error:", err);
        router.replace(`/login?error=${encodeURIComponent(err.message || "auth_failed")}`);
      }
    }

    processCallback();
  }, [searchParams, dispatch, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="text-center">
        <h3 className="text-lg font-semibold mb-2">Completing authentication...</h3>
        <p className="text-sm text-muted-foreground">Exchanging OAuth credentials with gateway</p>
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center bg-background">
        <p className="text-sm text-muted-foreground">Loading authentication...</p>
      </div>
    }>
      <CallbackContent />
    </Suspense>
  );
}
