import { FormEvent, useEffect, useState } from "react";
import CommunicationBodyField from "./CommunicationBodyField";
import YesNoPillToggle from "./YesNoPillToggle";
import {
  COMMUNICATION_STATUS_RECEIVED,
  COMMUNICATION_TYPE_INBOUND_EMAIL,
} from "./formOptions";
import type { RequestCommunication, RequestCommunicationInput } from "./types";

export type InboundEmailInput = {
  received_at: string;
  sender_email: string;
  subject: string;
  body: string;
  is_response_to_agent: boolean;
};

type InboundEmailModalProps = {
  open: boolean;
  communication: RequestCommunication | null;
  saving: boolean;
  disabled: boolean;
  onCancel: () => void;
  onSave: (payload: RequestCommunicationInput) => Promise<void>;
  onDelete?: () => void;
};

function toLocalDateTimeInput(value: string | null | undefined): string {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const offset = date.getTimezoneOffset();
  const local = new Date(date.getTime() - offset * 60_000);
  return local.toISOString().slice(0, 16);
}

function emptyInboundEmailForm(): InboundEmailInput {
  const now = new Date();
  const offset = now.getTimezoneOffset();
  const local = new Date(now.getTime() - offset * 60_000);
  return {
    received_at: local.toISOString().slice(0, 16),
    sender_email: "",
    subject: "",
    body: "",
    is_response_to_agent: false,
  };
}

function communicationToInboundForm(communication: RequestCommunication): InboundEmailInput {
  return {
    received_at: toLocalDateTimeInput(communication.received_at ?? communication.created_at),
    sender_email: communication.sender_email ?? "",
    subject: communication.subject,
    body: communication.body,
    is_response_to_agent: communication.is_response_to_agent ?? false,
  };
}

export function inboundEmailToPayload(form: InboundEmailInput): RequestCommunicationInput {
  const receivedAt = new Date(form.received_at);
  return {
    communication_type: COMMUNICATION_TYPE_INBOUND_EMAIL,
    subject: form.subject.trim(),
    body: form.body,
    status: COMMUNICATION_STATUS_RECEIVED,
    sender_email: form.sender_email.trim(),
    received_at: Number.isNaN(receivedAt.getTime()) ? undefined : receivedAt.toISOString(),
    is_response_to_agent: form.is_response_to_agent,
  };
}

export default function InboundEmailModal({
  open,
  communication,
  saving,
  disabled,
  onCancel,
  onSave,
  onDelete,
}: InboundEmailModalProps) {
  const [form, setForm] = useState<InboundEmailInput>(emptyInboundEmailForm);

  useEffect(() => {
    if (!open) {
      setForm(emptyInboundEmailForm());
      return;
    }
    setForm(communication ? communicationToInboundForm(communication) : emptyInboundEmailForm());
  }, [open, communication]);

  if (!open) {
    return null;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      disabled ||
      !form.received_at ||
      !form.sender_email.trim() ||
      !form.subject.trim() ||
      !form.body.trim()
    ) {
      return;
    }
    await onSave(inboundEmailToPayload(form));
  }

  return (
    <div className="modal-backdrop" role="presentation" onClick={onCancel}>
      <div
        className="modal-card modal-card-wide inbound-email-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="inbound-email-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="modal-card-header">
          <h3 id="inbound-email-modal-title">
            {communication ? "Edit received email" : "Save received email"}
          </h3>
        </header>

        <form className="modal-form-layout" onSubmit={handleSubmit}>
          <div className="modal-scroll-body communication-form">
            <div className="modal-section-panel">
              <label>
                Received
                <input
                  type="datetime-local"
                  required
                  disabled={disabled || saving}
                  value={form.received_at}
                  onChange={(event) => setForm({ ...form, received_at: event.target.value })}
                />
              </label>

              <label>
                Sender email
                <input
                  type="email"
                  required
                  disabled={disabled || saving}
                  value={form.sender_email}
                  onChange={(event) => setForm({ ...form, sender_email: event.target.value })}
                  placeholder="client@example.com"
                />
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

              <CommunicationBodyField
                body={form.body}
                disabled={disabled}
                saving={saving}
                resetKey={communication?.id ?? "new-inbound"}
                onChange={(body) => setForm({ ...form, body })}
              />

              <YesNoPillToggle
                label="This email is a response to a query from the agent"
                value={form.is_response_to_agent}
                disabled={disabled || saving}
                onChange={(is_response_to_agent) => setForm({ ...form, is_response_to_agent })}
              />
            </div>
          </div>

          <div className="modal-actions modal-actions-footer">
            {communication && onDelete && !disabled ? (
              <button
                type="button"
                className="danger-button communication-delete-button"
                disabled={saving}
                onClick={onDelete}
              >
                {saving ? "Deleting..." : "Delete email"}
              </button>
            ) : null}
            <button type="button" className="modal-secondary" disabled={saving} onClick={onCancel}>
              Cancel
            </button>
            {!disabled ? (
              <button
                type="submit"
                className="modal-primary"
                disabled={
                  saving ||
                  !form.received_at ||
                  !form.sender_email.trim() ||
                  !form.subject.trim() ||
                  !form.body.trim()
                }
              >
                {saving ? "Saving..." : communication ? "Save email" : "Save received email"}
              </button>
            ) : null}
          </div>
        </form>
      </div>
    </div>
  );
}
