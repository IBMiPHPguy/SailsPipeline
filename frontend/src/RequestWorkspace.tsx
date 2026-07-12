import { FormEvent, useCallback, useEffect, useState, type ReactNode } from "react";
import { addNote, fetchRequest, generateCommunicationAiSummary, updateRequest, uploadChatLog, uploadTranscript } from "./api";
import RequestClientContentSection from "./RequestClientContentSection";
import RequestHistorySection from "./RequestHistorySection";
import RequestNotesResearchSection from "./RequestNotesResearchSection";
import RequestProposalsSection, { type ProposalsTab } from "./RequestProposalsSection";
import CloseRequestModal from "./CloseRequestModal";
import { formatCruiseLines } from "./CruiseLineMultiSelect";
import PassengersSection from "./PassengersSection";
import RequestForm, { emptyRequestForm, isReturnAfterDeparture } from "./RequestForm";
import WorkflowsSection from "./WorkflowsSection";
import WorkspaceBandHeader from "./WorkspaceBandHeader";
import { REQUEST_STATUS_CLOSED, WORKFLOW_TYPE_ENTER_TRIP_CRM } from "./formOptions";
import type { TravelRequestDetail, TravelRequestInput, User } from "./types";
import { formatDestinationSummary, formatDate, formatTimestamp } from "./utils";
import { getActiveWorkflow } from "./workflowForm";
import { canManageTravelRequest } from "./agentCapabilities";

type RequestWorkspaceProps = {
  requestId: number;
  currentUser: User;
  onBack: () => void;
  onClosed: () => void;
};

type WorkspaceTab =
  | "details"
  | "passengers"
  | "proposals"
  | "communications"
  | "workflow"
  | "notes"
  | "audit";

type WorkspaceTabShellProps = {
  title: string;
  meta?: string;
  children: ReactNode;
};

function WorkspaceTabShell({ title, meta, children }: WorkspaceTabShellProps) {
  return (
    <section className="request-form-band">
      <WorkspaceBandHeader title={title} meta={meta} />
      <div className="request-form-band-body workspace-embedded-band-body">{children}</div>
    </section>
  );
}

function requestToForm(request: TravelRequestDetail): TravelRequestInput {
  return {
    first_name: request.first_name,
    last_name: request.last_name,
    email: request.email,
    phone: request.phone,
    cruise_lines: request.cruise_lines ?? [],
    excluded_cruise_lines: request.excluded_cruise_lines ?? [],
    destination: request.destination,
    destination_details: request.destination_details ?? {},
    departure_date: request.departure_date,
    return_date: request.return_date,
    cabin_types: request.cabin_types,
    passengers: request.passengers,
    cabins_needed: request.cabins_needed ?? 1,
    lead_source: request.lead_source ?? "",
    referral_source_name: request.referral_source_name ?? "",
    marketing_campaign_id: request.marketing_campaign_id ?? "",
    intake_mode: request.intake_mode ?? "",
    intake_social_platform: request.intake_social_platform ?? "",
  };
}

function buildSummaryRequest(
  request: TravelRequestDetail,
  form: TravelRequestInput,
): TravelRequestDetail {
  return {
    ...request,
    first_name: form.first_name,
    last_name: form.last_name,
    cruise_lines: form.cruise_lines,
    destination: form.destination,
    destination_details: ["Caribbean", "Alaska", "Asia", "Europe"].includes(form.destination)
      ? form.destination_details ?? null
      : null,
    departure_date: form.departure_date,
    return_date: form.return_date,
  };
}

