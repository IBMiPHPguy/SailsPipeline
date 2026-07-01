import { useEffect, useMemo, useState } from "react";
import { fetchActiveGroupBlocksPicker } from "./api";
import { filterGroupPickerItems, formatGroupPickerLabel } from "./groupIntakeHelpers";
import type { AgencyGroupPickerItem } from "./types";
import { formatDate } from "./utils";

type GroupBlockPickerModalProps = {
  open: boolean;
  onClose: () => void;
  onSelect: (group: AgencyGroupPickerItem) => void;
};

export default function GroupBlockPickerModal({ open, onClose, onSelect }: GroupBlockPickerModalProps) {
  const [groups, setGroups] = useState<AgencyGroupPickerItem[]>([]);
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) {
      setSearchInput("");
      setSearchQuery("");
      setError("");
      return;
    }

    const timer = window.setTimeout(() => setSearchQuery(searchInput.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [open, searchInput]);

  useEffect(() => {
    if (!open) {
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError("");
    void fetchActiveGroupBlocksPicker(searchQuery)
      .then((items) => {
        if (!cancelled) {
          setGroups(items);
        }
      })
      .catch((loadError) => {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Unable to load group blocks.");
          setGroups([]);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [open, searchQuery]);

  const filteredGroups = useMemo(() => filterGroupPickerItems(groups, searchInput), [groups, searchInput]);

  if (!open) {
    return null;
  }

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="modal-card modal-card-wide group-block-picker-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="group-block-picker-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="modal-card-header">
          <h3 id="group-block-picker-title">Choose a group block</h3>
        </header>

        <div className="modal-scroll-body group-block-picker-modal-body">
          <label className="group-block-picker-search">
            Search active group blocks
            <input
              type="search"
              value={searchInput}
              placeholder="Group name, sail date, cruise line, or ship"
              onChange={(event) => setSearchInput(event.target.value)}
            />
          </label>

          {loading ? <p className="meta">Loading group blocks...</p> : null}
          {error ? <p className="status error">{error}</p> : null}

          {!loading && !error && filteredGroups.length === 0 ? (
            <p className="meta">No active group blocks match your search.</p>
          ) : null}

          {!loading && filteredGroups.length > 0 ? (
            <ul className="group-block-picker-list">
              {filteredGroups.map((group) => (
                <li key={group.id}>
                  <button type="button" className="group-block-picker-option" onClick={() => onSelect(group)}>
                    <span className="group-block-picker-option-name">{group.group_name}</span>
                    <span className="meta group-block-picker-option-meta">
                      {group.cruise_line} · {group.ship_name}
                    </span>
                    <span className="meta group-block-picker-option-meta">
                      Sailing {formatDate(group.sailing_date)} – {formatDate(group.disembarkation_date)}
                    </span>
                    <span className="sr-only">{formatGroupPickerLabel(group)}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>

        <div className="modal-actions modal-actions-footer">
          <button type="button" className="modal-secondary" onClick={onClose}>
            Back
          </button>
        </div>
      </div>
    </div>
  );
}
