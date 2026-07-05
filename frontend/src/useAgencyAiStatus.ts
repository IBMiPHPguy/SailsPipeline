import { useEffect, useState } from "react";
import { fetchAgencyAiStatus, type AgencyAiStatus } from "./agencySettingsApi";

export function useAgencyAiStatus(): {
  aiStatus: AgencyAiStatus | null;
  aiStatusLoading: boolean;
  aiUnavailableMessage: string | null;
} {
  const [aiStatus, setAiStatus] = useState<AgencyAiStatus | null>(null);
  const [aiStatusLoading, setAiStatusLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    fetchAgencyAiStatus()
      .then((status) => {
        if (!cancelled) {
          setAiStatus(status);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setAiStatus(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setAiStatusLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const aiUnavailableMessage =
    aiStatus && aiStatus.uses_tenant_key && !aiStatus.configured
      ? aiStatus.can_manage
        ? "AI is not configured for your agency. Add a Gemini API key in Agency Settings to enable AI features."
        : "AI is not configured for your agency. Ask your agency owner to add a Gemini API key in Agency Settings to enable AI features."
      : null;

  return { aiStatus, aiStatusLoading, aiUnavailableMessage };
}
