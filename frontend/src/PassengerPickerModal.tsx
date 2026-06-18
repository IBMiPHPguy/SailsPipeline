import { useEffect, useMemo, useRef, useState } from "react";
import { searchPassengers } from "./api";
import PassengerFields, { emptyPassengerInput, toPassengerPayload } from "./PassengerFields";
import { formatPassengerContact } from "./passengerDisplay";
import type { PassengerProfile, RequestPassengerInput } from "./types";
import { formatDate } from "./utils";

type PassengerPickerModalProps = {
  open: boolean;
  title: string;
  saving: boolean;
  excludePassengerIds?: number[];
  showQualifiers?: boolean;
  newSectionHeading?: string;
  onClose: () => void;
  onAttachExisting: (passenger: PassengerProfile, qualifiers: string[]) => Promise<void>;
  onCreateNew: (payload: RequestPassengerInput) => Promise<void>;
};

export default function PassengerPickerModal({
  open,
  title,
  saving,
  excludePassengerIds = [],
  showQualifiers = false,
  newSectionHeading = "New passenger",
  onClose,
  onAttachExisting,
  onCreateNew,
}: PassengerPickerModalProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PassengerProfile[]>([]);
  const [resultsForQuery, setResultsForQuery] = useState("");
  const [isFetching, setIsFetching] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [newForm, setNewForm] = useState<RequestPassengerInput>(emptyPassengerInput());
  const searchRequestIdRef = useRef(0);

  const trimmedQuery = query.trim();
  const excludingAttached = excludePassengerIds.length > 0;

  const visibleResults = useMemo(
    () => results.filter((passenger) => !excludePassengerIds.includes(passenger.id)),
    [excludePassengerIds, results],
  );

  const resultsAreCurrent = resultsForQuery === trimmedQuery;
  const isPending = Boolean(trimmedQuery) && (isFetching || !resultsAreCurrent);
  const showResults = visibleResults.length > 0;

  const emptyMessage = (() => {
    if (!trimmedQuery || isPending || searchError) {
      return trimmedQuery ? null : "Search by name, email, or phone to find someone already in the system.";
    }
    if (results.length === 0) {
      return "No matching passengers found.";
    }
    if (visibleResults.length === 0 && excludingAttached) {
      return "Matching passengers are already on this request.";
    }
    return null;
  })();

  useEffect(() => {
    if (!open) {
      setQuery("");
      setResults([]);
      setResultsForQuery("");
      setSearchError("");
      setIsFetching(false);
      setNewForm(emptyPassengerInput());
      searchRequestIdRef.current += 1;
      return;
    }

    if (!trimmedQuery) {
      setResults([]);
      setResultsForQuery("");
      setSearchError("");
      setIsFetching(false);
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(() => {
      const requestId = searchRequestIdRef.current + 1;
      searchRequestIdRef.current = requestId;
      setIsFetching(true);
      setSearchError("");

      searchPassengers(trimmedQuery)
        .then((passengers) => {
          if (cancelled || requestId !== searchRequestIdRef.current) {
            return;
          }
          setResults(passengers);
          setResultsForQuery(trimmedQuery);
        })
        .catch((error) => {
          if (cancelled || requestId !== searchRequestIdRef.current) {
            return;
          }
          setSearchError(error instanceof Error ? error.message : "Unable to search passengers.");
          setResults([]);
          setResultsForQuery(trimmedQuery);
        })
        .finally(() => {
          if (cancelled || requestId !== searchRequestIdRef.current) {
            return;
          }
          setIsFetching(false);
        });
    }, 250);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [open, trimmedQuery]);

  if (!open) {
    return null;
  }

  async function handleCreateNew() {
    await onCreateNew(toPassengerPayload(newForm));
  }

  const canCreateNew =
    Boolean(newForm.first_name?.trim()) &&
    Boolean(newForm.last_name?.trim());

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="modal-card modal-card-wide passenger-picker-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="passenger-picker-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="modal-card-header">
          <h3 id="passenger-picker-title">{title}</h3>
        </header>

        <div className="modal-scroll-body passenger-picker-body">
          <label>
            Search existing passenger
            <input
              autoFocus
              type="search"
              disabled={saving}
              value={query}
              placeholder="Name, email, or phone"
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>

          <div className="passenger-search-panel" aria-busy={isPending}>
            {searchError ? <p className="status error">{searchError}</p> : null}
            {emptyMessage ? <p className="meta passenger-picker-empty">{emptyMessage}</p> : null}

            {showResults ? (
              <ul className={`passenger-search-results${isPending ? " is-pending" : ""}`}>
                {visibleResults.map((passenger) => {
              const contact = formatPassengerContact(passenger.email, passenger.phone);
              return (
                  <li key={passenger.id}>
                    <button
                      type="button"
                      className="passenger-search-result"
                      disabled={saving || isPending}
                      onClick={() => void onAttachExisting(passenger, newForm.qualifiers ?? [])}
                    >
                      <span className="passenger-search-result-name">
                        {passenger.first_name} {passenger.last_name}
                      </span>
                      {passenger.date_of_birth ? (
                        <span className="passenger-search-result-meta meta">
                          {formatDate(passenger.date_of_birth)}
                        </span>
                      ) : null}
                      {contact ? (
                        <span className="passenger-search-result-meta meta">{contact}</span>
                      ) : null}
                    </button>
                  </li>
              );
            })}
              </ul>
            ) : null}
          </div>

          <div className="passenger-picker-divider" role="separator" aria-hidden="true" />

          <div className="passenger-picker-new">
            <p className="passenger-picker-new-heading">{newSectionHeading}</p>
            <p className="field-hint">Enter details below to add someone who is not in the system yet.</p>
            <PassengerFields
              value={newForm}
              onChange={setNewForm}
              disabled={saving}
              showQualifiers={showQualifiers}
            />
          </div>
        </div>

        <div className="modal-actions modal-actions-footer">
          <button type="button" className="modal-secondary" disabled={saving} onClick={onClose}>
            Cancel
          </button>
          <button type="button" disabled={saving || !canCreateNew} onClick={() => void handleCreateNew()}>
            {saving ? "Saving..." : "Add new passenger"}
          </button>
        </div>
      </div>
    </div>
  );
}
