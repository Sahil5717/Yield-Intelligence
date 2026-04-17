import { tokens as t } from "../tokens.js";
import { KpiPill } from "../components/KpiPill.jsx";
import { FindingCard } from "../components/FindingCard.jsx";

/**
 * Diagnosis screen — the opening surface of MarketLens.
 *
 * Layout, top to bottom:
 *   1. Hero section: headline paragraph + three KPI pills
 *   2. Findings list: 3-5 ranked finding cards, expandable
 *   3. Methodology footer: which engines contributed
 *
 * The hero section uses a wider width (1100px grid) to accommodate the
 * KPI bento-row. The headline paragraph and findings use the narrower
 * reading width (760px) for legibility — this is prose-heavy content
 * and longer line lengths hurt scan-ability.
 *
 * The "hero card" wrapping the headline paragraph is deliberately
 * prominent -- it's the first thing the reader's eye lands on and sets
 * the tone. Below it the visual weight drops; findings are cards but
 * quieter, establishing hierarchy.
 */
export function Diagnosis({
  data,
  editorMode = false,
  onSaveCommentary,
  onDeleteCommentary,
  onRequestSuppress,
  onUnsuppress,
}) {
  if (!data) return null;

  const { headline_paragraph, kpis, findings, methodology, data_coverage } = data;

  return (
    <main
      style={{
        minHeight: "100vh",
        background: t.color.canvas,
        fontFamily: t.font.body,
        color: t.color.textPrimary,
      }}
    >
      {/* Section 1 — Hero */}
      <section
        style={{
          maxWidth: t.layout.gridWidth,
          margin: "0 auto",
          padding: `${t.space[16]} ${t.space[8]} ${t.space[12]}`,
        }}
      >
        {/* Section label */}
        <div
          style={{
            fontFamily: t.font.body,
            fontSize: t.size.xs,
            fontWeight: t.weight.semibold,
            color: t.color.accent,
            textTransform: "uppercase",
            letterSpacing: t.tracking.wider,
            marginBottom: t.space[4],
          }}
        >
          Diagnosis
        </div>

        {/* Hero card with the headline paragraph */}
        <div
          style={{
            background: t.color.surface,
            border: `1px solid ${t.color.border}`,
            borderRadius: t.radius.xl,
            padding: `${t.space[10]} ${t.space[12]}`,
            boxShadow: t.shadow.card,
            marginBottom: t.space[8],
            maxWidth: t.layout.readingWidth,
            animation: `heroFadeIn ${t.motion.slow} ${t.motion.ease} both`,
          }}
        >
          <p
            style={{
              fontFamily: t.font.display,
              fontSize: "clamp(1.375rem, 2.2vw, 1.625rem)",
              fontWeight: t.weight.regular,
              color: t.color.textPrimary,
              letterSpacing: t.tracking.snug,
              lineHeight: t.leading.relaxed,
              margin: 0,
            }}
          >
            {headline_paragraph}
          </p>
        </div>

        {/* KPI row */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: t.space[4],
            animation: `kpiFadeIn ${t.motion.slow} ${t.motion.ease} 120ms both`,
          }}
        >
          {kpis && (
            <>
              <KpiPill
                label={kpis.portfolio_roas.label}
                display={kpis.portfolio_roas.display}
                tone={kpis.portfolio_roas.tone}
                context={
                  kpis.portfolio_roas.benchmark
                    ? `Industry benchmark: ${kpis.portfolio_roas.benchmark}`
                    : "Revenue per dollar of marketing spend"
                }
              />
              <KpiPill
                label={kpis.value_at_risk.label}
                display={kpis.value_at_risk.display}
                tone={kpis.value_at_risk.tone}
                context={`${kpis.value_at_risk.pct_of_revenue}% of attributable revenue recoverable`}
              />
              <KpiPill
                label={kpis.plan_confidence.label}
                display={kpis.plan_confidence.display}
                tone={kpis.plan_confidence.tone}
                context="Based on fit quality of underlying models"
              />
            </>
          )}
        </div>
      </section>

      {/* Section 2 — Findings */}
      <section
        style={{
          maxWidth: t.layout.readingWidth,
          margin: "0 auto",
          padding: `${t.space[4]} ${t.space[8]} ${t.space[16]}`,
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
            marginBottom: t.space[4],
          }}
        >
          Findings
        </div>

        <h2
          style={{
            fontFamily: t.font.display,
            fontSize: t.size.xl,
            fontWeight: t.weight.semibold,
            color: t.color.textPrimary,
            letterSpacing: t.tracking.tight,
            lineHeight: t.leading.snug,
            margin: `0 0 ${t.space[2]} 0`,
          }}
        >
          What the analysis surfaces
        </h2>
        <p
          style={{
            fontFamily: t.font.body,
            fontSize: t.size.sm,
            color: t.color.textSecondary,
            lineHeight: t.leading.normal,
            margin: `0 0 ${t.space[8]} 0`,
          }}
        >
          Ranked by estimated impact. Expand any finding to see the underlying evidence.
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: t.space[4] }}>
          {findings && findings.map((f, i) => (
            <FindingCard
              key={f.key || i}
              finding={f}
              index={i}
              editorMode={editorMode}
              onSaveCommentary={onSaveCommentary}
              onDeleteCommentary={onDeleteCommentary}
              onRequestSuppress={onRequestSuppress}
              onUnsuppress={onUnsuppress}
            />
          ))}
        </div>
      </section>

      {/* Section 3 — Methodology footer */}
      {methodology && methodology.length > 0 && (
        <section
          style={{
            maxWidth: t.layout.readingWidth,
            margin: "0 auto",
            padding: `${t.space[12]} ${t.space[8]} ${t.space[20]}`,
            borderTop: `1px solid ${t.color.borderFaint}`,
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
              marginBottom: t.space[4],
              paddingTop: t.space[8],
            }}
          >
            How we built this
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: t.space[3] }}>
            {methodology.map((m, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "baseline",
                  gap: t.space[4],
                  padding: `${t.space[3]} 0`,
                  borderBottom: i < methodology.length - 1 ? `1px solid ${t.color.borderFaint}` : "none",
                }}
              >
                <span
                  style={{
                    fontFamily: t.font.display,
                    fontSize: t.size.sm,
                    fontWeight: t.weight.medium,
                    color: t.color.textPrimary,
                    minWidth: "200px",
                    flexShrink: 0,
                  }}
                >
                  {m.engine}
                </span>
                <span
                  style={{
                    fontFamily: t.font.body,
                    fontSize: t.size.sm,
                    color: t.color.textSecondary,
                    lineHeight: t.leading.normal,
                  }}
                >
                  {m.method}
                </span>
              </div>
            ))}
          </div>

          {data_coverage && (
            <div
              style={{
                marginTop: t.space[6],
                fontFamily: t.font.body,
                fontSize: t.size.xs,
                color: t.color.textTertiary,
              }}
            >
              Analysis covers {data_coverage.n_channels} channels across{" "}
              {data_coverage.n_campaigns} campaigns, {data_coverage.period_rows} data points.
            </div>
          )}
        </section>
      )}
    </main>
  );
}
