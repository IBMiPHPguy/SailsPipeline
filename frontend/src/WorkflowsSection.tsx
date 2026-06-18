import { FormEvent, useEffect, useState } from "react";
import { fetchWorkflowTemplates, startWorkflow, updateTask, updateWorkflow, uploadResearchDocument } from "./api";
import CloseRequestModal from "./CloseRequestModal";
import WorkflowTaskModal from "./WorkflowTaskModal";
import type { RequestTask, RequestWorkflow, TravelRequestDetail, TravelRequestInput, WorkflowTemplate } from "./types";
import { formatTimestamp } from "./utils";
import {
  TASK_KEY_FOLLOW_UP_RESEARCH,
  TASK_STATUS_DONE,
  TASK_STATUS_OPEN,
  WORKFLOW_STATUS_ACTIVE,
  WORKFLOW_STATUS_CANCELLED,
  WORKFLOW_STATUS_COMPLETED,
  WORKFLOW_TYPE_ENTER_TRIP_CRM,
} from "./formOptions";
import {
  countOpenTasks,
  getActiveWorkflow,
  getFollowUpDueLabel,
  getTaskBlockedReason,
  getTaskDisplayStatus,
  getTaskRowMeta,
  isFollowUpTaskLate,
  isTaskBlockedByPrerequisites,
  taskDisplayStatusClass,
  taskStatusClass,
  workflowTypeLabel,
} from "./workflowForm";

type WorkflowTab = "active" | "previous";

type WorkflowsSectionProps = {
  requestId: number;
  request: TravelRequestDetail;
  form: TravelRequestInput;
  workflows: RequestWorkflow[];
  disabled: boolean;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
  onCloseRequest: (closeReason: string) => Promise<void>;
};

function ChevronIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="m9 18 6-6-6-6" />
    </svg>
  );
}

