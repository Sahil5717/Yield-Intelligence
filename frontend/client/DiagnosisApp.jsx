import { useState, useEffect } from "react";
import { tokens as t } from "./tokens.js";
import { ensureDiagnosisReady, ensurePlanReady, ensureScenarioReady, getStoredAuth, setUnauthorizedHandler, logout } from "./api.js";
import { Diagnosis } from "./screens/Diagnosis.jsx";
import { Plan } from "./screens/Plan.jsx";
import { Scenarios } from "./screens/Scenarios.jsx";

/**
 * DiagnosisApp — client-mode shell for MarketLens.
 *
 * Loads the published diagnosis (with any EY edits already layered in by
 * the backend when it receives view=client) and renders it read-only.
 * No editor affordances, no mutation endpoints ever called. A client
 * view cannot accidentally edit anything because it has no edit handlers
 * to pass to the screen.
 *
 * Auth guard (v18e): on mount, checks localStorage for a valid auth
 * token. If none exists, redirects to /login. Both `editor` and `client`
 * roles are permitted to view this shell — editors use it for preview.
 * If the backend ever returns 401 (expired token, revoked user), the
 * api layer clears storage and triggers a redirect via the handler
 * registered in setUnauthorizedHandler.
 *
 * Screen routing: reads ?screen= from the URL. Values: "diagnosis"
 * (default), "plan".
 *
 * For the EY-facing editor version, see EditorApp.jsx.
 */
function getScreenFromUrl() {
  if (typeof window === "undefined") return "diagnosis";
  const params = new URLSearchParams(window.location.search);
  const s = params.get("screen");
  if (s === "plan") return "plan";
  if (s === "scenarios") return "scenarios";
  return "diagnosis";
}

function redirectToLogin() {
  if (typeof window !== "undefined") {
    // Preserve the intended screen as a post-login hint, wire-in later
    window.location.href = "/login";
  }
}

export default function DiagnosisApp() {
  const screen = getScreenFromUrl();
  const [state, setState] = useState({ status: "loading", data: null, error: null });
  const [auth, setAuth] = useState(null);

  useEffect(() => {
    // Auth guard: require any valid token. Both editor and client roles
    // are allowed on this shell (editor uses it for "Preview as client").
    const stored = getStoredAuth();
    if (!stored?.token) {
      redirectToLogin();
      return;
    }
    setAuth(stored);

    // Register 401 handler so expired-token responses redirect cleanly
    setUnauthorizedHandler(redirectToLogin);

    (async () => {
      const loader =
        screen === "plan" ? ensurePlanReady :
        screen === "scenarios" ? ensureScenarioReady :
        ensureDiagnosisReady;
      const { data, error } = await loader("client");
      if (data) {
        setState({ status: "ready", data, error: null });
      } else {
        setState({ status: "error", data: null, error });
      }
    })();
  }, [screen]);

  // While redirecting, render nothing (avoids a flash of the shell chrome
  // before window.location.href takes effect).
  if (!auth) return null;

  return (
    <div style={{ minHeight: "100vh", background: t.color.canvas, fontFamily: t.font.body }}>
      <GlobalStyles />
      <Header currentScreen={screen} auth={auth} />

      {state.status === "loading" && <LoadingView />}
      {state.status === "error" && <ErrorView error={state.error} />}
      {state.status === "ready" && screen === "diagnosis" && (
        <Diagnosis data={state.data} editorMode={false} />
      )}
      {state.status === "ready" && screen === "plan" && (
        <Plan data={state.data} editorMode={false} />
      )}
      {state.status === "ready" && screen === "scenarios" && (
        <Scenarios data={state.data} view="client" />
      )}

      <Footer />
    </div>
  );
}

