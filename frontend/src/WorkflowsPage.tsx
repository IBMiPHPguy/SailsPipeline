import { useCallback, useEffect, useMemo, useState } from "react";
import { deleteAgencyWorkflowTemplate, fetchAgencyWorkflowTemplates } from "./api";
import ChickenSwitchModal from "./ChickenSwitchModal";
import CreateWorkflowModal from "./CreateWorkflowModal";
import EditIcon from "./EditIcon";
import IconTooltip from "./IconTooltip";
import TaskInventoryPanel from "./TaskInventoryPanel";
import TopStatusBar from "./TopStatusBar";
import WorkflowTemplateEditModal from "./WorkflowTemplateEditModal";
import type { AgencyWorkflowTemplate } from "./types";
import { useTopStatusBar } from "./useTopStatusBar";

function formatTaskCount(count: number): string {
  return count === 1 ? "1 task" : `${count} tasks`;
}

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<AgencyWorkflowTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<AgencyWorkflowTemplate | null>(null);
  const [deletingTemplate, setDeletingTemplate] = useState<AgencyWorkflowTemplate | null>(null);
  const [deletingTemplateId, setDeletingTemplateId] = useState<string | null>(null);
  const { status, showStatus, clearStatus } = useTopStatusBar();

  const loadWorkflows = useCallback(
    async (options?: { silent?: boolean }) => {
      if (!options?.silent) {
        setLoading(true);
      }
      try {
        const items = await fetchAgencyWorkflowTemplates();
        setWorkflows(items);
      } catch (loadError) {
        showStatus(loadError instanceof Error ? loadError.message : "Unable to load workflows.", "error");
      } finally {
        if (!options?.silent) {
          setLoading(false);
        }
      }
    },
    [showStatus],
  );

  useEffect(() => {
    void loadWorkflows();
  }, [loadWorkflows]);

  const sortedWorkflows = useMemo(
    () => [...workflows].sort((left, right) => left.workflow_name.localeCompare(right.workflow_name)),
    [workflows],
  );

  async function confirmDeleteWorkflow() {
    if (!deletingTemplate) {
      return;
    }

    setDeletingTemplateId(deletingTemplate.id);
    try {
      await deleteAgencyWorkflowTemplate(deletingTemplate.id);
      showStatus("Workflow removed. Its tasks are now available.", "delete");
      setDeletingTemplate(null);
      await loadWorkflows({ silent: true });
    } catch (deleteError) {
      showStatus(deleteError instanceof Error ? deleteError.message : "Unable to remove workflow.", "error");
    } finally {
      setDeletingTemplateId(null);
    }
  }

  return (
    <section className="workflows-settings-page workflows-tasks-page">
      <TopStatusBar status={status} onDismiss={clearStatus} />

      <header className="request-summary-card request-summary-card-compact workflows-summary-card">
        <div className="request-summary-compact-main">
          <h1>Workflows &amp; Tasks</h1>
          <p className="meta">
            Manage agency workflows and the built-in and library checklist tasks assigned to them.
          </p>
        </div>
      </header>

      <section className="open-requests-table-card agency-workflows-table-card">
        <header className="open-requests-table-card-header agency-workflows-table-card-header">
          <div className="open-requests-table-card-header-main">
            <h2>Agency workflows</h2>
          </div>
          <button type="button" className="agency-workflows-create-button" onClick={() => setCreateModalOpen(true)}>
            + Create Workflow
          </button>
        </header>

        <div className="open-requests-table-card-body">
          {loading ? (
            <p>Loading workflows...</p>
          ) : sortedWorkflows.length === 0 ? (
            <p className="meta">No workflows yet. Create one to start assigning tasks.</p>
          ) : (
            <div className="open-requests-table-wrap">
              <table className="open-requests-table agency-workflows-table">
                <thead>
                  <tr>
                    <th>Workflow</th>
                    <th>Tasks</th>
                    <th>Type</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedWorkflows.map((workflow) => {
                    const isRecommended = Boolean(workflow.workflow_type_key);
                    const taskCount = workflow.task_templates.length;

                    return (
                      <tr key={workflow.id}>
                        <td>
                          <span className="agency-workflows-table-name">{workflow.workflow_name}</span>
                        </td>
                        <td>{formatTaskCount(taskCount)}</td>
                        <td>
                          <span
                            className={`agency-workflows-type-badge${
                              isRecommended
                                ? " agency-workflows-type-badge-recommended"
                                : " agency-workflows-type-badge-custom"
                            }`}
                          >
                            {isRecommended ? "Recommended" : "Custom"}
                          </span>
                        </td>
                        <td className="dashboard-table-actions-cell">
                          <div className="dashboard-table-actions">
                            <IconTooltip label="Edit Workflow">
                              <button
                                type="button"
                                className="icon-button"
                                aria-label="Edit Workflow"
                                onClick={() => setEditingTemplate(workflow)}
                              >
                                <EditIcon />
                              </button>
                            </IconTooltip>
                            <IconTooltip label="Remove workflow">
                              <button
                                type="button"
                                className="icon-button icon-button-danger"
                                aria-label="Remove workflow"
                                disabled={deletingTemplateId === workflow.id}
                                onClick={() => setDeletingTemplate(workflow)}
                              >
                                ×
                              </button>
                            </IconTooltip>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      <TaskInventoryPanel
        workflows={workflows}
        showStatus={showStatus}
        onDataChange={() => loadWorkflows({ silent: true })}
      />

      <CreateWorkflowModal
        open={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onCreated={async () => {
          showStatus("Workflow created.", "success");
          await loadWorkflows({ silent: true });
        }}
      />

      <WorkflowTemplateEditModal
        open={editingTemplate !== null}
        template={editingTemplate}
        onClose={() => setEditingTemplate(null)}
        onSaved={async () => {
          showStatus("Workflow updated.", "success");
          await loadWorkflows({ silent: true });
        }}
      />

      <ChickenSwitchModal
        open={deletingTemplate !== null}
        title="Remove workflow?"
        description={`"${deletingTemplate?.workflow_name ?? "This workflow"}" will be removed from your active workflow list. ${formatTaskCount(deletingTemplate?.task_templates.length ?? 0)} will become available and can be added to other workflows. Completed request history is preserved.`}
        switchLabel={`Yes, remove ${deletingTemplate?.workflow_name ?? "this workflow"}`}
        confirmLabel="Remove workflow"
        confirmingLabel="Removing..."
        hint="The workflow is archived for audit history and will not reappear in pickers."
        confirming={deletingTemplate !== null && deletingTemplateId === deletingTemplate.id}
        onCancel={() => setDeletingTemplate(null)}
        onConfirm={() => void confirmDeleteWorkflow()}
      />
    </section>
  );
}
