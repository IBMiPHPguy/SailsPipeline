import { useEffect, useState } from "react";
import { updateRequest, updateTask } from "./api";
import CabinHoldReservationFields from "./CabinHoldReservationFields";
import {
  normalizeCabinHoldReservationDrafts,
  sanitizeCabinHoldReservationIds,
  validateCabinHoldReservationDrafts,
  type CabinHoldReservationIds,
} from "./cabinHoldReservations";
import { formatPassengerNames } from "./proposedCruiseRooms";
import { TASK_STATUS_DONE } from "./formOptions";
import type { ProposedCruise } from "./types";

type CreateCabinHoldsTaskPanelProps = {
  requestId: number;
  cabinsNeeded: number;
  reservationIds: CabinHoldReservationIds | null | undefined;
  bookingCruise: ProposedCruise | null;
  taskId: number;
  disabled: boolean;
  isDone: boolean;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
  onSaved: () => void;
};

export default function CreateCabinHoldsTaskPanel({
  requestId,
  cabinsNeeded,
  reservationIds,
  bookingCruise,
  taskId,
  disabled,
  isDone,
  onChanged,
  onError,
  onSaved,
}: CreateCabinHoldsTaskPanelProps) {
  const safeCabinsNeeded = Math.max(1, cabinsNeeded);
  const [drafts, setDrafts] = useState<CabinHoldReservationIds>(() =>
    normalizeCabinHoldReservationDrafts(reservationIds, safeCabinsNeeded),
  );
  const [saving, setSaving] = useState(false);
  const readOnly = disabled || isDone;

  useEffect(() => {
    setDrafts(normalizeCabinHoldReservationDrafts(reservationIds, safeCabinsNeeded));
  }, [reservationIds, safeCabinsNeeded]);

  async function handleSaveAndComplete() {
    const validationError = validateCabinHoldReservationDrafts(drafts, safeCabinsNeeded);
    if (validationError) {
      onError(validationError);
      return;
    }

    setSaving(true);
    onError("");
    try {
      await updateRequest(requestId, {
        cabin_hold_reservation_ids: sanitizeCabinHoldReservationIds(drafts, safeCabinsNeeded),
      });
      await updateTask(requestId, taskId, { status: TASK_STATUS_DONE });
      await onChanged();
      onSaved();
    } catch (saveError) {
      onError(saveError instanceof Error ? saveError.message : "Unable to save cabin hold reservation IDs.");
    } finally {
      setSaving(false);
    }
  }

  const passengerNamesByCabin = Array.from({ length: safeCabinsNeeded }, (_, cabinIndex) =>
    formatPassengerNames(bookingCruise?.room_passengers?.[cabinIndex] ?? []),
  );

  return (
    <div className="create-cabin-holds-panel">
      <p className="field-hint">
        This request needs {safeCabinsNeeded} cabin{safeCabinsNeeded === 1 ? "" : "s"}. Enter at least one cruise line
        reservation ID for each cabin. Add more IDs when a cabin has multiple holds.
      </p>

      <CabinHoldReservationFields
        cabinsNeeded={safeCabinsNeeded}
        value={drafts}
        onChange={setDrafts}
        disabled={disabled || saving}
        readOnly={readOnly}
        passengerNamesByCabin={passengerNamesByCabin}
      />

      {!readOnly ? (
        <button type="button" disabled={saving} onClick={() => void handleSaveAndComplete()}>
          {saving ? "Saving..." : "Save reservation IDs and mark task done"}
        </button>
      ) : null}
    </div>
  );
}
