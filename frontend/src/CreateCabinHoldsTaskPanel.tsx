import { useEffect, useMemo, useState } from "react";
import { updateProposedCruise, updateTask } from "./api";
import AcceptedCruiseSummary from "./AcceptedCruiseSummary";
import CabinHoldReservationFields from "./CabinHoldReservationFields";
import {
  normalizeCabinHoldReservationDrafts,
  proposedCruiseReservationIds,
  sanitizeCabinHoldReservationIds,
  validateCabinHoldReservationDrafts,
  type CabinHoldReservationIds,
} from "./cabinHoldReservations";
import { TASK_STATUS_DONE } from "./formOptions";
import { formatPassengerNames } from "./proposedCruiseRooms";
import type { ProposedCruise } from "./types";

type CreateCabinHoldsTaskPanelProps = {
  requestId: number;
  cabinsNeeded: number;
  bookingCruises: ProposedCruise[];
  taskId: number;
  disabled: boolean;
  isDone: boolean;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
  onSaved: () => void;
};

function sortBookingCruises(cruises: ProposedCruise[]): ProposedCruise[] {
  return [...cruises].sort(
    (left, right) => left.departure_date.localeCompare(right.departure_date) || left.id - right.id,
  );
}

export default function CreateCabinHoldsTaskPanel({
  requestId,
  cabinsNeeded,
  bookingCruises,
  taskId,
  disabled,
  isDone,
  onChanged,
  onError,
  onSaved,
}: CreateCabinHoldsTaskPanelProps) {
  const safeCabinsNeeded = Math.max(1, cabinsNeeded);
  const sortedBookingCruises = useMemo(() => sortBookingCruises(bookingCruises), [bookingCruises]);
  const [draftsByCruiseId, setDraftsByCruiseId] = useState<Record<number, CabinHoldReservationIds>>({});
  const [saving, setSaving] = useState(false);
  const readOnly = disabled || isDone;

  useEffect(() => {
    const nextDrafts: Record<number, CabinHoldReservationIds> = {};
    for (const cruise of sortedBookingCruises) {
      nextDrafts[cruise.id] = proposedCruiseReservationIds(cruise, safeCabinsNeeded);
    }
    setDraftsByCruiseId(nextDrafts);
  }, [sortedBookingCruises, safeCabinsNeeded]);

  function updateCruiseDrafts(cruiseId: number, drafts: CabinHoldReservationIds) {
    setDraftsByCruiseId((current) => ({
      ...current,
      [cruiseId]: drafts,
    }));
  }

  async function handleSaveAndComplete() {
    if (sortedBookingCruises.length === 0) {
      onError("Accept at least one proposed cruise before saving cabin hold reservation IDs.");
      return;
    }

    for (const cruise of sortedBookingCruises) {
      const drafts = draftsByCruiseId[cruise.id] ?? normalizeCabinHoldReservationDrafts([], safeCabinsNeeded);
      const validationError = validateCabinHoldReservationDrafts(drafts, safeCabinsNeeded);
      if (validationError) {
        onError(`${cruise.ship}: ${validationError}`);
        return;
      }
    }

    setSaving(true);
    onError("");
    try {
      for (const cruise of sortedBookingCruises) {
        const drafts = draftsByCruiseId[cruise.id] ?? normalizeCabinHoldReservationDrafts([], safeCabinsNeeded);
        await updateProposedCruise(requestId, cruise.id, {
          cabin_hold_reservation_ids: sanitizeCabinHoldReservationIds(drafts, safeCabinsNeeded),
        });
      }

      await updateTask(requestId, taskId, { status: TASK_STATUS_DONE });
      await onChanged();
      onSaved();
    } catch (saveError) {
      onError(saveError instanceof Error ? saveError.message : "Unable to save cabin hold reservation IDs.");
    } finally {
      setSaving(false);
    }
  }

  if (sortedBookingCruises.length === 0) {
    return (
      <div className="create-cabin-holds-panel">
        <p className="field-hint">Accept at least one proposed cruise before entering cabin hold reservation IDs.</p>
      </div>
    );
  }

  return (
    <div className="create-cabin-holds-panel">
      <p className="field-hint">
        {sortedBookingCruises.length === 1
          ? "Enter a cruise line reservation ID for each room on the accepted cruise."
          : "This request has multiple accepted cruises. Enter a reservation ID for each room on every accepted cruise below."}
      </p>

      <div className="create-cabin-holds-cruise-list">
        {sortedBookingCruises.map((cruise) => {
          const drafts =
            draftsByCruiseId[cruise.id] ?? proposedCruiseReservationIds(cruise, safeCabinsNeeded);
          const passengerNamesByCabin = Array.from({ length: safeCabinsNeeded }, (_, cabinIndex) =>
            formatPassengerNames(cruise.room_passengers?.[cabinIndex] ?? []),
          );

          return (
            <section className="create-cabin-holds-cruise-card" key={cruise.id}>
              <header className="create-cabin-holds-cruise-header">
                <AcceptedCruiseSummary cruise={cruise} />
                <p className="meta">
                  {cruise.number_of_nights} nights · {cruise.itinerary_name}
                </p>
              </header>

              <CabinHoldReservationFields
                cabinsNeeded={safeCabinsNeeded}
                value={drafts}
                onChange={(nextDrafts) => updateCruiseDrafts(cruise.id, nextDrafts)}
                disabled={disabled || saving}
                readOnly={readOnly}
                passengerNamesByCabin={passengerNamesByCabin}
                singleReservationOnly
              />
            </section>
          );
        })}
      </div>

      {!readOnly ? (
        <button type="button" disabled={saving} onClick={() => void handleSaveAndComplete()}>
          {saving ? "Saving..." : "Save reservation IDs and mark task done"}
        </button>
      ) : null}
    </div>
  );
}
