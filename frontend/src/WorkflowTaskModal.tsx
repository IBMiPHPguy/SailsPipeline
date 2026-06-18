import CollectPaymentAndBookingCommunicationTaskPanel from "./CollectPaymentAndBookingCommunicationTaskPanel";
import CreateCabinHoldsTaskPanel from "./CreateCabinHoldsTaskPanel";
import CollectPassengerAddressesTaskPanel, {
  isCollectPassengerAddressesTask,
} from "./CollectPassengerAddressesTaskPanel";
import CreateTripInCrmTaskPanel from "./CreateTripInCrmTaskPanel";
import DraftResearchCommunicationTaskPanel from "./DraftResearchCommunicationTaskPanel";
import FollowUpResearchTaskPanel from "./FollowUpResearchTaskPanel";
import ProposedCruisesTaskPanel from "./ProposedCruisesTaskPanel";
import RecordClientResponseTaskPanel from "./RecordClientResponseTaskPanel";
import ResearchTaskBriefPanel from "./ResearchTaskBriefPanel";
import ResearchUploadPanel from "./ResearchUploadPanel";
import SendResearchCommunicationTaskPanel from "./SendResearchCommunicationTaskPanel";
import VerifyPassengerDetailsTaskPanel from "./VerifyPassengerDetailsTaskPanel";
import {
  TASK_KEY_CLIENT_RESPONSE,
  TASK_KEY_COLLECT_PAYMENT_AND_SEND_BOOKING,
  TASK_KEY_CREATE_CABIN_HOLDS,
  TASK_KEY_CREATE_PROPOSED_CRUISES,
  TASK_KEY_CREATE_TRIP_IN_CRM,
  TASK_KEY_DRAFT_RESEARCH_COMMUNICATION,
  TASK_KEY_FOLLOW_UP_RESEARCH,
  TASK_KEY_RESEARCH_CRUISE_OPTIONS,
  TASK_KEY_SEND_RESEARCH_COMMUNICATION,
  TASK_KEY_UPLOAD_RESEARCH_DOCUMENT,
  TASK_KEY_VERIFY_PASSENGER_DETAILS,
  PROPOSED_CRUISE_STATUS_ACCEPTED,
  PROPOSED_CRUISE_STATUS_DEPOSITED,
} from "./formOptions";
import type { RequestTask, TravelRequestDetail, TravelRequestInput } from "./types";
import { formatTimestamp } from "./utils";
import { TASK_STATUS_DONE, getActiveWorkflow, getTaskDisplayStatus, getTaskWorkspaceHint, taskDisplayStatusClass } from "./workflowForm";

type WorkflowTaskModalProps = {
  open: boolean;
  task: RequestTask | null;
  disabled: boolean;
  saving: boolean;
  uploadingResearch: boolean;
  uploadSuccessMessage: string | null;
  request: TravelRequestDetail;
  form: TravelRequestInput;
  onClose: () => void;
  onMarkDone: () => Promise<void>;
  onReopen: () => Promise<void>;
  onUploadResearch: (file: File) => Promise<void>;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
  onCloseRequest: (closeReason: string) => Promise<void>;
};

function TaskGuidance({ taskKey }: { taskKey: string }) {
  const hint = getTaskWorkspaceHint(taskKey);
  if (!hint) {
    return null;
  }

  return (
    <div className="workflow-task-guidance">
      <p>{hint}</p>
    </div>
  );
}

