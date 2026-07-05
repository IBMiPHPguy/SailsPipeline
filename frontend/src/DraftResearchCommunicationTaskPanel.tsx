import { useMemo, useState } from "react";
import { generateResearchCommunicationFromProposals } from "./api";
import { PROPOSED_CRUISE_STATUS_PROPOSED } from "./formOptions";
import ResearchCommunicationBodyPreview from "./ResearchCommunicationBodyPreview";
import type { GeneratedResearchCommunicationResponse, ProposedCruise } from "./types";
import { copyCommunicationBodyToClipboard, formatDate } from "./utils";
import { useAgencyAiStatus } from "./useAgencyAiStatus";

type DraftResearchCommunicationTaskPanelProps = {
  requestId: number;
  requestWorkflowId: number | null;
  proposedCruises: ProposedCruise[];
  disabled: boolean;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
};

function formatMoney(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(value);
}

function getProposalEmailValidationIssues(cruises: ProposedCruise[]): string[] {
  const proposed = cruises.filter((cruise) => cruise.status === PROPOSED_CRUISE_STATUS_PROPOSED);
  const issues: string[] = [];

  if (proposed.length === 0) {
    issues.push(
      "No proposed cruises in Proposed status were found. Add priced cruise options before drafting the email.",
    );
  }

  for (const cruise of proposed) {
    const label = `${cruise.cruise_line} · ${cruise.ship} (departs ${formatDate(cruise.departure_date)})`;
    if (Number(cruise.cost) <= 0) {
      issues.push(`${label}: cruise cost must be greater than $0.`);
    }
    if (Number(cruise.deposit_amount) <= 0) {
      issues.push(`${label}: deposit amount must be greater than $0.`);
    }
  }

  return issues;
}

function getProposalEmailItineraryWarnings(cruises: ProposedCruise[]): string[] {
  const proposed = cruises.filter((cruise) => cruise.status === PROPOSED_CRUISE_STATUS_PROPOSED);
  const warnings: string[] = [];

  for (const cruise of proposed) {
    if (cruise.itinerary_details?.trim()) {
      continue;
    }
    const label = `${cruise.cruise_line} · ${cruise.ship} (departs ${formatDate(cruise.departure_date)})`;
    warnings.push(
      `${label}: add itinerary details on the proposed cruise (one day/port per line) for an accurate proposal email.`,
    );
  }

  return warnings;
}

export default function DraftResearchCommunicationTaskPanel({
  requestId,
  requestWorkflowId,
  proposedCruises,
  disabled,
  onChanged,
  onError,
}: DraftResearchCommunicationTaskPanelProps) {
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState<GeneratedResearchCommunicationResponse | null>(null);
  const [copyMessage, setCopyMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const { aiUnavailableMessage } = useAgencyAiStatus();
  const aiBlocked = Boolean(aiUnavailableMessage);

  const proposedOptions = useMemo(
    () => proposedCruises.filter((cruise) => cruise.status === PROPOSED_CRUISE_STATUS_PROPOSED),
    [proposedCruises],
  );
  const validationIssues = useMemo(
    () => getProposalEmailValidationIssues(proposedCruises),
    [proposedCruises],
  );
  const itineraryWarnings = useMemo(
    () => getProposalEmailItineraryWarnings(proposedCruises),
    [proposedCruises],
  );
  const canGenerate = validationIssues.length === 0 && !aiBlocked;

  async function handleGenerate() {
    if (!canGenerate) {
      onError(validationIssues.join(" "));
      return;
    }

    setGenerating(true);
    setErrorMessage("");
    onError("");
    try {
      const result = await generateResearchCommunicationFromProposals(requestId, requestWorkflowId);
      setGenerated(result);
      await onChanged();
    } catch (generateError) {
      setGenerated(null);
      const message =
        generateError instanceof Error ? generateError.message : "Unable to generate proposal email.";
      setErrorMessage(message);
      onError(message);
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="draft-research-communication-task-panel">
      <div className="workflow-task-guidance">
        <p>
          AI writes the intro and closing only. Cruise pricing and itinerary come from each proposed cruise. Add
          itinerary details on the proposed cruise before generating for an accurate day-by-day itinerary in the email.
        </p>
      </div>

      {validationIssues.length > 0 ? (
        <div className="status error draft-research-communication-validation">
          <p>Fix these items before generating the email:</p>
          <ul>
            {validationIssues.map((issue) => (
              <li key={issue}>{issue}</li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="workflow-task-guidance">
          <p>
            {proposedOptions.length} proposed cruise{proposedOptions.length === 1 ? "" : "s"} ready for the proposal
            email.
          </p>
        </div>
      )}

      {itineraryWarnings.length > 0 ? (
        <div className="status warning draft-research-communication-validation">
          <p>For the best proposal email, add itinerary details to each proposed cruise:</p>
          <ul>
            {itineraryWarnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {proposedOptions.length > 0 ? (
        <ul className="proposed-cruises-task-result-list">
          {proposedOptions.map((cruise) => (
            <li key={cruise.id}>
              <strong>
                {cruise.cruise_line} · {cruise.ship}
              </strong>
              <div className="meta">
                Departs {formatDate(cruise.departure_date)} · {cruise.number_of_nights} nights · {cruise.itinerary_name}
              </div>
              <div className="meta">
                {cruise.room_category} · Cost {formatMoney(Number(cruise.cost))} · Deposit{" "}
                {formatMoney(Number(cruise.deposit_amount))}
              </div>
            </li>
          ))}
        </ul>
      ) : null}

      {aiUnavailableMessage ? (
        <p className="status warning workflow-task-ai-blocked">{aiUnavailableMessage}</p>
      ) : null}

      {!disabled && !aiBlocked ? (
        <button type="button" disabled={!canGenerate || generating} onClick={() => void handleGenerate()}>
          {generating ? "Generating and saving..." : "Generate proposal email with AI"}
        </button>
      ) : null}

      {errorMessage ? <p className="status error">{errorMessage}</p> : null}

      {generated ? (
        <div className="draft-research-communication-results">
          <p className="status success workflow-task-upload-success">
            Saved in Communications as &ldquo;{generated.subject}&rdquo;. Edit it there before sending to the client.
          </p>
          <label>
            Communication name
            <input type="text" readOnly value={generated.subject} />
          </label>
          <label>
            Suggested email subject
            <input type="text" readOnly value={generated.email_subject} />
          </label>
          <label>
            Email preview
            <ResearchCommunicationBodyPreview body={generated.body} />
          </label>
          <button
            type="button"
            className="modal-secondary"
            onClick={() => {
              setCopyMessage("");
              void copyCommunicationBodyToClipboard(generated.body)
                .then(() => setCopyMessage("Email body copied to clipboard."))
                .catch(() => onError("Unable to copy email body."));
            }}
          >
            Copy formatted email body
          </button>
          {copyMessage ? <p className="status success workflow-task-upload-success">{copyMessage}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
