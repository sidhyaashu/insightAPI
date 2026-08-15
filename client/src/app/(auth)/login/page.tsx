"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  IconBrandGithub,
  IconBrandGoogle,
  IconEye,
  IconEyeOff,
  IconSparkles,
  IconLock,
  IconMail,
  IconUser,
  IconAlertTriangle,
  IconCheck,
  IconRefresh,
} from "@tabler/icons-react";
import { useAppDispatch, useAppSelector } from "@/store";
import { setCredentials } from "@/features/auth/store/authSlice";
import { authApi } from "@/features/auth/api/auth.api";
import env from "@/lib/env";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const dispatch = useAppDispatch();
  const { isAuthenticated, isLoading: isAuthLoading } = useAppSelector((state) => state.auth);

  useEffect(() => {
    if (!isAuthLoading && isAuthenticated) {
      router.replace("/chat");
    }
  }, [isAuthLoading, isAuthenticated, router]);

  // Check URL error params from OAuth redirect
  useEffect(() => {
    const errorParam = searchParams.get("error");
    if (errorParam) {
      setErrorMsg(decodeURIComponent(errorParam));
    }
  }, [searchParams]);

  const [tab, setTab] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [resendingEmail, setResendingEmail] = useState(false);

  const handleGithubLogin = () => {
    sessionStorage.setItem("oauth_provider", "github");
    window.location.href = `${env.API_BASE_URL}/auth/github/login`;
  };

  const handleGoogleLogin = () => {
    sessionStorage.setItem("oauth_provider", "google");
    window.location.href = `${env.API_BASE_URL}/auth/google/login`;
  };

  const handleResendVerification = async () => {
    if (!email) {
      setErrorMsg("Please enter your email address to resend verification.");
      return;
    }
    setResendingEmail(true);
    try {
      const res = await authApi.resendVerification(email);
      setSuccessMsg(res.message || "Verification email resent. Please check your inbox.");
      setErrorMsg("");
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || "Failed to resend verification email.");
    } finally {
      setResendingEmail(false);
    }
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
          router.push("/chat");
        }
      } else {
        const tokens = await authApi.register({ email, password, name });
        if (tokens.user && tokens.access_token) {
          dispatch(setCredentials({ user: tokens.user, accessToken: tokens.access_token }));
          setSuccessMsg("Account created successfully! Check your email for verification link.");
          setTimeout(() => router.push("/chat"), 1500);
        }
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || "Authentication failed";
      setErrorMsg(msg);
    } finally {
      setLoading(false);
    }
  };

  const isEmailNotVerified = errorMsg.toLowerCase().includes("not verified") || errorMsg.toLowerCase().includes("verify your email");

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4 font-sans select-none">
      <div className="w-full max-w-md border border-border/80 p-8 rounded-2xl shadow-xl bg-card text-card-foreground">
        {/* Brand Header */}
        <div className="text-center mb-6 space-y-1">
          <div className="inline-flex items-center justify-center size-11 rounded-2xl bg-primary/10 text-primary border border-primary/20 shadow-xs mb-2">
            <IconSparkles className="size-6" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground">{env.APP_NAME}</h2>
          <p className="text-xs text-muted-foreground">
            Agentic Web API Intelligence Platform &amp; Explorer
          </p>
        </div>

        {/* Login / Register Tab Switches */}
        <div className="flex border-b border-border/60 mb-6">
          <button
            type="button"
            onClick={() => { setTab("login"); setErrorMsg(""); setSuccessMsg(""); }}
            className={`flex-1 py-2.5 text-xs font-semibold text-center border-b-2 transition-all cursor-pointer ${
              tab === "login"
                ? "border-primary text-foreground font-bold"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => { setTab("register"); setErrorMsg(""); setSuccessMsg(""); }}
            className={`flex-1 py-2.5 text-xs font-semibold text-center border-b-2 transition-all cursor-pointer ${
              tab === "register"
                ? "border-primary text-foreground font-bold"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Create Account
          </button>
        </div>

        {/* Error Alert */}
        {errorMsg && (
          <div className="mb-4 p-3.5 bg-destructive/10 border border-destructive/30 text-destructive text-xs rounded-xl flex items-start gap-2.5 animate-in fade-in">
            <IconAlertTriangle className="size-4 shrink-0 mt-0.5" />
            <div className="space-y-1 flex-1">
              <span>{errorMsg}</span>
              {isEmailNotVerified && (
                <div>
                  <button
                    type="button"
                    onClick={handleResendVerification}
                    disabled={resendingEmail}
                    className="text-xs text-primary underline font-semibold hover:opacity-80 cursor-pointer inline-flex items-center gap-1 mt-1"
                  >
                    <IconRefresh className={`size-3 ${resendingEmail ? "animate-spin" : ""}`} />
                    {resendingEmail ? "Resending..." : "Resend verification email"}
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Success Alert */}
        {successMsg && (
          <div className="mb-4 p-3.5 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs rounded-xl flex items-center gap-2.5 animate-in fade-in">
            <IconCheck className="size-4 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {tab === "register" && (
            <div>
              <label className="block text-xs font-semibold text-foreground mb-1.5 flex items-center gap-1.5">
                <IconUser className="size-3.5 text-muted-foreground" /> Full Name
              </label>
              <input
                type="text"
                placeholder="e.g. Ashutosh Sidhya"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3.5 py-2.5 border border-border/80 rounded-xl bg-muted/20 text-foreground text-xs focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition-colors"
              />
            </div>
          )}

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

          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label className="block text-xs font-semibold text-foreground flex items-center gap-1.5">
                <IconLock className="size-3.5 text-muted-foreground" /> Password
              </label>
              {tab === "login" && (
                <Link
                  href="/forgot-password"
                  className="text-[11px] text-primary hover:underline font-medium cursor-pointer"
                >
                  Forgot Password?
                </Link>
              )}
            </div>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                required
                minLength={8}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
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
            disabled={loading}
            className="w-full py-2.5 bg-primary hover:bg-primary/90 text-primary-foreground font-semibold rounded-xl text-xs transition-all shadow-xs disabled:opacity-50 mt-1 cursor-pointer flex items-center justify-center gap-2"
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
            <div className="w-full border-t border-border/60" />
          </div>
          <span className="relative bg-card px-3 text-[11px] font-mono text-muted-foreground uppercase">
            OR CONTINUE WITH
          </span>
        </div>

        {/* OAuth Buttons */}
        <div className="flex flex-col gap-2.5">
          <button
            type="button"
            onClick={handleGithubLogin}
            className="w-full py-2.5 px-4 bg-muted/30 hover:bg-muted/80 text-foreground font-semibold text-xs rounded-xl border border-border/80 transition-all flex items-center justify-center gap-2.5 cursor-pointer shadow-xs"
          >
            <IconBrandGithub className="size-4" />
            <span>Continue with GitHub</span>
          </button>
          <button
            type="button"
            onClick={handleGoogleLogin}
            className="w-full py-2.5 px-4 bg-muted/30 hover:bg-muted/80 text-foreground font-semibold text-xs rounded-xl border border-border/80 transition-all flex items-center justify-center gap-2.5 cursor-pointer shadow-xs"
          >
            <IconBrandGoogle className="size-4 text-rose-500" />
            <span>Continue with Google</span>
          </button>
        </div>

        <p className="text-[11px] text-muted-foreground text-center mt-6 leading-relaxed">
          Special Admin Account: Sign in with <span className="font-mono text-foreground font-semibold">ashutoshsidhya69@gmail.com</span> for auto ADMIN access.
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-background">
          <p className="text-xs font-mono text-muted-foreground">Loading sign in form...</p>
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
