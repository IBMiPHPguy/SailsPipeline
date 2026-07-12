import { createPortal } from "react-dom";
import type { AgencyPendingInvite } from "./types";
import { USER_ROLE_TENANT_AGENT, USER_ROLE_TENANT_SUPER_USER } from "./tenantRoles";

function formatRoleLabel(role: string): string {
  if (role === USER_ROLE_TENANT_SUPER_USER) {
    return "Super user";
  }
  if (role === USER_ROLE_TENANT_AGENT) {
    return "Agent";
  }
  return role;
}

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

type ArchivedInvitationsModalProps = {
  open: boolean;
  invitations: AgencyPendingInvite[];
  onClose: () => void;
};

export default function ArchivedInvitationsModal({
  open,
  invitations,
  onClose,
}: ArchivedInvitationsModalProps) {
  if (!open) {
    return null;
  }

  return createPortal(
    <div className="modal-backdrop modal-backdrop-scroll" role="presentation" onClick={onClose}>
      <div
        className="modal-card modal-card-wide"
        role="dialog"
        aria-modal="true"
        aria-labelledby="archived-invitations-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="modal-card-header">
          <h3 id="archived-invitations-title">Archived expired / cancelled invitations</h3>
        </header>

        <div className="modal-scroll-body">
          <p className="muted">
            Expired and cancelled invitations older than 7 days are hidden from the Pending invitations
            card. This archive lists those older invitations.
          </p>

          <div className="team-table-wrap">
            <table className="team-table">
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Expires</th>
                  <th>Cancelled</th>
                </tr>
              </thead>
              <tbody>
                {invitations.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="muted">
                      No archived invitations.
                    </td>
                  </tr>
                ) : (
                  invitations.map((invite) => (
                    <tr key={invite.id}>
                      <td>{invite.invite_email}</td>
                      <td>{formatRoleLabel(invite.role)}</td>
                      <td>{invite.token_status}</td>
                      <td>{formatTimestamp(invite.expires_at)}</td>
                      <td>
                        {invite.cancelled_at ? formatTimestamp(invite.cancelled_at) : "—"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <footer className="modal-actions-footer">
          <button type="button" className="modal-secondary" onClick={onClose}>
            Close
          </button>
        </footer>
      </div>
    </div>,
    document.body,
  );
}
