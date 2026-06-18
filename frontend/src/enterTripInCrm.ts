export type EnterTripInCrmChecklist = {
  create_trip: boolean;
  create_bookings: boolean;
  sent_agency_invoice: boolean;
};

export function readEnterTripInCrmChecklist(
  result: Record<string, unknown> | null | undefined,
): EnterTripInCrmChecklist {
  return {
    create_trip: result?.create_trip === true,
    create_bookings: result?.create_bookings === true,
    sent_agency_invoice: result?.sent_agency_invoice === true,
  };
}

export function isEnterTripInCrmChecklistComplete(checklist: EnterTripInCrmChecklist): boolean {
  return checklist.create_trip && checklist.create_bookings && checklist.sent_agency_invoice;
}
