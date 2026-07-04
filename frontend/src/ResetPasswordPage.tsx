import { FormEvent, useEffect, useState, type CSSProperties } from "react";
import { resetPassword, validateResetPasswordToken, type PasswordResetValidateResponse } from "./authApi";
import { validatePassword } from "./authStorage";
import {
  hasAgencyBrandLogo,
  portalAgencyName,
  portalBrandingStyle,
  resolveBrandLogoUrl,
  type PortalBranding,
} from "./portalBranding";
import { BRAND_APP_TITLE } from "./branding";
import "./App.css";

function readTokenFromQuery(): string | null {
  const params = new URLSearchParams(window.location.search);
  const token = params.get("token")?.trim();
  return token || null;
}

type ResetPasswordBrandHeaderProps = {
  branding: PortalBranding;
  agencyName: string;
};

function ResetPasswordBrandHeader({ branding, agencyName }: ResetPasswordBrandHeaderProps) {
  const primaryColor = branding.primary_color ?? "#0d5c75";

  return (
    <header
      className="reset-password-brand-header"
      style={{ borderBottomColor: primaryColor }}
    >
      {hasAgencyBrandLogo(branding) ? (
        <img
          src={resolveBrandLogoUrl(branding.brand_logo_url)}
          alt={`${agencyName} logo`}
          className="auth-logo reset-password-brand-logo"
        />
      ) : (
        <div className="reset-password-brand-name">{agencyName}</div>
      )}
      <h2 className="reset-password-title">Reset password</h2>
      <p className="reset-password-subtitle">Choose a new password for your {agencyName} account.</p>
      <p className="reset-password-powered">Powered by {BRAND_APP_TITLE}</p>
    </header>
  );
}

export default function ResetPasswordPage() {
  const [token, setToken] = useState<string | null>(null);
  const [portal, setPortal] = useState<PasswordResetValidateResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const queryToken = readTokenFromQuery();
    if (!queryToken) {
      sessionStorage.setItem(
        "auth_flash_error",
        "Your password reset link is missing or invalid. Please request a new one.",
      );
      window.location.replace("/");
      return;
    }

    setToken(queryToken);

    async function loadPortal() {
      try {
        const payload = await validateResetPasswordToken(queryToken);
        setPortal(payload);
      } catch {
        sessionStorage.setItem(
          "auth_flash_error",
          "Your password reset link is invalid or has expired. Please request a new one.",
        );
        window.location.replace("/");
        return;
      } finally {
        setLoading(false);
      }
    }

    void loadPortal();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    const passwordError = validatePassword(newPassword);
    if (passwordError) {
      setError(passwordError);
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (!token) {
      return;
    }

    setSubmitting(true);
    try {
      await resetPassword(token, newPassword);
      setSuccess(true);
      window.setTimeout(() => {
        sessionStorage.setItem(
          "auth_flash_success",
          "Password updated successfully! Please sign in with your new credentials.",
        );
        window.location.replace("/");
      }, 1400);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to reset password.");
      setSubmitting(false);
    }
  }

  if (loading || !token || !portal) {
    return (
      <main className="page auth-page reset-password-page">
        <section className="card auth-card section-card">
          <div className="section-card-body">
            <p className="muted">Verifying your secure reset link…</p>
          </div>
        </section>
      </main>
    );
  }

  const agencyName = portalAgencyName(portal.branding);
  const brandingStyle = portalBrandingStyle(portal.branding);

  return (
    <main
      className="page auth-page reset-password-page"
      style={
        {
          ...brandingStyle,
          "--reset-primary": brandingStyle["--portal-primary"],
        } as CSSProperties
      }
    >
      <section className="card auth-card section-card reset-password-card">
        <ResetPasswordBrandHeader branding={portal.branding} agencyName={agencyName} />

        <div className="section-card-body">
          <form onSubmit={handleSubmit}>
            <label>
              New password
              <input
                required
                type="password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                autoComplete="new-password"
              />
            </label>

            <label>
              Confirm new password
              <input
                required
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                autoComplete="new-password"
              />
            </label>

            <p className="password-rules reset-password-instructions">
              Password must be more than 10 characters with at least one uppercase letter, one
              lowercase letter, one numeral, and one special character. Spaces are not allowed.
            </p>

            <button type="submit" className="reset-password-submit" disabled={submitting || success}>
              {submitting ? "Updating…" : "Update password"}
            </button>
          </form>

          {error ? <p className="status error">{error}</p> : null}

          <p className="register-login-link muted">
            <a href="/">Back to sign in</a>
          </p>
        </div>
      </section>

      {success ? (
        <div className="register-toast" role="status" aria-live="polite">
          <span className="register-toast-icon" aria-hidden="true">
            ✓
          </span>
          <span>Password updated successfully! Please sign in with your new credentials.</span>
        </div>
      ) : null}
    </main>
  );
}
