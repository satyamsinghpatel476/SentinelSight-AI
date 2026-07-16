import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ApiError, listWebsites, type WebsiteAsset } from "../api/client";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import { formatStatusLabel } from "../utils/format";

export function WebsiteAssetsPage() {
  const { user, loading: authLoading } = useAuth();
  const [assets, setAssets] = useState<WebsiteAsset[]>([]);
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
    async function loadAssets() {
      setLoading(true);
      setError(null);
      try {
        const response = await listWebsites();
        if (!cancelled) {
          setAssets(response);
        }
      } catch (caughtError) {
        if (!cancelled) {
          const message =
            caughtError instanceof ApiError ? caughtError.message : "Unable to load websites.";
          setError(message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadAssets();
    return () => {
      cancelled = true;
    };
  }, [authLoading, user]);

  const isAdmin = user?.role === "administrator";

  return (
    <section className="page-section" aria-labelledby="websites-heading">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Assets</p>
          <h1 id="websites-heading">Website Assets</h1>
          <p className="page-description">
            Registered public websites that your organization is authorized to monitor.
          </p>
        </div>
        {isAdmin ? (
          <Link className="button" to="/websites/new">
            Add website
          </Link>
        ) : null}
      </div>

      {!user && !authLoading ? (
        <div className="empty-state">
          <h2>Sign in required</h2>
          <p>Website assets are visible only to authenticated organization members.</p>
          <Link className="button" to="/login">
            Sign in
          </Link>
        </div>
      ) : null}

      {error ? (
        <div className="alert" role="alert">
          <strong>Could not load website assets.</strong>
          <span>{error}</span>
        </div>
      ) : null}

      {user && loading ? <p className="body-copy">Loading website assets.</p> : null}

      {user && !loading && assets.length === 0 ? (
        <div className="empty-state">
          <h2>No websites registered</h2>
          <p>Administrators can add the first authorized public website.</p>
        </div>
      ) : null}

      {assets.length > 0 ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>URL</th>
                <th>Risk</th>
                <th>Monitoring</th>
                <th>Contact</th>
              </tr>
            </thead>
            <tbody>
              {assets.map((asset) => (
                <tr key={asset.id}>
                  <td>
                    <Link to={`/websites/${asset.id}`}>{asset.name}</Link>
                  </td>
                  <td>{asset.normalized_url}</td>
                  <td>{formatStatusLabel(asset.risk_category)}</td>
                  <td>
                    <StatusBadge
                      label={asset.monitoring_enabled ? "Enabled" : "Disabled"}
                      tone={asset.monitoring_enabled ? "good" : "pending"}
                    />
                  </td>
                  <td>{asset.contact_email}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
