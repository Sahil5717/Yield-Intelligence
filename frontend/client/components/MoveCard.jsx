import { useState } from "react";
import { ChevronDown, TrendingUp, TrendingDown, Minus, AlertTriangle, EyeOff, Eye, MessageSquare } from "lucide-react";
import { tokens as t } from "../tokens.js";
import { CommentaryEditor } from "./CommentaryEditor.jsx";

/**
 * MoveCard — one per-channel reallocation action on the Plan screen.
 *
 * Parallel to FindingCard on the Diagnosis screen, but shaped for numeric
 * before/after display rather than prose findings. The card shows:
 *
 *   - action badge (increase / decrease / hold) with an icon color-coded
 *     to the direction
 *   - channel name + the action verb as headline
 *   - compact before/after spend figures with the delta highlighted
 *   - ROI row: current → optimized, with marginal ROI as supporting metric
 *   - on expand: the narrative (the "why"), plus editor controls if in editor mode
 *
 * When a move depends on a near-linear response curve fit, the card
 * renders an "inconclusive" banner — the revenue delta is an extrapolation
 * past observed spend, not a reliable estimate. This is the same honesty
 * principle we applied to the Diagnosis findings (no fabricated precision).
 */
export function MoveCard({
  move,
  index,
  editorMode = false,
  onSaveCommentary,
  onDeleteCommentary,
  onRequestSuppress,
  onUnsuppress,
}) {
  const [expanded, setExpanded] = useState(false);
  const [editingCommentary, setEditingCommentary] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const actionConfig = ACTION_CONFIG[move.action] || ACTION_CONFIG.hold;
  const isInconclusive = move.reliability === "inconclusive";
  const hasCommentary = !!move.ey_commentary;
  const isSuppressed = !!move.suppressed;

  async function handleCommentarySave(text) {
    if (!onSaveCommentary) return { error: "No save handler" };
    setSubmitting(true);
    const result = await onSaveCommentary(move.key, text);
    setSubmitting(false);
    if (!result?.error) setEditingCommentary(false);
    return result;
  }

  async function handleCommentaryDelete() {
    if (!onDeleteCommentary) return;
    setSubmitting(true);
    await onDeleteCommentary(move.key);
    setSubmitting(false);
    setEditingCommentary(false);
  }

  return (
    <div
      style={{
        background: isSuppressed ? t.color.surfaceSunken : t.color.surface,
        border: `1px solid ${expanded ? t.color.borderStrong : t.color.border}`,
        borderRadius: t.radius.md,
        borderLeft: `3px solid ${isSuppressed ? t.color.textTertiary : actionConfig.color}`,
        boxShadow: expanded ? t.shadow.raised : t.shadow.card,
        transition: `box-shadow ${t.motion.base} ${t.motion.ease}, border-color ${t.motion.base} ${t.motion.ease}`,
        overflow: "hidden",
        animation: `findingFadeIn ${t.motion.slow} ${t.motion.ease} ${index * 60}ms both`,
        opacity: isSuppressed ? 0.75 : 1,
      }}
    >
      {/* Suppressed banner — editor mode only */}
      {isSuppressed && editorMode && (
        <div style={bannerStyle("warning")}>
          <EyeOff size={13} strokeWidth={2} />
          <span>Hidden from client</span>
          {move.suppression_reason && (
            <span style={bannerReasonStyle()}>· {move.suppression_reason}</span>
          )}
        </div>
      )}

      {/* Inconclusive banner — both modes */}
      {isInconclusive && !isSuppressed && (
        <div style={bannerStyle("inconclusive")}>
          <AlertTriangle size={13} strokeWidth={2} />
          <span>Inconclusive saturation — treat estimates as directional</span>
        </div>
      )}

      {/* Header (click to expand) */}
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
          gap: t.space[4],
          textAlign: "left",
          fontFamily: "inherit",
        }}
        aria-expanded={expanded}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          {/* Action badge */}
          <div style={{ display: "flex", alignItems: "center", gap: t.space[2], marginBottom: t.space[3] }}>
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: t.space[1],
                padding: `3px ${t.space[2]}`,
                borderRadius: t.radius.sm,
                background: actionConfig.bg,
                color: actionConfig.color,
                fontFamily: t.font.body,
                fontSize: t.size.xs,
                fontWeight: t.weight.semibold,
                textTransform: "uppercase",
                letterSpacing: t.tracking.wider,
              }}
            >
              {actionConfig.icon}
              {actionConfig.label}
            </span>
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
              marginBottom: t.space[4],
            }}
          >
            {move.headline}
          </h3>

          {/* Number grid — the "what" of the move */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr auto 1fr auto 1fr",
              alignItems: "center",
              gap: t.space[3],
              paddingTop: t.space[3],
              borderTop: `1px solid ${t.color.borderFaint}`,
            }}
          >
            <Metric label="Current spend" value={formatCompact(move.current_spend)} />
            <ArrowCell />
            <Metric label="Optimized spend" value={formatCompact(move.optimized_spend)} accent={actionConfig.color} />
            <div style={{ width: 1, height: 28, background: t.color.borderFaint }} />
            <Metric
              label="Revenue impact"
              value={move.revenue_delta_display}
              accent={move.revenue_delta > 0 ? t.color.positive : (move.revenue_delta < 0 ? t.color.warning : t.color.textSecondary)}
            />
          </div>

          {/* Commentary indicator */}
          {hasCommentary && !editingCommentary && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: t.space[2],
                marginTop: t.space[4],
                padding: `${t.space[2]} ${t.space[3]}`,
                background: t.color.accentSubtle,
                borderRadius: t.radius.sm,
                fontFamily: t.font.body,
                fontSize: t.size.xs,
                color: t.color.accent,
                fontWeight: t.weight.medium,
              }}
            >
              <MessageSquare size={12} strokeWidth={2} />
              EY has added commentary — expand to read
            </div>
          )}
        </div>

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
          {/* Narrative — the "why" */}
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
            {move.narrative}
          </p>

          {/* ROI detail row */}
          <div
            style={{
              display: "flex",
              gap: t.space[6],
              padding: `${t.space[4]} 0`,
              borderTop: `1px solid ${t.color.borderFaint}`,
              borderBottom: `1px solid ${t.color.borderFaint}`,
            }}
          >
            <RoiMetric label="Current ROI" value={`${move.current_roi.toFixed(1)}x`} />
            <RoiMetric label="Optimized ROI" value={`${move.optimized_roi.toFixed(1)}x`} />
            <RoiMetric label="Marginal ROI" value={`${move.marginal_roi.toFixed(1)}x`} tone={isInconclusive ? "warning" : "default"} />
          </div>

          {/* Commentary panel or editor */}
          {editorMode && editingCommentary ? (
            <CommentaryEditor
              initialText={move.ey_commentary?.text || ""}
              onSave={handleCommentarySave}
              onCancel={() => setEditingCommentary(false)}
              onDelete={hasCommentary ? handleCommentaryDelete : undefined}
              submitting={submitting}
            />
          ) : hasCommentary ? (
            <EyTakePanel
              commentary={move.ey_commentary}
              editorMode={editorMode}
              onEdit={() => setEditingCommentary(true)}
            />
          ) : null}
        </div>
      )}

      {/* Editor action bar */}
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
              onClick={() => onUnsuppress?.(move.key)}
              disabled={submitting}
            />
          ) : (
            <EditorActionButton
              icon={<EyeOff size={14} strokeWidth={1.75} />}
              label="Hide from client"
              onClick={() => onRequestSuppress?.(move)}
              disabled={submitting}
              tone="warning"
            />
          )}
        </div>
      )}
    </div>
  );
}

