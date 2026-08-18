import apiClient from "@/lib/api-client";
import type { DriftReport, DriftWebhookResponse } from "@/lib/api-client/types";

export interface WebhookPayload {
  compare_crawl_id: string;
  webhook_url: string;
  base_crawl_id?: string;
}

export const driftApi = {
  /**
   * Fetch a structured drift report comparing two crawl snapshots.
   * ``base`` is optional — omit to auto-detect the most recent prior crawl.
   */
  getDriftReport: async (
    projectId: string,
    compareCrawlId: string,
    baseCrawlId?: string
  ): Promise<DriftReport> => {
    const params = new URLSearchParams({ compare: compareCrawlId });
    if (baseCrawlId) params.set("base", baseCrawlId);
    const { data } = await apiClient.get<DriftReport>(
      `/v1/projects/${projectId}/drift?${params.toString()}`
    );
    return data;
  },

  /**
   * Trigger an outbound webhook if the drift report contains breaking changes.
   * Requires PRO tier or above.
   */
  triggerWebhook: async (
    projectId: string,
    payload: WebhookPayload
  ): Promise<DriftWebhookResponse> => {
    const { data } = await apiClient.post<DriftWebhookResponse>(
      `/v1/projects/${projectId}/drift/webhook`,
      payload
    );
    return data;
  },
};
