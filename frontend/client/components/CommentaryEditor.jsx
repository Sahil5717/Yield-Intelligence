import { useState, useRef, useEffect } from "react";
import { tokens as t } from "../tokens.js";

/**
 * CommentaryEditor — inline textarea for authoring/editing EY commentary.
 *
 * Appears inside an expanded finding when the editor clicks "Add" or "Edit"
 * commentary. Handles its own local text state, submission state, and
 * error display; reports up via onSave / onCancel / onDelete callbacks.
 *
 * onSave should return a promise resolving to {error: ...} or {ok: true}
 * so we can show inline error messages without closing the editor.
 *
 * Design intent: low chrome, feels like writing in a document. No rich
 * text, no markdown support — the backend stores plain text. Keep it
 * simple; v18c can add formatting if it turns out to matter.
 */
export function CommentaryEditor({
  initialText = "",
  onSave,
  onCancel,
  onDelete,
  submitting = false,
}) {
  const [text, setText] = useState(initialText);
  const [errorMsg, setErrorMsg] = useState(null);
  const textareaRef = useRef(null);

  // Auto-focus the textarea when opened. Defer to next tick so the
  // expand animation doesn't fight with focus management.
  useEffect(() => {
    const id = setTimeout(() => {
      textareaRef.current?.focus();
      // Place cursor at end of existing text, not at start, so editing
      // feels like continuing rather than overwriting.
      const len = textareaRef.current?.value.length ?? 0;
      textareaRef.current?.setSelectionRange(len, len);
    }, 50);
    return () => clearTimeout(id);
  }, []);

  const trimmed = text.trim();
  const hasChanged = trimmed !== initialText.trim();
  const canSave = trimmed.length > 0 && hasChanged && !submitting;

  async function handleSave() {
    if (!canSave) return;
    setErrorMsg(null);
    const result = await onSave(trimmed);
    if (result?.error) {
      setErrorMsg(
        typeof result.error === "string"
          ? result.error
          : result.error.message || "Failed to save."
      );
    }
  }

  function handleKeyDown(e) {
    // Ctrl+Enter / Cmd+Enter to save
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      handleSave();
    }
    // Escape to cancel
    if (e.key === "Escape") {
      e.preventDefault();
      onCancel?.();
    }
  }

  return (
    <div
      style={{
        background: t.color.surface,
        border: `1px solid ${t.color.accent}`,
        borderLeft: `3px solid ${t.color.accent}`,
        borderRadius: t.radius.md,
        padding: `${t.space[4]} ${t.space[5]}`,
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
          color: t.color.accent,
          textTransform: "uppercase",
          letterSpacing: t.tracking.wider,
        }}
      >
        {initialText ? "Edit EY's Take" : "Add EY's Take"}
      </div>

      <textarea
        ref={textareaRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Add context, caveats, or a point of view the client needs to see alongside this finding…"
        rows={4}
        disabled={submitting}
        style={{
          width: "100%",
          minHeight: "96px",
          padding: t.space[3],
          border: `1px solid ${t.color.border}`,
          borderRadius: t.radius.sm,
          fontFamily: t.font.body,
          fontSize: t.size.md,
          lineHeight: t.leading.relaxed,
          color: t.color.textPrimary,
          background: t.color.canvas,
          resize: "vertical",
          outline: "none",
          transition: `border-color ${t.motion.fast} ${t.motion.ease}`,
        }}
        onFocus={(e) => { e.currentTarget.style.borderColor = t.color.accent; }}
        onBlur={(e) => { e.currentTarget.style.borderColor = t.color.border; }}
      />

      {errorMsg && (
        <div
          style={{
            fontFamily: t.font.body,
            fontSize: t.size.sm,
            color: t.color.negative,
            background: t.color.negativeBg,
            padding: `${t.space[2]} ${t.space[3]}`,
            borderRadius: t.radius.sm,
          }}
        >
          {errorMsg}
        </div>
      )}

      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: t.space[3],
        }}
      >
        <div
          style={{
            fontFamily: t.font.body,
            fontSize: t.size.xs,
            color: t.color.textTertiary,
          }}
        >
          {trimmed.length} characters · ⌘↵ to save · Esc to cancel
        </div>
        <div style={{ display: "flex", gap: t.space[2] }}>
          {onDelete && (
            <button
              onClick={onDelete}
              disabled={submitting}
              style={buttonStyle("danger", submitting)}
            >
              Delete
            </button>
          )}
          <button onClick={onCancel} disabled={submitting} style={buttonStyle("ghost", submitting)}>
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!canSave}
            style={buttonStyle("primary", !canSave)}
          >
            {submitting ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}

function buttonStyle(variant, disabled) {
  const base = {
    padding: `${t.space[2]} ${t.space[4]}`,
    fontFamily: t.font.body,
    fontSize: t.size.sm,
    fontWeight: t.weight.medium,
    borderRadius: t.radius.sm,
    cursor: disabled ? "not-allowed" : "pointer",
    opacity: disabled ? 0.5 : 1,
    border: `1px solid ${t.color.border}`,
    transition: `background ${t.motion.fast} ${t.motion.ease}, border-color ${t.motion.fast} ${t.motion.ease}`,
  };
  if (variant === "primary") {
    return {
      ...base,
      background: t.color.accent,
      color: t.color.textInverse,
      borderColor: t.color.accent,
    };
  }
  if (variant === "danger") {
    return {
      ...base,
      background: t.color.surface,
      color: t.color.negative,
      borderColor: t.color.border,
    };
  }
  // ghost
  return {
    ...base,
    background: t.color.surface,
    color: t.color.textSecondary,
  };
}
