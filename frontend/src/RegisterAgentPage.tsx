import { FormEvent, useEffect, useState } from "react";
import { acceptAgentInvite, verifyAgentInvite } from "./agentOnboardingApi";
import { setToken, validatePassword } from "./authStorage";
import { BRAND_APP_TITLE } from "./branding";
import type { AgentInvite } from "./types";

function readInviteToken(): string {
  const params = new URLSearchParams(window.location.search);
  return params.get("token")?.trim() ?? "";
}

function formatRoleLabel(role: string): string {
  if (role === "tenant_super_user") {
    return "Super user";
  }
  if (role === "tenant_agent") {
    return "Agent";
  }
  return role;
}

export default function RegisterAgentPage() {
  const [token] = useState(readInviteToken);
  const [invite, setInvite] = useState<AgentInvite | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    async function verifyInvite() {
      if (!token) {
        setError("Missing invitation token. Open the team invitation link from your agency owner.");
        setLoading(false);
        return;
      }

      try {
        const verified = await verifyAgentInvite(token);
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
      const auth = await acceptAgentInvite({
        token,
        full_name: fullName,
        password,
      });
      setToken(auth.access_token, "crm");
      window.location.replace("/");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Registration failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page auth-page">
      <section className="card auth-card section-card team-register-card">
        <header className="section-card-header">
          <h3>Join your agency team</h3>
        </header>

        <div className="section-card-body">
          <div className="auth-brand">
            <img src="/sailspipeline-logo.png" alt={BRAND_APP_TITLE} className="auth-logo" />
          </div>

          {loading ? <p className="muted">Verifying invitation…</p> : null}

          {!loading && invite ? (
            <>
              <div className="team-register-summary">
                <p>
                  <strong>Agency:</strong> {invite.agency_name}
                </p>
                <p>
                  <strong>Organization handle:</strong> {invite.organization_handle}
                </p>
                <p>
                  <strong>Invited email:</strong> {invite.invite_email}
                </p>
                <p>
                  <strong>Role:</strong> {formatRoleLabel(invite.role)}
                </p>
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
                  {submitting ? "Creating account…" : "Join SailsPipeline CRM"}
                </button>
              </form>
            </>
          ) : null}

          {error ? <p className="status error">{error}</p> : null}
        </div>
      </section>
    </main>
  );
}
