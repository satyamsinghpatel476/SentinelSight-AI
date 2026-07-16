import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  ApiError,
  getScan,
  getScanFindings,
  screenshotUrl,
  type Finding,
  type Scan,
  type ScanStatus
} from "../api/client";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import { formatStatusLabel } from "../utils/format";

export function ScanDetailPage() {
  const { scanId } = useParams();
  const { user, loading: authLoading } = useAuth();
  const [scan, setScan] = useState<Scan | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading || !scanId) {
      return;
    }
    if (!user) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    const id = scanId;
    async function loadScan() {
      setLoading(true);
      setError(null);
      try {
        const [scanResponse, findingsResponse] = await Promise.all([
          getScan(id),
          getScanFindings(id)
        ]);
        if (!cancelled) {
          setScan(scanResponse);
          setFindings(findingsResponse);
        }
      } catch (caughtError) {
        if (!cancelled) {
          const message =
            caughtError instanceof ApiError ? caughtError.message : "Unable to load scan.";
          setError(message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadScan();
    return () => {
      cancelled = true;
    };
  }, [authLoading, scanId, user]);

  const tlsFindings = useMemo(
    () => findings.filter((finding) => finding.type.startsWith("tls_")),
    [findings]
  );

  if (!authLoading && !user) {
    return (
      <section className="page-section page-section--narrow">
        <div className="empty-state">
          <h1>Sign in required</h1>
          <p>Scan details are visible only to authenticated organization members.</p>
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
        <p className="body-copy">Loading scan detail.</p>
      </section>
    );
  }

  if (error || !scan) {
    return (
      <section className="page-section page-section--narrow">
        <div className="alert" role="alert">
          <strong>Scan unavailable.</strong>
          <span>{error ?? "Scan not found."}</span>
        </div>
        <Link className="button" to="/websites">
          Back to websites
        </Link>
      </section>
    );
  }

  return (
    <section className="page-section" aria-labelledby="scan-detail-heading">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Scan Detail</p>
          <h1 id="scan-detail-heading">{formatStatusLabel(scan.status)} Scan</h1>
          <p className="page-description">{scan.requested_url}</p>
        </div>
        <Link className="button button--secondary" to={`/websites/${scan.website_asset_id}`}>
          Back to website
        </Link>
      </div>

      <div className="status-grid">
        <article className="status-card">
          <div className="card-header">
            <h2>Status</h2>
            <StatusBadge label={formatStatusLabel(scan.status)} tone={statusTone(scan.status)} />
          </div>
          <p className="body-copy">{formatStatusLabel(scan.scan_type)} scan</p>
        </article>
        <article className="status-card">
          <div className="card-header">
            <h2>HTTP</h2>
            <StatusBadge label={scan.http_status ? String(scan.http_status) : "Pending"} tone="pending" />
          </div>
          <p className="body-copy">
            {scan.response_time_ms !== null ? `${scan.response_time_ms} ms` : "No timing captured"}
          </p>
        </article>
        <article className="status-card">
          <div className="card-header">
            <h2>Content</h2>
            <StatusBadge label={scan.page_title ? "Captured" : "Pending"} tone={scan.page_title ? "good" : "pending"} />
          </div>
          <p className="body-copy">{scan.page_title ?? "No page title captured"}</p>
        </article>
        <article className="status-card">
          <div className="card-header">
            <h2>Findings</h2>
            <StatusBadge label={String(findings.length)} tone={findings.length ? "pending" : "good"} />
          </div>
          <p className="body-copy">
            {tlsFindings.length ? `${tlsFindings.length} TLS-related finding(s)` : "No TLS findings"}
          </p>
        </article>
      </div>

      {scan.failure_reason ? (
        <div className="alert" role="alert">
          <strong>Scan failed safely.</strong>
          <span>{scan.failure_reason}</span>
        </div>
      ) : null}

      <div className="detail-grid">
        <section className="panel" aria-labelledby="evidence-heading">
          <div className="card-header">
            <h2 id="evidence-heading">Evidence</h2>
          </div>
          <dl className="compact-list">
            <div>
              <dt>Final URL</dt>
              <dd>{scan.final_url ?? "Not captured"}</dd>
            </div>
            <div>
              <dt>HTML hash</dt>
              <dd>{scan.html_hash ?? "Not captured"}</dd>
            </div>
            <div>
              <dt>Visible text hash</dt>
              <dd>{scan.visible_text_hash ?? "Not captured"}</dd>
            </div>
            <div>
              <dt>Screenshot pHash</dt>
              <dd>{scan.screenshot_perceptual_hash ?? "Not captured"}</dd>
            </div>
          </dl>
          {scan.screenshot_filename ? (
            <img
              className="screenshot-preview"
              src={screenshotUrl(scan.id)}
              alt="Scan screenshot"
            />
          ) : null}
        </section>

        <section className="panel" aria-labelledby="headers-heading">
          <div className="card-header">
            <h2 id="headers-heading">Headers Summary</h2>
          </div>
          {scan.response_headers ? (
            <dl className="compact-list">
              {Object.entries(scan.response_headers).map(([name, value]) => (
                <div key={name}>
                  <dt>{name}</dt>
                  <dd>{Array.isArray(value) ? value.join(", ") : String(value)}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="body-copy">No response headers captured.</p>
          )}
        </section>
      </div>

      <section className="panel panel--full" aria-labelledby="findings-heading">
        <div className="card-header">
          <h2 id="findings-heading">Security Findings</h2>
        </div>
        {findings.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Severity</th>
                  <th>Title</th>
                  <th>Evidence</th>
                  <th>Remediation</th>
                  <th>Risk</th>
                </tr>
              </thead>
              <tbody>
                {findings.map((finding) => (
                  <tr key={finding.id}>
                    <td>{formatStatusLabel(finding.severity)}</td>
                    <td>{finding.title}</td>
                    <td>{finding.evidence}</td>
                    <td>{finding.remediation}</td>
                    <td>{finding.risk_points}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="body-copy">No passive security findings were generated.</p>
        )}
      </section>
    </section>
  );
}

function statusTone(status: ScanStatus): "good" | "pending" | "blocked" {
  if (status === "completed") {
    return "good";
  }
  if (status === "failed") {
    return "blocked";
  }
  return "pending";
}
