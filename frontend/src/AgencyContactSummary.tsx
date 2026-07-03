import { useCallback, useEffect, useState } from "react";
import { fetchAgencySettings } from "./agencySettingsApi";

export default function AgencyContactSummary() {
  const [address, setAddress] = useState<string | null>(null);
  const [phone, setPhone] = useState<string | null>(null);
  const [agencyName, setAgencyName] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadContact = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const settings = await fetchAgencySettings();
      setAgencyName(settings.agency_name);
      setAddress(settings.business_address ?? null);
      setPhone(settings.business_phone ?? null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load agency contact details.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadContact();
  }, [loadContact]);

  return (
    <section className="card section-card agency-contact-summary-card">
      <header className="section-card-header">
        <div>
          <h3>Agency contact</h3>
          <p className="muted">Managed centrally in Agency Settings (address and phone).</p>
        </div>
      </header>
      <div className="section-card-body">
        {loading ? <p className="muted">Loading contact details…</p> : null}
        {error ? <p className="status error">{error}</p> : null}
        {!loading && !error ? (
          <dl className="agency-contact-summary-list">
            <div>
              <dt>Agency</dt>
              <dd>{agencyName || "—"}</dd>
            </div>
            <div>
              <dt>Business phone</dt>
              <dd>{phone || "—"}</dd>
            </div>
            <div>
              <dt>Business address</dt>
              <dd>{address || "—"}</dd>
            </div>
          </dl>
        ) : null}
      </div>
    </section>
  );
}
