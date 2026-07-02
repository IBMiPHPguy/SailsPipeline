import { FormEvent, useEffect, useMemo, useState } from "react";
import { completeCcAuth, validateCcAuthToken } from "./ccAuthApi";
import {
  formatCardNumberInput,
  formatExpirationInput,
  toCcAuthCardPayload,
  validateCcAuthCardForm,
  type CcAuthCardForm,
} from "./ccAuthCardValidation";
import { BRAND_APP_TITLE, BRAND_NAME } from "./branding";
import type { CcAuthValidateResponse } from "./types";
import { formatDate } from "./utils";
import "./bridge-portal.css";
import "./cc-auth-portal.css";

type CcAuthPortalPageProps = {
  token: string;
};

function formatMoney(value: string | number): string {
  const amount = Number(value);
  if (!Number.isFinite(amount)) {
    return String(value);
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(amount);
}

function formatExpiryDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString(undefined, {
    month: "long",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function initialCardForm(passengerName: string): CcAuthCardForm {
  return {
    cardholderName: passengerName,
    cardNumber: "",
    expiration: "",
    securityCode: "",
  };
}

export default function CcAuthPortalPage({ token }: CcAuthPortalPageProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [portal, setPortal] = useState<CcAuthValidateResponse | null>(null);
  const [cardForm, setCardForm] = useState<CcAuthCardForm>(initialCardForm(""));
  const [completed, setCompleted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [completionMessage, setCompletionMessage] = useState("");

  useEffect(() => {
    async function loadPortal() {
      if (!token) {
        setError("This authorization link is missing a secure token.");
        setLoading(false);
        return;
      }

      try {
        const payload = await validateCcAuthToken(token);
        setPortal(payload);
        setCardForm(initialCardForm(payload.passenger_name));
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load authorization details.");
      } finally {
        setLoading(false);
      }
    }

    void loadPortal();
  }, [token]);

  const sortedCruises = useMemo(
    () =>
      portal
        ? [...portal.cruises].sort(
            (left, right) =>
              left.sailing_date.localeCompare(right.sailing_date) || left.ship.localeCompare(right.ship),
          )
        : [],
    [portal],
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || completed) {
      return;
    }

    const validationError = validateCcAuthCardForm(cardForm);
    if (validationError) {
      setError(validationError);
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      const result = await completeCcAuth(token, toCcAuthCardPayload(cardForm));
      setCompleted(true);
      setCompletionMessage(result.message);
      setCardForm(initialCardForm(""));
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to complete authorization.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page auth-page cc-auth-portal-page">
      <section className="card bridge-card cc-auth-portal-card">
        <header className="bridge-card-header cc-auth-portal-header">
          <div className="cc-auth-portal-brand">
            <img src="/sailspipeline-logo.png" alt={BRAND_APP_TITLE} className="auth-logo" />
            <div>
              <h1>Secure card authorization</h1>
              <p className="muted">Encrypted passenger portal · {BRAND_NAME}</p>
            </div>
          </div>
        </header>

        <div className="bridge-card-body cc-auth-portal-body">
          {loading ? (
            <p className="muted">Verifying your secure authorization link…</p>
          ) : null}

          {!loading && error && !portal ? (
            <section className="cc-auth-portal-alert cc-auth-portal-alert--error">
              <h2>Link unavailable</h2>
              <p>{error}</p>
              <p className="muted">
                For your security, authorization links expire after 48 hours. Contact your travel advisor if you need a
                new link.
              </p>
            </section>
          ) : null}

          {!loading && portal && !completed ? (
            <>
              <section className="cc-auth-portal-summary">
                <p className="cc-auth-portal-greeting">
                  Hello <strong>{portal.passenger_name}</strong>,
                </p>
                <p>
                  {portal.agency_name} has requested authorization for the deposit below. Review your sailing details,
                  then enter your card securely for your travel advisor.
                </p>
                <div className="cc-auth-portal-total">
                  <span className="cc-auth-portal-total-label">Total deposit authorizing</span>
                  <strong className="cc-auth-portal-total-amount">{formatMoney(portal.total_deposit_due)}</strong>
                  <span className="muted">
                    Across {sortedCruises.length} accepted sailing{sortedCruises.length === 1 ? "" : "s"}
                  </span>
                </div>
                <p className="cc-auth-portal-expiry muted">Link expires: {formatExpiryDate(portal.expires_at)}</p>
              </section>

              <section className="cc-auth-portal-cruises">
                <h2>Sailing details</h2>
                <div className="cc-auth-portal-cruise-list">
                  {sortedCruises.map((cruise, index) => (
                    <article className="cc-auth-portal-cruise-card" key={`${cruise.ship}-${cruise.sailing_date}-${index}`}>
                      <header>
                        <span className="cc-auth-portal-cruise-badge">Sailing {index + 1}</span>
                        <h3>
                          {cruise.cruise_line} · {cruise.ship}
                        </h3>
                        <p className="muted">
                          {cruise.number_of_nights} nights · {cruise.itinerary_name}
                        </p>
                      </header>
                      <dl className="cc-auth-portal-cruise-grid">
                        <div>
                          <dt>Passenger</dt>
                          <dd>{portal.passenger_name}</dd>
                        </div>
                        <div>
                          <dt>Email</dt>
                          <dd>{portal.passenger_email}</dd>
                        </div>
                        <div>
                          <dt>Sailing date</dt>
                          <dd>{formatDate(cruise.sailing_date)}</dd>
                        </div>
                        <div>
                          <dt>Cabin type</dt>
                          <dd>{cruise.cabin_type}</dd>
                        </div>
                        <div>
                          <dt>Deposit due</dt>
                          <dd>{formatMoney(cruise.deposit_amount)}</dd>
                        </div>
                        <div>
                          <dt>Final payment due</dt>
                          <dd>{formatDate(cruise.final_payment_due_date)}</dd>
                        </div>
                      </dl>
                    </article>
                  ))}
                </div>
              </section>

              <section className="cc-auth-portal-form-card">
                <header className="cc-auth-portal-form-header">
                  <h2>Payment details</h2>
                  <p className="muted">
                    Enter your card below. Details are encrypted in a temporary vault for your advisor and purged after
                    they enter them into the cruise line booking portal.
                  </p>
                </header>

                <form className="cc-auth-portal-form" onSubmit={(event) => void handleSubmit(event)} autoComplete="off">
                  <div className="cc-auth-portal-form-grid">
                    <label>
                      Cardholder name
                      <input
                        type="text"
                        name="cc-name"
                        autoComplete="cc-name"
                        value={cardForm.cardholderName}
                        onChange={(event) =>
                          setCardForm((current) => ({ ...current, cardholderName: event.target.value }))
                        }
                        required
                      />
                    </label>
                    <label>
                      Card number
                      <input
                        type="text"
                        name="cc-number"
                        inputMode="numeric"
                        autoComplete="cc-number"
                        value={cardForm.cardNumber}
                        onChange={(event) =>
                          setCardForm((current) => ({
                            ...current,
                            cardNumber: formatCardNumberInput(event.target.value),
                          }))
                        }
                        placeholder="1234 5678 9012 3456"
                        required
                      />
                    </label>
                    <label>
                      Expiration (MM/YY)
                      <input
                        type="text"
                        name="cc-exp"
                        inputMode="numeric"
                        autoComplete="cc-exp"
                        value={cardForm.expiration}
                        onChange={(event) =>
                          setCardForm((current) => ({
                            ...current,
                            expiration: formatExpirationInput(event.target.value),
                          }))
                        }
                        placeholder="MM/YY"
                        required
                      />
                    </label>
                    <label>
                      Security code
                      <input
                        type="password"
                        name="cc-csc"
                        inputMode="numeric"
                        autoComplete="cc-csc"
                        value={cardForm.securityCode}
                        onChange={(event) =>
                          setCardForm((current) => ({
                            ...current,
                            securityCode: event.target.value.replace(/\D/g, "").slice(0, 4),
                          }))
                        }
                        placeholder="CVV"
                        required
                      />
                    </label>
                  </div>

                  <p className="cc-auth-portal-security-note">
                    For your security, this authorization link is encrypted and will expire in 48 hours. Card details are
                    never stored in plain text.
                  </p>

                  {error ? <p className="cc-auth-portal-inline-error">{error}</p> : null}

                  <button type="submit" className="cc-auth-portal-submit" disabled={submitting}>
                    {submitting ? "Authorizing…" : "Securely Authorize Card"}
                  </button>
                </form>
              </section>
            </>
          ) : null}

          {!loading && completed ? (
            <section className="cc-auth-portal-alert cc-auth-portal-alert--success">
              <h2>Authorization complete</h2>
              <p>{completionMessage || "Your card authorization has been recorded."}</p>
              <p className="muted">
                Thank you, {portal?.passenger_name ?? "traveler"}. Your travel advisor will enter this card into the
                cruise line booking system and securely purge it from the vault.
              </p>
            </section>
          ) : null}
        </div>
      </section>
    </main>
  );
}
