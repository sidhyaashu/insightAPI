import apiClient from "@/lib/api-client";
import type { CrawlSession, CrawlReport } from "@/lib/api-client/types";

export const crawlsApi = {
  startCrawl: async (params: {
    target_url: string;
    max_pages?: number;
    goal?: string;
    require_review?: boolean;
    tos_accepted?: boolean;
    auth_profile_id?: string;
  }): Promise<CrawlSession> => {
    const { data } = await apiClient.post<CrawlSession>("/v1/crawls/start", params);
    return data;
  },

  listCrawls: async (limit = 20, offset = 0): Promise<CrawlSession[]> => {
    const { data } = await apiClient.get<CrawlSession[]>(`/v1/crawls?limit=${limit}&offset=${offset}`);
    return data;
  },

  getCrawlById: async (sessionId: string): Promise<CrawlSession> => {
    const { data } = await apiClient.get<CrawlSession>(`/v1/crawls/${sessionId}`);
    return data;
  },

  deleteCrawl: async (sessionId: string): Promise<void> => {
    await apiClient.delete(`/v1/crawls/${sessionId}`);
  },

  getReport: async (sessionId: string): Promise<CrawlReport> => {
    const { data } = await apiClient.get<CrawlReport>(`/v1/reports/${sessionId}`);
    return data;
  },

  generateTests: async (sessionId: string, format: "python" | "typescript" = "python"): Promise<string> => {
    const { data } = await apiClient.get<string>(`/v1/crawls/${sessionId}/generate-tests?format=${format}`, {
      responseType: "text" as const,
    });
    return data;
  },

  downloadTestSuiteZip: async (sessionId: string, format: "python" | "typescript" = "python"): Promise<Blob> => {
    const { data } = await apiClient.get<Blob>(
      `/v1/crawls/${sessionId}/generate-tests?format=${format}&as_zip=true`,
      { responseType: "blob" as const }
    );
    return data;
  },
};

