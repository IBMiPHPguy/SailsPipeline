import type { RequestPassenger } from "./types";

export function isInactiveClient(passenger: Pick<RequestPassenger, "passenger_is_active">): boolean {
  return passenger.passenger_is_active === false;
}

export function inactiveClientLabel(): string {
  return "Inactive client";
}

export function formatPassengerContact(
  email: string | null | undefined,
  phone: string | null | undefined,
): string | null {
  const parts = [email?.trim(), phone?.trim()].filter(Boolean);
  return parts.length > 0 ? parts.join(" · ") : null;
}
