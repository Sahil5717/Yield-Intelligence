import { tokens as t } from "../tokens.js";
import { KpiPill } from "../components/KpiPill.jsx";
import { MoveCard } from "../components/MoveCard.jsx";
import { TradeoffCard } from "../components/TradeoffCard.jsx";

/**
 * Plan screen — the "here's what to do" surface.
 *
 * Visual structure parallels the Diagnosis screen so a reader moving
 * between the two surfaces doesn't have to re-learn the layout:
 *   1. Section label + hero paragraph (the rationale, not a summary)
 *   2. KPI row: Reallocation Size, Expected Uplift, Plan Confidence
 *   3. Moves — grouped visually by direction (Increase / Reduce / Hold)
 *      but emitted in impact order by the backend
 *   4. Tradeoffs — honest caveats, quieter tone than the moves
 *   5. Methodology footer
 *
 * Grouping moves visually (rather than showing them in pure impact order)
 * is a deliberate choice: on Diagnosis, findings are heterogeneous and
 * ordering by impact is the obvious presentation. On Plan, moves are all
 * the same shape (channel + action) and grouping by direction helps a
 * reader scan "what am I being asked to increase?" separately from
 * "what am I being asked to cut?" That's how a CMO will think about it.
 */
export function Plan({
  data,
  editorMode = false,
  onSaveCommentary,
  onDeleteCommentary,
  onRequestSuppress,
  onUnsuppress,
}) {
  if (!data) return null;

  const { headline_paragraph, kpis, moves, tradeoffs, methodology, summary } = data;

  // Group moves by action direction. Within each group the backend's
  // impact-ordering is preserved, so the biggest-impact items float up
  // within their group.
  const increases = (moves || []).filter((m) => m.action === "increase");
  const decreases = (moves || []).filter((m) => m.action === "decrease");
  const holds = (moves || []).filter((m) => m.action === "hold");

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
          Plan
        </div>

        {/* Hero card */}
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
        {kpis && kpis.reallocation_size && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: t.space[4],
              animation: `kpiFadeIn ${t.motion.slow} ${t.motion.ease} 120ms both`,
            }}
          >
            <KpiPill
              label={kpis.reallocation_size.label}
              display={kpis.reallocation_size.display}
              tone={kpis.reallocation_size.tone}
              context={kpis.reallocation_size.context}
            />
            <KpiPill
              label={kpis.expected_uplift.label}
              display={kpis.expected_uplift.display}
              tone={kpis.expected_uplift.tone}
              context={kpis.expected_uplift.context}
            />
            <KpiPill
              label={kpis.plan_confidence.label}
              display={kpis.plan_confidence.display}
              tone={kpis.plan_confidence.tone}
              context={kpis.plan_confidence.context}
            />
          </div>
        )}
      </section>

      {/* Section 2 — Moves */}
      <section
        style={{
          maxWidth: t.layout.readingWidth,
          margin: "0 auto",
          padding: `${t.space[4]} ${t.space[8]} ${t.space[12]}`,
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
          Reallocation
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
          Channel-by-channel moves
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
          Ranked by revenue impact within each direction. Expand any card for the rationale.
        </p>

        {increases.length > 0 && (
          <MoveGroup
            label={`Increase (${increases.length})`}
            moves={increases}
            editorMode={editorMode}
            onSaveCommentary={onSaveCommentary}
            onDeleteCommentary={onDeleteCommentary}
            onRequestSuppress={onRequestSuppress}
            onUnsuppress={onUnsuppress}
            startIndex={0}
          />
        )}

        {decreases.length > 0 && (
          <MoveGroup
            label={`Reduce (${decreases.length})`}
            moves={decreases}
            editorMode={editorMode}
            onSaveCommentary={onSaveCommentary}
            onDeleteCommentary={onDeleteCommentary}
            onRequestSuppress={onRequestSuppress}
            onUnsuppress={onUnsuppress}
            startIndex={increases.length}
          />
        )}

        {holds.length > 0 && (
          <MoveGroup
            label={`Hold (${holds.length})`}
            moves={holds}
            editorMode={editorMode}
            onSaveCommentary={onSaveCommentary}
            onDeleteCommentary={onDeleteCommentary}
            onRequestSuppress={onRequestSuppress}
            onUnsuppress={onUnsuppress}
            startIndex={increases.length + decreases.length}
          />
        )}
      </section>

      {/* Section 3 — Tradeoffs */}
      {tradeoffs && tradeoffs.length > 0 && (
        <section
          style={{
            maxWidth: t.layout.readingWidth,
            margin: "0 auto",
            padding: `${t.space[4]} ${t.space[8]} ${t.space[12]}`,
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
            Tradeoffs
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
            What we're assuming, and where to validate
          </h2>
          <p
            style={{
              fontFamily: t.font.body,
              fontSize: t.size.sm,
              color: t.color.textSecondary,
              lineHeight: t.leading.normal,
              margin: `0 0 ${t.space[6]} 0`,
            }}
          >
            These caveats matter for acting on the plan with appropriate confidence.
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: t.space[3] }}>
            {tradeoffs.map((tr, i) => (
              <TradeoffCard key={tr.key || i} tradeoff={tr} index={i} />
            ))}
          </div>
        </section>
      )}

      {/* Section 4 — Methodology footer */}
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
                  {m.objective && ` · objective: ${m.objective}`}
                </span>
              </div>
            ))}
          </div>

          {summary && summary.total_budget > 0 && (
            <div
              style={{
                marginTop: t.space[6],
                fontFamily: t.font.body,
                fontSize: t.size.xs,
                color: t.color.textTertiary,
              }}
            >
              Plan optimized at ${(summary.total_budget / 1e6).toFixed(1)}M budget · projected uplift {summary.uplift_pct?.toFixed(1)}%.
            </div>
          )}
        </section>
      )}
    </main>
  );
}

/**
 * MoveGroup — labeled subsection (Increase / Reduce / Hold) wrapping
 * its member move cards. The group label is small and muted — the moves
 * themselves carry the visual weight.
 *
 * startIndex is used so the staggered fade-in animation indexes
 * correctly across groups (otherwise all three groups would start their
 * animation at index 0 simultaneously, which looks wrong).
 */
function MoveGroup({
  label, moves, editorMode, onSaveCommentary, onDeleteCommentary,
  onRequestSuppress, onUnsuppress, startIndex = 0,
}) {
  return (
    <div style={{ marginBottom: t.space[8] }}>
      <div
        style={{
          fontFamily: t.font.body,
          fontSize: t.size.xs,
          fontWeight: t.weight.semibold,
          color: t.color.textTertiary,
          textTransform: "uppercase",
          letterSpacing: t.tracking.wider,
          marginBottom: t.space[3],
        }}
      >
        {label}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: t.space[3] }}>
        {moves.map((m, i) => (
          <MoveCard
            key={m.key}
            move={m}
            index={startIndex + i}
            editorMode={editorMode}
            onSaveCommentary={onSaveCommentary}
            onDeleteCommentary={onDeleteCommentary}
            onRequestSuppress={onRequestSuppress}
            onUnsuppress={onUnsuppress}
          />
        ))}
      </div>
    </div>
  );
}
