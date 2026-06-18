import { useState } from "react";
import { getPassengersInRoomLimits, updateCabinRoom, formatCommissionPercentOfCost, type CabinRooms } from "./cabinRooms";
import type { CabinHoldReservationIds } from "./cabinHoldReservations";
import ProposedCruiseIncludesFields from "./ProposedCruiseIncludesFields";
import ProposedCruiseRoomPassengerFields from "./ProposedCruiseRoomPassengerFields";
import {
  proposedRoomLabel,
  type RoomPassengerIds,
} from "./proposedCruiseRooms";
import type { RequestPassenger } from "./types";

type RoomSubTab = "room" | "passengers" | "includes";

type ProposedCruiseRoomEditorProps = {
  cabinsNeeded: number;
  cabinRooms: CabinRooms;
  roomPassengerIds: RoomPassengerIds;
  passengers: RequestPassenger[];
  reservationDrafts: CabinHoldReservationIds;
  showReservationFields: boolean;
  disabled: boolean;
  canSaveRoom: boolean;
  savingRoom: boolean;
  roomSaveMessage: string;
  onSaveRoom: (cabinIndex: number) => void;
  onActiveRoomChange?: () => void;
  onCabinRoomsChange: (rooms: CabinRooms) => void;
  onRoomPassengerIdsChange: (roomPassengerIds: RoomPassengerIds) => void;
  onReservationDraftsChange: (reservationDrafts: CabinHoldReservationIds) => void;
};

const ROOM_SUB_TABS: { id: RoomSubTab; label: string }[] = [
  { id: "room", label: "Room Info" },
  { id: "passengers", label: "Passengers" },
  { id: "includes", label: "Includes" },
];

