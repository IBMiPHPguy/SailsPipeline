const WORKFLOW_PILL_CLASSES = [
  "next-task-badge-research",
  "next-task-badge-upload",
  "next-task-badge-proposals",
  "next-task-badge-draft",
  "next-task-badge-send",
  "next-task-badge-follow-up",
  "next-task-badge-client-response",
  "next-task-badge-addresses",
  "next-task-badge-cabin-holds",
  "next-task-badge-payment",
  "next-task-badge-crm",
] as const;

function hashString(value: string): number {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) >>> 0;
  }
  return hash;
}

/** Stable pill color per workflow, using the same palette as open-request task badges. */
export function getWorkflowPillClass(workflowTemplateId: string): string {
  const index = hashString(workflowTemplateId) % WORKFLOW_PILL_CLASSES.length;
  return WORKFLOW_PILL_CLASSES[index] ?? "next-task-badge-default";
}
