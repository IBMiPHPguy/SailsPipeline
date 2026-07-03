type QuoteMailedToggleProps = {
  value: boolean;
  disabled?: boolean;
  onChange: (mailed: boolean) => void;
};

export default function QuoteMailedToggle({ value, disabled = false, onChange }: QuoteMailedToggleProps) {
  return (
    <div className="quote-mailed-toggle">
      <span className="quote-mailed-toggle-label">Quote mailed to client</span>
      <div
        className="quote-mailed-toggle-track"
        role="group"
        aria-label="Quote mailed to client"
      >
        <button
          type="button"
          className={`quote-mailed-toggle-option${value ? "" : " is-active"}`}
          disabled={disabled}
          aria-pressed={!value}
          onClick={() => onChange(false)}
        >
          Not mailed
        </button>
        <button
          type="button"
          className={`quote-mailed-toggle-option${value ? " is-active" : ""}`}
          disabled={disabled}
          aria-pressed={value}
          onClick={() => onChange(true)}
        >
          Mailed
        </button>
      </div>
    </div>
  );
}

export function QuoteMailedBadge() {
  return <span className="quote-mailed-badge">Mailed</span>;
}
