import { useEffect, useMemo, useState } from "react";
import {
  updateProposedCruise,
  updateTask,
  uploadResearchDocument,
} from "./api";
import CloseReasonPicker from "./CloseReasonPicker";
import ProposedCruiseRejectionReasonFields from "./ProposedCruiseRejectionReasonFields";
import ResearchUploadPanel from "./ResearchUploadPanel";
import {
  PROPOSED_CRUISE_STATUS_ACCEPTED,
  PROPOSED_CRUISE_STATUS_DEPOSITED,
  PROPOSED_CRUISE_STATUS_PROPOSED,
  PROPOSED_CRUISE_STATUS_REJECTED,
  PRIMARY_CLOSE_REASON,
  TASK_KEY_CLIENT_RESPONSE,
  TASK_KEY_FOLLOW_UP_RESEARCH,
  TASK_STATUS_DONE,
} from "./formOptions";
import type { ProposedCruise, RequestWorkflow } from "./types";
import {
  buildProposedCruiseRejectionPayload,
  EMPTY_PROPOSED_CRUISE_REJECTION,
  formatProposedCruiseRejectionReason,
  type ProposedCruiseRejectionInput,
  validateProposedCruiseRejectionInput,
} from "./proposedCruiseRejection";
import { proposedCruiseStatusClass } from "./proposedCruiseForm";
import { formatDate } from "./utils";
import { TASK_STATUS_OPEN } from "./workflowForm";

type CruiseDecision = typeof PROPOSED_CRUISE_STATUS_ACCEPTED | typeof PROPOSED_CRUISE_STATUS_REJECTED;

type RejectedOutcome = "close_request" | "new_research";

type RecordClientResponseTaskPanelProps = {
  requestId: number;
  proposedCruises: ProposedCruise[];
  workflow: RequestWorkflow;
  disabled: boolean;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
  onCloseRequest: (closeReason: string) => Promise<void>;
  onSaved: () => void;
};

function formatMoney(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(value);
}

function initialDecision(): typeof PROPOSED_CRUISE_STATUS_PROPOSED {
  return PROPOSED_CRUISE_STATUS_PROPOSED;
}

