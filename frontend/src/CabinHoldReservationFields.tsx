import {
  buildCabinHoldReservationDisplayLines,
  cabinHoldReservationLabel,
  normalizeCabinHoldReservationDrafts,
  type CabinHoldReservationDisplayLine,
  type CabinHoldReservationIds,
} from "./cabinHoldReservations";
import { proposedRoomLabel } from "./proposedCruiseRooms";

type CabinHoldReservationFieldsProps = {
  cabinsNeeded: number;
  value: CabinHoldReservationIds;
  onChange: (value: CabinHoldReservationIds) => void;
  disabled: boolean;
  readOnly?: boolean;
  passengerNamesByCabin?: string[];
  singleReservationOnly?: boolean;
  compact?: boolean;
};

export function CabinHoldReservationDisplay({
  lines,
}: {
  lines: CabinHoldReservationDisplayLine[];
}) {
  if (lines.length === 0) {
    return null;
  }

  return (
    <div className="cabin-hold-reservations-display">
      {lines.map((line) => (
        <div className="cabin-hold-reservation-line" key={line.label}>
          <span className="cabin-hold-reservation-label">{line.label}</span>
          {line.reservationIds.length === 1 ? (
            <span className="cabin-hold-reservation-value">{line.reservationIds[0]}</span>
          ) : (
            <ul className="cabin-hold-reservation-id-list">
              {line.reservationIds.map((reservationId, index) => (
                <li key={`${line.label}-${index}-${reservationId}`}>{reservationId}</li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}

export function cabinHoldReservationDisplayLines(
  reservationIds: CabinHoldReservationIds | null | undefined,
) {
  return buildCabinHoldReservationDisplayLines(reservationIds);
}

export default function CabinHoldReservationFields({
  cabinsNeeded,
  value,
  onChange,
  disabled,
  readOnly = false,
  passengerNamesByCabin,
  singleReservationOnly = true,
  compact = false,
}: CabinHoldReservationFieldsProps) {
  const drafts = normalizeCabinHoldReservationDrafts(value, cabinsNeeded).map((cabinIds, cabinIndex) =>
    singleReservationOnly ? [cabinIds[0] ?? ""] : cabinIds,
  );
  const fieldsDisabled = disabled || readOnly;

  function updateDrafts(nextDrafts: CabinHoldReservationIds) {
    onChange(normalizeCabinHoldReservationDrafts(nextDrafts, cabinsNeeded));
  }

  function updateReservationId(cabinIndex: number, reservationIndex: number, nextValue: string) {
    const nextDrafts = drafts.map((cabinIds, index) =>
      index === cabinIndex
        ? singleReservationOnly
          ? [nextValue]
          : cabinIds.map((reservationId, currentIndex) =>
              currentIndex === reservationIndex ? nextValue : reservationId,
            )
        : [...cabinIds],
    );
    updateDrafts(nextDrafts);
  }

  function addReservationId(cabinIndex: number) {
    const nextDrafts = drafts.map((cabinIds, index) =>
      index === cabinIndex ? [...cabinIds, ""] : [...cabinIds],
    );
    updateDrafts(nextDrafts);
  }

  function removeReservationId(cabinIndex: number, reservationIndex: number) {
    const nextDrafts = drafts.map((cabinIds, index) => {
      if (index !== cabinIndex) {
        return [...cabinIds];
      }
      const filtered = cabinIds.filter((_, currentIndex) => currentIndex !== reservationIndex);
      return filtered.length > 0 ? filtered : [""];
    });
    updateDrafts(nextDrafts);
  }

  return (
    <div className="cabin-hold-reservation-fields">
      {drafts.map((cabinIds, cabinIndex) => (
        <article className="cabin-hold-reservation-cabin" key={`cabin-${cabinIndex + 1}`}>
          {!compact ? <h4>{proposedRoomLabel(cabinIndex, cabinsNeeded)}</h4> : null}
          {passengerNamesByCabin?.[cabinIndex] ? (
            <p className="meta cabin-hold-room-passengers">Passengers: {passengerNamesByCabin[cabinIndex]}</p>
          ) : null}

          <div className="cabin-hold-reservation-id-list-editor">
            {cabinIds.map((reservationId, reservationIndex) => (
              <div className="cabin-hold-reservation-id-row" key={`cabin-${cabinIndex + 1}-id-${reservationIndex}`}>
                <label>
                  {singleReservationOnly
                    ? "Reservation ID"
                    : `${cabinHoldReservationLabel(cabinIndex, cabinsNeeded)}${
                        cabinIds.length > 1 ? ` ${reservationIndex + 1}` : ""
                      }`}
                  <input
                    type="text"
                    disabled={fieldsDisabled}
                    value={reservationId}
                    onChange={(event) =>
                      updateReservationId(cabinIndex, reservationIndex, event.target.value)
                    }
                  />
                </label>
                {!fieldsDisabled && !singleReservationOnly && cabinIds.length > 1 ? (
                  <button
                    type="button"
                    className="modal-secondary cabin-hold-reservation-remove"
                    disabled={fieldsDisabled}
                    onClick={() => removeReservationId(cabinIndex, reservationIndex)}
                  >
                    Remove
                  </button>
                ) : null}
              </div>
            ))}
          </div>

          {!fieldsDisabled && !singleReservationOnly ? (
            <button
              type="button"
              className="modal-secondary cabin-hold-reservation-add"
              disabled={fieldsDisabled}
              onClick={() => addReservationId(cabinIndex)}
            >
              Add another reservation ID
            </button>
          ) : null}
        </article>
      ))}
    </div>
  );
}
