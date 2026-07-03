import { ChangeEvent, FormEvent, useCallback, useEffect, useState } from "react";
import {
  fetchAgencySettings,
  updateAgencySettings,
  uploadAgencyLogo,
  uploadAgencySignatureImage,
  type AgencySettings,
} from "./agencySettingsApi";
import { contrastTextColor, resolveBrandLogoUrl } from "./portalBranding";
import RichTextEditor from "./RichTextEditor";
import "./portal-branding.css";

type SettingsDraft = {
  agency_name: string;
  primary_color: string;
  secondary_color: string;
  custom_master_tc: string;
  email_signature_block: string;
  business_address: string;
  business_phone: string;
};

function settingsToDraft(settings: AgencySettings): SettingsDraft {
  return {
    agency_name: settings.agency_name,
    primary_color: settings.primary_color,
    secondary_color: settings.secondary_color,
    custom_master_tc: settings.custom_master_tc ?? "",
    email_signature_block: settings.email_signature_block ?? "",
    business_address: settings.business_address ?? "",
    business_phone: settings.business_phone ?? "",
  };
}

function buildSettingsPayload(original: AgencySettings, draft: SettingsDraft) {
  const payload: Record<string, string | null> = {};
  const fields: (keyof SettingsDraft)[] = [
    "agency_name",
    "primary_color",
    "secondary_color",
    "custom_master_tc",
    "email_signature_block",
    "business_address",
    "business_phone",
  ];

  for (const field of fields) {
    const nextValue = draft[field].trim();
    const previousValue = (original[field as keyof AgencySettings] ?? "").toString().trim();
    if (nextValue !== previousValue) {
      payload[field] = nextValue || null;
    }
  }
  return Object.keys(payload).length > 0 ? payload : null;
}

