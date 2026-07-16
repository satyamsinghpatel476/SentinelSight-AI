import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  ApiError,
  deactivateWebsite,
  getWebsite,
  updateWebsite,
  type WebsiteAsset
} from "../api/client";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import { formatStatusLabel } from "../utils/format";

export function WebsiteDetailPage() {
  const { websiteId } = useParams();
  const { user, loading: authLoading } = useAuth();
  const [asset, setAsset] = useState<WebsiteAsset | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const isAdmin = user?.role === "administrator";

  useEffect(() => {
    if (authLoading || !websiteId) {
      return;
    }
    if (!user) {
      setLoading(false);
      return;
    }

    const id = websiteId;
    let cancelled = false;
    async function loadAsset() {
      setLoading(true);
      setError(null);
      try {
        const response = await getWebsite(id);
        if (!cancelled) {
          setAsset(response);
        }
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

    void loadAsset();
    return () => {
      cancelled = true;
    };
  }, [authLoading, user, websiteId]);

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
          <p className="body-copy">Authorization confirmed: {asset.authorization_confirmed ? "Yes" : "No"}</p>
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
            <h2>Baseline</h2>
            <StatusBadge label="Not created" tone="pending" />
          </div>
          <p className="body-copy">Baseline approval arrives in the next milestone group.</p>
        </article>

        <article className="status-card">
          <div className="card-header">
            <h2>Scanning</h2>
            <StatusBadge label="Not implemented" tone="pending" />
          </div>
          <p className="body-copy">Safe scanner endpoints are not available yet.</p>
        </article>
      </div>

      {isAdmin ? (
        <div className="action-row">
          <button className="button" type="button" onClick={() => void toggleMonitoring()}>
            {asset.monitoring_enabled ? "Disable monitoring" : "Enable monitoring"}
          </button>
          <button className="button button--secondary" type="button" onClick={() => void deactivate()}>
            Deactivate
          </button>
        </div>
      ) : null}

      {actionError ? (
        <div className="alert" role="alert">
          <strong>Action failed.</strong>
          <span>{actionError}</span>
        </div>
      ) : null}
    </section>
  );
}
