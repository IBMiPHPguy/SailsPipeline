import type { GroupLiquidationTone } from "./types";
import { liquidationToneLabel } from "./groupMetricsHelpers";

type GroupLiquidationBarProps = {
  label: string;
  reserved: number;
  allocated: number;
  percent: number;
  tone: GroupLiquidationTone;
  compact?: boolean;
};

export default function GroupLiquidationBar({
  label,
  reserved,
  allocated,
  percent,
  tone,
  compact = false,
}: GroupLiquidationBarProps) {
  const safeAllocated = Math.max(0, allocated);
  const safeReserved = Math.max(0, Math.min(reserved, safeAllocated || reserved));
  const ariaMax = safeAllocated > 0 ? safeAllocated : Math.max(safeReserved, 1);

  return (
    <div className={`group-liquidation-bar${compact ? " group-liquidation-bar--compact" : ""}`}>
      <div className="group-liquidation-bar-header">
        <span className="group-liquidation-bar-label">{label}</span>
        <span className="group-liquidation-bar-meta">
          {safeReserved}/{safeAllocated || 0} · {percent.toFixed(0)}%
        </span>
      </div>
      <div
        className={`group-liquidation-bar-track group-liquidation-bar-track--${tone}`}
        role="progressbar"
        aria-valuemin={0}
        aria-valuenow={safeReserved}
        aria-valuemax={ariaMax}
        aria-label={`${label}: ${safeReserved} of ${safeAllocated} cabins reserved (${liquidationToneLabel(tone)})`}
      >
        <div className="group-liquidation-bar-fill" style={{ width: `${Math.min(100, percent)}%` }} />
      </div>
    </div>
  );
}
