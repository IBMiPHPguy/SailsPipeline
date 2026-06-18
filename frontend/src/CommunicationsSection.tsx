import { useState } from "react";
import { deleteCommunication, fetchCommunication, updateCommunication } from "./api";
import ChickenSwitchModal from "./ChickenSwitchModal";
import CommunicationModal from "./CommunicationModal";
import { COMMUNICATION_STATUS_DRAFT } from "./formOptions";
import type {
  RequestCommunication,
  RequestCommunicationInput,
  RequestCommunicationSummary,
  RequestWorkflow,
} from "./types";
import { formatTimestamp } from "./utils";
import {
  communicationStatusClass,
  communicationTypeLabel,
  getActiveWorkflow,
} from "./workflowForm";

type CommunicationsSectionProps = {
  requestId: number;
  communications: RequestCommunicationSummary[];
  workflows: RequestWorkflow[];
  disabled: boolean;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
  embedded?: boolean;
};

type PendingDeleteCommunication = {
  id: number;
  subject: string;
};

export default function CommunicationsSection({
  requestId,
  communications,
  workflows,
  disabled,
  onChanged,
  onError,
  embedded = false,
}: CommunicationsSectionProps) {
  const [modalOpen, setModalOpen] = useState(false);
  const [editingCommunication, setEditingCommunication] = useState<RequestCommunication | null>(null);
  const [saving, setSaving] = useState(false);
  const [loadingCommunication, setLoadingCommunication] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [pendingDelete, setPendingDelete] = useState<PendingDeleteCommunication | null>(null);

  const activeWorkflow = getActiveWorkflow(workflows);

  async function openEditModal(communication: RequestCommunicationSummary) {
    setModalOpen(true);
    setLoadingCommunication(true);
    setEditingCommunication(null);
    onError("");
    try {
      setEditingCommunication(await fetchCommunication(requestId, communication.id));
    } catch (loadError) {
      setModalOpen(false);
      onError(loadError instanceof Error ? loadError.message : "Unable to load communication.");
    } finally {
      setLoadingCommunication(false);
    }
  }

  async function handleSave(payload: RequestCommunicationInput) {
    if (!editingCommunication) {
      return;
    }

    setSaving(true);
    onError("");
    try {
      await updateCommunication(requestId, editingCommunication.id, payload);
      setModalOpen(false);
      setEditingCommunication(null);
      await onChanged();
    } catch (saveError) {
      onError(saveError instanceof Error ? saveError.message : "Unable to save communication.");
    } finally {
      setSaving(false);
    }
  }

  function requestDelete(communication: PendingDeleteCommunication) {
    if (disabled) {
      return;
    }
    onError("");
    setPendingDelete(communication);
  }

  async function confirmDelete() {
    if (!pendingDelete) {
      return;
    }

    setDeletingId(pendingDelete.id);
    onError("");
    try {
      await deleteCommunication(requestId, pendingDelete.id);
      if (editingCommunication?.id === pendingDelete.id) {
        setModalOpen(false);
        setEditingCommunication(null);
      }
      setPendingDelete(null);
      await onChanged();
    } catch (deleteError) {
      onError(deleteError instanceof Error ? deleteError.message : "Unable to delete communication.");
    } finally {
      setDeletingId(null);
    }
  }

  const body =
    communications.length === 0 ? (
      <p className="meta communications-empty">No communications saved yet.</p>
    ) : (
        <div className="communications-table-wrap">
          <table className="communications-table">
            <thead>
              <tr>
                <th scope="col">Subject</th>
                <th scope="col">Type</th>
                <th scope="col">Status</th>
                <th scope="col">Updated</th>
                {!disabled ? <th scope="col">Actions</th> : null}
              </tr>
            </thead>
            <tbody>
              {communications.map((communication) => (
                <tr key={communication.id}>
                  <td>
                    <button
                      type="button"
                      className="link-button communications-subject-link"
                      onClick={() => openEditModal(communication)}
                    >
                      <span className="attachment-truncate">{communication.subject}</span>
                    </button>
                  </td>
                  <td>{communicationTypeLabel(communication.communication_type)}</td>
                  <td>
                    <span className={`communication-status ${communicationStatusClass(communication.status)}`}>
                      {communication.status}
                    </span>
                  </td>
                  <td className="meta">
                    {communication.updated_by.username} · {formatTimestamp(communication.updated_at)}
                  </td>
                  {!disabled ? (
                    <td>
                      {communication.status === COMMUNICATION_STATUS_DRAFT ? (
                        <button
                          type="button"
                          className="danger-button communications-delete-button"
                          disabled={deletingId === communication.id || saving || loadingCommunication}
                          onClick={() =>
                            requestDelete({ id: communication.id, subject: communication.subject })
                          }
                        >
                          {deletingId === communication.id ? "Deleting..." : "Delete"}
                        </button>
                      ) : (
                        <span className="meta">—</span>
                      )}
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
    );

  return (
    <>
      {embedded ? (
        body
      ) : (
        <section className="section-card communications-card">
          <header className="section-card-header">
            <h3>Communications</h3>
          </header>
          <div className="section-card-body">{body}</div>
        </section>
      )}

      <CommunicationModal
        open={modalOpen}
        communication={editingCommunication}
        requestWorkflowId={activeWorkflow?.id ?? null}
        saving={saving || loadingCommunication}
        disabled={disabled}
        onCancel={() => {
          setModalOpen(false);
          setEditingCommunication(null);
        }}
        onSave={handleSave}
        onDelete={
          editingCommunication?.status === COMMUNICATION_STATUS_DRAFT
            ? () =>
                requestDelete({
                  id: editingCommunication.id,
                  subject: editingCommunication.subject,
                })
            : undefined
        }
      />

      <ChickenSwitchModal
        open={pendingDelete !== null}
        title="Delete draft communication?"
        description="This draft will be permanently removed from the request."
        itemName={pendingDelete?.subject}
        switchLabel="Yes, delete this draft communication"
        confirmLabel="Delete communication"
        confirming={pendingDelete !== null && deletingId === pendingDelete.id}
        onCancel={() => setPendingDelete(null)}
        onConfirm={() => void confirmDelete()}
      />
    </>
  );
}
