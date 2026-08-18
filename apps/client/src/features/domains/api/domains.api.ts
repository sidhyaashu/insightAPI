import apiClient from "@/lib/api-client";
import type { VerifiedDomain } from "@/lib/api-client/types";

export interface CheckDomainResponse {
  verified: boolean;
  domain: string;
  verification_method?: string;
  message?: string;
  detail?: string;
  domain_record?: VerifiedDomain;
}

export interface DomainStatusResponse {
  domain: string;
  is_verified: boolean;
}

export const domainsApi = {
  listDomains: async (): Promise<VerifiedDomain[]> => {
    const { data } = await apiClient.get<VerifiedDomain[]>("/v1/domains");
    return data;
  },

  verifyDomain: async (domain: string): Promise<VerifiedDomain> => {
    const { data } = await apiClient.post<VerifiedDomain>("/v1/domains/verify", { domain });
    return data;
  },

  checkVerification: async (domain: string, method: string = "auto"): Promise<CheckDomainResponse> => {
    const { data } = await apiClient.post<CheckDomainResponse>(`/v1/domains/${encodeURIComponent(domain)}/check`, {
      method,
    });
    return data;
  },

  checkStatus: async (domain: string): Promise<DomainStatusResponse> => {
    const { data } = await apiClient.get<DomainStatusResponse>(
      `/v1/domains/status?domain=${encodeURIComponent(domain)}`
    );
    return data;
  },

  deleteDomain: async (domain: string): Promise<{ message: string }> => {
    const { data } = await apiClient.delete<{ message: string }>(`/v1/domains/${encodeURIComponent(domain)}`);
    return data;
  },

  setActiveTestingOptIn: async (domain: string, optIn: boolean): Promise<{ domain: string; active_testing_opt_in: boolean }> => {
    const { data } = await apiClient.post<{ domain: string; active_testing_opt_in: boolean }>(
      `/v1/domains/${encodeURIComponent(domain)}/active-testing?opt_in=${optIn}`
    );
    return data;
  },
};

