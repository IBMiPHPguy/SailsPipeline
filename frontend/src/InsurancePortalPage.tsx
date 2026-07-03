import { FormEvent, useEffect, useState } from "react";
import PortalBrandingHeader from "./PortalBrandingHeader";
import { signInsuranceWaiver, validateInsuranceWaiverToken } from "./insuranceApi";
import type { InsuranceWaiverValidateResponse } from "./insuranceApi";
import { portalAgencyName, portalBrandingStyle } from "./portalBranding";
import "./bridge-portal.css";
import "./portal-branding.css";
import "./insurance-portal.css";

type InsurancePortalPageProps = {
  token: string;
};

const WAIVER_ACCEPTANCE =
  "By checking this box and clicking 'Submit Waiver', I certify under penalty of perjury that I am the primary billing party and am legally authorized to sign on behalf of all passengers included in my booking. I explicitly acknowledge that I have been offered comprehensive travel insurance, that I understand the substantial financial risks of traveling unprotected, and that I voluntarily decline to purchase coverage. I accept full financial responsibility for any and all losses resulting from my declination of insurance. I agree that this electronic checkwrap acceptance constitutes a binding legal signature.";

function splitWaiverParagraphs(text: string): string[] {
  return text
    .split(/\n\s*\n/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);
}

function WaiverTextContent({ text }: { text: string }) {
  const paragraphs = splitWaiverParagraphs(text);
  const blocks =
    paragraphs.length > 1
      ? paragraphs
      : text
          .split("\n")
          .map((paragraph) => paragraph.trim())
          .filter(Boolean);

  return (
    <div className="insurance-portal-text-content">
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

export default function InsurancePortalPage({ token }: InsurancePortalPageProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [portal, setPortal] = useState<InsuranceWaiverValidateResponse | null>(null);
  const [acceptedCheckbox, setAcceptedCheckbox] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [completionMessage, setCompletionMessage] = useState("");

  useEffect(() => {
    async function loadPortal() {
      if (!token) {
        setError("This insurance waiver link is missing a secure token.");
        setLoading(false);
        return;
      }

      try {
        const payload = await validateInsuranceWaiverToken(token);
        setPortal(payload);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load waiver details.");
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
      const result = await signInsuranceWaiver(token);
      setCompleted(true);
      setCompletionMessage(result.message);
      setAcceptedCheckbox(false);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to record waiver signature.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page auth-page insurance-portal-page" style={portalBrandingStyle(portal?.branding)}>
      <section className="card bridge-card insurance-portal-card">
        <PortalBrandingHeader
          branding={portal?.branding}
          title="Travel Protection Declination"
          className="insurance-portal-header"
        />

        <div className="bridge-card-body insurance-portal-body">
          {loading ? <p className="muted">Verifying your secure waiver link…</p> : null}

          {!loading && error && !portal ? (
            <section className="insurance-portal-alert insurance-portal-alert--error">
              <h2>Link unavailable</h2>
              <p>{error}</p>
              <p className="muted">
                For your security, waiver links expire after 48 hours. Contact your travel advisor if you need a new
                link.
              </p>
            </section>
          ) : null}

          {!loading && portal && !completed ? (
            <>
              <section className="insurance-portal-summary">
                <p className="insurance-portal-greeting">
                  Hello <strong>{portal.passenger_name}</strong>,
                </p>
                <p>
                  {portalAgencyName(portal.branding, portal.agency_name)} requires your electronic signature on the
                  declination waiver below because you have chosen not to purchase travel protection for this cruise.
                </p>
                <p className="insurance-portal-expiry muted">Link expires: {formatExpiryDate(portal.expires_at)}</p>
              </section>

              <section className="insurance-portal-text-card">
                <header className="insurance-portal-text-header">
                  <h2>Important Legal Document</h2>
                  <p className="muted">Please read the full waiver carefully before signing.</p>
                </header>
                <div className="insurance-portal-text-box" tabIndex={0}>
                  <WaiverTextContent text={portal.waiver_text} />
                </div>
              </section>

              <form className="insurance-portal-form" onSubmit={handleSubmit}>
                <label className="insurance-portal-checkbox">
                  <input
                    type="checkbox"
                    checked={acceptedCheckbox}
                    onChange={(event) => setAcceptedCheckbox(event.target.checked)}
                    disabled={submitting}
                  />
                  <span>{WAIVER_ACCEPTANCE}</span>
                </label>

                {error ? <p className="insurance-portal-form-error">{error}</p> : null}

                <button type="submit" className="insurance-portal-submit" disabled={!acceptedCheckbox || submitting}>
                  {submitting ? "Submitting…" : "Submit Waiver"}
                </button>
              </form>
            </>
          ) : null}

          {!loading && completed ? (
            <section className="insurance-portal-success">
              <h2>Waiver recorded</h2>
              <p>{completionMessage}</p>
              <p className="muted">You may close this window. Your travel advisor has been notified.</p>
            </section>
          ) : null}
        </div>
      </section>
    </main>
  );
}
