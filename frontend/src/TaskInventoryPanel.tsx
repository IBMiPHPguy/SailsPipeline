import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  deleteAgencyCustomTaskDefinition,
  deleteAgencyTaskTemplate,
  fetchAgencyTaskInventory,
  moveAgencyTaskTemplate,
} from "./api";
import AddTaskToWorkflowModal from "./AddTaskToWorkflowModal";
import ArrowDownIcon from "./ArrowDownIcon";
import ArrowUpIcon from "./ArrowUpIcon";
import ChickenSwitchModal from "./ChickenSwitchModal";
import CustomTaskBuilderModal from "./CustomTaskBuilderModal";
import EditIcon from "./EditIcon";
import IconTooltip from "./IconTooltip";
import PlusIcon from "./PlusIcon";
import TrashIcon from "./TrashIcon";
import TaskInventoryEditModal from "./TaskInventoryEditModal";
import {
  buildTaskInventorySections,
  type WorkflowFilterValue,
} from "./taskInventoryUtils";
import type { AgencyCustomTaskDefinition, AgencyTaskInventoryItem, AgencyWorkflowTemplate } from "./types";
import type { TopStatusBarVariant } from "./TopStatusBar";

type TaskInventoryPanelProps = {
  workflows: AgencyWorkflowTemplate[];
  onDataChange?: () => void | Promise<void>;
  showStatus: (message: string, variant: TopStatusBarVariant) => void;
};

