import { useEffect, useState } from "react";
import ResearchCommunicationBodyPreview from "./ResearchCommunicationBodyPreview";
import { copyCommunicationBodyToClipboard, isHtmlCommunicationBody } from "./utils";

type BodyEditMode = "preview" | "html";

type CommunicationBodyFieldProps = {
  body: string;
  disabled: boolean;
  saving: boolean;
  resetKey: string | number;
  onChange: (body: string) => void;
};

export default function CommunicationBodyField({
  body,
  disabled,
  saving,
  resetKey,
  onChange,
}: CommunicationBodyFieldProps) {
  const isHtml = isHtmlCommunicationBody(body);
  const [mode, setMode] = useState<BodyEditMode>("preview");
  const [copyMessage, setCopyMessage] = useState<string | null>(null);

  useEffect(() => {
    setMode(isHtmlCommunicationBody(body) ? "preview" : "html");
    setCopyMessage(null);
  }, [resetKey, body]);

  async function handleCopy() {
    if (!body.trim()) {
      return;
    }

    try {
      await copyCommunicationBodyToClipboard(body);
      setCopyMessage(isHtml ? "Formatted message copied to clipboard." : "Message copied to clipboard.");
    } catch {
      setCopyMessage("Unable to copy message.");
    }
  }

  return (
    <div className="communication-body-field">
      <div className="communication-body-field-header">
        <span className="communication-body-field-label">Message</span>
        <div className="communication-body-field-actions">
          {isHtml ? (
            <div className="communication-body-mode-toggle" role="tablist" aria-label="Message view">
              <button
                type="button"
                role="tab"
                aria-selected={mode === "preview"}
                className={`communication-body-mode${mode === "preview" ? " is-active" : ""}`}
                disabled={disabled || saving}
                onClick={() => setMode("preview")}
              >
                Preview
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={mode === "html"}
                className={`communication-body-mode${mode === "html" ? " is-active" : ""}`}
                disabled={disabled || saving}
                onClick={() => setMode("html")}
              >
                Edit HTML
              </button>
            </div>
          ) : null}
          <button
            type="button"
            className="modal-secondary communication-body-copy"
            disabled={disabled || saving || !body.trim()}
            onClick={() => void handleCopy()}
          >
            {isHtml ? "Copy formatted message" : "Copy message"}
          </button>
        </div>
      </div>

      {isHtml && mode === "preview" ? (
        <ResearchCommunicationBodyPreview body={body} />
      ) : (
        <textarea
          required
          rows={12}
          disabled={disabled || saving}
          value={body}
          className={isHtml ? "communication-body-textarea communication-body-textarea--html" : "communication-body-textarea"}
          placeholder="Paste the communication content here"
          onChange={(event) => onChange(event.target.value)}
        />
      )}

      {copyMessage ? <p className="status success communication-body-copy-status">{copyMessage}</p> : null}

      <p className="field-hint">
        {isHtml
          ? "Preview shows the rendered email. Switch to Edit HTML to change the source, then copy the formatted message into your email client."
          : "Paste rich text or formatted content from your email client. Formatting will be preserved as entered."}
      </p>
    </div>
  );
}
