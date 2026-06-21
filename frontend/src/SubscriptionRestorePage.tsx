import { logout } from "./authApi";
import { BRAND_APP_TITLE } from "./branding";

function readSubscriptionState(): string {
  const params = new URLSearchParams(window.location.search);
  return params.get("state")?.trim() || "Locked";
}

function subscriptionMessage(state: string): string {
  if (state === "Past Due") {
    return "Your agency subscription payment is past due. CRM access is paused until billing is restored.";
  }
  return "Your agency subscription is locked. CRM access is paused until billing is restored.";
}

export default function SubscriptionRestorePage() {
  const subscriptionState = readSubscriptionState();

  function handleReturnToSignIn() {
    logout("crm");
    window.location.replace("/");
  }

  return (
    <main className="page auth-page subscription-restore-page">
      <section className="card auth-card section-card subscription-restore-card">
        <header className="section-card-header">
          <h3>Subscription restoration required</h3>
        </header>

        <div className="section-card-body">
          <div className="auth-brand">
            <img src="/sailspipeline-logo.png" alt={BRAND_APP_TITLE} className="auth-logo" />
          </div>

          <p className="subscription-restore-status">
            Current status: <strong>{subscriptionState}</strong>
          </p>
          <p>{subscriptionMessage(subscriptionState)}</p>
          <p className="muted">
            Contact your agency owner or SailsPipeline billing support to restore access. Once your
            subscription is active again, sign in to return to the CRM.
          </p>

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
