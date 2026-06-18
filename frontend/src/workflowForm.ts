import {
  COMMUNICATION_STATUS_ARCHIVED,
  COMMUNICATION_STATUS_DRAFT,
  COMMUNICATION_STATUS_SENT,
  COMMUNICATION_TYPE_AGENCY,
  COMMUNICATION_TYPE_BOOKING,
  COMMUNICATION_TYPE_RESEARCH_FINDINGS,
  COMMUNICATION_TYPE_RESEARCH_FOLLOW_UP,
  COMMUNICATION_TYPE_RESEARCH_PROPOSAL,
  FOLLOW_UP_DUE_DAYS,
  TASK_DISPLAY_STATUS_LATE,
  TASK_KEY_CLIENT_RESPONSE,
  TASK_KEY_FOLLOW_UP_RESEARCH,
  TASK_KEY_SEND_RESEARCH_COMMUNICATION,
  TASK_STATUS_DONE,
  TASK_STATUS_OPEN,
  WORKFLOW_STATUS_ACTIVE,
  WORKFLOW_STATUS_CANCELLED,
  WORKFLOW_STATUS_COMPLETED,
  WORKFLOW_TYPE_COMMUNICATE_RESEARCH,
  WORKFLOW_TYPE_ENTER_TRIP_CRM,
  WORKFLOW_TYPE_RESEARCH,
} from "./formOptions";
import type { RequestCommunication, RequestCommunicationInput, RequestTask, RequestWorkflow } from "./types";
import { formatTimestamp } from "./utils";

const COMMUNICATE_RESEARCH_PREREQUISITE_KEYS: Record<string, string[]> = {
  [TASK_KEY_FOLLOW_UP_RESEARCH]: [TASK_KEY_SEND_RESEARCH_COMMUNICATION],
  [TASK_KEY_CLIENT_RESPONSE]: [TASK_KEY_SEND_RESEARCH_COMMUNICATION],
};

export function workflowTypeLabel(workflowType: string): string {
  if (workflowType === WORKFLOW_TYPE_RESEARCH) {
    return "Research";
  }
  if (workflowType === WORKFLOW_TYPE_COMMUNICATE_RESEARCH) {
    return "Communicate Research";
  }
  if (workflowType === WORKFLOW_TYPE_ENTER_TRIP_CRM) {
    return "Enter Trip in CRM";
  }
  return workflowType;
}

export function communicationTypeLabel(type: string): string {
  if (type === COMMUNICATION_TYPE_RESEARCH_FINDINGS) {
    return "Research findings";
  }
  if (type === COMMUNICATION_TYPE_RESEARCH_PROPOSAL) {
    return "Cruise proposal";
  }
  if (type === COMMUNICATION_TYPE_RESEARCH_FOLLOW_UP) {
    return "Research follow-up";
  }
  if (type === COMMUNICATION_TYPE_BOOKING) {
    return "Booking confirmation";
  }
  if (type === COMMUNICATION_TYPE_AGENCY) {
    return "Agency follow-up";
  }
  return type;
}

export function communicationStatusClass(status: string): string {
  if (status === COMMUNICATION_STATUS_SENT) {
    return "communication-status-sent";
  }
  if (status === COMMUNICATION_STATUS_ARCHIVED) {
    return "communication-status-archived";
  }
  return "communication-status-draft";
}

export function taskStatusClass(status: string): string {
  return status === TASK_STATUS_DONE ? "task-status-done" : "task-status-open";
}

export function getActiveWorkflow(workflows: RequestWorkflow[]): RequestWorkflow | null {
  return workflows.find((workflow) => workflow.status === WORKFLOW_STATUS_ACTIVE) ?? null;
}

export function countOpenTasks(workflow: RequestWorkflow): number {
  return workflow.tasks.filter((task) => task.status === TASK_STATUS_OPEN).length;
}

