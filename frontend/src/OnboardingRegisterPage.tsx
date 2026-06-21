import { FormEvent, useEffect, useState } from "react";
import { acceptOnboardingInvite, verifyOnboardingInvite } from "./onboardingApi";
import { setToken, validatePassword } from "./authStorage";
import { BRAND_APP_TITLE } from "./branding";
import type { OnboardingInvite } from "./types";
import "./bridge-portal.css";

function readInviteToken(): string {
  const params = new URLSearchParams(window.location.search);
  return params.get("token")?.trim() ?? "";
}

export default function OnboardingRegisterPage() {
  const [token] = useState(readInviteToken);
  const [invite, setInvite] = useState<OnboardingInvite | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    async function verifyInvite() {
      if (!token) {
        setError("Missing invitation token. Open the onboarding link from your platform invitation email.");
        setLoading(false);
        return;
      }

      try {
        const verified = await verifyOnboardingInvite(token);
        setInvite(verified);
      } catch (verifyError) {
        setError(verifyError instanceof Error ? verifyError.message : "Invitation verification failed.");
      } finally {
        setLoading(false);
      }
    }

    void verifyInvite();
  }, [token]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) {
      return;
    }

    setError("");
    const passwordError = validatePassword(password);
    if (passwordError) {
      setError(passwordError);
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      const auth = await acceptOnboardingInvite({
        token,
        full_name: fullName,
        password,
      });
      setToken(auth.access_token, "crm");
      window.location.replace("/");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Onboarding failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page auth-page bridge-page">
      <section className="card auth-card bridge-onboarding-card">
        <div className="auth-brand">
          <img src="/sailspipeline-logo.png" alt={BRAND_APP_TITLE} className="auth-logo" />
        </div>
        <h1>Agency onboarding</h1>
        <p className="auth-subtitle">Complete your SailsPipeline workspace setup.</p>

        {loading ? <p className="muted">Verifying invitation…</p> : null}

        {!loading && invite ? (
          <>
            <div className="bridge-onboarding-summary">
              <p>
                <strong>Agency:</strong> {invite.target_agency_name}
              </p>
              <label>
                Organization handle
                <input value={invite.organization_handle} readOnly disabled />
              </label>
              <label>
                Owner email
                <input value={invite.invite_email} readOnly disabled />
              </label>
            </div>

            <form onSubmit={handleSubmit}>
              <label>
                Full name
                <input
                  required
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  autoComplete="name"
                  maxLength={120}
                />
              </label>

              <label>
                Password
                <input
                  required
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete="new-password"
                />
              </label>

              <label>
                Confirm password
                <input
                  required
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  autoComplete="new-password"
                />
              </label>

              <p className="password-rules">
                Password must be more than 10 characters with at least one uppercase letter, one
                lowercase letter, one numeral, and one special character. Spaces are not allowed.
              </p>

              <button type="submit" disabled={submitting}>
                {submitting ? "Creating workspace…" : "Launch my CRM workspace"}
              </button>
            </form>
          </>
        ) : null}

        {error ? <p className="status error">{error}</p> : null}
      </section>
    </main>
  );
}
