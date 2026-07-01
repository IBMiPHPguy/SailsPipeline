import type { AgencyGroupPickerItem, GroupIntakeDraft, TravelRequestGroupBookingInput } from "./types";
import { formatDate } from "./utils";

export function formatGroupPickerLabel(group: AgencyGroupPickerItem): string {
  return `${group.group_name} · ${group.cruise_line} · ${group.ship_name} · ${formatDate(group.sailing_date)}`;
}

export function filterGroupPickerItems(groups: AgencyGroupPickerItem[], query: string): AgencyGroupPickerItem[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    return groups;
  }

  const tokens = normalized.split(/\s+/).filter(Boolean);
  return groups.filter((group) => {
    const haystack = [
      group.group_name,
      group.cruise_line,
      group.ship_name,
      group.sailing_date,
      group.disembarkation_date,
      formatGroupPickerLabel(group),
    ]
      .join(" ")
      .toLowerCase();
    return tokens.every((token) => haystack.includes(token));
  });
}

export function summarizeGroupBookings(
  bookings: TravelRequestGroupBookingInput[],
  labelsByInventoryId: Map<string, string>,
): string {
  if (bookings.length === 0) {
    return "No inventory selected.";
  }
  return bookings
    .map((booking) => {
      const label = labelsByInventoryId.get(booking.group_inventory_id) ?? "Inventory row";
      return `${booking.cabins_requested} × ${label}`;
    })
    .join(" · ");
}

export function buildGroupIntakeDraftSummary(draft: GroupIntakeDraft): string {
  return `${draft.groupSummary.group_name} · ${summarizeGroupBookings(
    draft.bookings,
    new Map(draft.inventoryOptions.map((option) => [option.id, option.label])),
  )}`;
}
