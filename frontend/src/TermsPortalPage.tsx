import { FormEvent, useEffect, useState } from "react";
import { acceptMasterTerms, validateTermsToken } from "./termsApi";
import { BRAND_APP_TITLE, BRAND_NAME } from "./branding";
import type { TermsValidateResponse } from "./termsApi";
import "./bridge-portal.css";
import "./terms-portal.css";

type TermsPortalPageProps = {
  token: string;
};

const buildAcceptanceCertification = (agencyName: string) =>
  `By clicking the check box below, I certify that I have read, understood, and accept these Master Terms and Conditions on behalf of myself and all travelers included in my booking parties. I acknowledge and agree that this agreement is permanent and applies to my current booking and all future cruise bookings made through ${agencyName}.`;

function splitTermsParagraphs(text: string): string[] {
  return text
    .split(/\n\s*\n/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);
}

function TermsTextContent({ text }: { text: string }) {
  const paragraphs = splitTermsParagraphs(text);
  const blocks =
    paragraphs.length > 1
      ? paragraphs
      : text
          .split("\n")
          .map((paragraph) => paragraph.trim())
          .filter(Boolean);

  return (
    <div className="terms-portal-text-content">
      {blocks.map((paragraph, index) => (
        <p key={`${index}-${paragraph.slice(0, 24)}`}>{paragraph}</p>
      ))}
    </div>
  );
}

function formatExpiryDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString(undefined, {
    month: "long",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function TermsPortalPage({ token }: TermsPortalPageProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [portal, setPortal] = useState<TermsValidateResponse | null>(null);
  const [acceptedCheckbox, setAcceptedCheckbox] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [completionMessage, setCompletionMessage] = useState("");

  useEffect(() => {
    async function loadPortal() {
      if (!token) {
        setError("This terms acceptance link is missing a secure token.");
        setLoading(false);
        return;
      }

      try {
        const payload = await validateTermsToken(token);
        setPortal(payload);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load terms review details.");
      } finally {
        setLoading(false);
      }
    }

    void loadPortal();
  }, [token]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || completed || !acceptedCheckbox) {
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      const result = await acceptMasterTerms(token);
      setCompleted(true);
      setCompletionMessage(result.message);
      setAcceptedCheckbox(false);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to record terms acceptance.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page auth-page terms-portal-page">
      <section className="card bridge-card terms-portal-card">
        <header className="bridge-card-header terms-portal-header">
          <div className="terms-portal-brand">
            <img src="/sailspipeline-logo.png" alt={BRAND_APP_TITLE} className="auth-logo" />
            <div>
              <h1>Master Terms &amp; Conditions</h1>
              <p className="muted">Secure client portal · {BRAND_NAME}</p>
            </div>
          </div>
        </header>

        <div className="bridge-card-body terms-portal-body">
          {loading ? <p className="muted">Verifying your secure review link…</p> : null}

          {!loading && error && !portal ? (
            <section className="terms-portal-alert terms-portal-alert--error">
              <h2>Link unavailable</h2>
              <p>{error}</p>
              <p className="muted">
                For your security, review links expire after 48 hours. Contact your travel advisor if you need a new
                link.
              </p>
            </section>
          ) : null}

          {!loading && portal && !completed ? (
            <>
              <section className="terms-portal-summary">
                <p className="terms-portal-greeting">
                  Hello <strong>{portal.passenger_name}</strong>,
                </p>
                <p>
                  {portal.agency_name} requires your one-time acceptance of our Master Terms &amp; Conditions before we
                  continue with your cruise booking.
                </p>
                <p className="terms-portal-expiry muted">Link expires: {formatExpiryDate(portal.expires_at)}</p>
              </section>

              <section className="terms-portal-text-card">
                <header className="terms-portal-text-header">
                  <h2>{portal.agency_name} — Master Terms and Conditions</h2>
                  <p className="muted">Please scroll through the full agreement below.</p>
                </header>
                <div className="terms-portal-text-box" tabIndex={0}>
                  <TermsTextContent text={portal.terms_text} />
                </div>
              </section>

              <section className="terms-portal-form-card">
                <form className="terms-portal-form" onSubmit={(event) => void handleSubmit(event)}>
                  <label className="terms-portal-checkbox">
                    <input
                      type="checkbox"
                      checked={acceptedCheckbox}
                      onChange={(event) => setAcceptedCheckbox(event.target.checked)}
                      required
                    />
                    <span>{buildAcceptanceCertification(portal.agency_name)}</span>
                  </label>

                  {error ? <p className="terms-portal-inline-error">{error}</p> : null}

                  <button type="submit" className="terms-portal-submit" disabled={submitting || !acceptedCheckbox}>
                    {submitting ? "Submitting…" : "Accept Master Terms & Conditions"}
                  </button>
                </form>
              </section>
            </>
          ) : null}

          {!loading && completed ? (
            <section className="terms-portal-alert terms-portal-alert--success">
              <h2>Acceptance recorded</h2>
              <p>{completionMessage || "Thank you, your agency profile is up to date!"}</p>
              <p className="muted">
                Thank you, {portal?.passenger_name ?? "traveler"}. Your acceptance is on file with{" "}
                {portal?.agency_name ?? "your travel agency"} for this and future bookings.
              </p>
            </section>
          ) : null}
        </div>
      </section>
    </main>
  );
}
