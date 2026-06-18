import {
  emptyCabinRooms,
  normalizeCabinRooms,
  proposedCruiseToCabinRooms,
  sanitizeCabinRoomsForPayload,
  syncLegacyFieldsFromCabinRooms,
} from "./cabinRooms";
import { normalizeCruiseLineValue } from "./formOptions";
import type { ProposedCruise, ProposedCruiseIncludes, ProposedCruiseInput } from "./types";
import {
  flattenRoomPassengerIds,
  normalizeRoomPassengerIds,
  proposedCruiseToRoomPassengerIds,
} from "./proposedCruiseRooms";

export function emptyProposedCruiseIncludes(): ProposedCruiseIncludes {
  return {
    drink_package: { included: false, name: "" },
    wifi: { included: false, name: "" },
    tips: false,
    excursion: false,
    excursion_credit: { included: false, amount: null },
    onboard_credit: { included: false, amount: null },
    gift_obc: { included: false, amount: null },
  };
}

export const emptyProposedCruiseForm: ProposedCruiseInput = {
  departure_date: "",
  cruise_line: "",
  ship: "",
  number_of_nights: 7,
  itinerary_name: "",
  itinerary_details: "",
  room_category: "",
  room_number: "",
  passengers_in_room: 2,
  deposit_amount: 0,
  deposit_due_date: "",
  final_payment_due_date: "",
  cost: 0,
  includes: emptyProposedCruiseIncludes(),
  room_passenger_ids: [[]],
  passenger_ids: [],
  cabin_rooms: emptyCabinRooms(1),
};

export function proposedCruiseToForm(cruise: ProposedCruise, cabinsNeeded = 1): ProposedCruiseInput {
  const roomPassengerIds = proposedCruiseToRoomPassengerIds(cruise, cabinsNeeded);
  const cabinRooms = proposedCruiseToCabinRooms(cruise, cabinsNeeded);
  const legacy = syncLegacyFieldsFromCabinRooms(cabinRooms);

  return {
    departure_date: cruise.departure_date,
    cruise_line: normalizeCruiseLineValue(cruise.cruise_line),
    ship: cruise.ship,
    number_of_nights: cruise.number_of_nights,
    itinerary_name: cruise.itinerary_name,
    itinerary_details: cruise.itinerary_details ?? "",
    room_category: legacy.room_category,
    room_number: legacy.room_number,
    passengers_in_room: legacy.passengers_in_room,
    deposit_amount: legacy.deposit_amount,
    deposit_due_date: cruise.deposit_due_date,
    final_payment_due_date: cruise.final_payment_due_date,
    cost: legacy.cost,
    includes: legacy.includes,
    room_passenger_ids: roomPassengerIds,
    passenger_ids: flattenRoomPassengerIds(roomPassengerIds),
    cabin_pricing: legacy.cabin_pricing,
    cabin_rooms: cabinRooms,
    status: cruise.status,
  };
}

export function buildProposedCruisePayload(form: ProposedCruiseInput, cabinsNeeded = 1): ProposedCruiseInput {
  const cabinRooms = sanitizeCabinRoomsForPayload(
    normalizeCabinRooms(form.cabin_rooms, cabinsNeeded, {
      room_category: form.room_category,
      room_number: form.room_number,
      passengers_in_room: form.passengers_in_room,
      deposit_amount: form.deposit_amount,
      cost: form.cost,
      includes: form.includes,
      cabin_pricing: form.cabin_pricing,
    }),
  );
  const legacy = syncLegacyFieldsFromCabinRooms(cabinRooms);
  const roomPassengerIds = normalizeRoomPassengerIds(form.room_passenger_ids, cabinsNeeded);

  return {
    ...form,
    itinerary_details: form.itinerary_details?.trim() || null,
    room_category: legacy.room_category,
    room_number: legacy.room_number,
    passengers_in_room: legacy.passengers_in_room,
    deposit_amount: legacy.deposit_amount,
    cost: legacy.cost,
    includes: legacy.includes,
    cabin_pricing: legacy.cabin_pricing,
    cabin_rooms: cabinRooms,
    room_passenger_ids: roomPassengerIds,
    passenger_ids: flattenRoomPassengerIds(roomPassengerIds),
  };
}

export function proposedCruiseStatusClass(status: string): string {
  if (status === "Accepted") {
    return "proposed-cruise-status-accepted";
  }
  if (status === "Deposited") {
    return "proposed-cruise-status-deposited";
  }
  if (status === "Rejected") {
    return "proposed-cruise-status-rejected";
  }
  return "proposed-cruise-status-proposed";
}

export function proposedCruiseStatusOptionClass(status: string): string {
  if (status === "Accepted") {
    return "status-option-accepted";
  }
  if (status === "Deposited") {
    return "status-option-deposited";
  }
  if (status === "Rejected") {
    return "status-option-declined";
  }
  return "status-option-proposed";
}
