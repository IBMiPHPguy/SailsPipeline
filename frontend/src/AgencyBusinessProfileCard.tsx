import { FormEvent, useCallback, useEffect, useState } from "react";
import { US_STATES } from "./formOptions";
import { fetchAgencyProfile, updateAgencyBusinessAddress } from "./teamApi";
import type { AgencyBusinessAddressUpdate, AgencyProfile } from "./types";

type AddressDraft = {
  business_address_line_1: string;
  business_address_line_2: string;
  business_city: string;
  business_state_or_province: string;
  business_postal_code: string;
  business_country: string;
};

function emptyDraft(): AddressDraft {
  return {
    business_address_line_1: "",
    business_address_line_2: "",
    business_city: "",
    business_state_or_province: "",
    business_postal_code: "",
    business_country: "United States",
  };
}

function profileToDraft(profile: AgencyProfile): AddressDraft {
  return {
    business_address_line_1: profile.business_address_line_1 ?? "",
    business_address_line_2: profile.business_address_line_2 ?? "",
    business_city: profile.business_city ?? "",
    business_state_or_province: profile.business_state_or_province ?? "",
    business_postal_code: profile.business_postal_code ?? "",
    business_country: profile.business_country ?? "United States",
  };
}

function buildUpdatePayload(original: AgencyProfile, draft: AddressDraft): AgencyBusinessAddressUpdate | null {
  const payload: AgencyBusinessAddressUpdate = {};
  const fields: (keyof AddressDraft)[] = [
    "business_address_line_1",
    "business_address_line_2",
    "business_city",
    "business_state_or_province",
    "business_postal_code",
    "business_country",
  ];

  for (const field of fields) {
    const nextValue = draft[field].trim() || null;
    const previousValue = (original[field] ?? "").trim() || null;
    if (nextValue !== previousValue) {
      payload[field] = nextValue;
    }
  }

  return Object.keys(payload).length > 0 ? payload : null;
}

export default function AgencyBusinessProfileCard() {
  const [profile, setProfile] = useState<AgencyProfile | null>(null);
  const [draft, setDraft] = useState<AddressDraft>(emptyDraft());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadProfile = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const nextProfile = await fetchAgencyProfile();
      setProfile(nextProfile);
      setDraft(profileToDraft(nextProfile));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load agency profile.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProfile();
  }, [loadProfile]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!profile || saving) {
      return;
    }

    const payload = buildUpdatePayload(profile, draft);
    if (!payload) {
      setSuccess("No changes to save.");
      return;
    }

    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const updated = await updateAgencyBusinessAddress(payload);
      setProfile(updated);
      setDraft(profileToDraft(updated));
      setSuccess("Business address saved. Master Terms governing law uses your state or province.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to save business address.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="card section-card agency-business-profile-card">
      <header className="section-card-header">
        <div>
          <h3>Agency business address</h3>
          <p className="muted">
            Used for agency records and to set governing law state in Master Terms &amp; Conditions.
          </p>
        </div>
      </header>
      <div className="section-card-body">
        {loading ? <p className="muted">Loading agency profile…</p> : null}
        {error ? <p className="status error">{error}</p> : null}
        {success ? <p className="status success">{success}</p> : null}

        {!loading && profile ? (
          <form className="agency-business-profile-form" onSubmit={(event) => void handleSubmit(event)}>
            <p className="agency-business-profile-name">
              <strong>{profile.name}</strong>
              <span className="muted"> · {profile.organization_handle}</span>
            </p>

            <label>
              Address line 1
              <input
                type="text"
                value={draft.business_address_line_1}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, business_address_line_1: event.target.value }))
                }
                maxLength={120}
                required
              />
            </label>

            <label>
              Address line 2
              <input
                type="text"
                value={draft.business_address_line_2}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, business_address_line_2: event.target.value }))
                }
                maxLength={120}
              />
            </label>

            <div className="agency-business-profile-grid">
              <label>
                City
                <input
                  type="text"
                  value={draft.business_city}
                  onChange={(event) => setDraft((current) => ({ ...current, business_city: event.target.value }))}
                  maxLength={80}
                  required
                />
              </label>

              <label>
                State / province
                <input
                  type="text"
                  list="agency-business-state-options"
                  value={draft.business_state_or_province}
                  onChange={(event) =>
                    setDraft((current) => ({ ...current, business_state_or_province: event.target.value }))
                  }
                  maxLength={50}
                  required
                />
              </label>

              <label>
                Postal code
                <input
                  type="text"
                  value={draft.business_postal_code}
                  onChange={(event) =>
                    setDraft((current) => ({ ...current, business_postal_code: event.target.value }))
                  }
                  maxLength={20}
                  required
                />
              </label>

              <label>
                Country
                <input
                  type="text"
                  value={draft.business_country}
                  onChange={(event) => setDraft((current) => ({ ...current, business_country: event.target.value }))}
                  maxLength={80}
                />
              </label>
            </div>

            <datalist id="agency-business-state-options">
              {US_STATES.map((state) => (
                <option key={state} value={state} />
              ))}
            </datalist>

            <button type="submit" disabled={saving}>
              {saving ? "Saving…" : "Save business address"}
            </button>
          </form>
        ) : null}
      </div>
    </section>
  );
}
