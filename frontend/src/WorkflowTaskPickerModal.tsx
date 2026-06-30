import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { createAgencyTaskFromCatalog } from "./api";
import type { AgencyTaskCatalogItem, AgencyWorkflowTemplate } from "./types";

type WorkflowTaskPickerModalProps = {
  open: boolean;
  workflow: AgencyWorkflowTemplate | null;
  availableTasks: AgencyTaskCatalogItem[];
  onClose: () => void;
  onAdded: () => void | Promise<void>;
};

export default function WorkflowTaskPickerModal({
  open,
  workflow,
  availableTasks,
  onClose,
  onAdded,
}: WorkflowTaskPickerModalProps) {
  const [query, setQuery] = useState("");
  const [addingTaskKey, setAddingTaskKey] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) {
      setQuery("");
      setAddingTaskKey(null);
      setError("");
    }
  }, [open]);

  const filteredTasks = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return availableTasks;
    }
    return availableTasks.filter(
      (task) =>
        task.task_title.toLowerCase().includes(normalized) ||
        task.description.toLowerCase().includes(normalized) ||
        task.task_key.toLowerCase().includes(normalized),
    );
  }, [availableTasks, query]);

  if (!open || !workflow) {
    return null;
  }

  async function handleAdd(task: AgencyTaskCatalogItem) {
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

  return createPortal(
    <div className="modal-backdrop modal-backdrop-scroll" role="presentation" onClick={onClose}>
      <div
        className="modal-card modal-card-wide workflow-task-picker-modal"
        role="dialog"
        aria-labelledby="workflow-task-picker-title"
        aria-modal="true"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="modal-card-header">
          <h3 id="workflow-task-picker-title">Add task to workflow</h3>
        </header>

        <div className="modal-scroll-body workflow-task-picker-body">
          <div className="modal-meta-row">
            <span>{workflow.workflow_name}</span>
            <span className="modal-meta-separator" aria-hidden="true">
              |
            </span>
            <span>
              {availableTasks.length} available {availableTasks.length === 1 ? "task" : "tasks"}
            </span>
          </div>

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

          {error ? <p className="status error">{error}</p> : null}

          {availableTasks.length === 0 ? (
            <p className="meta workflow-task-picker-empty">
              No tasks are available right now. Remove a task from another workflow to free it up.
            </p>
          ) : filteredTasks.length === 0 ? (
            <p className="meta workflow-task-picker-empty">No tasks match your search.</p>
          ) : (
            <ul className="workflow-task-picker-list">
              {filteredTasks.map((task) => {
                const isAdding = addingTaskKey === task.task_key;
                return (
                  <li key={task.task_key} className="modal-section-panel workflow-task-picker-row">
                    <div className="workflow-task-picker-row-main">
                      <div className="workflow-task-picker-row-text">
                        <h4 className="workflow-task-picker-row-title">{task.task_title}</h4>
                        <p className="meta workflow-task-picker-row-description">{task.description}</p>
                      </div>
                      <button
                        type="button"
                        className="workflow-task-picker-add-button"
                        disabled={addingTaskKey !== null}
                        onClick={() => void handleAdd(task)}
                      >
                        {isAdding ? "Adding..." : "Add"}
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div className="modal-actions modal-actions-footer">
          <button type="button" className="modal-secondary" disabled={addingTaskKey !== null} onClick={onClose}>
            Cancel
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
