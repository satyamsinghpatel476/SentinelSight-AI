import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  ApiError,
  getAIConfig,
  removeAIKey,
  saveAIConfig,
  testAIConfig,
  type AIConfiguration,
  type AIProvider
} from "../api/client";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";

const PROVIDERS: Array<{ value: AIProvider; label: string }> = [
  { value: "gemini", label: "Gemini" },
  { value: "openai", label: "OpenAI" },
  { value: "openai_compatible", label: "OpenAI-compatible" }
];

export function AISettingsPage() {
  const { user, loading: authLoading } = useAuth();
  const [config, setConfig] = useState<AIConfiguration | null>(null);
  const [provider, setProvider] = useState<AIProvider>("gemini");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [enabled, setEnabled] = useState(false);
  const [timeoutSeconds, setTimeoutSeconds] = useState(20);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading) {
      return;
    }
    if (!user || user.role !== "administrator") {
      setLoading(false);
      return;
    }

    let cancelled = false;
    async function loadConfig() {
      setLoading(true);
      setError(null);
      try {
        const response = await getAIConfig();
        if (!cancelled) {
          applyConfig(response);
        }
      } catch (caughtError) {
        if (!cancelled) {
          const errorMessage =
            caughtError instanceof ApiError ? caughtError.message : "Unable to load AI settings.";
          setError(errorMessage);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadConfig();
    return () => {
      cancelled = true;
    };
  }, [authLoading, user]);

  function applyConfig(nextConfig: AIConfiguration) {
    setConfig(nextConfig);
    setProvider(nextConfig.provider ?? "gemini");
    setModel(nextConfig.model ?? "");
    setBaseUrl(nextConfig.base_url ?? "");
    setEnabled(nextConfig.is_enabled);
    setTimeoutSeconds(nextConfig.timeout_seconds);
    setApiKey("");
  }

  function payload() {
    return {
      provider,
      model: model.trim() || null,
      api_key: apiKey.trim() || null,
      base_url: provider === "openai_compatible" ? baseUrl.trim() || null : null,
      is_enabled: enabled,
      timeout_seconds: timeoutSeconds
    };
  }

  async function saveSettings() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const response = await saveAIConfig(payload());
      applyConfig(response);
      setMessage("AI configuration saved.");
    } catch (caughtError) {
      const errorMessage =
        caughtError instanceof ApiError ? caughtError.message : "Unable to save AI settings.";
      setError(errorMessage);
    } finally {
      setBusy(false);
    }
  }

  async function testSettings() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const response = await testAIConfig(payload());
      if (response.success) {
        setMessage(`Connection succeeded for ${response.provider ?? "provider"} / ${response.model ?? "model"}.`);
      } else {
        setError(response.message);
      }
    } catch (caughtError) {
      const errorMessage =
        caughtError instanceof ApiError ? caughtError.message : "Unable to test AI provider.";
      setError(errorMessage);
    } finally {
      setBusy(false);
    }
  }

  async function deleteKey() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const response = await removeAIKey();
      applyConfig(response);
      setMessage("API key removed.");
    } catch (caughtError) {
      const errorMessage =
        caughtError instanceof ApiError ? caughtError.message : "Unable to remove API key.";
      setError(errorMessage);
    } finally {
      setBusy(false);
    }
  }

  if (!authLoading && !user) {
    return (
      <section className="page-section page-section--narrow">
        <div className="empty-state">
          <h1>Sign in required</h1>
          <p>AI configuration is visible only to Administrators.</p>
          <Link className="button" to="/login">
            Sign in
          </Link>
        </div>
      </section>
    );
  }

  if (!authLoading && user && user.role !== "administrator") {
    return (
      <section className="page-section page-section--narrow">
        <div className="empty-state">
          <h1>Administrator access required</h1>
          <p>Only Administrators can view or change organization AI provider settings.</p>
        </div>
      </section>
    );
  }

  if (loading) {
    return (
      <section className="page-section">
        <p className="body-copy">Loading AI configuration.</p>
      </section>
    );
  }

  return (
    <section className="page-section page-section--narrow" aria-labelledby="ai-settings-heading">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Settings</p>
          <h1 id="ai-settings-heading">AI Configuration</h1>
          <p className="page-description">
            Configure Bring Your Own Key provider access for the real AI Incident Analyst.
          </p>
        </div>
      </div>

      {message ? (
        <div className="success-alert" role="status">
          <strong>Saved.</strong>
          <span>{message}</span>
        </div>
      ) : null}
      {error ? (
        <div className="alert" role="alert">
          <strong>Action failed.</strong>
          <span>{error}</span>
        </div>
      ) : null}

      <form className="form-panel" onSubmit={(event) => event.preventDefault()}>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(event) => setEnabled(event.target.checked)}
          />
          <span>AI enabled</span>
        </label>

        <label>
          Provider
          <select
            value={provider}
            onChange={(event) => setProvider(event.target.value as AIProvider)}
          >
            {PROVIDERS.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>

        <label>
          Exact model name/version
          <input
            type="text"
            value={model}
            placeholder="gemini-1.5-flash or gpt-4.1-mini"
            onChange={(event) => setModel(event.target.value)}
          />
        </label>

        {provider === "openai_compatible" ? (
          <label>
            Base URL
            <input
              type="url"
              value={baseUrl}
              placeholder="https://provider.example/v1"
              onChange={(event) => setBaseUrl(event.target.value)}
            />
          </label>
        ) : null}

        <label>
          API key
          <input
            type="password"
            value={apiKey}
            placeholder={config?.has_api_key ? "Leave blank to keep current key" : "Enter API key"}
            autoComplete="new-password"
            onChange={(event) => setApiKey(event.target.value)}
          />
        </label>

        <div className="key-status">
          <StatusBadge
            label={config?.has_api_key ? "Key configured" : "No key"}
            tone={config?.has_api_key ? "good" : "pending"}
          />
          <span>
            {config?.has_api_key && config.api_key_last_four
              ? `API key configured: ••••••••${config.api_key_last_four}`
              : "API key is never returned after saving."}
          </span>
        </div>

        <label>
          Timeout in seconds
          <input
            type="number"
            min={1}
            max={120}
            value={timeoutSeconds}
            onChange={(event) => setTimeoutSeconds(Number(event.target.value))}
          />
        </label>

        <div className="action-row">
          <button className="button" type="button" disabled={busy} onClick={() => void saveSettings()}>
            Save Configuration
          </button>
          <button
            className="button button--secondary"
            type="button"
            disabled={busy}
            onClick={() => void testSettings()}
          >
            Test Connection
          </button>
          <button
            className="button button--secondary"
            type="button"
            disabled={busy || !config?.has_api_key}
            onClick={() => void deleteKey()}
          >
            Remove API Key
          </button>
        </div>
      </form>
    </section>
  );
}
