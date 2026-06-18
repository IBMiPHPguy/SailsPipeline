import type { ReactNode } from "react";

type IconTooltipProps = {
  label: string;
  children: ReactNode;
  placement?: "above" | "below";
  wide?: boolean;
  align?: "center" | "start";
};

export default function IconTooltip({
  label,
  children,
  placement = "above",
  wide = false,
  align = "center",
}: IconTooltipProps) {
  const popoverClassName = [
    "icon-tooltip-popover",
    placement === "below" ? "icon-tooltip-popover-below" : null,
    wide ? "icon-tooltip-popover-wide" : null,
    align === "start" ? "icon-tooltip-popover-align-start" : null,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <span className="icon-tooltip">
      {children}
      <span className={popoverClassName} role="tooltip">
        {label}
      </span>
    </span>
  );
}
