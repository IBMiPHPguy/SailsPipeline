import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import ChickenSwitchModal from "./ChickenSwitchModal";
import DeactivateIcon from "./DeactivateIcon";
import EditIcon from "./EditIcon";
import IconTooltip from "./IconTooltip";
import RejectIcon from "./RejectIcon";
import ReopenIcon from "./ReopenIcon";
import { createAgencyInvite, cancelAgencyInvite, fetchAgencyTeam, updateAgencyUser } from "./teamApi";
import type { AgencyTeamMember, User } from "./types";
import type { UserRole } from "./tenantRoles";
import { USER_ROLE_TENANT_AGENT, USER_ROLE_TENANT_SUPER_USER } from "./tenantRoles";

const ASSIGNABLE_ROLES: UserRole[] = [USER_ROLE_TENANT_AGENT, USER_ROLE_TENANT_SUPER_USER];

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

type TeamPageProps = {
  currentUser: User;
};

type EditDraft = {
  email: string;
  role: UserRole;
  is_active: boolean;
};

type UserStatusFilter = "active" | "inactive" | "both";

type PendingDeactivateUser = {
  id: number;
  username: string;
};

export default function TeamPage({ currentUser }: TeamPageProps) {
  const [users, setUsers] = useState<AgencyTeamMember[]>([]);
  const [invitations, setInvitations] = useState<
    Awaited<ReturnType<typeof fetchAgencyTeam>>["invitations"]
  >([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<UserRole>(USER_ROLE_TENANT_AGENT);
  const [inviteSubmitting, setInviteSubmitting] = useState(false);
  const [inviteMessage, setInviteMessage] = useState("");
  const [issuedInviteLink, setIssuedInviteLink] = useState("");
  const [editingUserId, setEditingUserId] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState<EditDraft | null>(null);
  const [saveSubmitting, setSaveSubmitting] = useState(false);
  const [revokingInviteId, setRevokingInviteId] = useState<string | null>(null);
  const [userStatusFilter, setUserStatusFilter] = useState<UserStatusFilter>("active");
  const [pendingDeactivateUser, setPendingDeactivateUser] = useState<PendingDeactivateUser | null>(null);
  const [togglingUserId, setTogglingUserId] = useState<number | null>(null);

  const loadTeam = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const team = await fetchAgencyTeam();
      setUsers(team.users);
      setInvitations(team.invitations);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load team workspace.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadTeam();
  }, [loadTeam]);

  async function handleInviteSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setInviteSubmitting(true);
    setInviteMessage("");
    setIssuedInviteLink("");
    setError("");

    try {
      const created = await createAgencyInvite({
        invite_email: inviteEmail,
        role: inviteRole,
      });
      const inviteUrl = `${window.location.origin}${created.onboarding_path}`;
      setIssuedInviteLink(inviteUrl);
      setInviteMessage("Team invitation issued successfully.");
      setInviteEmail("");
      setInviteRole(USER_ROLE_TENANT_AGENT);
      await loadTeam();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to issue invitation.");
    } finally {
      setInviteSubmitting(false);
    }
  }

  function beginEdit(user: AgencyTeamMember) {
    setEditingUserId(user.id);
    setEditDraft({
      email: user.email,
      role: user.role,
      is_active: user.is_active,
    });
  }

  function cancelEdit() {
    setEditingUserId(null);
    setEditDraft(null);
  }

  async function handleSaveEdit(userId: number) {
    if (!editDraft) {
      return;
    }

    setSaveSubmitting(true);
    setError("");
    try {
      await updateAgencyUser(userId, editDraft);
      setEditingUserId(null);
      setEditDraft(null);
      await loadTeam();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to save team member.");
    } finally {
      setSaveSubmitting(false);
    }
  }

  const filteredUsers = useMemo(() => {
    if (userStatusFilter === "active") {
      return users.filter((user) => user.is_active);
    }
    if (userStatusFilter === "inactive") {
      return users.filter((user) => !user.is_active);
    }
    return users;
  }, [users, userStatusFilter]);

  function requestDeactivateUser(user: AgencyTeamMember) {
    setPendingDeactivateUser({
      id: user.id,
      username: user.username,
    });
  }

  async function confirmDeactivateUser() {
    if (!pendingDeactivateUser) {
      return;
    }

    setTogglingUserId(pendingDeactivateUser.id);
    setError("");
    try {
      await updateAgencyUser(pendingDeactivateUser.id, { is_active: false });
      setPendingDeactivateUser(null);
      if (editingUserId === pendingDeactivateUser.id) {
        cancelEdit();
      }
      await loadTeam();
    } catch (deactivateError) {
      setError(deactivateError instanceof Error ? deactivateError.message : "Unable to deactivate team member.");
    } finally {
      setTogglingUserId(null);
    }
  }

  async function handleReactivateUser(user: AgencyTeamMember) {
    setTogglingUserId(user.id);
    setError("");
    try {
      await updateAgencyUser(user.id, { is_active: true });
      await loadTeam();
    } catch (reactivateError) {
      setError(reactivateError instanceof Error ? reactivateError.message : "Unable to reactivate team member.");
    } finally {
      setTogglingUserId(null);
    }
  }

  function emptyUsersMessage(): string {
    if (users.length === 0) {
      return "No team members found.";
    }
    if (userStatusFilter === "active") {
      return "No active team members.";
    }
    if (userStatusFilter === "inactive") {
      return "No inactive team members.";
    }
    return "No team members found.";
  }

  async function handleRevokeInvite(invitationId: string) {
    setRevokingInviteId(invitationId);
    setError("");
    try {
      await cancelAgencyInvite(invitationId);
      await loadTeam();
    } catch (revokeError) {
      setError(revokeError instanceof Error ? revokeError.message : "Unable to revoke invitation.");
    } finally {
      setRevokingInviteId(null);
    }
  }

  const openInvites = invitations;

  return (
    <div className="team-page-grid">
      <section className="card section-card team-invite-card">
        <header className="section-card-header">
          <h3>Invite team member</h3>
        </header>
        <div className="section-card-body">
          <p className="muted">
            Send a secure invitation link for a new agent or super user to join your agency workspace.
            Invitations expire automatically after 3 days if not accepted.
          </p>

          <form className="team-invite-form" onSubmit={handleInviteSubmit}>
            <label>
              Email address
              <input
                required
                type="email"
                value={inviteEmail}
                onChange={(event) => setInviteEmail(event.target.value)}
                maxLength={255}
              />
            </label>

            <label>
              Authorization level
              <select
                value={inviteRole}
                onChange={(event) => setInviteRole(event.target.value as UserRole)}
              >
                {ASSIGNABLE_ROLES.map((role) => (
                  <option key={role} value={role}>
                    {formatRoleLabel(role)}
                  </option>
                ))}
              </select>
            </label>

            <button type="submit" disabled={inviteSubmitting}>
              {inviteSubmitting ? "Issuing…" : "Issue team invitation"}
            </button>
          </form>

          {inviteMessage ? <p className="status success">{inviteMessage}</p> : null}
          {issuedInviteLink ? (
            <div className="team-invite-result">
              <p className="team-invite-label">Registration link</p>
              <code className="team-invite-link">{issuedInviteLink}</code>
            </div>
          ) : null}
        </div>
      </section>

      <section className="card section-card team-members-card">
        <header className="section-card-header">
          <h3>Agency users</h3>
        </header>
        <div className="section-card-body">
          {loading ? <p className="muted">Loading team members…</p> : null}
          {error ? <p className="status error">{error}</p> : null}

          {!loading ? (
            <>
            <div className="team-users-toolbar">
              <label className="team-users-filter">
                Show users
                <select
                  value={userStatusFilter}
                  onChange={(event) => setUserStatusFilter(event.target.value as UserStatusFilter)}
                >
                  <option value="active">Active only</option>
                  <option value="inactive">Inactive only</option>
                  <option value="both">Active and inactive</option>
                </select>
              </label>
            </div>
            <div className="team-table-wrap">
              <table className="team-table">
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th className="team-table-actions-heading">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="muted">
                        {emptyUsersMessage()}
                      </td>
                    </tr>
                  ) : (
                    filteredUsers.flatMap((user) => {
                      const rows = [
                        <tr
                          key={user.id}
                          className={user.is_active ? undefined : "team-table-row-inactive"}
                        >
                          <td>{user.username}</td>
                          <td>{user.email}</td>
                          <td>{formatRoleLabel(user.role)}</td>
                          <td>
                            {user.is_active ? (
                              "Active"
                            ) : (
                              <span className="inactive-user-badge">Inactive</span>
                            )}
                          </td>
                          <td className="team-table-actions">
                            <div className="dashboard-table-actions">
                              <IconTooltip label="Edit team member">
                                <button
                                  type="button"
                                  className="icon-button"
                                  aria-label={`Edit ${user.username}`}
                                  onClick={() => beginEdit(user)}
                                >
                                  <EditIcon />
                                </button>
                              </IconTooltip>
                              {user.is_active ? (
                                user.id !== currentUser.id ? (
                                  <IconTooltip label={`Deactivate ${user.username}`}>
                                    <button
                                      type="button"
                                      className="icon-button icon-button-danger"
                                      aria-label={`Deactivate ${user.username}`}
                                      disabled={togglingUserId === user.id}
                                      onClick={() => requestDeactivateUser(user)}
                                    >
                                      <DeactivateIcon />
                                    </button>
                                  </IconTooltip>
                                ) : null
                              ) : (
                                <IconTooltip label={`Reactivate ${user.username}`}>
                                  <button
                                    type="button"
                                    className="icon-button icon-button-reopen"
                                    aria-label={`Reactivate ${user.username}`}
                                    disabled={togglingUserId === user.id}
                                    onClick={() => void handleReactivateUser(user)}
                                  >
                                    <ReopenIcon />
                                  </button>
                                </IconTooltip>
                              )}
                            </div>
                          </td>
                        </tr>,
                      ];

                      if (editingUserId === user.id && editDraft) {
                        rows.push(
                          <tr key={`edit-${user.id}`} className="team-edit-row">
                            <td colSpan={5}>
                              <div className="team-edit-panel">
                                <label>
                                  Email
                                  <input
                                    type="email"
                                    value={editDraft.email}
                                    onChange={(event) =>
                                      setEditDraft({ ...editDraft, email: event.target.value })
                                    }
                                    disabled={user.id === currentUser.id}
                                  />
                                </label>
                                <label>
                                  Authorization level
                                  <select
                                    value={editDraft.role}
                                    onChange={(event) =>
                                      setEditDraft({
                                        ...editDraft,
                                        role: event.target.value as UserRole,
                                      })
                                    }
                                    disabled={user.id === currentUser.id}
                                  >
                                    {ASSIGNABLE_ROLES.map((role) => (
                                      <option key={role} value={role}>
                                        {formatRoleLabel(role)}
                                      </option>
                                    ))}
                                  </select>
                                </label>
                                <label className="team-active-toggle">
                                  <input
                                    type="checkbox"
                                    checked={editDraft.is_active}
                                    onChange={(event) =>
                                      setEditDraft({ ...editDraft, is_active: event.target.checked })
                                    }
                                    disabled={user.id === currentUser.id}
                                  />
                                  Active account
                                </label>
                                <div className="team-edit-actions">
                                  <button
                                    type="button"
                                    onClick={() => handleSaveEdit(user.id)}
                                    disabled={saveSubmitting}
                                  >
                                    {saveSubmitting ? "Saving…" : "Save changes"}
                                  </button>
                                  <button
                                    type="button"
                                    className="secondary-button"
                                    onClick={cancelEdit}
                                    disabled={saveSubmitting}
                                  >
                                    Cancel
                                  </button>
                                </div>
                              </div>
                            </td>
                          </tr>,
                        );
                      }

                      return rows;
                    })
                  )}
                </tbody>
              </table>
            </div>
            </>
          ) : null}
        </div>
      </section>

      <ChickenSwitchModal
        open={pendingDeactivateUser !== null}
        title="Deactivate team member?"
        description="This user will be marked inactive and will not be able to sign in. Their profile stays in SailsPipeline so past work still appears in reports."
        itemName={pendingDeactivateUser?.username}
        switchLabel="Yes, deactivate this user"
        confirmLabel="Deactivate user"
        confirmingLabel="Deactivating..."
        hint="You can reactivate this user later from the Agency users table."
        confirming={
          pendingDeactivateUser !== null && togglingUserId === pendingDeactivateUser.id
        }
        onCancel={() => setPendingDeactivateUser(null)}
        onConfirm={() => void confirmDeactivateUser()}
      />

      <section className="card section-card team-pending-card">
        <header className="section-card-header">
          <h3>Pending invitations</h3>
        </header>
        <div className="section-card-body">
          {!loading ? (
            <div className="team-table-wrap">
              <table className="team-table">
                <thead>
                  <tr>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Expires</th>
                    <th className="team-table-actions-heading">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {openInvites.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="muted">
                        No pending invitations.
                      </td>
                    </tr>
                  ) : (
                    openInvites.map((invite) => (
                      <tr key={invite.id}>
                        <td>{invite.invite_email}</td>
                        <td>{formatRoleLabel(invite.role)}</td>
                        <td>{invite.token_status}</td>
                        <td>{formatTimestamp(invite.expires_at)}</td>
                        <td className="team-table-actions">
                          {invite.token_status === "Pending" ? (
                            <IconTooltip label="Revoke invitation">
                              <button
                                type="button"
                                className="icon-button icon-button-danger"
                                aria-label={`Revoke invitation for ${invite.invite_email}`}
                                disabled={revokingInviteId === invite.id}
                                onClick={() => handleRevokeInvite(invite.id)}
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
