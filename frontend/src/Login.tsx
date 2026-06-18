import { FormEvent, useState } from "react";
import { login, register } from "./authApi";
import { validatePassword } from "./authStorage";
import { BRAND_APP_TITLE } from "./branding";
import type { User } from "./types";

type LoginProps = {
  onAuthenticated: (user: User) => void;
};

export default function Login({ onAuthenticated }: LoginProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    setSubmitting(true);

    try {
      if (mode === "register") {
        const passwordError = validatePassword(password);
        if (passwordError) {
          throw new Error(passwordError);
        }
        if (password !== confirmPassword) {
          throw new Error("Passwords do not match.");
        }

        await register({ username, email, password });
        setMessage("Account created. Signing you in...");
        const auth = await login(username, password);
        onAuthenticated(auth.user);
        return;
      }

      const auth = await login(username, password);
      onAuthenticated(auth.user);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Authentication failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page auth-page">
      <section className="card auth-card">
        <h1>{BRAND_APP_TITLE}</h1>
        <p className="auth-subtitle">Sign in to manage cruise travel requests.</p>

        <div className="auth-toggle">
          <button
            type="button"
            className={mode === "login" ? "active" : ""}
            onClick={() => setMode("login")}
          >
            Login
          </button>
          <button
            type="button"
            className={mode === "register" ? "active" : ""}
            onClick={() => setMode("register")}
          >
            Register
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <label>
            Username
            <input
              required
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
            />
          </label>

          {mode === "register" ? (
            <label>
              Email
              <input
                required
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="email"
              />
            </label>
          ) : null}

          <label>
            Password
            <input
              required
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
            />
          </label>

          {mode === "register" ? (
            <>
              <label>
                Confirm password
                <input
                  required
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  autoComplete="new-password"
                />
              </label>
              <p className="password-rules">
                Password must be more than 10 characters with at least one uppercase letter,
                one lowercase letter, one numeral, and one special character. Spaces are not
                allowed.
              </p>
            </>
          ) : null}

          <button type="submit" disabled={submitting}>
            {submitting ? "Please wait..." : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>

        {message ? <p className="status success">{message}</p> : null}
        {error ? <p className="status error">{error}</p> : null}
      </section>
    </main>
  );
}
