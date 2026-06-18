import { useEffect, useState } from "react";
import { fetchResearchDocumentContent, generateProposedCruisesFromResearch, addProposedCruisesBulk } from "./api";
import type { GeneratedProposedCruisesResponse, ProposedCruiseInput, ResearchDocument } from "./types";
import { formatDate, formatFileSize } from "./utils";

type ProposedCruisesTaskPanelProps = {
  requestId: number;
  researchDocuments: ResearchDocument[];
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

export default function ProposedCruisesTaskPanel({
  requestId,
  researchDocuments,
  disabled,
  onChanged,
  onError,
}: ProposedCruisesTaskPanelProps) {
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | "">("");
  const [documentPreview, setDocumentPreview] = useState("");
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [generated, setGenerated] = useState<GeneratedProposedCruisesResponse | null>(null);
  const [addedMessage, setAddedMessage] = useState<string | null>(null);

  useEffect(() => {
    if (researchDocuments.length === 0) {
      setSelectedDocumentId("");
      setDocumentPreview("");
      return;
    }
    setSelectedDocumentId((current) => current || researchDocuments[0].id);
  }, [researchDocuments]);

  useEffect(() => {
    if (!selectedDocumentId || typeof selectedDocumentId !== "number") {
      setDocumentPreview("");
      return;
    }

    let cancelled = false;
    setLoadingPreview(true);
    setGenerated(null);
    setAddedMessage(null);

    fetchResearchDocumentContent(requestId, selectedDocumentId)
      .then((content) => {
        if (!cancelled) {
          setDocumentPreview(content);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setDocumentPreview("");
          onError(error instanceof Error ? error.message : "Unable to load research document.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingPreview(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [requestId, selectedDocumentId]);

  async function handleGenerate() {
    if (typeof selectedDocumentId !== "number") {
      return;
    }

    setGenerating(true);
    onError("");
    setAddedMessage(null);
    try {
      const result = await generateProposedCruisesFromResearch(requestId, selectedDocumentId);
      setGenerated(result);
    } catch (generateError) {
      setGenerated(null);
      onError(generateError instanceof Error ? generateError.message : "Unable to generate proposed cruises.");
    } finally {
      setGenerating(false);
    }
  }

  async function handleAddGenerated() {
    if (!generated || generated.cruises.length === 0) {
      return;
    }

    setSaving(true);
    onError("");
    try {
      await addProposedCruisesBulk(requestId, generated.cruises as ProposedCruiseInput[]);
      setAddedMessage(
        `${generated.cruises.length} proposed cruise${generated.cruises.length === 1 ? "" : "s"} added to the request.`,
      );
      setGenerated(null);
      await onChanged();
    } catch (saveError) {
      onError(saveError instanceof Error ? saveError.message : "Unable to add proposed cruises.");
    } finally {
      setSaving(false);
    }
  }

  if (researchDocuments.length === 0) {
    return (
      <div className="workflow-task-guidance">
        <p>Upload a research document first, then return here to generate proposed cruises with AI.</p>
      </div>
    );
  }

  const selectedDocument = researchDocuments.find((document) => document.id === selectedDocumentId);

  return (
    <div className="proposed-cruises-task-panel">
      <div className="workflow-task-guidance">
        <p>Review the research document below, then use Gemini to extract proposed cruise options.</p>
      </div>

      <label>
        Research document
        <select
          disabled={disabled || generating || saving}
          value={selectedDocumentId}
          onChange={(event) => setSelectedDocumentId(Number(event.target.value))}
        >
          {researchDocuments.map((document) => (
            <option key={document.id} value={document.id}>
              {document.original_filename}
            </option>
          ))}
        </select>
      </label>

      {selectedDocument ? (
        <p className="meta proposed-cruises-task-doc-meta">
          {formatFileSize(selectedDocument.size_bytes)} · Uploaded by {selectedDocument.uploaded_by.username}
        </p>
      ) : null}

      <div className="proposed-cruises-task-preview">
        {loadingPreview ? <p className="meta">Loading document...</p> : null}
        {!loadingPreview && documentPreview ? (
          <pre className="attachment-reader-content">{documentPreview}</pre>
        ) : null}
        {!loadingPreview && !documentPreview ? <p className="meta">No preview available.</p> : null}
      </div>

      {!disabled ? (
        <button
          type="button"
          disabled={generating || saving || loadingPreview || typeof selectedDocumentId !== "number"}
          onClick={() => void handleGenerate()}
        >
          {generating ? "Generating with AI..." : "Generate proposed cruises with AI"}
        </button>
      ) : null}

      {addedMessage ? <p className="status success workflow-task-upload-success">{addedMessage}</p> : null}

      {generated ? (
        <div className="proposed-cruises-task-results">
          <div className="workflow-task-guidance">
            <p>
              Gemini found {generated.cruises.length} option{generated.cruises.length === 1 ? "" : "s"} in{" "}
              {generated.research_document_filename}. Review them before adding to the request.
            </p>
          </div>
          <ul className="proposed-cruises-task-result-list">
            {generated.cruises.map((cruise, index) => (
              <li key={`${cruise.ship}-${cruise.departure_date}-${index}`}>
                <strong>
                  {cruise.cruise_line} · {cruise.ship}
                </strong>
                <div className="meta">
                  Departs {formatDate(cruise.departure_date)} · {cruise.number_of_nights} nights · {cruise.itinerary_name}
                </div>
                <div className="meta">
                  {cruise.room_category} · Room {cruise.room_number} · {formatMoney(Number(cruise.cost))}
                </div>
              </li>
            ))}
          </ul>
          {!disabled ? (
            <button type="button" disabled={saving || generating} onClick={() => void handleAddGenerated()}>
              {saving ? "Adding..." : `Add ${generated.cruises.length} proposed cruise${generated.cruises.length === 1 ? "" : "s"}`}
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
