import { CRUISE_LINES } from "./formOptions";

type CruiseLineSelectProps = {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  required?: boolean;
  id?: string;
};

export default function CruiseLineSelect({
  value,
  onChange,
  disabled = false,
  required = false,
  id,
}: CruiseLineSelectProps) {
  const knownLines = CRUISE_LINES as readonly string[];
  const showLegacyOption = Boolean(value) && !knownLines.includes(value);

  return (
    <select
      id={id}
      required={required}
      disabled={disabled}
      value={value}
      onChange={(event) => onChange(event.target.value)}
    >
      <option value="" disabled>
        Select a cruise line
      </option>
      {showLegacyOption ? (
        <option value={value}>{value}</option>
      ) : null}
      {CRUISE_LINES.map((line) => (
        <option key={line} value={line}>
          {line}
        </option>
      ))}
    </select>
  );
}
