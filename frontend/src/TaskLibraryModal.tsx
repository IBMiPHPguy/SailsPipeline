import { createPortal } from "react-dom";
import type { AgencyTaskCatalogItem } from "./types";

type TaskLibraryModalProps = {
  open: boolean;
  catalog: AgencyTaskCatalogItem[];
  placedTaskKeys: Set<string>;
  onClose: () => void;
};

export default function TaskLibraryModal({ open, catalog, placedTaskKeys, onClose }: TaskLibraryModalProps) {
  if (!open) {
    return null;
  }

  return createPortal(
    <div className="modal-overlay" role="presentation" onClick={onClose}>
      <div
        className="modal-card workflows-task-library-modal"
        role="dialog"
        aria-labelledby="task-library-title"
        aria-modal="true"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="modal-header">
          <h2 id="task-library-title">Built-in task library</h2>
          <button type="button" className="icon-button" aria-label="Close" onClick={onClose}>
            ×
          </button>
        </header>
        <div className="modal-body workflows-task-library-body">
          <p className="meta">
            System tasks your agency can place on a playbook. Tasks already in use are marked as placed.
          </p>
          <ul className="workflows-task-library-list">
            {catalog.map((item) => {
              const isPlaced = placedTaskKeys.has(item.task_key);
              return (
                <li key={item.task_key} className="workflows-task-library-row">
                  <div className="workflows-task-library-row-main">
                    <span className="workflows-task-library-title">{item.task_title}</span>
                    <span
                      className={`workflows-settings-task-type-badge workflows-settings-task-type-badge-builtin${
                        isPlaced ? " is-placed" : ""
                      }`}
                    >
                      {isPlaced ? "Placed" : "Available"}
                    </span>
                  </div>
                  <p className="meta workflows-task-library-description">{item.description}</p>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </div>,
    document.body,
  );
}

function taskTypeLabel(task: { task_key: string | null; action_type: string }): "Built-in" | "Checklist" {
  if (task.task_key) {
    return "Built-in";
  }
  if (task.action_type === "manual_check") {
    return "Checklist";
  }
  return "Built-in";
}

export function TaskTypeBadge({ task }: { task: { task_key: string | null; action_type: string } }) {
  const label = taskTypeLabel(task);
  const className =
    label === "Checklist"
      ? "workflows-settings-task-type-badge workflows-settings-task-type-badge-checklist"
      : "workflows-settings-task-type-badge workflows-settings-task-type-badge-builtin";
  return <span className={className}>{label}</span>;
}
