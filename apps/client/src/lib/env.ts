/**
 * Typed accessor for ALL client-side environment variables.
 * This is the single source of truth for env in the client.
 * Dynamically resolves origin to prevent cross-origin/mixed-content network errors.
 */

const getApiBaseUrl = (): string => {
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL;
  }
  if (typeof window !== "undefined") {
    return `${window.location.origin}/api`;
  }
  return "http://localhost/api";
};

const getWsBaseUrl = (): string => {
  if (process.env.NEXT_PUBLIC_WS_BASE_URL) {
    return process.env.NEXT_PUBLIC_WS_BASE_URL;
  }
  if (typeof window !== "undefined") {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}/ws`;
  }
  return "ws://localhost/ws";
};

const env = {
  APP_NAME: process.env.NEXT_PUBLIC_APP_NAME ?? "InsightAPI AI",
  APP_URL: process.env.NEXT_PUBLIC_APP_URL ?? (typeof window !== "undefined" ? window.location.origin : "http://localhost"),
  get API_BASE_URL() {
    return getApiBaseUrl();
  },
  get WS_BASE_URL() {
    return getWsBaseUrl();
  },
  STRIPE_PUBLISHABLE_KEY: process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY ?? "",
  GOOGLE_CLIENT_ID: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? "1745111960-p3i6c3oirjlnma3gtl9rucgcr8h59tll.apps.googleusercontent.com",
  GITHUB_CLIENT_ID: process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID ?? "Ov23li85oG43DxTtgPiW",
  APP_ENV: process.env.NEXT_PUBLIC_APP_ENV ?? "development",
  IS_PROD: process.env.NEXT_PUBLIC_APP_ENV === "production",
};

export type Env = typeof env;
export default env;
