import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  fetchAgencySettings,
  updateAgencySettings,
  type AgentConfigurablePermissions,
} from "./agencySettingsApi";
import YesNoPillToggle from "./YesNoPillToggle";

const DEFAULT_PERMISSIONS: AgentConfigurablePermissions = {
  view_other_agent_requests: false,
  manage_other_agent_requests: false,
  create_own_groups: false,
  manage_other_agent_groups: false,
  book_other_agent_groups: false,
};

function normalizeDraft(permissions: AgentConfigurablePermissions): AgentConfigurablePermissions {
  const viewOther = permissions.view_other_agent_requests || permissions.manage_other_agent_requests;
  const createOwn = permissions.create_own_groups;
  return {
    view_other_agent_requests: viewOther,
    manage_other_agent_requests: viewOther ? permissions.manage_other_agent_requests : false,
    create_own_groups: createOwn,
    manage_other_agent_groups: createOwn ? permissions.manage_other_agent_groups : false,
    book_other_agent_groups: permissions.book_other_agent_groups,
  };
}

export default function AgencyAgentPermissionsCard() {
  const [draft, setDraft] = useState<AgentConfigurablePermissions>(DEFAULT_PERMISSIONS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadPermissions = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const settings = await fetchAgencySettings();
      setDraft(normalizeDraft(settings.agent_permissions ?? DEFAULT_PERMISSIONS));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load agent permissions.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadPermissions();
  }, [loadPermissions]);

  function updatePermission<K extends keyof AgentConfigurablePermissions>(
    key: K,
    value: AgentConfigurablePermissions[K],
  ) {
    setDraft((current) => {
      const next = { ...current, [key]: value };
      if (key === "view_other_agent_requests" && !value) {
        next.manage_other_agent_requests = false;
      }
      if (key === "create_own_groups" && !value) {
        next.manage_other_agent_groups = false;
      }
      return normalizeDraft(next);
    });
    setSuccess("");
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving) {
      return;
    }

    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const payload = normalizeDraft(draft);
      const updated = await updateAgencySettings({ agent_permissions: payload });
      setDraft(normalizeDraft(updated.agent_permissions ?? payload));
      setSuccess("Agent permissions saved.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to save agent permissions.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <section className="card section-card">
        <header className="section-card-header">
          <div>
            <h3>Agent permissions</h3>
            <p className="muted">Loading agency-wide agent access rules…</p>
          </div>
        </header>
      </section>
    );
  }

  return (
    <section className="card section-card agency-agent-permissions-card">
      <header className="section-card-header">
        <div>
          <h3>Agent permissions</h3>
          <p className="muted">
            Agency-wide defaults for what tenant agents can view and manage. Super users remain unrestricted.
          </p>
        </div>
      </header>
      <div className="section-card-body">
        {error ? <p className="status error">{error}</p> : null}
        {success ? <p className="status success">{success}</p> : null}

        <form className="agency-agent-permissions-form" onSubmit={(event) => void handleSave(event)}>
          <YesNoPillToggle
            label="View other agents' requests"
            value={draft.view_other_agent_requests}
            onChange={(value) => updatePermission("view_other_agent_requests", value)}
          />
          <YesNoPillToggle
            label="Manage other agents' requests"
            value={draft.manage_other_agent_requests}
            disabled={!draft.view_other_agent_requests}
            onChange={(value) => updatePermission("manage_other_agent_requests", value)}
          />
          <YesNoPillToggle
            label="Create and manage own group blocks"
            value={draft.create_own_groups}
            onChange={(value) => updatePermission("create_own_groups", value)}
          />
          <YesNoPillToggle
            label="Manage other agents' group blocks"
            value={draft.manage_other_agent_groups}
            disabled={!draft.create_own_groups}
            onChange={(value) => updatePermission("manage_other_agent_groups", value)}
          />
          <YesNoPillToggle
            label="Book into other agents' group blocks"
            value={draft.book_other_agent_groups}
            onChange={(value) => updatePermission("book_other_agent_groups", value)}
          />

          <div className="agency-settings-actions">
            <button type="submit" className="modal-primary" disabled={saving}>
              {saving ? "Saving…" : "Save agent permissions"}
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}
