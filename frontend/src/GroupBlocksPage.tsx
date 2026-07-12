import { useCallback, useEffect, useMemo, useState } from "react";
import { archiveAgencyGroup, fetchAgencyGroup, fetchAgencyGroups } from "./api";
import { canCreateGroupBlocks, canMutateGroupBlock } from "./agentCapabilities";
import BedIcon from "./BedIcon";
import ChickenSwitchModal from "./ChickenSwitchModal";
import EditIcon from "./EditIcon";
import GroupInventoryLedgerModal from "./GroupInventoryLedgerModal";
import GroupShellModal from "./GroupShellModal";
import IconTooltip from "./IconTooltip";
import ReportPagination from "./ReportPagination";
import TopStatusBar from "./TopStatusBar";
import { DEFAULT_PAGE_SIZE, type PageSizeOption } from "./pagination";
import type { AgencyGroup, AgencyGroupActiveFilter, AgencyGroupListItem, User } from "./types";
import { useTopStatusBar } from "./useTopStatusBar";
import { formatDate } from "./utils";

function statusLabel(group: AgencyGroupListItem): string {
  return group.is_active ? "Active" : "Archived";
}

export default function GroupBlocksPage({ currentUser }: { currentUser: User }) {
  const [groups, setGroups] = useState<AgencyGroupListItem[]>([]);
  const [filter, setFilter] = useState<AgencyGroupActiveFilter>("active");
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<PageSizeOption>(DEFAULT_PAGE_SIZE);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [inventoryModalGroupId, setInventoryModalGroupId] = useState<string | null>(null);
  const [inventoryModalGroupName, setInventoryModalGroupName] = useState<string | null>(null);
  const [inventoryModalReadOnly, setInventoryModalReadOnly] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editingGroup, setEditingGroup] = useState<AgencyGroup | null>(null);
  const [archivingGroup, setArchivingGroup] = useState<AgencyGroupListItem | null>(null);
  const [archivingGroupId, setArchivingGroupId] = useState<string | null>(null);
  const { status, showStatus, clearStatus } = useTopStatusBar();

  const allowCreate = canCreateGroupBlocks(currentUser);

  const loadGroups = useCallback(
    async (options?: { silent?: boolean }) => {
      if (!options?.silent) {
        setLoading(true);
      }
      try {
        const response = await fetchAgencyGroups({
          filter,
          q: searchQuery,
          page,
          pageSize,
        });
        setGroups(response.items);
        setTotal(response.total);
        setTotalPages(response.total_pages);
        if (response.total_pages > 0 && page > response.total_pages) {
          setPage(response.total_pages);
        }
      } catch (loadError) {
        showStatus(loadError instanceof Error ? loadError.message : "Unable to load group blocks.", "error");
      } finally {
        if (!options?.silent) {
          setLoading(false);
        }
      }
    },
    [filter, page, pageSize, searchQuery, showStatus],
  );

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearchQuery(searchInput.trim());
      setPage(1);
    }, 300);

    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    setPage(1);
  }, [filter]);

  useEffect(() => {
    void loadGroups();
  }, [loadGroups]);

  const emptyMessage = useMemo(() => {
    if (searchQuery.trim()) {
      return "No group blocks match your search.";
    }
    if (filter === "active") {
      return allowCreate
        ? "No active group blocks yet. Create one to start tracking cabin inventory."
        : "No active group blocks match this filter.";
    }
    if (filter === "archived") {
      return "No archived group blocks match this filter.";
    }
    return "No group blocks yet.";
  }, [allowCreate, filter, searchQuery]);

  function openInventoryLedger(group: AgencyGroupListItem) {
    setInventoryModalGroupId(group.id);
    setInventoryModalGroupName(group.group_name);
    setInventoryModalReadOnly(!canMutateGroupBlock(currentUser, group));
  }

  function closeInventoryLedger() {
    setInventoryModalGroupId(null);
    setInventoryModalGroupName(null);
    setInventoryModalReadOnly(false);
  }

  async function confirmArchiveGroup() {
    if (!archivingGroup) {
      return;
    }

    setArchivingGroupId(archivingGroup.id);
    try {
      await archiveAgencyGroup(archivingGroup.id);
      showStatus("Group block archived.", "delete");
      if (inventoryModalGroupId === archivingGroup.id) {
        closeInventoryLedger();
      }
      setArchivingGroup(null);
      await loadGroups({ silent: true });
    } catch (archiveError) {
      showStatus(archiveError instanceof Error ? archiveError.message : "Unable to archive group block.", "error");
    } finally {
      setArchivingGroupId(null);
    }
  }

  return (
    <section className="group-blocks-page workflows-tasks-page">
      <TopStatusBar status={status} onDismiss={clearStatus} />

      <header className="request-summary-card request-summary-card-compact group-blocks-summary-card">
        <div className="request-summary-compact-main">
          <h1>Group Blocks</h1>
          <p className="meta group-blocks-summary-lead">
            Manage agency group shells and cabin inventory ledgers before linking them to cruise requests.
          </p>
        </div>
      </header>

      <section className="open-requests-table-card agency-group-blocks-table-card">
        <header className="open-requests-table-card-header agency-group-blocks-table-card-header">
          <div className="open-requests-table-card-header-main">
            <h2>Agency group blocks</h2>
            <div className="group-blocks-filter-tabs" role="tablist" aria-label="Group block status filter">
              {(["active", "archived", "all"] as const).map((tab) => (
                <button
                  key={tab}
                  type="button"
                  role="tab"
                  aria-selected={filter === tab}
                  className={`group-blocks-filter-tab${filter === tab ? " is-active" : ""}`}
                  onClick={() => setFilter(tab)}
                >
                  {tab === "active" ? "Active" : tab === "archived" ? "Archived" : "All"}
                </button>
              ))}
            </div>
          </div>
          {allowCreate ? (
            <button type="button" className="agency-workflows-create-button" onClick={() => setCreateModalOpen(true)}>
              + Create Group Block
            </button>
          ) : null}
        </header>

        <div className="open-requests-table-card-body">
          <div className="group-blocks-table-toolbar">
            <label className="group-blocks-search">
              Search group blocks
              <input
                type="search"
                value={searchInput}
                placeholder="Group name, cruise line, ship, sailing date..."
                onChange={(event) => setSearchInput(event.target.value)}
              />
            </label>
          </div>

          {loading ? (
            <p>Loading group blocks...</p>
          ) : groups.length === 0 ? (
            <p className="meta">{emptyMessage}</p>
          ) : (
            <>
              <div className="open-requests-table-wrap">
                <table className="open-requests-table agency-group-blocks-table">
                  <thead>
                    <tr>
                      <th>Group</th>
                      <th>Sailing</th>
                      <th>Allocated</th>
                      <th>Remaining</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {groups.map((group) => {
                      const canMutate = canMutateGroupBlock(currentUser, group);
                      return (
                        <tr key={group.id}>
                          <td>
                            <span className="agency-group-blocks-table-name">{group.group_name}</span>
                            <span className="meta agency-group-blocks-table-ship">
                              {group.cruise_line} · {group.ship_name}
                            </span>
                          </td>
                          <td>{formatDate(group.sailing_date)}</td>
                          <td>{group.summary.total_cabins_allocated}</td>
                          <td>{group.summary.total_cabins_remaining}</td>
                          <td>
                            <span
                              className={`agency-group-blocks-status-badge${
                                group.is_active ? " agency-group-blocks-status-badge-active" : ""
                              }`}
                            >
                              {statusLabel(group)}
                            </span>
                          </td>
                          <td className="dashboard-table-actions-cell">
                            <div className="dashboard-table-actions">
                              <IconTooltip label={canMutate ? "View inventory ledger" : "View inventory (read-only)"}>
                                <button
                                  type="button"
                                  className="icon-button icon-button-inventory"
                                  aria-label={canMutate ? "View inventory ledger" : "View inventory (read-only)"}
                                  onClick={() => openInventoryLedger(group)}
                                >
                                  <BedIcon />
                                </button>
                              </IconTooltip>
                              {canMutate ? (
                                <IconTooltip label="Edit group block">
                                  <button
                                    type="button"
                                    className="icon-button"
                                    aria-label="Edit group block"
                                    onClick={() => {
                                      void fetchAgencyGroup(group.id)
                                        .then((detail) => setEditingGroup(detail))
                                        .catch((editError) =>
                                          showStatus(
                                            editError instanceof Error
                                              ? editError.message
                                              : "Unable to load group block.",
                                            "error",
                                          ),
                                        );
                                    }}
                                  >
                                    <EditIcon />
                                  </button>
                                </IconTooltip>
                              ) : null}
                              {canMutate && group.is_active ? (
                                <IconTooltip label="Archive group block">
                                  <button
                                    type="button"
                                    className="icon-button icon-button-danger"
                                    aria-label="Archive group block"
                                    disabled={archivingGroupId === group.id}
                                    onClick={() => setArchivingGroup(group)}
                                  >
                                    ×
                                  </button>
                                </IconTooltip>
                              ) : null}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              <ReportPagination
                page={page}
                total={total}
                totalPages={totalPages}
                pageSize={pageSize}
                loading={loading}
                summaryLabel="group blocks"
                onPageChange={setPage}
                onPageSizeChange={(size) => {
                  setPageSize(size);
                  setPage(1);
                }}
              />
            </>
          )}
        </div>
      </section>

      <GroupInventoryLedgerModal
        open={inventoryModalGroupId !== null}
        groupId={inventoryModalGroupId}
        groupName={inventoryModalGroupName}
        readOnly={inventoryModalReadOnly}
        onClose={closeInventoryLedger}
        onGroupUpdated={() => void loadGroups({ silent: true })}
        showStatus={showStatus}
      />

      <GroupShellModal
        open={createModalOpen}
        mode="create"
        group={null}
        onClose={() => setCreateModalOpen(false)}
        onSaved={(group) => {
          showStatus("Group block created.", "success");
          void loadGroups({ silent: true });
          setInventoryModalGroupId(group.id);
          setInventoryModalGroupName(group.group_name);
          setInventoryModalReadOnly(false);
        }}
      />

      <GroupShellModal
        open={editingGroup !== null}
        mode="edit"
        group={editingGroup}
        onClose={() => setEditingGroup(null)}
        onSaved={() => {
          showStatus("Group block updated.", "success");
          setEditingGroup(null);
          void loadGroups({ silent: true });
        }}
      />

      <ChickenSwitchModal
        open={archivingGroup !== null}
        title="Archive group block?"
        description={`"${archivingGroup?.group_name ?? "This group block"}" will be hidden from active pickers. Inventory and request history are preserved.`}
        switchLabel={`Yes, archive ${archivingGroup?.group_name ?? "this group block"}`}
        confirmLabel="Archive group block"
        confirmingLabel="Archiving..."
        hint="Archived groups can still be viewed under the Archived filter."
        confirming={archivingGroup !== null && archivingGroupId === archivingGroup.id}
        onCancel={() => setArchivingGroup(null)}
        onConfirm={() => void confirmArchiveGroup()}
      />
    </section>
  );
}
