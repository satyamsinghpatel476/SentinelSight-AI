export type HealthResponse = {
  status: string;
  service?: string;
  environment?: string;
};

export type UserRole = "administrator" | "security_analyst" | "viewer";

export type User = {
  id: string;
  organization_id: string;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AuthResponse = {
  user: User;
};

export type WebsiteRiskCategory = "low" | "moderate" | "high" | "critical";

export type WebsiteAsset = {
  id: string;
  organization_id: string;
  name: string;
  url: string;
  normalized_url: string;
  authorization_confirmed: boolean;
  monitoring_enabled: boolean;
  risk_category: WebsiteRiskCategory;
  contact_email: string;
  current_baseline_id: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type WebsiteAssetInput = {
  name: string;
  url: string;
  contact_email: string;
  risk_category: WebsiteRiskCategory;
  monitoring_enabled: boolean;
  authorization_confirmed: boolean;
};

export type ScanStatus = "queued" | "running" | "completed" | "failed";
export type ScanType = "baseline" | "comparison";
export type FindingSeverity = "low" | "moderate" | "high" | "critical";
export type RiskLevel = "low" | "moderate" | "high" | "critical";
export type IncidentStatus = "open" | "investigating" | "resolved" | "false_positive";
export type AIProvider = "gemini" | "openai" | "openai_compatible";
export type AIAnalysisStatus = "pending" | "completed" | "failed";

export type RiskBreakdownItem = {
  reason: string;
  points: number;
  evidence: string;
};

export type Scan = {
  id: string;
  organization_id: string;
  website_asset_id: string;
  requested_by: string;
  scan_type: ScanType;
  status: ScanStatus;
  requested_url: string;
  final_url: string | null;
  http_status: number | null;
  response_time_ms: number | null;
  page_title: string | null;
  visible_text_hash: string | null;
  html_hash: string | null;
  response_headers: Record<string, unknown> | null;
  external_script_domains: string[] | null;
  external_iframe_domains: string[] | null;
  redirect_chain: Array<Record<string, unknown>> | null;
  failure_reason: string | null;
  screenshot_filename: string | null;
  screenshot_content_type: string | null;
  screenshot_width: number | null;
  screenshot_height: number | null;
  screenshot_perceptual_hash: string | null;
  baseline_scan_id: string | null;
  title_changed: boolean | null;
  baseline_title: string | null;
  current_title: string | null;
  text_similarity_percent: number | null;
  visual_change_percent: number | null;
  visual_change_level: string | null;
  perceptual_hash_distance: number | null;
  difference_image_filename: string | null;
  difference_image_content_type: string | null;
  comparison_error: string | null;
  baseline_external_script_domains: string[] | null;
  current_external_script_domains: string[] | null;
  new_external_script_domains: string[] | null;
  baseline_external_iframe_domains: string[] | null;
  current_external_iframe_domains: string[] | null;
  new_external_iframe_domains: string[] | null;
  suspicious_phrases: string[] | null;
  risk_score: number | null;
  risk_level: RiskLevel | null;
  risk_breakdown: RiskBreakdownItem[] | null;
  started_at: string | null;
  completed_at: string | null;
  scanned_at: string | null;
  created_at: string;
  updated_at: string;
};

export type Finding = {
  id: string;
  organization_id: string;
  website_asset_id: string;
  scan_id: string;
  type: string;
  title: string;
  description: string;
  severity: FindingSeverity;
  evidence: string;
  remediation: string;
  risk_points: number;
  created_at: string;
};

export type Baseline = {
  id: string;
  organization_id: string;
  website_asset_id: string;
  scan_id: string;
  approved_by: string;
  approved_at: string;
  is_active: boolean;
  created_at: string;
  scan: Scan;
};

export type IncidentNote = {
  id: string;
  organization_id: string;
  incident_id: string;
  user_id: string;
  content: string;
  created_at: string;
};

export type Incident = {
  id: string;
  organization_id: string;
  website_asset_id: string;
  scan_id: string;
  title: string;
  description: string;
  severity: FindingSeverity;
  risk_score: number;
  risk_breakdown: RiskBreakdownItem[] | null;
  status: IncidentStatus;
  assigned_to: string | null;
  resolution_notes: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  website_asset: WebsiteAsset | null;
  scan: Scan | null;
  notes: IncidentNote[];
  findings: Finding[];
};

export type IncidentUpdate = {
  status?: IncidentStatus;
  resolution_notes?: string | null;
  assigned_to?: string | null;
};

export type AuditLog = {
  id: string;
  organization_id: string;
  user_id: string;
  user_name: string | null;
  user_email: string | null;
  action: string;
  resource_type: string;
  resource_id: string;
  metadata_json: Record<string, unknown> | null;
  previous_hash: string;
  entry_hash: string;
  created_at: string;
};

export type AuditVerification = {
  valid: boolean;
  records_checked: number;
  first_broken_record_id: string | null;
};

export type AIConfiguration = {
  provider: AIProvider | null;
  model: string | null;
  base_url: string | null;
  is_enabled: boolean;
  timeout_seconds: number;
  has_api_key: boolean;
  api_key_last_four: string | null;
};

export type AIStatus = {
  is_configured: boolean;
  provider: AIProvider | null;
  model: string | null;
  is_enabled: boolean;
  has_api_key: boolean;
};

export type AIConfigurationInput = {
  provider: AIProvider | null;
  model: string | null;
  api_key?: string | null;
  base_url?: string | null;
  is_enabled: boolean;
  timeout_seconds: number;
};

export type AIConnectionTestResult = {
  success: boolean;
  message: string;
  provider: AIProvider | null;
  model: string | null;
};

export type AIAnalysis = {
  id: string;
  organization_id: string;
  scan_id: string | null;
  incident_id: string | null;
  requested_by: string;
  provider: AIProvider;
  model: string;
  prompt_version: string;
  incident_summary: string | null;
  priority_explanation: string | null;
  immediate_actions: string[] | null;
  long_term_actions: string[] | null;
  possible_false_positive_factors: string[] | null;
  confidence_note: string | null;
  status: AIAnalysisStatus;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
};

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function requestJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    method: options.method ?? "GET",
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers
    },
    credentials: "same-origin",
    body: options.body
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        message = payload.detail;
      }
    } catch {
      // Keep the generic message when the server does not return JSON.
    }
    throw new ApiError(response.status, message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export function getHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>("/api/health");
}

