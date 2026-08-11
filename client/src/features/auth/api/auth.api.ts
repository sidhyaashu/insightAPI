import apiClient from "@/lib/api-client";
import type { ApiUser, AuthTokens } from "@/lib/api-client/types";
import {
  mockAuthTokens,
  getMockUser,
  saveMockUser,
  clearMockUser,
} from "@/lib/api-client/mockFallback";

export const authApi = {
  /** Register a new user with Email & Password */
  register: async (data: { email: string; password: string; name?: string }): Promise<AuthTokens> => {
    try {
      const response = await apiClient.post<AuthTokens>("/auth/register", data);
      return response.data;
    } catch (err: any) {
      if (!err.response || err.code === "ERR_NETWORK" || err.message?.includes("Network Error")) {
        console.warn("[Mock Fallback] Backend offline — registering with mock credentials.");
        const tokens = mockAuthTokens(data.email);
        if (data.name && tokens.user) tokens.user.name = data.name;
        saveMockUser(tokens.user!);
        return tokens;
      }
      throw err;
    }
  },

  /** Login with Email & Password */
  login: async (data: { email: string; password: string }): Promise<AuthTokens> => {
    try {
      const response = await apiClient.post<AuthTokens>("/auth/login", data);
      return response.data;
    } catch (err: any) {
      if (!err.response || err.code === "ERR_NETWORK" || err.message?.includes("Network Error")) {
        console.warn("[Mock Fallback] Backend offline — logging in with mock credentials.");
        const tokens = mockAuthTokens(data.email);
        saveMockUser(tokens.user!);
        return tokens;
      }
      throw err;
    }
  },

  /** Verify Email address using token */
  verifyEmail: async (token: string): Promise<{ message: string }> => {
    try {
      const response = await apiClient.get<{ message: string }>(`/auth/verify-email?token=${token}`);
      return response.data;
    } catch (err: any) {
      if (!err.response || err.code === "ERR_NETWORK") {
        return { message: "Mock Fallback: Email verified successfully." };
      }
      throw err;
    }
  },

  /** Resend email verification link */
  resendVerification: async (email: string): Promise<{ message: string }> => {
    try {
      const response = await apiClient.post<{ message: string }>("/auth/resend-verification", { email });
      return response.data;
    } catch (err: any) {
      if (!err.response || err.code === "ERR_NETWORK") {
        return { message: "Mock Fallback: Verification email resent." };
      }
      throw err;
    }
  },

  /** Request password reset email */
  forgotPassword: async (email: string): Promise<{ message: string }> => {
    try {
      const response = await apiClient.post<{ message: string }>("/auth/forgot-password", { email });
      return response.data;
    } catch (err: any) {
      if (!err.response || err.code === "ERR_NETWORK") {
        return { message: "Mock Fallback: Password reset link sent." };
      }
      throw err;
    }
  },

  /** Reset password using token */
  resetPassword: async (token: string, newPassword: string): Promise<{ message: string }> => {
    try {
      const response = await apiClient.post<{ message: string }>("/auth/reset-password", {
        token,
        new_password: newPassword,
      });
      return response.data;
    } catch (err: any) {
      if (!err.response || err.code === "ERR_NETWORK") {
        return { message: "Mock Fallback: Password updated successfully." };
      }
      throw err;
    }
  },

  /** Exchange OAuth callback code for tokens via BFF */
  exchangeOAuthCode: async (code: string, provider: string): Promise<AuthTokens> => {
    try {
      const response = await apiClient.get<AuthTokens>(
        `/auth/callback?code=${code}&provider=${provider}`
      );
      return response.data;
    } catch (err: any) {
      if (!err.response || err.code === "ERR_NETWORK") {
        return mockAuthTokens("sidhyaasutosh@gmail.com");
      }
      throw err;
    }
  },

  /** Silent token refresh using HttpOnly cookie */
  refreshToken: async (): Promise<{ access_token: string }> => {
    try {
      const response = await apiClient.post<{ access_token: string }>("/auth/refresh");
      return response.data;
    } catch (err: any) {
      if (!err.response || err.code === "ERR_NETWORK" || err.message?.includes("Network Error")) {
        const user = getMockUser();
        return { access_token: `mock-access-token-${user.tier.toLowerCase()}` };
      }
      throw err;
    }
  },

  /** Fetch current user profile */
  getMe: async (): Promise<ApiUser> => {
    try {
      const response = await apiClient.get<ApiUser>("/users/me");
      return response.data;
    } catch (err: any) {
      if (!err.response || err.code === "ERR_NETWORK" || err.message?.includes("Network Error")) {
        return getMockUser();
      }
      throw err;
    }
  },

  /** Logout */
  logout: async (): Promise<void> => {
    try {
      await apiClient.post("/auth/logout");
    } catch {
    } finally {
      clearMockUser();
    }
  },
};
