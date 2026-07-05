import { useMemo, useState } from "react";
import { addCommunication, deleteCommunication, fetchCommunication, updateCommunication } from "./api";
import AttachmentReaderModal from "./AttachmentReaderModal";
import ChickenSwitchModal from "./ChickenSwitchModal";
import CommunicationModal from "./CommunicationModal";
import CommunicationRecordsTable from "./CommunicationRecordsTable";
import CommunicationUploadBanner from "./CommunicationUploadBanner";
import InboundEmailModal from "./InboundEmailModal";
import TabHeaderAddButton from "./TabHeaderAddButton";
import {
  buildAttachmentRecord,
  buildEmailRecord,
  type CommunicationRecord,
} from "./communicationAi";
import { COMMUNICATION_STATUS_DRAFT, COMMUNICATION_TYPE_INBOUND_EMAIL } from "./formOptions";
import type {
  Attachment,
  AttachmentKind,
  RequestCommunication,
  RequestCommunicationInput,
  RequestCommunicationSummary,
  RequestNoteSummary,
  RequestWorkflow,
} from "./types";
import { getActiveWorkflow } from "./workflowForm";

type ClientContentTab = "transcripts" | "chats" | "communications";

type UploadOptions = {
  autoGenerateAiSummary: boolean;
};

type RequestClientContentSectionProps = {
  requestId: number;
  callTranscripts: Attachment[];
  chatLogs: Attachment[];
  communications: RequestCommunicationSummary[];
  notes: RequestNoteSummary[];
  workflows: RequestWorkflow[];
  disabled: boolean;
  uploadingTranscript: boolean;
  uploadingChat: boolean;
  onUploadTranscript: (file: File, options: UploadOptions) => Promise<void>;
  onUploadChat: (file: File, options: UploadOptions) => Promise<void>;
  onOpenAiSummary: (noteId: number) => void;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
  embeddedInWorkspace?: boolean;
};

type PendingDeleteCommunication = {
  id: number;
  subject: string;
};

const AUTO_AI_SUMMARY_STORAGE_KEY = "sails-auto-ai-summary";

function readAutoGeneratePreference(): boolean {
  if (typeof window === "undefined") {
    return true;
  }
  const stored = window.localStorage.getItem(AUTO_AI_SUMMARY_STORAGE_KEY);
  return stored === null ? true : stored === "true";
}

