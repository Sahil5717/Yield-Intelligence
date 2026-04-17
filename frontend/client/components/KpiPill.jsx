import { tokens as t } from "../tokens.js";

/**
 * KpiPill — one of the three headline KPI cards at the top of the
 * Diagnosis screen.
 *
 * Layout is bento-grid style: three equal cards in a row, each showing
 * a label, a large value, and (where relevant) a secondary line of context
 * (benchmark comparison, % of revenue, etc.).
 *
 * Tones are sparing by design. Only Value-at-Risk uses the warning color
 * when its tone is "warning"; Plan Confidence uses the signal color of its
 * own tier, and Portfolio ROAS tends to stay neutral. Restraint here is
 * deliberate — a screen with three loud KPIs reads as alarmist rather than
 * authoritative.
 */

const toneColors = {
  positive: { fg: t.color.positive, accent: t.color.positive },
  neutral: { fg: t.color.textPrimary, accent: t.color.textSecondary },
  warning: { fg: t.color.warning, accent: t.color.warning },
  negative: { fg: t.color.negative, accent: t.color.negative },
};

export function KpiPill({ label, value, display, tone = "neutral", context, children }) {
  const colors = toneColors[tone] || toneColors.neutral;

  return (
    <div
      style={{
        background: t.color.surface,
        border: `1px solid ${t.color.border}`,
        borderRadius: t.radius.md,
        padding: `${t.space[5]} ${t.space[6]}`,
        boxShadow: t.shadow.card,
        display: "flex",
        flexDirection: "column",
        gap: t.space[3],
        transition: `box-shadow ${t.motion.base} ${t.motion.ease}`,
      }}
    >
      {/* Label — small, muted, uppercase-tracked. Acts as a caption. */}
      <div
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
      </div>

      {/* Value — the hero number */}
      <div
        style={{
          fontFamily: t.font.display,
          fontSize: t.size["2xl"],
          fontWeight: t.weight.semibold,
          color: colors.fg,
          letterSpacing: t.tracking.tight,
          lineHeight: t.leading.tight,
        }}
      >
        {display || value}
      </div>

      {/* Context line — secondary, smaller, muted */}
      {context && (
        <div
          style={{
            fontFamily: t.font.body,
            fontSize: t.size.sm,
            fontWeight: t.weight.regular,
            color: t.color.textSecondary,
            lineHeight: t.leading.normal,
          }}
        >
          {context}
        </div>
      )}

      {children}
    </div>
  );
}
