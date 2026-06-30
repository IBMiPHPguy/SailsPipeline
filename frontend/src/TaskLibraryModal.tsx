import { createPortal } from "react-dom";
import type { AgencyTaskCatalogItem } from "./types";

type TaskLibraryModalProps = {
  open: boolean;
  catalog: AgencyTaskCatalogItem[];
  placedTaskKeys: Set<string>;
  availableCount: number;
  onClose: () => void;
};

export default function TaskLibraryModal({
  open,
  catalog,
  placedTaskKeys,
  availableCount,
  onClose,
}: TaskLibraryModalProps) {
  if (!open) {
    return null;
  }

  const placedCount = placedTaskKeys.size;
  const totalCount = catalog.length;

  return createPortal(
    <div className="modal-backdrop modal-backdrop-scroll" role="presentation" onClick={onClose}>
      <div
        className="modal-card modal-card-wide task-library-modal"
        role="dialog"
        aria-labelledby="task-library-title"
        aria-modal="true"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="modal-card-header">
          <h3 id="task-library-title">Task library</h3>
        </header>

        <div className="modal-scroll-body task-library-modal-body">
          <div className="modal-meta-row task-library-modal-summary">
            <span>
              {totalCount} built-in {totalCount === 1 ? "task" : "tasks"}
            </span>
            <span className="modal-meta-separator" aria-hidden="true">
              |
            </span>
            <span>
              {availableCount} available
            </span>
            <span className="modal-meta-separator" aria-hidden="true">
              |
            </span>
            <span>
              {placedCount} placed
            </span>
          </div>

          <p className="meta task-library-modal-intro">
            Built-in steps your agency can add to a workflow. Each task can appear on only one workflow at a time.
          </p>

          <ul className="task-library-modal-list">
            {catalog.map((item) => {
              const isPlaced = placedTaskKeys.has(item.task_key);
              return (
                <li key={item.task_key} className="modal-section-panel task-library-modal-item">
                  <div className="task-library-modal-item-header">
                    <h4 className="task-library-modal-item-title">{item.task_title}</h4>
                    <span
                      className={`task-library-modal-status${
                        isPlaced ? " task-library-modal-status-placed" : " task-library-modal-status-available"
                      }`}
                    >
                      {isPlaced ? "Placed" : "Available"}
                    </span>
                  </div>
                  <p className="meta task-library-modal-item-description">{item.description}</p>
                </li>
              );
            })}
          </ul>
        </div>

        <div className="modal-actions modal-actions-footer">
          <button type="button" className="modal-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}

function taskTypeLabel(task: { task_key: string | null; action_type: string }): "Built-in" | "Checklist" | "Library" {
  if (task.task_key?.startsWith("custom_")) {
    return "Library";
  }
  if (task.task_key) {
    return "Built-in";
  }
  if (task.action_type === "manual_check") {
    return "Checklist";
  }
  return "Built-in";
}

export function TaskTypeBadge({
  task,
  onLibraryClick,
}: {
  task: { task_key: string | null; action_type: string };
  onLibraryClick?: () => void;
}) {
  const label = taskTypeLabel(task);
  const className =
    label === "Checklist"
      ? "workflows-settings-task-type-badge workflows-settings-task-type-badge-checklist"
      : label === "Library"
        ? "workflows-settings-task-type-badge workflows-settings-task-type-badge-library"
        : "workflows-settings-task-type-badge workflows-settings-task-type-badge-builtin";

  if (label === "Library" && onLibraryClick) {
    return (
      <button type="button" className={`${className} workflows-settings-task-type-badge-button`} onClick={onLibraryClick}>
        {label}
      </button>
    );
  }

  return <span className={className}>{label}</span>;
}
