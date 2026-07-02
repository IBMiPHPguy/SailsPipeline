import type { ReactNode } from "react";
import CollectPaymentAndBookingCommunicationTaskPanel from "./CollectPaymentAndBookingCommunicationTaskPanel";
import CreateCabinHoldsTaskPanel from "./CreateCabinHoldsTaskPanel";
import CollectPassengerAddressesTaskPanel, {
  isCollectPassengerAddressesTask,
} from "./CollectPassengerAddressesTaskPanel";
import CreateTripInCrmTaskPanel from "./CreateTripInCrmTaskPanel";
import { getCrmEntryProposedCruises } from "./crmEntrySummary";
import DraftResearchCommunicationTaskPanel from "./DraftResearchCommunicationTaskPanel";
import FollowUpResearchTaskPanel from "./FollowUpResearchTaskPanel";
import {
  LEGACY_TASK_KEY_COLLECT_LEAD_PASSENGER_ADDRESSES,
  TASK_KEY_ACCEPT_MASTER_TERMS,
  TASK_KEY_CLIENT_RESPONSE,
  TASK_KEY_COLLECT_PAYMENT_AND_SEND_BOOKING,
  TASK_KEY_COLLECT_PASSENGER_ADDRESSES,
  TASK_KEY_CREATE_CABIN_HOLDS,
  TASK_KEY_CREATE_PROPOSED_CRUISES,
  TASK_KEY_CREATE_TRIP_IN_CRM,
  TASK_KEY_DRAFT_RESEARCH_COMMUNICATION,
  TASK_KEY_FOLLOW_UP_RESEARCH,
  TASK_KEY_RESEARCH_CRUISE_OPTIONS,
  TASK_KEY_SEND_RESEARCH_COMMUNICATION,
  TASK_KEY_UPLOAD_RESEARCH_DOCUMENT,
  TASK_KEY_VERIFY_PASSENGER_DETAILS,
} from "./formOptions";
import MasterTermsTaskPanel from "./MasterTermsTaskPanel";
import ProposedCruisesTaskPanel from "./ProposedCruisesTaskPanel";
import RecordClientResponseTaskPanel from "./RecordClientResponseTaskPanel";
import ResearchTaskBriefPanel from "./ResearchTaskBriefPanel";
import ResearchUploadPanel from "./ResearchUploadPanel";
import SendResearchCommunicationTaskPanel from "./SendResearchCommunicationTaskPanel";
import VerifyPassengerDetailsTaskPanel from "./VerifyPassengerDetailsTaskPanel";
import type { RequestTask, RequestWorkflow, TravelRequestDetail, TravelRequestInput } from "./types";
import { isManualCheckTask } from "./workflowForm";

export type WorkflowTaskPanelContext = {
  task: RequestTask;
  request: TravelRequestDetail;
  form: TravelRequestInput;
  disabled: boolean;
  isDone: boolean;
  uploadingResearch: boolean;
  uploadSuccessMessage: string | null;
  activeWorkflow: RequestWorkflow | null;
  bookingCruises: ReturnType<typeof getCrmEntryProposedCruises>;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
  onCloseRequest: (closeReason: string) => Promise<void>;
  onUploadResearch: (file: File) => Promise<void>;
  onSaved: () => void;
};

export type WorkflowTaskPanelDefinition = {
  usesCustomSave?: boolean;
  showGuidanceWhenReadOnly?: boolean;
  render: (context: WorkflowTaskPanelContext) => ReactNode;
};

function registerCollectPassengerAddresses(): WorkflowTaskPanelDefinition {
  return {
    usesCustomSave: true,
    render: (context) => (
      <CollectPassengerAddressesTaskPanel
        requestId={context.request.id}
        passengers={context.request.request_passengers}
        taskId={context.task.id}
        disabled={context.disabled}
        isDone={context.isDone}
        onChanged={context.onChanged}
        onError={context.onError}
        onSaved={context.onSaved}
      />
    ),
  };
}