export default function TaskInventoryPanel({ workflows, onDataChange, showStatus }: TaskInventoryPanelProps) {
  const [inventory, setInventory] = useState<AgencyTaskInventoryItem[]>([]);
  const [workflowFilter, setWorkflowFilter] = useState<WorkflowFilterValue>("all");
  const [loading, setLoading] = useState(true);
  const [builderOpen, setBuilderOpen] = useState(false);
  const [editingDefinition, setEditingDefinition] = useState<AgencyCustomTaskDefinition | null>(null);
  const [deletingItem, setDeletingItem] = useState<AgencyTaskInventoryItem | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [removingFromWorkflowItem, setRemovingFromWorkflowItem] = useState<AgencyTaskInventoryItem | null>(null);
  const [removingFromWorkflowId, setRemovingFromWorkflowId] = useState<string | null>(null);
  const [addingToWorkflowItem, setAddingToWorkflowItem] = useState<AgencyTaskInventoryItem | null>(null);
  const [editingItem, setEditingItem] = useState<AgencyTaskInventoryItem | null>(null);
  const [movingTaskId, setMovingTaskId] = useState<string | null>(null);
  const skipWorkflowSyncRef = useRef(true);

  const workflowSyncKey = useMemo(
    () => workflows.map((workflow) => `${workflow.id}:${workflow.task_templates.length}`).join("|"),
    [workflows],
  );

  const loadInventory = useCallback(
    async (options?: { silent?: boolean }) => {
      if (!options?.silent) {
        setLoading(true);
      }
      try {
        const items = await fetchAgencyTaskInventory();
        setInventory(items);
      } catch (loadError) {
        showStatus(loadError instanceof Error ? loadError.message : "Unable to load tasks.", "error");
      } finally {
        if (!options?.silent) {
          setLoading(false);
        }
      }
    },
    [showStatus],
  );

  useEffect(() => {
    void loadInventory();
  }, [loadInventory]);

  useEffect(() => {
    if (skipWorkflowSyncRef.current) {
      skipWorkflowSyncRef.current = false;
      return;
    }
    void loadInventory({ silent: true });
  }, [workflowSyncKey, loadInventory]);

  const inventorySections = useMemo(
    () => buildTaskInventorySections(inventory, workflowFilter, workflows),
    [inventory, workflowFilter, workflows],
  );

  const showInventoryTable = inventorySections.length > 0;

  const sortedWorkflows = useMemo(
    () => [...workflows].sort((left, right) => left.workflow_name.localeCompare(right.workflow_name)),
    [workflows],
  );

  const builtinCount = useMemo(
    () => inventory.filter((item) => item.task_type === "builtin").length,
    [inventory],
  );

  const libraryCount = useMemo(
    () => inventory.filter((item) => item.task_type === "library").length,
    [inventory],
  );

  async function notifyDataChange() {
    await onDataChange?.();
  }

  function openCreateBuilder() {
    setEditingDefinition(null);
    setBuilderOpen(true);
  }

  async function handleInventoryItemSaved() {
    showStatus("Task updated.", "success");
    await loadInventory({ silent: true });
  }

  async function handleSaved() {
    showStatus(editingDefinition ? "Checklist task updated." : "Checklist task created.", "success");
    setEditingDefinition(null);
    await loadInventory({ silent: true });
    await notifyDataChange();
  }

  async function handleTaskAddedToWorkflow() {
    showStatus("Task added to workflow.", "success");
    await loadInventory({ silent: true });
    await notifyDataChange();
  }

  async function confirmDelete() {
    if (!deletingItem?.definition_id) {
      return;
    }

    setDeletingId(deletingItem.definition_id);
    try {
      await deleteAgencyCustomTaskDefinition(deletingItem.definition_id);
      showStatus("Checklist task deleted from agency.", "delete");
      setDeletingItem(null);
      await loadInventory({ silent: true });
    } catch (deleteError) {
      showStatus(deleteError instanceof Error ? deleteError.message : "Unable to delete checklist task.", "error");
    } finally {
      setDeletingId(null);
    }
  }

  async function confirmRemoveFromWorkflow() {
    if (!removingFromWorkflowItem?.task_template_id) {
      return;
    }

    setRemovingFromWorkflowId(removingFromWorkflowItem.task_template_id);
    try {
      await deleteAgencyTaskTemplate(removingFromWorkflowItem.task_template_id);
      showStatus("Task removed from workflow.", "delete");
      setRemovingFromWorkflowItem(null);
      await loadInventory({ silent: true });
      await notifyDataChange();
    } catch (removeError) {
      showStatus(removeError instanceof Error ? removeError.message : "Unable to remove task from workflow.", "error");
    } finally {
      setRemovingFromWorkflowId(null);
    }
  }

  async function handleMoveTask(taskTemplateId: string, direction: "up" | "down") {
    setMovingTaskId(taskTemplateId);
    try {
      await moveAgencyTaskTemplate(taskTemplateId, direction);
      await loadInventory({ silent: true });
    } catch (moveError) {
      showStatus(moveError instanceof Error ? moveError.message : "Unable to reorder task.", "error");
    } finally {
      setMovingTaskId(null);
    }
  }

  return (
    <>
      <section className="open-requests-table-card tasks-table-card">
        <header className="open-requests-table-card-header tasks-table-card-header">
          <div className="open-requests-table-card-header-main tasks-table-card-header-main">
            <div className="tasks-table-title-group">
              <h2>Task inventory</h2>
              <p
                className="meta tasks-inventory-counts"
                aria-label={`${builtinCount} built-in tasks and ${libraryCount} library tasks`}
              >
                <span>{builtinCount} built-in</span>
                <span className="tasks-inventory-count-separator" aria-hidden="true">
                  ·
                </span>
                <span>{libraryCount} library</span>
              </p>
            </div>
          </div>
          <div className="tasks-table-header-actions">
            <label className="tasks-inventory-filter" htmlFor="workflows-task-inventory-filter">
              Workflow
              <select
                id="workflows-task-inventory-filter"
                value={workflowFilter}
                onChange={(event) => setWorkflowFilter(event.target.value as WorkflowFilterValue)}
              >
                <option value="all">All</option>
                <option value="available">Available</option>
                {sortedWorkflows.map((workflow) => (
                  <option key={workflow.id} value={workflow.id}>
                    {workflow.workflow_name}
                  </option>
                ))}
              </select>
            </label>
            <button type="button" className="tasks-create-button" onClick={openCreateBuilder}>
              + Create task
            </button>
          </div>
        </header>

        <div className="open-requests-table-card-body">
          {loading ? (
            <p>Loading tasks...</p>
          ) : !showInventoryTable ? (
            <p>
              {inventory.length === 0 ? "No tasks found." : "No tasks match this workflow filter."}
            </p>
          ) : (
            <div className="tasks-inventory-sections">
              {inventorySections.map((section) => (
                <section
                  key={section.key}
                  className={`tasks-inventory-section${section.kind === "workflow" ? " tasks-inventory-section-workflow" : ""}`}
                >
                  <div className={`tasks-inventory-section-banner ${section.pillClass}`}>{section.label}</div>
                  <div className="open-requests-table-wrap tasks-inventory-section-table-wrap">
                    <table className="open-requests-table tasks-table">
                      <thead>
                        <tr>
                          <th>Task</th>
                          <th>Type</th>
                          <th>Sequence</th>
                          <th>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {section.tasks.map((item, index) => {
                          const isLibrary = item.task_type === "library";
                          const isAvailable = !item.workflow_template_id;
                          const isWorkflowSection = section.kind === "workflow";
                          const taskTemplateId = item.task_template_id;
                          const isMoving = taskTemplateId !== null && movingTaskId === taskTemplateId;
                          const canMoveUp = isWorkflowSection && index > 0 && taskTemplateId !== null;
                          const canMoveDown =
                            isWorkflowSection && index < section.tasks.length - 1 && taskTemplateId !== null;

                          return (
                            <tr key={item.task_key}>
                              <td>
                                <span className="tasks-table-task-title">{item.task_title}</span>
                              </td>
                              <td>
                                <span
                                  className={`tasks-type-badge${
                                    isLibrary ? " tasks-type-badge-library" : " tasks-type-badge-builtin"
                                  }`}
                                >
                                  {isLibrary ? "Library" : "Built-in"}
                                </span>
                              </td>
                              <td className="tasks-table-sequence-cell">
                                {isWorkflowSection ? (
                                  <div className="tasks-table-sequence-controls">
                                    <span className="tasks-table-sequence-number">{item.sequence_order}</span>
                                    <div className="dashboard-table-actions tasks-table-sequence-actions">
                                      <IconTooltip label="Move task up">
                                        <button
                                          type="button"
                                          className="icon-button"
                                          aria-label="Move task up"
                                          disabled={!canMoveUp || isMoving}
                                          onClick={() => {
                                            if (taskTemplateId) {
                                              void handleMoveTask(taskTemplateId, "up");
                                            }
                                          }}
                                        >
                                          <ArrowUpIcon />
                                        </button>
                                      </IconTooltip>
                                      <IconTooltip label="Move task down">
                                        <button
                                          type="button"
                                          className="icon-button"
                                          aria-label="Move task down"
                                          disabled={!canMoveDown || isMoving}
                                          onClick={() => {
                                            if (taskTemplateId) {
                                              void handleMoveTask(taskTemplateId, "down");
                                            }
                                          }}
                                        >
                                          <ArrowDownIcon />
                                        </button>
                                      </IconTooltip>
                                    </div>
                                  </div>
                                ) : (
                                  "—"
                                )}
                              </td>
                              <td className="dashboard-table-actions-cell tasks-table-actions-cell">
                                <div className="dashboard-table-actions">
                                  <IconTooltip label="Edit Task">
                                    <button
                                      type="button"
                                      className="icon-button"
                                      aria-label="Edit Task"
                                      onClick={() => setEditingItem(item)}
                                    >
                                      <EditIcon />
                                    </button>
                                  </IconTooltip>
                                  {isAvailable ? (
                                    <>
                                      <IconTooltip label="Add task to a workflow">
                                        <button
                                          type="button"
                                          className="icon-button icon-button-add-workflow"
                                          aria-label="Add task to a workflow"
                                          onClick={() => setAddingToWorkflowItem(item)}
                                        >
                                          <PlusIcon />
                                        </button>
                                      </IconTooltip>
                                      {isLibrary ? (
                                        <IconTooltip label="Delete Task">
                                          <button
                                            type="button"
                                            className="icon-button icon-button-danger"
                                            aria-label="Delete Task"
                                            disabled={deletingId === item.definition_id}
                                            onClick={() => setDeletingItem(item)}
                                          >
                                            <TrashIcon />
                                          </button>
                                        </IconTooltip>
                                      ) : null}
                                    </>
                                  ) : (
                                    <IconTooltip label="Remove task from workflow">
                                      <button
                                        type="button"
                                        className="icon-button icon-button-danger"
                                        aria-label="Remove task from workflow"
                                        disabled={removingFromWorkflowId === item.task_template_id}
                                        onClick={() => setRemovingFromWorkflowItem(item)}
                                      >
                                        ×
                                      </button>
                                    </IconTooltip>
                                  )}
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </section>
              ))}
            </div>
          )}
        </div>
      </section>

      <TaskInventoryEditModal
        open={editingItem !== null}
        item={editingItem}
        onClose={() => setEditingItem(null)}
        onSaved={handleInventoryItemSaved}
      />

      <AddTaskToWorkflowModal
        open={addingToWorkflowItem !== null}
        task={addingToWorkflowItem}
        workflows={workflows}
        onClose={() => setAddingToWorkflowItem(null)}
        onAdded={handleTaskAddedToWorkflow}
      />

      <CustomTaskBuilderModal
        open={builderOpen}
        definition={editingDefinition}
        placementWorkflow={null}
        onClose={() => {
          setBuilderOpen(false);
          setEditingDefinition(null);
        }}
        onSaved={handleSaved}
      />

      <ChickenSwitchModal
        open={deletingItem !== null}
        title="Delete task from agency?"
        description={`"${deletingItem?.task_title ?? "This task"}" will be permanently deleted from your agency. This action is destructive and cannot be reversed.`}
        switchLabel="Yes, permanently delete this task from the agency"
        confirmLabel="Delete task"
        confirmingLabel="Deleting..."
        hint="The task will be removed from your library and cannot be recovered."
        confirming={deletingItem !== null && deletingId === deletingItem.definition_id}
        onCancel={() => setDeletingItem(null)}
        onConfirm={() => void confirmDelete()}
      />

      <ChickenSwitchModal
        open={removingFromWorkflowItem !== null}
        title="Remove task from workflow?"
        description={`This removes "${removingFromWorkflowItem?.task_title ?? "the task"}" from ${removingFromWorkflowItem?.workflow_name ?? "the workflow"}. The task becomes available again and can be added to another workflow.`}
        switchLabel={`Yes, remove this task from ${removingFromWorkflowItem?.workflow_name ?? "the workflow"}`}
        confirmLabel="Remove from workflow"
        confirmingLabel="Removing..."
        hint="This does not delete the task from your agency."
        confirming={
          removingFromWorkflowItem !== null &&
          removingFromWorkflowId === removingFromWorkflowItem.task_template_id
        }
        onCancel={() => setRemovingFromWorkflowItem(null)}
        onConfirm={() => void confirmRemoveFromWorkflow()}
      />
    </>
  );
}
