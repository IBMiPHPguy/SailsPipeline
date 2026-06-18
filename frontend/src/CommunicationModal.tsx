import { FormEvent, useEffect, useState } from "react";
import {
  COMMUNICATION_STATUS_DRAFT,
  COMMUNICATION_STATUS_SENT,
  COMMUNICATION_TYPE_AGENCY,
  COMMUNICATION_TYPE_BOOKING,
  COMMUNICATION_TYPE_RESEARCH_FINDINGS,
  COMMUNICATION_TYPE_RESEARCH_FOLLOW_UP,
  COMMUNICATION_TYPE_RESEARCH_PROPOSAL,
} from "./formOptions";
import {
  communicationToForm,
  emptyCommunicationForm,
} from "./workflowForm";
import type { RequestCommunication, RequestCommunicationInput } from "./types";

type CommunicationModalProps = {
  open: boolean;
  communication: RequestCommunication | null;
  requestWorkflowId: number | null;
  saving: boolean;
  disabled: boolean;
  onCancel: () => void;
  onSave: (payload: RequestCommunicationInput) => Promise<void>;
  onDelete?: () => void;
};

export default function CommunicationModal({
  open,
  communication,
  requestWorkflowId,
  saving,
  disabled,
  onCancel,
  onSave,
  onDelete,
}: CommunicationModalProps) {
  const [form, setForm] = useState<RequestCommunicationInput>(emptyCommunicationForm);

  useEffect(() => {
    if (!open) {
      setForm(emptyCommunicationForm);
      return;
    }
    setForm(
      communication
        ? communicationToForm(communication)
        : { ...emptyCommunicationForm, request_workflow_id: requestWorkflowId },
    );
  }, [open, communication, requestWorkflowId]);

  if (!open) {
    return null;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (disabled || !form.subject.trim() || !form.body.trim()) {
      return;
    }
    await onSave({
      ...form,
      subject: form.subject.trim(),
      body: form.body,
      request_workflow_id: form.request_workflow_id ?? requestWorkflowId,
    });
  }

  return (
    <div className="modal-backdrop" role="presentation" onClick={onCancel}>
      <div
        className="modal-card modal-card-wide communication-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="communication-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="modal-card-header">
          <h3 id="communication-modal-title">
            {communication ? "Edit communication" : "Add communication"}
          </h3>
        </header>

        <form className="modal-form-layout" onSubmit={handleSubmit}>
          <div className="modal-scroll-body communication-form">
            <label>
              Type
              <select
                disabled={disabled || saving}
                value={form.communication_type}
                onChange={(event) => setForm({ ...form, communication_type: event.target.value })}
              >
                <option value={COMMUNICATION_TYPE_RESEARCH_FINDINGS}>Research findings</option>
                <option value={COMMUNICATION_TYPE_RESEARCH_PROPOSAL}>Cruise proposal</option>
                <option value={COMMUNICATION_TYPE_RESEARCH_FOLLOW_UP}>Research follow-up</option>
                <option value={COMMUNICATION_TYPE_BOOKING}>Booking confirmation</option>
                <option value={COMMUNICATION_TYPE_AGENCY}>Agency follow-up</option>
              </select>
            </label>

            <label>
              Subject
              <input
                required
                disabled={disabled || saving}
                value={form.subject}
                onChange={(event) => setForm({ ...form, subject: event.target.value })}
              />
            </label>

            <label>
              Message
              <textarea
                required
                rows={12}
                disabled={disabled || saving}
                value={form.body}
                placeholder="Paste the communication content here"
                onChange={(event) => setForm({ ...form, body: event.target.value })}
              />
            </label>
            <p className="field-hint">
              Paste rich text or formatted content from your email client. Formatting will be preserved as entered.
            </p>

            <label>
              Status
              <select
                disabled={disabled || saving}
                value={form.status ?? COMMUNICATION_STATUS_DRAFT}
                onChange={(event) => setForm({ ...form, status: event.target.value })}
              >
                <option value={COMMUNICATION_STATUS_DRAFT}>Draft</option>
                <option value={COMMUNICATION_STATUS_SENT}>Sent</option>
              </select>
            </label>
          </div>

          <div className="modal-actions modal-actions-footer">
            {communication?.status === COMMUNICATION_STATUS_DRAFT && onDelete && !disabled ? (
              <button
                type="button"
                className="danger-button communication-delete-button"
                disabled={saving}
                onClick={onDelete}
              >
                {saving ? "Deleting..." : "Delete draft"}
              </button>
            ) : null}
            <button type="button" className="modal-secondary" disabled={saving} onClick={onCancel}>
              Cancel
            </button>
            {!disabled ? (
              <button type="submit" disabled={saving || !form.subject.trim() || !form.body.trim()}>
                {saving ? "Saving..." : communication ? "Save communication" : "Add communication"}
              </button>
            ) : null}
          </div>
        </form>
      </div>
    </div>
  );
}
