import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  ApiError,
  approveBaseline,
  deactivateWebsite,
  getWebsite,
  getWebsiteBaseline,
  listWebsiteScans,
  screenshotUrl,
  startScan,
  updateWebsite,
  type Baseline,
  type Scan,
  type ScanStatus,
  type WebsiteAsset
} from "../api/client";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import { formatStatusLabel } from "../utils/format";

export function WebsiteDetailPage() {
  const { websiteId } = useParams();
  const { user, loading: authLoading } = useAuth();
  const [asset, setAsset] = useState<WebsiteAsset | null>(null);
  const [scans, setScans] = useState<Scan[]>([]);
  const [baseline, setBaseline] = useState<Baseline | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState(false);

  const canManageWebsite = user?.role === "administrator";
  const canStartScan = user?.role === "administrator" || user?.role === "security_analyst";
  const latestScan = scans[0] ?? null;
  const polling = latestScan?.status === "queued" || latestScan?.status === "running";

  const loadAll = useCallback(async () => {
    if (!websiteId || !user) {
      return;
    }
    const [assetResponse, scansResponse, baselineResponse] = await Promise.all([
      getWebsite(websiteId),
      listWebsiteScans(websiteId),
      getWebsiteBaseline(websiteId)
    ]);
    setAsset(assetResponse);
    setScans(scansResponse);
    setBaseline(baselineResponse);
  }, [user, websiteId]);

  useEffect(() => {
    if (authLoading || !websiteId) {
      return;
    }
    if (!user) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    async function loadInitial() {
      setLoading(true);
      setError(null);
      try {
        await loadAll();
      } catch (caughtError) {
        if (!cancelled) {
          const message =
            caughtError instanceof ApiError ? caughtError.message : "Unable to load website.";
          setError(message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadInitial();
    return () => {
      cancelled = true;
    };
  }, [authLoading, loadAll, user, websiteId]);

  useEffect(() => {
    if (!polling) {
      return;
    }
    const timer = window.setInterval(() => {
      void loadAll().catch(() => {
        setActionError("Unable to refresh scan status.");
      });
    }, 2500);
    return () => window.clearInterval(timer);
  }, [loadAll, polling]);

  const baselineScanIds = useMemo(
    () => new Set(baseline ? [baseline.scan_id] : []),
    [baseline]
  );

  async function runScan() {
    if (!asset || !canStartScan) {
      return;
    }
    setActionError(null);
    setActionBusy(true);
    try {
      const created = await startScan(asset.id, baseline ? "comparison" : "baseline");
      setScans((current) => [created, ...current]);
    } catch (caughtError) {
      const message =
        caughtError instanceof ApiError ? caughtError.message : "Unable to start scan.";
      setActionError(message);
    } finally {
      setActionBusy(false);
    }
  }

  async function approveLatestBaseline(scan: Scan) {
    setActionError(null);
    setActionBusy(true);
    try {
      const approved = await approveBaseline(scan.id);
      setBaseline(approved);
      setAsset((current) =>
        current ? { ...current, current_baseline_id: approved.id } : current
      );
    } catch (caughtError) {
      const message =
        caughtError instanceof ApiError ? caughtError.message : "Unable to approve baseline.";
      setActionError(message);
    } finally {
      setActionBusy(false);
    }
  }

  async function toggleMonitoring() {
    if (!asset) {
      return;
    }
    setActionError(null);
    try {
      const updated = await updateWebsite(asset.id, {
        monitoring_enabled: !asset.monitoring_enabled
      });
      setAsset(updated);
    } catch (caughtError) {
      const message =
        caughtError instanceof ApiError ? caughtError.message : "Unable to update monitoring.";
      setActionError(message);
    }
  }

  async function deactivate() {
    if (!asset) {
      return;
    }
    setActionError(null);
    try {
      await deactivateWebsite(asset.id);
      setAsset({ ...asset, monitoring_enabled: false });
    } catch (caughtError) {
      const message =
        caughtError instanceof ApiError ? caughtError.message : "Unable to deactivate website.";
      setActionError(message);
    }
  }

  if (!authLoading && !user) {
    return (
      <section className="page-section page-section--narrow">
        <div className="empty-state">
          <h1>Sign in required</h1>
          <p>Website details are visible only to authenticated organization members.</p>
          <Link className="button" to="/login">
            Sign in
          </Link>
        </div>
      </section>
    );
  }

  if (loading) {
    return (
      <section className="page-section">
        <p className="body-copy">Loading website detail.</p>
      </section>
    );
  }

  if (error || !asset) {
    return (
      <section className="page-section page-section--narrow">
        <div className="alert" role="alert">
          <strong>Website unavailable.</strong>
          <span>{error ?? "Website asset not found."}</span>
        </div>
        <Link className="button" to="/websites">
          Back to websites
        </Link>
      </section>
    );
  }

  return (
    <section className="page-section" aria-labelledby="website-detail-heading">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Website Detail</p>
          <h1 id="website-detail-heading">{asset.name}</h1>
          <p className="page-description">{asset.normalized_url}</p>
        </div>
        <Link className="button button--secondary" to="/websites">
          Back to websites
        </Link>
      </div>

      <div className="status-grid">
        <article className="status-card">
          <div className="card-header">
            <h2>Monitoring</h2>
            <StatusBadge
              label={asset.monitoring_enabled ? "Enabled" : "Disabled"}
              tone={asset.monitoring_enabled ? "good" : "pending"}
            />
          </div>
          <p className="body-copy">
            Authorization confirmed: {asset.authorization_confirmed ? "Yes" : "No"}
          </p>
        </article>

        <article className="status-card">
          <div className="card-header">
            <h2>Risk Category</h2>
            <StatusBadge label={formatStatusLabel(asset.risk_category)} tone="pending" />
          </div>
          <p className="body-copy">{asset.contact_email}</p>
        </article>

        <article className="status-card">
          <div className="card-header">
            <h2>Latest Scan</h2>
            <StatusBadge
              label={latestScan ? formatStatusLabel(latestScan.status) : "Not run"}
              tone={statusTone(latestScan?.status)}
            />
          </div>
          <p className="body-copy">
            {latestScan
              ? `${latestScan.scan_type} scan created ${formatDate(latestScan.created_at)}`
              : "No scan has been started for this website."}
          </p>
        </article>

        <article className="status-card">
          <div className="card-header">
            <h2>Baseline</h2>
            <StatusBadge label={baseline ? "Active" : "Not approved"} tone={baseline ? "good" : "pending"} />
          </div>
          <p className="body-copy">
            {baseline
              ? `Approved ${formatDate(baseline.approved_at)}`
              : "A completed scan can be approved as the trusted baseline."}
          </p>
        </article>
      </div>

      <div className="action-row">
        {canStartScan ? (
          <button
            className="button"
            type="button"
            disabled={actionBusy || polling || !asset.monitoring_enabled}
            onClick={() => void runScan()}
          >
            {polling ? "Scan running" : "Run Scan"}
          </button>
        ) : null}
        {canManageWebsite ? (
          <>
            <button className="button button--secondary" type="button" onClick={() => void toggleMonitoring()}>
              {asset.monitoring_enabled ? "Disable monitoring" : "Enable monitoring"}
            </button>
            <button className="button button--secondary" type="button" onClick={() => void deactivate()}>
              Deactivate
            </button>
          </>
        ) : null}
      </div>

      {actionError ? (
        <div className="alert" role="alert">
          <strong>Action failed.</strong>
          <span>{actionError}</span>
        </div>
      ) : null}

      <div className="detail-grid">
        <section className="panel" aria-labelledby="baseline-heading">
          <div className="card-header">
            <h2 id="baseline-heading">Active Baseline</h2>
            {baseline?.scan.screenshot_filename ? (
              <Link to={`/scans/${baseline.scan_id}`}>Open scan</Link>
            ) : null}
          </div>
          {baseline ? (
            <>
              <dl className="compact-list">
                <div>
                  <dt>Scan</dt>
                  <dd>{baseline.scan_id}</dd>
                </div>
                <div>
                  <dt>Approved</dt>
                  <dd>{formatDate(baseline.approved_at)}</dd>
                </div>
                <div>
                  <dt>Page title</dt>
                  <dd>{baseline.scan.page_title ?? "Not captured"}</dd>
                </div>
              </dl>
              {baseline.scan.screenshot_filename ? (
                <img
                  className="screenshot-preview"
                  src={screenshotUrl(baseline.scan_id)}
                  alt="Approved baseline screenshot"
                />
              ) : null}
            </>
          ) : (
            <p className="body-copy">No trusted baseline has been approved yet.</p>
          )}
        </section>

        <section className="panel" aria-labelledby="scan-history-heading">
          <div className="card-header">
            <h2 id="scan-history-heading">Scan History</h2>
          </div>
          {scans.length > 0 ? (
            <div className="table-wrap table-wrap--compact">
              <table>
                <thead>
                  <tr>
                    <th>Status</th>
                    <th>Type</th>
                    <th>HTTP</th>
                    <th>Created</th>
                    <th>Result</th>
                  </tr>
                </thead>
                <tbody>
                  {scans.map((scan) => (
                    <tr key={scan.id}>
                      <td>
                        <StatusBadge label={formatStatusLabel(scan.status)} tone={statusTone(scan.status)} />
                      </td>
                      <td>{formatStatusLabel(scan.scan_type)}</td>
                      <td>{scan.http_status ?? "-"}</td>
                      <td>{formatDate(scan.created_at)}</td>
                      <td>
                        <Link to={`/scans/${scan.id}`}>
                          {baselineScanIds.has(scan.id) ? "Baseline" : "Open"}
                        </Link>
                        {canStartScan && scan.status === "completed" && !baselineScanIds.has(scan.id) ? (
                          <button
                            className="link-button"
                            type="button"
                            disabled={actionBusy}
                            onClick={() => void approveLatestBaseline(scan)}
                          >
                            Approve as Baseline
                          </button>
                        ) : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="body-copy">No scans are available.</p>
          )}
        </section>
      </div>
    </section>
  );
}

function statusTone(status: ScanStatus | undefined): "good" | "pending" | "blocked" {
  if (status === "completed") {
    return "good";
  }
  if (status === "failed") {
    return "blocked";
  }
  return "pending";
}

function formatDate(value: string | null): string {
  if (!value) {
    return "Not available";
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}
