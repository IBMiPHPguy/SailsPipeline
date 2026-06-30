import { getCrmEntryProposedCruises } from "./crmEntrySummary";
import type { RequestTask, TravelRequestDetail, TravelRequestInput } from "./types";
import { getActiveWorkflow, getTaskDisplayStatus, getTaskWorkspaceHint, taskDisplayStatusClass } from "./workflowForm";
import {
  getWorkflowTaskPanelDefinition,
  taskUsesCustomSave,
  type WorkflowTaskPanelContext,
} from "./workflowTaskPanelRegistry";
import { TASK_STATUS_DONE } from "./formOptions";
import { formatTimestamp } from "./utils";

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
    <div className="modal-section-panel workflow-task-guidance">
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
  const bookingCruises = getCrmEntryProposedCruises(request.proposed_cruises);
  const panelDefinition = getWorkflowTaskPanelDefinition(task);
  const usesCustomSave = taskUsesCustomSave(task) && !isDone && !disabled;
  const displayStatus = activeWorkflow ? getTaskDisplayStatus(task, activeWorkflow) : task.status;
  const displayStatusClass = activeWorkflow
    ? taskDisplayStatusClass(task, activeWorkflow)
    : task.status === TASK_STATUS_DONE
      ? "task-status-done"
      : "task-status-open";

  const panelContext: WorkflowTaskPanelContext = {
    task,
    request,
    form,
    disabled,
    isDone,
    uploadingResearch,
    uploadSuccessMessage,
    activeWorkflow,
    bookingCruises,
    onChanged,
    onError,
    onCloseRequest,
    onUploadResearch,
    onSaved: onClose,
  };

  const showFallbackGuidance =
    workspaceHint &&
    (panelDefinition === null || (panelDefinition.showGuidanceWhenReadOnly && (isDone || disabled)));

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
            <p className="modal-meta-row workflow-task-modal-completed">
              <span>Completed by {task.completed_by.username}</span>
              {task.completed_at ? (
                <>
                  <span className="modal-meta-separator" aria-hidden="true">
                    |
                  </span>
                  <span>{formatTimestamp(task.completed_at)}</span>
                </>
              ) : null}
            </p>
          ) : null}

          {panelDefinition ? panelDefinition.render(panelContext) : null}
          {showFallbackGuidance ? <TaskGuidance taskKey={task.task_key} /> : null}
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
            <button
              type="button"
              className="modal-primary"
              disabled={saving || uploadingResearch}
              onClick={() => void onMarkDone()}
            >
              {saving ? "Saving..." : "Mark task done"}
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
