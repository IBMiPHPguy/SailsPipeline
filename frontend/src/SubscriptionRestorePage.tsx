import { logout } from "./authApi";
import { BRAND_APP_TITLE, BRAND_NAME } from "./branding";
import "./App.css";

function readSubscriptionState(): string {
  const params = new URLSearchParams(window.location.search);
  return params.get("state")?.trim() || "Locked";
}

function readSubscriptionReason(): string | null {
  const params = new URLSearchParams(window.location.search);
  return params.get("reason")?.trim() || null;
}

function pageTitle(reason: string | null): string {
  if (reason === "trial_expired") {
    return "Demo period ended";
  }
  return "Subscription restoration required";
}

function subscriptionMessage(state: string, reason: string | null): string {
  if (reason === "trial_expired") {
    return `Your ${BRAND_NAME} demo has ended. Contact ${BRAND_NAME} to activate your account with a subscription.`;
  }
  if (state === "Past Due") {
    return "Your agency subscription payment is past due. CRM access is paused until billing is restored.";
  }
  return "Your agency subscription is locked. CRM access is paused until billing is restored.";
}

function supportMessage(reason: string | null): string {
  if (reason === "trial_expired") {
    return `When you're ready to continue, reach out to ${BRAND_NAME} to activate your agency subscription. Once your account is active, sign in again to return to the CRM.`;
  }
  return "Contact your agency owner or SailsPipeline billing support to restore access. Once your subscription is active again, sign in to return to the CRM.";
}

export default function SubscriptionRestorePage() {
  const subscriptionState = readSubscriptionState();
  const subscriptionReason = readSubscriptionReason();

  function handleReturnToSignIn() {
    logout("crm");
    window.location.replace("/");
  }

  return (
    <main className="page auth-page subscription-restore-page">
      <section className="card auth-card section-card subscription-restore-card">
        <header className="section-card-header">
          <h3>{pageTitle(subscriptionReason)}</h3>
        </header>

        <div className="section-card-body">
          <div className="auth-brand">
            <img src="/sailspipeline-logo.png" alt={BRAND_APP_TITLE} className="auth-logo" />
          </div>

          <p className="subscription-restore-status">
            Current status: <strong>{subscriptionState}</strong>
          </p>
          <p>{subscriptionMessage(subscriptionState, subscriptionReason)}</p>
          <p className="muted">{supportMessage(subscriptionReason)}</p>

          <div className="subscription-restore-actions">
            <button type="button" onClick={handleReturnToSignIn}>
              Return to sign in
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}
