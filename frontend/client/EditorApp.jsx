import { useState, useEffect, useCallback } from "react";
import { Eye } from "lucide-react";
import { tokens as t } from "./tokens.js";
import {
  ensureDiagnosisReady,
  ensurePlanReady,
  saveCommentary,
  deleteCommentary,
  suppressFinding,
  unsuppressFinding,
} from "./api.js";
import { Diagnosis } from "./screens/Diagnosis.jsx";
import { Plan } from "./screens/Plan.jsx";
import { SuppressionModal } from "./components/SuppressionModal.jsx";
import { Toast } from "./components/Toast.jsx";
import { GlobalStyles } from "./DiagnosisApp.jsx";

/**
 * EditorApp — EY-mode shell for MarketLens.
 *
 * Same screens as the client app, but with editor callbacks wired to the
 * /api/editor/* endpoints. Rendered from the separate index-editor.html
 * entry point so the client build literally cannot contain editor controls.
 *
 * Screen routing: reads ?screen= from URL. "diagnosis" (default) or "plan".
 * Same editor overlay mechanism works on both — commentary and suppression
 * keys are stable per-surface (findings for Diagnosis, moves for Plan),
 * so the same handlers serve both screens.
 *
 * Responsibilities:
 *  - Load the current screen's data with view=editor (includes suppressed
 *    items flagged rather than filtered, plus commentary attached)
 *  - Manage modal and toast state at the app level so all cards share
 *    one modal and one toast stack
 *  - Call editor mutation endpoints, refetch on success, surface errors
 *    via toast so the user knows a save landed or failed
 *  - Render a distinct header that makes it impossible to confuse editor
 *    and client modes (different background band, "EY Editor" badge,
 *    override count indicators)
 */
function getScreenFromUrl() {
  if (typeof window === "undefined") return "diagnosis";
  const params = new URLSearchParams(window.location.search);
  const s = params.get("screen");
  return s === "plan" ? "plan" : "diagnosis";
}

export default function EditorApp() {
  const screen = getScreenFromUrl();
  const [state, setState] = useState({ status: "loading", data: null, error: null });
  const [suppressTarget, setSuppressTarget] = useState(null);
  const [toast, setToast] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const reload = useCallback(async () => {
    const loader = screen === "plan" ? ensurePlanReady : ensureDiagnosisReady;
    const { data, error } = await loader("editor");
    if (data) {
      setState({ status: "ready", data, error: null });
    } else {
      setState({ status: "error", data: null, error });
    }
  }, [screen]);

  useEffect(() => {
    reload();
  }, [reload]);

  // ── Editor action handlers ──
  //
  // Each handler: sets submitting, calls the API, shows a toast on the
  // outcome, reloads the diagnosis (so the updated override is visible),
  // and resets submitting. On errors we return the error up to the
  // calling component (commentary editor, suppression modal) so they can
  // surface it inline without losing the user's unsaved input.

  async function handleSaveCommentary(findingKey, text) {
    setSubmitting(true);
    const { error } = await saveCommentary(findingKey, text, "ey.editor");
    setSubmitting(false);
    if (error) {
      setToast({ message: error.message || "Couldn't save commentary", kind: "error" });
      return { error };
    }
    setToast({ message: "Commentary saved", kind: "success" });
    await reload();
    return { ok: true };
  }

  async function handleDeleteCommentary(findingKey) {
    setSubmitting(true);
    const { error } = await deleteCommentary(findingKey, "ey.editor");
    setSubmitting(false);
    if (error) {
      setToast({ message: error.message || "Couldn't delete commentary", kind: "error" });
      return { error };
    }
    setToast({ message: "Commentary removed", kind: "success" });
    await reload();
    return { ok: true };
  }

  function handleRequestSuppress(finding) {
    // Opens the modal; actual suppression happens in handleConfirmSuppress
    setSuppressTarget(finding);
  }

  async function handleConfirmSuppress(reason) {
    if (!suppressTarget) return { error: "No target" };
    setSubmitting(true);
    const { error } = await suppressFinding(suppressTarget.key, reason, "ey.editor");
    setSubmitting(false);
    if (error) {
      setToast({ message: error.message || "Couldn't hide finding", kind: "error" });
      return { error };
    }
    setSuppressTarget(null);
    setToast({ message: "Finding hidden from client view", kind: "success" });
    await reload();
    return { ok: true };
  }

  async function handleUnsuppress(findingKey) {
    setSubmitting(true);
    const { error } = await unsuppressFinding(findingKey, "ey.editor");
    setSubmitting(false);
    if (error) {
      setToast({ message: error.message || "Couldn't restore finding", kind: "error" });
      return { error };
    }
    setToast({ message: "Finding restored to client view", kind: "success" });
    await reload();
    return { ok: true };
  }

  const counts = state.data?.ey_overrides?.counts;
  // Shared editor-callback props — same handlers serve both screens
  // because commentary/suppression keys are stable per-surface.
  const editorProps = {
    editorMode: true,
    onSaveCommentary: handleSaveCommentary,
    onDeleteCommentary: handleDeleteCommentary,
    onRequestSuppress: handleRequestSuppress,
    onUnsuppress: handleUnsuppress,
  };

  return (
    <div style={{ minHeight: "100vh", background: t.color.canvas, fontFamily: t.font.body }}>
      <GlobalStyles />
      <EditorHeader counts={counts} currentScreen={screen} />

      {state.status === "loading" && <LoadingView />}
      {state.status === "error" && <ErrorView error={state.error} />}
      {state.status === "ready" && screen === "diagnosis" && (
        <Diagnosis data={state.data} {...editorProps} />
      )}
      {state.status === "ready" && screen === "plan" && (
        <Plan data={state.data} {...editorProps} />
      )}

      <Footer />

      {suppressTarget && (
        <SuppressionModal
          finding={suppressTarget}
          onConfirm={handleConfirmSuppress}
          onCancel={() => setSuppressTarget(null)}
          submitting={submitting}
        />
      )}

      {toast && (
        <Toast
          message={toast.message}
          kind={toast.kind}
          onDismiss={() => setToast(null)}
        />
      )}
    </div>
  );
}

