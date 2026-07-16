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
