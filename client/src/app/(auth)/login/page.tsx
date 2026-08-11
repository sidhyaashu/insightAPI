"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAppDispatch } from "@/store";
import { setCredentials } from "@/features/auth/store/authSlice";
import { authApi } from "@/features/auth/api/auth.api";
import env from "@/lib/env";

export default function LoginPage() {
  const router = useRouter();
  const dispatch = useAppDispatch();

  const [tab, setTab] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const handleGithubLogin = () => {
    window.location.href = `${env.API_BASE_URL}/auth/github/login`;
  };

  const handleGoogleLogin = () => {
    window.location.href = `${env.API_BASE_URL}/auth/google/login`;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");
    setSuccessMsg("");
    setLoading(true);

    try {
      if (tab === "login") {
        const tokens = await authApi.login({ email, password });
        if (tokens.user && tokens.access_token) {
          dispatch(setCredentials({ user: tokens.user, accessToken: tokens.access_token }));
          router.push("/dashboard");
        }
      } else {
        const tokens = await authApi.register({ email, password, name });
        if (tokens.user && tokens.access_token) {
          dispatch(setCredentials({ user: tokens.user, accessToken: tokens.access_token }));
          setSuccessMsg("Account created successfully! Check your email for verification link.");
          setTimeout(() => router.push("/dashboard"), 1500);
        }
      }
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || err.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-md border border-border p-8 rounded-xl shadow-sm bg-card text-card-foreground">
        <h2 className="text-2xl font-bold text-center mb-1">{env.APP_NAME}</h2>
        <p className="text-xs text-muted-foreground text-center mb-6">
          Agentic Web API Intelligence Platform
        </p>

        {/* Login / Register Tab Switches */}
        <div className="flex border-b border-border mb-6">
          <button
            onClick={() => { setTab("login"); setErrorMsg(""); }}
            className={`flex-1 py-2 text-sm font-medium text-center border-b-2 transition ${
              tab === "login"
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Sign In
          </button>
          <button
            onClick={() => { setTab("register"); setErrorMsg(""); }}
            className={`flex-1 py-2 text-sm font-medium text-center border-b-2 transition ${
              tab === "register"
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Create Account
          </button>
        </div>

        {errorMsg && (
          <div className="mb-4 p-3 bg-destructive/10 border border-destructive/20 text-destructive text-xs rounded-lg">
            {errorMsg}
          </div>
        )}

        {successMsg && (
          <div className="mb-4 p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 text-xs rounded-lg">
            {successMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {tab === "register" && (
            <div>
              <label className="block text-xs font-medium mb-1">Full Name</label>
              <input
                type="text"
                placeholder="e.g. Ashutosh Sidhya"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          )}

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

          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="block text-xs font-medium">Password</label>
              {tab === "login" && (
                <Link href="/forgot-password" className="text-xs text-primary hover:underline">
                  Forgot Password?
                </Link>
              )}
            </div>
            <input
              type="password"
              required
              minLength={8}
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-primary text-primary-foreground font-medium rounded-lg text-sm hover:opacity-90 transition disabled:opacity-50 mt-2"
          >
            {loading
              ? "Authenticating..."
              : tab === "login"
              ? "Sign In with Email"
              : "Create Account"}
          </button>
        </form>

        <div className="relative my-6 text-center">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-border" />
          </div>
          <span className="relative bg-card px-2 text-xs text-muted-foreground">OR CONTINUE WITH</span>
        </div>

        {/* OAuth Buttons */}
        <div className="flex flex-col gap-2">
          <button
            onClick={handleGithubLogin}
            className="w-full py-2.5 px-4 bg-muted hover:bg-accent text-foreground font-medium text-xs rounded-lg border transition flex items-center justify-center gap-2"
          >
            Continue with GitHub
          </button>
          <button
            onClick={handleGoogleLogin}
            className="w-full py-2.5 px-4 bg-muted hover:bg-accent text-foreground font-medium text-xs rounded-lg border transition flex items-center justify-center gap-2"
          >
            Continue with Google
          </button>
        </div>

        <p className="text-[11px] text-muted-foreground text-center mt-6">
          Special Admin Account: Login with <span className="font-mono text-foreground">sidhyaasutosh@gmail.com</span> for auto ADMIN access.
        </p>
      </div>
    </div>
  );
}