export default function ProposedCruiseRoomEditor({
  cabinsNeeded,
  cabinRooms,
  roomPassengerIds,
  passengers,
  reservationDrafts,
  showReservationFields,
  disabled,
  canSaveRoom,
  savingRoom,
  roomSaveMessage,
  onSaveRoom,
  onActiveRoomChange,
  onCabinRoomsChange,
  onRoomPassengerIdsChange,
  onReservationDraftsChange,
}: ProposedCruiseRoomEditorProps) {
  const safeCabinsNeeded = Math.max(1, cabinsNeeded);
  const [activeRoomIndex, setActiveRoomIndex] = useState(0);
  const [activeSubTab, setActiveSubTab] = useState<RoomSubTab>("room");
  const clampedRoomIndex = Math.min(activeRoomIndex, safeCabinsNeeded - 1);
  const activeRoom = cabinRooms[clampedRoomIndex];

  function updateActiveRoom(patch: Parameters<typeof updateCabinRoom>[2]) {
    onCabinRoomsChange(updateCabinRoom(cabinRooms, clampedRoomIndex, patch));
  }

  function updateReservationId(nextValue: string) {
    const normalized = reservationDrafts.map((cabinIds) => [...cabinIds]);
    normalized[clampedRoomIndex] = [nextValue];
    onReservationDraftsChange(normalized);
  }

  return (
    <section className="proposed-cruise-room-editor">
      <p className="field-label">Room details</p>

      <div className="proposed-cruise-tab-group">
        <div className="proposed-cruise-tab-bar proposed-cruise-tab-bar--rooms" role="tablist" aria-label="Cruise rooms">
          {cabinRooms.map((room, cabinIndex) => (
            <button
              key={`room-tab-${cabinIndex}`}
              type="button"
              role="tab"
              aria-selected={cabinIndex === clampedRoomIndex}
              className={`proposed-cruise-tab${cabinIndex === clampedRoomIndex ? " is-active" : ""}`}
              onClick={() => {
                setActiveRoomIndex(cabinIndex);
                onActiveRoomChange?.();
              }}
            >
              {proposedRoomLabel(cabinIndex, safeCabinsNeeded)}
              {room.room_number.trim() ? ` · ${room.room_number.trim()}` : ""}
            </button>
          ))}
        </div>

        <div className="proposed-cruise-tab-content">
          <div className="proposed-cruise-tab-bar proposed-cruise-tab-bar--sub" role="tablist" aria-label="Room details">
            {ROOM_SUB_TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={tab.id === activeSubTab}
                className={`proposed-cruise-tab proposed-cruise-tab--sub${
                  tab.id === activeSubTab ? " is-active" : ""
                }`}
                onClick={() => setActiveSubTab(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="proposed-cruise-tab-panel">
            {activeSubTab === "room" ? (
              <>
                <div className="field-row field-row--aligned">
                  <label className="field-stack">
                    <span className="field-stack-label">Room category</span>
                    <span className="field-hint field-hint--placeholder" aria-hidden="true">
                      &nbsp;
                    </span>
                    <input
                      required
                      disabled={disabled}
                      value={activeRoom.room_category}
                      onChange={(event) => updateActiveRoom({ room_category: event.target.value })}
                    />
                  </label>
                  <label className="field-stack">
                    <span className="field-stack-label">Room number</span>
                    <span className="field-hint">Use GTY for guaranteed cabin.</span>
                    <input
                      required
                      disabled={disabled}
                      value={activeRoom.room_number}
                      onChange={(event) => updateActiveRoom({ room_number: event.target.value })}
                      placeholder="e.g. GTY"
                    />
                  </label>
                </div>

                <label className="field-stack field-stack--narrow">
                  <span className="field-stack-label">Passengers in room</span>
                  <span className="field-hint field-hint--placeholder" aria-hidden="true">
                    &nbsp;
                  </span>
                  <input
                    required
                    disabled={disabled}
                    type="number"
                    min={1}
                    max={20}
                    value={activeRoom.passengers_in_room}
                    onChange={(event) =>
                      updateActiveRoom({ passengers_in_room: Number(event.target.value) })
                    }
                  />
                </label>

                <div className="field-row field-row--aligned">
                  <label className="field-stack">
                    <span className="field-stack-label">Deposit amount</span>
                    <span className="field-hint field-hint--placeholder" aria-hidden="true">
                      &nbsp;
                    </span>
                    <input
                      required
                      disabled={disabled}
                      type="number"
                      min={0}
                      step="0.01"
                      value={activeRoom.deposit_amount}
                      onChange={(event) =>
                        updateActiveRoom({ deposit_amount: Number(event.target.value) })
                      }
                    />
                  </label>
                  <label className="field-stack">
                    <span className="field-stack-label">Total cost</span>
                    <span className="field-hint field-hint--placeholder" aria-hidden="true">
                      &nbsp;
                    </span>
                    <input
                      required
                      disabled={disabled}
                      type="number"
                      min={0}
                      step="0.01"
                      value={activeRoom.cost}
                      onChange={(event) => updateActiveRoom({ cost: Number(event.target.value) })}
                    />
                  </label>
                </div>

                <div className="field-row field-row--aligned proposed-cruise-commission-row">
                  <label className="field-stack">
                    <span className="field-stack-label">Commission</span>
                    <span className="field-hint field-hint--placeholder" aria-hidden="true">
                      &nbsp;
                    </span>
                    <input
                      disabled={disabled}
                      type="number"
                      min={0}
                      step="0.01"
                      value={activeRoom.commission ?? 0}
                      onChange={(event) =>
                        updateActiveRoom({ commission: Number(event.target.value) })
                      }
                    />
                  </label>
                  <p className="proposed-cruise-commission-percent meta" aria-live="polite">
                    {formatCommissionPercentOfCost(activeRoom.commission ?? 0, activeRoom.cost)}
                  </p>
                </div>

                {showReservationFields ? (
                  <label className="field-stack field-stack--narrow">
                    <span className="field-stack-label">Reservation ID</span>
                    <span className="field-hint">Stored on the request with the accepted cruise.</span>
                    <input
                      type="text"
                      disabled={disabled}
                      value={reservationDrafts[clampedRoomIndex]?.[0] ?? ""}
                      onChange={(event) => updateReservationId(event.target.value)}
                    />
                  </label>
                ) : null}
              </>
            ) : null}

            {activeSubTab === "passengers" ? (
              <ProposedCruiseRoomPassengerFields
                cabinsNeeded={safeCabinsNeeded}
                activeCabinIndex={clampedRoomIndex}
                passengersInRoom={getPassengersInRoomLimits(cabinRooms)}
                passengers={passengers}
                value={roomPassengerIds}
                disabled={disabled}
                onChange={onRoomPassengerIdsChange}
              />
            ) : null}

            {activeSubTab === "includes" ? (
              <ProposedCruiseIncludesFields
                value={activeRoom.includes}
                disabled={disabled}
                onChange={(includes) => updateActiveRoom({ includes })}
              />
            ) : null}

            {!disabled && canSaveRoom ? (
              <div className="proposed-cruise-room-save-row">
                <button
                  type="button"
                  disabled={disabled || savingRoom}
                  onClick={() => onSaveRoom(clampedRoomIndex)}
                >
                  {savingRoom ? "Saving room..." : `Save ${proposedRoomLabel(clampedRoomIndex, safeCabinsNeeded)}`}
                </button>
                {roomSaveMessage ? <p className="status success">{roomSaveMessage}</p> : null}
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  );
}
