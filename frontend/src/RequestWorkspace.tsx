import { FormEvent, useEffect, useRef, useState } from "react";
import { fetchRequest, updateRequest, uploadChatLog, uploadTranscript } from "./api";
import RequestClientContentSection from "./RequestClientContentSection";
import RequestHistorySection from "./RequestHistorySection";
import RequestNotesResearchSection from "./RequestNotesResearchSection";
import RequestProposalsSection from "./RequestProposalsSection";
import CloseRequestModal from "./CloseRequestModal";
import { formatCruiseLines } from "./CruiseLineMultiSelect";
import PassengersSection from "./PassengersSection";
import RequestForm, { emptyRequestForm, isReturnAfterDeparture } from "./RequestForm";
import WorkflowsSection from "./WorkflowsSection";
import { useClientContentFullWidth } from "./useClientContentFullWidth";
import { REQUEST_STATUS_CLOSED, WORKFLOW_TYPE_ENTER_TRIP_CRM } from "./formOptions";
import type { TravelRequestDetail, TravelRequestInput } from "./types";
import { formatDestinationSummary, formatDate, formatTimestamp } from "./utils";
import { getActiveWorkflow } from "./workflowForm";

type RequestWorkspaceProps = {
  requestId: number;
  onBack: () => void;
  onClosed: () => void;
};

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

