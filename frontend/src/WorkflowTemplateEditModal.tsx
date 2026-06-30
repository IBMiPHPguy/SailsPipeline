import { FormEvent, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { updateAgencyWorkflowTemplate } from "./api";
import type { AgencyWorkflowTemplate } from "./types";

type WorkflowTemplateEditModalProps = {
  open: boolean;
  template: AgencyWorkflowTemplate | null;
  onClose: () => void;
  onSaved: () => void;
};

function templateToForm(template: AgencyWorkflowTemplate) {
  return {
    workflow_name: template.workflow_name,
    description: template.description ?? "",
  };
}

export default function WorkflowTemplateEditModal({
  open,
  template,
  onClose,
  onSaved,
}: WorkflowTemplateEditModalProps) {
  const [form, setForm] = useState({ workflow_name: "", description: "" });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open || !template) {
      setForm({ workflow_name: "", description: "" });
      setError("");
      setSubmitting(false);
      return;
    }

    setForm(templateToForm(template));
    setError("");
  }, [open, template]);

  if (!open || !template) {
    return null;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const workflowName = form.workflow_name.trim();
    if (!workflowName) {
      setError("Workflow name is required.");
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      await updateAgencyWorkflowTemplate(template.id, {
        workflow_name: workflowName,
        description: form.description.trim() || null,
      });
      onSaved();
      onClose();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to update workflow playbook.");
    } finally {
      setSubmitting(false);
    }
  }

  return createPortal(
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="modal-card workflow-template-edit-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="workflow-template-edit-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="modal-card-header">
          <h3 id="workflow-template-edit-title">Edit Workflow</h3>
        </header>

        <form
          id="workflow-template-edit-form"
          className="modal-scroll-body workflow-template-edit-form"
          onSubmit={(event) => void handleSubmit(event)}
        >
          {error ? <p className="status error">{error}</p> : null}

          <label>
            Workflow name
            <input
              required
              type="text"
              value={form.workflow_name}
              disabled={submitting}
              onChange={(event) => setForm({ ...form, workflow_name: event.target.value })}
            />
          </label>

          <label>
            <span>
              Description <span className="field-optional">(Optional)</span>
            </span>
            <textarea
              rows={3}
              value={form.description}
              disabled={submitting}
              placeholder="Short summary shown in the workflow sequencer"
              onChange={(event) => setForm({ ...form, description: event.target.value })}
            />
          </label>
        </form>

        <div className="modal-actions modal-actions-footer">
          <button type="button" className="modal-secondary" disabled={submitting} onClick={onClose}>
            Cancel
          </button>
          <button type="submit" form="workflow-template-edit-form" disabled={submitting}>
            {submitting ? "Saving..." : "Save changes"}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