/**
 * EditorHeader — distinct, unambiguously editor-mode.
 *
 * Uses a darker-than-canvas background band with an accent left border so
 * at-a-glance scanning tells you which mode you're in. The "EY Editor"
 * pill and override counts make the mode status persistent — a user who
 * tabs away and comes back instantly sees "I'm editing, and I have X
 * overrides in place."
 *
 * The "Preview as Client" link doesn't do a mode switch inside this app —
 * it opens the client entry point in a new tab. That's deliberate: a
 * single-page mode toggle risks accidentally publishing unsaved edits
 * or confusing the author about which surface they're in.
 */
function EditorHeader({ counts, currentScreen = "diagnosis" }) {
  return (
    <header
      style={{
        position: "sticky",
        top: 0,
        zIndex: 10,
        background: t.color.surfaceSunken,
        borderBottom: `1px solid ${t.color.border}`,
        boxShadow: "inset 0 -1px 0 rgba(0,0,0,0.02)",
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
        {/* Left: brand + editor indicator + screen nav */}
        <div style={{ display: "flex", alignItems: "center", gap: t.space[6] }}>
          <div style={{ display: "flex", alignItems: "center", gap: t.space[3] }}>
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
            <span
              style={{
                fontFamily: t.font.body,
                fontSize: t.size.xs,
                fontWeight: t.weight.semibold,
                color: t.color.accent,
                background: t.color.accentSubtle,
                padding: `3px ${t.space[2]}`,
                borderRadius: t.radius.sm,
                textTransform: "uppercase",
                letterSpacing: t.tracking.wider,
              }}
            >
              EY Editor
            </span>
          </div>

          {/* Screen nav — mirrors the client header's minimal pattern */}
          <nav style={{ display: "flex", alignItems: "center", gap: t.space[4] }}>
            <EditorNavLink label="Diagnosis" screen="diagnosis" active={currentScreen === "diagnosis"} />
            <EditorNavLink label="Plan" screen="plan" active={currentScreen === "plan"} />
          </nav>
        </div>

        {/* Right: override counts + preview-as-client link */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: t.space[5],
            fontFamily: t.font.body,
            fontSize: t.size.xs,
            color: t.color.textSecondary,
          }}
        >
          {counts && (
            <div style={{ display: "flex", gap: t.space[4] }}>
              <OverrideCountPill label="Notes" count={counts.commentary} />
              <OverrideCountPill label="Hidden" count={counts.suppressions} />
            </div>
          )}
          <a
            href={`/index-client.html?screen=${currentScreen}`}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: t.space[2],
              fontFamily: t.font.body,
              fontSize: t.size.sm,
              fontWeight: t.weight.medium,
              color: t.color.accent,
              textDecoration: "none",
              padding: `${t.space[2]} ${t.space[3]}`,
              borderRadius: t.radius.sm,
              border: `1px solid ${t.color.accent}`,
              background: t.color.surface,
              transition: `background ${t.motion.fast} ${t.motion.ease}`,
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = t.color.accentSubtle)}
            onMouseLeave={(e) => (e.currentTarget.style.background = t.color.surface)}
          >
            <Eye size={14} strokeWidth={1.75} />
            Preview as client
          </a>
        </div>
      </div>
    </header>
  );
}

function OverrideCountPill({ label, count }) {
  const active = count > 0;
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: t.space[2],
        fontFamily: t.font.body,
        fontSize: t.size.xs,
        fontWeight: t.weight.medium,
        color: active ? t.color.textPrimary : t.color.textTertiary,
      }}
    >
      <span
        style={{
          fontFamily: t.font.mono,
          fontSize: t.size.xs,
          fontWeight: t.weight.semibold,
          color: active ? t.color.accent : t.color.textTertiary,
          minWidth: "16px",
          textAlign: "right",
        }}
      >
        {count}
      </span>
      <span
        style={{
          textTransform: "uppercase",
          letterSpacing: t.tracking.wider,
        }}
      >
        {label}
      </span>
    </span>
  );
}

/**
 * EditorNavLink — screen link in the editor header.
 *
 * Mirrors the client-side NavLink pattern but styled for the sunken
 * editor header (slightly different contrast requirements — the editor
 * header's background is surfaceSunken, not canvas).
 */
function EditorNavLink({ label, screen, active }) {
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
      EY Editor · Edits are saved immediately and visible to the client view. Draft / publish workflow lands in a later release.
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
        Loading the diagnosis and any saved EY overrides…
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
        {isNetwork ? "Connection issue" : "Couldn't load editor"}
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