// ─── Internal helper components ───

const ACTION_CONFIG = {
  increase: {
    label: "Increase",
    color: "#15803D",
    bg: "#F0FDF4",
    icon: <TrendingUp size={12} strokeWidth={2.2} />,
  },
  decrease: {
    label: "Reduce",
    color: "#B45309",
    bg: "#FFFBEB",
    icon: <TrendingDown size={12} strokeWidth={2.2} />,
  },
  hold: {
    label: "Hold",
    color: "#525252",
    bg: "#F5F5F0",
    icon: <Minus size={12} strokeWidth={2.2} />,
  },
};

function formatCompact(amount) {
  if (amount == null) return "—";
  const a = Math.abs(amount);
  if (a >= 1e9) return `$${(a / 1e9).toFixed(1)}B`;
  if (a >= 1e6) return `$${(a / 1e6).toFixed(1)}M`;
  if (a >= 1e3) return `$${(a / 1e3).toFixed(0)}K`;
  return `$${a.toFixed(0)}`;
}

function Metric({ label, value, accent = null }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: t.space[1] }}>
      <span
        style={{
          fontFamily: t.font.body,
          fontSize: t.size.xs,
          fontWeight: t.weight.medium,
          color: t.color.textTertiary,
          textTransform: "uppercase",
          letterSpacing: t.tracking.wider,
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontFamily: t.font.display,
          fontSize: t.size.lg,
          fontWeight: t.weight.semibold,
          color: accent || t.color.textPrimary,
          letterSpacing: t.tracking.tight,
          lineHeight: t.leading.tight,
        }}
      >
        {value}
      </span>
    </div>
  );
}

