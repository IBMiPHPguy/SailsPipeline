import { FormEvent, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { createAgencyGroupInventory, updateAgencyGroupInventory } from "./api";
import { CABIN_TYPES } from "./formOptions";
import type { AgencyGroupInventory } from "./types";

const emptyInventoryForm = {
  cabin_category: "",
  cabin_type: CABIN_TYPES[0] as string,
  cabin_description: "",
  price_per_cabin: "0",
  cabins_allocated: "0",
  cabins_reserved: "0",
};

type GroupInventoryEditModalMode = "create" | "edit";

type GroupInventoryEditModalProps = {
  open: boolean;
  mode: GroupInventoryEditModalMode;
  groupId: string | null;
  inventory: AgencyGroupInventory | null;
  onClose: () => void;
  onSaved: () => void | Promise<void>;
};

function inventoryToForm(inventory: AgencyGroupInventory) {
  return {
    cabin_category: inventory.cabin_category,
    cabin_type: inventory.cabin_type,
    cabin_description: inventory.cabin_description ?? "",
    price_per_cabin: String(inventory.price_per_cabin),
    cabins_allocated: String(inventory.cabins_allocated),
    cabins_reserved: String(inventory.cabins_reserved),
  };
}

export default function GroupInventoryEditModal({
  open,
  mode,
  groupId,
  inventory,
  onClose,
  onSaved,
}: GroupInventoryEditModalProps) {
  const [form, setForm] = useState(emptyInventoryForm);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const isEdit = mode === "edit";

  useEffect(() => {
    if (!open) {
      setForm(emptyInventoryForm);
      setError("");
      setSubmitting(false);
      return;
    }

    if (isEdit && inventory) {
      setForm(inventoryToForm(inventory));
      setError("");
      return;
    }

    setForm(emptyInventoryForm);
    setError("");
  }, [open, isEdit, inventory]);

  if (!open) {
    return null;
  }

  if (isEdit && !inventory) {
    return null;
  }

  if (!isEdit && !groupId) {
    return null;
  }

  const formId = isEdit ? "edit-group-inventory-form" : "create-group-inventory-form";
  const titleId = isEdit ? "edit-group-inventory-title" : "create-group-inventory-title";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const payload = {
        cabin_category: form.cabin_category.trim(),
        cabin_type: form.cabin_type,
        cabin_description: form.cabin_description.trim() || undefined,
        price_per_cabin: Number(form.price_per_cabin || 0),
        cabins_allocated: Number(form.cabins_allocated || 0),
        cabins_reserved: Number(form.cabins_reserved || 0),
      };

      if (isEdit && inventory) {
        await updateAgencyGroupInventory(inventory.id, payload);
      } else if (groupId) {
        await createAgencyGroupInventory(groupId, payload);
      }

      await onSaved();
      onClose();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to save inventory row.");
    } finally {
      setSubmitting(false);
    }
  }

  return createPortal(
    <div className="modal-backdrop modal-backdrop-scroll" role="presentation" onClick={onClose}>
      <div
        className="modal-card group-inventory-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(event) => event.stopPropagation()}
      >
        <header className="modal-card-header">
          <h3 id={titleId}>{isEdit ? "Edit Inventory Row" : "Add Inventory Row"}</h3>
        </header>

        <form
          id={formId}
          className="modal-scroll-body group-inventory-form"
          onSubmit={(event) => void handleSubmit(event)}
        >
          {error ? <p className="status error">{error}</p> : null}

          <label>
            Cabin category
            <input
              required
              type="text"
              value={form.cabin_category}
              disabled={submitting}
              onChange={(event) => setForm({ ...form, cabin_category: event.target.value })}
            />
          </label>

          <label>
            Cabin type
            <select
              required
              value={form.cabin_type}
              disabled={submitting}
              onChange={(event) => setForm({ ...form, cabin_type: event.target.value })}
            >
              {CABIN_TYPES.map((cabinType) => (
                <option key={cabinType} value={cabinType}>
                  {cabinType}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span>
              Description <span className="field-optional">(Optional)</span>
            </span>
            <textarea
              rows={2}
              value={form.cabin_description}
              disabled={submitting}
              onChange={(event) => setForm({ ...form, cabin_description: event.target.value })}
            />
          </label>

          <label>
            Price per cabin
            <input
              required
              type="number"
              min={0}
              step="0.01"
              value={form.price_per_cabin}
              disabled={submitting}
              onChange={(event) => setForm({ ...form, price_per_cabin: event.target.value })}
            />
          </label>

          <div className="field-row">
            <label>
              Cabins allocated
              <input
                required
                type="number"
                min={0}
                step="1"
                value={form.cabins_allocated}
                disabled={submitting}
                onChange={(event) => setForm({ ...form, cabins_allocated: event.target.value })}
              />
            </label>
            <label>
              Cabins reserved
              <input
                required
                type="number"
                min={0}
                step="1"
                value={form.cabins_reserved}
                disabled={submitting}
                onChange={(event) => setForm({ ...form, cabins_reserved: event.target.value })}
              />
            </label>
          </div>
        </form>

        <div className="modal-actions modal-actions-footer">
          <button type="button" className="modal-secondary" disabled={submitting} onClick={onClose}>
            Cancel
          </button>
          <button type="submit" form={formId} disabled={submitting}>
            {submitting ? (isEdit ? "Saving..." : "Adding...") : isEdit ? "Save changes" : "Add row"}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
