import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  ApiError,
  generateIncidentAIAnalysis,
  generateScanAIAnalysis,
  getAIStatus,
  getIncidentAIAnalysis,
  getScanAIAnalysis,
  type AIAnalysis,
  type AIStatus
} from "../api/client";
import { formatStatusLabel } from "../utils/format";
import { StatusBadge } from "./StatusBadge";

type AIAnalysisCardProps = {
  subjectId: string;
  subjectType: "scan" | "incident";
  canGenerate: boolean;
  completed: boolean;
};

export function AIAnalysisCard({
  subjectId,
  subjectType,
  canGenerate,
  completed
}: AIAnalysisCardProps) {
  const [status, setStatus] = useState<AIStatus | null>(null);
  const [analysis, setAnalysis] = useState<AIAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadAIState() {
      setLoading(true);
      setError(null);
      try {
        const [statusResponse, analysisResponse] = await Promise.all([
          getAIStatus(),
          subjectType === "scan"
            ? getScanAIAnalysis(subjectId)
            : getIncidentAIAnalysis(subjectId)
        ]);
        if (!cancelled) {
          setStatus(statusResponse);
          setAnalysis(analysisResponse);
        }
      } catch (caughtError) {
        if (!cancelled) {
          const message =
            caughtError instanceof ApiError ? caughtError.message : "Unable to load AI analysis.";
          setError(message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadAIState();
    return () => {
      cancelled = true;
    };
  }, [subjectId, subjectType]);

  async function generateAnalysis() {
    setBusy(true);
    setError(null);
    try {
      const response =
        subjectType === "scan"
          ? await generateScanAIAnalysis(subjectId)
          : await generateIncidentAIAnalysis(subjectId);
      setAnalysis(response);
    } catch (caughtError) {
      const message =
        caughtError instanceof ApiError ? caughtError.message : "Unable to generate AI analysis.";
      setError(message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel panel--full" aria-labelledby={`ai-${subjectType}-heading`}>
      <div className="card-header">
        <h2 id={`ai-${subjectType}-heading`}>AI Incident Analysis</h2>
        {analysis ? (
          <StatusBadge
            label={formatStatusLabel(analysis.status)}
            tone={analysis.status === "completed" ? "good" : analysis.status === "failed" ? "blocked" : "pending"}
          />
        ) : null}
      </div>

      {loading ? <p className="body-copy">Loading AI analysis state.</p> : null}

      {!loading && status && !status.is_configured ? (
        <p className="body-copy">
          AI provider is not configured. An Administrator can configure BYOK settings in{" "}
          <Link to="/settings/ai">AI Configuration</Link>.
        </p>
      ) : null}

      {!loading && status?.is_configured && !status.is_enabled ? (
        <p className="body-copy">
          AI analysis is disabled. Deterministic findings and remediation remain available.
        </p>
      ) : null}

      {!loading && status?.is_configured && status.is_enabled && !status.has_api_key ? (
        <p className="body-copy">
          AI provider API key is not configured. Deterministic findings and remediation remain
          available.
        </p>
      ) : null}

      {status?.provider && status.model ? (
        <dl className="compact-list">
          <div>
            <dt>Configured provider</dt>
            <dd>{providerLabel(status.provider)}</dd>
          </div>
          <div>
            <dt>Configured model</dt>
            <dd>{status.model}</dd>
          </div>
        </dl>
      ) : null}

      {analysis ? <AnalysisResult analysis={analysis} /> : null}

      {error ? (
        <div className="alert" role="alert">
          <strong>AI analysis unavailable.</strong>
          <span>{error}</span>
        </div>
      ) : null}

      {canGenerate && completed && status?.is_configured && status.is_enabled && status.has_api_key ? (
        <div className="action-row">
          <p className="body-copy cost-warning">
            This action sends structured security findings to the selected AI provider and may
            consume API quota.
          </p>
          <button
            className="button"
            type="button"
            disabled={busy}
            onClick={() => void generateAnalysis()}
          >
            {busy ? "Generating" : "Generate AI Analysis"}
          </button>
        </div>
      ) : null}

      {!completed ? (
        <p className="body-copy">AI analysis requires a completed scan.</p>
      ) : null}
    </section>
  );
}

function AnalysisResult({ analysis }: { analysis: AIAnalysis }) {
  if (analysis.status === "failed") {
    return (
      <div className="alert" role="alert">
        <strong>AI analysis failed safely.</strong>
        <span>{analysis.error_message ?? "The provider did not return valid analysis."}</span>
      </div>
    );
  }

  if (analysis.status !== "completed") {
    return <p className="body-copy">AI analysis is pending.</p>;
  }

  return (
    <div className="ai-result">
      <dl className="compact-list">
        <div>
          <dt>Provider and model used</dt>
          <dd>
            {providerLabel(analysis.provider)} / {analysis.model}
          </dd>
        </div>
        <div>
          <dt>Generated</dt>
          <dd>{analysis.completed_at ? formatDate(analysis.completed_at) : "Not available"}</dd>
        </div>
        <div>
          <dt>Incident summary</dt>
          <dd>{analysis.incident_summary}</dd>
        </div>
        <div>
          <dt>Priority explanation</dt>
          <dd>{analysis.priority_explanation}</dd>
        </div>
        <div>
          <dt>Confidence note</dt>
          <dd>{analysis.confidence_note}</dd>
        </div>
      </dl>
      <ActionList title="Immediate actions" items={analysis.immediate_actions} />
      <ActionList title="Long-term actions" items={analysis.long_term_actions} />
      <ActionList
        title="Possible false-positive factors"
        items={analysis.possible_false_positive_factors}
      />
    </div>
  );
}

function ActionList({ title, items }: { title: string; items: string[] | null }) {
  if (!items?.length) {
    return null;
  }
  return (
    <div className="ai-action-list">
      <h3>{title}</h3>
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function providerLabel(provider: string): string {
  if (provider === "openai_compatible") {
    return "OpenAI-compatible";
  }
  return formatStatusLabel(provider);
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}
