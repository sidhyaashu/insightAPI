import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import type { ApiUser } from "@/lib/api-client/types";

interface AuthState {
  user: ApiUser | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const initialState: AuthState = {
  user: null,
  accessToken: null,
  isAuthenticated: false,
  isLoading: true,
};

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    setCredentials(state, action: PayloadAction<{ user: ApiUser; accessToken: string }>) {
      state.user = action.payload.user;
      state.accessToken = action.payload.accessToken;
      state.isAuthenticated = true;
      state.isLoading = false;
      // Also store token in window for axios interceptor (in-memory only)
      if (typeof window !== "undefined") {
        (window as any).__INSIGHTAPI_ACCESS_TOKEN__ = action.payload.accessToken;
      }
    },
    clearCredentials(state) {
      state.user = null;
      state.accessToken = null;
      state.isAuthenticated = false;
      state.isLoading = false;
      if (typeof window !== "undefined") {
        delete (window as any).__INSIGHTAPI_ACCESS_TOKEN__;
      }
    },
    setLoading(state, action: PayloadAction<boolean>) {
      state.isLoading = action.payload;
    },
  },
});

export const { setCredentials, clearCredentials, setLoading } = authSlice.actions;
export default authSlice.reducer;
