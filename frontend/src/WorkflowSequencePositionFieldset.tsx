import type { AgencyTaskTemplate } from "./types";

/** null means append at end of the sequence. */
export type InsertPosition = number | null;

type WorkflowSequencePositionFieldsetProps = {
  tasks: AgencyTaskTemplate[];
  insertPosition: InsertPosition;
  disabled?: boolean;
  legend?: string;
  onChange: (position: InsertPosition) => void;
};

export default function WorkflowSequencePositionFieldset({
  tasks,
  insertPosition,
  disabled = false,
  legend = "Insert task at",
  onChange,
}: WorkflowSequencePositionFieldsetProps) {
  return (
    <fieldset className="workflow-task-move-fieldset">
      <legend className="workflow-task-move-legend">{legend}</legend>
      <ul className="workflow-task-move-list">
        {tasks.length === 0 ? (
          <li className="modal-section-panel workflow-task-move-option">
            <label className="workflow-task-move-option-label">
              <input
                type="radio"
                name="workflow-sequence-position"
                checked={insertPosition === 1}
                disabled={disabled}
                onChange={() => onChange(1)}
              />
              <span className="workflow-task-move-option-text">
                <span className="workflow-task-move-option-name">As the first task</span>
              </span>
            </label>
          </li>
        ) : (
          <>
            {tasks.map((task, index) => (
              <li key={task.id} className="modal-section-panel workflow-task-move-option">
                <label className="workflow-task-move-option-label">
                  <input
                    type="radio"
                    name="workflow-sequence-position"
                    checked={insertPosition === index + 1}
                    disabled={disabled}
                    onChange={() => onChange(index + 1)}
                  />
                  <span className="workflow-task-move-option-text">
                    <span className="workflow-task-move-option-name">
                      Before step {index + 1}: {task.task_title}
                    </span>
                  </span>
                </label>
              </li>
            ))}
            <li className="modal-section-panel workflow-task-move-option">
              <label className="workflow-task-move-option-label">
                <input
                  type="radio"
                  name="workflow-sequence-position"
                  checked={insertPosition === null}
                  disabled={disabled}
                  onChange={() => onChange(null)}
                />
                <span className="workflow-task-move-option-text">
                  <span className="workflow-task-move-option-name">At end of sequence</span>
                  <span className="meta workflow-task-move-option-meta">
                    After step {tasks.length}: {tasks[tasks.length - 1]?.task_title}
                  </span>
                </span>
              </label>
            </li>
          </>
        )}
      </ul>
    </fieldset>
  );
}
