import { FormEvent, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { createAgencyGroup, updateAgencyGroup } from "./api";
import CruiseLineSelect from "./CruiseLineSelect";
import type { AgencyGroup } from "./types";

const emptyGroupForm = {
  group_name: "",
  cruise_line: "",
  ship_name: "",
  sailing_date: "",
  disembarkation_date: "",
  group_id_code: "",
  group_amenities: "",
  tc_ratio: "1:16",
};

type GroupShellModalMode = "create" | "edit";

type GroupShellModalProps = {
  open: boolean;
  mode: GroupShellModalMode;
  group: AgencyGroup | null;
  onClose: () => void;
  onSaved: (group: AgencyGroup) => void;
};

function groupToForm(group: AgencyGroup) {
  return {
    group_name: group.group_name,
    cruise_line: group.cruise_line,
    ship_name: group.ship_name,
    sailing_date: group.sailing_date,
    disembarkation_date: group.disembarkation_date,
    group_id_code: group.group_id_code ?? "",
    group_amenities: group.group_amenities ?? "",
    tc_ratio: group.tc_ratio ?? "1:16",
  };
}

export default function GroupShellModal({ open, mode, group, onClose, onSaved }: GroupShellModalProps) {
  const [form, setForm] = useState(emptyGroupForm);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const isEdit = mode === "edit";

  useEffect(() => {
    if (!open) {
      setForm(emptyGroupForm);
      setError("");
      setSubmitting(false);
      return;
    }

    if (isEdit && group) {
      setForm(groupToForm(group));
      setError("");
      return;
    }

    setForm(emptyGroupForm);
    setError("");
  }, [open, isEdit, group]);

  if (!open) {
    return null;
  }

  if (isEdit && !group) {
    return null;
  }

  const formId = isEdit ? "edit-group-shell-form" : "create-group-shell-form";
  const titleId = isEdit ? "edit-group-shell-title" : "create-group-shell-title";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const payload = {
        group_name: form.group_name.trim(),
        cruise_line: form.cruise_line,
        ship_name: form.ship_name.trim(),
        sailing_date: form.sailing_date,
        disembarkation_date: form.disembarkation_date,
        group_id_code: form.group_id_code.trim() || undefined,
        group_amenities: form.group_amenities.trim() || undefined,
        tc_ratio: form.tc_ratio.trim() || "1:16",
      };

      const saved = isEdit && group ? await updateAgencyGroup(group.id, payload) : await createAgencyGroup(payload);
      onSaved(saved);
      onClose();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to save group block.");
    } finally {
      setSubmitting(false);
    }
  }

  return createPortal(
    <div className="modal-backdrop modal-backdrop-scroll" role="presentation" onClick={onClose}>
      <div
        className="modal-card group-shell-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(event) => event.stopPropagation()}
      >
        <header className="modal-card-header">
          <h3 id={titleId}>{isEdit ? "Edit Group Block" : "Create Group Block"}</h3>
        </header>

        <form id={formId} className="modal-scroll-body group-shell-form" onSubmit={(event) => void handleSubmit(event)}>
          {error ? <p className="status error">{error}</p> : null}

          <label>
            Group name
            <input
              required
              type="text"
              value={form.group_name}
              disabled={submitting}
              onChange={(event) => setForm({ ...form, group_name: event.target.value })}
            />
          </label>

          <label>
            Cruise line
            <CruiseLineSelect
              required
              value={form.cruise_line}
              disabled={submitting}
              onChange={(value) => setForm({ ...form, cruise_line: value })}
            />
          </label>

          <label>
            Ship name
            <input
              required
              type="text"
              value={form.ship_name}
              disabled={submitting}
              onChange={(event) => setForm({ ...form, ship_name: event.target.value })}
            />
          </label>

          <div className="field-row">
            <label>
              Sailing date
              <input
                required
                type="date"
                value={form.sailing_date}
                disabled={submitting}
                onChange={(event) => setForm({ ...form, sailing_date: event.target.value })}
              />
            </label>
            <label>
              Disembarkation date
              <input
                required
                type="date"
                value={form.disembarkation_date}
                disabled={submitting}
                onChange={(event) => setForm({ ...form, disembarkation_date: event.target.value })}
              />
            </label>
          </div>

          <label>
            <span>
              Group ID code <span className="field-optional">(Optional)</span>
            </span>
            <input
              type="text"
              value={form.group_id_code}
              disabled={submitting}
              onChange={(event) => setForm({ ...form, group_id_code: event.target.value })}
            />
          </label>

          <label>
            <span>
              TC ratio <span className="field-optional">(Optional)</span>
            </span>
            <input
              type="text"
              value={form.tc_ratio}
              disabled={submitting}
              onChange={(event) => setForm({ ...form, tc_ratio: event.target.value })}
            />
          </label>

          <label>
            <span>
              Group amenities <span className="field-optional">(Optional)</span>
            </span>
            <textarea
              rows={3}
              value={form.group_amenities}
              disabled={submitting}
              onChange={(event) => setForm({ ...form, group_amenities: event.target.value })}
            />
          </label>
        </form>

        <div className="modal-actions modal-actions-footer">
          <button type="button" className="modal-secondary" disabled={submitting} onClick={onClose}>
            Cancel
          </button>
          <button type="submit" form={formId} disabled={submitting}>
            {submitting ? (isEdit ? "Saving..." : "Creating...") : isEdit ? "Save changes" : "Create group block"}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
