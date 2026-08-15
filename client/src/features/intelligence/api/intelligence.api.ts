import apiClient from "@/lib/api-client";

export interface CostsSummaryResponse {
  total_spend_usd: number;
  total_tokens: number;
  total_cached_calls: number;
  cache_hit_rate_pct: number;
  total_calls: number;
  active_budget?: {
    max_budget_usd: number;
    hard_limit_usd: number;
    current_spend_usd: number;
  };
}

export interface CostBreakdownItem {
  node_name: string;
  model: string;
  total_calls: number;
  total_tokens: number;
  total_cost_usd: number;
  cached_calls: number;
}

export const intelligenceApi = {
  getCostsSummary: async (): Promise<CostsSummaryResponse> => {
    const { data } = await apiClient.get<CostsSummaryResponse>("/v1/costs/summary");
    return data;
  },

  getCostBreakdown: async (): Promise<{ breakdown: CostBreakdownItem[] }> => {
    const { data } = await apiClient.get<{ breakdown: CostBreakdownItem[] }>("/v1/costs/breakdown");
    return data;
  },

  getCrawlCost: async (crawlId: string): Promise<any> => {
    const { data } = await apiClient.get<any>(`/v1/costs/crawls/${crawlId}`);
    return data;
  },
};
