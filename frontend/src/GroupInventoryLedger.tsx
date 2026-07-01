import { useCallback, useEffect, useState } from "react";
import { deleteAgencyGroupInventory, fetchAgencyGroup, fetchAgencyGroupMetrics } from "./api";
import ChickenSwitchModal from "./ChickenSwitchModal";
import GroupDetailReadOnly, { formatInventoryDescription } from "./GroupDetailReadOnly";
import GroupInventoryEditModal from "./GroupInventoryEditModal";
import type { AgencyGroup, AgencyGroupInventory, AgencyGroupMetrics } from "./types";
import type { TopStatusBarVariant } from "./TopStatusBar";

type GroupInventoryLedgerProps = {
  group: AgencyGroup;
  readOnly?: boolean;
  onGroupUpdated: (group: AgencyGroup, metrics?: AgencyGroupMetrics | null) => void;
  showStatus: (message: string, variant: TopStatusBarVariant) => void;
};

export default function GroupInventoryLedger({
  group,
  readOnly = false,
  onGroupUpdated,
  showStatus,
}: GroupInventoryLedgerProps) {
  const [metrics, setMetrics] = useState<AgencyGroupMetrics | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(true);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editingInventory, setEditingInventory] = useState<AgencyGroupInventory | null>(null);
  const [deletingInventory, setDeletingInventory] = useState<AgencyGroupInventory | null>(null);
  const [deletingInventoryId, setDeletingInventoryId] = useState<string | null>(null);

  const loadMetrics = useCallback(async () => {
    setMetricsLoading(true);
    try {
      const nextMetrics = await fetchAgencyGroupMetrics(group.id);
      setMetrics(nextMetrics);
      return nextMetrics;
    } catch {
      setMetrics(null);
      return null;
    } finally {
      setMetricsLoading(false);
    }
  }, [group.id]);

  useEffect(() => {
    void loadMetrics();
  }, [loadMetrics]);

  async function refreshGroup() {
    const [updatedGroup, updatedMetrics] = await Promise.all([
      fetchAgencyGroup(group.id),
      fetchAgencyGroupMetrics(group.id).catch(() => null),
    ]);
    setMetrics(updatedMetrics);
    onGroupUpdated(updatedGroup, updatedMetrics);
    return updatedGroup;
  }

  async function confirmDeleteInventory() {
    if (!deletingInventory) {
      return;
    }

    setDeletingInventoryId(deletingInventory.id);
    try {
      await deleteAgencyGroupInventory(deletingInventory.id);
      showStatus("Inventory row removed.", "delete");
      setDeletingInventory(null);
      await refreshGroup();
    } catch (deleteError) {
      showStatus(deleteError instanceof Error ? deleteError.message : "Unable to remove inventory row.", "error");
    } finally {
      setDeletingInventoryId(null);
    }
  }

  if (readOnly) {
    return <GroupDetailReadOnly group={group} metrics={metricsLoading ? null : metrics} />;
  }

  return (
    <>
      <header className="group-inventory-ledger-toolbar">
        <p className="meta group-inventory-panel-meta">
          {group.summary.inventory_row_count} inventory rows · {group.summary.total_cabins_remaining} cabins remaining
          {metrics ? ` · ${metrics.linked_request_count} linked requests` : ""}
        </p>
        {group.is_active ? (
          <button type="button" className="agency-workflows-create-button" onClick={() => setCreateModalOpen(true)}>
            + Add inventory row
          </button>
        ) : null}
      </header>

      <GroupDetailReadOnly
        group={group}
        metrics={metricsLoading ? null : metrics}
        showActions={group.is_active}
        deletingInventoryId={deletingInventoryId}
        onEditInventory={(item) => setEditingInventory(item)}
        onDeleteInventory={(item) => setDeletingInventory(item)}
      />

      {!group.is_active ? <p className="meta group-inventory-archived-note">This group block is archived.</p> : null}

      <GroupInventoryEditModal
        open={createModalOpen}
        mode="create"
        groupId={group.id}
        inventory={null}
        onClose={() => setCreateModalOpen(false)}
        onSaved={async () => {
          showStatus("Inventory row added.", "success");
          await refreshGroup();
        }}
      />

      <GroupInventoryEditModal
        open={editingInventory !== null}
        mode="edit"
        groupId={group.id}
        inventory={editingInventory}
        onClose={() => setEditingInventory(null)}
        onSaved={async () => {
          showStatus("Inventory row updated.", "success");
          await refreshGroup();
        }}
      />

      <ChickenSwitchModal
        open={deletingInventory !== null}
        title="Remove inventory row?"
        description={`Remove ${deletingInventory ? formatInventoryDescription(deletingInventory) : "this inventory row"} from this group block?`}
        switchLabel="Yes, remove this inventory row"
        confirmLabel="Remove row"
        confirmingLabel="Removing..."
        hint="Rows with reserved cabins cannot be removed."
        confirming={deletingInventory !== null && deletingInventoryId === deletingInventory.id}
        onCancel={() => setDeletingInventory(null)}
        onConfirm={() => void confirmDeleteInventory()}
      />
    </>
  );
}
