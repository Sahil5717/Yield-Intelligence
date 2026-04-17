import { useState, useEffect } from "react";
import { tokens as t } from "../tokens.js";
import { login, fetchDemoUsers, getStoredAuth } from "../api.js";

/**
 * LoginScreen — username/password form with optional demo-credentials hint.
 *
 * Visually matches the rest of MarketLens: off-white canvas, Geist
 * typography, teal accent. Single centered card with the wordmark,
 * form, and a demo-credentials list shown below when the backend reports
 * any (pitch-tool mode). In a production deployment with
 * MARKETLENS_HIDE_DEMO_CREDS=1 set on the server, the demo list is empty
 * and the section collapses — the login page reads as a normal SaaS
 * login.
 *
 * After successful login, routes to the correct app based on role:
 *   editor  → /editor
 *   client  → /  (Diagnosis)
 *
 * The login itself is a hard page redirect (window.location), not a
 * client-side router transition, because (a) the target URL loads a
 * different bundle (editor.js vs client.js) and (b) it triggers a fresh
 * boot of the target app which loads the user's tokened diagnosis.
 */
export function LoginScreen() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [demoUsers, setDemoUsers] = useState([]);

  // Redirect if already logged in
  useEffect(() => {
    const auth = getStoredAuth();
    if (auth?.role) {
      redirectByRole(auth.role);
    }
  }, []);

  // Load demo credentials (if any are seeded — empty in production builds)
  useEffect(() => {
    (async () => {
      const { data } = await fetchDemoUsers();
      if (data?.demo_users) setDemoUsers(data.demo_users);
    })();
  }, []);

  async function handleSubmit(e) {
    if (e) e.preventDefault();
    if (!username.trim() || !password) return;
    setSubmitting(true);
    setErrorMsg(null);
    const { data, error } = await login(username.trim(), password);
    setSubmitting(false);
    if (error) {
      // Don't leak server internals — tailor the message to what the user
      // can act on. The backend returns "Invalid credentials" for both
      // wrong-username and wrong-password to avoid account enumeration;
      // we pass that through.
      setErrorMsg(error.message || "Login failed. Try again.");
      return;
    }
    redirectByRole(data.role);
  }

  function fillDemo(u) {
    setUsername(u.username);
    setPassword(u.password_hint);
    setErrorMsg(null);
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        background: t.color.canvas,
        fontFamily: t.font.body,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: t.space[8],
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "440px",
          display: "flex",
          flexDirection: "column",
          gap: t.space[6],
        }}
      >
        {/* Brand header */}
        <div style={{ textAlign: "center" }}>
          <div
            style={{
              fontFamily: t.font.display,
              fontSize: t.size["3xl"],
              fontWeight: t.weight.semibold,
              color: t.color.textPrimary,
              letterSpacing: t.tracking.tight,
              lineHeight: t.leading.tight,
              marginBottom: t.space[2],
            }}
          >
            MarketLens
          </div>
          <div
            style={{
              fontFamily: t.font.body,
              fontSize: t.size.sm,
              color: t.color.textTertiary,
              textTransform: "uppercase",
              letterSpacing: t.tracking.wider,
              fontWeight: t.weight.medium,
            }}
          >
            Marketing ROI Analytics
          </div>
        </div>

        {/* Form card */}
        <form
          onSubmit={handleSubmit}
          style={{
            background: t.color.surface,
            border: `1px solid ${t.color.border}`,
            borderRadius: t.radius.xl,
            padding: `${t.space[8]} ${t.space[8]}`,
            boxShadow: t.shadow.card,
            display: "flex",
            flexDirection: "column",
            gap: t.space[5],
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: t.space[2] }}>
            <label htmlFor="username" style={labelStyle()}>Username</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={submitting}
              autoComplete="username"
              autoFocus
              style={inputStyle()}
            />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: t.space[2] }}>
            <label htmlFor="password" style={labelStyle()}>Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={submitting}
              autoComplete="current-password"
              style={inputStyle()}
            />
          </div>

          {errorMsg && (
            <div
              style={{
                fontFamily: t.font.body,
                fontSize: t.size.sm,
                color: t.color.negative,
                background: t.color.negativeBg,
                padding: `${t.space[2]} ${t.space[3]}`,
                borderRadius: t.radius.sm,
                borderLeft: `3px solid ${t.color.negative}`,
              }}
              role="alert"
            >
              {errorMsg}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting || !username.trim() || !password}
            style={{
              padding: `${t.space[3]} ${t.space[4]}`,
              background: t.color.accent,
              color: t.color.textInverse,
              border: "none",
              borderRadius: t.radius.sm,
              fontFamily: t.font.body,
              fontSize: t.size.md,
              fontWeight: t.weight.semibold,
              cursor: submitting || !username.trim() || !password ? "not-allowed" : "pointer",
              opacity: submitting || !username.trim() || !password ? 0.55 : 1,
              transition: `background ${t.motion.fast} ${t.motion.ease}, opacity ${t.motion.fast} ${t.motion.ease}`,
              marginTop: t.space[2],
            }}
            onMouseEnter={(e) => {
              if (!submitting && username.trim() && password) {
                e.currentTarget.style.background = t.color.accentHover;
              }
            }}
            onMouseLeave={(e) => (e.currentTarget.style.background = t.color.accent)}
          >
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        {/* Demo credentials (pitch-tool mode only) */}
        {demoUsers.length > 0 && (
          <div
            style={{
              background: t.color.surfaceSunken,
              border: `1px solid ${t.color.borderFaint}`,
              borderRadius: t.radius.md,
              padding: `${t.space[5]} ${t.space[6]}`,
              display: "flex",
              flexDirection: "column",
              gap: t.space[3],
            }}
          >
            <div
              style={{
                fontFamily: t.font.body,
                fontSize: t.size.xs,
                fontWeight: t.weight.semibold,
                color: t.color.textTertiary,
                textTransform: "uppercase",
                letterSpacing: t.tracking.wider,
              }}
            >
              Demo credentials
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: t.space[1] }}>
              {demoUsers.map((u) => (
                <button
                  key={u.username}
                  type="button"
                  onClick={() => fillDemo(u)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: t.space[3],
                    padding: `${t.space[2]} ${t.space[3]}`,
                    background: "none",
                    border: "1px solid transparent",
                    borderRadius: t.radius.sm,
                    fontFamily: t.font.body,
                    fontSize: t.size.sm,
                    color: t.color.textPrimary,
                    cursor: "pointer",
                    textAlign: "left",
                    transition: `background ${t.motion.fast} ${t.motion.ease}, border-color ${t.motion.fast} ${t.motion.ease}`,
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = t.color.surface;
                    e.currentTarget.style.borderColor = t.color.border;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "none";
                    e.currentTarget.style.borderColor = "transparent";
                  }}
                >
                  <span style={{ fontFamily: t.font.mono, fontSize: t.size.sm }}>
                    {u.username}
                  </span>
                  <span
                    style={{
                      fontFamily: t.font.body,
                      fontSize: t.size.xs,
                      color: t.color.textTertiary,
                      textTransform: "uppercase",
                      letterSpacing: t.tracking.wider,
                      fontWeight: t.weight.medium,
                    }}
                  >
                    {u.role}
                  </span>
                </button>
              ))}
            </div>
            <div
              style={{
                fontFamily: t.font.body,
                fontSize: t.size.xs,
                color: t.color.textTertiary,
                lineHeight: t.leading.normal,
                marginTop: t.space[2],
              }}
            >
              Click any row to auto-fill the form, then Sign in. All demo accounts use password "demo1234".
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function labelStyle() {
  return {
    fontFamily: t.font.body,
    fontSize: t.size.xs,
    fontWeight: t.weight.semibold,
    color: t.color.textSecondary,
    textTransform: "uppercase",
    letterSpacing: t.tracking.wider,
  };
}

function inputStyle() {
  return {
    padding: `${t.space[3]} ${t.space[4]}`,
    border: `1px solid ${t.color.border}`,
    borderRadius: t.radius.sm,
    fontFamily: t.font.body,
    fontSize: t.size.md,
    color: t.color.textPrimary,
    background: t.color.canvas,
    outline: "none",
    transition: `border-color ${t.motion.fast} ${t.motion.ease}`,
  };
}

/**
 * Redirect a freshly-logged-in user to the app that matches their role.
 * editor  → /editor (full shell with editor controls)
 * client  → /       (read-only client shell)
 * anything else → /  (safe default)
 */
function redirectByRole(role) {
  if (role === "editor") {
    window.location.href = "/editor";
  } else {
    window.location.href = "/";
  }
}
