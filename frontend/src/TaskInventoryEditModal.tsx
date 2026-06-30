import { FormEvent, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { updateAgencyCustomTaskDefinition, updateAgencyTaskTemplate } from "./api";
import type { AgencyTaskInventoryItem } from "./types";

type TaskInventoryEditModalProps = {
  open: boolean;
  item: AgencyTaskInventoryItem | null;
  onClose: () => void;
  onSaved: () => void | Promise<void>;
};

function canEditInventoryItem(item: AgencyTaskInventoryItem): boolean {
  if (item.task_type === "library") {
    return item.definition_id !== null;
  }
  return item.task_template_id !== null;
}

export default function TaskInventoryEditModal({ open, item, onClose, onSaved }: TaskInventoryEditModalProps) {
  const [taskTitle, setTaskTitle] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const editable = item ? canEditInventoryItem(item) : false;

  useEffect(() => {
    if (!open || !item) {
      setTaskTitle("");
      setDescription("");
      setError("");
      setSubmitting(false);
      return;
    }
    setTaskTitle(item.task_title);
    setDescription(item.description);
    setError("");
  }, [item, open]);

  if (!open || !item) {
    return null;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!item || !editable) {
      return;
    }

    const title = taskTitle.trim();
    if (!title) {
      setError("Task name is required.");
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      if (item.task_type === "library" && item.definition_id) {
        await updateAgencyCustomTaskDefinition(item.definition_id, {
          task_title: title,
          description: description.trim() || null,
        });
      } else if (item.task_template_id) {
        await updateAgencyTaskTemplate(item.task_template_id, {
          task_title: title,
          description: description.trim() || null,
        });
      }

      await onSaved();
      onClose();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to save task.");
    } finally {
      setSubmitting(false);
    }
  }

  const typeLabel = item.task_type === "library" ? "Library" : "Built-in";

  return createPortal(
    <div className="modal-backdrop modal-backdrop-scroll" role="presentation" onClick={onClose}>
      <div
        className="modal-card task-inventory-edit-modal"
        role="dialog"
        aria-labelledby="task-inventory-edit-title"
        aria-modal="true"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="modal-card-header">
          <h3 id="task-inventory-edit-title">Edit task</h3>
        </header>

        <form className="modal-scroll-body task-inventory-edit-body" onSubmit={(event) => void handleSubmit(event)}>
          <div className="modal-meta-row">
            <span>{typeLabel}</span>
            {item.workflow_name ? (
              <>
                <span className="modal-meta-separator" aria-hidden="true">
                  |
                </span>
                <span>{item.workflow_name}</span>
              </>
            ) : (
              <>
                <span className="modal-meta-separator" aria-hidden="true">
                  |
                </span>
                <span>Available</span>
              </>
            )}
          </div>

          {!editable ? (
            <p className="meta task-inventory-edit-note">
              Built-in tasks use default names until they are added to a workflow. Add this task to a workflow to
              customize its name and description.
            </p>
          ) : null}

          <label>
            Task name
            <input
              type="text"
              value={taskTitle}
              placeholder="Task name"
              disabled={submitting || !editable}
              onChange={(event) => setTaskTitle(event.target.value)}
            />
          </label>

          <label>
            Description (optional)
            <textarea
              value={description}
              rows={3}
              placeholder="What should the agent do on this step?"
              disabled={submitting || !editable}
              onChange={(event) => setDescription(event.target.value)}
            />
          </label>

          {error ? <p className="status error">{error}</p> : null}

          <div className="modal-actions modal-actions-footer">
            <button type="button" className="modal-secondary" disabled={submitting} onClick={onClose}>
              Cancel
            </button>
            {editable ? (
              <button type="submit" className="modal-primary" disabled={submitting}>
                {submitting ? "Saving..." : "Save changes"}
              </button>
            ) : null}
          </div>
        </form>
      </div>
    </div>,
    document.body,
  );
}