export default function WorkflowsSection({
  requestId,
  request,
  form,
  workflows,
  disabled,
  onChanged,
  onError,
  onCloseRequest,
}: WorkflowsSectionProps) {
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [selectedType, setSelectedType] = useState("");
  const [starting, setStarting] = useState(false);
  const [updatingWorkflowId, setUpdatingWorkflowId] = useState<number | null>(null);
  const [savingTask, setSavingTask] = useState(false);
  const [uploadingResearch, setUploadingResearch] = useState(false);
  const [uploadSuccessMessage, setUploadSuccessMessage] = useState<string | null>(null);
  const [activeTask, setActiveTask] = useState<RequestTask | null>(null);
  const [activeTab, setActiveTab] = useState<WorkflowTab>("active");
  const [completeWorkflowModalOpen, setCompleteWorkflowModalOpen] = useState(false);

  const activeWorkflow = getActiveWorkflow(workflows);
  const pastWorkflows = workflows
    .filter((workflow) => workflow.status !== WORKFLOW_STATUS_ACTIVE)
    .sort((left, right) => {
      const leftTime = left.completed_at ?? left.updated_at;
      const rightTime = right.completed_at ?? right.updated_at;
      return rightTime.localeCompare(leftTime);
    });
  const selectedTemplate = templates.find((template) => template.workflow_type === selectedType);

  const sortedTasks = activeWorkflow
    ? [...activeWorkflow.tasks].sort((left, right) => left.sort_order - right.sort_order)
    : [];

  useEffect(() => {
    fetchWorkflowTemplates()
      .then(setTemplates)
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!activeTask || !activeWorkflow) {
      return;
    }
    const refreshedTask = activeWorkflow.tasks.find((task) => task.id === activeTask.id);
    if (refreshedTask) {
      setActiveTask(refreshedTask);
    }
  }, [activeWorkflow, activeTask?.id]);

  async function handleStartWorkflow(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedType || disabled || activeWorkflow) {
      return;
    }

    setStarting(true);
    onError("");
    try {
      const workflow = await startWorkflow(requestId, selectedType);
      await onChanged();
      setSelectedType("");
      const firstTask = [...workflow.tasks].sort((left, right) => left.sort_order - right.sort_order)[0];
      if (firstTask) {
        setActiveTask(firstTask);
      }
    } catch (startError) {
      onError(startError instanceof Error ? startError.message : "Unable to start workflow.");
    } finally {
      setStarting(false);
    }
  }

  async function handleWorkflowStatus(workflowId: number, status: string, closeReason?: string) {
    setUpdatingWorkflowId(workflowId);
    onError("");
    try {
      await updateWorkflow(
        requestId,
        workflowId,
        closeReason ? { status, close_reason: closeReason } : { status },
      );
      setActiveTask(null);
      setCompleteWorkflowModalOpen(false);
      await onChanged();
    } catch (updateError) {
      onError(updateError instanceof Error ? updateError.message : "Unable to update workflow.");
    } finally {
      setUpdatingWorkflowId(null);
    }
  }

  function handleCompleteWorkflowClick() {
    if (!activeWorkflow || disabled) {
      return;
    }

    if (activeWorkflow.workflow_type === WORKFLOW_TYPE_ENTER_TRIP_CRM) {
      setCompleteWorkflowModalOpen(true);
      return;
    }

    void handleWorkflowStatus(activeWorkflow.id, WORKFLOW_STATUS_COMPLETED);
  }

  async function handleConfirmCompleteEnterTripCrm(closeReason: string) {
    if (!activeWorkflow) {
      return;
    }

    await handleWorkflowStatus(activeWorkflow.id, WORKFLOW_STATUS_COMPLETED, closeReason);
  }

  async function handleTaskStatus(taskId: number, status: string) {
    setSavingTask(true);
    onError("");
    try {
      await updateTask(requestId, taskId, { status });
      await onChanged();
      if (status === TASK_STATUS_DONE) {
        setActiveTask(null);
      }
    } catch (updateError) {
      onError(updateError instanceof Error ? updateError.message : "Unable to update task.");
    } finally {
      setSavingTask(false);
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
      setUploadSuccessMessage(`${file.name} uploaded successfully.`);
      await onChanged();
    } catch (uploadError) {
      setUploadSuccessMessage(null);
      onError(uploadError instanceof Error ? uploadError.message : "Unable to upload research document.");
    } finally {
      setUploadingResearch(false);
    }
  }

  function closeTaskModal() {
    setActiveTask(null);
    setUploadSuccessMessage(null);
  }

  return (
    <>
      <section className="section-card section-tabs-card workflows-card">
        <div className="section-tablist" role="tablist" aria-label="Workflows">
          <button
            type="button"
            role="tab"
            id="workflows-tab-active"
            aria-selected={activeTab === "active"}
            aria-controls="workflows-panel-active"
            className={`section-tab${activeTab === "active" ? " is-active" : ""}`}
            onClick={() => setActiveTab("active")}
          >
            Active workflow
          </button>
          <button
            type="button"
            role="tab"
            id="workflows-tab-previous"
            aria-selected={activeTab === "previous"}
            aria-controls="workflows-panel-previous"
            className={`section-tab${activeTab === "previous" ? " is-active" : ""}`}
            onClick={() => setActiveTab("previous")}
          >
            Previous workflows ({pastWorkflows.length})
          </button>
        </div>

        <div className="section-card-body section-tab-body">
          {activeTab === "active" ? (
            <div role="tabpanel" id="workflows-panel-active" aria-labelledby="workflows-tab-active">
              {activeWorkflow ? (
                <div className="workflow-active">
                  <div className="workflow-active-header">
                    <div>
                      <p className="workflow-active-type">{workflowTypeLabel(activeWorkflow.workflow_type)}</p>
                      <p className="meta">
                        Started by {activeWorkflow.started_by.username} · {formatTimestamp(activeWorkflow.created_at)}
                      </p>
                    </div>
                    <span className="workflow-status workflow-status-active">{activeWorkflow.status}</span>
                  </div>

                  <p className="workflow-task-summary meta">
                    {countOpenTasks(activeWorkflow)} open task
                    {countOpenTasks(activeWorkflow) === 1 ? "" : "s"} · Click a task to open it
                  </p>

                  <ul className="workflow-task-list">
                    {sortedTasks.map((task) => {
                      const isDone = task.status === TASK_STATUS_DONE;
                      const isBlocked =
                        activeWorkflow !== null && isTaskBlockedByPrerequisites(activeWorkflow, task);
                      const blockedReason =
                        activeWorkflow !== null ? getTaskBlockedReason(activeWorkflow, task) : null;
                      const followUpMeta =
                        activeWorkflow !== null ? getTaskRowMeta(task, activeWorkflow) : null;
                      const followUpDueLabel =
                        task.task_key === TASK_KEY_FOLLOW_UP_RESEARCH &&
                        task.status === TASK_STATUS_OPEN &&
                        activeWorkflow !== null
                          ? getFollowUpDueLabel(task, activeWorkflow)
                          : null;
                      const followUpLate =
                        activeWorkflow !== null && isFollowUpTaskLate(task, activeWorkflow);
                      const displayStatus =
                        activeWorkflow !== null ? getTaskDisplayStatus(task, activeWorkflow) : task.status;
                      const displayStatusClass =
                        activeWorkflow !== null ? taskDisplayStatusClass(task, activeWorkflow) : taskStatusClass(task.status);
                      return (
                        <li key={task.id}>
                          <button
                            type="button"
                            className={`workflow-task-row ${displayStatusClass}${
                              activeTask?.id === task.id ? " is-selected" : ""
                            }${isBlocked ? " is-blocked" : ""}${displayStatus === "Late" ? " is-late" : ""}`}
                            disabled={isBlocked}
                            title={blockedReason ?? undefined}
                            onClick={() => {
                              if (isBlocked) {
                                return;
                              }
                              setUploadSuccessMessage(null);
                              setActiveTask(task);
                            }}
                          >
                            <span className="workflow-task-row-main">
                              <span className="workflow-task-row-title">{task.title}</span>
                              {isBlocked && blockedReason ? (
                                <span className="workflow-task-row-meta meta">{blockedReason}</span>
                              ) : followUpMeta ? (
                                <span className="workflow-task-row-meta meta">{followUpMeta}</span>
                              ) : isDone && task.completed_by ? (
                                <span className="workflow-task-row-meta meta">
                                  {task.completed_by.username}
                                  {task.completed_at ? ` · ${formatTimestamp(task.completed_at)}` : ""}
                                </span>
                              ) : task.description ? (
                                <span className="workflow-task-row-meta meta">{task.description}</span>
                              ) : null}
                            </span>
                            <span className="workflow-task-row-trailing">
                              {followUpDueLabel ? (
                                <span
                                  className={`workflow-task-due${followUpLate ? " workflow-task-due--late" : ""}`}
                                >
                                  {followUpDueLabel}
                                </span>
                              ) : null}
                              <span className={`workflow-task-status ${displayStatusClass}`}>{displayStatus}</span>
                              <ChevronIcon />
                            </span>
                          </button>
                        </li>
                      );
                    })}
                  </ul>

                  {!disabled ? (
                    <div className="workflow-actions">
                      <button
                        type="button"
                        className="modal-secondary"
                        disabled={updatingWorkflowId === activeWorkflow.id}
                        onClick={() => handleWorkflowStatus(activeWorkflow.id, WORKFLOW_STATUS_CANCELLED)}
                      >
                        {updatingWorkflowId === activeWorkflow.id ? "Updating..." : "Cancel workflow"}
                      </button>
                      <button
                        type="button"
                        disabled={updatingWorkflowId === activeWorkflow.id}
                        onClick={handleCompleteWorkflowClick}
                      >
                        {updatingWorkflowId === activeWorkflow.id ? "Updating..." : "Complete workflow"}
                      </button>
                    </div>
                  ) : null}
                </div>
              ) : !disabled ? (
                <form className="workflow-start-form" onSubmit={handleStartWorkflow}>
                  <label>
                    Start a workflow
                    <select
                      value={selectedType}
                      disabled={starting || templates.length === 0}
                      onChange={(event) => setSelectedType(event.target.value)}
                    >
                      <option value="">--- Select ---</option>
                      {templates.map((template) => (
                        <option key={template.workflow_type} value={template.workflow_type}>
                          {template.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  {selectedTemplate?.description ? (
                    <p className="field-hint">{selectedTemplate.description}</p>
                  ) : null}
                  <p className="field-hint">Starting a workflow creates a set of tasks for your team to complete.</p>
                  <button type="submit" disabled={starting || !selectedType}>
                    {starting ? "Creating tasks..." : "Start workflow"}
                  </button>
                </form>
              ) : (
                <p className="meta">No active workflow.</p>
              )}
            </div>
          ) : (
            <div role="tabpanel" id="workflows-panel-previous" aria-labelledby="workflows-tab-previous">
              {pastWorkflows.length === 0 ? (
                <p className="meta">No previous workflows yet.</p>
              ) : (
                <div className="workflow-history-table-wrap">
                  <table className="workflow-history-table">
                    <thead>
                      <tr>
                        <th scope="col">Workflow</th>
                        <th scope="col">Status</th>
                        <th scope="col">Started by</th>
                        <th scope="col">Started</th>
                        <th scope="col">Ended by</th>
                        <th scope="col">Ended</th>
                      </tr>
                    </thead>
                    <tbody>
                      {pastWorkflows.map((workflow) => (
                        <tr key={workflow.id}>
                          <td>{workflowTypeLabel(workflow.workflow_type)}</td>
                          <td>
                            <span
                              className={`workflow-status ${
                                workflow.status === WORKFLOW_STATUS_COMPLETED
                                  ? "workflow-status-completed"
                                  : "workflow-status-cancelled"
                              }`}
                            >
                              {workflow.status}
                            </span>
                          </td>
                          <td className="meta">{workflow.started_by.username}</td>
                          <td className="meta">{formatTimestamp(workflow.created_at)}</td>
                          <td className="meta">{workflow.completed_by?.username ?? "—"}</td>
                          <td className="meta">
                            {workflow.completed_at ? formatTimestamp(workflow.completed_at) : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      </section>

      <CloseRequestModal
        open={completeWorkflowModalOpen}
        request={request}
        closing={updatingWorkflowId !== null}
        mode="complete_enter_trip_crm"
        onCancel={() => setCompleteWorkflowModalOpen(false)}
        onConfirm={(closeReason) => void handleConfirmCompleteEnterTripCrm(closeReason)}
      />

      <WorkflowTaskModal
        open={activeTask !== null}
        task={activeTask}
        disabled={disabled}
        saving={savingTask}
        uploadingResearch={uploadingResearch}
        uploadSuccessMessage={uploadSuccessMessage}
        request={request}
        form={form}
        onClose={closeTaskModal}
        onMarkDone={() => (activeTask ? handleTaskStatus(activeTask.id, TASK_STATUS_DONE) : Promise.resolve())}
        onReopen={() => (activeTask ? handleTaskStatus(activeTask.id, TASK_STATUS_OPEN) : Promise.resolve())}
        onUploadResearch={handleResearchUpload}
        onChanged={onChanged}
        onError={onError}
        onCloseRequest={onCloseRequest}
      />
    </>
  );
}