export default function RequestClientContentSection({
  requestId,
  callTranscripts,
  chatLogs,
  communications,
  notes,
  workflows,
  disabled,
  uploadingTranscript,
  uploadingChat,
  onUploadTranscript,
  onUploadChat,
  onOpenAiSummary,
  onChanged,
  onError,
  embeddedInWorkspace = false,
}: RequestClientContentSectionProps) {
  const [activeTab, setActiveTab] = useState<ClientContentTab>("transcripts");
  const [autoGenerateAiSummary, setAutoGenerateAiSummary] = useState(readAutoGeneratePreference);
  const [viewingAttachment, setViewingAttachment] = useState<{
    attachment: Attachment;
    kind: AttachmentKind;
  } | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [inboundModalOpen, setInboundModalOpen] = useState(false);
  const [editingCommunication, setEditingCommunication] = useState<RequestCommunication | null>(null);
  const [editingInboundCommunication, setEditingInboundCommunication] = useState<RequestCommunication | null>(null);
  const [saving, setSaving] = useState(false);
  const [loadingCommunication, setLoadingCommunication] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [pendingDelete, setPendingDelete] = useState<PendingDeleteCommunication | null>(null);

  const activeWorkflow = getActiveWorkflow(workflows);

  const transcriptRecords = useMemo(
    () => callTranscripts.map((item) => buildAttachmentRecord(item, "transcripts", notes)),
    [callTranscripts, notes],
  );
  const chatRecords = useMemo(
    () => chatLogs.map((item) => buildAttachmentRecord(item, "chats", notes)),
    [chatLogs, notes],
  );
  const emailRecords = useMemo(
    () => communications.map((item) => buildEmailRecord(item, notes)),
    [communications, notes],
  );

  function handleAutoGenerateChange(value: boolean) {
    setAutoGenerateAiSummary(value);
    window.localStorage.setItem(AUTO_AI_SUMMARY_STORAGE_KEY, String(value));
  }

  async function openEditModal(communication: RequestCommunicationSummary) {
    onError("");
    if (communication.communication_type === COMMUNICATION_TYPE_INBOUND_EMAIL) {
      setInboundModalOpen(true);
      setLoadingCommunication(true);
      setEditingInboundCommunication(null);
      try {
        setEditingInboundCommunication(await fetchCommunication(requestId, communication.id));
      } catch (loadError) {
        setInboundModalOpen(false);
        onError(loadError instanceof Error ? loadError.message : "Unable to load communication.");
      } finally {
        setLoadingCommunication(false);
      }
      return;
    }

    setModalOpen(true);
    setLoadingCommunication(true);
    setEditingCommunication(null);
    try {
      setEditingCommunication(await fetchCommunication(requestId, communication.id));
    } catch (loadError) {
      setModalOpen(false);
      onError(loadError instanceof Error ? loadError.message : "Unable to load communication.");
    } finally {
      setLoadingCommunication(false);
    }
  }

  function openCreateInboundModal() {
    if (disabled) {
      return;
    }
    onError("");
    setEditingInboundCommunication(null);
    setInboundModalOpen(true);
  }

  async function handleSaveInbound(payload: RequestCommunicationInput) {
    setSaving(true);
    onError("");
    try {
      if (editingInboundCommunication) {
        await updateCommunication(requestId, editingInboundCommunication.id, payload);
      } else {
        await addCommunication(requestId, payload);
      }
      setInboundModalOpen(false);
      setEditingInboundCommunication(null);
      await onChanged();
    } catch (saveError) {
      onError(saveError instanceof Error ? saveError.message : "Unable to save email communication.");
    } finally {
      setSaving(false);
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
      if (editingInboundCommunication?.id === pendingDelete.id) {
        setInboundModalOpen(false);
        setEditingInboundCommunication(null);
      }
      setPendingDelete(null);
      await onChanged();
    } catch (deleteError) {
      onError(deleteError instanceof Error ? deleteError.message : "Unable to delete communication.");
    } finally {
      setDeletingId(null);
    }
  }

  function handleViewRecord(record: CommunicationRecord) {
    if (record.kind === "email") {
      if (record.communication) {
        void openEditModal(record.communication);
      }
      return;
    }

    const attachment =
      record.kind === "transcripts"
        ? callTranscripts.find((item) => item.id === record.id)
        : chatLogs.find((item) => item.id === record.id);
    if (attachment) {
      setViewingAttachment({ attachment, kind: record.kind });
    }
  }

  function handleOpenAiSummary(record: CommunicationRecord) {
    if (!record.aiNoteId) {
      onError("No AI summary note is linked to this communication yet.");
      return;
    }
    onOpenAiSummary(record.aiNoteId);
  }

  function handleDeleteEmail(record: CommunicationRecord) {
    if (record.kind !== "email" || !record.communication) {
      return;
    }
    const canDelete =
      record.communication.status === COMMUNICATION_STATUS_DRAFT ||
      record.communication.communication_type === COMMUNICATION_TYPE_INBOUND_EMAIL;
    if (!canDelete) {
      return;
    }
    requestDelete({ id: record.id, subject: record.subject });
  }

  const rootClassName = embeddedInWorkspace
    ? "workspace-nested-tabs request-client-content-section"
    : "section-card section-tabs-card section-tabs-card--sidebar request-client-content-section";

  const activeRecords =
    activeTab === "transcripts" ? transcriptRecords : activeTab === "chats" ? chatRecords : emailRecords;
  const activeEmptyMessage =
    activeTab === "transcripts"
      ? "No call transcripts uploaded yet."
      : activeTab === "chats"
        ? "No chat logs uploaded yet."
        : "No email communications saved yet.";

  return (
    <>
      <div className={rootClassName}>
        {activeTab !== "communications" ? (
          <CommunicationUploadBanner
            kind={activeTab === "transcripts" ? "transcripts" : "chats"}
            uploading={activeTab === "transcripts" ? uploadingTranscript : uploadingChat}
            disabled={disabled}
            autoGenerateAiSummary={autoGenerateAiSummary}
            onAutoGenerateChange={handleAutoGenerateChange}
            onUpload={activeTab === "transcripts" ? onUploadTranscript : onUploadChat}
          />
        ) : null}

        {activeTab === "communications" ? (
          <div className="communication-records-toolbar">
            {!disabled ? (
              <TabHeaderAddButton label="Save received email" onClick={openCreateInboundModal} />
            ) : null}
          </div>
        ) : null}

        <div className="section-tablist" role="tablist" aria-label="Client content">
          <button
            type="button"
            role="tab"
            id="client-content-tab-transcripts"
            aria-selected={activeTab === "transcripts"}
            aria-controls="client-content-panel-transcripts"
            className={`section-tab${activeTab === "transcripts" ? " is-active" : ""}`}
            onClick={() => setActiveTab("transcripts")}
          >
            Call transcripts ({callTranscripts.length})
          </button>
          <button
            type="button"
            role="tab"
            id="client-content-tab-chats"
            aria-selected={activeTab === "chats"}
            aria-controls="client-content-panel-chats"
            className={`section-tab${activeTab === "chats" ? " is-active" : ""}`}
            onClick={() => setActiveTab("chats")}
          >
            Chat logs ({chatLogs.length})
          </button>
          <button
            type="button"
            role="tab"
            id="client-content-tab-communications"
            aria-selected={activeTab === "communications"}
            aria-controls="client-content-panel-communications"
            className={`section-tab${activeTab === "communications" ? " is-active" : ""}`}
            onClick={() => setActiveTab("communications")}
          >
            Email communications ({communications.length})
          </button>
        </div>

        <div className="section-card-body section-tab-body communication-records-panel">
          <CommunicationRecordsTable
            records={activeRecords}
            emptyMessage={activeEmptyMessage}
            disabled={disabled}
            deletingEmailId={deletingId}
            onView={handleViewRecord}
            onDeleteEmail={activeTab === "communications" && !disabled ? handleDeleteEmail : undefined}
            onOpenAiSummary={handleOpenAiSummary}
          />
        </div>
      </div>

      <AttachmentReaderModal
        open={viewingAttachment !== null}
        title={viewingAttachment ? viewingAttachment.attachment.original_filename : "Attachment"}
        requestId={requestId}
        kind={viewingAttachment?.kind ?? "transcripts"}
        attachment={viewingAttachment?.attachment ?? null}
        onClose={() => setViewingAttachment(null)}
      />

      <InboundEmailModal
        open={inboundModalOpen}
        communication={editingInboundCommunication}
        saving={saving || loadingCommunication}
        disabled={disabled}
        onCancel={() => {
          setInboundModalOpen(false);
          setEditingInboundCommunication(null);
        }}
        onSave={handleSaveInbound}
        onDelete={
          editingInboundCommunication
            ? () =>
                requestDelete({
                  id: editingInboundCommunication.id,
                  subject: editingInboundCommunication.subject,
                })
            : undefined
        }
      />

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
        title={
          pendingDelete && communications.find((item) => item.id === pendingDelete.id)?.communication_type ===
            COMMUNICATION_TYPE_INBOUND_EMAIL
            ? "Delete received email?"
            : "Delete draft communication?"
        }
        description={
          pendingDelete && communications.find((item) => item.id === pendingDelete.id)?.communication_type ===
            COMMUNICATION_TYPE_INBOUND_EMAIL
            ? "This received email will be permanently removed from the request."
            : "This draft will be permanently removed from the request."
        }
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
