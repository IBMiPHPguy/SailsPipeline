import { useMemo, useRef, useState } from "react";
import {
  QUOTED_INSURANCE_STATUS_ACCEPTED,
} from "./formOptions";
import ProposedCruisesSection, { type ProposedCruisesSectionHandle } from "./ProposedCruisesSection";
import QuotedInsuranceSection, { type QuotedInsuranceSectionHandle } from "./QuotedInsuranceSection";
import TabHeaderAddButton from "./TabHeaderAddButton";
import type { ProposedCruise, QuotedInsurance, RequestPassenger } from "./types";

type ProposalsTab = "cruises" | "insurance";

type RequestProposalsSectionProps = {
  requestId: number;
  cabinsNeeded: number;
  cruises: ProposedCruise[];
  quotes: QuotedInsurance[];
  passengers: RequestPassenger[];
  requestPassengerCount: number;
  disabled: boolean;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
  allowAcceptProposedCruise?: boolean;
  embeddedInWorkspace?: boolean;
};

export default function RequestProposalsSection({
  requestId,
  cabinsNeeded,
  cruises,
  quotes,
  passengers,
  requestPassengerCount,
  disabled,
  onChanged,
  onError,
  allowAcceptProposedCruise = false,
  embeddedInWorkspace = false,
}: RequestProposalsSectionProps) {
  const [activeTab, setActiveTab] = useState<ProposalsTab>("cruises");
  const cruisesSectionRef = useRef<ProposedCruisesSectionHandle>(null);
  const insuranceSectionRef = useRef<QuotedInsuranceSectionHandle>(null);

  const canAddCruise = useMemo(() => !disabled, [disabled]);

  const canAddInsurance = useMemo(
    () => !disabled && !quotes.some((quote) => quote.status === QUOTED_INSURANCE_STATUS_ACCEPTED),
    [disabled, quotes],
  );

  const rootClassName = embeddedInWorkspace
    ? "workspace-nested-tabs request-proposals-section"
    : "section-card section-tabs-card section-tabs-card--sidebar request-proposals-section";

  return (
    <div className={rootClassName}>
      <div className="proposals-tab-header">
        <div className="section-tablist" role="tablist" aria-label="Proposals and insurance">
          <button
            type="button"
            role="tab"
            id="proposals-tab-cruises"
            aria-selected={activeTab === "cruises"}
            aria-controls="proposals-panel-cruises"
            className={`section-tab${activeTab === "cruises" ? " is-active" : ""}`}
            onClick={() => setActiveTab("cruises")}
          >
            Proposed cruises ({cruises.length})
          </button>
          <button
            type="button"
            role="tab"
            id="proposals-tab-insurance"
            aria-selected={activeTab === "insurance"}
            aria-controls="proposals-panel-insurance"
            className={`section-tab${activeTab === "insurance" ? " is-active" : ""}`}
            onClick={() => setActiveTab("insurance")}
          >
            Quoted insurance ({quotes.length})
          </button>
        </div>

        {activeTab === "cruises" && canAddCruise ? (
          <TabHeaderAddButton
            label="Add Cruise"
            onClick={() => cruisesSectionRef.current?.openCreateModal()}
          />
        ) : null}

        {activeTab === "insurance" && canAddInsurance ? (
          <TabHeaderAddButton
            label="Add Insurance"
            onClick={() => insuranceSectionRef.current?.openCreateModal()}
          />
        ) : null}
      </div>

      <div className="section-card-body section-tab-body">
        {activeTab === "cruises" ? (
          <div role="tabpanel" id="proposals-panel-cruises" aria-labelledby="proposals-tab-cruises">
            <ProposedCruisesSection
              ref={cruisesSectionRef}
              embedded
              requestId={requestId}
              cabinsNeeded={cabinsNeeded}
              cruises={cruises}
              passengers={passengers}
              requestPassengerCount={requestPassengerCount}
              disabled={disabled}
              onChanged={onChanged}
              onError={onError}
              allowAcceptProposedCruise={allowAcceptProposedCruise}
            />
          </div>
        ) : (
          <div role="tabpanel" id="proposals-panel-insurance" aria-labelledby="proposals-tab-insurance">
            <QuotedInsuranceSection
              ref={insuranceSectionRef}
              embedded
              requestId={requestId}
              quotes={quotes}
              disabled={disabled}
              onChanged={onChanged}
              onError={onError}
            />
          </div>
        )}
      </div>
    </div>
  );
}
