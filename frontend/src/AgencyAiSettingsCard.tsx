import { FormEvent, useEffect, useState } from "react";
import {
  clearAgencyGeminiApiKey,
  fetchAgencyAiSettings,
  fetchAgencyAiStatus,
  saveAgencyGeminiApiKey,
  type AgencyAiSettings,
  type AgencyAiStatus,
} from "./agencySettingsApi";

const GEMINI_KEY_HELP_URL = "https://aistudio.google.com/apikey";

export default function AgencyAiSettingsCard() {
  const [aiStatus, setAiStatus] = useState<AgencyAiStatus | null>(null);
  const [aiSettings, setAiSettings] = useState<AgencyAiSettings | null>(null);
  const [apiKeyDraft, setApiKeyDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const status = await fetchAgencyAiStatus();
        if (cancelled) {
          return;
        }
        setAiStatus(status);
        if (status.uses_tenant_key && status.can_manage) {
          const settings = await fetchAgencyAiSettings();
          if (!cancelled) {
            setAiSettings(settings);
          }
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Unable to load AI settings.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <section className="card section-card">
        <header className="section-card-header">
          <div>
            <h3>AI (Gemini)</h3>
            <p className="muted">Loading AI configuration…</p>
          </div>
        </header>
      </section>
    );
  }

  if (!aiStatus?.uses_tenant_key) {
    return null;
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving || !apiKeyDraft.trim()) {
      return;
    }

    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const updated = await saveAgencyGeminiApiKey(apiKeyDraft.trim());
      setAiSettings(updated);
      setAiStatus((current) => (current ? { ...current, configured: updated.configured } : current));
      setApiKeyDraft("");
      setSuccess("Gemini API key saved. The key is stored securely and cannot be viewed again.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to save Gemini API key.");
    } finally {
      setSaving(false);
    }
  }

  async function handleRemove() {
    if (removing || !aiSettings?.configured) {
      return;
    }
    if (!window.confirm("Remove the stored Gemini API key? AI features will stop working until a new key is saved.")) {
      return;
    }

    setRemoving(true);
    setError("");
    setSuccess("");
    try {
      const updated = await clearAgencyGeminiApiKey();
      setAiSettings(updated);
      setAiStatus((current) => (current ? { ...current, configured: false } : current));
      setApiKeyDraft("");
      setSuccess("Gemini API key removed.");
    } catch (removeError) {
      setError(removeError instanceof Error ? removeError.message : "Unable to remove Gemini API key.");
    } finally {
      setRemoving(false);
    }
  }

  const configured = aiSettings?.configured ?? aiStatus.configured;

  return (
    <section className="card section-card agency-ai-settings-card">
      <header className="section-card-header">
        <div>
          <h3>AI (Gemini)</h3>
          <p className="muted">
            One Gemini API key powers AI for your entire agency — research extraction, communication drafts, and
            summaries.
          </p>
        </div>
      </header>
      <div className="section-card-body agency-ai-settings-body">
        {error ? <p className="status error">{error}</p> : null}
        {success ? <p className="status success">{success}</p> : null}

        <div className="agency-ai-settings-instructions">
          <h4>How to get a Gemini API key</h4>
          <ol>
            <li>
              Sign in with a Google account at{" "}
              <a href={GEMINI_KEY_HELP_URL} target="_blank" rel="noreferrer">
                Google AI Studio
              </a>
              .
            </li>
            <li>Open <strong>Get API key</strong> and create a key for your agency&apos;s Google Cloud project.</li>
            <li>Copy the key once — after you save it here, SailsPipeline will never show it again.</li>
            <li>Paste the key below and save. All agents on your agency will use this key for built-in AI tasks.</li>
          </ol>
        </div>

        {configured ? (
          <p className="agency-ai-settings-configured-note">
            A Gemini API key is stored for your agency. To replace it, paste a new key below and save. To disable AI,
            remove the key.
          </p>
        ) : (
          <p className="status warning agency-ai-settings-missing-note">
            No Gemini API key is stored yet. AI features stay disabled until you save a key.
          </p>
        )}

        {aiStatus.can_manage ? (
          <form className="agency-ai-settings-form" onSubmit={(event) => void handleSave(event)}>
            <label>
              Gemini API key
              <input
                type="password"
                value={apiKeyDraft}
                onChange={(event) => setApiKeyDraft(event.target.value)}
                placeholder={configured ? "Paste a new key to replace the stored key" : "Paste your Gemini API key"}
                autoComplete="off"
                spellCheck={false}
                minLength={20}
                required={!configured}
              />
            </label>
            <div className="agency-ai-settings-actions">
              <button type="submit" className="modal-primary" disabled={saving || !apiKeyDraft.trim()}>
                {saving ? "Saving…" : configured ? "Replace API key" : "Save API key"}
              </button>
              {configured ? (
                <button type="button" className="modal-secondary" disabled={removing} onClick={() => void handleRemove()}>
                  {removing ? "Removing…" : "Remove API key"}
                </button>
              ) : null}
            </div>
          </form>
        ) : (
          <p className="muted">Only your agency owner can add or change the Gemini API key.</p>
        )}
      </div>
    </section>
  );
}