export function sortedWorkflowTasks(workflow: RequestWorkflow): RequestTask[] {
  return [...workflow.tasks].sort((left, right) => left.sort_order - right.sort_order);
}

function getWorkflowTaskByKey(workflow: RequestWorkflow, taskKey: string): RequestTask | null {
  return workflow.tasks.find((task) => task.task_key === taskKey) ?? null;
}

export function isClientResponseRecorded(workflow: RequestWorkflow): boolean {
  return getWorkflowTaskByKey(workflow, TASK_KEY_CLIENT_RESPONSE)?.status === TASK_STATUS_DONE;
}

export function isFollowUpTaskLate(task: RequestTask, workflow: RequestWorkflow): boolean {
  if (task.task_key !== TASK_KEY_FOLLOW_UP_RESEARCH) {
    return false;
  }
  if (task.status !== TASK_STATUS_OPEN) {
    return false;
  }
  if (isClientResponseRecorded(workflow)) {
    return false;
  }

  const dueAt = getFollowUpDueAt(task, workflow);
  if (!dueAt) {
    return false;
  }

  return dueAt.getTime() < Date.now();
}

export function getTaskDisplayStatus(task: RequestTask, workflow: RequestWorkflow): string {
  if (isFollowUpTaskLate(task, workflow)) {
    return TASK_DISPLAY_STATUS_LATE;
  }
  return task.status;
}

export function taskDisplayStatusClass(task: RequestTask, workflow: RequestWorkflow): string {
  if (isFollowUpTaskLate(task, workflow)) {
    return "task-status-late";
  }
  return taskStatusClass(task.status);
}

export function isTaskBlockedByPrerequisites(workflow: RequestWorkflow, task: RequestTask): boolean {
  if (workflow.workflow_type !== WORKFLOW_TYPE_COMMUNICATE_RESEARCH) {
    return false;
  }

  const requiredTaskKeys = COMMUNICATE_RESEARCH_PREREQUISITE_KEYS[task.task_key];
  if (!requiredTaskKeys?.length) {
    return false;
  }

  return requiredTaskKeys.some((taskKey) => {
    const prerequisite = getWorkflowTaskByKey(workflow, taskKey);
    return prerequisite?.status !== TASK_STATUS_DONE;
  });
}

export function getTaskBlockedReason(workflow: RequestWorkflow, task: RequestTask): string | null {
  if (!isTaskBlockedByPrerequisites(workflow, task)) {
    return null;
  }

  const requiredTaskKeys = COMMUNICATE_RESEARCH_PREREQUISITE_KEYS[task.task_key] ?? [];
  const blockingTaskKey = requiredTaskKeys.find((taskKey) => {
    const prerequisite = getWorkflowTaskByKey(workflow, taskKey);
    return prerequisite?.status !== TASK_STATUS_DONE;
  });
  if (!blockingTaskKey) {
    return "Complete the required task first.";
  }

  const blockingTask = getWorkflowTaskByKey(workflow, blockingTaskKey);
  if (!blockingTask) {
    return "Complete the required task first.";
  }

  return `Complete "${blockingTask.title}" before working on this task.`;
}

export function getFollowUpLastReachedOutAt(task: RequestTask): string | null {
  const lastReachedOut = task.result?.last_reached_out_at;
  return typeof lastReachedOut === "string" ? lastReachedOut : null;
}

export function getFollowUpDueAt(task: RequestTask, workflow: RequestWorkflow): Date | null {
  if (task.task_key !== TASK_KEY_FOLLOW_UP_RESEARCH) {
    return null;
  }

  if (task.due_at) {
    return new Date(task.due_at);
  }

  const sendTask = getWorkflowTaskByKey(workflow, TASK_KEY_SEND_RESEARCH_COMMUNICATION);
  if (sendTask?.status !== TASK_STATUS_DONE || !sendTask.completed_at) {
    return null;
  }

  const dueAt = new Date(sendTask.completed_at);
  dueAt.setDate(dueAt.getDate() + FOLLOW_UP_DUE_DAYS);
  return dueAt;
}