function ArrowCell() {
  return (
    <span
      style={{
        color: t.color.textTertiary,
        fontFamily: t.font.body,
        fontSize: t.size.lg,
        fontWeight: t.weight.regular,
        lineHeight: 1,
      }}
    >
      →
    </span>
  );
}

function RoiMetric({ label, value, tone = "default" }) {
  const color = tone === "warning" ? t.color.warning : t.color.textPrimary;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: t.space[1] }}>
      <span
        style={{
          fontFamily: t.font.body,
          fontSize: t.size.xs,
          fontWeight: t.weight.medium,
          color: t.color.textTertiary,
          textTransform: "uppercase",
          letterSpacing: t.tracking.wider,
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontFamily: t.font.display,
          fontSize: t.size.md,
          fontWeight: t.weight.semibold,
          color,
          letterSpacing: t.tracking.tight,
        }}
      >
        {value}
      </span>
    </div>
  );
}

function bannerStyle(kind) {
  const bg = kind === "warning" ? t.color.warningBg : "#FEF3C7";
  const fg = kind === "warning" ? t.color.warning : "#A16207";
  return {
    background: bg,
    color: fg,
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
  };
}

function bannerReasonStyle() {
  return {
    fontWeight: t.weight.regular,
    textTransform: "none",
    letterSpacing: t.tracking.normal,
    color: t.color.textSecondary,
    marginLeft: t.space[2],
  };
}

function EyTakePanel({ commentary, editorMode, onEdit }) {
  return (
    <div
      style={{
        background: t.color.accentSubtle,
        border: `1px solid ${t.color.accent}30`,
        borderRadius: t.radius.md,
        padding: `${t.space[4]} ${t.space[5]}`,
        display: "flex",
        flexDirection: "column",
        gap: t.space[2],
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: t.space[3] }}>
        <span
          style={{
            fontFamily: t.font.body,
            fontSize: t.size.xs,
            fontWeight: t.weight.semibold,
            color: t.color.accent,
            textTransform: "uppercase",
            letterSpacing: t.tracking.wider,
          }}
        >
          EY's Take
        </span>
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
              cursor: "pointer",
              padding: 0,
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
          color: t.color.textPrimary,
          lineHeight: t.leading.relaxed,
          margin: 0,
        }}
      >
        {commentary.text}
      </p>
    </div>
  );
}

function EditorActionButton({ icon, label, onClick, disabled, tone = "default" }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: t.space[2],
        padding: `${t.space[2]} ${t.space[3]}`,
        background: t.color.surface,
        border: `1px solid ${tone === "warning" ? t.color.warning : t.color.border}`,
        borderRadius: t.radius.sm,
        fontFamily: t.font.body,
        fontSize: t.size.xs,
        fontWeight: t.weight.medium,
        color: tone === "warning" ? t.color.warning : t.color.textSecondary,
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.5 : 1,
        transition: `background ${t.motion.fast} ${t.motion.ease}`,
      }}
    >
      {icon}
      {label}
    </button>
  );
}