export default function WorkflowTaskModal({
  open,
  task,
  disabled,
  saving,
  uploadingResearch,
  uploadSuccessMessage,
  request,
  form,
  onClose,
  onMarkDone,
  onReopen,
  onUploadResearch,
  onChanged,
  onError,
  onCloseRequest,
}: WorkflowTaskModalProps) {
  if (!open || !task) {
    return null;
  }

  const isDone = task.status === TASK_STATUS_DONE;
  const workspaceHint = getTaskWorkspaceHint(task.task_key);
  const activeWorkflow = getActiveWorkflow(request.request_workflows);
  const acceptedCruise =
    request.proposed_cruises.find((cruise) => cruise.status === PROPOSED_CRUISE_STATUS_ACCEPTED) ?? null;
  const bookingCruise =
    request.proposed_cruises.find(
      (cruise) =>
        cruise.status === PROPOSED_CRUISE_STATUS_ACCEPTED ||
        cruise.status === PROPOSED_CRUISE_STATUS_DEPOSITED,
    ) ?? null;
  const usesCustomSave =
    (task.task_key === TASK_KEY_CLIENT_RESPONSE ||
      task.task_key === TASK_KEY_VERIFY_PASSENGER_DETAILS ||
      task.task_key === TASK_KEY_CREATE_CABIN_HOLDS ||
      task.task_key === TASK_KEY_COLLECT_PAYMENT_AND_SEND_BOOKING ||
      task.task_key === TASK_KEY_CREATE_TRIP_IN_CRM ||
      isCollectPassengerAddressesTask(task.task_key)) &&
    !isDone &&
    !disabled;
  const displayStatus = activeWorkflow ? getTaskDisplayStatus(task, activeWorkflow) : task.status;
  const displayStatusClass = activeWorkflow ? taskDisplayStatusClass(task, activeWorkflow) : task.status === TASK_STATUS_DONE ? "task-status-done" : "task-status-open";

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="modal-card modal-card-wide workflow-task-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="workflow-task-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="modal-card-header">
          <div className="workflow-task-modal-header">
            <div>
              <h3 id="workflow-task-modal-title">{task.title}</h3>
              {task.description ? <p className="workflow-task-modal-description">{task.description}</p> : null}
            </div>
            <span className={`workflow-task-status ${displayStatusClass}`}>{displayStatus}</span>
          </div>
        </header>

        <div className="modal-scroll-body workflow-task-modal-body">
          {isDone && task.completed_by ? (
            <p className="workflow-task-modal-completed meta">
              Completed by {task.completed_by.username}
              {task.completed_at ? ` · ${formatTimestamp(task.completed_at)}` : ""}
            </p>
          ) : null}

          {task.task_key === TASK_KEY_RESEARCH_CRUISE_OPTIONS ? (
            <ResearchTaskBriefPanel request={request} form={form} />
          ) : null}

          {task.task_key === TASK_KEY_UPLOAD_RESEARCH_DOCUMENT && !isDone && !disabled ? (
            <>
              {uploadSuccessMessage ? (
                <p className="status success workflow-task-upload-success">{uploadSuccessMessage}</p>
              ) : null}
              <ResearchUploadPanel
                disabled={disabled}
                uploading={uploadingResearch}
                onUpload={onUploadResearch}
              />
            </>
          ) : null}

          {task.task_key === TASK_KEY_UPLOAD_RESEARCH_DOCUMENT && request.research_documents.length > 0 ? (
            <div className="workflow-task-guidance">
              <p>
                {request.research_documents.length} research document
                {request.research_documents.length === 1 ? "" : "s"} on file. View them in Research Documents on the
                right.
              </p>
            </div>
          ) : null}

          {task.task_key === TASK_KEY_SEND_RESEARCH_COMMUNICATION && (isDone || disabled) && workspaceHint ? (
            <TaskGuidance taskKey={task.task_key} />
          ) : null}

          {task.task_key === TASK_KEY_SEND_RESEARCH_COMMUNICATION && !disabled ? (
            <SendResearchCommunicationTaskPanel
              requestId={request.id}
              communications={request.request_communications}
              disabled={isDone}
              onChanged={onChanged}
              onError={onError}
            />
          ) : null}

          {task.task_key === TASK_KEY_FOLLOW_UP_RESEARCH && !disabled && activeWorkflow ? (
            <FollowUpResearchTaskPanel
              requestId={request.id}
              task={task}
              workflow={activeWorkflow}
              disabled={isDone}
              onChanged={onChanged}
              onError={onError}
            />
          ) : null}

          {task.task_key === TASK_KEY_FOLLOW_UP_RESEARCH && (isDone || disabled) && workspaceHint ? (
            <TaskGuidance taskKey={task.task_key} />
          ) : null}

          {task.task_key === TASK_KEY_CLIENT_RESPONSE && (isDone || disabled) && workspaceHint ? (
            <TaskGuidance taskKey={task.task_key} />
          ) : null}

          {task.task_key === TASK_KEY_CLIENT_RESPONSE && !isDone && !disabled && activeWorkflow ? (
            <RecordClientResponseTaskPanel
              requestId={request.id}
              proposedCruises={request.proposed_cruises}
              workflow={activeWorkflow}
              disabled={disabled}
              onChanged={onChanged}
              onError={onError}
              onCloseRequest={onCloseRequest}
              onSaved={onClose}
            />
          ) : null}

          {task.task_key === TASK_KEY_VERIFY_PASSENGER_DETAILS ? (
            <VerifyPassengerDetailsTaskPanel
              requestId={request.id}
              passengers={request.request_passengers}
              taskId={task.id}
              disabled={disabled}
              isDone={isDone}
              onChanged={onChanged}
              onError={onError}
              onSaved={onClose}
            />
          ) : null}

          {task.task_key === TASK_KEY_CREATE_CABIN_HOLDS ? (
            <CreateCabinHoldsTaskPanel
              requestId={request.id}
              cabinsNeeded={request.cabins_needed}
              reservationIds={request.cabin_hold_reservation_ids}
              bookingCruise={bookingCruise}
              taskId={task.id}
              disabled={disabled}
              isDone={isDone}
              onChanged={onChanged}
              onError={onError}
              onSaved={onClose}
            />
          ) : null}

          {task.task_key === TASK_KEY_COLLECT_PAYMENT_AND_SEND_BOOKING ? (
            <CollectPaymentAndBookingCommunicationTaskPanel
              requestId={request.id}
              cabinsNeeded={request.cabins_needed}
              reservationIds={request.cabin_hold_reservation_ids}
              acceptedCruise={acceptedCruise}
              task={task}
              disabled={disabled}
              isDone={isDone}
              onChanged={onChanged}
              onError={onError}
              onSaved={onClose}
            />
          ) : null}

          {isCollectPassengerAddressesTask(task.task_key) ? (
            <CollectPassengerAddressesTaskPanel
              requestId={request.id}
              passengers={request.request_passengers}
              taskId={task.id}
              disabled={disabled}
              isDone={isDone}
              onChanged={onChanged}
              onError={onError}
              onSaved={onClose}
            />
          ) : null}

          {task.task_key === TASK_KEY_CREATE_TRIP_IN_CRM ? (
            <CreateTripInCrmTaskPanel
              requestId={request.id}
              request={request}
              form={form}
              task={task}
              disabled={disabled}
              isDone={isDone}
              onChanged={onChanged}
              onError={onError}
              onSaved={onClose}
            />
          ) : null}

          {task.task_key !== TASK_KEY_RESEARCH_CRUISE_OPTIONS &&
          task.task_key !== TASK_KEY_UPLOAD_RESEARCH_DOCUMENT &&
          task.task_key !== TASK_KEY_CREATE_PROPOSED_CRUISES &&
          task.task_key !== TASK_KEY_DRAFT_RESEARCH_COMMUNICATION &&
          task.task_key !== TASK_KEY_SEND_RESEARCH_COMMUNICATION &&
          task.task_key !== TASK_KEY_FOLLOW_UP_RESEARCH &&
          task.task_key !== TASK_KEY_CLIENT_RESPONSE &&
          task.task_key !== TASK_KEY_VERIFY_PASSENGER_DETAILS &&
          task.task_key !== TASK_KEY_CREATE_CABIN_HOLDS &&
          task.task_key !== TASK_KEY_COLLECT_PAYMENT_AND_SEND_BOOKING &&
          task.task_key !== TASK_KEY_CREATE_TRIP_IN_CRM &&
          !isCollectPassengerAddressesTask(task.task_key) &&
          workspaceHint ? (
            <TaskGuidance taskKey={task.task_key} />
          ) : null}

          {task.task_key === TASK_KEY_CREATE_PROPOSED_CRUISES && !isDone && !disabled ? (
            <ProposedCruisesTaskPanel
              requestId={request.id}
              researchDocuments={request.research_documents}
              disabled={disabled}
              onChanged={onChanged}
              onError={onError}
            />
          ) : null}

          {task.task_key === TASK_KEY_CREATE_PROPOSED_CRUISES && request.proposed_cruises.length > 0 ? (
            <div className="workflow-task-guidance">
              <p>
                {request.proposed_cruises.length} proposed cruise
                {request.proposed_cruises.length === 1 ? "" : "s"} on the request.
              </p>
            </div>
          ) : null}

          {task.task_key === TASK_KEY_DRAFT_RESEARCH_COMMUNICATION && !isDone && !disabled ? (
            <DraftResearchCommunicationTaskPanel
              requestId={request.id}
              requestWorkflowId={activeWorkflow?.id ?? null}
              proposedCruises={request.proposed_cruises}
              disabled={disabled}
              onChanged={onChanged}
              onError={onError}
            />
          ) : null}

          {task.task_key === TASK_KEY_DRAFT_RESEARCH_COMMUNICATION &&
          request.request_communications.length > 0 ? (
            <p className="meta workflow-task-context">
              {request.request_communications.length} communication
              {request.request_communications.length === 1 ? "" : "s"} saved so far.
            </p>
          ) : null}
        </div>

        <div className="modal-actions modal-actions-footer">
          <button type="button" className="modal-secondary" disabled={saving} onClick={onClose}>
            Close
          </button>
          {!disabled && isDone ? (
            <button type="button" className="modal-secondary" disabled={saving} onClick={() => void onReopen()}>
              {saving ? "Updating..." : "Reopen task"}
            </button>
          ) : null}
          {!disabled && !isDone && !usesCustomSave ? (
            <button type="button" disabled={saving || uploadingResearch} onClick={() => void onMarkDone()}>
              {saving ? "Saving..." : "Mark task done"}
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
