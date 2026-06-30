import { useCallback, useState } from "react";
import type { TopStatusBarState, TopStatusBarVariant } from "./TopStatusBar";

export function useTopStatusBar() {
  const [status, setStatus] = useState<TopStatusBarState | null>(null);

  const showStatus = useCallback((text: string, variant: TopStatusBarVariant) => {
    setStatus({ text, variant });
  }, []);

  const clearStatus = useCallback(() => {
    setStatus(null);
  }, []);

  return { status, showStatus, clearStatus };
}