export default function AgencySettingsPage({
  onBrandingUpdated,
}: {
  onBrandingUpdated?: () => void;
}) {
  const [settings, setSettings] = useState<AgencySettings | null>(null);
  const [draft, setDraft] = useState<SettingsDraft | null>(null);
  const [logoPreviewUrl, setLogoPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadSettings = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const nextSettings = await fetchAgencySettings();
      setSettings(nextSettings);
      setDraft(settingsToDraft(nextSettings));
      setLogoPreviewUrl(resolveBrandLogoUrl(nextSettings.brand_logo_url));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load agency settings.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSettings();
  }, [loadSettings]);

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!settings || !draft || saving) {
      return;
    }

    const payload = buildSettingsPayload(settings, draft);
    if (!payload) {
      setSuccess("No changes to save.");
      return;
    }

    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const updated = await updateAgencySettings(payload);
      setSettings(updated);
      setDraft(settingsToDraft(updated));
      setSuccess("Agency settings saved.");
      onBrandingUpdated?.();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to save agency settings.");
    } finally {
      setSaving(false);
    }
  }

  async function handleLogoChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    setUploadingLogo(true);
    setError("");
    setSuccess("");
    const localPreview = URL.createObjectURL(file);
    setLogoPreviewUrl(localPreview);

    try {
      const result = await uploadAgencyLogo(file);
      const updated = await fetchAgencySettings();
      setSettings(updated);
      setDraft(settingsToDraft(updated));
      setLogoPreviewUrl(resolveBrandLogoUrl(result.brand_logo_url));
      setSuccess("Brand logo uploaded.");
      onBrandingUpdated?.();
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Unable to upload brand logo.");
      if (settings) {
        setLogoPreviewUrl(resolveBrandLogoUrl(settings.brand_logo_url));
      }
    } finally {
      URL.revokeObjectURL(localPreview);
      setUploadingLogo(false);
      event.target.value = "";
    }
  }

  const primaryPreviewText = draft ? contrastTextColor(draft.primary_color) : "#ffffff";
  const secondaryPreviewText = draft ? contrastTextColor(draft.secondary_color) : "#ffffff";

  return (
    <div className="agency-settings-page">
      <section className="card section-card agency-settings-hero">
        <header className="section-card-header">
          <div>
            <h2>Agency Settings</h2>
            <p className="muted">
              White-label branding, corporate contact details, communications, and your Master Terms vault.
            </p>
          </div>
        </header>
      </section>

      {loading ? (
        <section className="card section-card">
          <div className="section-card-body">
            <p className="muted">Loading agency settings…</p>
          </div>
        </section>
      ) : null}

      {error ? <p className="status error agency-settings-status">{error}</p> : null}
      {success ? <p className="status success agency-settings-status">{success}</p> : null}

      {!loading && settings && draft ? (
        <form className="agency-settings-form" onSubmit={(event) => void handleSave(event)}>
          <section className="card section-card">
            <header className="section-card-header">
              <div>
                <h3>Brand identity</h3>
                <p className="muted">Agency display name and logo shown on client portals.</p>
              </div>
            </header>
            <div className="section-card-body agency-settings-brand-grid">
              <label>
                Agency name
                <input
                  type="text"
                  value={draft.agency_name}
                  onChange={(event) => setDraft((current) => current && { ...current, agency_name: event.target.value })}
                  maxLength={255}
                  required
                />
              </label>

              <div className="agency-settings-logo-block">
                <span className="agency-settings-field-label">Brand logo</span>
                <div className="agency-settings-logo-preview portal-branding-accent-border">
                  {logoPreviewUrl ? (
                    <img src={logoPreviewUrl} alt={`${draft.agency_name} logo preview`} />
                  ) : (
                    <p className="muted">No logo uploaded</p>
                  )}
                </div>
                <label className="agency-settings-upload-button">
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/gif,image/webp,image/svg+xml"
                    onChange={(event) => void handleLogoChange(event)}
                    disabled={uploadingLogo}
                  />
                  {uploadingLogo ? "Uploading…" : "Upload Brand Logo"}
                </label>
              </div>
            </div>
          </section>

          <section className="card section-card">
            <header className="section-card-header">
              <div>
                <h3>Theme customization</h3>
                <p className="muted">Accent colors for portal headers and primary actions. Canvas stays neutral.</p>
              </div>
            </header>
            <div className="section-card-body agency-settings-theme-grid">
              <label>
                Primary color
                <div className="agency-settings-color-row">
                  <input
                    type="color"
                    value={draft.primary_color}
                    onChange={(event) =>
                      setDraft((current) => current && { ...current, primary_color: event.target.value })
                    }
                  />
                  <input
                    type="text"
                    value={draft.primary_color}
                    onChange={(event) =>
                      setDraft((current) => current && { ...current, primary_color: event.target.value })
                    }
                    pattern="^#[0-9A-Fa-f]{6}$"
                    maxLength={7}
                  />
                  <span
                    className="agency-settings-swatch"
                    style={{ background: draft.primary_color, color: primaryPreviewText }}
                  >
                    Primary
                  </span>
                </div>
              </label>

              <label>
                Secondary color
                <div className="agency-settings-color-row">
                  <input
                    type="color"
                    value={draft.secondary_color}
                    onChange={(event) =>
                      setDraft((current) => current && { ...current, secondary_color: event.target.value })
                    }
                  />
                  <input
                    type="text"
                    value={draft.secondary_color}
                    onChange={(event) =>
                      setDraft((current) => current && { ...current, secondary_color: event.target.value })
                    }
                    pattern="^#[0-9A-Fa-f]{6}$"
                    maxLength={7}
                  />
                  <span
                    className="agency-settings-swatch"
                    style={{ background: draft.secondary_color, color: secondaryPreviewText }}
                  >
                    Secondary
                  </span>
                </div>
              </label>
            </div>
          </section>

          <section className="card section-card">
            <header className="section-card-header">
              <div>
                <h3>Corporate contact details</h3>
                <p className="muted">Centralized address and phone for portals, emails, and team reference.</p>
              </div>
            </header>
            <div className="section-card-body agency-settings-contact-grid">
              <label>
                Business address
                <textarea
                  value={draft.business_address}
                  onChange={(event) =>
                    setDraft((current) => current && { ...current, business_address: event.target.value })
                  }
                  rows={3}
                  maxLength={512}
                  placeholder="Street, city, state, postal code, country"
                />
              </label>
              <label>
                Business phone
                <input
                  type="tel"
                  value={draft.business_phone}
                  onChange={(event) =>
                    setDraft((current) => current && { ...current, business_phone: event.target.value })
                  }
                  maxLength={50}
                  placeholder="(555) 555-0100"
                />
              </label>
            </div>
          </section>

          <section className="card section-card">
            <header className="section-card-header">
              <div>
                <h3>Communications</h3>
                <p className="muted">Email signature block appended to outbound agency correspondence.</p>
              </div>
            </header>
            <div className="section-card-body">
              <div className="agency-settings-full-width agency-settings-rich-text-field">
                <span className="agency-settings-field-label">Email signature block</span>
                <RichTextEditor
                  value={draft.email_signature_block}
                  onChange={(html) =>
                    setDraft((current) => current && { ...current, email_signature_block: html })
                  }
                  uploadImage={async (file) => {
                    const result = await uploadAgencySignatureImage(file);
                    return result.image_url;
                  }}
                  placeholder="Kind regards, your name, agency name, phone, and logo…"
                  disabled={saving || uploadingLogo}
                  minHeight="12rem"
                  ariaLabel="Email signature block"
                />
                <p className="muted agency-settings-rich-text-hint">
                  Images are uploaded to secure agency storage (not embedded), so large signatures save reliably.
                </p>
              </div>
            </div>
          </section>

          <section className="card section-card">
            <header className="section-card-header">
              <div>
                <h3>Legal compliance vault</h3>
                <p className="muted">Master Terms &amp; Conditions boilerplate served on the client acceptance portal.</p>
              </div>
            </header>
            <div className="section-card-body">
              <label className="agency-settings-full-width">
                Master Terms &amp; Conditions
                <textarea
                  className="agency-settings-legal-textarea"
                  value={draft.custom_master_tc}
                  onChange={(event) =>
                    setDraft((current) => current && { ...current, custom_master_tc: event.target.value })
                  }
                  rows={18}
                  required
                />
              </label>
            </div>
          </section>

          <div className="agency-settings-actions">
            <button type="submit" disabled={saving || uploadingLogo}>
              {saving ? "Saving…" : "Save agency settings"}
            </button>
          </div>
        </form>
      ) : null}
    </div>
  );
}