export default function RequestWorkspace({ requestId, onBack, onClosed }: RequestWorkspaceProps) {
  const [request, setRequest] = useState<TravelRequestDetail | null>(null);
  const [form, setForm] = useState<TravelRequestInput>(emptyRequestForm);
  const [showCloseModal, setShowCloseModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [closing, setClosing] = useState(false);
  const [uploadingTranscript, setUploadingTranscript] = useState(false);
  const [uploadingChat, setUploadingChat] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const mainRef = useRef<HTMLDivElement>(null);
  const sidebarTopRef = useRef<HTMLDivElement>(null);
  const sidebarRef = useRef<HTMLDivElement>(null);
  const clientContentRef = useRef<HTMLDivElement>(null);
  const clientContentExpanded = useClientContentFullWidth(
    mainRef,
    sidebarTopRef,
    sidebarRef,
    clientContentRef,
    Boolean(request && !loading),
  );

  const isClosed = request?.status === REQUEST_STATUS_CLOSED;
  const activeWorkflow = request ? getActiveWorkflow(request.request_workflows) : null;
  const enterTripInCrmActive = activeWorkflow?.workflow_type === WORKFLOW_TYPE_ENTER_TRIP_CRM;

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

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isClosed) {
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

  async function handleUploadTranscript(file: File) {
    setUploadingTranscript(true);
    setError("");
    try {
      await uploadTranscript(requestId, file);
      await refreshRequest();
      setMessage("Call transcript uploaded.");
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Unable to upload transcript.");
    } finally {
      setUploadingTranscript(false);
    }
  }

  async function handleUploadChat(file: File) {
    setUploadingChat(true);
    setError("");
    try {
      await uploadChatLog(requestId, file);
      await refreshRequest();
      setMessage("Chat log uploaded.");
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Unable to upload chat log.");
    } finally {
      setUploadingChat(false);
    }
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
          Back to dashboard
        </button>
      </section>
    );
  }

  return (
    <div className="workspace">
      <section className="request-summary-card">
        <div className="request-summary-card-top">
          <button type="button" className="back-button" onClick={onBack}>
            Back to dashboard
          </button>
          <span
            className={`status-badge ${
              isClosed ? "status-badge-closed" : "status-badge-open"
            }`}
          >
            {request.status}
          </span>
        </div>

        <div className="request-summary-card-main">
          <h2>Request #{request.id}</h2>
          <p className="request-summary-client">
            {form.first_name} {form.last_name}
          </p>
        </div>

        <dl className="request-summary-details">
          <div className="request-summary-detail">
            <dt>Destination</dt>
            <dd>{formatDestinationSummary(buildSummaryRequest(request, form))}</dd>
          </div>
          <div className="request-summary-detail">
            <dt>Cruise lines</dt>
            <dd>{formatCruiseLines(form.cruise_lines)}</dd>
          </div>
          <div className="request-summary-detail">
            <dt>Travel dates</dt>
            <dd>
              {formatDate(form.departure_date)} to {formatDate(form.return_date)}
            </dd>
          </div>
          <div className="request-summary-detail">
            <dt>Last worked</dt>
            <dd>
              {request.last_worked_by.username} · {formatTimestamp(request.last_worked_at)}
            </dd>
          </div>
          {request.close_reason ? (
            <div className="request-summary-detail">
              <dt>Close reason</dt>
              <dd>{request.close_reason}</dd>
            </div>
          ) : null}
        </dl>
      </section>

      <div
        className={`workspace-grid${clientContentExpanded ? " is-client-expanded" : ""}`}
      >
        <div className="workspace-main" ref={mainRef}>
          <section className="section-card">
            <header className="section-card-header">
              <h3>Request Details</h3>
            </header>
            <div className="section-card-body">
              <RequestForm
                formId="request-edit-form"
                hideActions
                form={form}
                setForm={setForm}
                onSubmit={handleSubmit}
                submitting={submitting}
                submitLabel="Save Changes"
                disabled={isClosed}
              />
            </div>
          </section>
        </div>

        <div className="workspace-sidebar" ref={sidebarRef}>
          <div className="workspace-sidebar-top" ref={sidebarTopRef}>
            <PassengersSection
              requestId={requestId}
              passengers={request.request_passengers}
              disabled={isClosed}
              onChanged={refreshRequest}
              onError={setError}
            />
            <RequestProposalsSection
              requestId={requestId}
              cabinsNeeded={request.cabins_needed ?? 1}
              cabinHoldReservationIds={request.cabin_hold_reservation_ids ?? []}
              cruises={request.proposed_cruises}
              quotes={request.quoted_insurance}
              passengers={request.request_passengers}
              disabled={isClosed}
              onChanged={refreshRequest}
              onError={setError}
              allowAcceptProposedCruise={enterTripInCrmActive && !isClosed}
            />
          </div>
          <div className="workspace-client-content" ref={clientContentRef}>
            <RequestClientContentSection
              requestId={requestId}
              callTranscripts={request.call_transcripts}
              chatLogs={request.chat_logs}
              communications={request.request_communications}
              workflows={request.request_workflows}
              disabled={isClosed}
              uploadingTranscript={uploadingTranscript}
              uploadingChat={uploadingChat}
              onUploadTranscript={handleUploadTranscript}
              onUploadChat={handleUploadChat}
              onChanged={refreshRequest}
              onError={setError}
            />
          </div>
        </div>
      </div>

      <div className="workspace-full-width">
        <WorkflowsSection
          requestId={requestId}
          request={request}
          form={form}
          workflows={request.request_workflows}
          disabled={isClosed}
          onChanged={refreshRequest}
          onError={setError}
          onCloseRequest={handleCloseRequest}
        />
      </div>

      <RequestNotesResearchSection
        requestId={requestId}
        notes={request.request_notes}
        researchDocuments={request.research_documents}
        disabled={isClosed}
        onChanged={refreshRequest}
        onError={setError}
      />

      <RequestHistorySection
        requestId={requestId}
        passengers={request.request_passengers}
        workflows={request.request_workflows}
      />

      {message ? <p className="status success">{message}</p> : null}
      {error ? <p className="status error">{error}</p> : null}

      {!isClosed ? (
        <div className="workspace-actions">
          <button type="submit" form="request-edit-form" disabled={submitting}>
            {submitting ? "Saving..." : "Save Changes"}
          </button>
          <button type="button" className="danger-button" onClick={() => setShowCloseModal(true)}>
            Close request
          </button>
        </div>
      ) : null}

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
