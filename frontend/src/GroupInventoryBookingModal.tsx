import { useEffect, useMemo, useState } from "react";
import { fetchGroupInventoryOptions } from "./api";
import type { AgencyGroupInventoryOption, AgencyGroupPickerItem, TravelRequestGroupBookingInput } from "./types";

type GroupInventoryBookingModalProps = {
  open: boolean;
  group: AgencyGroupPickerItem | null;
  onClose: () => void;
  onConfirm: (bookings: TravelRequestGroupBookingInput[], options: AgencyGroupInventoryOption[]) => void;
};

type BookingDraft = Record<string, number>;

function buildInitialDraft(options: AgencyGroupInventoryOption[]): BookingDraft {
  const draft: BookingDraft = {};
  for (const option of options) {
    draft[option.id] = 0;
  }
  return draft;
}

export default function GroupInventoryBookingModal({
  open,
  group,
  onClose,
  onConfirm,
}: GroupInventoryBookingModalProps) {
  const [options, setOptions] = useState<AgencyGroupInventoryOption[]>([]);
  const [draft, setDraft] = useState<BookingDraft>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open || !group) {
      setOptions([]);
      setDraft({});
      setError("");
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError("");
    void fetchGroupInventoryOptions(group.id)
      .then((items) => {
        if (!cancelled) {
          setOptions(items);
          setDraft(buildInitialDraft(items));
        }
      })
      .catch((loadError) => {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Unable to load inventory options.");
          setOptions([]);
          setDraft({});
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [open, group]);

  const selectedBookings = useMemo(() => {
    return options
      .filter((option) => (draft[option.id] ?? 0) > 0)
      .map((option) => ({
        group_inventory_id: option.id,
        cabins_requested: draft[option.id] ?? 0,
      }));
  }, [draft, options]);

  const totalCabins = useMemo(
    () => selectedBookings.reduce((sum, booking) => sum + booking.cabins_requested, 0),
    [selectedBookings],
  );

  function updateCount(inventoryId: string, nextValue: number, maxRemaining: number) {
    const normalized = Math.max(0, Math.min(nextValue, maxRemaining, 10));
    setDraft((current) => ({ ...current, [inventoryId]: normalized }));
  }

  if (!open || !group) {
    return null;
  }

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="modal-card modal-card-wide group-inventory-booking-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="group-inventory-booking-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="modal-card-header">
          <h3 id="group-inventory-booking-title">Choose group inventory</h3>
          <p className="meta">{group.group_name}</p>
        </header>

        <div className="modal-scroll-body group-inventory-booking-modal-body">
          {loading ? <p className="meta">Loading inventory options...</p> : null}
          {error ? <p className="status error">{error}</p> : null}

          {!loading && !error && options.length === 0 ? (
            <p className="meta">This group block has no inventory rows yet.</p>
          ) : null}

          {!loading && options.length > 0 ? (
            <ul className="group-inventory-booking-list">
              {options.map((option) => {
                const count = draft[option.id] ?? 0;
                const disabled = !option.is_selectable;
                return (
                  <li key={option.id} className={`group-inventory-booking-row${disabled ? " is-disabled" : ""}`}>
                    <div className="group-inventory-booking-row-main">
                      <p className="group-inventory-booking-row-label">{option.label}</p>
                      {!option.is_selectable ? <p className="meta">Sold out</p> : null}
                    </div>
                    <label className="group-inventory-booking-count">
                      Cabins
                      <input
                        type="number"
                        min={0}
                        max={Math.min(option.cabins_remaining, 10)}
                        value={count}
                        disabled={disabled}
                        onChange={(event) => updateCount(option.id, Number(event.target.value), option.cabins_remaining)}
                      />
                    </label>
                  </li>
                );
              })}
            </ul>
          ) : null}

          {selectedBookings.length > 0 ? (
            <p className="meta group-inventory-booking-summary">
              {selectedBookings.length} categor{selectedBookings.length === 1 ? "y" : "ies"} · {totalCabins} cabin
              {totalCabins === 1 ? "" : "s"} requested
            </p>
          ) : null}
        </div>

        <div className="modal-actions modal-actions-footer">
          <button type="button" className="modal-secondary" onClick={onClose}>
            Back
          </button>
          <button
            type="button"
            disabled={loading || selectedBookings.length === 0}
            onClick={() => onConfirm(selectedBookings, options)}
          >
            Continue to request
          </button>
        </div>
      </div>
    </div>
  );
}
