import { normalizeCabinPricing, sumCabinPricing } from "./cabinPricing";
import { emptyProposedCruiseIncludes } from "./proposedCruiseForm";
import type { ProposedCruise, ProposedCruiseIncludes, ProposedCruiseRoom } from "./types";

export type CabinRooms = ProposedCruiseRoom[];

type LegacyRoomDefaults = {
  room_category: string;
  room_number: string;
  passengers_in_room: number;
  deposit_amount: number;
  cost: number;
  includes: ProposedCruiseIncludes;
  cabin_pricing?: { deposit_amount: number; cost: number }[];
};

export function cloneProposedCruiseIncludes(includes: ProposedCruiseIncludes): ProposedCruiseIncludes {
  return {
    drink_package: {
      included: includes.drink_package.included,
      name: includes.drink_package.name ?? "",
    },
    wifi: {
      included: includes.wifi.included,
      name: includes.wifi.name ?? "",
    },
    tips: includes.tips,
    excursion: includes.excursion,
    excursion_credit: {
      included: includes.excursion_credit.included,
      amount: includes.excursion_credit.amount ?? null,
    },
    onboard_credit: {
      included: includes.onboard_credit.included,
      amount: includes.onboard_credit.amount ?? null,
    },
    gift_obc: {
      included: includes.gift_obc?.included ?? false,
      amount: includes.gift_obc?.amount ?? null,
    },
  };
}

export function cloneProposedCruiseRoom(room: ProposedCruiseRoom): ProposedCruiseRoom {
  return {
    ...room,
    includes: cloneProposedCruiseIncludes(room.includes),
  };
}

export function normalizeCabinRooms(
  raw: CabinRooms | null | undefined,
  cabinsNeeded: number,
  fallback: LegacyRoomDefaults,
): CabinRooms {
  const safeCabinsNeeded = Math.max(1, cabinsNeeded);
  const pricing = normalizeCabinPricing(fallback.cabin_pricing, safeCabinsNeeded, {
    deposit_amount: fallback.deposit_amount,
    cost: fallback.cost,
  });
  const source = raw ?? [];
  const rooms: CabinRooms = [];

  for (let cabinIndex = 0; cabinIndex < safeCabinsNeeded; cabinIndex += 1) {
    const existing = source[cabinIndex];
    rooms.push({
      room_category: existing?.room_category ?? fallback.room_category,
      room_number: existing?.room_number ?? fallback.room_number,
      passengers_in_room: existing?.passengers_in_room ?? fallback.passengers_in_room,
      deposit_amount: existing?.deposit_amount ?? pricing[cabinIndex].deposit_amount,
      commission: existing?.commission ?? 0,
      cost: existing?.cost ?? pricing[cabinIndex].cost,
      includes: existing?.includes
        ? cloneProposedCruiseIncludes(existing.includes)
        : cloneProposedCruiseIncludes(fallback.includes),
    });
  }

  return rooms;
}

export function proposedCruiseToCabinRooms(cruise: ProposedCruise, cabinsNeeded: number): CabinRooms {
  const includes = cloneProposedCruiseIncludes({
    drink_package: {
      included: cruise.includes.drink_package.included,
      name: cruise.includes.drink_package.name ?? "",
    },
    wifi: {
      included: cruise.includes.wifi.included,
      name: cruise.includes.wifi.name ?? "",
    },
    tips: cruise.includes.tips,
    excursion: cruise.includes.excursion,
    excursion_credit: {
      included: cruise.includes.excursion_credit.included,
      amount: cruise.includes.excursion_credit.amount ?? null,
    },
    onboard_credit: {
      included: cruise.includes.onboard_credit.included,
      amount: cruise.includes.onboard_credit.amount ?? null,
    },
    gift_obc: {
      included: cruise.includes.gift_obc?.included ?? false,
      amount: cruise.includes.gift_obc?.amount ?? null,
    },
  });

  if (cruise.cabin_rooms?.length) {
    return normalizeCabinRooms(
      cruise.cabin_rooms.map((room) => ({
        ...room,
        includes: cloneProposedCruiseIncludes(room.includes),
      })),
      cabinsNeeded,
      {
        room_category: cruise.room_category,
        room_number: cruise.room_number,
        passengers_in_room: cruise.passengers_in_room,
        deposit_amount: cruise.deposit_amount,
        cost: cruise.cost,
        includes,
        cabin_pricing: cruise.cabin_pricing,
      },
    );
  }

  return normalizeCabinRooms([], cabinsNeeded, {
    room_category: cruise.room_category,
    room_number: cruise.room_number,
    passengers_in_room: cruise.passengers_in_room,
    deposit_amount: cruise.deposit_amount,
    cost: cruise.cost,
    includes,
    cabin_pricing: cruise.cabin_pricing,
  });
}

export function emptyCabinRooms(cabinsNeeded: number, passengersInRoom = 2): CabinRooms {
  return normalizeCabinRooms([], cabinsNeeded, {
    room_category: "",
    room_number: "",
    passengers_in_room: passengersInRoom,
    deposit_amount: 0,
    cost: 0,
    includes: emptyProposedCruiseIncludes(),
  });
}

