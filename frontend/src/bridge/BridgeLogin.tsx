import { FormEvent, useState } from "react";
import { loginBridge } from "../bridgeApi";
import { BRAND_APP_TITLE } from "../branding";
import type { User } from "../types";
import BridgeCaptainIcon from "./BridgeCaptainIcon";
import "../App.css";
import "../bridge-portal.css";

type BridgeLoginProps = {
  onAuthenticated: (user: User) => void;
};

export default function BridgeLogin({ onAuthenticated }: BridgeLoginProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      const auth = await loginBridge({ username, password });
      onAuthenticated(auth.user);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Sign in failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page auth-page bridge-page">
      <section className="card auth-card bridge-login-card bridge-card">
        <header className="bridge-card-header bridge-card-header--centered">
          <div className="bridge-login-title-row">
            <BridgeCaptainIcon size={44} />
            <h2>The Bridge</h2>
          </div>
          <p className="muted bridge-login-subtitle">
            Platform operator sign in for tenant provisioning and management.
          </p>
        </header>

        <div className="bridge-card-body">
          <div className="auth-brand">
            <img src="/sailspipeline-logo.png" alt={BRAND_APP_TITLE} className="auth-logo" />
          </div>

          <form onSubmit={handleSubmit}>
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

          <button type="submit" className="bridge-primary-button" disabled={submitting}>
            {submitting ? "Signing in…" : "Sign in to The Bridge"}
          </button>
        </form>

        {error ? <p className="status error">{error}</p> : null}

        <p className="muted bridge-login-footnote">
          Need the travel agency CRM instead? <a href="/">Open SailsPipeline CRM</a>
        </p>
        </div>
      </section>
    </main>
  );
}
