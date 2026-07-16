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
