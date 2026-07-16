import { Link } from "react-router-dom";

import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import { useHealthCheck } from "../hooks/useHealthCheck";
import { formatStatusLabel } from "../utils/format";

export function FoundationPage() {
  const { health, readiness, loading, error, refresh } = useHealthCheck();
  const { user, loading: authLoading } = useAuth();

  const apiTone = error ? "blocked" : loading ? "pending" : "good";
  const apiLabel = error ? "Unavailable" : loading ? "Checking" : "Online";
  const authTone = user ? "good" : authLoading ? "pending" : "blocked";
  const authLabel = user ? "Signed in" : authLoading ? "Checking" : "Signed out";

  return (
    <section className="page-section" aria-labelledby="foundation-heading">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Milestone 1</p>
          <h1 id="foundation-heading">Project Foundation</h1>
          <p className="page-description">
            Backend, frontend, database configuration and container wiring are being verified
            before security workflows are added.
          </p>
        </div>
        <button className="button" type="button" onClick={() => void refresh()}>
          Refresh
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
            <h2>Database Readiness</h2>
            <StatusBadge
              label={readiness?.status === "ready" ? "Ready" : loading ? "Checking" : "Blocked"}
              tone={readiness?.status === "ready" ? "good" : loading ? "pending" : "blocked"}
            />
          </div>
          <p className="body-copy">
            The readiness endpoint performs a minimal database connectivity check.
          </p>
        </article>

        <article className="status-card">
          <div className="card-header">
            <h2>Authentication</h2>
            <StatusBadge label={authLabel} tone={authTone} />
          </div>
          {user ? (
            <dl>
              <div>
                <dt>User</dt>
                <dd>{user.email}</dd>
              </div>
              <div>
                <dt>Role</dt>
                <dd>{formatStatusLabel(user.role)}</dd>
              </div>
            </dl>
          ) : (
            <p className="body-copy">
              Sign in to use role-protected workflows as they are added.
            </p>
          )}
        </article>

        <article className="status-card">
          <div className="card-header">
            <h2>Scanner Status</h2>
            <StatusBadge label="Not implemented" tone="pending" />
          </div>
          <p className="body-copy">
            Scanner, baseline and incident workflows will appear after their backend milestones are
            complete.
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

      {error ? (
        <div className="alert" role="alert">
          <strong>Backend check failed.</strong>
          <span>{error}</span>
        </div>
      ) : null}
    </section>
  );
}
