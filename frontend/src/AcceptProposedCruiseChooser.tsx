import { useEffect, useMemo, useState } from "react";
import { acceptProposedCruiseForRequest, getProposedCruisesAwaitingAcceptance } from "./acceptProposedCruise";
import { formatMoney } from "./cabinPricing";
import type { ProposedCruise } from "./types";
import { formatDate } from "./utils";

type AcceptProposedCruiseChooserProps = {
  requestId: number;
  cruises: ProposedCruise[];
  disabled?: boolean;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
  title?: string;
  intro?: string;
};

export default function AcceptProposedCruiseChooser({
  requestId,
  cruises,
  disabled = false,
  onChanged,
  onError,
  title = "Accept a proposed cruise",
  intro = "Choose a proposed cruise to mark as accepted. You can accept more than one cruise on a request (for example back-to-back or side-by-side sailings).",
}: AcceptProposedCruiseChooserProps) {
  const [selectedCruiseId, setSelectedCruiseId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  const proposedCruisesAwaitingAcceptance = useMemo(
    () => getProposedCruisesAwaitingAcceptance(cruises),
    [cruises],
  );

  useEffect(() => {
    if (proposedCruisesAwaitingAcceptance.length === 0) {
      setSelectedCruiseId(null);
      return;
    }

    setSelectedCruiseId((current) => {
      if (current && proposedCruisesAwaitingAcceptance.some((cruise) => cruise.id === current)) {
        return current;
      }
      return proposedCruisesAwaitingAcceptance[0]?.id ?? null;
    });
  }, [proposedCruisesAwaitingAcceptance]);

  if (proposedCruisesAwaitingAcceptance.length === 0) {
    return null;
  }

  async function handleAccept() {
    if (selectedCruiseId === null) {
      onError("Select a proposed cruise to accept.");
      return;
    }

    setSaving(true);
    onError("");
    try {
      await acceptProposedCruiseForRequest(requestId, selectedCruiseId, cruises);
      await onChanged();
    } catch (acceptError) {
      onError(acceptError instanceof Error ? acceptError.message : "Unable to accept proposed cruise.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="accept-proposed-cruise-chooser">
      <h4 className="accept-proposed-cruise-chooser-title">{title}</h4>
      <p className="meta">{intro}</p>
      <ul className="record-client-response-cruise-list">
        {proposedCruisesAwaitingAcceptance.map((cruise) => (
          <li key={cruise.id}>
            <div className="record-client-response-cruise-summary">
              <strong>
                {cruise.cruise_line} · {cruise.ship}
              </strong>
              <div className="meta">
                Departs {formatDate(cruise.departure_date)} · {cruise.number_of_nights} nights · {cruise.itinerary_name}
              </div>
              <div className="meta">
                {cruise.room_category} · Cost {formatMoney(Number(cruise.cost))}
              </div>
            </div>
            <label className="crm-entry-accept-cruise-choice">
              <input
                type="radio"
                name={`accept-proposed-cruise-${requestId}`}
                checked={selectedCruiseId === cruise.id}
                disabled={disabled || saving}
                onChange={() => setSelectedCruiseId(cruise.id)}
              />
              Accept this cruise
            </label>
          </li>
        ))}
      </ul>
      {!disabled ? (
        <button
          type="button"
          disabled={saving || selectedCruiseId === null}
          onClick={() => void handleAccept()}
        >
          {saving ? "Saving..." : "Mark selected cruise as accepted"}
        </button>
      ) : null}
    </section>
  );
}
