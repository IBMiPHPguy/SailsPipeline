import { useMemo } from "react";
import { CRUISE_LINES } from "./formOptions";

export type CruiseLoyaltyNumberInput = {
  cruise_line: string;
  loyalty_number: string;
};

type CruiseLineLoyaltyFieldsProps = {
  value: CruiseLoyaltyNumberInput[];
  onChange: (value: CruiseLoyaltyNumberInput[]) => void;
  disabled?: boolean;
};

function emptyEntry(): CruiseLoyaltyNumberInput {
  return { cruise_line: "", loyalty_number: "" };
}

export default function CruiseLineLoyaltyFields({
  value,
  onChange,
  disabled = false,
}: CruiseLineLoyaltyFieldsProps) {
  const entries = value.length > 0 ? value : [];

  const usedLines = useMemo(
    () => new Set(entries.map((entry) => entry.cruise_line).filter(Boolean)),
    [entries],
  );

  function updateEntry(index: number, patch: Partial<CruiseLoyaltyNumberInput>) {
    const next = entries.map((entry, entryIndex) =>
      entryIndex === index ? { ...entry, ...patch } : entry,
    );
    onChange(next);
  }

  function removeEntry(index: number) {
    onChange(entries.filter((_, entryIndex) => entryIndex !== index));
  }

  function addEntry() {
    onChange([...entries, emptyEntry()]);
  }

  return (
    <fieldset className="cruise-loyalty-fields">
      <legend className="field-label">Cruise line loyalty numbers</legend>
      <p className="field-hint">
        Add one loyalty number per cruise line. These follow the passenger across all requests.
      </p>

      {entries.length === 0 ? (
        <p className="meta">No loyalty numbers saved yet.</p>
      ) : (
        <div className="cruise-loyalty-list">
          {entries.map((entry, index) => (
            <div className="cruise-loyalty-row" key={`loyalty-${index}`}>
              <label>
                Cruise line
                <select
                  disabled={disabled}
                  value={entry.cruise_line}
                  onChange={(event) => updateEntry(index, { cruise_line: event.target.value })}
                >
                  <option value="">Select cruise line</option>
                  {CRUISE_LINES.map((line) => (
                    <option
                      key={line}
                      value={line}
                      disabled={usedLines.has(line) && entry.cruise_line !== line}
                    >
                      {line}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Loyalty number
                <input
                  type="text"
                  disabled={disabled}
                  value={entry.loyalty_number}
                  onChange={(event) => updateEntry(index, { loyalty_number: event.target.value })}
                  placeholder="Enter loyalty number"
                />
              </label>

              {!disabled ? (
                <button
                  type="button"
                  className="modal-secondary cruise-loyalty-remove"
                  onClick={() => removeEntry(index)}
                >
                  Remove
                </button>
              ) : null}
            </div>
          ))}
        </div>
      )}

      {!disabled ? (
        <button type="button" className="modal-secondary cruise-loyalty-add" onClick={addEntry}>
          Add loyalty number
        </button>
      ) : null}
    </fieldset>
  );
}

export function normalizeCruiseLoyaltyNumbers(
  entries: CruiseLoyaltyNumberInput[],
): CruiseLoyaltyNumberInput[] {
  return entries
    .map((entry) => ({
      cruise_line: entry.cruise_line.trim(),
      loyalty_number: entry.loyalty_number.trim(),
    }))
    .filter((entry) => entry.cruise_line && entry.loyalty_number);
}
