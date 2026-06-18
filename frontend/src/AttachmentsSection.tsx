import { useRef, useState } from "react";
import AttachmentReaderModal from "./AttachmentReaderModal";
import type { Attachment, AttachmentKind } from "./types";
import { formatFileSize, formatTimestamp } from "./utils";
import ViewIcon from "./ViewIcon";

const ACCEPTED_FILE_TYPES = ".txt,.md,.csv,.json,.log,.vtt,.srt,text/plain";

type AttachmentsSectionProps = {
  title: string;
  kind: AttachmentKind;
  requestId: number;
  items: Attachment[];
  disabled: boolean;
  uploading: boolean;
  onUpload: (file: File) => Promise<void>;
  embedded?: boolean;
};

function UploadIcon() {
  return (
    <svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.75">
      <path d="M12 16V4" />
      <path d="m7 9 5-5 5 5" />
      <path d="M4 20h16" />
    </svg>
  );
}

function FileIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
      <path d="M14 2v6h6" />
    </svg>
  );
}

export default function AttachmentsSection({
  title,
  kind,
  requestId,
  items,
  disabled,
  uploading,
  onUpload,
  embedded = false,
}: AttachmentsSectionProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [viewingAttachment, setViewingAttachment] = useState<Attachment | null>(null);

  async function handleFile(file: File | null | undefined) {
    if (!file || uploading) {
      return;
    }
    await onUpload(file);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  function openFilePicker() {
    if (!uploading) {
      fileInputRef.current?.click();
    }
  }

  const singularLabel = title.endsWith("s") ? title.slice(0, -1) : title;

  const body = (
    <>
      {!disabled ? (
            <div
              className={`attachment-dropzone${dragOver ? " is-dragover" : ""}${
                uploading ? " is-uploading" : ""
              }`}
              onDragEnter={(event) => {
                event.preventDefault();
                setDragOver(true);
              }}
              onDragOver={(event) => {
                event.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={(event) => {
                if (event.currentTarget.contains(event.relatedTarget as Node)) {
                  return;
                }
                setDragOver(false);
              }}
              onDrop={(event) => {
                event.preventDefault();
                setDragOver(false);
                void handleFile(event.dataTransfer.files?.[0]);
              }}
              onClick={openFilePicker}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  openFilePicker();
                }
              }}
              role="button"
              tabIndex={0}
              aria-busy={uploading}
              aria-label={`Upload ${singularLabel.toLowerCase()}`}
            >
              <input
                ref={fileInputRef}
                className="attachment-dropzone-input"
                type="file"
                accept={ACCEPTED_FILE_TYPES}
                disabled={uploading}
                onChange={(event) => {
                  void handleFile(event.target.files?.[0]);
                }}
                onClick={(event) => event.stopPropagation()}
              />
              <div className="attachment-dropzone-icon">
                {uploading ? <span className="attachment-dropzone-spinner" aria-hidden="true" /> : <UploadIcon />}
              </div>
              <p className="attachment-dropzone-title">
                {uploading ? "Uploading file..." : "Drop file here"}
              </p>
              <p className="attachment-dropzone-hint">
                {uploading ? "Please wait while we attach your file." : "or click to browse from your computer"}
              </p>
              {!uploading ? (
                <div className="attachment-dropzone-types">TXT · MD · CSV · JSON · LOG · VTT · SRT</div>
              ) : null}
            </div>
          ) : null}

          <div className="attachment-list">
            {items.length === 0 ? (
              <p className="attachment-empty meta">No files uploaded yet.</p>
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
                          onClick={() => setViewingAttachment(item)}
                        >
                          <span className="attachment-truncate">{item.original_filename}</span>
                        </button>
                        <div className="meta">
                          {formatFileSize(item.size_bytes)} · Added by {item.created_by.username} ·{" "}
                          {formatTimestamp(item.created_at)}
                        </div>
                      </div>
                    </div>
                    <div className="attachment-item-actions">
                      <button
                        type="button"
                        className="icon-button"
                        aria-label={`View ${item.original_filename}`}
                        onClick={() => setViewingAttachment(item)}
                      >
                        <ViewIcon />
                      </button>
                    </div>
                  </div>
                </article>
              ))
            )}
          </div>
    </>
  );

  return (
    <>
      {embedded ? (
        body
      ) : (
        <section className="section-card attachment-card">
          <header className="section-card-header">
            <h3>{title}</h3>
          </header>
          <div className="section-card-body">{body}</div>
        </section>
      )}

      <AttachmentReaderModal
        open={viewingAttachment !== null}
        title={viewingAttachment ? viewingAttachment.original_filename : singularLabel}
        requestId={requestId}
        kind={kind}
        attachment={viewingAttachment}
        onClose={() => setViewingAttachment(null)}
      />
    </>
  );
}
