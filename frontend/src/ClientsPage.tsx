import { useEffect, useState } from "react";
import { activateClient, deactivateClient, fetchClients } from "./api";
import ChickenSwitchModal from "./ChickenSwitchModal";
import ClientModal from "./ClientModal";
import DeactivateIcon from "./DeactivateIcon";
import EditIcon from "./EditIcon";
import IconTooltip from "./IconTooltip";
import InactiveClientBadge from "./InactiveClientBadge";
import ReopenIcon from "./ReopenIcon";
import type { ClientListItem } from "./types";
import ViewIcon from "./ViewIcon";
import { formatDate } from "./utils";

const CLIENTS_PAGE_SIZE = 25;

type PendingDeactivateClient = {
  id: number;
  name: string;
};

export default function ClientsPage() {
  const [clients, setClients] = useState<ClientListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [registryCount, setRegistryCount] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [modalClientId, setModalClientId] = useState<number | null>(null);
  const [modalMode, setModalMode] = useState<"view" | "edit">("view");
  const [pendingDeactivate, setPendingDeactivate] = useState<PendingDeactivateClient | null>(null);
  const [deactivatingId, setDeactivatingId] = useState<number | null>(null);

  async function loadClients(activeSearch: string, activePage: number) {
    setLoading(true);
    setError("");
    try {
      const response = await fetchClients({
        q: activeSearch,
        page: activePage,
        pageSize: CLIENTS_PAGE_SIZE,
      });
      setClients(response.items);
      setTotal(response.total);
      setRegistryCount(response.registry_count);
      setTotalPages(response.total_pages);
      if (response.total_pages > 0 && activePage > response.total_pages) {
        setPage(response.total_pages);
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load clients.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearchQuery(searchInput.trim());
      setPage(1);
    }, 300);

    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    void loadClients(searchQuery, page);
  }, [searchQuery, page]);

  function openClient(clientId: number, mode: "view" | "edit") {
    setModalClientId(clientId);
    setModalMode(mode);
  }

  function requestDeactivateClient(client: ClientListItem) {
    setPendingDeactivate({
      id: client.id,
      name: `${client.first_name} ${client.last_name}`,
    });
  }

  async function confirmDeactivateClient() {
    if (!pendingDeactivate) {
      return;
    }

    setDeactivatingId(pendingDeactivate.id);
    setError("");
    try {
      await deactivateClient(pendingDeactivate.id);
      setPendingDeactivate(null);
      await loadClients(searchQuery, page);
    } catch (deactivateError) {
      setError(deactivateError instanceof Error ? deactivateError.message : "Unable to deactivate client.");
    } finally {
      setDeactivatingId(null);
    }
  }

  async function handleReactivateClient(client: ClientListItem) {
    const confirmed = window.confirm(
      `Reactivate ${client.first_name} ${client.last_name}? They will be available to add to new requests again.`,
    );
    if (!confirmed) {
      return;
    }

    setError("");
    try {
      await activateClient(client.id);
      await loadClients(searchQuery, page);
    } catch (reactivateError) {
      setError(reactivateError instanceof Error ? reactivateError.message : "Unable to reactivate client.");
    }
  }

  const pageStart = total === 0 ? 0 : (page - 1) * CLIENTS_PAGE_SIZE + 1;
  const pageEnd = total === 0 ? 0 : Math.min(page * CLIENTS_PAGE_SIZE, total);
  const emptyMessage = searchQuery.trim()
    ? "No clients match your search."
    : "No clients yet.";

  return (
    <section className="clients-page">
      <section className="card open-requests-table-card clients-table-card">
        <header className="open-requests-table-card-header clients-table-card-header">
          <div className="open-requests-table-card-header-main">
            <h3>Clients</h3>
            <span
              className="open-requests-table-card-count clients-table-card-count"
              aria-label={`${registryCount} clients`}
            >
              {registryCount}
            </span>
          </div>
        </header>
        <div className="open-requests-table-card-body">
          <div className="clients-table-toolbar">
            <label className="clients-search">
              Search clients
              <input
                type="search"
                value={searchInput}
                placeholder="Name, email, phone, or date of birth"
                onChange={(event) => setSearchInput(event.target.value)}
              />
            </label>
          </div>

          {loading ? (
            <p>Loading clients...</p>
          ) : clients.length === 0 ? (
            <p>{emptyMessage}</p>
          ) : (
            <>
              <div className="open-requests-table-wrap">
                <table className="open-requests-table clients-table">
                  <thead>
                    <tr>
                      <th scope="col">Name</th>
                      <th scope="col">Date of birth</th>
                      <th scope="col">Phone</th>
                      <th scope="col">Email</th>
                      <th scope="col">Requests</th>
                      <th scope="col">
                        <span className="sr-only">Actions</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {clients.map((client) => {
                      const clientName = `${client.first_name} ${client.last_name}`;

                      return (
                        <tr key={client.id} className={client.is_active ? undefined : "clients-table-row-inactive"}>
                        <td>
                          <div className="clients-table-name">
                            <span>
                              {client.first_name} {client.last_name}
                            </span>
                            {!client.is_active ? <InactiveClientBadge /> : null}
                          </div>
                        </td>
                        <td>{client.date_of_birth ? formatDate(client.date_of_birth) : "—"}</td>
                        <td>{client.phone ?? "—"}</td>
                        <td>{client.email ?? "—"}</td>
                        <td>{client.request_count}</td>
                        <td className="dashboard-table-actions-cell clients-table-actions-cell">
                          <div className="dashboard-table-actions">
                            <IconTooltip label={`View ${clientName}`}>
                              <button
                                type="button"
                                className="icon-button"
                                aria-label={`View ${clientName}`}
                                onClick={() => openClient(client.id, "view")}
                              >
                                <ViewIcon />
                              </button>
                            </IconTooltip>
                            <IconTooltip label={`Edit ${clientName}`}>
                              <button
                                type="button"
                                className="icon-button"
                                aria-label={`Edit ${clientName}`}
                                onClick={() => openClient(client.id, "edit")}
                              >
                                <EditIcon />
                              </button>
                            </IconTooltip>
                            {client.is_active ? (
                              <IconTooltip label={`Deactivate ${clientName}`}>
                                <button
                                  type="button"
                                  className="icon-button icon-button-danger"
                                  aria-label={`Deactivate ${clientName}`}
                                  onClick={() => requestDeactivateClient(client)}
                                >
                                  <DeactivateIcon />
                                </button>
                              </IconTooltip>
                            ) : (
                              <IconTooltip label={`Reactivate ${clientName}`}>
                                <button
                                  type="button"
                                  className="icon-button icon-button-reopen"
                                  aria-label={`Reactivate ${clientName}`}
                                  onClick={() => void handleReactivateClient(client)}
                                >
                                  <ReopenIcon />
                                </button>
                              </IconTooltip>
                            )}
                          </div>
                        </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              <div className="table-pagination">
                <p className="table-pagination-summary">
                  {searchQuery.trim()
                    ? `Showing ${pageStart}-${pageEnd} of ${total} matching clients`
                    : `Showing ${pageStart}-${pageEnd} of ${total} clients`}
                </p>
                <div className="table-pagination-controls">
                  <button
                    type="button"
                    className="secondary-button"
                    disabled={page <= 1 || loading}
                    onClick={() => setPage((currentPage) => Math.max(1, currentPage - 1))}
                  >
                    Previous
                  </button>
                  <span className="table-pagination-status">
                    Page {totalPages === 0 ? 0 : page} of {totalPages}
                  </span>
                  <button
                    type="button"
                    className="secondary-button"
                    disabled={page >= totalPages || totalPages === 0 || loading}
                    onClick={() => setPage((currentPage) => currentPage + 1)}
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </section>

      {error ? <p className="status error">{error}</p> : null}

      <ClientModal
        open={modalClientId !== null}
        clientId={modalClientId}
        mode={modalMode}
        onClose={() => setModalClientId(null)}
        onModeChange={setModalMode}
        onSaved={() => void loadClients(searchQuery, page)}
        onDeactivated={() => void loadClients(searchQuery, page)}
      />

      <ChickenSwitchModal
        open={pendingDeactivate !== null}
        title="Deactivate client?"
        description="This client will be marked inactive. They will stay on existing requests but cannot be added to new ones."
        itemName={pendingDeactivate?.name}
        switchLabel="Yes, deactivate this client"
        confirmLabel="Deactivate client"
        confirmingLabel="Deactivating..."
        hint="You can reactivate this client later from the Clients page."
        confirming={pendingDeactivate !== null && deactivatingId === pendingDeactivate.id}
        onCancel={() => setPendingDeactivate(null)}
        onConfirm={() => void confirmDeactivateClient()}
      />
    </section>
  );
}
