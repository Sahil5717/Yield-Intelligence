import { useState } from "react";
import { ChevronDown, MessageSquare, EyeOff, Eye } from "lucide-react";
import { tokens as t, findingTypeColors } from "../tokens.js";
import { ConfidenceChip } from "./ConfidenceChip.jsx";
import { CommentaryEditor } from "./CommentaryEditor.jsx";

/**
 * FindingCard — one of the 3-5 ranked findings on the Diagnosis screen.
 *
 * Two modes, controlled by the `editorMode` prop:
 *
 * CLIENT MODE (editorMode=false, default):
 *   Collapsed state shows: headline, confidence tier, impact, narrative preview.
 *   Expanded state reveals full narrative, evidence chart placeholder,
 *   source engines, and (if present) an "EY's Take" commentary panel.
 *   Suppressed findings never appear — they're filtered at the backend.
 *
 * EDITOR MODE (editorMode=true):
 *   Same base rendering, PLUS:
 *     - Suppressed findings appear with visual dimming and a
 *       "Hidden from client" indicator
 *     - An action bar at the bottom with Comment + Hide/Show buttons
 *       (visible only when card is expanded, to avoid clutter)
 *     - When Comment is active, an inline textarea replaces the
 *       commentary panel with a save/cancel editor
 *     - Suppression is triggered via a modal (rendered by DiagnosisApp)
 *
 * The left-edge accent stripe uses the finding's type color. It's the only
 * color-carrying decoration on the card — everything else is neutral.
 */
