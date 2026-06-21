import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { cancelBridgeInvite, createBridgeInvite, fetchBridgeSummary } from "../bridgeApi";
import EditIcon from "../EditIcon";
import IconTooltip from "../IconTooltip";
import RejectIcon from "../RejectIcon";
import type { BridgeInvitationSummary, BridgeSummary, PlatformInviteCreated } from "../types";
type LedgerRow =
  | {
      key: string;
      rowType: "tenant";
      agencyId: string;
      name: string;
      handle: string;
      status: string;
      expiresAt: string | null;
    }
  | {
      key: string;
      rowType: "invitation";
      invitationId: string;
      agencyId: null;
      name: string;
      handle: string;
      status: string;
      expiresAt: string | null;
    };
function formatTimestamp(value: string | null): string {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function buildLedgerRows(summary: BridgeSummary): LedgerRow[] {
  const tenantRows: LedgerRow[] = summary.agencies.map((agency) => ({
    key: `agency-${agency.id}`,
    rowType: "tenant",
    agencyId: agency.id,
    name: agency.name,
    handle: agency.organization_handle,
    status: agency.subscription_state,
    expiresAt: null,
  }));

  const inviteRows: LedgerRow[] = summary.invitations.map((invite: BridgeInvitationSummary) => ({
    key: `invite-${invite.id}`,
    rowType: "invitation",
    invitationId: invite.id,
    agencyId: null,
    name: invite.invite_email,
    handle: invite.target_organization_handle,
    status: invite.token_status,
    expiresAt: invite.expires_at,
  }));

  return [...tenantRows, ...inviteRows];
}

export default function BridgePage({ onEditTenant }: { onEditTenant: (agencyId: string) => void }) {  const [summary, setSummary] = useState<BridgeSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [agencyName, setAgencyName] = useState("");
  const [organizationHandle, setOrganizationHandle] = useState("");
  const [ownerEmail, setOwnerEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [issuedInvite, setIssuedInvite] = useState<PlatformInviteCreated | null>(null);
  const [formError, setFormError] = useState("");
  const [revokingInviteId, setRevokingInviteId] = useState<string | null>(null);

  const loadSummary = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await fetchBridgeSummary();
      setSummary(data);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load Bridge summary.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSummary();
  }, [loadSummary]);

  const ledgerRows = useMemo(() => (summary ? buildLedgerRows(summary) : []), [summary]);

  async function handleRevokeInvite(invitationId: string) {
    setRevokingInviteId(invitationId);
    setError("");
    try {
      await cancelBridgeInvite(invitationId);
      await loadSummary();
    } catch (revokeError) {
      setError(revokeError instanceof Error ? revokeError.message : "Unable to revoke invitation.");
    } finally {
      setRevokingInviteId(null);
    }
  }

  async function handleIssueInvite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setFormError("");
    setIssuedInvite(null);

    try {
      const created = await createBridgeInvite({
        target_agency_name: agencyName,
        target_organization_handle: organizationHandle,
        invite_email: ownerEmail,
      });
      setIssuedInvite(created);
      setAgencyName("");
      setOrganizationHandle("");
      setOwnerEmail("");
      await loadSummary();
    } catch (submitError) {
      setFormError(submitError instanceof Error ? submitError.message : "Unable to issue invitation.");
    } finally {
      setSubmitting(false);
    }
  }

  const onboardingUrl = issuedInvite
    ? `${window.location.origin}${issuedInvite.onboarding_path}`
    : "";

  return (
    <div className="bridge-grid">
      <section className="card bridge-panel bridge-card">
        <header className="bridge-card-header">
          <div>
            <h2>Provision New Agency</h2>
            <p className="muted">
              Issue a secure platform invitation for a new tenant owner. They will complete onboarding at
              the generated registration link.
            </p>
          </div>
        </header>

        <div className="bridge-card-body">
          <form className="bridge-form" onSubmit={handleIssueInvite}>
          <label>
            Agency name
            <input
              required
              value={agencyName}
              onChange={(event) => setAgencyName(event.target.value)}
              maxLength={255}
            />
          </label>

          <label>
            Desired organization handle
            <input
              required
              value={organizationHandle}
              onChange={(event) => setOrganizationHandle(event.target.value)}
              spellCheck={false}
              maxLength={50}
              placeholder="bluehorizon"
            />
          </label>

          <label>
            Owner email address
            <input
              required
              type="email"
              value={ownerEmail}
              onChange={(event) => setOwnerEmail(event.target.value)}
              maxLength={255}
            />
          </label>

          <button type="submit" className="bridge-primary-button" disabled={submitting}>
            {submitting ? "Issuing…" : "Issue Platform Invitation"}
          </button>
        </form>

        {formError ? <p className="status error">{formError}</p> : null}

        {issuedInvite ? (
          <div className="bridge-invite-result">
            <p className="status success">Invitation issued successfully.</p>
            <p className="bridge-invite-label">Onboarding link</p>
            <code className="bridge-invite-link">{onboardingUrl}</code>
            <p className="muted">Expires {formatTimestamp(issuedInvite.expires_at)}</p>
          </div>
        ) : null}
        </div>
      </section>

      <section className="card bridge-panel bridge-card bridge-ledger-panel">
        <header className="bridge-card-header">
          <div>
            <h2>Active Tenants &amp; Pending Invites</h2>
          </div>
        </header>

        <div className="bridge-card-body">
        {loading ? <p className="muted">Loading tenant ledger…</p> : null}
        {error ? <p className="status error">{error}</p> : null}

        {!loading && !error ? (
          <div className="bridge-table-wrap">
            <table className="bridge-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Name / Email</th>
                  <th>Handle</th>
                  <th>Status</th>
                  <th>Expires</th>
                  <th className="bridge-table-actions-heading">Actions</th>
                </tr>
              </thead>
              <tbody>
                {ledgerRows.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="muted">
                      No tenants or invitations yet.
                    </td>
                  </tr>
                ) : (
                  ledgerRows.map((row) => (
                    <tr key={row.key}>
                      <td>{row.rowType === "tenant" ? "Active tenant" : "Invitation"}</td>
                      <td>{row.name}</td>
                      <td>{row.handle}</td>
                      <td>{row.status}</td>
                      <td>{formatTimestamp(row.expiresAt)}</td>
                      <td className="bridge-table-actions">
                        {row.rowType === "tenant" ? (
                          <IconTooltip label="Edit tenant">
                            <button
                              type="button"
                              className="icon-button"
                              aria-label={`Edit ${row.name}`}
                              onClick={() => onEditTenant(row.agencyId)}
                            >
                              <EditIcon />
                            </button>
                          </IconTooltip>
                        ) : row.status === "Pending" ? (
                          <IconTooltip label="Revoke invitation">
                            <button
                              type="button"
                              className="icon-button icon-button-danger"
                              aria-label={`Revoke invitation for ${row.name}`}
                              disabled={revokingInviteId === row.invitationId}
                              onClick={() => handleRevokeInvite(row.invitationId)}
                            >
                              <RejectIcon />
                            </button>
                          </IconTooltip>
                        ) : (
                          <span className="muted">—</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        ) : null}
        </div>
      </section>
    </div>
  );
}
