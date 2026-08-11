import apiClient from "@/lib/api-client";
import type { CrawlSession, CrawlReport } from "@/lib/api-client/types";
import { mockCrawlSessions, mockCrawlReport } from "@/lib/api-client/mockFallback";

export const crawlsApi = {
  startCrawl: async (params: { target_url: string; max_pages?: number; goal?: string }): Promise<CrawlSession> => {
    try {
      const { data } = await apiClient.post<CrawlSession>("/v1/crawls/start", params);
      return data;
    } catch (err: any) {
      if (!err.response || err.code === "ERR_NETWORK" || err.message?.includes("Network Error")) {
        console.warn("[Mock Fallback] Crawl engine offline — creating mock crawl session.");
        const mockNew: CrawlSession = {
          session_id: `mock-session-${Date.now()}`,
          user_id: "admin-uuid-sidhyaasutosh",
          target_url: params.target_url,
          status: "running",
          max_pages: params.max_pages || 10,
          goal: params.goal || null,
          captured_count: 0,
          error_message: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        mockCrawlSessions.unshift(mockNew);
        return mockNew;
      }
      throw err;
    }
  },

  listCrawls: async (limit = 20): Promise<CrawlSession[]> => {
    try {
      const { data } = await apiClient.get<CrawlSession[]>(`/v1/crawls?limit=${limit}`);
      return data;
    } catch (err: any) {
      if (!err.response || err.code === "ERR_NETWORK" || err.message?.includes("Network Error")) {
        return mockCrawlSessions.slice(0, limit);
      }
      throw err;
    }
  },

  getCrawlById: async (sessionId: string): Promise<CrawlSession> => {
    try {
      const { data } = await apiClient.get<CrawlSession>(`/v1/crawls/${sessionId}`);
      return data;
    } catch (err: any) {
      if (!err.response || err.code === "ERR_NETWORK" || err.message?.includes("Network Error")) {
        const found = mockCrawlSessions.find((s) => s.session_id === sessionId);
        return found || mockCrawlSessions[0];
      }
      throw err;
    }
  },

  getReport: async (sessionId: string): Promise<CrawlReport> => {
    try {
      const { data } = await apiClient.get<CrawlReport>(`/v1/reports/${sessionId}`);
      return data;
    } catch (err: any) {
      if (!err.response || err.code === "ERR_NETWORK" || err.message?.includes("Network Error")) {
        return mockCrawlReport(sessionId);
      }
      throw err;
    }
  },
};
