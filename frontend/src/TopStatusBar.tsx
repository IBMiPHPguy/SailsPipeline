import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

export type TopStatusBarVariant = "success" | "delete" | "error";

export type TopStatusBarState = {
  text: string;
  variant: TopStatusBarVariant;
};

type TopStatusBarProps = {
  status: TopStatusBarState | null;
  onDismiss: () => void;
  durationMs?: number;
};

export default function TopStatusBar({ status, onDismiss, durationMs = 5000 }: TopStatusBarProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!status) {
      setVisible(false);
      return;
    }

    setVisible(false);
    const showFrame = window.requestAnimationFrame(() => {
      setVisible(true);
    });

    const hideTimer = window.setTimeout(() => {
      setVisible(false);
    }, durationMs);

    const dismissTimer = window.setTimeout(() => {
      onDismiss();
    }, durationMs + 280);

    return () => {
      window.cancelAnimationFrame(showFrame);
      window.clearTimeout(hideTimer);
      window.clearTimeout(dismissTimer);
    };
  }, [status, durationMs, onDismiss]);

  if (!status) {
    return null;
  }

  return createPortal(
    <div
      className={`top-status-bar top-status-bar--${status.variant}${visible ? " is-visible" : ""}`}
      role="status"
      aria-live="polite"
    >
      <p className="top-status-bar-text">{status.text}</p>
    </div>,
    document.body,
  );
}