export function getReadiness(): Promise<HealthResponse> {
  return requestJson<HealthResponse>("/api/ready");
}

export function login(email: string, password: string): Promise<AuthResponse> {
  return requestJson<AuthResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
}

export function logout(): Promise<{ status: string }> {
  return requestJson<{ status: string }>("/api/auth/logout", {
    method: "POST"
  });
}

export function getCurrentUser(): Promise<User> {
  return requestJson<User>("/api/auth/me");
}

export function listWebsites(): Promise<WebsiteAsset[]> {
  return requestJson<WebsiteAsset[]>("/api/websites");
}

export function getWebsite(websiteId: string): Promise<WebsiteAsset> {
  return requestJson<WebsiteAsset>(`/api/websites/${websiteId}`);
}

export function createWebsite(payload: WebsiteAssetInput): Promise<WebsiteAsset> {
  return requestJson<WebsiteAsset>("/api/websites", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateWebsite(
  websiteId: string,
  payload: Partial<WebsiteAssetInput>
): Promise<WebsiteAsset> {
  return requestJson<WebsiteAsset>(`/api/websites/${websiteId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function deactivateWebsite(websiteId: string): Promise<void> {
  return requestJson<void>(`/api/websites/${websiteId}`, {
    method: "DELETE"
  });
}

export function startScan(websiteId: string, scanType: ScanType): Promise<Scan> {
  return requestJson<Scan>(`/api/websites/${websiteId}/scans`, {
    method: "POST",
    body: JSON.stringify({ scan_type: scanType })
  });
}

export function listWebsiteScans(websiteId: string): Promise<Scan[]> {
  return requestJson<Scan[]>(`/api/websites/${websiteId}/scans`);
}

export function getScan(scanId: string): Promise<Scan> {
  return requestJson<Scan>(`/api/scans/${scanId}`);
}

export function getScanFindings(scanId: string): Promise<Finding[]> {
  return requestJson<Finding[]>(`/api/scans/${scanId}/findings`);
}

export function approveBaseline(scanId: string): Promise<Baseline> {
  return requestJson<Baseline>(`/api/scans/${scanId}/approve-baseline`, {
    method: "POST"
  });
}

export function getWebsiteBaseline(websiteId: string): Promise<Baseline | null> {
  return requestJson<Baseline | null>(`/api/websites/${websiteId}/baseline`);
}

export function screenshotUrl(scanId: string): string {
  return `/api/evidence/screenshots/${scanId}`;
}

export function differenceImageUrl(scanId: string): string {
  return `/api/evidence/differences/${scanId}`;
}

export function listIncidents(): Promise<Incident[]> {
  return requestJson<Incident[]>("/api/incidents");
}

export function getIncident(incidentId: string): Promise<Incident> {
  return requestJson<Incident>(`/api/incidents/${incidentId}`);
}

export function updateIncident(
  incidentId: string,
  payload: IncidentUpdate
): Promise<Incident> {
  return requestJson<Incident>(`/api/incidents/${incidentId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function addIncidentNote(
  incidentId: string,
  content: string
): Promise<Incident> {
  return requestJson<Incident>(`/api/incidents/${incidentId}/notes`, {
    method: "POST",
    body: JSON.stringify({ content })
  });
}

export function listAuditLogs(): Promise<AuditLog[]> {
  return requestJson<AuditLog[]>("/api/audit");
}

export function verifyAuditChain(): Promise<AuditVerification> {
  return requestJson<AuditVerification>("/api/audit/verify");
}

export function getAIStatus(): Promise<AIStatus> {
  return requestJson<AIStatus>("/api/ai/status");
}

export function getAIConfig(): Promise<AIConfiguration> {
  return requestJson<AIConfiguration>("/api/ai/config");
}

export function saveAIConfig(payload: AIConfigurationInput): Promise<AIConfiguration> {
  return requestJson<AIConfiguration>("/api/ai/config", {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function removeAIKey(): Promise<AIConfiguration> {
  return requestJson<AIConfiguration>("/api/ai/config/key", {
    method: "DELETE"
  });
}

export function testAIConfig(
  payload: AIConfigurationInput
): Promise<AIConnectionTestResult> {
  return requestJson<AIConnectionTestResult>("/api/ai/config/test", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getScanAIAnalysis(scanId: string): Promise<AIAnalysis | null> {
  return requestJson<AIAnalysis | null>(`/api/scans/${scanId}/ai-analysis`);
}

export function generateScanAIAnalysis(scanId: string): Promise<AIAnalysis> {
  return requestJson<AIAnalysis>(`/api/scans/${scanId}/ai-analysis`, {
    method: "POST"
  });
}

export function getIncidentAIAnalysis(incidentId: string): Promise<AIAnalysis | null> {
  return requestJson<AIAnalysis | null>(`/api/incidents/${incidentId}/ai-analysis`);
}

export function generateIncidentAIAnalysis(incidentId: string): Promise<AIAnalysis> {
  return requestJson<AIAnalysis>(`/api/incidents/${incidentId}/ai-analysis`, {
    method: "POST"
  });
}
