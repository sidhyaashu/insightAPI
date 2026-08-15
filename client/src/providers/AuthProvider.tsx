"use client";

import React, { useEffect } from "react";
import { useAppDispatch } from "@/store";
import { setCredentials, clearCredentials, setLoading } from "@/features/auth/store/authSlice";
import { authApi } from "@/features/auth/api/auth.api";

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const dispatch = useAppDispatch();

  useEffect(() => {
    async function restoreSession() {
      try {
        dispatch(setLoading(true));
        // Try refreshing access token using HttpOnly refresh cookie via BFF
        const tokenRes = await authApi.refreshToken();
        if (tokenRes?.access_token) {
          (window as any).__INSIGHTAPI_ACCESS_TOKEN__ = tokenRes.access_token;
          let user = tokenRes.user;
          if (!user) {
            try {
              user = await authApi.getMe();
            } catch {
              // fallback if getMe throws
            }
          }
          if (user) {
            const adminEmails = ["ashutoshsidhya69@gmail.com", "sidhyaasutosh@gmail.com"];
            if (user.email && adminEmails.includes(user.email.toLowerCase())) {
              user = { ...user, tier: "ADMIN", role: "admin", is_verified: true };
            }
            dispatch(setCredentials({ user, accessToken: tokenRes.access_token }));
          } else {
            dispatch(clearCredentials());
          }
        } else {
          dispatch(clearCredentials());
        }
      } catch {
        dispatch(clearCredentials());
      } finally {
        dispatch(setLoading(false));
      }
    }

    restoreSession();
  }, [dispatch]);

  return <>{children}</>;
}
