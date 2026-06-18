import { updateProposedCruise } from "./api";
import {
  PROPOSED_CRUISE_STATUS_ACCEPTED,
  PROPOSED_CRUISE_STATUS_PROPOSED,
  PROPOSED_CRUISE_STATUS_REJECTED,
} from "./formOptions";
import type { ProposedCruise } from "./types";

export function getProposedCruisesAwaitingAcceptance(cruises: ProposedCruise[]): ProposedCruise[] {
  return cruises.filter((cruise) => cruise.status === PROPOSED_CRUISE_STATUS_PROPOSED);
}

export async function acceptProposedCruiseForRequest(
  requestId: number,
  cruiseId: number,
  cruises: ProposedCruise[],
): Promise<void> {
  const awaitingAcceptance = getProposedCruisesAwaitingAcceptance(cruises);
  for (const cruise of awaitingAcceptance) {
    await updateProposedCruise(requestId, cruise.id, {
      status: cruise.id === cruiseId ? PROPOSED_CRUISE_STATUS_ACCEPTED : PROPOSED_CRUISE_STATUS_REJECTED,
    });
  }
}
