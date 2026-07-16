import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  ApiError,
  addIncidentNote,
  differenceImageUrl,
  getIncident,
  screenshotUrl,
  updateIncident,
  type Incident,
  type IncidentStatus
} from "../api/client";
import { AIAnalysisCard } from "../components/AIAnalysisCard";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import { formatStatusLabel } from "../utils/format";

export function IncidentDetailPage() {
  const { incidentId } = useParams();
  const { user, loading: authLoading } = useAuth();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [note, setNote] = useState("");
  const [resolutionNotes, setResolutionNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [actionBusy, setActionBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const canManage = user?.role === "administrator" || user?.role === "security_analyst";
  const transitionTargets = useMemo(
    () => (incident ? allowedTargets(incident.status) : []),
    [incident]
  );

  useEffect(() => {
    if (authLoading || !incidentId) {
      return;
    }
    if (!user) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    const id = incidentId;
    async function loadIncident() {
      setLoading(true);
      setError(null);
      try {
        const response = await getIncident(id);
        if (!cancelled) {
          setIncident(response);
          setResolutionNotes(response.resolution_notes ?? "");
        }
      } catch (caughtError) {
        if (!cancelled) {
          const message =
            caughtError instanceof ApiError ? caughtError.message : "Unable to load incident.";
          setError(message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadIncident();
    return () => {
      cancelled = true;
    };
  }, [authLoading, incidentId, user]);

  async function changeStatus(status: IncidentStatus) {
    if (!incident) {
      return;
    }
    setActionError(null);
    setActionBusy(true);
    try {
      const updated = await updateIncident(incident.id, {
        status,
        resolution_notes: resolutionNotes || null
      });
      setIncident(updated);
      setResolutionNotes(updated.resolution_notes ?? "");
    } catch (caughtError) {
      const message =
        caughtError instanceof ApiError ? caughtError.message : "Unable to update incident.";
      setActionError(message);
    } finally {
      setActionBusy(false);
    }
  }

  async function saveResolutionNotes() {
    if (!incident) {
      return;
    }
    setActionError(null);
    setActionBusy(true);
    try {
      const updated = await updateIncident(incident.id, {
        resolution_notes: resolutionNotes || null
      });
      setIncident(updated);
      setResolutionNotes(updated.resolution_notes ?? "");
    } catch (caughtError) {
      const message =
        caughtError instanceof ApiError ? caughtError.message : "Unable to save notes.";
      setActionError(message);
    } finally {
      setActionBusy(false);
    }
  }

  async function submitNote() {
    if (!incident || !note.trim()) {
      return;
    }
    setActionError(null);
    setActionBusy(true);
    try {
      const updated = await addIncidentNote(incident.id, note.trim());
      setIncident(updated);
      setNote("");
    } catch (caughtError) {
      const message =
        caughtError instanceof ApiError ? caughtError.message : "Unable to add note.";
      setActionError(message);
    } finally {
      setActionBusy(false);
    }
  }

  if (!authLoading && !user) {
    return (
      <section className="page-section page-section--narrow">
        <div className="empty-state">
          <h1>Sign in required</h1>
          <p>Incident details are visible only to authenticated organization members.</p>
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
        <p className="body-copy">Loading incident.</p>
      </section>
    );
  }

  if (error || !incident) {
    return (
      <section className="page-section page-section--narrow">
        <div className="alert" role="alert">
          <strong>Incident unavailable.</strong>
          <span>{error ?? "Incident not found."}</span>
        </div>
        <Link className="button" to="/incidents">
          Back to incidents
        </Link>
      </section>
    );
  }

  return (
    <section className="page-section" aria-labelledby="incident-heading">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Incident Detail</p>
          <h1 id="incident-heading">{incident.title}</h1>
          <p className="page-description">{incident.description}</p>
        </div>
        <Link className="button button--secondary" to="/incidents">
          Back to incidents
        </Link>
      </div>

      <div className="status-grid">
        <article className="status-card">
          <div className="card-header">
            <h2>Status</h2>
            <StatusBadge
              label={formatStatusLabel(incident.status)}
              tone={incidentTone(incident.status)}
            />
          </div>
          <p className="body-copy">{formatDate(incident.created_at)}</p>
        </article>
        <article className="status-card">
          <div className="card-header">
            <h2>Severity</h2>
            <StatusBadge label={formatStatusLabel(incident.severity)} tone="blocked" />
          </div>
          <p className="body-copy">Risk score {incident.risk_score}</p>
        </article>
        <article className="status-card">
          <div className="card-header">
            <h2>Website</h2>
          </div>
          <p className="body-copy">
            {incident.website_asset ? (
              <Link to={`/websites/${incident.website_asset.id}`}>
                {incident.website_asset.name}
              </Link>
            ) : (
              incident.website_asset_id
            )}
          </p>
        </article>
        <article className="status-card">
          <div className="card-header">
            <h2>Scan</h2>
          </div>
          <p className="body-copy">
            <Link to={`/scans/${incident.scan_id}`}>Open linked scan</Link>
          </p>
        </article>
      </div>

      {actionError ? (
        <div className="alert" role="alert">
          <strong>Action failed.</strong>
          <span>{actionError}</span>
        </div>
      ) : null}

      <div className="detail-grid">
        <section className="panel" aria-labelledby="incident-evidence-heading">
          <div className="card-header">
            <h2 id="incident-evidence-heading">Evidence Images</h2>
          </div>
          {incident.scan?.baseline_scan_id ? (
            <img
              className="screenshot-preview"
              src={screenshotUrl(incident.scan.baseline_scan_id)}
              alt="Approved baseline screenshot"
            />
          ) : null}
          {incident.scan?.screenshot_filename ? (
            <img
              className="screenshot-preview"
              src={screenshotUrl(incident.scan.id)}
              alt="Current scan screenshot"
            />
          ) : null}
          {incident.scan?.difference_image_filename ? (
            <img
              className="screenshot-preview"
              src={differenceImageUrl(incident.scan.id)}
              alt="Highlighted visual difference"
            />
          ) : null}
        </section>

        <section className="panel" aria-labelledby="incident-risk-heading">
          <div className="card-header">
            <h2 id="incident-risk-heading">Risk Breakdown</h2>
          </div>
          {incident.risk_breakdown?.length ? (
            <dl className="compact-list">
              {incident.risk_breakdown.map((item) => (
                <div key={`${item.reason}-${item.evidence}`}>
                  <dt>
                    {item.reason} (+{item.points})
                  </dt>
                  <dd>{item.evidence}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="body-copy">No risk breakdown was stored.</p>
          )}
        </section>
      </div>

      <section className="panel panel--full" aria-labelledby="workflow-heading">
        <div className="card-header">
          <h2 id="workflow-heading">Investigation Workflow</h2>
          {!canManage ? <StatusBadge label="Read only" tone="pending" /> : null}
        </div>
        <label className="field-stack">
          Resolution notes
          <textarea
            value={resolutionNotes}
            disabled={!canManage || actionBusy}
            onChange={(event) => setResolutionNotes(event.target.value)}
          />
        </label>
        {canManage ? (
          <div className="action-row">
            <button
              className="button button--secondary"
              type="button"
              disabled={actionBusy}
              onClick={() => void saveResolutionNotes()}
            >
              Save Notes
            </button>
            {transitionTargets.map((status) => (
              <button
                className="button"
                type="button"
                disabled={actionBusy}
                key={status}
                onClick={() => void changeStatus(status)}
              >
                {actionLabel(status)}
              </button>
            ))}
          </div>
        ) : null}
      </section>

      <AIAnalysisCard
        subjectId={incident.id}
        subjectType="incident"
        canGenerate={canManage}
        completed={incident.scan?.status === "completed"}
      />

      <section className="panel panel--full" aria-labelledby="notes-heading">
        <div className="card-header">
          <h2 id="notes-heading">Investigation Notes</h2>
        </div>
        {canManage ? (
          <div className="note-composer">
            <textarea
              value={note}
              disabled={actionBusy}
              placeholder="Add an investigation note"
              onChange={(event) => setNote(event.target.value)}
            />
            <button
              className="button"
              type="button"
              disabled={actionBusy || !note.trim()}
              onClick={() => void submitNote()}
            >
              Add Note
            </button>
          </div>
        ) : null}
        {incident.notes.length ? (
          <dl className="compact-list">
            {incident.notes.map((item) => (
              <div key={item.id}>
                <dt>{formatDate(item.created_at)}</dt>
                <dd>{item.content}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="body-copy">No investigation notes have been added.</p>
        )}
      </section>

      <section className="panel panel--full" aria-labelledby="incident-findings-heading">
        <div className="card-header">
          <h2 id="incident-findings-heading">Rule-Based Security Findings</h2>
        </div>
        {incident.findings.length ? (
          <div className="table-wrap table-wrap--compact">
            <table>
              <thead>
                <tr>
                  <th>Severity</th>
                  <th>Title</th>
                  <th>Evidence</th>
                  <th>Remediation</th>
                </tr>
              </thead>
              <tbody>
                {incident.findings.map((finding) => (
                  <tr key={finding.id}>
                    <td>{formatStatusLabel(finding.severity)}</td>
                    <td>{finding.title}</td>
                    <td>{finding.evidence}</td>
                    <td>{finding.remediation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="body-copy">No findings are linked to this incident.</p>
        )}
      </section>
    </section>
  );
}

function allowedTargets(status: IncidentStatus): IncidentStatus[] {
  if (status === "open") {
    return ["investigating", "false_positive"];
  }
  if (status === "investigating") {
    return ["resolved", "false_positive"];
  }
  return ["investigating"];
}

function actionLabel(status: IncidentStatus): string {
  if (status === "investigating") {
    return "Start Investigating";
  }
  if (status === "resolved") {
    return "Resolve";
  }
  return "Mark False Positive";
}

function incidentTone(status: string): "good" | "pending" | "blocked" {
  if (status === "resolved" || status === "false_positive") {
    return "good";
  }
  if (status === "investigating") {
    return "pending";
  }
  return "blocked";
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}
