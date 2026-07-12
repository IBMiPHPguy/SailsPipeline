import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { fetchAgencyGroup } from "./api";
import GroupInventoryLedger from "./GroupInventoryLedger";
import type { AgencyGroup } from "./types";
import type { TopStatusBarVariant } from "./TopStatusBar";

type GroupInventoryLedgerModalProps = {
  open: boolean;
  groupId: string | null;
  groupName?: string | null;
  readOnly?: boolean;
  onClose: () => void;
  onGroupUpdated: () => void;
  showStatus: (message: string, variant: TopStatusBarVariant) => void;
};

export default function GroupInventoryLedgerModal({
  open,
  groupId,
  groupName,
  readOnly = false,
  onClose,
  onGroupUpdated,
  showStatus,
}: GroupInventoryLedgerModalProps) {
  const [group, setGroup] = useState<AgencyGroup | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadGroup = useCallback(async () => {
    if (!groupId) {
      setGroup(null);
      return;
    }

    setLoading(true);
    setError("");
    try {
      setGroup(await fetchAgencyGroup(groupId));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load inventory ledger.");
      setGroup(null);
    } finally {
      setLoading(false);
    }
  }, [groupId]);

  useEffect(() => {
    if (!open || !groupId) {
      setGroup(null);
      setError("");
      setLoading(false);
      return;
    }
    void loadGroup();
  }, [open, groupId, loadGroup]);

  if (!open) {
    return null;
  }

  const title = group?.group_name ?? groupName ?? "Inventory ledger";

  return createPortal(
    <div className="modal-backdrop modal-backdrop-scroll" role="presentation" onClick={onClose}>
      <div
        className="modal-card modal-card-wide group-inventory-ledger-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="group-inventory-ledger-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="modal-card-header">
          <h3 id="group-inventory-ledger-title">{title}</h3>
        </header>

        <div className="modal-scroll-body group-inventory-ledger-modal-body">
          {loading ? <p className="meta">Loading inventory ledger...</p> : null}
          {error ? <p className="status error">{error}</p> : null}
          {!loading && !error && group ? (
            <GroupInventoryLedger
              group={group}
              readOnly={readOnly}
              onGroupUpdated={(updated) => {
                setGroup(updated);
                onGroupUpdated();
              }}
              showStatus={showStatus}
            />
          ) : null}
        </div>

        <div className="modal-actions modal-actions-footer">
          <button type="button" className="modal-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
