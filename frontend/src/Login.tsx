import { FormEvent, useEffect, useState } from "react";
import { login } from "./authApi";
import { BRAND_APP_TITLE } from "./branding";
import { DEFAULT_ORGANIZATION_HANDLE } from "./tenantConstants";
import type { User } from "./types";

type LoginProps = {
  onAuthenticated: (user: User) => void;
};

export default function Login({ onAuthenticated }: LoginProps) {
  const [organizationHandle, setOrganizationHandle] = useState(DEFAULT_ORGANIZATION_HANDLE);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [flashError, setFlashError] = useState("");
  const [flashMessage, setFlashMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const storedError = sessionStorage.getItem("auth_flash_error");
    const storedSuccess = sessionStorage.getItem("auth_flash_success");
    if (storedError) {
      sessionStorage.removeItem("auth_flash_error");
      setFlashError(storedError);
    } else if (storedSuccess) {
      sessionStorage.removeItem("auth_flash_success");
      setFlashMessage(storedSuccess);
    }
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      const auth = await login({
        organization_handle: organizationHandle,
        username,
        password,
      });
      onAuthenticated(auth.user);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Authentication failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page auth-page">
      <section className="card auth-card">
        <div className="auth-brand">
          <img src="/sailspipeline-logo.png" alt={BRAND_APP_TITLE} className="auth-logo" />
        </div>
        <p className="auth-subtitle">Sign in to manage cruise travel requests.</p>

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
            Username
            <input
              required
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
            />
          </label>

          <label>
            Password
            <input
              required
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
            />
          </label>

          <p className="auth-forgot-link">
            <a href="/forgot-password">Forgot Password?</a>
          </p>

          <button type="submit" disabled={submitting}>
            {submitting ? "Please wait..." : "Sign in"}
          </button>
        </form>

        {error ? <p className="status error">{error}</p> : null}

        <p className="register-login-link muted">
          New agency? <a href="/register">Register your Agency</a>
        </p>
      </section>

      {flashError ? (
        <div className="register-toast register-toast-error" role="alert" aria-live="assertive">
          <span className="register-toast-icon" aria-hidden="true">
            !
          </span>
          <span>{flashError}</span>
        </div>
      ) : null}

      {flashMessage ? (
        <div className="register-toast" role="status" aria-live="polite">
          <span className="register-toast-icon" aria-hidden="true">
            ✓
          </span>
          <span>{flashMessage}</span>
        </div>
      ) : null}
    </main>
  );
}
