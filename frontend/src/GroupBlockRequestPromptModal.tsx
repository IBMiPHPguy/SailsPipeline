type GroupBlockRequestPromptModalProps = {
  open: boolean;
  onChooseStandard: () => void;
  onChooseGroupBlock: () => void;
  onCancel: () => void;
};

export default function GroupBlockRequestPromptModal({
  open,
  onChooseStandard,
  onChooseGroupBlock,
  onCancel,
}: GroupBlockRequestPromptModalProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="modal-backdrop" role="presentation" onClick={onCancel}>
      <div
        className="modal-card group-block-request-prompt-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="group-block-request-prompt-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="modal-card-header">
          <h3 id="group-block-request-prompt-title">Is this a group block request?</h3>
        </header>

        <div className="modal-scroll-body">
          <p className="meta">
            Group block requests are linked to an active agency group shell and its cabin inventory. Standard requests
            follow the usual FIT intake flow.
          </p>
        </div>

        <div className="modal-actions modal-actions-footer">
          <button type="button" className="modal-secondary" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="modal-secondary" onClick={onChooseStandard}>
            No, standard request
          </button>
          <button type="button" onClick={onChooseGroupBlock}>
            Yes, group block
          </button>
        </div>
      </div>
    </div>
  );
}
