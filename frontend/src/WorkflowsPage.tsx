import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  createAgencyTaskTemplate,
  createAgencyWorkflowTemplate,
  deleteAgencyTaskTemplate,
  deleteAgencyWorkflowTemplate,
  fetchAgencyTaskAvailability,
  fetchAgencyTaskCatalog,
  fetchAgencyWorkflowTemplates,
  moveAgencyTaskTemplate,
  updateAgencyTaskTemplate,
} from "./api";
import EditIcon from "./EditIcon";
import IconTooltip from "./IconTooltip";
import TaskLibraryModal, { TaskTypeBadge } from "./TaskLibraryModal";
import type { AgencyTaskCatalogItem, AgencyTaskTemplate, AgencyWorkflowTemplate } from "./types";
import ChickenSwitchModal from "./ChickenSwitchModal";
import TopStatusBar from "./TopStatusBar";
import WorkflowTaskMoveModal from "./WorkflowTaskMoveModal";
import WorkflowTaskPickerModal from "./WorkflowTaskPickerModal";
import WorkflowTemplateEditModal from "./WorkflowTemplateEditModal";
import { useTopStatusBar } from "./useTopStatusBar";

function ArrowUpIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="m12 19V5" />
      <path d="m5 12 7-7 7 7" />
    </svg>
  );
}

function ArrowDownIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="m12 5v14" />
      <path d="m19 12-7 7-7-7" />
    </svg>
  );
}

function TransferIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M7 7h11" />
      <path d="m14 4 4 3-4 3" />
      <path d="M17 17H6" />
      <path d="m10 20-4-3 4-3" />
    </svg>
  );
}

function formatTaskCount(count: number): string {
  return count === 1 ? "1 task" : `${count} tasks`;
}

