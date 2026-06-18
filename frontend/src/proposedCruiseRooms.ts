import type { ProposedCruise, RequestPassenger } from "./types";

export type RoomPassengerIds = number[][];

function resolvePassengersInRoomLimit(
  passengersInRoom: number | number[],
  cabinIndex: number,
): number {
  if (Array.isArray(passengersInRoom)) {
    return passengersInRoom[cabinIndex] ?? passengersInRoom[passengersInRoom.length - 1] ?? 2;
  }
  return passengersInRoom;
}

export function proposedRoomLabel(cabinIndex: number, cabinsNeeded: number): string {
  return cabinsNeeded === 1 ? "Room" : `Room ${cabinIndex + 1}`;
}

export function normalizeRoomPassengerIds(
  raw: RoomPassengerIds | null | undefined,
  cabinsNeeded: number,
  fallbackPassengerIds: number[] = [],
): RoomPassengerIds {
  const safeCabinsNeeded = Math.max(1, cabinsNeeded);
  const source = raw ?? [];
  const normalized: RoomPassengerIds = [];

  for (let cabinIndex = 0; cabinIndex < safeCabinsNeeded; cabinIndex += 1) {
    const room = source[cabinIndex];
    normalized.push(Array.isArray(room) ? [...room] : []);
  }

  if (normalized.every((room) => room.length === 0) && fallbackPassengerIds.length > 0) {
    normalized[0] = [...fallbackPassengerIds];
  }

  return normalized;
}

export function flattenRoomPassengerIds(roomPassengerIds: RoomPassengerIds): number[] {
  return roomPassengerIds.flat();
}

export function formatPassengerNames(passengers: RequestPassenger[]): string {
  if (passengers.length === 0) {
    return "No passengers assigned";
  }

  return passengers.map((passenger) => `${passenger.first_name} ${passenger.last_name}`.trim()).join(", ");
}

export function getAssignedPassengerIds(roomPassengerIds: RoomPassengerIds): number[] {
  return flattenRoomPassengerIds(roomPassengerIds);
}

export function toggleRoomPassengerId(
  roomPassengerIds: RoomPassengerIds,
  cabinIndex: number,
  passengerId: number,
  passengersInRoom: number | number[],
): RoomPassengerIds {
  const limit = resolvePassengersInRoomLimit(passengersInRoom, cabinIndex);
  const nextRooms = roomPassengerIds.map((room) => [...room]);
  const targetRoom = nextRooms[cabinIndex] ?? [];

  if (targetRoom.includes(passengerId)) {
    nextRooms[cabinIndex] = targetRoom.filter((id) => id !== passengerId);
    return nextRooms;
  }

  for (let index = 0; index < nextRooms.length; index += 1) {
    if (index !== cabinIndex) {
      nextRooms[index] = nextRooms[index].filter((id) => id !== passengerId);
    }
  }

  const clearedTargetRoom = nextRooms[cabinIndex] ?? [];
  if (clearedTargetRoom.length >= limit) {
    return roomPassengerIds;
  }

  nextRooms[cabinIndex] = [...clearedTargetRoom, passengerId];
  return nextRooms;
}

export function validateRoomPassengerIds(
  roomPassengerIds: RoomPassengerIds,
  passengersInRoom: number | number[],
): string | null {
  const flatIds = flattenRoomPassengerIds(roomPassengerIds);
  if (new Set(flatIds).size !== flatIds.length) {
    return "Each passenger can only be assigned to one room.";
  }

  for (let cabinIndex = 0; cabinIndex < roomPassengerIds.length; cabinIndex += 1) {
    const limit = resolvePassengersInRoomLimit(passengersInRoom, cabinIndex);
    if (roomPassengerIds[cabinIndex].length > limit) {
      return `${proposedRoomLabel(cabinIndex, roomPassengerIds.length)} exceeds the passengers-in-room limit.`;
    }
  }

  return null;
}

export function proposedCruiseToRoomPassengerIds(
  cruise: ProposedCruise,
  cabinsNeeded: number,
): RoomPassengerIds {
  if (cruise.room_passengers?.length) {
    return normalizeRoomPassengerIds(
      cruise.room_passengers.map((room) => room.map((passenger) => passenger.id)),
      cabinsNeeded,
    );
  }

  return normalizeRoomPassengerIds([], cabinsNeeded, cruise.passengers.map((passenger) => passenger.id));
}

export function getRoomPassengerNames(
  roomPassengers: RequestPassenger[][] | undefined,
  cabinIndex: number,
): string {
  const passengers = roomPassengers?.[cabinIndex] ?? [];
  return formatPassengerNames(passengers);
}
