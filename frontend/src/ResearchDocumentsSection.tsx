import { useState } from "react";
import ResearchDocumentReaderModal from "./ResearchDocumentReaderModal";
import type { ResearchDocument } from "./types";
import { formatFileSize, formatTimestamp } from "./utils";
import ViewIcon from "./ViewIcon";

type ResearchDocumentsSectionProps = {
  requestId: number;
  items: ResearchDocument[];
  embedded?: boolean;
};

function FileIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
      <path d="M14 2v6h6" />
    </svg>
  );
}

export default function ResearchDocumentsSection({
  requestId,
  items,
  embedded = false,
}: ResearchDocumentsSectionProps) {
  const [viewingDocument, setViewingDocument] = useState<ResearchDocument | null>(null);

  const body = (
    <div className="attachment-list">
      {items.length === 0 ? (
        <p className="attachment-empty meta">
          No research documents uploaded yet. Upload from the Research workflow task when ready.
        </p>
      ) : (
        items.map((item) => (
          <article className="attachment-item" key={item.id}>
            <div className="attachment-item-header">
              <div className="attachment-item-leading">
                <span className="attachment-file-icon" aria-hidden="true">
                  <FileIcon />
                </span>
                <div className="attachment-item-details">
                  <button
                    type="button"
                    className="link-button attachment-file-name"
                    title={item.original_filename}
                    onClick={() => setViewingDocument(item)}
                  >
                    <span className="attachment-truncate">{item.original_filename}</span>
                  </button>
                  <div className="meta">
                    {formatFileSize(item.size_bytes)} · Uploaded by {item.uploaded_by.username} ·{" "}
                    {formatTimestamp(item.created_at)}
                  </div>
                </div>
              </div>
              <div className="attachment-item-actions">
                <button
                  type="button"
                  className="icon-button"
                  aria-label={`View ${item.original_filename}`}
                  onClick={() => setViewingDocument(item)}
                >
                  <ViewIcon />
                </button>
              </div>
            </div>
          </article>
        ))
      )}
    </div>
  );

  return (
    <>
      {embedded ? (
        body
      ) : (
        <section className="section-card attachment-card">
          <header className="section-card-header">
            <h3>Research Documents</h3>
          </header>
          <div className="section-card-body">{body}</div>
        </section>
      )}

      <ResearchDocumentReaderModal
        open={viewingDocument !== null}
        requestId={requestId}
        document={viewingDocument}
        onClose={() => setViewingDocument(null)}
      />
    </>
  );
}
