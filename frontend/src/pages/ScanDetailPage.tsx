import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  ApiError,
  differenceImageUrl,
  getScan,
  getScanFindings,
  listIncidents,
  screenshotUrl,
  type Finding,
  type Incident,
  type Scan,
  type ScanStatus
} from "../api/client";
import { AIAnalysisCard } from "../components/AIAnalysisCard";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import { formatStatusLabel } from "../utils/format";

export function ScanDetailPage() {
  const { scanId } = useParams();
  const { user, loading: authLoading } = useAuth();
  const [scan, setScan] = useState<Scan | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [incident, setIncident] = useState<Incident | null>(null);
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
        const incidentResponse = await listIncidents();
        if (!cancelled) {
          setScan(scanResponse);
          setFindings(findingsResponse);
          setIncident(
            incidentResponse.find((item) => item.scan_id === scanResponse.id) ?? null
          );
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

  useEffect(() => {
    if (!scanId || !user || !scan || !["queued", "running"].includes(scan.status)) {
      return;
    }
    const timer = window.setInterval(() => {
      void Promise.all([getScan(scanId), getScanFindings(scanId)])
        .then(([scanResponse, findingsResponse]) => {
          setScan(scanResponse);
          setFindings(findingsResponse);
        })
        .catch(() => {
          setError("Unable to refresh scan status.");
        });
    }, 2000);
    return () => window.clearInterval(timer);
  }, [scan, scanId, user]);

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
            <h2>Latest Scan Risk</h2>
            <StatusBadge
              label={scan.risk_level ? formatStatusLabel(scan.risk_level) : "Pending"}
              tone={riskTone(scan.risk_level)}
            />
          </div>
          <p className="body-copy">
            {scan.risk_score !== null
              ? `${scan.risk_score} calculated evidence point(s)`
              : "Risk is calculated after scan completion."}
          </p>
        </article>
      </div>

      {scan.failure_reason ? (
        <div className="alert" role="alert">
          <strong>Scan failed safely.</strong>
          <span>{scan.failure_reason}</span>
        </div>
      ) : null}

      {incident ? (
        <div className="alert" role="alert">
          <strong>Incident created.</strong>
          <span>
            <Link to={`/incidents/${incident.id}`}>Open generated incident</Link>
          </span>
        </div>
      ) : null}

      {scan.status === "completed" && !scan.baseline_scan_id ? (
        <div className="empty-state">
          <h2>Initial scan — no baseline comparison available</h2>
          <p>Approve this successful scan as the trusted baseline before running a comparison.</p>
        </div>
      ) : null}

      {scan.baseline_scan_id ? (
        <div className="empty-state">
          <h2>Comparison scan</h2>
          <p>
            This scan was compared against the active approved baseline and scored from
            deterministic evidence.
          </p>
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
            <div>
              <dt>AI availability</dt>
              <dd>AI remediation is disabled. Deterministic remediation guidance remains available.</dd>
            </div>
          </dl>
        </section>

        <section className="panel" aria-labelledby="comparison-heading">
          <div className="card-header">
            <h2 id="comparison-heading">Comparison Summary</h2>
          </div>
          <dl className="compact-list">
            <div>
              <dt>Visual change</dt>
              <dd>
                {scan.visual_change_percent !== null
                  ? `${formatNumber(scan.visual_change_percent)}% (${scan.visual_change_level ?? "unclassified"})`
                  : "Not available"}
              </dd>
            </div>
            <div>
              <dt>Text similarity</dt>
              <dd>
                {scan.text_similarity_percent !== null
                  ? `${formatNumber(scan.text_similarity_percent)}%`
                  : "Not available"}
              </dd>
            </div>
            <div>
              <dt>Perceptual hash distance</dt>
              <dd>{scan.perceptual_hash_distance ?? "Not available"}</dd>
            </div>
            <div>
              <dt>Title change</dt>
              <dd>
                {scan.title_changed === null
                  ? "Not available"
                  : scan.title_changed
                    ? `${scan.baseline_title ?? "Untitled"} -> ${scan.current_title ?? "Untitled"}`
                    : "No title change detected"}
              </dd>
            </div>
            <div>
              <dt>Suspicious phrases</dt>
              <dd>{scan.suspicious_phrases?.join(", ") || "None detected"}</dd>
            </div>
            <div>
              <dt>New script domains</dt>
              <dd>{scan.new_external_script_domains?.join(", ") || "None detected"}</dd>
            </div>
            <div>
              <dt>New iframe domains</dt>
              <dd>{scan.new_external_iframe_domains?.join(", ") || "None detected"}</dd>
            </div>
            {scan.comparison_error ? (
              <div>
                <dt>Comparison warning</dt>
                <dd>{scan.comparison_error}</dd>
              </div>
            ) : null}
          </dl>
        </section>
      </div>

      <section className="panel panel--full" aria-labelledby="screenshots-heading">
        <div className="card-header">
          <h2 id="screenshots-heading">Screenshots</h2>
        </div>
        <div className="evidence-grid">
          {scan.baseline_scan_id ? (
            <figure>
              <figcaption>Approved baseline</figcaption>
              <img
                className="screenshot-preview"
                src={screenshotUrl(scan.baseline_scan_id)}
                alt="Approved baseline screenshot"
              />
            </figure>
          ) : null}
          {scan.screenshot_filename ? (
            <figure>
              <figcaption>Current scan</figcaption>
              <img
                className="screenshot-preview"
                src={screenshotUrl(scan.id)}
                alt="Current scan screenshot"
              />
            </figure>
          ) : null}
          {scan.difference_image_filename ? (
            <figure>
              <figcaption>Difference image</figcaption>
              <img
                className="screenshot-preview"
                src={differenceImageUrl(scan.id)}
                alt="Highlighted visual difference"
              />
            </figure>
          ) : null}
        </div>
      </section>

      <section className="panel panel--full" aria-labelledby="risk-heading">
        <div className="card-header">
          <h2 id="risk-heading">Deterministic Risk Score</h2>
          <StatusBadge
            label={scan.risk_score !== null ? String(scan.risk_score) : "Pending"}
            tone={riskTone(scan.risk_level)}
          />
        </div>
        {scan.risk_breakdown?.length ? (
          <dl className="compact-list">
            {scan.risk_breakdown.map((item) => (
              <div key={`${item.reason}-${item.evidence}`}>
                <dt>
                  {item.reason} (+{item.points})
                </dt>
                <dd>{item.evidence}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="body-copy">No risk factors have been recorded for this scan.</p>
        )}
      </section>

      <AIAnalysisCard
        subjectId={scan.id}
        subjectType="scan"
        canGenerate={user?.role === "administrator" || user?.role === "security_analyst"}
        completed={scan.status === "completed"}
      />

      <section className="panel panel--full" aria-labelledby="headers-heading">
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

      <section className="panel panel--full" aria-labelledby="findings-heading">
        <div className="card-header">
          <h2 id="findings-heading">Rule-Based Security Findings</h2>
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

function riskTone(riskLevel: string | null): "good" | "pending" | "blocked" {
  if (riskLevel === "low") {
    return "good";
  }
  if (riskLevel === "moderate" || riskLevel === null) {
    return "pending";
  }
  return "blocked";
}

function formatNumber(value: number): string {
  return value.toLocaleString(undefined, {
    maximumFractionDigits: 2
  });
}
