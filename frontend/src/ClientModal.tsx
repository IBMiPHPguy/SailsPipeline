import { useEffect, useState } from "react";
import { activateClient, createClient, deactivateClient, fetchClient, updateClient } from "./api";
import AnnualInsuranceFields from "./AnnualInsuranceFields";
import ChickenSwitchModal from "./ChickenSwitchModal";
import InactiveClientBadge from "./InactiveClientBadge";
import PassengerQualifierBadges from "./PassengerQualifierBadges";
import PassengerFields, { emptyPassengerInput, toPassengerPayload } from "./PassengerFields";
import { formatPassengerAddressLine, passengerAddressToInput } from "./passengerAddress";
import { formatDisplayPhone } from "./passengerDisplay";
import type { ClientDetail, RequestPassengerInput } from "./types";
import { formatDate } from "./utils";
import "./insurance-portal.css";

type ClientModalMode = "view" | "edit" | "create";

type ClientModalProps = {
  open: boolean;
  clientId: number | null;
  mode: ClientModalMode;
  onClose: () => void;
  onModeChange: (mode: ClientModalMode) => void;
  onSaved: () => void;
  onDeactivated: () => void;
  /** Opens a focused annual-insurance editor stacked above another modal. */
  annualInsuranceQuickEdit?: boolean;
  stacked?: boolean;
};

function clientToForm(client: ClientDetail): RequestPassengerInput {
  return {
    first_name: client.first_name,
    last_name: client.last_name,
    email: client.email,
    phone: client.phone,
    date_of_birth: client.date_of_birth ?? "",
    qualifiers: client.qualifiers ?? [],
    has_annual_insurance: client.has_annual_insurance ?? false,
    annual_insurance_expires_at: client.annual_insurance_expires_at ?? "",
    annual_insurance_policy_number: client.annual_insurance_policy_number ?? "",
    ...passengerAddressToInput(client),
  };
}

function buildClientPayload(payload: RequestPassengerInput) {
  return {
    first_name: payload.first_name,
    last_name: payload.last_name,
    email: payload.email,
    phone: payload.phone,
    date_of_birth: payload.date_of_birth,
    address_line_1: payload.address_line_1,
    address_line_2: payload.address_line_2,
    city: payload.city,
    state_or_province: payload.state_or_province,
    postal_code: payload.postal_code,
    country: payload.country,
    qualifiers: payload.qualifiers,
    has_annual_insurance: payload.has_annual_insurance ?? false,
    annual_insurance_expires_at:
      payload.has_annual_insurance ? payload.annual_insurance_expires_at?.trim() || null : null,
    annual_insurance_policy_number:
      payload.has_annual_insurance ? payload.annual_insurance_policy_number?.trim() || null : null,
  };
}

