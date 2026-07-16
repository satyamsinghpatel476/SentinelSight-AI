import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ApiError, listIncidents, type Incident } from "../api/client";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import { formatStatusLabel } from "../utils/format";

export function IncidentsPage() {
  const { user, loading: authLoading } = useAuth();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading) {
      return;
    }
    if (!user) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    async function loadIncidents() {
      setLoading(true);
      setError(null);
      try {
        const response = await listIncidents();
        if (!cancelled) {
          setIncidents(response);
        }
      } catch (caughtError) {
        if (!cancelled) {
          const message =
            caughtError instanceof ApiError ? caughtError.message : "Unable to load incidents.";
          setError(message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadIncidents();
    return () => {
      cancelled = true;
    };
  }, [authLoading, user]);

  if (!authLoading && !user) {
    return (
      <section className="page-section page-section--narrow">
        <div className="empty-state">
          <h1>Sign in required</h1>
          <p>Incidents are visible only to authenticated organization members.</p>
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
        <p className="body-copy">Loading incidents.</p>
      </section>
    );
  }

  return (
    <section className="page-section" aria-labelledby="incidents-heading">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Incident Response</p>
          <h1 id="incidents-heading">Incidents</h1>
          <p className="page-description">
            Automatically created from deterministic scan evidence when risk crosses the
            configured threshold.
          </p>
        </div>
      </div>

      {error ? (
        <div className="alert" role="alert">
          <strong>Incidents unavailable.</strong>
          <span>{error}</span>
        </div>
      ) : null}

      {incidents.length ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Incident</th>
                <th>Website</th>
                <th>Severity</th>
                <th>Risk</th>
                <th>Status</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {incidents.map((incident) => (
                <tr key={incident.id}>
                  <td>
                    <Link to={`/incidents/${incident.id}`}>{incident.title}</Link>
                  </td>
                  <td>{incident.website_asset?.name ?? incident.website_asset_id}</td>
                  <td>{formatStatusLabel(incident.severity)}</td>
                  <td>{incident.risk_score}</td>
                  <td>
                    <StatusBadge
                      label={formatStatusLabel(incident.status)}
                      tone={incidentTone(incident.status)}
                    />
                  </td>
                  <td>{formatDate(incident.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">
          <h2>No incidents</h2>
          <p>Comparison scans have not generated any investigation records yet.</p>
        </div>
      )}
    </section>
  );
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
