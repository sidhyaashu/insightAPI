/**
 * Shared API response types used across all features.
 * Import these instead of defining local interfaces in feature files.
 */

export interface ApiUser {
  id: string;
  email: string;
  name: string | null;
  avatar_url: string | null;
  tier: "FREE" | "PAYG" | "STARTER" | "PRO" | "ENTERPRISE" | "ADMIN";
  role?: "user" | "admin";
  is_verified?: boolean;
  oauth_provider?: string;
  allow_overage?: boolean;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  token_type: string;
  user?: ApiUser;
}

export interface CrawlSession {
  id?: string;
  session_id: string;
  user_id: string;
  target_url: string;
  status: "running" | "pending_review" | "completed" | "failed";
  max_pages: number;
  goal: string | null;
  captured_count: number;
  action_traces?: any[];
  error_message: string | null;
  openapi_spec?: Record<string, unknown> | null;
  postman_collection?: Record<string, unknown> | null;
  markdown_docs?: string | null;
  cost_usd?: number;
  total_tokens?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  created_at: string;
  updated_at: string;
}

export interface CrawlReport {
  session_id: string;
  openapi_spec: Record<string, unknown> | null;
  postman_collection: Record<string, unknown> | null;
  markdown_docs: string | null;
  action_traces?: any[];
}

export interface Subscription {
  tier: ApiUser["tier"];
  status: "active" | "canceled" | "past_due" | "free";
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  subscription: unknown | null;
}

export interface ToolCallEvent {
  tool_id: string;
  tool: string;
  title?: string;
  input?: Record<string, unknown>;
  status: "running" | "completed" | "failed";
  latency_ms?: number;
  output?: Record<string, unknown>;
  error?: string | null;
}

export interface ApprovalEvent {
  approval_id: string;
  action: {
    method: string;
    url: string;
    description: string;
  };
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  tool_calls?: ToolCallEvent[];
  approvals?: ApprovalEvent[];
  created_at: string;
}

export interface ChatSession {
  id: string;
  user_id: string;
  title: string;
  is_archived: boolean;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface SessionWithMessages {
  session: ChatSession;
  messages: ChatMessage[];
}

export type WsEvent =
  | { type: "connected"; session_id: string }
  | { type: "log"; message: string; page?: number; endpoints_found?: number }
  | { type: "pending_review"; captured_count: number }
  | { type: "complete"; captured_count: number }
  | { type: "error"; message: string }
  | { type: "token"; content: string }
  | { type: "done"; session_id: string };

export interface DomainInstructions {
  dns: {
    record_type: string;
    host: string;
    value: string;
    description: string;
  };
  well_known: {
    file_path: string;
    target_url: string;
    content: string;
    description: string;
  };
}

export interface VerifiedDomain {
  id: string;
  domain: string;
  verification_token: string;
  verification_method: "dns_txt" | "well_known" | null;
  is_verified: boolean;
  active_testing_opt_in?: boolean;
  verified_at: string | null;
  created_at: string;
  instructions: DomainInstructions;
}

export type AuthType = "form" | "oauth_google" | "oauth_github" | "saml";

export interface AuthProfile {
  id: string;
  user_id: string;
  project_id: string;
  name: string;
  target_domain: string;
  login_url: string;
  auth_type: AuthType;
  credentials: Record<string, string>;
  last_tested_at: string | null;
  last_test_status: "success" | "failed" | null;
  last_test_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateAuthProfileInput {
  name: string;
  target_domain?: string;
  login_url: string;
  auth_type: AuthType;
  credentials: Record<string, string>;
  project_id?: string;
}

export interface UpdateAuthProfileInput {
  name?: string;
  target_domain?: string;
  login_url?: string;
  auth_type?: AuthType;
  credentials?: Record<string, string>;
  project_id?: string;
}

export interface TestAuthProfileResult {
  success: boolean;
  status: "success" | "failed";
  profile_id?: string;
  error?: string | null;
  diagnostics?: {
    cookies_count?: number;
    sample_cookie_names?: string[];
    origins_count?: number;
  };
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
}

export interface ApiError {
  detail: string;
  status?: number;
}

// ── Drift Detection Types ─────────────────────────────────────────────────────

export interface EndpointDiff {
  endpoint_key: string;
  method: string;
  path: string;
  status_code: number;
}

export interface BreakingChange {
  endpoint_key: string;
  change_type:
    | "endpoint_removed"
    | "type_changed"
    | "required_field_removed"
    | "required_field_added"
    | "auth_added"
    | string;
  field_path: string | null;
  old_value: unknown;
  new_value: unknown;
  description: string;
}

export interface NonBreakingChange {
  endpoint_key: string;
  change_type:
    | "endpoint_added"
    | "optional_field_added"
    | "optional_field_removed"
    | "field_made_optional"
    | "description_changed"
    | "auth_removed"
    | string;
  field_path: string | null;
  old_value: unknown;
  new_value: unknown;
  description: string;
}

export interface DriftSummary {
  added_count: number;
  removed_count: number;
  breaking_count: number;
  non_breaking_count: number;
  total_endpoints_base: number;
  total_endpoints_compare: number;
}

export interface DriftReport {
  base_crawl_id: string;
  compare_crawl_id: string;
  generated_at: string;
  summary: DriftSummary;
  added_endpoints: EndpointDiff[];
  removed_endpoints: EndpointDiff[];
  breaking_changes: BreakingChange[];
  non_breaking_changes: NonBreakingChange[];
  has_breaking_changes: boolean;
}

export interface DriftWebhookResponse {
  fired: boolean;
  breaking_change_count: number;
  compare_crawl_id: string;
  base_crawl_id: string;
  has_breaking_changes: boolean;
}

// ── Review & Approval Gate Types ─────────────────────────────────────────────

export interface EndpointReviewItem {
  endpoint_key: string;
  method: string;
  path: string;
  template_route?: string;
  status_code: number;
  schema_json: Record<string, unknown> | null;
  confidence: number;
  example_count: number;
  is_excluded: boolean;
  reviewed_schema?: Record<string, unknown> | null;
  has_review: boolean;
}

export interface ReviewPatchBody {
  schema?: Record<string, unknown>;
  is_excluded?: boolean;
}

export interface ApproveBody {
  confidence_threshold?: number;
}

export interface ApproveResponse {
  session_id: string;
  captured_count: number;
  excluded_count: number;
  has_excluded: boolean;
}

