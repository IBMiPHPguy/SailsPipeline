import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { createAgencyTaskFromCatalog, createAgencyTaskFromCustomDefinition } from "./api";
import WorkflowSequencePositionFieldset, { type InsertPosition } from "./WorkflowSequencePositionFieldset";
import type { AgencyTaskInventoryItem, AgencyWorkflowTemplate } from "./types";
import { getWorkflowPillClass } from "./workflowPill";

type AddStep = "workflow" | "sequence";

type AddTaskToWorkflowModalProps = {
  open: boolean;
  task: AgencyTaskInventoryItem | null;
  workflows: AgencyWorkflowTemplate[];
  onClose: () => void;
  onAdded: () => void | Promise<void>;
};

export default function AddTaskToWorkflowModal({
  open,
  task,
  workflows,
  onClose,
  onAdded,
}: AddTaskToWorkflowModalProps) {
  const [step, setStep] = useState<AddStep>("workflow");
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null);
  const [insertPosition, setInsertPosition] = useState<InsertPosition>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const sortedWorkflows = useMemo(
    () => [...workflows].sort((left, right) => left.workflow_name.localeCompare(right.workflow_name)),
    [workflows],
  );

  const selectedWorkflow = useMemo(
    () => sortedWorkflows.find((workflow) => workflow.id === selectedWorkflowId) ?? null,
    [selectedWorkflowId, sortedWorkflows],
  );

  const workflowTasks = useMemo(
    () =>
      selectedWorkflow
        ? [...selectedWorkflow.task_templates].sort((left, right) => left.sequence_order - right.sequence_order)
        : [],
    [selectedWorkflow],
  );

  useEffect(() => {
    if (!open) {
      setStep("workflow");
      setSelectedWorkflowId(null);
      setInsertPosition(null);
      setSubmitting(false);
      setError("");
    }
  }, [open]);

  useEffect(() => {
    if (step === "sequence") {
      setInsertPosition(workflowTasks.length === 0 ? 1 : null);
      setError("");
    }
  }, [step, workflowTasks.length, selectedWorkflowId]);

  if (!open || !task) {
    return null;
  }

  function handleClose() {
    if (submitting) {
      return;
    }
    onClose();
  }

  function handleChooseWorkflow(workflowId: string) {
    if (submitting) {
      return;
    }
    setSelectedWorkflowId(workflowId);
    setStep("sequence");
    setError("");
  }

  function handleBack() {
    if (submitting) {
      return;
    }
    setStep("workflow");
    setError("");
  }

  async function handleAccept() {
    if (!selectedWorkflowId) {
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      const sequenceOrder = insertPosition === null ? null : insertPosition;
      if (task.task_type === "library") {
        await createAgencyTaskFromCustomDefinition(selectedWorkflowId, task.task_key, sequenceOrder);
      } else {
        await createAgencyTaskFromCatalog(selectedWorkflowId, task.task_key, null, sequenceOrder);
      }
      await onAdded();
      onClose();
    } catch (addError) {
      setError(addError instanceof Error ? addError.message : "Unable to add task to workflow.");
    } finally {
      setSubmitting(false);
    }
  }

  const title =
    step === "workflow" ? "Choose the workflow to add the task to" : "Set position in sequence";

  return createPortal(
    <div className="modal-backdrop modal-backdrop-scroll" role="presentation" onClick={handleClose}>
      <div
        className="modal-card modal-card-wide add-task-to-workflow-modal"
        role="dialog"
        aria-labelledby="add-task-to-workflow-title"
        aria-modal="true"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="modal-card-header">
          <h3 id="add-task-to-workflow-title">{title}</h3>
        </header>

        <div className="modal-scroll-body add-task-to-workflow-body">
          <div className="modal-meta-row">
            <span className="add-task-to-workflow-task-label">Task</span>
            <span className="modal-meta-separator" aria-hidden="true">
              |
            </span>
            <span className="add-task-to-workflow-task-name">{task.task_title}</span>
            {step === "sequence" && selectedWorkflow ? (
              <>
                <span className="modal-meta-separator" aria-hidden="true">
                  |
                </span>
                <span>Workflow: {selectedWorkflow.workflow_name}</span>
              </>
            ) : null}
          </div>

          {error ? <p className="status error">{error}</p> : null}

          {step === "workflow" ? (
            sortedWorkflows.length === 0 ? (
              <p className="meta add-task-to-workflow-empty">Create a workflow before adding tasks.</p>
            ) : (
              <ul className="add-task-to-workflow-cards">
                {sortedWorkflows.map((workflow) => (
                  <li key={workflow.id}>
                    <button
                      type="button"
                      className={`add-task-to-workflow-card ${getWorkflowPillClass(workflow.id)}`}
                      disabled={submitting}
                      onClick={() => handleChooseWorkflow(workflow.id)}
                    >
                      <span className="add-task-to-workflow-card-name">{workflow.workflow_name}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )
          ) : (
            <WorkflowSequencePositionFieldset
              tasks={workflowTasks}
              insertPosition={insertPosition}
              disabled={submitting}
              legend="Where should this task go in the sequence?"
              onChange={setInsertPosition}
            />
          )}
        </div>

        <div className="modal-actions modal-actions-footer">
          {step === "workflow" ? (
            <button type="button" className="modal-secondary" disabled={submitting} onClick={handleClose}>
              Cancel
            </button>
          ) : (
            <>
              <button type="button" className="modal-secondary" disabled={submitting} onClick={handleBack}>
                Back
              </button>
              <button type="button" className="modal-secondary" disabled={submitting} onClick={handleClose}>
                Cancel
              </button>
              <button
                type="button"
                className="modal-primary"
                disabled={submitting || !selectedWorkflowId}
                onClick={() => void handleAccept()}
              >
                {submitting ? "Adding..." : "Accept"}
              </button>
            </>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}
