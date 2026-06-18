import { useEffect, useMemo, useState } from "react";
import { activateClient, deactivateClient, fetchClients } from "./api";
import ChickenSwitchModal from "./ChickenSwitchModal";
import ClientModal from "./ClientModal";
import InactiveClientBadge from "./InactiveClientBadge";
import type { ClientListItem } from "./types";
import { formatDate } from "./utils";

type PendingDeactivateClient = {
  id: number;
  name: string;
};

export default function ClientsPage() {
  const [clients, setClients] = useState<ClientListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [modalClientId, setModalClientId] = useState<number | null>(null);
  const [modalMode, setModalMode] = useState<"view" | "edit">("view");
  const [pendingDeactivate, setPendingDeactivate] = useState<PendingDeactivateClient | null>(null);
  const [deactivatingId, setDeactivatingId] = useState<number | null>(null);

  async function loadClients() {
    setLoading(true);
    setError("");
    try {
      setClients(await fetchClients());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load clients.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadClients();
  }, []);

  const filteredClients = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) {
      return clients;
    }

    return clients.filter((client) => {
      const haystack = [
        client.first_name,
        client.last_name,
        client.email,
        client.phone,
        client.date_of_birth ? formatDate(client.date_of_birth) : "",
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(query);
    });
  }, [clients, searchQuery]);

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
      await loadClients();
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
      await loadClients();
    } catch (reactivateError) {
      setError(reactivateError instanceof Error ? reactivateError.message : "Unable to reactivate client.");
    }
  }

  return (
    <section className="clients-page">
      <div className="clients-page-header">
        <div>
          <h2>Clients</h2>
          <p className="meta">Manage reusable passenger profiles across requests.</p>
        </div>
        <label className="clients-search">
          Search clients
          <input
            type="search"
            value={searchQuery}
            placeholder="Name, email, phone, or date of birth"
            onChange={(event) => setSearchQuery(event.target.value)}
          />
        </label>
      </div>

      {error ? <p className="status error">{error}</p> : null}

      <section className="card clients-table-card">
        {loading ? (
          <p>Loading clients...</p>
        ) : filteredClients.length === 0 ? (
          <p>{clients.length === 0 ? "No clients yet." : "No clients match your search."}</p>
        ) : (
          <div className="clients-table-wrap">
            <table className="clients-table">
              <thead>
                <tr>
                  <th scope="col">Name</th>
                  <th scope="col">Date of birth</th>
                  <th scope="col">Phone</th>
                  <th scope="col">Email</th>
                  <th scope="col">Requests</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredClients.map((client) => (
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
                    <td>
                      <div className="clients-table-actions">
                        <button type="button" className="modal-secondary" onClick={() => openClient(client.id, "view")}>
                          View
                        </button>
                        <button type="button" className="modal-secondary" onClick={() => openClient(client.id, "edit")}>
                          Edit
                        </button>
                        {client.is_active ? (
                          <button
                            type="button"
                            className="modal-secondary danger-button"
                            onClick={() => requestDeactivateClient(client)}
                          >
                            Deactivate
                          </button>
                        ) : (
                          <button
                            type="button"
                            className="modal-secondary"
                            onClick={() => void handleReactivateClient(client)}
                          >
                            Reactivate
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <ClientModal
        open={modalClientId !== null}
        clientId={modalClientId}
        mode={modalMode}
        onClose={() => setModalClientId(null)}
        onModeChange={setModalMode}
        onSaved={() => void loadClients()}
        onDeactivated={() => void loadClients()}
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