export function getFollowUpDueLabel(task: RequestTask, workflow: RequestWorkflow): string | null {
  if (task.status !== TASK_STATUS_OPEN) {
    return null;
  }

  const dueAt = getFollowUpDueAt(task, workflow);
  if (!dueAt) {
    return null;
  }

  const late = isFollowUpTaskLate(task, workflow);
  return `${late ? "Overdue" : "Due"} ${formatTimestamp(dueAt.toISOString())}`;
}

export function getTaskRowMeta(task: RequestTask, workflow: RequestWorkflow): string | null {
  if (task.task_key !== TASK_KEY_FOLLOW_UP_RESEARCH || task.status !== TASK_STATUS_OPEN) {
    return null;
  }

  const parts: string[] = [];
  const lastReachedOutAt = getFollowUpLastReachedOutAt(task);
  if (lastReachedOutAt) {
    parts.push(`Reached out ${formatTimestamp(lastReachedOutAt)}`);
  }

  const dueLabel = getFollowUpDueLabel(task, workflow);
  if (dueLabel) {
    parts.push(dueLabel);
  }

  return parts.length > 0 ? parts.join(" · ") : null;
}

export const emptyCommunicationForm: RequestCommunicationInput = {
  communication_type: COMMUNICATION_TYPE_RESEARCH_FINDINGS,
  subject: "",
  body: "",
  status: COMMUNICATION_STATUS_DRAFT,
};

export function communicationToForm(communication: RequestCommunication): RequestCommunicationInput {
  return {
    communication_type: communication.communication_type,
    subject: communication.subject,
    body: communication.body,
    request_workflow_id: communication.request_workflow_id,
    status: communication.status,
  };
}

export function getTaskWorkspaceHint(taskKey: string): string | null {
  switch (taskKey) {
    case "draft_research_communication":
      return "Generate a cruise proposal email below. It is saved automatically in Communications, then mark this task done.";
    case "send_research_communication":
      return "Select the cruise proposal communication below, copy the subject and body to send to the client, then mark this task done.";
    case "follow_up_research":
      return `Follow up with the client if they have not responded within ${FOLLOW_UP_DUE_DAYS} days of sending the proposal. Mark as reached out to extend the due date another ${FOLLOW_UP_DUE_DAYS} days without closing the task.`;
    case "client_response":
      return "Record whether each proposed cruise was accepted or rejected. This task can be completed anytime after the proposal is sent, even if follow-up is still open.";
    case "verify_passenger_details":
      return "Review each passenger's name, date of birth, and contact information below. Email and phone are required for the primary passenger only. Save to update passenger records and complete this task.";
    case "collect_passenger_addresses":
    case "collect_lead_passenger_addresses":
      return "Enter the primary passenger's home address below. Other passenger addresses are optional, and you can copy the primary address to another passenger when it matches.";
    case "create_cabin_holds":
      return "Enter cruise line reservation IDs for each cabin based on the request's max cabins needed. Add multiple IDs per cabin when needed.";
    case "collect_payment_and_send_booking_communication":
      return "Collect deposit or final payment for each reservation ID, send cruise line booking communications, then mark payment collected for every reservation.";
    case "create_trip_in_crm":
      return "Use the CRM entry summary below while you work in your agency CRM. Check off each step as you complete it, then mark this task done.";
    default:
      return null;
  }
}

export {
  COMMUNICATION_STATUS_ARCHIVED,
  COMMUNICATION_STATUS_DRAFT,
  COMMUNICATION_STATUS_SENT,
  TASK_STATUS_DONE,
  TASK_STATUS_OPEN,
  WORKFLOW_STATUS_ACTIVE,
  WORKFLOW_STATUS_CANCELLED,
  WORKFLOW_STATUS_COMPLETED,
};
