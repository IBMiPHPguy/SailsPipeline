type YesNoPillToggleProps = {
  label: string;
  value: boolean;
  disabled?: boolean;
  onChange: (value: boolean) => void;
};

export default function YesNoPillToggle({
  label,
  value,
  disabled = false,
  onChange,
}: YesNoPillToggleProps) {
  return (
    <div className="yes-no-pill-toggle">
      <span className="yes-no-pill-toggle-label">{label}</span>
      <div className="yes-no-pill-toggle-track" role="group" aria-label={label}>
        <button
          type="button"
          className={`yes-no-pill-toggle-option${value ? "" : " is-active"}`}
          disabled={disabled}
          aria-pressed={!value}
          onClick={() => onChange(false)}
        >
          No
        </button>
        <button
          type="button"
          className={`yes-no-pill-toggle-option${value ? " is-active" : ""}`}
          disabled={disabled}
          aria-pressed={value}
          onClick={() => onChange(true)}
        >
          Yes
        </button>
      </div>
    </div>
  );
}
