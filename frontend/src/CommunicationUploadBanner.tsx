import { useRef, useState } from "react";
import type { AttachmentKind } from "./types";

const ACCEPTED_FILE_TYPES = ".txt,.md,.csv,.json,.log,.vtt,.srt,text/plain";

type CommunicationUploadBannerProps = {
  kind: AttachmentKind;
  uploading: boolean;
  disabled: boolean;
  autoGenerateAiSummary: boolean;
  aiUnavailableMessage?: string | null;
  onAutoGenerateChange: (value: boolean) => void;
  onUpload: (file: File, options: { autoGenerateAiSummary: boolean }) => Promise<void>;
};

function UploadIcon() {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.75">
      <path d="M12 16V4" />
      <path d="m7 9 5-5 5 5" />
      <path d="M4 20h16" />
    </svg>
  );
}

export default function CommunicationUploadBanner({
  kind,
  uploading,
  disabled,
  autoGenerateAiSummary,
  aiUnavailableMessage = null,
  onAutoGenerateChange,
  onUpload,
}: CommunicationUploadBannerProps) {
  const aiBlocked = Boolean(aiUnavailableMessage);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const label = kind === "transcripts" ? "call transcript" : "chat log";

  async function handleFile(file: File | null | undefined) {
    if (!file || uploading || disabled) {
      return;
    }
    await onUpload(file, { autoGenerateAiSummary });
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  function openFilePicker() {
    if (!uploading && !disabled) {
      fileInputRef.current?.click();
    }
  }

  if (disabled) {
    return null;
  }

  return (
    <div className="communication-upload-banner">
      <div
        className={`attachment-dropzone communication-upload-dropzone${dragOver ? " is-dragover" : ""}${
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
        aria-label={`Upload ${label}`}
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
        <div className="communication-upload-dropzone-main">
          <div className="attachment-dropzone-icon communication-upload-icon">
            {uploading ? <span className="attachment-dropzone-spinner" aria-hidden="true" /> : <UploadIcon />}
          </div>
          <div className="communication-upload-copy">
            <p className="attachment-dropzone-title">
              {uploading ? "Uploading file..." : `Drop ${label} here`}
            </p>
            <p className="attachment-dropzone-hint">
              {uploading ? "Please wait while we attach your file." : "or click to browse from your computer"}
            </p>
            {!uploading ? (
              <div className="attachment-dropzone-types">TXT · MD · CSV · JSON · LOG · VTT · SRT</div>
            ) : null}
          </div>
        </div>
        <label className="communication-auto-ai-toggle" onClick={(event) => event.stopPropagation()}>
          <input
            type="checkbox"
            checked={autoGenerateAiSummary && !aiBlocked}
            disabled={uploading || aiBlocked}
            onChange={(event) => onAutoGenerateChange(event.target.checked)}
          />
          <span>✨ Auto-generate AI Summary &amp; Research Brief on upload</span>
        </label>
        {aiUnavailableMessage ? <p className="status warning communication-ai-blocked-note">{aiUnavailableMessage}</p> : null}
      </div>
    </div>
  );
}
