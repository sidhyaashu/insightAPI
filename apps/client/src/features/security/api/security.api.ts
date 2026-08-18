import apiClient from "@/lib/api-client";

export interface SecurityApprovalItem {
  id: string;
  pattern_id: string;
  crawl_id: string;
  user_id: string;
  endpoint_route: string;
  method: string;
  target_domain?: string;
  test_strategy_snapshot: Record<string, any>;
  status: "pending" | "approved" | "rejected" | "executed";
  requested_at: string;
  reviewed_at?: string;
  reasoning_trace?: string;
  pattern_meta?: {
    vuln_class: string;
    occurrences: number;
    distinct_target_count: number;
    confidence: number;
    status: string;
    is_destructive: boolean;
  };
}

export interface SecurityFindingItem {
  id: string;
  crawl_id: string;
  user_id: string;
  pattern_id: string;
  endpoint_signature: string;
  endpoint_route: string;
  method: string;
  vuln_class: string;
  severity: "critical" | "high" | "medium" | "low";
  evidence: Record<string, any>;
  ran_via_cache: boolean;
  created_at: string;
}

export interface SecurityTestPatternItem {
  id: string;
  endpoint_signature: string;
  vuln_class: string;
  test_strategy: Record<string, any>;
  is_destructive: boolean;
  outcome: string;
  confidence: number;
  occurrences: number;
  distinct_target_count: number;
  seen_domains: string[];
  reasoning_trace?: string;
  status: "needs_review" | "learned";
  last_human_reviewed_at?: string;
  created_at: string;
}

export const securityApi = {
  listPendingApprovals: async (): Promise<{ pending_approvals: SecurityApprovalItem[]; total: number }> => {
    const { data } = await apiClient.get<{ pending_approvals: SecurityApprovalItem[]; total: number }>(
      "/v1/security-patterns/pending-review"
    );
    return data;
  },

  approveRun: async (approvalId: string): Promise<any> => {
    const { data } = await apiClient.post<any>(
      `/v1/security-patterns/${approvalId}/approve-run`
    );
    return data;
  },

  rejectApproval: async (approvalId: string): Promise<any> => {
    const { data } = await apiClient.post<any>(
      `/v1/security-patterns/${approvalId}/reject`
    );
    return data;
  },

  listFindings: async (crawlId?: string): Promise<{ findings: SecurityFindingItem[]; total: number }> => {
    const params = crawlId ? `?crawl_id=${encodeURIComponent(crawlId)}` : "";
    const { data } = await apiClient.get<{ findings: SecurityFindingItem[]; total: number }>(
      `/v1/security-patterns/findings${params}`
    );
    return data;
  },

  listPatterns: async (status?: string): Promise<{ patterns: SecurityTestPatternItem[]; total: number }> => {
    const params = status ? `?status=${encodeURIComponent(status)}` : "";
    const { data } = await apiClient.get<{ patterns: SecurityTestPatternItem[]; total: number }>(
      `/v1/security-patterns/patterns${params}`
    );
    return data;
  },
};
