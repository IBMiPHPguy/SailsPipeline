import { FormEvent, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { createAgencyWorkflowTemplate } from "./api";

type CreateWorkflowModalProps = {
  open: boolean;
  onClose: () => void;
  onCreated: () => void | Promise<void>;
};

export default function CreateWorkflowModal({ open, onClose, onCreated }: CreateWorkflowModalProps) {
  const [workflowName, setWorkflowName] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) {
      setWorkflowName("");
      setDescription("");
      setError("");
      setSubmitting(false);
    }
  }, [open]);

  if (!open) {
    return null;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = workflowName.trim();
    if (!name) {
      setError("Workflow name is required.");
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      await createAgencyWorkflowTemplate({
        workflow_name: name,
        description: description.trim() || null,
      });
      await onCreated();
      onClose();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to create workflow.");
    } finally {
      setSubmitting(false);
    }
  }

  return createPortal(
    <div className="modal-backdrop modal-backdrop-scroll" role="presentation" onClick={onClose}>
      <div
        className="modal-card workflow-template-edit-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-workflow-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="modal-card-header">
          <h3 id="create-workflow-title">Create workflow</h3>
        </header>

        <form
          id="create-workflow-form"
          className="modal-scroll-body workflow-template-edit-form"
          onSubmit={(event) => void handleSubmit(event)}
        >
          <p className="meta">Custom workflows can be deleted later. Tasks can be added from the task inventory below.</p>

          {error ? <p className="status error">{error}</p> : null}

          <label>
            Workflow name
            <input
              required
              type="text"
              value={workflowName}
              placeholder="Enter workflow name..."
              disabled={submitting}
              onChange={(event) => setWorkflowName(event.target.value)}
            />
          </label>

          <label>
            <span>
              Description <span className="field-optional">(Optional)</span>
            </span>
            <textarea
              rows={3}
              value={description}
              placeholder="Short summary for your agency"
              disabled={submitting}
              onChange={(event) => setDescription(event.target.value)}
            />
          </label>
        </form>

        <div className="modal-actions modal-actions-footer">
          <button type="button" className="modal-secondary" disabled={submitting} onClick={onClose}>
            Cancel
          </button>
          <button type="submit" form="create-workflow-form" className="modal-primary" disabled={submitting}>
            {submitting ? "Creating..." : "Create workflow"}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
