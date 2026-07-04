import { FormEvent, useState } from "react";
import { requestPasswordReset } from "./authApi";
import { BRAND_APP_TITLE } from "./branding";
import { DEFAULT_ORGANIZATION_HANDLE } from "./tenantConstants";
import "./App.css";

export default function ForgotPasswordPage() {
  const [organizationHandle, setOrganizationHandle] = useState(DEFAULT_ORGANIZATION_HANDLE);
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      await requestPasswordReset({
        organization_handle: organizationHandle.trim(),
        email: email.trim(),
      });
      setSuccess(true);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to send reset email.");
      setSubmitting(false);
    }
  }

  return (
    <main className="page auth-page">
      <section className="card auth-card section-card">
        <header className="section-card-header">
          <div>
            <h2>Forgot password</h2>
            <p className="muted">
              Enter your organization handle and email to reset your {BRAND_APP_TITLE} password.
            </p>
          </div>
        </header>

        <div className="section-card-body">
          {!success ? (
            <form onSubmit={handleSubmit}>
              <label>
                Organization handle
                <input
                  required
                  value={organizationHandle}
                  onChange={(event) => setOrganizationHandle(event.target.value)}
                  autoComplete="organization"
                  spellCheck={false}
                />
              </label>

              <label>
                Email address
                <input
                  required
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  autoComplete="email"
                  placeholder="you@youragency.com"
                />
              </label>

              <button type="submit" disabled={submitting}>
                {submitting ? "Sending…" : "Send recovery link"}
              </button>
            </form>
          ) : (
            <div className="auth-recovery-success">
              <p className="status success">
                If your account exists, an email recovery link has been sent to your inbox.
              </p>
              <a className="button-link" href="/">
                Back to sign in
              </a>
            </div>
          )}

          {error ? <p className="status error">{error}</p> : null}

          {!success ? (
            <p className="register-login-link muted">
              Remember your password? <a href="/">Back to sign in</a>
            </p>
          ) : null}
        </div>
      </section>

      {success ? (
        <div className="register-toast" role="status" aria-live="polite">
          <span className="register-toast-icon" aria-hidden="true">
            ✓
          </span>
          <span>If your account exists, an email recovery link has been sent to your inbox.</span>
        </div>
      ) : null}
    </main>
  );
}
