import { useEffect, useMemo, useState } from "react";
import {
  startWorkflow,
  updateProposedCruise,
  updateTask,
  updateWorkflow,
  uploadResearchDocument,
} from "./api";
import CloseReasonPicker from "./CloseReasonPicker";
import ResearchUploadPanel from "./ResearchUploadPanel";
import {
  PROPOSED_CRUISE_STATUS_ACCEPTED,
  PROPOSED_CRUISE_STATUS_PROPOSED,
  PROPOSED_CRUISE_STATUS_REJECTED,
  PRIMARY_CLOSE_REASON,
  TASK_KEY_CLIENT_RESPONSE,
  TASK_KEY_FOLLOW_UP_RESEARCH,
  TASK_STATUS_DONE,
  WORKFLOW_STATUS_COMPLETED,
  WORKFLOW_TYPE_RESEARCH,
} from "./formOptions";
import type { ProposedCruise, RequestWorkflow } from "./types";
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
  const followUpTask = workflow.tasks.find((task) => task.task_key === TASK_KEY_FOLLOW_UP_RESEARCH) ?? null;
  const clientResponseTask = workflow.tasks.find((task) => task.task_key === TASK_KEY_CLIENT_RESPONSE) ?? null;
  const followUpOpen = followUpTask?.status === TASK_STATUS_OPEN;

  const [decisions, setDecisions] = useState<Record<number, CruiseDecision | typeof PROPOSED_CRUISE_STATUS_PROPOSED>>(
    {},
  );
  const [markFollowUpDone, setMarkFollowUpDone] = useState(true);
  const [rejectedOutcome, setRejectedOutcome] = useState<RejectedOutcome>("new_research");
  const [closeReason, setCloseReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [uploadingResearch, setUploadingResearch] = useState(false);
  const [researchUploaded, setResearchUploaded] = useState(false);

  useEffect(() => {
    const nextDecisions: Record<number, CruiseDecision | typeof PROPOSED_CRUISE_STATUS_PROPOSED> = {};
    for (const cruise of activeProposedCruises) {
      nextDecisions[cruise.id] = initialDecision();
    }
    setDecisions(nextDecisions);
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
    setDecisions((current) => {
      if (decision === PROPOSED_CRUISE_STATUS_ACCEPTED) {
        const next: Record<number, CruiseDecision | typeof PROPOSED_CRUISE_STATUS_PROPOSED> = { ...current };
        for (const cruise of activeProposedCruises) {
          next[cruise.id] =
            cruise.id === cruiseId ? PROPOSED_CRUISE_STATUS_ACCEPTED : PROPOSED_CRUISE_STATUS_REJECTED;
        }
        return next;
      }

      return {
        ...current,
        [cruiseId]: decision,
      };
    });
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
        await updateProposedCruise(requestId, cruise.id, { status: decision });
      }

      if (followUpOpen && markFollowUpDone && followUpTask) {
        await updateTask(requestId, followUpTask.id, { status: TASK_STATUS_DONE });
      }

      if (clientResponseTask) {
        await updateTask(requestId, clientResponseTask.id, { status: TASK_STATUS_DONE });
      }

      await updateWorkflow(requestId, workflow.id, { status: WORKFLOW_STATUS_COMPLETED });

      if (allRejected && rejectedOutcome === "close_request") {
        await onCloseRequest(closeReason);
      } else if (allRejected && rejectedOutcome === "new_research") {
        await startWorkflow(requestId, WORKFLOW_TYPE_RESEARCH, workflow.id);
      }

      await onChanged();
      onSaved();
    } catch (saveError) {
      onError(saveError instanceof Error ? saveError.message : "Unable to save client response.");
    } finally {
      setSaving(false);
    }
  }

  if (activeProposedCruises.length === 0) {
    return (
      <div className="record-client-response-task-panel">
        <p className="status error">No proposed cruises are awaiting a client response.</p>
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
            <strong>All options were rejected.</strong> Close the request or start a new Research workflow.
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
              Start a new Research workflow
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
