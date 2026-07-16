import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import {
  ApiError,
  getAIStatus,
  listIncidents,
  listWebsiteScans,
  listWebsites,
  verifyAuditChain,
  type AIStatus,
  type AuditVerification,
  type Incident,
  type Scan,
  type WebsiteAsset
} from "../api/client";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import { useHealthCheck } from "../hooks/useHealthCheck";
import { formatStatusLabel } from "../utils/format";

type DashboardData = {
  assets: WebsiteAsset[];
  scans: Scan[];
  incidents: Incident[];
  audit: AuditVerification | null;
  ai: AIStatus | null;
};

export function FoundationPage() {
  const { health, readiness, loading: healthLoading, error: healthError, refresh } = useHealthCheck();
  const { user, loading: authLoading } = useAuth();
  const [dashboard, setDashboard] = useState<DashboardData>({
    assets: [],
    scans: [],
    incidents: [],
    audit: null,
    ai: null
  });
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [dashboardError, setDashboardError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading || !user) {
      return;
    }
    let cancelled = false;
    async function loadDashboard() {
      setDashboardLoading(true);
      setDashboardError(null);
      try {
        const [assets, incidents, audit, ai] = await Promise.all([
          listWebsites(),
          listIncidents(),
          verifyAuditChain(),
          getAIStatus()
        ]);
        const scansByAsset = await Promise.all(
          assets.map((asset) => listWebsiteScans(asset.id))
        );
        if (!cancelled) {
          setDashboard({
            assets,
            incidents,
            audit,
            ai,
            scans: scansByAsset.flat()
          });
        }
      } catch (caughtError) {
        if (!cancelled) {
          const message =
            caughtError instanceof ApiError
              ? caughtError.message
              : "Unable to load dashboard data.";
          setDashboardError(message);
        }
      } finally {
        if (!cancelled) {
          setDashboardLoading(false);
        }
      }
    }

    void loadDashboard();
    return () => {
      cancelled = true;
    };
  }, [authLoading, user]);

  const latestScan = useMemo(
    () =>
      dashboard.scans
        .slice()
        .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))[0] ?? null,
    [dashboard.scans]
  );
  const activeIncidents = dashboard.incidents.filter(
    (incident) => incident.status === "open" || incident.status === "investigating"
  );
  const completedScans = dashboard.scans.filter((scan) => scan.status === "completed");

  const apiTone = healthError ? "blocked" : healthLoading ? "pending" : "good";
  const apiLabel = healthError ? "Unavailable" : healthLoading ? "Checking" : "Online";

  return (
    <section className="page-section" aria-labelledby="dashboard-heading">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Operations</p>
          <h1 id="dashboard-heading">Security Operations Dashboard</h1>
          <p className="page-description">
            Live monitoring status for authorized websites, deterministic scans, incidents, audit
            verification and BYOK AI availability.
          </p>
        </div>
        <button className="button" type="button" onClick={() => void refresh()}>
          Refresh Health
        </button>
      </div>

      <div className="status-grid">
        <article className="status-card">
          <div className="card-header">
            <h2>Backend API</h2>
            <StatusBadge label={apiLabel} tone={apiTone} />
          </div>
          <dl>
            <div>
              <dt>Service</dt>
              <dd>{health?.service ?? "Waiting for health response"}</dd>
            </div>
            <div>
              <dt>Environment</dt>
              <dd>{health?.environment ?? "Unknown"}</dd>
            </div>
          </dl>
        </article>

        <article className="status-card">
          <div className="card-header">
            <h2>Database</h2>
            <StatusBadge
              label={readiness?.status === "ready" ? "Ready" : healthLoading ? "Checking" : "Blocked"}
              tone={readiness?.status === "ready" ? "good" : healthLoading ? "pending" : "blocked"}
            />
          </div>
          <p className="body-copy">Readiness includes database connectivity.</p>
        </article>

        <article className="status-card">
          <div className="card-header">
            <h2>Websites</h2>
            <StatusBadge
              label={user ? String(dashboard.assets.length) : "Sign in"}
              tone={dashboard.assets.length ? "good" : "pending"}
            />
          </div>
          <p className="body-copy">
            {user
              ? `${dashboard.assets.filter((asset) => asset.monitoring_enabled).length} actively monitored`
              : "Sign in to view organization assets."}
          </p>
        </article>

        <article className="status-card">
          <div className="card-header">
            <h2>Scanner Status</h2>
            <StatusBadge
              label={healthError ? "Unavailable" : healthLoading ? "Checking" : "Operational"}
              tone={healthError ? "blocked" : healthLoading ? "pending" : "good"}
            />
          </div>
          <p className="body-copy">
            Safe passive scanning, screenshot capture, baseline comparison, deterministic risk
            scoring and incident response are available.
          </p>
          <dl>
            <div>
              <dt>Completed scans</dt>
              <dd>{user ? completedScans.length : "Sign in"}</dd>
            </div>
            <div>
              <dt>Latest scan risk</dt>
              <dd>
                {latestScan?.risk_level
                  ? formatStatusLabel(latestScan.risk_level)
                  : "Not calculated"}
              </dd>
            </div>
          </dl>
        </article>
      </div>

      <div className="status-grid dashboard-secondary">
        <article className="status-card">
          <div className="card-header">
            <h2>Incidents</h2>
            <StatusBadge
              label={user ? String(activeIncidents.length) : "Sign in"}
              tone={activeIncidents.length ? "blocked" : "good"}
            />
          </div>
          <p className="body-copy">
            {dashboard.incidents.length} total incident record(s) in this organization.
          </p>
        </article>

        <article className="status-card">
          <div className="card-header">
            <h2>Audit Chain</h2>
            <StatusBadge
              label={
                dashboard.audit
                  ? dashboard.audit.valid
                    ? "Valid"
                    : "Broken"
                  : user
                    ? "Loading"
                    : "Sign in"
              }
              tone={dashboard.audit?.valid ? "good" : dashboard.audit ? "blocked" : "pending"}
            />
          </div>
          <p className="body-copy">
            {dashboard.audit
              ? `${dashboard.audit.records_checked} record(s) checked`
              : "Audit verification appears after sign-in."}
          </p>
        </article>

        <article className="status-card">
          <div className="card-header">
            <h2>AI Incident Analysis</h2>
            <StatusBadge
              label={aiStatusLabel(dashboard.ai, Boolean(user))}
              tone={aiStatusTone(dashboard.ai)}
            />
          </div>
          <p className="body-copy">
            {dashboard.ai?.provider && dashboard.ai.model
              ? `${formatStatusLabel(dashboard.ai.provider)} / ${dashboard.ai.model}`
              : "BYOK provider configuration is managed by Administrators."}
          </p>
        </article>

        <article className="status-card">
          <div className="card-header">
            <h2>Session</h2>
            <StatusBadge
              label={user ? "Signed in" : authLoading ? "Checking" : "Signed out"}
              tone={user ? "good" : authLoading ? "pending" : "blocked"}
            />
          </div>
          <p className="body-copy">
            {user ? `${user.name} (${formatStatusLabel(user.role)})` : "Sign in to run demo workflows."}
          </p>
        </article>
      </div>

      {!user && !authLoading ? (
        <div className="inline-action">
          <Link className="button" to="/login">
            Sign in
          </Link>
        </div>
      ) : null}

      {dashboardLoading ? <p className="body-copy">Refreshing dashboard data.</p> : null}

      {healthError ? (
        <div className="alert" role="alert">
          <strong>Backend check failed.</strong>
          <span>{healthError}</span>
        </div>
      ) : null}

      {dashboardError ? (
        <div className="alert" role="alert">
          <strong>Dashboard data unavailable.</strong>
          <span>{dashboardError}</span>
        </div>
      ) : null}
    </section>
  );
}

function aiStatusLabel(status: AIStatus | null, signedIn: boolean): string {
  if (!signedIn) {
    return "Sign in";
  }
  if (!status?.is_configured) {
    return "Not configured";
  }
  if (!status.is_enabled) {
    return "Disabled";
  }
  if (!status.has_api_key) {
    return "Missing key";
  }
  return "Ready";
}

function aiStatusTone(status: AIStatus | null): "good" | "pending" | "blocked" {
  if (status?.is_configured && status.is_enabled && status.has_api_key) {
    return "good";
  }
  if (status?.is_configured && status.is_enabled && !status.has_api_key) {
    return "blocked";
  }
  return "pending";
}
