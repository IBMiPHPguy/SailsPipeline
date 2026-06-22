import { BRAND_NAME } from "./branding";
import { formatMoney } from "./cabinPricing";
import { proposedCruiseReservationIds } from "./cabinHoldReservations";
import { proposedCruiseToCabinRooms } from "./cabinRooms";
import {
  PROPOSED_CRUISE_STATUS_ACCEPTED,
  PROPOSED_CRUISE_STATUS_DEPOSITED,
} from "./formOptions";
import { proposedRoomLabel } from "./proposedCruiseRooms";
import type { ProposedCruise, ProposedCruiseIncludes, RequestPassenger, TravelRequestDetail, TravelRequestInput } from "./types";
import { formatDate } from "./utils";

function displayValue(value: string | null | undefined): string {
  const trimmed = value?.trim();
  return trimmed ? trimmed : "—";
}

function line(label: string, value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return `${label}: —`;
  }
  return `${label}: ${value}`;
}

export function formatProposedCruiseIncludes(includes: ProposedCruiseIncludes): string[] {
  const lines: string[] = [];

  if (includes.drink_package.included) {
    lines.push(`Drink package${includes.drink_package.name?.trim() ? `: ${includes.drink_package.name.trim()}` : ""}`);
  }
  if (includes.wifi.included) {
    lines.push(`Wi-Fi${includes.wifi.name?.trim() ? `: ${includes.wifi.name.trim()}` : ""}`);
  }
  if (includes.tips) {
    lines.push("Gratuities / tips included");
  }
  if (includes.excursion) {
    lines.push("Shore excursion included");
  }
  if (includes.excursion_credit.included) {
    lines.push(`Excursion credit: ${formatMoney(Number(includes.excursion_credit.amount ?? 0))}`);
  }
  if (includes.onboard_credit.included) {
    lines.push(`Cruise line OBC: ${formatMoney(Number(includes.onboard_credit.amount ?? 0))}`);
  }
  if (includes.gift_obc?.included) {
    lines.push(`Gift OBC: ${formatMoney(Number(includes.gift_obc.amount ?? 0))}`);
  }

  return lines.length > 0 ? lines : ["No extra inclusions recorded"];
}

export function getDepositedProposedCruises(cruises: ProposedCruise[]): ProposedCruise[] {
  return cruises.filter((cruise) => cruise.status === PROPOSED_CRUISE_STATUS_DEPOSITED);
}

export function hasAcceptedOrDepositedProposedCruise(cruises: ProposedCruise[]): boolean {
  return cruises.some(
    (cruise) =>
      cruise.status === PROPOSED_CRUISE_STATUS_ACCEPTED ||
      cruise.status === PROPOSED_CRUISE_STATUS_DEPOSITED,
  );
}

export function getCrmEntryProposedCruises(cruises: ProposedCruise[]): ProposedCruise[] {
  return cruises.filter(
    (cruise) =>
      cruise.status === PROPOSED_CRUISE_STATUS_ACCEPTED ||
      cruise.status === PROPOSED_CRUISE_STATUS_DEPOSITED,
  );
}

export function buildPassengerDetailLines(passenger: RequestPassenger): string[] {
  return [
    line("Role", passenger.is_primary ? "Primary passenger" : "Additional passenger"),
    line("First name", passenger.first_name),
    line("Last name", passenger.last_name),
    line("Email", passenger.email),
    line("Phone", passenger.phone),
    line("Date of birth", passenger.date_of_birth ? formatDate(passenger.date_of_birth) : null),
    line("Address line 1", displayValue(passenger.address_line_1)),
    line("Address line 2", displayValue(passenger.address_line_2)),
    line("City", displayValue(passenger.city)),
    line("State / province", displayValue(passenger.state_or_province)),
    line("Postal code", displayValue(passenger.postal_code)),
    line("Country", displayValue(passenger.country)),
    line(
      "Qualifying discounts",
      passenger.qualifiers?.length ? passenger.qualifiers.join(", ") : null,
    ),
  ];
}

export function buildCrmEntrySummaryText(
  request: TravelRequestDetail,
  form: TravelRequestInput,
): string {
  const bookingCruises = getCrmEntryProposedCruises(request.proposed_cruises);
  const cabinsNeeded = Math.max(1, form.cabins_needed ?? request.cabins_needed ?? 1);

  const sections: string[] = [
    `${BRAND_NAME} — CRM Entry Summary`,
    line("Request", `#${request.id}`),
    "",
    "REQUEST",
    line("Client", `${form.first_name} ${form.last_name}`.trim()),
    line("Email", form.email),
    line("Phone", form.phone),
    line("Passenger count", form.passengers),
    line("Cabins needed", cabinsNeeded),
    "",
    "BOOKING DETAILS",
  ];

  if (bookingCruises.length === 0) {
    sections.push("  (none — accept a proposed cruise first)");
  }

  for (const cruise of bookingCruises) {
    const cabinRooms = proposedCruiseToCabinRooms(cruise, cabinsNeeded);
    const reservations = proposedCruiseReservationIds(cruise, cabinsNeeded);
    sections.push(
      "",
      `${cruise.cruise_line} · ${cruise.ship}`,
      line("Status", cruise.status),
      line("Departure", formatDate(cruise.departure_date)),
      line("Nights", cruise.number_of_nights),
      line("Itinerary", cruise.itinerary_name),
      line("Deposit due", formatDate(cruise.deposit_due_date)),
      line("Final payment due", formatDate(cruise.final_payment_due_date)),
      line("Total cost", formatMoney(cruise.cost)),
    );

    cabinRooms.forEach((room, cabinIndex) => {
      const cabinLabel = proposedRoomLabel(cabinIndex, cabinsNeeded);
      const reservationIds = (reservations[cabinIndex] ?? []).map((value) => value.trim()).filter(Boolean);
      const roomPassengers = cruise.room_passengers?.[cabinIndex] ?? [];

      sections.push("", cabinLabel.toUpperCase());
      sections.push(line("Category", room.room_category));
      sections.push(line("Room number", room.room_number));
      sections.push(line("Deposit", formatMoney(room.deposit_amount)));
      sections.push(line("Commission", formatMoney(room.commission ?? 0)));
      sections.push(line("Total cost", formatMoney(room.cost)));
      sections.push(line("Passengers in room", room.passengers_in_room));
      sections.push(line("Reservation IDs", reservationIds.length > 0 ? reservationIds.join(", ") : null));
      sections.push("Includes:");
      formatProposedCruiseIncludes(room.includes).forEach((includeLine) => {
        sections.push(`  - ${includeLine}`);
      });

      if (roomPassengers.length === 0) {
        sections.push("Passengers:", "  (none assigned to this room)");
      } else {
        roomPassengers.forEach((passenger, passengerIndex) => {
          sections.push(`Passenger ${passengerIndex + 1}:`);
          buildPassengerDetailLines(passenger).forEach((detailLine) => {
            sections.push(`  ${detailLine}`);
          });
        });
      }
    });
  }

  return sections.join("\n");
}
