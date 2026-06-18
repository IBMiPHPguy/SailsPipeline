import { useMemo, useState } from "react";
import { CRUISE_LINES } from "./formOptions";

type CruiseLineMultiSelectProps = {
  label: string;
  hint?: string;
  value: string[];
  onChange: (value: string[]) => void;
  disabled?: boolean;
  placeholder?: string;
};

const MAX_SUGGESTIONS = 8;

export default function CruiseLineMultiSelect({
  label,
  hint,
  value,
  onChange,
  disabled = false,
  placeholder = "Search cruise lines...",
}: CruiseLineMultiSelectProps) {
  const [query, setQuery] = useState("");

  const suggestions = useMemo(() => {
    const trimmed = query.trim().toLowerCase();
    if (!trimmed) {
      return [];
    }

    return CRUISE_LINES.filter(
      (line) => !value.includes(line) && line.toLowerCase().includes(trimmed),
    ).slice(0, MAX_SUGGESTIONS);
  }, [query, value]);

  function addLine(line: string) {
    if (disabled || value.includes(line)) {
      return;
    }
    onChange([...value, line]);
    setQuery("");
  }

  function removeLine(line: string) {
    if (disabled) {
      return;
    }
    onChange(value.filter((item) => item !== line));
  }

  return (
    <div className="cruise-line-multi-select">
      <span className="field-label">{label}</span>
      {hint ? <span className="field-hint">{hint}</span> : null}

      {value.length > 0 ? (
        <ul className="cruise-line-tags" aria-label={`Selected ${label.toLowerCase()}`}>
          {value.map((line) => (
            <li key={line} className="cruise-line-tag">
              <span>{line}</span>
              {!disabled ? (
                <button
                  type="button"
                  className="cruise-line-tag-remove"
                  aria-label={`Remove ${line}`}
                  onClick={() => removeLine(line)}
                >
                  ×
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}

      <div className="cruise-line-search">
        <input
          type="search"
          disabled={disabled}
          value={query}
          placeholder={placeholder}
          aria-autocomplete="list"
          aria-expanded={suggestions.length > 0}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && suggestions.length > 0) {
              event.preventDefault();
              addLine(suggestions[0]);
            }
          }}
        />

        {suggestions.length > 0 ? (
          <ul className="cruise-line-suggestions" role="listbox">
            {suggestions.map((line) => (
              <li key={line} role="presentation">
                <button type="button" role="option" onClick={() => addLine(line)}>
                  {line}
                </button>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </div>
  );
}

export function formatCruiseLines(lines: string[] | null | undefined): string {
  if (!lines?.length) {
    return "—";
  }
  return lines.join(", ");
}
