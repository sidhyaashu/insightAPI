import apiClient from "@/lib/api-client";
import type {
  EndpointReviewItem,
  ReviewPatchBody,
  ApproveBody,
  ApproveResponse,
} from "@/lib/api-client/types";

export const reviewApi = {
  /**
   * List all captured endpoints for review, sorted by confidence ascending.
   */
  listEndpoints: async (crawlId: string): Promise<EndpointReviewItem[]> => {
    const { data } = await apiClient.get<EndpointReviewItem[]>(
      `/v1/crawls/${crawlId}/endpoints`
    );
    return data;
  },

  /**
   * Patch a single endpoint's reviewed schema or exclusion flag.
   */
  patchEndpoint: async (
    crawlId: string,
    endpointKey: string,
    body: ReviewPatchBody
  ): Promise<EndpointReviewItem> => {
    const { data } = await apiClient.patch<EndpointReviewItem>(
      `/v1/crawls/${crawlId}/endpoints/${encodeURIComponent(endpointKey)}`,
      body
    );
    return data;
  },

  /**
   * Approve the reviewed crawl, running exporters and transitioning to completed.
   */
  approveCrawl: async (
    crawlId: string,
    body: ApproveBody = {}
  ): Promise<ApproveResponse> => {
    const { data } = await apiClient.post<ApproveResponse>(
      `/v1/crawls/${crawlId}/approve`,
      body
    );
    return data;
  },
};
