import apiClient from "@/lib/api-client";
import type {
  AuthProfile,
  CreateAuthProfileInput,
  UpdateAuthProfileInput,
  TestAuthProfileResult,
} from "@/lib/api-client/types";

export const authProfilesApi = {
  listProfiles: async (domain?: string, projectId?: string): Promise<AuthProfile[]> => {
    const params = new URLSearchParams();
    if (domain) params.append("domain", domain);
    if (projectId) params.append("project_id", projectId);
    const queryString = params.toString() ? `?${params.toString()}` : "";
    const { data } = await apiClient.get<AuthProfile[]>(`/v1/auth-profiles${queryString}`);
    return data;
  },

  getProfile: async (id: string): Promise<AuthProfile> => {
    const { data } = await apiClient.get<AuthProfile>(`/v1/auth-profiles/${id}`);
    return data;
  },

  createProfile: async (input: CreateAuthProfileInput): Promise<AuthProfile> => {
    const { data } = await apiClient.post<AuthProfile>("/v1/auth-profiles", input);
    return data;
  },

  updateProfile: async (id: string, input: UpdateAuthProfileInput): Promise<AuthProfile> => {
    const { data } = await apiClient.patch<AuthProfile>(`/v1/auth-profiles/${id}`, input);
    return data;
  },

  deleteProfile: async (id: string): Promise<{ message: string }> => {
    const { data } = await apiClient.delete<{ message: string }>(`/v1/auth-profiles/${id}`);
    return data;
  },

  testProfile: async (id: string): Promise<TestAuthProfileResult> => {
    const { data } = await apiClient.post<TestAuthProfileResult>(`/v1/auth-profiles/${id}/test`);
    return data;
  },

  testTransient: async (input: {
    login_url: string;
    auth_type: string;
    credentials: Record<string, string>;
  }): Promise<TestAuthProfileResult> => {
    const { data } = await apiClient.post<TestAuthProfileResult>("/v1/auth-profiles/test-transient", input);
    return data;
  },
};
