import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { transferAgencyTaskToWorkflow } from "./api";
import type { AgencyTaskTemplate, AgencyWorkflowTemplate } from "./types";

type MoveStep = "destination" | "position";

/** null means append at end of the destination sequence. */
type InsertPosition = number | null;

type WorkflowTaskMoveModalProps = {
  open: boolean;
  task: AgencyTaskTemplate | null;
  sourceWorkflow: AgencyWorkflowTemplate | null;
  workflows: AgencyWorkflowTemplate[];
  onClose: () => void;
  onMoved: () => void | Promise<void>;
};

export default function WorkflowTaskMoveModal({
  open,
  task,
  sourceWorkflow,
  workflows,
  onClose,
  onMoved,
}: WorkflowTaskMoveModalProps) {
  const [step, setStep] = useState<MoveStep>("destination");
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null);
  const [insertPosition, setInsertPosition] = useState<InsertPosition>(null);
  const [moving, setMoving] = useState(false);
  const [error, setError] = useState("");

  const destinationWorkflows = useMemo(
    () => workflows.filter((workflow) => workflow.id !== sourceWorkflow?.id),
    [sourceWorkflow?.id, workflows],
  );

  const selectedWorkflow = useMemo(
    () => destinationWorkflows.find((workflow) => workflow.id === selectedWorkflowId) ?? null,
    [destinationWorkflows, selectedWorkflowId],
  );

  const targetTasks = useMemo(
    () =>
      selectedWorkflow
        ? [...selectedWorkflow.task_templates].sort((left, right) => left.sequence_order - right.sequence_order)
        : [],
    [selectedWorkflow],
  );

  useEffect(() => {
    if (!open) {
      setStep("destination");
      setSelectedWorkflowId(null);
      setInsertPosition(null);
      setMoving(false);
      setError("");
      return;
    }
    setSelectedWorkflowId(destinationWorkflows[0]?.id ?? null);
  }, [destinationWorkflows, open]);

  useEffect(() => {
    if (step === "position") {
      const taskCount = selectedWorkflow?.task_templates.length ?? 0;
      setInsertPosition(taskCount === 0 ? 1 : null);
      setError("");
    }
  }, [selectedWorkflow, selectedWorkflowId, step]);

  if (!open || !task || !sourceWorkflow) {
    return null;
  }

  function handleClose() {
    if (moving) {
      return;
    }
    onClose();
  }

  function handleNext() {
    if (!selectedWorkflowId) {
      return;
    }
    setError("");
    setStep("position");
  }

  function handleBack() {
    if (moving) {
      return;
    }
    setError("");
    setStep("destination");
  }

  async function handleMove() {
    if (!selectedWorkflowId) {
      return;
    }

    setMoving(true);
    setError("");
    try {
      await transferAgencyTaskToWorkflow(
        task.id,
        selectedWorkflowId,
        insertPosition === null ? null : insertPosition,
      );
      await onMoved();
      onClose();
    } catch (moveError) {
      setError(moveError instanceof Error ? moveError.message : "Unable to move task.");
    } finally {
      setMoving(false);
    }
  }

  const title = step === "destination" ? "Move task to workflow" : "Choose position in sequence";

  return createPortal(
    <div className="modal-backdrop modal-backdrop-scroll" role="presentation" onClick={handleClose}>
      <div
        className="modal-card modal-card-wide workflow-task-move-modal"
        role="dialog"
        aria-labelledby="workflow-task-move-title"
        aria-modal="true"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="modal-card-header">
          <h3 id="workflow-task-move-title">{title}</h3>
        </header>

        <div className="modal-scroll-body workflow-task-move-body">
          <div className="modal-meta-row">
            <span>{task.task_title}</span>
            <span className="modal-meta-separator" aria-hidden="true">
              |
            </span>
            <span>From {sourceWorkflow.workflow_name}</span>
            {step === "position" && selectedWorkflow ? (
              <>
                <span className="modal-meta-separator" aria-hidden="true">
                  |
                </span>
                <span>To {selectedWorkflow.workflow_name}</span>
              </>
            ) : null}
          </div>

          {step === "destination" ? (
            destinationWorkflows.length === 0 ? (
              <p className="meta workflow-task-move-empty">Create another workflow to move tasks between sequences.</p>
            ) : (
              <fieldset className="workflow-task-move-fieldset">
                <legend className="workflow-task-move-legend">Choose destination workflow</legend>
                <ul className="workflow-task-move-list">
                  {destinationWorkflows.map((workflow) => (
                    <li key={workflow.id} className="modal-section-panel workflow-task-move-option">
                      <label className="workflow-task-move-option-label">
                        <input
                          type="radio"
                          name="workflow-task-move-target"
                          value={workflow.id}
                          checked={selectedWorkflowId === workflow.id}
                          disabled={moving}
                          onChange={() => setSelectedWorkflowId(workflow.id)}
                        />
                        <span className="workflow-task-move-option-text">
                          <span className="workflow-task-move-option-name">{workflow.workflow_name}</span>
                          <span className="meta workflow-task-move-option-meta">
                            {workflow.task_templates.length === 1
                              ? "1 task"
                              : `${workflow.task_templates.length} tasks`}
                            {workflow.workflow_type_key ? " · Recommended" : ""}
                          </span>
                        </span>
                      </label>
                    </li>
                  ))}
                </ul>
              </fieldset>
            )
          ) : (
            <fieldset className="workflow-task-move-fieldset">
              <legend className="workflow-task-move-legend">Insert task at</legend>
              <ul className="workflow-task-move-list">
                {targetTasks.length === 0 ? (
                  <li className="modal-section-panel workflow-task-move-option">
                    <label className="workflow-task-move-option-label">
                      <input
                        type="radio"
                        name="workflow-task-move-position"
                        checked={insertPosition === 1}
                        disabled={moving}
                        onChange={() => setInsertPosition(1)}
                      />
                      <span className="workflow-task-move-option-text">
                        <span className="workflow-task-move-option-name">As the first task</span>
                      </span>
                    </label>
                  </li>
                ) : (
                  <>
                    {targetTasks.map((targetTask, index) => (
                      <li key={targetTask.id} className="modal-section-panel workflow-task-move-option">
                        <label className="workflow-task-move-option-label">
                          <input
                            type="radio"
                            name="workflow-task-move-position"
                            checked={insertPosition === index + 1}
                            disabled={moving}
                            onChange={() => setInsertPosition(index + 1)}
                          />
                          <span className="workflow-task-move-option-text">
                            <span className="workflow-task-move-option-name">
                              Before step {index + 1}: {targetTask.task_title}
                            </span>
                          </span>
                        </label>
                      </li>
                    ))}
                    <li className="modal-section-panel workflow-task-move-option">
                      <label className="workflow-task-move-option-label">
                        <input
                          type="radio"
                          name="workflow-task-move-position"
                          checked={insertPosition === null}
                          disabled={moving}
                          onChange={() => setInsertPosition(null)}
                        />
                        <span className="workflow-task-move-option-text">
                          <span className="workflow-task-move-option-name">At end of sequence</span>
                          <span className="meta workflow-task-move-option-meta">
                            After step {targetTasks.length}: {targetTasks[targetTasks.length - 1]?.task_title}
                          </span>
                        </span>
                      </label>
                    </li>
                  </>
                )}
              </ul>
            </fieldset>
          )}

          {error ? <p className="status error">{error}</p> : null}
        </div>

        <div className="modal-actions modal-actions-footer">
          {step === "destination" ? (
            <>
              <button type="button" className="modal-secondary" disabled={moving} onClick={handleClose}>
                Cancel
              </button>
              <button
                type="button"
                className="modal-primary"
                disabled={moving || destinationWorkflows.length === 0 || !selectedWorkflowId}
                onClick={handleNext}
              >
                Next
              </button>
            </>
          ) : (
            <>
              <button type="button" className="modal-secondary" disabled={moving} onClick={handleBack}>
                Back
              </button>
              <button type="button" className="modal-primary" disabled={moving} onClick={() => void handleMove()}>
                {moving ? "Moving..." : "Move"}
              </button>
            </>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}
