import { AlertTriangle, Info } from "lucide-react";
import { tokens as t } from "../tokens.js";

/**
 * TradeoffCard — a single caveat row in the Plan screen's "Tradeoffs" section.
 *
 * Deliberately quieter than a MoveCard. Tradeoffs exist to stop the Plan
 * from reading as a calculator output; they're the consulting-quality
 * honesty layer ("this assumes current conditions hold," "large moves
 * warrant incrementality testing"). They shouldn't compete with the moves
 * for visual weight — they belong below them, in a lighter tone, as
 * supporting context a reader can scan.
 *
 * No expand/collapse, no editor affordances in this session. Tradeoffs
 * are static text emitted by the narrative engine; there's no obvious
 * reason to let EY suppress them or comment on them individually (if
 * that need emerges, we can add the override plumbing later with a
 * `tradeoff:<key>` keyspace).
 */

const SEVERITY_CONFIG = {
  warning: {
    icon: AlertTriangle,
    color: "#A16207",
    bg: "#FFFBEB",
    border: "#FDE68A",
  },
  info: {
    icon: Info,
    color: "#525252",
    bg: "#F8F8F3",
    border: "#E5E5E0",
  },
};

export function TradeoffCard({ tradeoff, index }) {
  const cfg = SEVERITY_CONFIG[tradeoff.severity] || SEVERITY_CONFIG.info;
  const Icon = cfg.icon;

  return (
    <div
      style={{
        background: cfg.bg,
        border: `1px solid ${cfg.border}`,
        borderRadius: t.radius.md,
        padding: `${t.space[4]} ${t.space[5]}`,
        display: "flex",
        alignItems: "flex-start",
        gap: t.space[4],
        animation: `findingFadeIn ${t.motion.slow} ${t.motion.ease} ${index * 60}ms both`,
      }}
    >
      {/* Icon slot — single color, no background circle. Aligns visually
          with the text baseline rather than centering vertically. */}
      <div
        style={{
          flexShrink: 0,
          color: cfg.color,
          paddingTop: "3px",
          display: "flex",
        }}
        aria-hidden="true"
      >
        <Icon size={16} strokeWidth={2} />
      </div>

      <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: t.space[2] }}>
        <h4
          style={{
            fontFamily: t.font.display,
            fontSize: t.size.md,
            fontWeight: t.weight.semibold,
            color: t.color.textPrimary,
            lineHeight: t.leading.snug,
            letterSpacing: t.tracking.snug,
            margin: 0,
          }}
        >
          {tradeoff.headline}
        </h4>
        <p
          style={{
            fontFamily: t.font.body,
            fontSize: t.size.sm,
            color: t.color.textSecondary,
            lineHeight: t.leading.relaxed,
            margin: 0,
          }}
        >
          {tradeoff.narrative}
        </p>
      </div>
    </div>
  );
}
