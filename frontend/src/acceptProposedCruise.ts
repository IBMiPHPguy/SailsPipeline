import { updateProposedCruise } from "./api";
import {
  PROPOSED_CRUISE_STATUS_ACCEPTED,
  PROPOSED_CRUISE_STATUS_PROPOSED,
} from "./formOptions";
import type { ProposedCruise } from "./types";

export function getProposedCruisesAwaitingAcceptance(cruises: ProposedCruise[]): ProposedCruise[] {
  return cruises.filter((cruise) => cruise.status === PROPOSED_CRUISE_STATUS_PROPOSED);
}

export function canQuickAcceptProposedCruise(cruise: ProposedCruise, _cruises: ProposedCruise[]): boolean {
  return cruise.status === PROPOSED_CRUISE_STATUS_PROPOSED;
}

export function canQuickRejectProposedCruise(cruise: ProposedCruise): boolean {
  return cruise.status === PROPOSED_CRUISE_STATUS_PROPOSED;
}

export async function acceptProposedCruiseForRequest(
  requestId: number,
  cruiseId: number,
  cruises: ProposedCruise[],
): Promise<void> {
  const cruise = cruises.find((item) => item.id === cruiseId);
  if (!cruise || cruise.status !== PROPOSED_CRUISE_STATUS_PROPOSED) {
    throw new Error("Only a proposed cruise can be accepted.");
  }

  await updateProposedCruise(requestId, cruiseId, {
    status: PROPOSED_CRUISE_STATUS_ACCEPTED,
  });
}
