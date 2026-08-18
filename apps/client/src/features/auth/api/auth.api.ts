import apiClient from "@/lib/api-client";
import type { ApiUser, AuthTokens } from "@/lib/api-client/types";

export const authApi = {
  /** Register a new user with Email & Password */
  register: async (data: { email: string; password: string; name?: string }): Promise<AuthTokens> => {
    const response = await apiClient.post<AuthTokens>("/auth/register", data);
    return response.data;
  },

  /** Login with Email & Password */
  login: async (data: { email: string; password: string }): Promise<AuthTokens> => {
    const response = await apiClient.post<AuthTokens>("/auth/login", data);
    return response.data;
  },

  /** Verify Email address using token */
  verifyEmail: async (token: string): Promise<{ message: string }> => {
    const response = await apiClient.get<{ message: string }>(`/auth/verify-email?token=${token}`);
    return response.data;
  },

  /** Resend email verification link */
  resendVerification: async (email: string): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>("/auth/resend-verification", { email });
    return response.data;
  },

  /** Request password reset email */
  forgotPassword: async (email: string): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>("/auth/forgot-password", { email });
    return response.data;
  },

  /** Reset password using token */
  resetPassword: async (token: string, newPassword: string): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>("/auth/reset-password", {
      token,
      new_password: newPassword,
    });
    return response.data;
  },

  /** Exchange OAuth callback code and CSRF state for tokens via BFF */
  exchangeOAuthCode: async (code: string, provider: string, state?: string | null): Promise<AuthTokens> => {
    const stateQuery = state ? `&state=${encodeURIComponent(state)}` : "";
    const response = await apiClient.get<AuthTokens>(
      `/auth/callback?code=${encodeURIComponent(code)}&provider=${encodeURIComponent(provider)}${stateQuery}`
    );
    return response.data;
  },

  /** Silent token refresh using HttpOnly cookie */
  refreshToken: async (): Promise<AuthTokens> => {
    const response = await apiClient.post<AuthTokens>("/auth/refresh");
    return response.data;
  },

  /** Fetch current user profile */
  getMe: async (): Promise<ApiUser> => {
    const response = await apiClient.get<ApiUser>("/users/me");
    return response.data;
  },

  /** Logout */
  logout: async (): Promise<void> => {
    await apiClient.post("/auth/logout");
  },
};