export default function WorkflowsPage() {
  const [templates, setTemplates] = useState<AgencyWorkflowTemplate[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [catalog, setCatalog] = useState<AgencyTaskCatalogItem[]>([]);
  const [availableCount, setAvailableCount] = useState(0);
  const [availableTasks, setAvailableTasks] = useState<AgencyTaskCatalogItem[]>([]);
  const [placedTaskKeys, setPlacedTaskKeys] = useState<Set<string>>(new Set());
  const [libraryOpen, setLibraryOpen] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [movingTask, setMovingTask] = useState<AgencyTaskTemplate | null>(null);
  const [removingTask, setRemovingTask] = useState<AgencyTaskTemplate | null>(null);
  const [deletingTaskId, setDeletingTaskId] = useState<string | null>(null);
  const { status, showStatus, clearStatus } = useTopStatusBar();
  const [newWorkflowName, setNewWorkflowName] = useState("");
  const [newWorkflowDescription, setNewWorkflowDescription] = useState("");
  const [creatingWorkflow, setCreatingWorkflow] = useState(false);
  const [quickAddTitle, setQuickAddTitle] = useState("");
  const [addingTask, setAddingTask] = useState(false);
  const [savingTaskId, setSavingTaskId] = useState<string | null>(null);
  const [movingTaskId, setMovingTaskId] = useState<string | null>(null);
  const [editingTemplate, setEditingTemplate] = useState<AgencyWorkflowTemplate | null>(null);

  const loadTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const [items, availability] = await Promise.all([
        fetchAgencyWorkflowTemplates(),
        fetchAgencyTaskAvailability(),
      ]);
      setTemplates(items);
      setAvailableCount(availability.available_count);
      setAvailableTasks(availability.available_tasks);
      setPlacedTaskKeys(new Set(availability.placed_task_keys));
      setSelectedTemplateId((current) => {
        if (current && items.some((item) => item.id === current)) {
          return current;
        }
        return items[0]?.id ?? null;
      });
    } catch (loadError) {
      showStatus(
        loadError instanceof Error ? loadError.message : "Unable to load workflows.",
        "error",
      );
    } finally {
      setLoading(false);
    }
  }, [showStatus]);

  useEffect(() => {
    void loadTemplates();
  }, [loadTemplates]);

  useEffect(() => {
    let cancelled = false;
    void fetchAgencyTaskCatalog()
      .then((items) => {
        if (!cancelled) {
          setCatalog(items);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setCatalog([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedTemplate = useMemo(
    () => templates.find((template) => template.id === selectedTemplateId) ?? null,
    [selectedTemplateId, templates],
  );

  const sortedTasks = useMemo(
    () =>
      selectedTemplate
        ? [...selectedTemplate.task_templates].sort((left, right) => left.sequence_order - right.sequence_order)
        : [],
    [selectedTemplate],
  );

  const canMoveBetweenWorkflows = templates.length > 1;

  async function handleCreateWorkflow(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = newWorkflowName.trim();
    if (!name) {
      return;
    }

    setCreatingWorkflow(true);
    try {
      const created = await createAgencyWorkflowTemplate({
        workflow_name: name,
        description: newWorkflowDescription.trim() || null,
      });
      setNewWorkflowName("");
      setNewWorkflowDescription("");
      showStatus("Workflow created.", "success");
      setSelectedTemplateId(created.id);
      await loadTemplates();
    } catch (createError) {
      showStatus(
        createError instanceof Error ? createError.message : "Unable to create workflow.",
        "error",
      );
    } finally {
      setCreatingWorkflow(false);
    }
  }

  async function handleAddChecklistTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedTemplate) {
      return;
    }
    const title = quickAddTitle.trim();
    if (!title) {
      return;
    }

    setAddingTask(true);
    try {
      await createAgencyTaskTemplate(selectedTemplate.id, title);
      setQuickAddTitle("");
      showStatus("Task appended to sequence.", "success");
      await loadTemplates();
    } catch (addError) {
      showStatus(addError instanceof Error ? addError.message : "Unable to add task.", "error");
    } finally {
      setAddingTask(false);
    }
  }

  async function handleCatalogTaskAdded() {
    showStatus("Task added to sequence.", "success");
    await loadTemplates();
  }

  async function handleTaskMoved() {
    showStatus("Task moved to workflow.", "success");
    await loadTemplates();
  }

  function requestDeleteTask(task: AgencyTaskTemplate) {
    if (task.task_key) {
      setRemovingTask(task);
      return;
    }
    void handleDeleteTask(task.id);
  }

  async function confirmDeleteTask() {
    if (!removingTask) {
      return;
    }
    setDeletingTaskId(removingTask.id);
    try {
      await deleteAgencyTaskTemplate(removingTask.id);
      showStatus("Task removed from workflow.", "delete");
      setRemovingTask(null);
      await loadTemplates();
    } catch (deleteError) {
      showStatus(deleteError instanceof Error ? deleteError.message : "Unable to delete task.", "error");
    } finally {
      setDeletingTaskId(null);
    }
  }

  async function handleRenameTask(task: AgencyTaskTemplate, nextTitle: string) {
    const title = nextTitle.trim();
    if (!title || title === task.task_title) {
      return;
    }

    setSavingTaskId(task.id);
    try {
      await updateAgencyTaskTemplate(task.id, title);
      await loadTemplates();
    } catch (renameError) {
      showStatus(renameError instanceof Error ? renameError.message : "Unable to rename task.", "error");
    } finally {
      setSavingTaskId(null);
    }
  }

  async function handleDeleteTask(taskId: string) {
    try {
      await deleteAgencyTaskTemplate(taskId);
      showStatus("Task removed from workflow.", "delete");
      await loadTemplates();
    } catch (deleteError) {
      showStatus(deleteError instanceof Error ? deleteError.message : "Unable to delete task.", "error");
    }
  }

  async function handleMoveTask(taskId: string, direction: "up" | "down") {
    setMovingTaskId(taskId);
    try {
      await moveAgencyTaskTemplate(taskId, direction);
      await loadTemplates();
    } catch (moveError) {
      showStatus(moveError instanceof Error ? moveError.message : "Unable to reorder task.", "error");
    } finally {
      setMovingTaskId(null);
    }
  }

  async function handleDeleteTemplate(template: AgencyWorkflowTemplate) {
    if (template.workflow_type_key) {
      showStatus("Recommended workflows cannot be deleted.", "error");
      return;
    }

    try {
      await deleteAgencyWorkflowTemplate(template.id);
      showStatus("Workflow deleted.", "delete");
      await loadTemplates();
    } catch (deleteError) {
      showStatus(
        deleteError instanceof Error ? deleteError.message : "Unable to delete workflow.",
        "error",
      );
    }
  }

  return (
    <section className="workflows-settings-page">
      <TopStatusBar status={status} onDismiss={clearStatus} />

      <header className="request-summary-card request-summary-card-compact workflows-summary-card">
        <div className="request-summary-compact-row">
          <div className="request-summary-compact-title">
            <h2>Workflows and Tasks</h2>
          </div>
        </div>
        <div className="request-summary-compact-meta">
          <span>Recommended workflow templates and task sequencing for your agency.</span>
        </div>
      </header>

      {loading ? (
        <p className="meta">Loading workflows...</p>
      ) : (
        <div className="workflows-settings-grid">
          <aside className="workflows-settings-left">
            <section className="section-card workflows-settings-section-card">
              <div className="workflows-settings-section-header">
                <h3>Create New Workflow</h3>
              </div>
              <div className="section-card-body workflows-settings-section-body">
                <form className="workflows-settings-create-form" onSubmit={handleCreateWorkflow}>
                  <label>
                    Enter workflow name
                    <input
                      type="text"
                      value={newWorkflowName}
                      placeholder="Enter workflow name..."
                      disabled={creatingWorkflow}
                      onChange={(event) => setNewWorkflowName(event.target.value)}
                    />
                  </label>
                  <label>
                    <span>
                      Description <span className="field-optional">(Optional)</span>
                    </span>
                    <textarea
                      rows={3}
                      value={newWorkflowDescription}
                      placeholder="Short summary shown in the workflow sequencer"
                      disabled={creatingWorkflow}
                      onChange={(event) => setNewWorkflowDescription(event.target.value)}
                    />
                  </label>
                  <button type="submit" disabled={creatingWorkflow || !newWorkflowName.trim()}>
                    {creatingWorkflow ? "Creating..." : "+ Create Workflow"}
                  </button>
                </form>
              </div>
            </section>

            <section className="section-card workflows-settings-section-card workflows-settings-available-card">
              <div className="workflows-settings-section-header">
                <h3>Available tasks</h3>
              </div>
              <div className="section-card-body workflows-settings-section-body">
                <p className="workflows-settings-available-summary">
                  <span className="workflows-settings-available-count">{availableCount}</span>
                  <span>
                    {availableCount === 1 ? "task" : "tasks"} not on any workflow yet
                  </span>
                </p>
                <button type="button" className="workflows-settings-library-button" onClick={() => setLibraryOpen(true)}>
                  View library
                </button>
              </div>
            </section>

            <section className="section-card workflows-settings-section-card workflows-settings-agency-card">
              <div className="workflows-settings-section-header">
                <h3>Agency Workflows</h3>
              </div>
              <div className="section-card-body workflows-settings-section-body">
                <ul className="workflows-settings-list">
                  {templates.map((template) => {
                    const isSelected = template.id === selectedTemplateId;
                    return (
                      <li
                        key={template.id}
                        className={`workflows-settings-list-row${isSelected ? " is-selected" : ""}`}
                      >
                        <button
                          type="button"
                          className="workflows-settings-list-item"
                          onClick={() => setSelectedTemplateId(template.id)}
                        >
                          <span className="workflows-settings-list-item-text">
                            <span className="workflows-settings-list-item-name">{template.workflow_name}</span>
                            <span className="workflows-settings-list-item-meta">
                              {formatTaskCount(template.task_templates.length)}
                            </span>
                          </span>
                          {template.workflow_type_key ? (
                            <span className="workflows-settings-list-item-badge">Recommended</span>
                          ) : null}
                        </button>
                        <IconTooltip label="Edit Workflow" placement="below" align="end">
                          <button
                            type="button"
                            className="icon-button workflows-settings-list-edit"
                            aria-label="Edit Workflow"
                            onClick={() => setEditingTemplate(template)}
                          >
                            <EditIcon />
                          </button>
                        </IconTooltip>
                      </li>
                    );
                  })}
                </ul>
              </div>
            </section>
          </aside>

          <section className="section-card workflows-settings-right workflows-settings-section-card">
            <div className="workflows-settings-section-header">
              <h3>Workflow Sequencer</h3>
            </div>
            <div className="section-card-body workflows-settings-section-body">
              {selectedTemplate ? (
                <>
                  <div className="workflows-settings-detail-header">
                    <div>
                      <h2 className="workflows-settings-active-title">{selectedTemplate.workflow_name}</h2>
                      {selectedTemplate.description ? (
                        <p className="meta">{selectedTemplate.description}</p>
                      ) : (
                        <p className="meta">Define the ordered checklist agents follow on travel requests. Remove tasks you do not use — they will not be re-added.</p>
                      )}
                    </div>
                    {!selectedTemplate.workflow_type_key ? (
                      <button
                        type="button"
                        className="workflows-settings-delete-button"
                        onClick={() => void handleDeleteTemplate(selectedTemplate)}
                      >
                        Delete workflow
                      </button>
                    ) : null}
                  </div>

                  <div className="workflows-settings-detail-divider" aria-hidden="true" />

                  <h3 className="workflows-settings-ledger-title">Task Sequence Ledger</h3>
                  {sortedTasks.length === 0 ? (
                    <p className="meta workflows-settings-ledger-empty">
                      No tasks yet. Add a built-in step from the task library or create a checklist task.
                    </p>
                  ) : (
                    <ol className="workflows-settings-task-list">
                      {sortedTasks.map((task, index) => (
                        <li key={task.id} className="workflows-settings-task-row">
                          <span className="workflows-settings-task-index">{index + 1}.</span>
                          <div className="workflows-settings-task-main">
                            <input
                              className="workflows-settings-task-input"
                              type="text"
                              defaultValue={task.task_title}
                              disabled={savingTaskId === task.id}
                              onBlur={(event) => void handleRenameTask(task, event.target.value)}
                              onKeyDown={(event) => {
                                if (event.key === "Enter") {
                                  event.currentTarget.blur();
                                }
                              }}
                            />
                            <TaskTypeBadge task={task} />
                          </div>
                          <div className="workflows-settings-task-actions">
                            <button
                              type="button"
                              className="icon-button"
                              aria-label="Move task up"
                              disabled={movingTaskId === task.id || index === 0}
                              onClick={() => void handleMoveTask(task.id, "up")}
                            >
                              <ArrowUpIcon />
                            </button>
                            <button
                              type="button"
                              className="icon-button"
                              aria-label="Move task down"
                              disabled={movingTaskId === task.id || index === sortedTasks.length - 1}
                              onClick={() => void handleMoveTask(task.id, "down")}
                            >
                              <ArrowDownIcon />
                            </button>
                            <IconTooltip
                              label={
                                canMoveBetweenWorkflows
                                  ? "Move task to another workflow"
                                  : "Create another workflow to move tasks"
                              }
                              placement="below"
                              align="end"
                            >
                              <button
                                type="button"
                                className="icon-button"
                                aria-label="Move task to another workflow"
                                disabled={!canMoveBetweenWorkflows || movingTaskId === task.id}
                                onClick={() => setMovingTask(task)}
                              >
                                <TransferIcon />
                              </button>
                            </IconTooltip>
                            <button
                              type="button"
                              className="icon-button icon-button-danger"
                              aria-label="Remove task from workflow"
                              onClick={() => requestDeleteTask(task)}
                            >
                              ×
                            </button>
                          </div>
                        </li>
                      ))}
                    </ol>
                  )}

                  <div className="workflows-settings-add-tasks">
                    <button
                      type="button"
                      className="workflows-settings-builtin-add-button"
                      disabled={availableCount === 0}
                      onClick={() => setPickerOpen(true)}
                    >
                      + Add task
                    </button>

                    <form className="workflows-settings-checklist-add" onSubmit={handleAddChecklistTask}>
                      <label>
                        Add checklist task
                        <input
                          type="text"
                          value={quickAddTitle}
                          placeholder="Type checklist step..."
                          disabled={addingTask}
                          onChange={(event) => setQuickAddTitle(event.target.value)}
                        />
                      </label>
                      <button type="submit" disabled={addingTask || !quickAddTitle.trim()}>
                        {addingTask ? "Adding..." : "+ Add checklist task"}
                      </button>
                    </form>
                  </div>
                </>
              ) : (
                <p className="meta">Create a workflow to begin defining tasks.</p>
              )}
            </div>
          </section>
        </div>
      )}

      <WorkflowTemplateEditModal
        open={editingTemplate !== null}
        template={editingTemplate}
        onClose={() => setEditingTemplate(null)}
        onSaved={async () => {
          showStatus("Workflow updated.", "success");
          await loadTemplates();
        }}
      />

      <TaskLibraryModal
        open={libraryOpen}
        catalog={catalog}
        placedTaskKeys={placedTaskKeys}
        availableCount={availableCount}
        onClose={() => setLibraryOpen(false)}
      />

      <WorkflowTaskPickerModal
        open={pickerOpen}
        workflow={selectedTemplate}
        availableTasks={availableTasks}
        onClose={() => setPickerOpen(false)}
        onAdded={handleCatalogTaskAdded}
      />

      <WorkflowTaskMoveModal
        open={movingTask !== null}
        task={movingTask}
        sourceWorkflow={selectedTemplate}
        workflows={templates}
        onClose={() => setMovingTask(null)}
        onMoved={handleTaskMoved}
      />

      <ChickenSwitchModal
        open={removingTask !== null && selectedTemplate !== null}
        title="Remove task from workflow?"
        description={`This removes "${removingTask?.task_title ?? "the task"}" from ${selectedTemplate?.workflow_name ?? "the workflow"}. The task returns to the available library and can be added to another workflow.`}
        switchLabel={`Yes, remove this task from ${selectedTemplate?.workflow_name ?? "the workflow"}`}
        confirmLabel="Remove from workflow"
        confirmingLabel="Removing..."
        hint="You can add this task back from Available tasks or the task picker."
        confirming={removingTask !== null && deletingTaskId === removingTask.id}
        onCancel={() => setRemovingTask(null)}
        onConfirm={() => void confirmDeleteTask()}
      />
    </section>
  );
}
