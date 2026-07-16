import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  ApiError,
  listAuditLogs,
  verifyAuditChain,
  type AuditLog,
  type AuditVerification
} from "../api/client";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";

export function AuditPage() {
  const { user, loading: authLoading } = useAuth();
  const [records, setRecords] = useState<AuditLog[]>([]);
  const [verification, setVerification] = useState<AuditVerification | null>(null);
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
    async function loadAudit() {
      setLoading(true);
      setError(null);
      try {
        const [logResponse, verificationResponse] = await Promise.all([
          listAuditLogs(),
          verifyAuditChain()
        ]);
        if (!cancelled) {
          setRecords(logResponse);
          setVerification(verificationResponse);
        }
      } catch (caughtError) {
        if (!cancelled) {
          const message =
            caughtError instanceof ApiError ? caughtError.message : "Unable to load audit trail.";
          setError(message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadAudit();
    return () => {
      cancelled = true;
    };
  }, [authLoading, user]);

  if (!authLoading && !user) {
    return (
      <section className="page-section page-section--narrow">
        <div className="empty-state">
          <h1>Sign in required</h1>
          <p>The audit trail is visible only to authenticated organization members.</p>
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
        <p className="body-copy">Loading audit trail.</p>
      </section>
    );
  }

  return (
    <section className="page-section" aria-labelledby="audit-heading">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Tamper-Evident Audit</p>
          <h1 id="audit-heading">Hash-Chained Audit Trail</h1>
          <p className="page-description">
            Organization-scoped event records with deterministic hash-chain verification.
          </p>
        </div>
        {verification ? (
          <StatusBadge
            label={
              verification.valid
                ? `Valid: ${verification.records_checked}`
                : `Broken at ${verification.first_broken_record_id ?? "unknown"}`
            }
            tone={verification.valid ? "good" : "blocked"}
          />
        ) : null}
      </div>

      {error ? (
        <div className="alert" role="alert">
          <strong>Audit unavailable.</strong>
          <span>{error}</span>
        </div>
      ) : null}

      {records.length ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>User</th>
                <th>Action</th>
                <th>Resource</th>
                <th>Hash Prefix</th>
              </tr>
            </thead>
            <tbody>
              {records.map((record) => (
                <tr key={record.id}>
                  <td>{formatDate(record.created_at)}</td>
                  <td>{record.user_id}</td>
                  <td>{record.action}</td>
                  <td>
                    {record.resource_type}:{record.resource_id}
                  </td>
                  <td>{record.entry_hash.slice(0, 16)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">
          <h2>No audit records</h2>
          <p>Events will appear after login, scans, baselines and incident actions.</p>
        </div>
      )}
    </section>
  );
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}