export function FindingCard({
  finding,
  index,
  editorMode = false,
  // Editor-mode callbacks. In client mode these are ignored.
  onSaveCommentary,
  onDeleteCommentary,
  onRequestSuppress,
  onUnsuppress,
}) {
  const [expanded, setExpanded] = useState(false);
  const [editingCommentary, setEditingCommentary] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const accentColor = findingTypeColors[finding.type] || findingTypeColors.neutral;
  const impactFormatted = finding.impact_dollars
    ? formatImpactDollars(finding.impact_dollars)
    : null;
  const hasCommentary = !!finding.ey_commentary;
  const isSuppressed = !!finding.suppressed;

  // Handle save from the commentary editor. Returns the promise so the
  // editor can show submitting state and handle errors locally.
  async function handleCommentarySave(text) {
    if (!onSaveCommentary) return { error: "No save handler" };
    setSubmitting(true);
    try {
      const result = await onSaveCommentary(finding.key, text);
      if (!result.error) setEditingCommentary(false);
      return result;
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCommentaryDelete() {
    if (!onDeleteCommentary) return;
    setSubmitting(true);
    try {
      await onDeleteCommentary(finding.key);
      setEditingCommentary(false);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      style={{
        background: isSuppressed ? t.color.surfaceSunken : t.color.surface,
        border: `1px solid ${expanded ? t.color.borderStrong : t.color.border}`,
        borderRadius: t.radius.md,
        borderLeft: `3px solid ${isSuppressed ? t.color.textTertiary : accentColor}`,
        boxShadow: expanded ? t.shadow.raised : t.shadow.card,
        transition: `box-shadow ${t.motion.base} ${t.motion.ease}, border-color ${t.motion.base} ${t.motion.ease}, background ${t.motion.base} ${t.motion.ease}`,
        overflow: "hidden",
        animation: `findingFadeIn ${t.motion.slow} ${t.motion.ease} ${index * 80}ms both`,
        opacity: isSuppressed ? 0.75 : 1,
      }}
    >
      {/* Suppressed banner — editor mode only; client view never renders these */}
      {isSuppressed && editorMode && (
        <div
          style={{
            background: t.color.warningBg,
            color: t.color.warning,
            padding: `${t.space[2]} ${t.space[6]}`,
            fontFamily: t.font.body,
            fontSize: t.size.xs,
            fontWeight: t.weight.semibold,
            letterSpacing: t.tracking.wider,
            textTransform: "uppercase",
            borderBottom: `1px solid ${t.color.border}`,
            display: "flex",
            alignItems: "center",
            gap: t.space[2],
          }}
        >
          <EyeOff size={13} strokeWidth={2} />
          <span>Hidden from client</span>
          {finding.suppression_reason && (
            <span
              style={{
                fontWeight: t.weight.regular,
                textTransform: "none",
                letterSpacing: t.tracking.normal,
                color: t.color.textSecondary,
                marginLeft: t.space[2],
              }}
            >
              · {finding.suppression_reason}
            </span>
          )}
        </div>
      )}

      {/* Header — clickable to expand */}
      <button
        onClick={() => setExpanded((x) => !x)}
        style={{
          width: "100%",
          background: "none",
          border: "none",
          padding: `${t.space[5]} ${t.space[6]}`,
          cursor: "pointer",
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: t.space[5],
          textAlign: "left",
          fontFamily: "inherit",
        }}
        aria-expanded={expanded}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          {/* Metadata row: tier chip + impact + commentary indicator */}
          <div
            style={{
              display: "flex",
              gap: t.space[2],
              marginBottom: t.space[3],
              alignItems: "center",
              flexWrap: "wrap",
            }}
          >
            <ConfidenceChip tier={finding.confidence} />
            {impactFormatted && (
              <span
                style={{
                  fontFamily: t.font.body,
                  fontSize: t.size.xs,
                  fontWeight: t.weight.medium,
                  color: finding.impact_dollars > 0 ? t.color.positive : t.color.textSecondary,
                  background: finding.impact_dollars > 0 ? t.color.positiveBg : t.color.neutralBg,
                  padding: `3px ${t.space[2]}`,
                  borderRadius: t.radius.sm,
                }}
              >
                {impactFormatted}
              </span>
            )}
            {hasCommentary && (
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "4px",
                  fontFamily: t.font.body,
                  fontSize: t.size.xs,
                  fontWeight: t.weight.medium,
                  color: t.color.accent,
                  background: t.color.accentSubtle,
                  padding: `3px ${t.space[2]}`,
                  borderRadius: t.radius.sm,
                }}
              >
                <MessageSquare size={10} strokeWidth={2.25} />
                EY commentary
              </span>
            )}
          </div>

          {/* Headline */}
          <h3
            style={{
              fontFamily: t.font.display,
              fontSize: t.size.lg,
              fontWeight: t.weight.semibold,
              color: t.color.textPrimary,
              letterSpacing: t.tracking.snug,
              lineHeight: t.leading.snug,
              margin: 0,
            }}
          >
            {finding.headline}
          </h3>

          {/* Prescribed action */}
          {finding.prescribed_action && (
            <div
              style={{
                fontFamily: t.font.body,
                fontSize: t.size.sm,
                fontWeight: t.weight.medium,
                color: t.color.accent,
                lineHeight: t.leading.normal,
                margin: `${t.space[2]} 0 0`,
                display: "flex",
                alignItems: "baseline",
                gap: t.space[2],
              }}
            >
              <span
                style={{
                  color: t.color.textTertiary,
                  fontSize: t.size.xs,
                  textTransform: "uppercase",
                  letterSpacing: t.tracking.wider,
                  fontWeight: t.weight.semibold,
                  flexShrink: 0,
                }}
              >
                Suggested
              </span>
              <span>{finding.prescribed_action}</span>
            </div>
          )}

          {/* Narrative preview (collapsed only) */}
          {!expanded && finding.narrative && (
            <p
              style={{
                fontFamily: t.font.body,
                fontSize: t.size.sm,
                fontWeight: t.weight.regular,
                color: t.color.textSecondary,
                lineHeight: t.leading.normal,
                margin: `${t.space[3]} 0 0`,
                display: "-webkit-box",
                WebkitLineClamp: 2,
                WebkitBoxOrient: "vertical",
                overflow: "hidden",
              }}
            >
              {finding.narrative}
            </p>
          )}
        </div>

        {/* Chevron */}
        <div
          style={{
            flexShrink: 0,
            padding: `${t.space[1]} 0`,
            color: t.color.textTertiary,
            transform: expanded ? "rotate(180deg)" : "rotate(0)",
            transition: `transform ${t.motion.base} ${t.motion.ease}`,
          }}
        >
          <ChevronDown size={18} strokeWidth={1.75} />
        </div>
      </button>

      {/* Expanded body */}
      {expanded && (
        <div
          style={{
            padding: `${t.space[2]} ${t.space[6]} ${t.space[6]}`,
            borderTop: `1px solid ${t.color.borderFaint}`,
            display: "flex",
            flexDirection: "column",
            gap: t.space[5],
          }}
        >
          {/* Full narrative */}
          {finding.narrative && (
            <p
              style={{
                fontFamily: t.font.body,
                fontSize: t.size.md,
                fontWeight: t.weight.regular,
                color: t.color.textPrimary,
                lineHeight: t.leading.relaxed,
                margin: `${t.space[4]} 0 0`,
              }}
            >
              {finding.narrative}
            </p>
          )}

          {/* EY commentary — two renderings depending on mode/state */}
          {editorMode && editingCommentary ? (
            // Editor mode, actively editing
            <CommentaryEditor
              initialText={finding.ey_commentary?.text || ""}
              onSave={handleCommentarySave}
              onCancel={() => setEditingCommentary(false)}
              onDelete={hasCommentary ? handleCommentaryDelete : null}
              submitting={submitting}
            />
          ) : hasCommentary ? (
            // Not editing (either mode): show the EY's Take panel
            <EyTakePanel
              commentary={finding.ey_commentary}
              editorMode={editorMode}
              onEdit={() => setEditingCommentary(true)}
            />
          ) : null}

          {/* Evidence placeholder */}
          <div
            style={{
              background: t.color.surfaceSunken,
              border: `1px dashed ${t.color.border}`,
              borderRadius: t.radius.md,
              padding: t.space[6],
              minHeight: "180px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: t.color.textTertiary,
              fontFamily: t.font.body,
              fontSize: t.size.sm,
              fontStyle: "italic",
            }}
          >
            Evidence chart: {finding.evidence_chart || "overview"}
          </div>

          {/* Source engines */}
          {finding.source_engines && finding.source_engines.length > 0 && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: t.space[2],
                flexWrap: "wrap",
              }}
            >
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
                Based on
              </span>
              {finding.source_engines.map((engine) => (
                <span
                  key={engine}
                  style={{
                    fontFamily: t.font.mono,
                    fontSize: t.size.xs,
                    color: t.color.textSecondary,
                    background: t.color.surfaceSunken,
                    padding: `2px ${t.space[2]}`,
                    borderRadius: t.radius.sm,
                  }}
                >
                  {engine}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Editor action bar — only in editor mode, only when expanded and
          not currently editing commentary. Keeps client view clean. */}
      {editorMode && expanded && !editingCommentary && (
        <div
          style={{
            padding: `${t.space[3]} ${t.space[6]}`,
            borderTop: `1px solid ${t.color.borderFaint}`,
            background: t.color.canvasAlt,
            display: "flex",
            alignItems: "center",
            justifyContent: "flex-end",
            gap: t.space[2],
          }}
        >
          <EditorActionButton
            icon={<MessageSquare size={14} strokeWidth={1.75} />}
            label={hasCommentary ? "Edit commentary" : "Add commentary"}
            onClick={() => setEditingCommentary(true)}
            disabled={submitting}
          />
          {isSuppressed ? (
            <EditorActionButton
              icon={<Eye size={14} strokeWidth={1.75} />}
              label="Show to client"
              onClick={() => onUnsuppress?.(finding.key)}
              disabled={submitting}
            />
          ) : (
            <EditorActionButton
              icon={<EyeOff size={14} strokeWidth={1.75} />}
              label="Hide from client"
              onClick={() => onRequestSuppress?.(finding)}
              disabled={submitting}
              tone="warning"
            />
          )}
        </div>
      )}
    </div>
  );
}

/**
 * EyTakePanel — displays saved commentary as a distinct section inside
 * the expanded finding. In client mode it's read-only; in editor mode
 * an "Edit" link appears.
 */
function EyTakePanel({ commentary, editorMode, onEdit }) {
  return (
    <div
      style={{
        background: t.color.accentSubtle,
        border: `1px solid ${t.color.accent}30`,
        borderLeft: `3px solid ${t.color.accent}`,
        borderRadius: t.radius.md,
        padding: `${t.space[4]} ${t.space[5]}`,
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
          marginBottom: t.space[2],
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span>EY's Take</span>
        {editorMode && (
          <button
            onClick={onEdit}
            style={{
              background: "none",
              border: "none",
              color: t.color.accent,
              fontFamily: t.font.body,
              fontSize: t.size.xs,
              fontWeight: t.weight.medium,
              textTransform: "none",
              letterSpacing: t.tracking.normal,
              cursor: "pointer",
              padding: 0,
              textDecoration: "underline",
              textDecorationColor: `${t.color.accent}50`,
              textUnderlineOffset: "3px",
            }}
          >
            Edit
          </button>
        )}
      </div>
      <p
        style={{
          fontFamily: t.font.body,
          fontSize: t.size.md,
          fontWeight: t.weight.regular,
          color: t.color.textPrimary,
          lineHeight: t.leading.relaxed,
          margin: 0,
          whiteSpace: "pre-wrap",
        }}
      >
        {commentary.text}
      </p>
    </div>
  );
}

/**
 * EditorActionButton — small tertiary-style button used in the editor
 * action bar. Neutral default, warning tone for destructive actions.
 */
function EditorActionButton({ icon, label, onClick, disabled, tone = "neutral" }) {
  const fg = tone === "warning" ? t.color.warning : t.color.textSecondary;
  const bg = tone === "warning" ? t.color.warningBg : t.color.surface;
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: t.space[2],
        padding: `${t.space[2]} ${t.space[3]}`,
        background: bg,
        border: `1px solid ${t.color.border}`,
        borderRadius: t.radius.sm,
        fontFamily: t.font.body,
        fontSize: t.size.sm,
        fontWeight: t.weight.medium,
        color: fg,
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.5 : 1,
        transition: `border-color ${t.motion.fast} ${t.motion.ease}`,
      }}
      onMouseEnter={(e) => {
        if (!disabled) e.currentTarget.style.borderColor = t.color.borderStrong;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = t.color.border;
      }}
    >
      {icon}
      {label}
    </button>
  );
}

/**
 * Format an impact dollar value as "+$14.2M", "-$820K", etc.
 */
function formatImpactDollars(amount) {
  if (amount == null || amount === 0) return null;
  const sign = amount > 0 ? "+" : "-";
  const abs = Math.abs(amount);
  const formatted =
    abs >= 1e9 ? `${(abs / 1e9).toFixed(1)}B`
    : abs >= 1e6 ? `${(abs / 1e6).toFixed(1)}M`
    : abs >= 1e3 ? `${(abs / 1e3).toFixed(0)}K`
    : `${abs.toFixed(0)}`;
  return `${sign}$${formatted}`;
}
