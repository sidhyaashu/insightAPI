import apiClient from "@/lib/api-client";

export interface AuditLogItem {
  id: string;
  user_id: string;
  project_id?: string;
  action: string;
  target_id?: string;
  ip_address?: string;
  metadata?: Record<string, any>;
  created_at: string;
}

export interface AuditLogsResponse {
  audit_logs: AuditLogItem[];
  total: number;
  limit: number;
  offset: number;
}

export const auditApi = {
  getAuditLogs: async (params?: {
    limit?: number;
    offset?: number;
    action?: string;
    target_id?: string;
  }): Promise<AuditLogsResponse> => {
    const query = new URLSearchParams();
    if (params?.limit) query.set("limit", params.limit.toString());
    if (params?.offset) query.set("offset", params.offset.toString());
    if (params?.action) query.set("action", params.action);
    if (params?.target_id) query.set("target_id", params.target_id);

    const { data } = await apiClient.get<AuditLogsResponse>(
      `/v1/audit-logs?${query.toString()}`
    );
    return data;
  },
};
