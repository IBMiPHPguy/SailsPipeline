import { useState } from "react";
import ProposedCruisesSection from "./ProposedCruisesSection";
import QuotedInsuranceSection from "./QuotedInsuranceSection";
import type { ProposedCruise, QuotedInsurance, RequestPassenger } from "./types";

type ProposalsTab = "cruises" | "insurance";

type RequestProposalsSectionProps = {
  requestId: number;
  cabinsNeeded: number;
  cabinHoldReservationIds: string[][];
  cruises: ProposedCruise[];
  quotes: QuotedInsurance[];
  passengers: RequestPassenger[];
  disabled: boolean;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
  allowAcceptProposedCruise?: boolean;
};

export default function RequestProposalsSection({
  requestId,
  cabinsNeeded,
  cabinHoldReservationIds,
  cruises,
  quotes,
  passengers,
  disabled,
  onChanged,
  onError,
  allowAcceptProposedCruise = false,
}: RequestProposalsSectionProps) {
  const [activeTab, setActiveTab] = useState<ProposalsTab>("cruises");

  return (
    <section className="section-card section-tabs-card section-tabs-card--sidebar request-proposals-section">
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

      <div className="section-card-body section-tab-body">
        {activeTab === "cruises" ? (
          <div role="tabpanel" id="proposals-panel-cruises" aria-labelledby="proposals-tab-cruises">
            <ProposedCruisesSection
              embedded
              requestId={requestId}
              cabinsNeeded={cabinsNeeded}
              cabinHoldReservationIds={cabinHoldReservationIds}
              cruises={cruises}
              passengers={passengers}
              disabled={disabled}
              onChanged={onChanged}
              onError={onError}
              allowAcceptProposedCruise={allowAcceptProposedCruise}
            />
          </div>
        ) : (
          <div role="tabpanel" id="proposals-panel-insurance" aria-labelledby="proposals-tab-insurance">
            <QuotedInsuranceSection
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
    </section>
  );
}