export default function ClientModal({
  open,
  clientId,
  mode,
  onClose,
  onModeChange,
  onSaved,
  onDeactivated,
  annualInsuranceQuickEdit = false,
  stacked = false,
}: ClientModalProps) {
  const [client, setClient] = useState<ClientDetail | null>(null);
  const [editForm, setEditForm] = useState<RequestPassengerInput>(emptyPassengerInput());
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [pendingDeactivate, setPendingDeactivate] = useState(false);
  const [deactivating, setDeactivating] = useState(false);

  useEffect(() => {
    if (!open) {
      setClient(null);
      setEditForm(emptyPassengerInput());
      setError("");
      setPendingDeactivate(false);
      return;
    }

    if (mode === "create") {
      setClient(null);
      setEditForm(emptyPassengerInput());
      setError("");
      setLoading(false);
      return;
    }

    if (clientId === null) {
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError("");

    fetchClient(clientId)
      .then((detail) => {
        if (!cancelled) {
          setClient(detail);
          const form = clientToForm(detail);
          if (annualInsuranceQuickEdit) {
            form.has_annual_insurance = true;
          }
          setEditForm(form);
        }
      })
      .catch((loadError) => {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Unable to load client.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [open, clientId, mode, annualInsuranceQuickEdit]);

  useEffect(() => {
    if (!open) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  if (!open || (mode !== "create" && clientId === null)) {
    return null;
  }

  async function handleSave() {
    if (!client) {
      return;
    }

    setSaving(true);
    setError("");
    try {
      const payload = toPassengerPayload(editForm);
      const updated = await updateClient(client.id, buildClientPayload(payload));
      if (annualInsuranceQuickEdit) {
        onSaved();
        onClose();
        return;
      }
      setClient(updated);
      setEditForm(clientToForm(updated));
      onModeChange("view");
      onSaved();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to update client.");
    } finally {
      setSaving(false);
    }
  }

  async function handleCreate() {
    setSaving(true);
    setError("");
    try {
      const payload = toPassengerPayload(editForm);
      if (!payload.first_name || !payload.last_name) {
        setError("First and last name are required.");
        return;
      }
      await createClient(buildClientPayload(payload));
      onSaved();
      onClose();
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Unable to add client.");
    } finally {
      setSaving(false);
    }
  }

  async function confirmDeactivate() {
    if (!client || !client.is_active) {
      return;
    }

    setDeactivating(true);
    setError("");
    try {
      const updated = await deactivateClient(client.id);
      setClient(updated);
      setPendingDeactivate(false);
      onDeactivated();
      onClose();
    } catch (deactivateError) {
      setError(deactivateError instanceof Error ? deactivateError.message : "Unable to deactivate client.");
    } finally {
      setDeactivating(false);
    }
  }

  async function handleReactivate() {
    if (!client || client.is_active) {
      return;
    }

    const confirmed = window.confirm(
      `Reactivate ${client.first_name} ${client.last_name}? They will be available to add to new requests again.`,
    );
    if (!confirmed) {
      return;
    }

    setSaving(true);
    setError("");
    try {
      const updated = await activateClient(client.id);
      setClient(updated);
      onDeactivated();
      onClose();
    } catch (reactivateError) {
      setError(reactivateError instanceof Error ? reactivateError.message : "Unable to reactivate client.");
    } finally {
      setSaving(false);
    }
  }

  const addressLine = client ? formatPassengerAddressLine(client) : "";
  const modalTitle = annualInsuranceQuickEdit
    ? "Add annual insurance"
    : mode === "create"
      ? "Add client"
      : mode === "view"
        ? "Client details"
        : "Edit client";
  const backdropClassName = [
    "modal-backdrop",
    "client-modal-backdrop",
    stacked ? "modal-backdrop-stacked" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <>
      <div className={backdropClassName} role="presentation" onClick={onClose}>
        <div
          className="modal-card modal-card-wide client-modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="client-modal-title"
          onClick={(event) => event.stopPropagation()}
        >
          <header className="modal-card-header">
            <div className="client-modal-header">
              <div>
                <h3 id="client-modal-title">{modalTitle}</h3>
                {annualInsuranceQuickEdit && client ? (
                  <p className="muted client-modal-subtitle">
                    {client.first_name} {client.last_name}
                  </p>
                ) : null}
              </div>
              {client && !client.is_active && !annualInsuranceQuickEdit ? <InactiveClientBadge /> : null}
            </div>
          </header>

          <div className="modal-scroll-body client-modal-body">
            {loading ? <p>Loading client...</p> : null}
            {error ? <p className="status error">{error}</p> : null}

            {!loading && client && annualInsuranceQuickEdit ? (
              <div className="modal-section-panel">
                <p className="field-hint">
                  Annual insurance is saved on this client&apos;s registry profile and applies across all of their
                  requests.
                </p>
                <AnnualInsuranceFields
                  value={{
                    has_annual_insurance: editForm.has_annual_insurance ?? true,
                    annual_insurance_expires_at: editForm.annual_insurance_expires_at,
                    annual_insurance_policy_number: editForm.annual_insurance_policy_number,
                  }}
                  onChange={(annualValue) =>
                    setEditForm((current) => ({
                      ...current,
                      ...annualValue,
                    }))
                  }
                  disabled={saving}
                />
              </div>
            ) : null}

            {!loading && client && mode === "view" && !annualInsuranceQuickEdit ? (
              <div className="modal-section-panel">
                <dl className="client-detail-grid">
                  <div>
                    <dt>Name</dt>
                    <dd>
                      {client.first_name} {client.last_name}
                    </dd>
                  </div>
                  <div>
                    <dt>Date of birth</dt>
                    <dd>{client.date_of_birth ? formatDate(client.date_of_birth) : "—"}</dd>
                  </div>
                  <div>
                    <dt>Phone</dt>
                    <dd>{formatDisplayPhone(client.phone) ?? "—"}</dd>
                  </div>
                  <div>
                    <dt>Email</dt>
                    <dd>{client.email}</dd>
                  </div>
                  <div>
                    <dt>Address</dt>
                    <dd>{addressLine || "—"}</dd>
                  </div>
                  <div>
                    <dt>Qualifying discounts</dt>
                    <dd>
                      <PassengerQualifierBadges qualifiers={client.qualifiers ?? []} />
                    </dd>
                  </div>
                  <div>
                    <dt>Annual travel insurance</dt>
                    <dd>
                      {client.has_annual_insurance ? (
                        <>
                          <div>Yes</div>
                          {client.annual_insurance_policy_number ? (
                            <div className="meta">Policy {client.annual_insurance_policy_number}</div>
                          ) : null}
                          {client.annual_insurance_expires_at ? (
                            <div className="meta">Expires {formatDate(client.annual_insurance_expires_at)}</div>
                          ) : null}
                        </>
                      ) : (
                        "No"
                      )}
                    </dd>
                  </div>
                  <div>
                    <dt>Status</dt>
                    <dd>{client.is_active ? "Active" : "Inactive"}</dd>
                  </div>
                </dl>
              </div>
            ) : null}

            {!loading && (mode === "edit" || mode === "create") && !annualInsuranceQuickEdit ? (
              <div className="modal-section-panel">
                <PassengerFields
                  value={editForm}
                  onChange={setEditForm}
                  disabled={saving}
                  showDateOfBirth
                  showAddress
                  showQualifiers
                  qualifierHint="Saved on this client record and used as their default qualifying discounts."
                />
                <AnnualInsuranceFields
                  value={{
                    has_annual_insurance: editForm.has_annual_insurance ?? false,
                    annual_insurance_expires_at: editForm.annual_insurance_expires_at,
                    annual_insurance_policy_number: editForm.annual_insurance_policy_number,
                  }}
                  onChange={(annualValue) =>
                    setEditForm((current) => ({
                      ...current,
                      ...annualValue,
                    }))
                  }
                  disabled={saving}
                />
                {mode === "edit" ? (
                  <p className="field-hint">
                    Updates apply to this person across all requests where they appear.
                  </p>
                ) : (
                  <p className="field-hint">
                    New clients are added to the registry and can be attached to requests later.
                  </p>
                )}
              </div>
            ) : null}
          </div>

          <div className="modal-actions modal-actions-footer">
            {annualInsuranceQuickEdit ? (
              <>
                <button type="button" className="modal-secondary" disabled={saving} onClick={onClose}>
                  Cancel
                </button>
                <button type="button" className="modal-primary" disabled={saving || loading} onClick={() => void handleSave()}>
                  {saving ? "Saving..." : "Save annual insurance"}
                </button>
              </>
            ) : (
              <>
            <button type="button" className="modal-secondary" disabled={saving} onClick={onClose}>
              {mode === "create" ? "Cancel" : "Close"}
            </button>
            {client && mode === "view" ? (
              <>
                {client.is_active ? (
                  <button
                    type="button"
                    className="modal-secondary danger-button"
                    disabled={saving || deactivating}
                    onClick={() => setPendingDeactivate(true)}
                  >
                    Mark inactive
                  </button>
                ) : (
                  <button type="button" className="modal-secondary" disabled={saving} onClick={() => void handleReactivate()}>
                    Reactivate
                  </button>
                )}
                <button type="button" className="modal-primary" disabled={saving} onClick={() => onModeChange("edit")}>
                  Edit client
                </button>
              </>
            ) : null}
            {client && mode === "edit" ? (
              <>
                <button type="button" className="modal-secondary" disabled={saving} onClick={() => onModeChange("view")}>
                  Cancel
                </button>
                <button type="button" className="modal-primary" disabled={saving} onClick={() => void handleSave()}>
                  {saving ? "Saving..." : "Save client"}
                </button>
              </>
            ) : null}
            {mode === "create" ? (
              <button type="button" className="modal-primary" disabled={saving} onClick={() => void handleCreate()}>
                {saving ? "Adding..." : "Add client"}
              </button>
            ) : null}
              </>
            )}
          </div>
        </div>
      </div>

      <ChickenSwitchModal
        open={pendingDeactivate}
        title="Deactivate client?"
        description="This client will be marked inactive. They will stay on existing requests but cannot be added to new ones."
        itemName={client ? `${client.first_name} ${client.last_name}` : undefined}
        switchLabel="Yes, deactivate this client"
        confirmLabel="Deactivate client"
        confirmingLabel="Deactivating..."
        hint="You can reactivate this client later from the Clients page."
        confirming={deactivating}
        onCancel={() => setPendingDeactivate(false)}
        onConfirm={() => void confirmDeactivate()}
      />
    </>
  );
}