function GlobalStyles() {
  return (
    <style>{`
      @import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;500&display=swap');
      * { box-sizing: border-box; margin: 0; padding: 0; }
      body {
        font-family: 'Geist', system-ui, -apple-system, sans-serif;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        background: ${t.color.canvas};
        color: ${t.color.textPrimary};
      }
      button { font-family: inherit; }
      ::-webkit-scrollbar { width: 10px; height: 10px; }
      ::-webkit-scrollbar-track { background: transparent; }
      ::-webkit-scrollbar-thumb { background: ${t.color.border}; border-radius: 5px; }
      ::-webkit-scrollbar-thumb:hover { background: ${t.color.borderStrong}; }

      @keyframes heroFadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
      @keyframes kpiFadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
      @keyframes findingFadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
      @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      @keyframes modalFadeIn { from { opacity: 0; } to { opacity: 1; } }
      @keyframes modalSlideIn { from { opacity: 0; transform: translateY(12px) scale(0.98); } to { opacity: 1; transform: translateY(0) scale(1); } }
      @keyframes toastSlideIn { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
    `}</style>
  );
}

/**
 * Header — client-mode: MarketLens wordmark + engagement metadata.
 *
 * Includes minimal screen nav (Diagnosis / Plan) as text links. This is
 * deliberately understated — the client is in a deliverable, not a
 * browsing tool; two screens need two clicks, not a full nav bar. When
 * more screens ship (Scenarios, Channel Deep Dive) we can promote this
 * to a proper tab bar.
 */
function Header({ currentScreen = "diagnosis", auth = null }) {
  return (
    <header
      style={{
        position: "sticky",
        top: 0,
        zIndex: 10,
        background: `${t.color.canvas}CC`,
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
        borderBottom: `1px solid ${t.color.borderFaint}`,
      }}
    >
      <div
        style={{
          maxWidth: t.layout.gridWidth,
          margin: "0 auto",
          padding: `0 ${t.space[8]}`,
          height: t.layout.headerHeight,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: t.space[6] }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: t.space[3] }}>
            <span
              style={{
                fontFamily: t.font.display,
                fontSize: t.size.lg,
                fontWeight: t.weight.semibold,
                color: t.color.textPrimary,
                letterSpacing: t.tracking.tight,
              }}
            >
              MarketLens
            </span>
          </div>

          <nav style={{ display: "flex", alignItems: "center", gap: t.space[4] }}>
            <NavLink label="Diagnosis" screen="diagnosis" active={currentScreen === "diagnosis"} />
            <NavLink label="Plan" screen="plan" active={currentScreen === "plan"} />
            <NavLink label="Scenarios" screen="scenarios" active={currentScreen === "scenarios"} />
          </nav>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: t.space[4],
            fontFamily: t.font.body,
            fontSize: t.size.xs,
            color: t.color.textTertiary,
          }}
        >
          <span>Demo Client · FY 2025</span>
          {auth && <UserChip auth={auth} />}
        </div>
      </div>
    </header>
  );
}

/**
 * UserChip — signed-in user indicator with a Sign out action.
 *
 * Deliberately plain — a username in the muted tone of the rest of the
 * header metadata, with a small "Sign out" link beside it. No dropdown
 * menu, no avatar, no dot indicator — there's only one user action
 * (sign out) so hiding it behind a menu toggle would be friction
 * without benefit.
 */
function UserChip({ auth }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: t.space[3] }}>
      <div style={{ display: "flex", alignItems: "center", gap: t.space[2] }}>
        <span
          style={{
            fontFamily: t.font.body,
            fontSize: t.size.xs,
            fontWeight: t.weight.medium,
            color: t.color.textSecondary,
          }}
        >
          {auth.username}
        </span>
        <span
          style={{
            fontFamily: t.font.body,
            fontSize: t.size.xs,
            fontWeight: t.weight.semibold,
            color: t.color.textTertiary,
            textTransform: "uppercase",
            letterSpacing: t.tracking.wider,
            padding: `2px ${t.space[2]}`,
            borderRadius: t.radius.sm,
            background: t.color.surfaceSunken,
            border: `1px solid ${t.color.borderFaint}`,
          }}
        >
          {auth.role}
        </span>
      </div>
      <button
        onClick={logout}
        style={{
          background: "none",
          border: "none",
          padding: 0,
          fontFamily: t.font.body,
          fontSize: t.size.xs,
          color: t.color.accent,
          cursor: "pointer",
          fontWeight: t.weight.medium,
        }}
      >
        Sign out
      </button>
    </div>
  );
}

