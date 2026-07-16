import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError, createWebsite, type WebsiteRiskCategory } from "../api/client";
import { useAuth } from "../hooks/useAuth";

const riskCategories: WebsiteRiskCategory[] = ["low", "moderate", "high", "critical"];

export function AddWebsitePage() {
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [riskCategory, setRiskCategory] = useState<WebsiteRiskCategory>("moderate");
  const [monitoringEnabled, setMonitoringEnabled] = useState(true);
  const [authorizationConfirmed, setAuthorizationConfirmed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const isAdmin = user?.role === "administrator";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const asset = await createWebsite({
        name,
        url,
        contact_email: contactEmail,
        risk_category: riskCategory,
        monitoring_enabled: monitoringEnabled,
        authorization_confirmed: authorizationConfirmed
      });
      navigate(`/websites/${asset.id}`, { replace: true });
    } catch (caughtError) {
      const message =
        caughtError instanceof ApiError ? caughtError.message : "Unable to add website.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  if (!authLoading && !user) {
    return (
      <section className="page-section page-section--narrow">
        <div className="empty-state">
          <h1>Sign in required</h1>
          <p>Only administrators can add website assets.</p>
          <Link className="button" to="/login">
            Sign in
          </Link>
        </div>
      </section>
    );
  }

  if (!authLoading && !isAdmin) {
    return (
      <section className="page-section page-section--narrow">
        <div className="empty-state">
          <h1>Administrator access required</h1>
          <p>Your role can view website assets but cannot register new ones.</p>
          <Link className="button" to="/websites">
            View websites
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section className="page-section page-section--narrow" aria-labelledby="add-website-heading">
      <p className="eyebrow">Assets</p>
      <h1 id="add-website-heading">Add Website</h1>
      <p className="page-description">
        Register only public websites your organization owns or is explicitly authorized to monitor.
      </p>

      <form className="form-panel" onSubmit={(event) => void handleSubmit(event)}>
        <label>
          <span>Website name</span>
          <input required value={name} onChange={(event) => setName(event.target.value)} />
        </label>

        <label>
          <span>Public URL</span>
          <input
            required
            inputMode="url"
            placeholder="https://example.com"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
          />
        </label>

        <label>
          <span>Contact email</span>
          <input
            required
            type="email"
            value={contactEmail}
            onChange={(event) => setContactEmail(event.target.value)}
          />
        </label>

        <label>
          <span>Risk category</span>
          <select
            value={riskCategory}
            onChange={(event) => setRiskCategory(event.target.value as WebsiteRiskCategory)}
          >
            {riskCategories.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
        </label>

        <label className="checkbox-row">
          <input
            checked={monitoringEnabled}
            type="checkbox"
            onChange={(event) => setMonitoringEnabled(event.target.checked)}
          />
          <span>Monitoring enabled</span>
        </label>

        <label className="checkbox-row">
          <input
            checked={authorizationConfirmed}
            required
            type="checkbox"
            onChange={(event) => setAuthorizationConfirmed(event.target.checked)}
          />
          <span>I confirm that I own this website or have authorization to monitor it.</span>
        </label>

        {error ? (
          <div className="alert" role="alert">
            <strong>Could not add website.</strong>
            <span>{error}</span>
          </div>
        ) : null}

        <button className="button" disabled={submitting || !authorizationConfirmed} type="submit">
          {submitting ? "Adding website" : "Add website"}
        </button>
      </form>
    </section>
  );
}