export function updateCabinRoom(
  rooms: CabinRooms,
  cabinIndex: number,
  patch: Partial<ProposedCruiseRoom>,
): CabinRooms {
  return rooms.map((room, index) => {
    if (index !== cabinIndex) {
      return room;
    }

    return {
      ...room,
      ...patch,
      includes: patch.includes ? cloneProposedCruiseIncludes(patch.includes) : room.includes,
    };
  });
}

export function getPassengersInRoomLimits(rooms: CabinRooms): number[] {
  return rooms.map((room) => room.passengers_in_room);
}

export function syncLegacyFieldsFromCabinRooms(rooms: CabinRooms): {
  room_category: string;
  room_number: string;
  passengers_in_room: number;
  deposit_amount: number;
  cost: number;
  includes: ProposedCruiseIncludes;
  cabin_pricing: { deposit_amount: number; cost: number }[];
} {
  const firstRoom = rooms[0];
  const cabinPricing = rooms.map((room) => ({
    deposit_amount: Number(room.deposit_amount || 0),
    cost: Number(room.cost || 0),
  }));
  const totals = sumCabinPricing(cabinPricing);

  return {
    room_category: firstRoom?.room_category ?? "",
    room_number: firstRoom?.room_number ?? "",
    passengers_in_room: firstRoom?.passengers_in_room ?? 2,
    deposit_amount: totals.deposit_amount,
    cost: totals.cost,
    includes: firstRoom?.includes ? cloneProposedCruiseIncludes(firstRoom.includes) : emptyProposedCruiseIncludes(),
    cabin_pricing: cabinPricing,
  };
}

export function sanitizeCabinRoomIncludes(includes: ProposedCruiseIncludes): ProposedCruiseIncludes {
  const excursionAmount =
    includes.excursion_credit.included && includes.excursion_credit.amount != null
      ? Number(includes.excursion_credit.amount)
      : null;
  const onboardAmount =
    includes.onboard_credit.included && includes.onboard_credit.amount != null
      ? Number(includes.onboard_credit.amount)
      : null;
  const giftObcAmount =
    includes.gift_obc?.included && includes.gift_obc.amount != null
      ? Number(includes.gift_obc.amount)
      : null;

  return {
    drink_package: {
      included: includes.drink_package.included,
      name: includes.drink_package.included ? includes.drink_package.name?.trim() || null : null,
    },
    wifi: {
      included: includes.wifi.included,
      name: includes.wifi.included ? includes.wifi.name?.trim() || null : null,
    },
    tips: includes.tips,
    excursion: includes.excursion,
    excursion_credit: {
      included: includes.excursion_credit.included,
      amount: includes.excursion_credit.included ? excursionAmount : null,
    },
    onboard_credit: {
      included: includes.onboard_credit.included,
      amount: includes.onboard_credit.included ? onboardAmount : null,
    },
    gift_obc: {
      included: includes.gift_obc?.included ?? false,
      amount: includes.gift_obc?.included ? giftObcAmount : null,
    },
  };
}

export function formatCommissionPercentOfCost(commission: number, cost: number): string {
  const safeCommission = Number(commission || 0);
  const safeCost = Number(cost || 0);
  if (safeCost <= 0) {
    return safeCommission > 0 ? "—" : "0% of total cost";
  }
  return `${((safeCommission / safeCost) * 100).toFixed(1)}% of total cost`;
}

export function sanitizeCabinRoomsForPayload(rooms: CabinRooms): CabinRooms {
  return rooms.map((room) => ({
    ...room,
    commission: Number(room.commission || 0),
    includes: sanitizeCabinRoomIncludes(room.includes),
  }));
}

export function validateCabinRoom(
  room: ProposedCruiseRoom,
  cabinIndex: number,
  cabinsNeeded: number,
): string | null {
  const label = cabinsNeeded === 1 ? "Room" : `Room ${cabinIndex + 1}`;

  if (!room.room_category.trim()) {
    return `${label}: enter a room category.`;
  }
  if (!room.room_number.trim()) {
    return `${label}: enter a room number.`;
  }
  if (room.includes.excursion_credit.included && room.includes.excursion_credit.amount == null) {
    return `${label}: enter an excursion credit amount.`;
  }
  if (room.includes.onboard_credit.included && room.includes.onboard_credit.amount == null) {
    return `${label}: enter a cruise line OBC amount.`;
  }
  if (room.includes.gift_obc?.included && room.includes.gift_obc.amount == null) {
    return `${label}: enter a gift OBC amount.`;
  }

  return null;
}

export function mergeRoomIntoCabinRooms(
  persistedRooms: CabinRooms,
  draftRooms: CabinRooms,
  cabinIndex: number,
): CabinRooms {
  return persistedRooms.map((room, index) =>
    index === cabinIndex ? cloneProposedCruiseRoom(draftRooms[cabinIndex]) : cloneProposedCruiseRoom(room),
  );
}

export function cloneCabinRooms(rooms: CabinRooms): CabinRooms {
  return rooms.map((room) => cloneProposedCruiseRoom(room));
}
