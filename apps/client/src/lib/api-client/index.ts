/**
 * Centralized Axios API client.
 * ALL API calls in the application go through this single instance.
 * Base URL reads from typed env accessor (NEXT_PUBLIC_API_BASE_URL).
 */
import axios, { type AxiosInstance, type InternalAxiosRequestConfig, type AxiosResponse, type AxiosError } from "axios";
import env from "@/lib/env";

const apiClient: AxiosInstance = axios.create({
  baseURL: env.API_BASE_URL,  // e.g. http://localhost/api
  withCredentials: true,       // sends HttpOnly refresh token cookie to BFF /api/auth/refresh
  timeout: 30_000,
  headers: {
    "Content-Type": "application/json",
  },
});

// ── Request Interceptor: attach access token from Redux store ─────────────────
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Access token lives only in memory (Redux store) — never localStorage
    if (typeof window !== "undefined") {
      const token = (window as any).__INSIGHTAPI_ACCESS_TOKEN__;
      if (token && config.headers) {
        config.headers["Authorization"] = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response Interceptor: auto-refresh on 401 ─────────────────────────────────
let isRefreshing = false;
let pendingRequests: Array<(token: string) => void> = [];

const onTokenRefreshed = (token: string) => {
  pendingRequests.forEach((cb) => cb(token));
  pendingRequests = [];
};

apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && !original._retry && !original.url?.includes("/auth/refresh")) {
      original._retry = true;

      if (!isRefreshing) {
        isRefreshing = true;
        try {
          // BFF /api/auth/refresh uses the HttpOnly refresh token cookie automatically
          const { data } = await axios.post(`${env.API_BASE_URL}/auth/refresh`, {}, { withCredentials: true });
          const newToken = data.access_token;
          (window as any).__INSIGHTAPI_ACCESS_TOKEN__ = newToken;
          onTokenRefreshed(newToken);
        } catch {
          pendingRequests = [];
          // Refresh failed — redirect to login
          if (typeof window !== "undefined") {
            window.location.href = "/login";
          }
          return Promise.reject(error);
        } finally {
          isRefreshing = false;
        }
      }

      // Queue requests while refresh is in progress
      return new Promise((resolve) => {
        pendingRequests.push((token) => {
          if (original.headers) original.headers["Authorization"] = `Bearer ${token}`;
          resolve(apiClient(original));
        });
      });
    }

    return Promise.reject(error);
  }
);

export default apiClient;