/**
 * NavLink — a single screen link in the header nav.
 *
 * Full page reload on click (href to ?screen=X). Using <a> rather than
 * a JS-routed click handler: (1) matches browser back-button expectations,
 * (2) avoids adding routing library this session, (3) the data refetch
 * on screen change is what we want anyway — each screen has its own
 * backend endpoint and its own cold-start.
 */
function NavLink({ label, screen, active }) {
  return (
    <a
      href={`?screen=${screen}`}
      style={{
        fontFamily: t.font.body,
        fontSize: t.size.sm,
        fontWeight: active ? t.weight.semibold : t.weight.medium,
        color: active ? t.color.textPrimary : t.color.textSecondary,
        textDecoration: "none",
        padding: `${t.space[2]} 0`,
        borderBottom: `2px solid ${active ? t.color.accent : "transparent"}`,
        transition: `color ${t.motion.fast} ${t.motion.ease}, border-color ${t.motion.fast} ${t.motion.ease}`,
      }}
    >
      {label}
    </a>
  );
}

function Footer() {
  return (
    <footer
      style={{
        maxWidth: t.layout.gridWidth,
        margin: "0 auto",
        padding: `${t.space[12]} ${t.space[8]}`,
        borderTop: `1px solid ${t.color.borderFaint}`,
        fontFamily: t.font.body,
        fontSize: t.size.xs,
        color: t.color.textTertiary,
        textAlign: "center",
      }}
    >
      MarketLens · All estimates are directional; validate with incrementality tests before major commits.
    </footer>
  );
}

function LoadingView() {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: `${t.space[24]} ${t.space[8]}`,
        gap: t.space[6],
      }}
    >
      <div
        style={{
          width: "28px",
          height: "28px",
          border: `2px solid ${t.color.border}`,
          borderTopColor: t.color.accent,
          borderRadius: "50%",
          animation: "spin 700ms linear infinite",
        }}
      />
      <div
        style={{
          fontFamily: t.font.body,
          fontSize: t.size.sm,
          color: t.color.textSecondary,
          textAlign: "center",
          maxWidth: "360px",
          lineHeight: t.leading.normal,
        }}
      >
        Running your analysis. This may take a moment on first load while the models fit.
      </div>
    </div>
  );
}

function ErrorView({ error }) {
  const isNetwork = error?.kind === "network";
  return (
    <div
      style={{
        maxWidth: "560px",
        margin: `${t.space[20]} auto`,
        padding: `${t.space[8]} ${t.space[8]}`,
        background: t.color.surface,
        border: `1px solid ${t.color.border}`,
        borderLeft: `3px solid ${t.color.warning}`,
        borderRadius: t.radius.md,
        boxShadow: t.shadow.card,
      }}
    >
      <div
        style={{
          fontFamily: t.font.body,
          fontSize: t.size.xs,
          fontWeight: t.weight.semibold,
          color: t.color.warning,
          textTransform: "uppercase",
          letterSpacing: t.tracking.wider,
          marginBottom: t.space[3],
        }}
      >
        {isNetwork ? "Connection issue" : "Couldn't load analysis"}
      </div>
      <p
        style={{
          fontFamily: t.font.body,
          fontSize: t.size.md,
          color: t.color.textPrimary,
          lineHeight: t.leading.relaxed,
          margin: 0,
        }}
      >
        {isNetwork
          ? "MarketLens couldn't reach the analysis server. Verify the backend is running and try again."
          : error?.message || "An unexpected error occurred."}
      </p>
    </div>
  );
}

// Export GlobalStyles so EditorApp can reuse it (animations + font loading
// + scrollbar styling are identical; only the Header and business logic
// differ between client and editor modes).
export { GlobalStyles };