export const WORKFLOW_TASK_PANEL_REGISTRY: Record<string, WorkflowTaskPanelDefinition> = {
  [TASK_KEY_RESEARCH_CRUISE_OPTIONS]: {
    render: (context) => <ResearchTaskBriefPanel request={context.request} form={context.form} />,
  },
  [TASK_KEY_UPLOAD_RESEARCH_DOCUMENT]: {
    render: (context) => (
      <>
        {!context.isDone && !context.disabled ? (
          <>
            {context.uploadSuccessMessage ? (
              <p className="status success workflow-task-upload-success">{context.uploadSuccessMessage}</p>
            ) : null}
            <ResearchUploadPanel
              disabled={context.disabled}
              uploading={context.uploadingResearch}
              onUpload={context.onUploadResearch}
            />
          </>
        ) : null}
        {context.request.research_documents.length > 0 ? (
          <div className="modal-section-panel workflow-task-guidance">
            <p>
              {context.request.research_documents.length} research document
              {context.request.research_documents.length === 1 ? "" : "s"} on file. View them in Research Documents on
              the right.
            </p>
          </div>
        ) : null}
      </>
    ),
  },
  [TASK_KEY_SEND_RESEARCH_COMMUNICATION]: {
    showGuidanceWhenReadOnly: true,
    render: (context) =>
      !context.disabled ? (
        <SendResearchCommunicationTaskPanel
          requestId={context.request.id}
          communications={context.request.request_communications}
          disabled={context.isDone}
          onChanged={context.onChanged}
          onError={context.onError}
        />
      ) : null,
  },
  [TASK_KEY_FOLLOW_UP_RESEARCH]: {
    showGuidanceWhenReadOnly: true,
    render: (context) =>
      !context.disabled && context.activeWorkflow ? (
        <FollowUpResearchTaskPanel
          requestId={context.request.id}
          task={context.task}
          workflow={context.activeWorkflow}
          disabled={context.isDone}
          onChanged={context.onChanged}
          onError={context.onError}
        />
      ) : null,
  },
  [TASK_KEY_CLIENT_RESPONSE]: {
    usesCustomSave: true,
    showGuidanceWhenReadOnly: true,
    render: (context) =>
      !context.isDone && !context.disabled && context.activeWorkflow ? (
        <RecordClientResponseTaskPanel
          requestId={context.request.id}
          proposedCruises={context.request.proposed_cruises}
          workflow={context.activeWorkflow}
          disabled={context.disabled}
          onChanged={context.onChanged}
          onError={context.onError}
          onCloseRequest={context.onCloseRequest}
          onSaved={context.onSaved}
        />
      ) : null,
  },
  [TASK_KEY_ACCEPT_MASTER_TERMS]: {
    showGuidanceWhenReadOnly: true,
    render: (context) => (
      <MasterTermsTaskPanel
        requestId={context.request.id}
        disabled={context.disabled}
        isDone={context.isDone}
        onChanged={context.onChanged}
        onError={context.onError}
      />
    ),
  },
  [TASK_KEY_VERIFY_PASSENGER_DETAILS]: {
    usesCustomSave: true,
    render: (context) => (
      <VerifyPassengerDetailsTaskPanel
        requestId={context.request.id}
        passengers={context.request.request_passengers}
        taskId={context.task.id}
        disabled={context.disabled}
        isDone={context.isDone}
        onChanged={context.onChanged}
        onError={context.onError}
        onSaved={context.onSaved}
      />
    ),
  },
  [TASK_KEY_CREATE_CABIN_HOLDS]: {
    usesCustomSave: true,
    render: (context) => (
      <CreateCabinHoldsTaskPanel
        requestId={context.request.id}
        cabinsNeeded={context.request.cabins_needed}
        bookingCruises={context.bookingCruises}
        taskId={context.task.id}
        disabled={context.disabled}
        isDone={context.isDone}
        onChanged={context.onChanged}
        onError={context.onError}
        onSaved={context.onSaved}
      />
    ),
  },
  [TASK_KEY_COLLECT_PAYMENT_AND_SEND_BOOKING]: {
    usesCustomSave: true,
    render: (context) => (
      <CollectPaymentAndBookingCommunicationTaskPanel
        requestId={context.request.id}
        cabinsNeeded={context.request.cabins_needed}
        bookingCruises={context.bookingCruises}
        task={context.task}
        disabled={context.disabled}
        isDone={context.isDone}
        onChanged={context.onChanged}
        onError={context.onError}
        onSaved={context.onSaved}
      />
    ),
  },
  [TASK_KEY_COLLECT_PASSENGER_ADDRESSES]: registerCollectPassengerAddresses(),
  [LEGACY_TASK_KEY_COLLECT_LEAD_PASSENGER_ADDRESSES]: registerCollectPassengerAddresses(),
  [TASK_KEY_CREATE_TRIP_IN_CRM]: {
    usesCustomSave: true,
    render: (context) => (
      <CreateTripInCrmTaskPanel
        requestId={context.request.id}
        request={context.request}
        form={context.form}
        task={context.task}
        disabled={context.disabled}
        isDone={context.isDone}
        onChanged={context.onChanged}
        onError={context.onError}
        onSaved={context.onSaved}
      />
    ),
  },
  [TASK_KEY_CREATE_PROPOSED_CRUISES]: {
    render: (context) => (
      <>
        {!context.isDone && !context.disabled ? (
          <ProposedCruisesTaskPanel
            requestId={context.request.id}
            researchDocuments={context.request.research_documents}
            disabled={context.disabled}
            onChanged={context.onChanged}
            onError={context.onError}
          />
        ) : null}
        {context.request.proposed_cruises.length > 0 ? (
          <div className="modal-section-panel workflow-task-guidance">
            <p>
              {context.request.proposed_cruises.length} proposed cruise
              {context.request.proposed_cruises.length === 1 ? "" : "s"} on the request.
            </p>
          </div>
        ) : null}
      </>
    ),
  },
  [TASK_KEY_DRAFT_RESEARCH_COMMUNICATION]: {
    render: (context) => (
      <>
        {!context.isDone && !context.disabled ? (
          <DraftResearchCommunicationTaskPanel
            requestId={context.request.id}
            requestWorkflowId={context.activeWorkflow?.id ?? null}
            proposedCruises={context.request.proposed_cruises}
            disabled={context.disabled}
            onChanged={context.onChanged}
            onError={context.onError}
          />
        ) : null}
        {context.request.request_communications.length > 0 ? (
          <p className="meta workflow-task-context">
            {context.request.request_communications.length} communication
            {context.request.request_communications.length === 1 ? "" : "s"} saved so far.
          </p>
        ) : null}
      </>
    ),
  },
};

export function getWorkflowTaskPanelDefinition(task: RequestTask): WorkflowTaskPanelDefinition | null {
  if (isManualCheckTask(task)) {
    return null;
  }
  if (WORKFLOW_TASK_PANEL_REGISTRY[task.task_key]) {
    return WORKFLOW_TASK_PANEL_REGISTRY[task.task_key];
  }
  if (isCollectPassengerAddressesTask(task.task_key)) {
    return registerCollectPassengerAddresses();
  }
  return null;
}

export function taskUsesCustomSave(task: RequestTask): boolean {
  return getWorkflowTaskPanelDefinition(task)?.usesCustomSave ?? false;
}
