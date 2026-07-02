import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  fetchRequestCcAuthorizations,
  purgeRequestCcAuthorization,
  revealRequestCcAuthorization,
} from "./ccAuthApi";
import type { CcAuthRevealedCard, CcAuthSummary } from "./types";
import { formatTimestamp } from "./utils";

type CcAuthVaultSectionProps = {
  requestId: number;
  disabled?: boolean;
};

function formatCardNumberDisplay(value: string): string {
  return value.replace(/(\d{4})(?=\d)/g, "$1 ").trim();
}

export default function CcAuthVaultSection({ requestId, disabled = false }: CcAuthVaultSectionProps) {
  const [authorizations, setAuthorizations] = useState<CcAuthSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [vaultAccessKey, setVaultAccessKey] = useState("");
  const [activeAuthorizationId, setActiveAuthorizationId] = useState<string | null>(null);
  const [revealedCard, setRevealedCard] = useState<CcAuthRevealedCard | null>(null);
  const [revealing, setRevealing] = useState(false);
  const [purging, setPurging] = useState(false);
  const [purgeConfirmId, setPurgeConfirmId] = useState<string | null>(null);
  const [message, setMessage] = useState("");

  const loadAuthorizations = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const records = await fetchRequestCcAuthorizations(requestId);
      setAuthorizations(records);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load card authorizations.");
    } finally {
      setLoading(false);
    }
  }, [requestId]);

  useEffect(() => {
    void loadAuthorizations();
  }, [loadAuthorizations]);

  async function handleReveal(event: FormEvent<HTMLFormElement>, authorizationId: string) {
    event.preventDefault();
    if (!vaultAccessKey.trim()) {
      setError("Enter the vault access key to reveal card data.");
      return;
    }

    setRevealing(true);
    setError("");
    setMessage("");
    try {
      const result = await revealRequestCcAuthorization(requestId, authorizationId, vaultAccessKey.trim());
      setActiveAuthorizationId(authorizationId);
      setRevealedCard(result.card);
      setMessage("Card data revealed. Enter it into the cruise line portal, then purge immediately.");
    } catch (revealError) {
      setRevealedCard(null);
      setActiveAuthorizationId(null);
      setError(revealError instanceof Error ? revealError.message : "Unable to reveal card data.");
    } finally {
      setRevealing(false);
    }
  }

  async function handlePurge(authorizationId: string) {
    setPurging(true);
    setError("");
    setMessage("");
    try {
      await purgeRequestCcAuthorization(requestId, authorizationId);
      setRevealedCard(null);
      setActiveAuthorizationId(null);
      setPurgeConfirmId(null);
      setVaultAccessKey("");
      setMessage("Card data securely purged. Authorization audit record retained.");
      await loadAuthorizations();
    } catch (purgeError) {
      setError(purgeError instanceof Error ? purgeError.message : "Unable to purge card data.");
    } finally {
      setPurging(false);
    }
  }

  const vaultRecords = authorizations.filter((record) => record.status === "completed");

  return (
    <section className="cc-auth-vault-card">
      <header className="cc-auth-vault-header">
        <div>
          <h3>Transient card vault</h3>
          <p className="muted">
            Burn-after-reading storage for passenger card authorizations. Reveal only when entering the cruise line
            portal, then purge immediately.
          </p>
        </div>
      </header>

      <div className="cc-auth-vault-body">
        {loading ? <p className="muted">Loading authorization vault…</p> : null}
        {error ? <p className="cc-auth-vault-error">{error}</p> : null}
        {message ? <p className="cc-auth-vault-success">{message}</p> : null}

        {!loading && vaultRecords.length === 0 ? (
          <p className="muted">No completed card authorizations yet for this request.</p>
        ) : null}

        {!loading && vaultRecords.length > 0 ? (
          <div className="cc-auth-vault-list">
            {vaultRecords.map((record) => {
              const isActive = activeAuthorizationId === record.id;
              const canReveal = record.has_card_data && !disabled;
              const showRevealed = isActive && revealedCard !== null;

              return (
                <article className="cc-auth-vault-item" key={record.id}>
                  <header className="cc-auth-vault-item-header">
                    <div>
                      <strong>Authorization {record.id.slice(0, 8)}…</strong>
                      <div className="meta">
                        Status: {record.status}
                        {record.card_data_purged ? " · purged" : record.has_card_data ? " · vault active" : ""}
                      </div>
                      <div className="meta">
                        Completed: {record.completed_at ? formatTimestamp(record.completed_at) : "—"}
                      </div>
                    </div>
                  </header>

                  {canReveal && !showRevealed ? (
                    <form className="cc-auth-vault-reveal-form" onSubmit={(event) => void handleReveal(event, record.id)}>
                      <label>
                        Vault access key
                        <input
                          type="password"
                          value={vaultAccessKey}
                          onChange={(event) => setVaultAccessKey(event.target.value)}
                          placeholder="Enter secure vault key"
                          disabled={revealing || purging}
                          autoComplete="off"
                        />
                      </label>
                      <button type="submit" className="modal-secondary" disabled={revealing || purging}>
                        {revealing ? "Unlocking…" : "Reveal card data"}
                      </button>
                    </form>
                  ) : null}

                  {showRevealed && revealedCard ? (
                    <section className="cc-auth-vault-revealed">
                      <h4>Card data (sensitive)</h4>
                      <dl className="cc-auth-vault-revealed-grid">
                        <div>
                          <dt>Cardholder</dt>
                          <dd>{revealedCard.cardholder_name}</dd>
                        </div>
                        <div>
                          <dt>Card number</dt>
                          <dd>{formatCardNumberDisplay(revealedCard.card_number)}</dd>
                        </div>
                        <div>
                          <dt>Expiration</dt>
                          <dd>{revealedCard.expiration}</dd>
                        </div>
                        <div>
                          <dt>Security code</dt>
                          <dd>{revealedCard.security_code}</dd>
                        </div>
                      </dl>

                      {purgeConfirmId === record.id ? (
                        <div className="cc-auth-vault-purge-confirm">
                          <p>
                            This permanently erases encrypted card data from the vault. The completed authorization audit
                            record will remain.
                          </p>
                          <button
                            type="button"
                            className="cc-auth-vault-purge-button"
                            disabled={purging || disabled}
                            onClick={() => void handlePurge(record.id)}
                          >
                            {purging ? "Purging…" : "Confirm purge now"}
                          </button>
                          <button
                            type="button"
                            className="modal-secondary"
                            disabled={purging}
                            onClick={() => setPurgeConfirmId(null)}
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          className="cc-auth-vault-purge-button"
                          disabled={purging || disabled}
                          onClick={() => setPurgeConfirmId(record.id)}
                        >
                          Mark as Processed &amp; Securely Purge Card Data
                        </button>
                      )}
                    </section>
                  ) : null}

                  {record.card_data_purged ? (
                    <p className="meta cc-auth-vault-purged-note">
                      Card data purged. Authorization audit retained for compliance.
                    </p>
                  ) : null}
                </article>
              );
            })}
          </div>
        ) : null}
      </div>
    </section>
  );
}
