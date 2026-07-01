import { useEffect, useState } from "react";
import { fetchAgencyGroupMetrics } from "./api";
import type { GroupIntakeDraft } from "./types";

type GroupAmenitiesCardProps = {
  draft: GroupIntakeDraft | null;
};

export default function GroupAmenitiesCard({ draft }: GroupAmenitiesCardProps) {
  const [expanded, setExpanded] = useState(true);
  const [tcMessage, setTcMessage] = useState<string | null>(null);
  const [tcWarning, setTcWarning] = useState(false);

  useEffect(() => {
    if (!draft?.groupId) {
      setTcMessage(null);
      setTcWarning(false);
      return;
    }

    let cancelled = false;
    void fetchAgencyGroupMetrics(draft.groupId)
      .then((metrics) => {
        if (cancelled) {
          return;
        }
        setTcMessage(metrics.tour_conductor.message);
        setTcWarning(metrics.tour_conductor.used_default_ratio);
      })
      .catch(() => {
        if (!cancelled) {
          setTcMessage(null);
          setTcWarning(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [draft?.groupId]);

  if (!draft?.groupAmenities?.trim() && !tcMessage) {
    return null;
  }

  return (
    <section className="group-amenities-card">
      <button
        type="button"
        className="group-amenities-card-toggle"
        aria-expanded={expanded}
        onClick={() => setExpanded((current) => !current)}
      >
        <span>Group block</span>
        <span className="meta">{draft.groupSummary.group_name}</span>
      </button>
      {expanded ? (
        <div className="group-amenities-card-body-wrap">
          {tcMessage ? (
            <p className="group-amenities-card-tc-line">
              {tcMessage}
              {tcWarning ? <span className="group-tc-callout-warning"> Default TC ratio in use.</span> : null}
            </p>
          ) : null}
          {draft.groupAmenities?.trim() ? (
            <p className="group-amenities-card-body">{draft.groupAmenities}</p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
