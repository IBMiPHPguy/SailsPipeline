import { FormEvent, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import {
  createAgencyCustomTaskDefinition,
  createAgencyTaskFromCustomDefinition,
  updateAgencyCustomTaskDefinition,
} from "./api";
import WorkflowSequencePositionFieldset, { type InsertPosition } from "./WorkflowSequencePositionFieldset";
import type { AgencyCustomTaskDefinition, AgencyWorkflowTemplate } from "./types";

type CustomTaskBuilderModalProps = {
  open: boolean;
  definition: AgencyCustomTaskDefinition | null;
  placementWorkflow: AgencyWorkflowTemplate | null;
  onClose: () => void;
  onSaved: (definition: AgencyCustomTaskDefinition) => void | Promise<void>;
};

export default function CustomTaskBuilderModal({
  open,
  definition,
  placementWorkflow,
  onClose,
  onSaved,
}: CustomTaskBuilderModalProps) {
  const isEdit = definition !== null;
  const isPlacementCreate = !isEdit && placementWorkflow !== null;
  const [taskTitle, setTaskTitle] = useState("");
  const [description, setDescription] = useState("");
  const [insertPosition, setInsertPosition] = useState<InsertPosition>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const placementTasks = useMemo(
    () =>
      placementWorkflow
        ? [...placementWorkflow.task_templates].sort((left, right) => left.sequence_order - right.sequence_order)
        : [],
    [placementWorkflow],
  );

  useEffect(() => {
    if (!open) {
      setTaskTitle("");
      setDescription("");
      setInsertPosition(null);
      setError("");
      setSubmitting(false);
      return;
    }
    setTaskTitle(definition?.task_title ?? "");
    setDescription(definition?.description ?? "");
    setError("");
    if (isPlacementCreate) {
      setInsertPosition(placementTasks.length === 0 ? 1 : null);
    } else {
      setInsertPosition(null);
    }
  }, [definition, isPlacementCreate, open, placementTasks.length]);

  if (!open) {
    return null;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const title = taskTitle.trim();
    if (!title) {
      setError("Task name is required.");
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      if (isEdit && definition) {
        const saved = await updateAgencyCustomTaskDefinition(definition.id, {
          task_title: title,
          description: description.trim() || null,
        });
        await onSaved(saved);
        onClose();
        return;
      }

      const saved = await createAgencyCustomTaskDefinition({
        task_title: title,
        description: description.trim() || null,
      });

      if (isPlacementCreate && placementWorkflow) {
        await createAgencyTaskFromCustomDefinition(
          placementWorkflow.id,
          saved.task_key,
          insertPosition === null ? null : insertPosition,
        );
      }

      await onSaved(saved);
      onClose();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to save checklist task.");
    } finally {
      setSubmitting(false);
    }
  }

  const submitLabel = isEdit
    ? "Save changes"
    : isPlacementCreate
      ? "Create and add to workflow"
      : "Create task";

  return createPortal(
    <div className="modal-backdrop modal-backdrop-scroll" role="presentation" onClick={onClose}>
      <div
        className="modal-card custom-task-builder-modal"
        role="dialog"
        aria-labelledby="custom-task-builder-title"
        aria-modal="true"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="modal-card-header">
          <h3 id="custom-task-builder-title">
            {isEdit ? "Edit checklist task" : "Create checklist task"}
          </h3>
        </header>

        <form className="modal-scroll-body custom-task-builder-body" onSubmit={(event) => void handleSubmit(event)}>
          {isPlacementCreate && placementWorkflow ? (
            <div className="modal-meta-row">
              <span>{placementWorkflow.workflow_name}</span>
              <span className="modal-meta-separator" aria-hidden="true">
                |
              </span>
              <span>Add to this workflow</span>
            </div>
          ) : null}

          <p className="meta custom-task-builder-intro">
            {isPlacementCreate
              ? "Create a reusable library checklist task and place it in the workflow sequence you choose below."
              : "Library checklist tasks can be added to any workflow. Each task can appear on only one workflow at a time."}
          </p>

          <label>
            Task name
            <input
              type="text"
              value={taskTitle}
              placeholder="e.g. Confirm client travel insurance"
              disabled={submitting}
              onChange={(event) => setTaskTitle(event.target.value)}
            />
          </label>

          <label>
            Description (optional)
            <textarea
              value={description}
              rows={3}
              placeholder="What should the agent do on this step?"
              disabled={submitting}
              onChange={(event) => setDescription(event.target.value)}
            />
          </label>

          {isPlacementCreate ? (
            <WorkflowSequencePositionFieldset
              tasks={placementTasks}
              insertPosition={insertPosition}
              disabled={submitting}
              legend="Where should this task go in the sequence?"
              onChange={setInsertPosition}
            />
          ) : null}

          {error ? <p className="status error">{error}</p> : null}

          <div className="modal-actions modal-actions-footer">
            <button type="button" className="modal-secondary" disabled={submitting} onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="modal-primary" disabled={submitting}>
              {submitting ? "Saving..." : submitLabel}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body,
  );
}
