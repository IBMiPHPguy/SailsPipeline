import { useState } from "react";
import type { GroupIntakeDraft } from "./types";

type GroupAmenitiesCardProps = {
  draft: GroupIntakeDraft | null;
};

export default function GroupAmenitiesCard({ draft }: GroupAmenitiesCardProps) {
  const [expanded, setExpanded] = useState(true);

  if (!draft?.groupAmenities?.trim()) {
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
        <span>Group amenities</span>
        <span className="meta">{draft.groupSummary.group_name}</span>
      </button>
      {expanded ? <p className="group-amenities-card-body">{draft.groupAmenities}</p> : null}
    </section>
  );
}
