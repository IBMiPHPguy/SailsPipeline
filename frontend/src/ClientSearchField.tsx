import { useEffect, useMemo, useRef, useState } from "react";
import { searchPassengers } from "./api";
import { formatPassengerContact } from "./passengerDisplay";
import type { PassengerProfile } from "./types";
import { formatDate } from "./utils";

type ClientSearchFieldProps = {
  disabled?: boolean;
  linkedClientId?: number;
  onSelect: (client: PassengerProfile) => void;
  onClearLink?: () => void;
};

export default function ClientSearchField({
  disabled = false,
  linkedClientId,
  onSelect,
  onClearLink,
}: ClientSearchFieldProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PassengerProfile[]>([]);
  const [resultsForQuery, setResultsForQuery] = useState("");
  const [isFetching, setIsFetching] = useState(false);
  const [searchError, setSearchError] = useState("");
  const searchRequestIdRef = useRef(0);

  const trimmedQuery = query.trim();
  const resultsAreCurrent = resultsForQuery === trimmedQuery;
  const isPending = Boolean(trimmedQuery) && (isFetching || !resultsAreCurrent);
  const showResults = results.length > 0 && trimmedQuery.length > 0;

  const emptyMessage = useMemo(() => {
    if (!trimmedQuery || isPending || searchError) {
      return trimmedQuery ? null : "Search by name, email, or phone to find an existing client.";
    }
    if (results.length === 0) {
      return "No matching clients found.";
    }
    return null;
  }, [isPending, results.length, searchError, trimmedQuery]);

  useEffect(() => {
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
          setSearchError(error instanceof Error ? error.message : "Unable to search clients.");
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
  }, [trimmedQuery]);

  function handleSelect(client: PassengerProfile) {
    onSelect(client);
    setQuery("");
    setResults([]);
    setResultsForQuery("");
    setSearchError("");
  }

  return (
    <div className="client-search-field">
      <label>
        Find existing client
        <input
          type="search"
          disabled={disabled}
          value={query}
          placeholder="Name, email, or phone"
          onChange={(event) => setQuery(event.target.value)}
        />
      </label>

      {linkedClientId ? (
        <div className="client-search-linked">
          <p className="field-hint">
            Linked to client record #{linkedClientId}. Contact fields below were filled from this client.
          </p>
          {onClearLink ? (
            <button type="button" className="modal-secondary" disabled={disabled} onClick={onClearLink}>
              Clear linked client
            </button>
          ) : null}
        </div>
      ) : (
        <p className="field-hint">
          The requestor is the primary passenger. Select a client to auto-fill contact details and link them on create.
        </p>
      )}

      <div className="passenger-search-panel" aria-busy={isPending}>
        {searchError ? <p className="status error">{searchError}</p> : null}
        {emptyMessage ? <p className="meta passenger-picker-empty">{emptyMessage}</p> : null}

        {showResults ? (
          <ul className={`passenger-search-results${isPending ? " is-pending" : ""}`}>
            {results.map((client) => {
              const contact = formatPassengerContact(client.email, client.phone);
              return (
                <li key={client.id}>
                  <button
                    type="button"
                    className="passenger-search-result"
                    disabled={disabled || isPending}
                    onClick={() => handleSelect(client)}
                  >
                    <span className="passenger-search-result-name">
                      {client.first_name} {client.last_name}
                    </span>
                    {client.date_of_birth ? (
                      <span className="passenger-search-result-meta meta">{formatDate(client.date_of_birth)}</span>
                    ) : null}
                    {contact ? <span className="passenger-search-result-meta meta">{contact}</span> : null}
                  </button>
                </li>
              );
            })}
          </ul>
        ) : null}
      </div>
    </div>
  );
}
