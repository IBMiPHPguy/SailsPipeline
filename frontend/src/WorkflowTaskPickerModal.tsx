import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { createAgencyTaskFromCatalog, createAgencyTaskFromCustomDefinition } from "./api";
import WorkflowSequencePositionFieldset, { type InsertPosition } from "./WorkflowSequencePositionFieldset";
import type { AgencyTaskCatalogItem, AgencyWorkflowTemplate } from "./types";

type PickerStep = "browse" | "custom-position";

type WorkflowTaskPickerModalProps = {
  open: boolean;
  workflow: AgencyWorkflowTemplate | null;
  availableTasks: AgencyTaskCatalogItem[];
  availableCustomTasks: AgencyTaskCatalogItem[];
  onClose: () => void;
  onAdded: () => void | Promise<void>;
  onCreateCustom: () => void;
};

function filterTasks(tasks: AgencyTaskCatalogItem[], query: string) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    return tasks;
  }
  return tasks.filter(
    (task) =>
      task.task_title.toLowerCase().includes(normalized) ||
      task.description.toLowerCase().includes(normalized) ||
      task.task_key.toLowerCase().includes(normalized),
  );
}

export default function WorkflowTaskPickerModal({
  open,
  workflow,
  availableTasks,
  availableCustomTasks,
  onClose,
  onAdded,
  onCreateCustom,
}: WorkflowTaskPickerModalProps) {
  const [step, setStep] = useState<PickerStep>("browse");
  const [query, setQuery] = useState("");
  const [pendingCustomTask, setPendingCustomTask] = useState<AgencyTaskCatalogItem | null>(null);
  const [insertPosition, setInsertPosition] = useState<InsertPosition>(null);
  const [addingTaskKey, setAddingTaskKey] = useState<string | null>(null);
  const [error, setError] = useState("");

  const workflowTasks = useMemo(
    () =>
      workflow
        ? [...workflow.task_templates].sort((left, right) => left.sequence_order - right.sequence_order)
        : [],
    [workflow],
  );

  useEffect(() => {
    if (!open) {
      setStep("browse");
      setQuery("");
      setPendingCustomTask(null);
      setInsertPosition(null);
      setAddingTaskKey(null);
      setError("");
    }
  }, [open]);

  useEffect(() => {
    if (step === "custom-position") {
      setInsertPosition(workflowTasks.length === 0 ? 1 : null);
      setError("");
    }
  }, [step, workflowTasks.length]);

  const filteredBuiltInTasks = useMemo(
    () => filterTasks(availableTasks, query),
    [availableTasks, query],
  );
  const filteredCustomTasks = useMemo(
    () => filterTasks(availableCustomTasks, query),
    [availableCustomTasks, query],
  );

  const totalAvailable = availableTasks.length + availableCustomTasks.length;

  if (!open || !workflow) {
    return null;
  }

  function handleClose() {
    if (addingTaskKey !== null) {
      return;
    }
    onClose();
  }

  function handleBackToBrowse() {
    if (addingTaskKey !== null) {
      return;
    }
    setStep("browse");
    setPendingCustomTask(null);
    setInsertPosition(null);
    setError("");
  }

  function handleStartAddCustom(task: AgencyTaskCatalogItem) {
    setPendingCustomTask(task);
    setStep("custom-position");
    setError("");
  }

  async function handleAddBuiltIn(task: AgencyTaskCatalogItem) {
    setAddingTaskKey(task.task_key);
    setError("");
    try {
      await createAgencyTaskFromCatalog(workflow.id, task.task_key);
      await onAdded();
      onClose();
    } catch (addError) {
      setError(addError instanceof Error ? addError.message : "Unable to add task.");
    } finally {
      setAddingTaskKey(null);
    }
  }

  async function handleConfirmAddCustom() {
    if (!pendingCustomTask) {
      return;
    }

    setAddingTaskKey(pendingCustomTask.task_key);
    setError("");
    try {
      await createAgencyTaskFromCustomDefinition(
        workflow.id,
        pendingCustomTask.task_key,
        insertPosition === null ? null : insertPosition,
      );
      await onAdded();
      onClose();
    } catch (addError) {
      setError(addError instanceof Error ? addError.message : "Unable to add checklist task.");
    } finally {
      setAddingTaskKey(null);
    }
  }

  function renderTaskRow(
    task: AgencyTaskCatalogItem,
    onAdd: (task: AgencyTaskCatalogItem) => void,
    actionLabel = "Add",
  ) {
    const isAdding = addingTaskKey === task.task_key;
    return (
      <li key={task.task_key} className="modal-section-panel workflow-task-picker-row">
        <div className="workflow-task-picker-row-main">
          <div className="workflow-task-picker-row-text">
            <h4 className="workflow-task-picker-row-title">{task.task_title}</h4>
            {task.description ? (
              <p className="meta workflow-task-picker-row-description">{task.description}</p>
            ) : null}
          </div>
          <button
            type="button"
            className="workflow-task-picker-add-button"
            disabled={addingTaskKey !== null}
            onClick={() => onAdd(task)}
          >
            {isAdding ? "Adding..." : actionLabel}
          </button>
        </div>
      </li>
    );
  }

  const title = step === "browse" ? "Add task to workflow" : "Choose position in sequence";

  return createPortal(
    <div className="modal-backdrop modal-backdrop-scroll" role="presentation" onClick={handleClose}>
      <div
        className="modal-card modal-card-wide workflow-task-picker-modal"
        role="dialog"
        aria-labelledby="workflow-task-picker-title"
        aria-modal="true"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="modal-card-header">
          <h3 id="workflow-task-picker-title">{title}</h3>
        </header>

        <div className="modal-scroll-body workflow-task-picker-body">
          <div className="modal-meta-row">
            <span>{workflow.workflow_name}</span>
            {step === "browse" ? (
              <>
                <span className="modal-meta-separator" aria-hidden="true">
                  |
                </span>
                <span>
                  {totalAvailable} available {totalAvailable === 1 ? "task" : "tasks"}
                </span>
              </>
            ) : pendingCustomTask ? (
              <>
                <span className="modal-meta-separator" aria-hidden="true">
                  |
                </span>
                <span>{pendingCustomTask.task_title}</span>
              </>
            ) : null}
          </div>

          {error ? <p className="status error">{error}</p> : null}

          {step === "browse" ? (
            <>
              <label className="workflow-task-picker-search">
                Search tasks
                <input
                  type="search"
                  value={query}
                  placeholder="Filter by title or description..."
                  disabled={addingTaskKey !== null}
                  onChange={(event) => setQuery(event.target.value)}
                />
              </label>

              {availableTasks.length > 0 ? (
                <section className="workflow-task-picker-section">
                  <h4 className="workflow-task-picker-section-title">Built-in tasks</h4>
                  {filteredBuiltInTasks.length === 0 ? (
                    <p className="meta workflow-task-picker-empty">No built-in tasks match your search.</p>
                  ) : (
                    <ul className="workflow-task-picker-list">
                      {filteredBuiltInTasks.map((task) => renderTaskRow(task, handleAddBuiltIn))}
                    </ul>
                  )}
                </section>
              ) : totalAvailable === 0 ? (
                <p className="meta workflow-task-picker-empty">
                  No tasks are available right now. Remove a task from another workflow, create one on the Workflows & Tasks page, or create a new checklist task below.
                </p>
              ) : null}

              {availableCustomTasks.length > 0 ? (
                <section className="workflow-task-picker-section">
                  <h4 className="workflow-task-picker-section-title">Library checklist tasks</h4>
                  {filteredCustomTasks.length === 0 ? (
                    <p className="meta workflow-task-picker-empty">No library tasks match your search.</p>
                  ) : (
                    <ul className="workflow-task-picker-list">
                      {filteredCustomTasks.map((task) => renderTaskRow(task, handleStartAddCustom, "Choose position"))}
                    </ul>
                  )}
                </section>
              ) : null}
            </>
          ) : (
            <WorkflowSequencePositionFieldset
              tasks={workflowTasks}
              insertPosition={insertPosition}
              disabled={addingTaskKey !== null}
              legend="Where should this task go in the sequence?"
              onChange={setInsertPosition}
            />
          )}
        </div>

        <div className="modal-actions modal-actions-footer workflow-task-picker-footer">
          {step === "browse" ? (
            <>
              <button
                type="button"
                className="modal-secondary"
                disabled={addingTaskKey !== null}
                onClick={onCreateCustom}
              >
                Create new checklist task
              </button>
              <button type="button" className="modal-secondary" disabled={addingTaskKey !== null} onClick={handleClose}>
                Cancel
              </button>
            </>
          ) : (
            <>
              <button type="button" className="modal-secondary" disabled={addingTaskKey !== null} onClick={handleBackToBrowse}>
                Back
              </button>
              <button
                type="button"
                className="modal-primary"
                disabled={addingTaskKey !== null || pendingCustomTask === null}
                onClick={() => void handleConfirmAddCustom()}
              >
                {addingTaskKey !== null ? "Adding..." : "Add to workflow"}
              </button>
            </>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}
