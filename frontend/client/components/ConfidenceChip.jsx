import { confidenceColors, tokens as t } from "../tokens.js";

/**
 * ConfidenceChip — small pill indicating evidence quality for a finding.
 *
 * Three tiers correspond to the backend's narrative engine output:
 *   High         → forest green — numerically confident, safe to act on
 *   Directional  → amber — signal present, validate before large commits
 *   Inconclusive → gray — insufficient evidence, pair with incrementality test
 *
 * The component is deliberately plain: no icon, no dot, no surrounding
 * decoration. A CMO glances at it and gets the signal in 300ms; any more
 * chrome and it becomes a thing to read instead of a thing to scan.
 */
export function ConfidenceChip({ tier, size = "sm" }) {
  const colors = confidenceColors[tier] || confidenceColors.Directional;
  const paddingY = size === "sm" ? "3px" : "5px";
  const paddingX = size === "sm" ? t.space[2] : t.space[3];
  const fontSize = size === "sm" ? t.size.xs : t.size.sm;

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: `${paddingY} ${paddingX}`,
        borderRadius: t.radius.sm,
        background: colors.bg,
        color: colors.fg,
        fontFamily: t.font.body,
        fontSize,
        fontWeight: t.weight.medium,
        letterSpacing: t.tracking.normal,
        whiteSpace: "nowrap",
        lineHeight: 1,
      }}
    >
      {tier}
    </span>
  );
}
