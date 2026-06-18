import {
  normalizeRoomPassengerIds,
  proposedRoomLabel,
  toggleRoomPassengerId,
  type RoomPassengerIds,
} from "./proposedCruiseRooms";
import type { RequestPassenger } from "./types";

type ProposedCruiseRoomPassengerFieldsProps = {
  cabinsNeeded: number;
  passengersInRoom: number | number[];
  passengers: RequestPassenger[];
  value: RoomPassengerIds;
  onChange: (value: RoomPassengerIds) => void;
  disabled: boolean;
  activeCabinIndex?: number;
};

export default function ProposedCruiseRoomPassengerFields({
  cabinsNeeded,
  passengersInRoom,
  passengers,
  value,
  onChange,
  disabled,
  activeCabinIndex,
}: ProposedCruiseRoomPassengerFieldsProps) {
  const safeCabinsNeeded = Math.max(1, cabinsNeeded);
  const roomPassengerIds = normalizeRoomPassengerIds(value, safeCabinsNeeded);
  const perRoomLimits = Array.isArray(passengersInRoom)
    ? passengersInRoom
    : Array.from({ length: safeCabinsNeeded }, () => passengersInRoom);
  const visibleCabinIndexes =
    activeCabinIndex === undefined
      ? roomPassengerIds.map((_, cabinIndex) => cabinIndex)
      : [activeCabinIndex];

  function handleRoomChange(nextRoomPassengerIds: RoomPassengerIds) {
    onChange(normalizeRoomPassengerIds(nextRoomPassengerIds, safeCabinsNeeded));
  }

  return (
    <div className="proposed-cruise-room-passengers">
      <p className="field-hint">
        Assign passengers to each room needed on this request. Selecting a passenger here moves them from any other
        room automatically.
      </p>

      <div className="proposed-cruise-room-passenger-list">
        {visibleCabinIndexes.map((cabinIndex) => {
          const roomIds = roomPassengerIds[cabinIndex] ?? [];
          const roomLimit = perRoomLimits[cabinIndex] ?? perRoomLimits[perRoomLimits.length - 1] ?? 2;

          return (
          <fieldset className="checkbox-group proposed-cruise-room-passenger-item" key={`room-passengers-${cabinIndex}`}>
            <legend className="field-label">
              {proposedRoomLabel(cabinIndex, safeCabinsNeeded)} passengers ({roomIds.length}/{roomLimit})
            </legend>
            {passengers.length === 0 ? (
              <p className="meta">Add passengers to the request before assigning them to rooms.</p>
            ) : (
              passengers.map((passenger) => {
                const checked = roomIds.includes(passenger.id);
                const roomFull = !checked && roomIds.length >= roomLimit;

                return (
                  <label className="checkbox-inline" key={`${cabinIndex}-${passenger.id}`}>
                    <input
                      type="checkbox"
                      disabled={disabled || roomFull}
                      checked={checked}
                      onChange={() =>
                        handleRoomChange(
                          toggleRoomPassengerId(roomPassengerIds, cabinIndex, passenger.id, passengersInRoom),
                        )
                      }
                    />
                    {passenger.first_name} {passenger.last_name}
                  </label>
                );
              })
            )}
          </fieldset>
        );
        })}
      </div>
    </div>
  );
}