export default function RequestWorkspace({
  requestId,
  currentUser,
  onBack,
  onClosed,
}: RequestWorkspaceProps) {
  const [request, setRequest] = useState<TravelRequestDetail | null>(null);
  const [form, setForm] = useState<TravelRequestInput>(emptyRequestForm);
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("details");
  const [proposalsFocusTab, setProposalsFocusTab] = useState<ProposalsTab | null>(null);
  const [focusedNoteId, setFocusedNoteId] = useState<number | null>(null);
  const [showCloseModal, setShowCloseModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [closing, setClosing] = useState(false);
  const [uploadingTranscript, setUploadingTranscript] = useState(false);
  const [uploadingChat, setUploadingChat] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const isClosed = request?.status === REQUEST_STATUS_CLOSED;
  const canManage =
    request != null ? canManageTravelRequest(currentUser, request) : false;
  const mutationsLocked = Boolean(isClosed || (request != null && !canManage));
  const activeWorkflow = request ? getActiveWorkflow(request.request_workflows) : null;
  const enterTripInCrmActive = activeWorkflow?.workflow_type === WORKFLOW_TYPE_ENTER_TRIP_CRM;

  const navigateToQuotedInsurance = useCallback(() => {
    setActiveTab("proposals");
    setProposalsFocusTab("insurance");
  }, []);

  async function loadRequest(options?: { silent?: boolean }) {
    const silent = options?.silent ?? false;
    if (!silent) {
      setLoading(true);
    }
    setError("");
    try {
      const data = await fetchRequest(requestId);
      setRequest(data);
      setForm(requestToForm(data));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load request.");
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  }

  async function refreshRequest() {
    await loadRequest({ silent: true });
  }

  useEffect(() => {
    loadRequest().catch(() => undefined);
  }, [requestId]);

  function buildPayload(extra?: { status?: string; close_reason?: string | null }): TravelRequestInput & {
    status?: string;
    close_reason?: string | null;
  } {
    return {
      ...form,
      excluded_cruise_lines: form.excluded_cruise_lines ?? [],
      destination_details: ["Caribbean", "Alaska", "Asia", "Europe"].includes(form.destination)
        ? form.destination_details
        : null,
      ...extra,
    };
  }

  async function handleSave() {
    if (mutationsLocked) {
      return;
    }

    setSubmitting(true);
    setMessage("");
    setError("");

    if (form.cabin_types.length === 0) {
      setError("Select at least one cabin type.");
      setSubmitting(false);
      return;
    }

    if (form.cruise_lines.length === 0) {
      setError("Select at least one preferred cruise line.");
      setSubmitting(false);
      return;
    }

    if (!isReturnAfterDeparture(form.departure_date, form.return_date)) {
      setError("Return date must be after the departure date.");
      setSubmitting(false);
      return;
    }

    try {
      const updated = await updateRequest(requestId, buildPayload());
      setRequest(updated);
      setForm(requestToForm(updated));
      setMessage("Request updated.");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Update failed.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await handleSave();
  }

  async function handleCloseRequest(closeReason: string) {
    setClosing(true);
    setMessage("");
    setError("");

    try {
      await updateRequest(requestId, {
        ...buildPayload(),
        status: REQUEST_STATUS_CLOSED,
        close_reason: closeReason,
      });
      setShowCloseModal(false);
      setMessage("Request closed.");
      onClosed();
    } catch (closeError) {
      setError(closeError instanceof Error ? closeError.message : "Unable to close request.");
    } finally {
      setClosing(false);
    }
  }

  async function handleUploadCommunication(
    kind: "transcripts" | "chats",
    file: File,
    options: { autoGenerateAiSummary: boolean },
  ) {
    const setUploading = kind === "transcripts" ? setUploadingTranscript : setUploadingChat;
    const upload = kind === "transcripts" ? uploadTranscript : uploadChatLog;
    const label = kind === "transcripts" ? "Call transcript" : "Chat log";

    setUploading(true);
    setError("");
    try {
      const attachment = await upload(requestId, file);
      await refreshRequest();
      if (options.autoGenerateAiSummary) {
        try {
          const noteInput = await generateCommunicationAiSummary(requestId, kind, attachment.id);
          await addNote(requestId, noteInput);
          await refreshRequest();
          setMessage(`${label} uploaded and AI summary note created.`);
        } catch (aiError) {
          setMessage(`${label} uploaded.`);
          setError(
            aiError instanceof Error
              ? `AI summary could not be generated: ${aiError.message}`
              : "AI summary could not be generated.",
          );
        }
      } else {
        setMessage(`${label} uploaded.`);
      }
    } catch (uploadError) {
      setError(
        uploadError instanceof Error ? uploadError.message : `Unable to upload ${label.toLowerCase()}.`,
      );
    } finally {
      setUploading(false);
    }
  }

  async function handleUploadTranscript(
    file: File,
    options: { autoGenerateAiSummary: boolean },
  ) {
    await handleUploadCommunication("transcripts", file, options);
  }

  async function handleUploadChat(file: File, options: { autoGenerateAiSummary: boolean }) {
    await handleUploadCommunication("chats", file, options);
  }

  function handleOpenAiSummary(noteId: number) {
    setFocusedNoteId(noteId);
    setActiveTab("notes");
  }

  if (loading) {
    return (
      <section className="card">
        <p>Loading request...</p>
      </section>
    );
  }

  if (!request) {
    return (
      <section className="card">
        <p>{error || "Request not found."}</p>
        <button type="button" onClick={onBack}>
          Back to Request Dashboard
        </button>
      </section>
    );
  }

  const summaryRequest = buildSummaryRequest(request, form);
  const passengerCount = request.request_passengers.length;
  const communicationCount =
    request.call_transcripts.length +
    request.chat_logs.length +
    request.request_communications.length;

  return (
    <div className="workspace workspace-tabbed">
      <section className="request-summary-card request-summary-card-compact">
        <div className="request-summary-compact-row">
          <button type="button" className="back-button" onClick={onBack}>
            Back
          </button>

          <div className="request-summary-compact-title">
            <h2>Request #{request.id}</h2>
            <p className="request-summary-compact-client">
              {form.first_name} {form.last_name}
            </p>
            <span
              className={`status-badge ${
                isClosed ? "status-badge-closed" : "status-badge-open"
              }`}
            >
              {request.status}
            </span>
          </div>

          {!mutationsLocked ? (
            <div className="request-summary-compact-actions">
              <button type="button" disabled={submitting} onClick={() => void handleSave()}>
                {submitting ? "Saving..." : "Save"}
              </button>
              <button type="button" className="danger-button" onClick={() => setShowCloseModal(true)}>
                Close request
              </button>
            </div>
          ) : null}
        </div>

        <div className="request-summary-compact-meta">
          <span>{formatDestinationSummary(summaryRequest)}</span>
          <span>{formatCruiseLines(form.cruise_lines)}</span>
          <span>
            {formatDate(form.departure_date)} – {formatDate(form.return_date)}
          </span>
          <span>
            Last worked {request.last_worked_by.username} · {formatTimestamp(request.last_worked_at)}
          </span>
          {request.close_reason ? <span>Closed: {request.close_reason}</span> : null}
        </div>
      </section>

      {!canManage && !isClosed ? (
        <p className="status warning">
          You can view this request, but your agency permissions do not allow managing another agent&apos;s
          request.
        </p>
      ) : null}

      {message || error ? (
        <div className="workspace-status-messages">
          {message ? <p className="status success">{message}</p> : null}
          {error ? <p className="status error">{error}</p> : null}
        </div>
      ) : null}

      <section className="section-card section-tabs-card workspace-tabs-card">
        <div className="section-tablist workspace-tablist" role="tablist" aria-label="Request workspace">
          <button
            type="button"
            role="tab"
            id="workspace-tab-details"
            aria-selected={activeTab === "details"}
            aria-controls="workspace-panel-details"
            className={`section-tab${activeTab === "details" ? " is-active" : ""}`}
            onClick={() => setActiveTab("details")}
          >
            Request detail
          </button>
          <button
            type="button"
            role="tab"
            id="workspace-tab-passengers"
            aria-selected={activeTab === "passengers"}
            aria-controls="workspace-panel-passengers"
            className={`section-tab${activeTab === "passengers" ? " is-active" : ""}`}
            onClick={() => setActiveTab("passengers")}
          >
            Passengers ({passengerCount})
          </button>
          <button
            type="button"
            role="tab"
            id="workspace-tab-proposals"
            aria-selected={activeTab === "proposals"}
            aria-controls="workspace-panel-proposals"
            className={`section-tab${activeTab === "proposals" ? " is-active" : ""}`}
            onClick={() => setActiveTab("proposals")}
          >
            Proposed cruises &amp; insurance
          </button>
          <button
            type="button"
            role="tab"
            id="workspace-tab-communications"
            aria-selected={activeTab === "communications"}
            aria-controls="workspace-panel-communications"
            className={`section-tab${activeTab === "communications" ? " is-active" : ""}`}
            onClick={() => setActiveTab("communications")}
          >
            Communications ({communicationCount})
          </button>
          <button
            type="button"
            role="tab"
            id="workspace-tab-workflow"
            aria-selected={activeTab === "workflow"}
            aria-controls="workspace-panel-workflow"
            className={`section-tab${activeTab === "workflow" ? " is-active" : ""}`}
            onClick={() => setActiveTab("workflow")}
          >
            Workflow
          </button>
          <button
            type="button"
            role="tab"
            id="workspace-tab-notes"
            aria-selected={activeTab === "notes"}
            aria-controls="workspace-panel-notes"
            className={`section-tab${activeTab === "notes" ? " is-active" : ""}`}
            onClick={() => setActiveTab("notes")}
          >
            Notes &amp; research
          </button>
          <button
            type="button"
            role="tab"
            id="workspace-tab-audit"
            aria-selected={activeTab === "audit"}
            aria-controls="workspace-panel-audit"
            className={`section-tab${activeTab === "audit" ? " is-active" : ""}`}
            onClick={() => setActiveTab("audit")}
          >
            Audit info
          </button>
        </div>

        <div className="section-card-body section-tab-body workspace-tab-body">
          {activeTab === "details" ? (
            <div
              role="tabpanel"
              id="workspace-panel-details"
              aria-labelledby="workspace-tab-details"
              className="workspace-tab-panel"
            >
              <RequestForm
                formId="request-edit-form"
                hideActions
                layout="workspace"
                form={form}
                setForm={setForm}
                onSubmit={handleSubmit}
                submitting={submitting}
                submitLabel="Save Changes"
                disabled={mutationsLocked}
                showLeadAttribution
              />
            </div>
          ) : null}

          {activeTab === "passengers" ? (
            <div
              role="tabpanel"
              id="workspace-panel-passengers"
              aria-labelledby="workspace-tab-passengers"
              className="workspace-tab-panel"
            >
              <PassengersSection
                layout="table"
                embeddedInWorkspace
                requestId={requestId}
                passengers={request.request_passengers}
                disabled={mutationsLocked}
                onChanged={refreshRequest}
                onError={setError}
              />
            </div>
          ) : null}

          {activeTab === "proposals" ? (
            <div
              role="tabpanel"
              id="workspace-panel-proposals"
              aria-labelledby="workspace-tab-proposals"
              className="workspace-tab-panel"
            >
              <WorkspaceTabShell
                title="Proposed cruises & insurance"
                meta={`${request.proposed_cruises.length} cruises · ${request.quoted_insurance.length} quotes`}
              >
                <RequestProposalsSection
                  embeddedInWorkspace
                  requestId={requestId}
                  cabinsNeeded={request.cabins_needed ?? 1}
                  cruises={request.proposed_cruises}
                  quotes={request.quoted_insurance}
                  passengers={request.request_passengers}
                  requestPassengerCount={request.passengers}
                  disabled={mutationsLocked}
                  onChanged={refreshRequest}
                  onError={setError}
                  allowAcceptProposedCruise={enterTripInCrmActive && !mutationsLocked}
                  focusedTab={proposalsFocusTab}
                  onFocusedTabHandled={() => setProposalsFocusTab(null)}
                />
              </WorkspaceTabShell>
            </div>
          ) : null}

          {activeTab === "communications" ? (
            <div
              role="tabpanel"
              id="workspace-panel-communications"
              aria-labelledby="workspace-tab-communications"
              className="workspace-tab-panel"
            >
              <WorkspaceTabShell
                title="Communications"
                meta={`${request.call_transcripts.length} transcripts · ${request.chat_logs.length} chats · ${request.request_communications.length} emails`}
              >
                <RequestClientContentSection
                  embeddedInWorkspace
                  requestId={requestId}
                  callTranscripts={request.call_transcripts}
                  chatLogs={request.chat_logs}
                  communications={request.request_communications}
                  notes={request.request_notes}
                  workflows={request.request_workflows}
                  disabled={mutationsLocked}
                  uploadingTranscript={uploadingTranscript}
                  uploadingChat={uploadingChat}
                  onUploadTranscript={handleUploadTranscript}
                  onUploadChat={handleUploadChat}
                  onOpenAiSummary={handleOpenAiSummary}
                  onChanged={refreshRequest}
                  onError={setError}
                />
              </WorkspaceTabShell>
            </div>
          ) : null}

          {activeTab === "workflow" ? (
            <div
              role="tabpanel"
              id="workspace-panel-workflow"
              aria-labelledby="workspace-tab-workflow"
              className="workspace-tab-panel"
            >
              <WorkspaceTabShell
                title="Workflow"
                meta={activeWorkflow ? activeWorkflow.status : "No active workflow"}
              >
                <WorkflowsSection
                  embeddedInWorkspace
                  requestId={requestId}
                  request={request}
                  form={form}
                  workflows={request.request_workflows}
                  disabled={mutationsLocked}
                  onChanged={refreshRequest}
                  onError={setError}
                  onCloseRequest={handleCloseRequest}
                  onNavigateToQuotedInsurance={navigateToQuotedInsurance}
                />
              </WorkspaceTabShell>
            </div>
          ) : null}

          {activeTab === "notes" ? (
            <div
              role="tabpanel"
              id="workspace-panel-notes"
              aria-labelledby="workspace-tab-notes"
              className="workspace-tab-panel"
            >
              <WorkspaceTabShell
                title="Notes & research"
                meta={`${request.request_notes.length} notes · ${request.research_documents.length} documents`}
              >
                <RequestNotesResearchSection
                  embeddedInWorkspace
                  requestId={requestId}
                  notes={request.request_notes}
                  researchDocuments={request.research_documents}
                  focusedNoteId={focusedNoteId}
                  onFocusedNoteHandled={() => setFocusedNoteId(null)}
                  disabled={mutationsLocked}
                  onChanged={refreshRequest}
                  onError={setError}
                />
              </WorkspaceTabShell>
            </div>
          ) : null}

          {activeTab === "audit" ? (
            <div
              role="tabpanel"
              id="workspace-panel-audit"
              aria-labelledby="workspace-tab-audit"
              className="workspace-tab-panel"
            >
              <WorkspaceTabShell title="Audit information" meta="Change history and completed tasks">
                <RequestHistorySection
                  embeddedInWorkspace
                  requestId={requestId}
                  passengers={request.request_passengers}
                  workflows={request.request_workflows}
                />
              </WorkspaceTabShell>
            </div>
          ) : null}
        </div>
      </section>

      <CloseRequestModal
        open={showCloseModal}
        request={{
          ...request,
          first_name: form.first_name,
          last_name: form.last_name,
          cruise_lines: form.cruise_lines,
          destination: form.destination,
          destination_details: form.destination_details ?? null,
          departure_date: form.departure_date,
          return_date: form.return_date,
        }}
        closing={closing}
        onCancel={() => setShowCloseModal(false)}
        onConfirm={handleCloseRequest}
      />
    </div>
  );
}
