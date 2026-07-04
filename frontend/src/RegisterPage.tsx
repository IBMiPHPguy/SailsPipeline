import { FormEvent, useState } from "react";
import { registerAgencyWorkspace } from "./authApi";
import { setToken, validatePassword } from "./authStorage";
import { BRAND_APP_TITLE, BRAND_NAME } from "./branding";
import "./App.css";

export default function RegisterPage() {
  const [agencyName, setAgencyName] = useState("");
  const [adminName, setAdminName] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSuccess("");

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
      const auth = await registerAgencyWorkspace({
        agency_name: agencyName.trim(),
        admin_name: adminName.trim(),
        admin_email: adminEmail.trim(),
        password,
      });
      setToken(auth.access_token, "crm");
      setSuccess("Workspace provisioned successfully!");
      window.setTimeout(() => {
        window.location.replace("/");
      }, 1400);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Registration failed.");
      setSubmitting(false);
    }
  }

  return (
    <main className="page register-page">
      <div className="register-layout">
        <aside className="register-hero" aria-hidden="true">
          <div className="register-hero-inner">
            <img src="/sailspipeline-logo.png" alt="" className="register-hero-logo" />
            <h1>Launch your agency on {BRAND_NAME}</h1>
            <p>
              Provision a dedicated CRM workspace with branded client communications, compliance
              workflows, and a ready-to-use terms library — in minutes.
            </p>
            <ul className="register-hero-list">
              <li>Instant multi-tenant workspace</li>
              <li>Default white-label branding</li>
              <li>Owner-ready compliance seeds</li>
            </ul>
          </div>
        </aside>

        <section className="card register-card section-card">
          <header className="section-card-header">
            <div>
              <h2>Register your agency</h2>
              <p className="muted">Create your {BRAND_APP_TITLE} owner account.</p>
            </div>
          </header>

          <div className="section-card-body">
            <form onSubmit={handleSubmit}>
              <label>
                Agency name
                <input
                  required
                  value={agencyName}
                  onChange={(event) => setAgencyName(event.target.value)}
                  autoComplete="organization"
                  maxLength={120}
                  placeholder="Harbor Lights Travel"
                />
              </label>

              <label>
                Full name
                <input
                  required
                  value={adminName}
                  onChange={(event) => setAdminName(event.target.value)}
                  autoComplete="name"
                  maxLength={120}
                  placeholder="Alex Morgan"
                />
              </label>

              <label>
                Email address
                <input
                  required
                  type="email"
                  value={adminEmail}
                  onChange={(event) => setAdminEmail(event.target.value)}
                  autoComplete="email"
                  placeholder="alex@harborlightstravel.com"
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

              <button type="submit" disabled={submitting || Boolean(success)}>
                {submitting ? "Provisioning workspace…" : "Create agency workspace"}
              </button>
            </form>

            {error ? <p className="status error">{error}</p> : null}

            <p className="register-login-link muted">
              Already have an account? <a href="/">Log in</a>
            </p>
          </div>
        </section>
      </div>

      {success ? (
        <div className="register-toast" role="status" aria-live="polite">
          <span className="register-toast-icon" aria-hidden="true">
            ✓
          </span>
          <span>{success}</span>
        </div>
      ) : null}
    </main>
  );
}
