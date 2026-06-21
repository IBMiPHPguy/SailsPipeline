import { FormEvent, useEffect, useState } from "react";
import { fetchBridgeTenant, updateBridgeTenant } from "../bridgeApi";
import type { BridgeTenantDetail } from "../types";
import BridgeCaptainIcon from "./BridgeCaptainIcon";

const SUBSCRIPTION_STATES = ["Active", "Trialing", "Past Due", "Locked"] as const;

type BridgeTenantEditPageProps = {
  agencyId: string;
  onBack: () => void;
};

export default function BridgeTenantEditPage({ agencyId, onBack }: BridgeTenantEditPageProps) {
  const [detail, setDetail] = useState<BridgeTenantDetail | null>(null);
  const [name, setName] = useState("");
  const [organizationHandle, setOrganizationHandle] = useState("");
  const [subscriptionState, setSubscriptionState] = useState<string>("Active");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    async function loadTenant() {
      setLoading(true);
      setError("");
      try {
        const data = await fetchBridgeTenant(agencyId);
        setDetail(data);
        setName(data.agency.name);
        setOrganizationHandle(data.agency.organization_handle);
        setSubscriptionState(data.agency.subscription_state);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load tenant.");
      } finally {
        setLoading(false);
      }
    }

    void loadTenant();
  }, [agencyId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    setMessage("");

    try {
      const updated = await updateBridgeTenant(agencyId, {
        name,
        organization_handle: organizationHandle,
        subscription_state: subscriptionState,
      });
      setDetail((current) =>
        current
          ? {
              ...current,
              agency: updated,
            }
          : current,
      );
      setMessage("Tenant updated successfully.");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to save tenant.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <section className="card bridge-panel bridge-card">
        <header className="bridge-card-header">
          <h2>Edit Tenant</h2>
        </header>
        <div className="bridge-card-body">
          <p className="muted">Loading tenant…</p>
        </div>
      </section>
    );
  }

  if (error && !detail) {
    return (
      <section className="card bridge-panel bridge-card">
        <header className="bridge-card-header">
          <h2>Edit Tenant</h2>
        </header>
        <div className="bridge-card-body">
          <p className="status error">{error}</p>
          <button type="button" className="secondary-button bridge-toolbar-button bridge-back-button" onClick={onBack}>
            <BridgeCaptainIcon size={18} className="bridge-back-button-icon" />
            Back to The Bridge
          </button>
        </div>
      </section>
    );
  }

  return (
    <div className="bridge-tenant-edit">
      <section className="card bridge-panel bridge-card">
        <header className="bridge-card-header">
          <div>
            <h2>Edit Tenant</h2>
            <p className="muted">Update base agency information for this tenant workspace.</p>
          </div>
          <button type="button" className="secondary-button bridge-toolbar-button bridge-back-button" onClick={onBack}>
            <BridgeCaptainIcon size={18} className="bridge-back-button-icon" />
            Back to The Bridge
          </button>
        </header>

        <div className="bridge-card-body">
        <form className="bridge-form bridge-tenant-form" onSubmit={handleSubmit}>
          <label>
            Agency name
            <input
              required
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={120}
            />
          </label>

          <label>
            Organization handle
            <input
              required
              value={organizationHandle}
              onChange={(event) => setOrganizationHandle(event.target.value)}
              spellCheck={false}
              maxLength={50}
            />
          </label>

          <label>
            Subscription state
            <select
              required
              value={subscriptionState}
              onChange={(event) => setSubscriptionState(event.target.value)}
            >
              {SUBSCRIPTION_STATES.map((state) => (
                <option key={state} value={state}>
                  {state}
                </option>
              ))}
            </select>
          </label>

          <div className="bridge-toolbar">
            <button type="submit" className="bridge-primary-button bridge-save-button" disabled={submitting}>
              {submitting ? "Saving…" : "Save changes"}
            </button>
          </div>
        </form>

        {message ? <p className="status success">{message}</p> : null}
        {error && detail ? <p className="status error">{error}</p> : null}
        </div>
      </section>

      <section className="card bridge-panel bridge-card">
        <header className="bridge-card-header">
          <div>
            <h2>Tenant users</h2>
            <p className="muted">Users assigned to this agency workspace.</p>
          </div>
        </header>

        <div className="bridge-card-body">
        <div className="bridge-table-wrap">
          <table className="bridge-table">
            <thead>
              <tr>
                <th>Username</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {!detail || detail.users.length === 0 ? (
                <tr>
                  <td colSpan={4} className="muted">
                    No users assigned to this tenant yet.
                  </td>
                </tr>
              ) : (
                detail.users.map((user) => (
                  <tr key={user.id}>
                    <td>{user.username}</td>
                    <td>{user.email}</td>
                    <td>{user.role}</td>
                    <td>{user.is_active ? "Active" : "Inactive"}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        </div>
      </section>
    </div>
  );
}