export default function RecordClientResponseTaskPanel({
  requestId,
  proposedCruises,
  workflow,
  disabled,
  onChanged,
  onError,
  onCloseRequest,
  onSaved,
}: RecordClientResponseTaskPanelProps) {
  const activeProposedCruises = useMemo(
    () => proposedCruises.filter((cruise) => cruise.status === PROPOSED_CRUISE_STATUS_PROPOSED),
    [proposedCruises],
  );
  const decidedCruises = useMemo(
    () => proposedCruises.filter((cruise) => cruise.status !== PROPOSED_CRUISE_STATUS_PROPOSED),
    [proposedCruises],
  );
  const acceptedCruises = useMemo(
    () =>
      proposedCruises.filter(
        (cruise) =>
          cruise.status === PROPOSED_CRUISE_STATUS_ACCEPTED ||
          cruise.status === PROPOSED_CRUISE_STATUS_DEPOSITED,
      ),
    [proposedCruises],
  );
  const responsesRecordedElsewhere =
    activeProposedCruises.length === 0 && decidedCruises.length > 0;
  const allDecidedRejected =
    responsesRecordedElsewhere &&
    decidedCruises.every((cruise) => cruise.status === PROPOSED_CRUISE_STATUS_REJECTED);
  const followUpTask = workflow.tasks.find((task) => task.task_key === TASK_KEY_FOLLOW_UP_RESEARCH) ?? null;
  const clientResponseTask = workflow.tasks.find((task) => task.task_key === TASK_KEY_CLIENT_RESPONSE) ?? null;
  const followUpOpen = followUpTask?.status === TASK_STATUS_OPEN;

  const [decisions, setDecisions] = useState<Record<number, CruiseDecision | typeof PROPOSED_CRUISE_STATUS_PROPOSED>>(
    {},
  );
  const [rejectionInputs, setRejectionInputs] = useState<Record<number, ProposedCruiseRejectionInput>>({});
  const [markFollowUpDone, setMarkFollowUpDone] = useState(true);
  const [rejectedOutcome, setRejectedOutcome] = useState<RejectedOutcome>("new_research");
  const [closeReason, setCloseReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [uploadingResearch, setUploadingResearch] = useState(false);
  const [researchUploaded, setResearchUploaded] = useState(false);

  useEffect(() => {
    const nextDecisions: Record<number, CruiseDecision | typeof PROPOSED_CRUISE_STATUS_PROPOSED> = {};
    const nextRejections: Record<number, ProposedCruiseRejectionInput> = {};
    for (const cruise of activeProposedCruises) {
      nextDecisions[cruise.id] = initialDecision();
      nextRejections[cruise.id] = { ...EMPTY_PROPOSED_CRUISE_REJECTION };
    }
    setDecisions(nextDecisions);
    setRejectionInputs(nextRejections);
  }, [activeProposedCruises]);

  useEffect(() => {
    setMarkFollowUpDone(followUpOpen);
  }, [followUpOpen, followUpTask?.id]);

  const pendingDecisions = useMemo(
    () =>
      activeProposedCruises.map((cruise) => ({
        cruise,
        decision: decisions[cruise.id] ?? initialDecision(),
      })),
    [activeProposedCruises, decisions],
  );

  const allRejected = useMemo(
    () =>
      pendingDecisions.length > 0 &&
      pendingDecisions.every(({ decision }) => decision === PROPOSED_CRUISE_STATUS_REJECTED),
    [pendingDecisions],
  );

  const hasUndecided = pendingDecisions.some(({ decision }) => decision === PROPOSED_CRUISE_STATUS_PROPOSED);

  useEffect(() => {
    if (allRejected && rejectedOutcome === "close_request" && closeReason === PRIMARY_CLOSE_REASON) {
      setCloseReason("");
    }
  }, [allRejected, rejectedOutcome, closeReason]);

  function setCruiseDecision(cruiseId: number, decision: CruiseDecision) {
    setDecisions((current) => ({
      ...current,
      [cruiseId]: decision,
    }));

    if (decision === PROPOSED_CRUISE_STATUS_REJECTED) {
      setRejectionInputs((current) => ({
        ...current,
        [cruiseId]: current[cruiseId] ?? { ...EMPTY_PROPOSED_CRUISE_REJECTION },
      }));
    }
  }

  async function completeClientResponseWorkflow() {
    if (followUpOpen && markFollowUpDone && followUpTask) {
      await updateTask(requestId, followUpTask.id, { status: TASK_STATUS_DONE });
    }

    if (clientResponseTask) {
      await updateTask(requestId, clientResponseTask.id, { status: TASK_STATUS_DONE });
    }

    await updateWorkflow(requestId, workflow.id, { status: WORKFLOW_STATUS_COMPLETED });
    await onChanged();
    onSaved();
  }

  async function handleMarkRecordedComplete() {
    setSaving(true);
    onError("");
    try {
      await completeClientResponseWorkflow();
    } catch (saveError) {
      onError(saveError instanceof Error ? saveError.message : "Unable to complete client response task.");
    } finally {
      setSaving(false);
    }
  }

  async function handleResearchUpload(file: File) {
    if (!file.name.toLowerCase().endsWith(".txt")) {
      onError("Research documents must be .txt files.");
      return;
    }

    setUploadingResearch(true);
    onError("");
    try {
      await uploadResearchDocument(requestId, file);
      setResearchUploaded(true);
      await onChanged();
    } catch (uploadError) {
      onError(uploadError instanceof Error ? uploadError.message : "Unable to upload research document.");
    } finally {
      setUploadingResearch(false);
    }
  }

  async function handleSaveResponse() {
    if (activeProposedCruises.length === 0) {
      onError("No proposed cruises are awaiting a client response.");
      return;
    }

    if (hasUndecided) {
      onError("Mark each proposed cruise as accepted or rejected before saving.");
      return;
    }

    for (const { cruise, decision } of pendingDecisions) {
      if (decision !== PROPOSED_CRUISE_STATUS_REJECTED) {
        continue;
      }
      const rejectionInput = rejectionInputs[cruise.id] ?? EMPTY_PROPOSED_CRUISE_REJECTION;
      const rejectionError = validateProposedCruiseRejectionInput(rejectionInput);
      if (rejectionError) {
        onError(`${cruise.ship}: ${rejectionError}`);
        return;
      }
    }

    if (allRejected && rejectedOutcome === "close_request" && !closeReason) {
      onError("Select a close reason before closing the request.");
      return;
    }

    if (allRejected && rejectedOutcome === "new_research" && !researchUploaded) {
      onError("Upload a new research document before starting another research workflow.");
      return;
    }

    setSaving(true);
    onError("");
    try {
      for (const { cruise, decision } of pendingDecisions) {
        if (decision === PROPOSED_CRUISE_STATUS_PROPOSED || decision === cruise.status) {
          continue;
        }
        if (decision === PROPOSED_CRUISE_STATUS_REJECTED) {
          const rejectionInput = rejectionInputs[cruise.id] ?? EMPTY_PROPOSED_CRUISE_REJECTION;
          await updateProposedCruise(requestId, cruise.id, {
            status: decision,
            ...buildProposedCruiseRejectionPayload(rejectionInput),
          });
          continue;
        }
        await updateProposedCruise(requestId, cruise.id, { status: decision });
      }

      if (followUpOpen && markFollowUpDone && followUpTask) {
        await updateTask(requestId, followUpTask.id, { status: TASK_STATUS_DONE });
      }

      if (clientResponseTask) {
        await updateTask(requestId, clientResponseTask.id, { status: TASK_STATUS_DONE });
      }

      if (allRejected && rejectedOutcome === "close_request") {
        await onCloseRequest(closeReason);
      }

      await onChanged();
      onSaved();
    } catch (saveError) {
      onError(saveError instanceof Error ? saveError.message : "Unable to save client response.");
    } finally {
      setSaving(false);
    }
  }

  if (activeProposedCruises.length === 0 && !responsesRecordedElsewhere) {
    return (
      <div className="record-client-response-task-panel">
        <p className="status error">No proposed cruises are awaiting a client response.</p>
      </div>
    );
  }

  if (responsesRecordedElsewhere) {
    return (
      <div className="record-client-response-task-panel">
        <p className="workflow-task-guidance">
          {acceptedCruises.length > 0
            ? "Client responses were already recorded on the proposed cruises. Review the accepted options below, then mark this task complete when you are ready."
            : "Client responses were already recorded on the proposed cruises. Review the decisions below, then mark this task complete when you are ready."}
        </p>

        <ul className="record-client-response-cruise-list">
          {decidedCruises.map((cruise) => {
            const rejectionReason = formatProposedCruiseRejectionReason(cruise);

            return (
              <li key={cruise.id}>
                <div className="record-client-response-cruise-summary">
                  <div className="record-client-response-cruise-summary-header">
                    <strong>
                      {cruise.cruise_line} · {cruise.ship}
                    </strong>
                    <span className={`proposed-cruise-status ${proposedCruiseStatusClass(cruise.status)}`}>
                      {cruise.status}
                    </span>
                  </div>
                  <div className="meta">
                    Departs {formatDate(cruise.departure_date)} · {cruise.number_of_nights} nights ·{" "}
                    {cruise.itinerary_name}
                  </div>
                  <div className="meta">
                    {cruise.room_category} · Cost {formatMoney(Number(cruise.cost))}
                  </div>
                  {rejectionReason ? (
                    <div className="meta">Rejected reason: {rejectionReason}</div>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ul>

        {followUpOpen ? (
          <label className="record-client-response-follow-up">
            <input
              type="checkbox"
              checked={markFollowUpDone}
              disabled={disabled || saving}
              onChange={(event) => setMarkFollowUpDone(event.target.checked)}
            />
            Mark follow-up task as done (client responded — no follow-up needed)
          </label>
        ) : null}

        {allDecidedRejected ? (
          <p className="field-hint">
            All options were rejected. Close the request or start a new Research workflow from the request if needed.
          </p>
        ) : null}

        {!disabled ? (
          <button type="button" disabled={saving} onClick={() => void handleMarkRecordedComplete()}>
            {saving ? "Saving..." : "Mark client response complete"}
          </button>
        ) : null}
      </div>
    );
  }

  return (
    <div className="record-client-response-task-panel">
      <ul className="record-client-response-cruise-list">
        {pendingDecisions.map(({ cruise, decision }) => (
          <li key={cruise.id}>
            <div className="record-client-response-cruise-summary">
              <strong>
                {cruise.cruise_line} · {cruise.ship}
              </strong>
              <div className="meta">
                Departs {formatDate(cruise.departure_date)} · {cruise.number_of_nights} nights · {cruise.itinerary_name}
              </div>
              <div className="meta">
                {cruise.room_category} · Cost {formatMoney(Number(cruise.cost))}
              </div>
            </div>
            <fieldset className="record-client-response-decision">
              <legend className="sr-only">Client decision for {cruise.ship}</legend>
              <label>
                <input
                  type="radio"
                  name={`cruise-decision-${cruise.id}`}
                  checked={decision === PROPOSED_CRUISE_STATUS_ACCEPTED}
                  disabled={disabled || saving}
                  onChange={() => setCruiseDecision(cruise.id, PROPOSED_CRUISE_STATUS_ACCEPTED)}
                />
                Accepted
              </label>
              <label>
                <input
                  type="radio"
                  name={`cruise-decision-${cruise.id}`}
                  checked={decision === PROPOSED_CRUISE_STATUS_REJECTED}
                  disabled={disabled || saving}
                  onChange={() => setCruiseDecision(cruise.id, PROPOSED_CRUISE_STATUS_REJECTED)}
                />
                Rejected
              </label>
            </fieldset>
            {decision === PROPOSED_CRUISE_STATUS_REJECTED ? (
              <ProposedCruiseRejectionReasonFields
                idPrefix={`client-response-${cruise.id}`}
                value={rejectionInputs[cruise.id] ?? EMPTY_PROPOSED_CRUISE_REJECTION}
                disabled={disabled || saving}
                onChange={(value) =>
                  setRejectionInputs((current) => ({
                    ...current,
                    [cruise.id]: value,
                  }))
                }
              />
            ) : null}
          </li>
        ))}
      </ul>

      {followUpOpen ? (
        <label className="record-client-response-follow-up">
          <input
            type="checkbox"
            checked={markFollowUpDone}
            disabled={disabled || saving}
            onChange={(event) => setMarkFollowUpDone(event.target.checked)}
          />
          Mark follow-up task as done (client responded — no follow-up needed)
        </label>
      ) : null}

      {allRejected ? (
        <div className="record-client-response-rejected-outcome">
          <p className="workflow-task-guidance">
            <strong>All options were rejected.</strong> Upload new research if needed, then start a Research workflow from the Workflows tab — or close the request.
          </p>
          <fieldset className="record-client-response-outcome-options">
            <legend className="sr-only">Next step after all options rejected</legend>
            <label>
              <input
                type="radio"
                name="rejected-outcome"
                checked={rejectedOutcome === "new_research"}
                disabled={disabled || saving}
                onChange={() => setRejectedOutcome("new_research")}
              />
              Start a new Research workflow after saving
            </label>
            <label>
              <input
                type="radio"
                name="rejected-outcome"
                checked={rejectedOutcome === "close_request"}
                disabled={disabled || saving}
                onChange={() => setRejectedOutcome("close_request")}
              />
              Close the request
            </label>
          </fieldset>

          {rejectedOutcome === "new_research" ? (
            <div className="record-client-response-new-research">
              <p className="field-hint">Upload the new research document required for the next round.</p>
              <ResearchUploadPanel
                disabled={disabled || saving}
                uploading={uploadingResearch}
                onUpload={handleResearchUpload}
              />
              {researchUploaded ? (
                <p className="status success workflow-task-upload-success">Research document uploaded.</p>
              ) : null}
            </div>
          ) : (
            <CloseReasonPicker value={closeReason} onChange={setCloseReason} includePrimaryReason={false} />
          )}
        </div>
      ) : null}

      {!disabled && !hasUndecided ? (
        <button type="button" disabled={saving || uploadingResearch} onClick={() => void handleSaveResponse()}>
          {saving ? "Saving response..." : "Save client response"}
        </button>
      ) : null}
    </div>
  );
}
