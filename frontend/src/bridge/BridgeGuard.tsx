import { useCallback, useEffect, useState, type ReactNode } from "react";
import { fetchCurrentUser, logout } from "../authApi";
import { clearToken, getToken } from "../authStorage";
import { isPlatformSuperAdmin } from "../tenantRoles";
import type { User } from "../types";
import BridgeLogin from "./BridgeLogin";
import "../App.css";
import "../bridge-portal.css";

type BridgeGuardProps = {
  children: (user: User) => ReactNode;
};

type GuardState =
  | { status: "loading" }
  | { status: "unauthenticated" }
  | { status: "forbidden"; user: User }
  | { status: "allowed"; user: User };

export default function BridgeGuard({ children }: BridgeGuardProps) {
  const [state, setState] = useState<GuardState>({ status: "loading" });

  const applyUser = useCallback((user: User) => {
    if (!isPlatformSuperAdmin(user.role)) {
      setState({ status: "forbidden", user });
      return;
    }
    setState({ status: "allowed", user });
  }, []);

  useEffect(() => {
    async function verifyAccess() {
      if (!getToken("bridge")) {
        setState({ status: "unauthenticated" });
        return;
      }

      try {
        const user = await fetchCurrentUser("bridge");
        applyUser(user);
      } catch {
        clearToken("bridge");
        setState({ status: "unauthenticated" });
      }
    }

    void verifyAccess();
  }, [applyUser]);

  if (state.status === "loading") {
    return (
      <main className="page bridge-page">
        <section className="card bridge-card">
          <header className="bridge-card-header">
            <h2>The Bridge</h2>
          </header>
          <div className="bridge-card-body">
            <p className="muted">Verifying Bridge access…</p>
          </div>
        </section>
      </main>
    );
  }

  if (state.status === "unauthenticated") {
    return <BridgeLogin onAuthenticated={applyUser} />;
  }

  if (state.status === "forbidden") {
    function handleSignOut() {
      logout("bridge");
      setState({ status: "unauthenticated" });
    }

    return (
      <main className="page bridge-page">
        <section className="card bridge-forbidden bridge-card">
          <header className="bridge-card-header">
            <h2>403 — Forbidden</h2>
          </header>
          <div className="bridge-card-body">
            <p>
              The Bridge is restricted to platform super administrators. Signed in as{" "}
              <strong>{state.user.username}</strong> ({state.user.role}).
            </p>
            <p className="muted">
              Use the platform operator account (for example, the seeded <code>bridge</code> user).
            </p>
            <div className="bridge-toolbar">
              <button type="button" className="secondary-button" onClick={handleSignOut}>
                Sign out
              </button>
            </div>
          </div>
        </section>
      </main>
    );
  }

  return <>{children(state.user)}</>;
}
