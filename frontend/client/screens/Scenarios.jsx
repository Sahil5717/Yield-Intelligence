import { useState, useEffect, useCallback } from "react";
import { tokens as t } from "../tokens.js";
import { fetchScenario, fetchScenarioPresets } from "../api.js";
import { KpiPill } from "../components/KpiPill.jsx";
import { MoveCard } from "../components/MoveCard.jsx";
import { TradeoffCard } from "../components/TradeoffCard.jsx";

/**
 * Scenarios screen — the "what if we did X instead?" surface.
 *
 * Same visual structure as Diagnosis and Plan (hero, KPIs, moves,
 * tradeoffs) but with a control panel at the top that lets the user
 * choose a budget scenario. Four presets (Current, Cut 20%, Increase
 * 25%, Optimizer recommended) plus a custom budget input for the
 * "what if" they don't see in the preset list.
 *
 * Above the moves: a comparison card showing the deltas vs. baseline
 * (the current allocation at current spend). This is what justifies
 * the screen's existence as separate from Plan — Plan tells you what
 * to do; Scenarios shows what happens if you don't.
 *
 * Editor controls (commentary / suppress) deliberately NOT wired here.
 * Scenarios are exploratory — the EY analyst's curation belongs on
 * the Diagnosis and Plan screens that get published. A scenario is a
 * tool the analyst USES, not a deliverable they CURATE.
 */
export function Scenarios({ data: initialData, initialPreset = null, view = "client" }) {
  // Initial data is whatever was loaded by the app shell (the baseline
  // scenario by default). The screen manages its own subsequent fetches
  // when the user clicks presets, so the state lives here, not in the
  // shell.
  const [scenarioData, setScenarioData] = useState(initialData);
  const [presets, setPresets] = useState([]);
  const [activePreset, setActivePreset] = useState(initialPreset || "baseline");
  const [customBudget, setCustomBudget] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load presets on mount
  useEffect(() => {
    (async () => {
      const { data } = await fetchScenarioPresets();
      if (data?.presets) setPresets(data.presets);
    })();
  }, []);

  const runScenario = useCallback(async (totalBudget, presetKey = null) => {
    setLoading(true);
    setError(null);
    const { data, error: err } = await fetchScenario({ totalBudget, view });
    setLoading(false);
    if (err) {
      setError(err.message || "Couldn't run scenario");
      return;
    }
    setScenarioData(data);
    setActivePreset(presetKey || "custom");
  }, [view]);

  function handlePresetClick(preset) {
    setCustomBudget(""); // clear the custom input when a preset is chosen
    runScenario(preset.total_budget, preset.key);
  }

  function handleCustomSubmit(e) {
    e.preventDefault();
    const value = parseFloat(customBudget);
    if (!isFinite(value) || value <= 0) return;
    // Convert from millions back to dollars (the input is in $M)
    runScenario(value * 1_000_000, "custom");
  }

  if (!scenarioData) return null;

  const { headline_paragraph, kpis, moves, tradeoffs, comparison } = scenarioData;
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
      {/* Section 1 — Hero with controls */}
      <section
        style={{
          maxWidth: t.layout.gridWidth,
          margin: "0 auto",
          padding: `${t.space[16]} ${t.space[8]} ${t.space[8]}`,
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
          Scenarios
        </div>

        <h1
          style={{
            fontFamily: t.font.display,
            fontSize: "clamp(1.75rem, 3vw, 2.25rem)",
            fontWeight: t.weight.semibold,
            color: t.color.textPrimary,
            letterSpacing: t.tracking.tight,
            lineHeight: t.leading.tight,
            margin: `0 0 ${t.space[3]} 0`,
            maxWidth: t.layout.readingWidth,
          }}
        >
          What happens if we change the budget?
        </h1>
        <p
          style={{
            fontFamily: t.font.body,
            fontSize: t.size.lg,
            color: t.color.textSecondary,
            lineHeight: t.leading.relaxed,
            margin: `0 0 ${t.space[8]} 0`,
            maxWidth: t.layout.readingWidth,
          }}
        >
          Pick a preset or set a custom budget. The model re-optimizes the channel allocation for the new spend level and shows the projected outcome compared to today's baseline.
        </p>

        {/* Control panel: presets + custom input */}
        <ControlPanel
          presets={presets}
          activePreset={activePreset}
          customBudget={customBudget}
          onCustomBudgetChange={setCustomBudget}
          onPresetClick={handlePresetClick}
          onCustomSubmit={handleCustomSubmit}
          loading={loading}
        />

        {error && (
          <div
            style={{
              marginTop: t.space[4],
              padding: `${t.space[3]} ${t.space[4]}`,
              background: t.color.negativeBg,
              color: t.color.negative,
              borderLeft: `3px solid ${t.color.negative}`,
              borderRadius: t.radius.sm,
              fontFamily: t.font.body,
              fontSize: t.size.sm,
            }}
            role="alert"
          >
            {error}
          </div>
        )}
      </section>

      {/* Section 2 — Comparison card (the "vs. baseline" summary) */}
      {comparison && (
        <section
          style={{
            maxWidth: t.layout.gridWidth,
            margin: "0 auto",
            padding: `0 ${t.space[8]} ${t.space[10]}`,
          }}
        >
          <ComparisonCard comparison={comparison} />
        </section>
      )}

      {/* Section 3 — KPI row */}
      {kpis && kpis.reallocation_size && (
        <section
          style={{
            maxWidth: t.layout.gridWidth,
            margin: "0 auto",
            padding: `0 ${t.space[8]} ${t.space[12]}`,
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: t.space[4],
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
        </section>
      )}

      {/* Section 4 — Allocation under this scenario */}
      <section
        style={{
          maxWidth: t.layout.readingWidth,
          margin: "0 auto",
          padding: `0 ${t.space[8]} ${t.space[12]}`,
        }}
      >
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
          Allocation under this scenario
        </h2>
        <p
          style={{
            fontFamily: t.font.body,
            fontSize: t.size.sm,
            color: t.color.textSecondary,
            margin: `0 0 ${t.space[8]} 0`,
          }}
        >
          {headline_paragraph}
        </p>

        {increases.length > 0 && (
          <MoveGroup label={`Increase (${increases.length})`} moves={increases} startIndex={0} />
        )}
        {decreases.length > 0 && (
          <MoveGroup label={`Reduce (${decreases.length})`} moves={decreases} startIndex={increases.length} />
        )}
        {holds.length > 0 && (
          <MoveGroup label={`Hold (${holds.length})`} moves={holds} startIndex={increases.length + decreases.length} />
        )}
      </section>

      {/* Section 5 — Tradeoffs */}
      {tradeoffs && tradeoffs.length > 0 && (
        <section
          style={{
            maxWidth: t.layout.readingWidth,
            margin: "0 auto",
            padding: `0 ${t.space[8]} ${t.space[20]}`,
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
              margin: `0 0 ${t.space[6]} 0`,
            }}
          >
            What this scenario assumes
          </h2>
          <div style={{ display: "flex", flexDirection: "column", gap: t.space[3] }}>
            {tradeoffs.map((tr, i) => (
              <TradeoffCard key={tr.key || i} tradeoff={tr} index={i} />
            ))}
          </div>
        </section>
      )}
    </main>
  );
}

// ─── Control panel ───

function ControlPanel({ presets, activePreset, customBudget, onCustomBudgetChange, onPresetClick, onCustomSubmit, loading }) {
  return (
    <div
      style={{
        background: t.color.surface,
        border: `1px solid ${t.color.border}`,
        borderRadius: t.radius.lg,
        padding: `${t.space[6]} ${t.space[6]}`,
        boxShadow: t.shadow.card,
        display: "flex",
        flexDirection: "column",
        gap: t.space[5],
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
        }}
      >
        Choose a scenario
      </div>

      {/* Preset buttons */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: t.space[3] }}>
        {presets.map((p) => (
          <PresetButton
            key={p.key}
            preset={p}
            active={activePreset === p.key}
            disabled={loading}
            onClick={() => onPresetClick(p)}
          />
        ))}
      </div>

      {/* Custom budget input */}
      <form
        onSubmit={onCustomSubmit}
        style={{
          display: "flex",
          alignItems: "flex-end",
          gap: t.space[3],
          paddingTop: t.space[5],
          borderTop: `1px solid ${t.color.borderFaint}`,
        }}
      >
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: t.space[2] }}>
          <label
            htmlFor="custom-budget"
            style={{
              fontFamily: t.font.body,
              fontSize: t.size.xs,
              fontWeight: t.weight.semibold,
              color: t.color.textSecondary,
              textTransform: "uppercase",
              letterSpacing: t.tracking.wider,
            }}
          >
            Or set a custom budget
          </label>
          <div style={{ display: "flex", alignItems: "center", gap: t.space[2] }}>
            <span style={{ fontFamily: t.font.body, fontSize: t.size.md, color: t.color.textTertiary }}>
              $
            </span>
            <input
              id="custom-budget"
              type="number"
              value={customBudget}
              onChange={(e) => onCustomBudgetChange(e.target.value)}
              placeholder="e.g. 30"
              min="0.1"
              step="0.5"
              disabled={loading}
              style={{
                flex: 1,
                padding: `${t.space[2]} ${t.space[3]}`,
                border: `1px solid ${t.color.border}`,
                borderRadius: t.radius.sm,
                fontFamily: t.font.body,
                fontSize: t.size.md,
                color: t.color.textPrimary,
                background: t.color.canvas,
                outline: "none",
                maxWidth: "180px",
              }}
            />
            <span
              style={{
                fontFamily: t.font.body,
                fontSize: t.size.sm,
                color: t.color.textTertiary,
              }}
            >
              million / year
            </span>
          </div>
        </div>
        <button
          type="submit"
          disabled={loading || !customBudget}
          style={{
            padding: `${t.space[2]} ${t.space[5]}`,
            background: t.color.accent,
            color: t.color.textInverse,
            border: "none",
            borderRadius: t.radius.sm,
            fontFamily: t.font.body,
            fontSize: t.size.sm,
            fontWeight: t.weight.semibold,
            cursor: loading || !customBudget ? "not-allowed" : "pointer",
            opacity: loading || !customBudget ? 0.5 : 1,
            transition: `opacity ${t.motion.fast} ${t.motion.ease}`,
          }}
        >
          {loading ? "Running…" : "Run scenario"}
        </button>
      </form>
    </div>
  );
}

function PresetButton({ preset, active, disabled, onClick }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        textAlign: "left",
        padding: `${t.space[4]} ${t.space[4]}`,
        background: active ? t.color.accentSubtle : t.color.canvas,
        border: `1px solid ${active ? t.color.accent : t.color.border}`,
        borderRadius: t.radius.md,
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled && !active ? 0.5 : 1,
        transition: `background ${t.motion.fast} ${t.motion.ease}, border-color ${t.motion.fast} ${t.motion.ease}`,
        display: "flex",
        flexDirection: "column",
        gap: t.space[2],
        fontFamily: "inherit",
      }}
      onMouseEnter={(e) => {
        if (!disabled && !active) {
          e.currentTarget.style.background = t.color.surfaceSunken;
          e.currentTarget.style.borderColor = t.color.borderStrong;
        }
      }}
      onMouseLeave={(e) => {
        if (!disabled && !active) {
          e.currentTarget.style.background = t.color.canvas;
          e.currentTarget.style.borderColor = t.color.border;
        }
      }}
    >
      <div
        style={{
          fontFamily: t.font.display,
          fontSize: t.size.md,
          fontWeight: t.weight.semibold,
          color: active ? t.color.accent : t.color.textPrimary,
          letterSpacing: t.tracking.snug,
        }}
      >
        {preset.label}
      </div>
      <div
        style={{
          fontFamily: t.font.display,
          fontSize: t.size.lg,
          fontWeight: t.weight.semibold,
          color: t.color.textPrimary,
          letterSpacing: t.tracking.tight,
        }}
      >
        ${(preset.total_budget / 1e6).toFixed(1)}M
      </div>
      <div
        style={{
          fontFamily: t.font.body,
          fontSize: t.size.xs,
          color: t.color.textTertiary,
          lineHeight: t.leading.normal,
        }}
      >
        {preset.description}
      </div>
    </button>
  );
}

// ─── Comparison card ───

function ComparisonCard({ comparison }) {
  const { narrative, scenario, baseline, deltas } = comparison;
  const revPositive = deltas.revenue_delta > 0;
  const roiPositive = deltas.roi_delta > 0;

  return (
    <div
      style={{
        background: t.color.surface,
        border: `1px solid ${t.color.border}`,
        borderRadius: t.radius.xl,
        padding: `${t.space[8]} ${t.space[10]}`,
        boxShadow: t.shadow.card,
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
        }}
      >
        Compared to baseline
      </div>

      <p
        style={{
          fontFamily: t.font.display,
          fontSize: "clamp(1.25rem, 1.8vw, 1.5rem)",
          fontWeight: t.weight.regular,
          color: t.color.textPrimary,
          lineHeight: t.leading.relaxed,
          letterSpacing: t.tracking.snug,
          margin: `0 0 ${t.space[8]} 0`,
        }}
      >
        {narrative}
      </p>

      {/* Delta grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: t.space[6],
          paddingTop: t.space[6],
          borderTop: `1px solid ${t.color.borderFaint}`,
        }}
      >
        <DeltaCell
          label="Budget"
          baselineValue={`$${(baseline.total_budget / 1e6).toFixed(1)}M`}
          scenarioValue={`$${(scenario.total_budget / 1e6).toFixed(1)}M`}
          delta={deltas.budget_delta}
          format={(v) => `${v >= 0 ? "+" : "-"}$${(Math.abs(v) / 1e6).toFixed(1)}M`}
          tone="neutral"
        />
        <DeltaCell
          label="Projected revenue"
          baselineValue={`$${(baseline.projected_revenue / 1e6).toFixed(1)}M`}
          scenarioValue={`$${(scenario.projected_revenue / 1e6).toFixed(1)}M`}
          delta={deltas.revenue_delta}
          format={(v) => `${v >= 0 ? "+" : "-"}$${(Math.abs(v) / 1e6).toFixed(1)}M`}
          tone={revPositive ? "positive" : "warning"}
        />
        <DeltaCell
          label="Portfolio ROI"
          baselineValue={`${baseline.projected_roi.toFixed(1)}x`}
          scenarioValue={`${scenario.projected_roi.toFixed(1)}x`}
          delta={deltas.roi_delta}
          format={(v) => `${v >= 0 ? "+" : ""}${v.toFixed(2)}x`}
          tone={roiPositive ? "positive" : "warning"}
        />
      </div>
    </div>
  );
}

function DeltaCell({ label, baselineValue, scenarioValue, delta, format, tone }) {
  const toneColor = tone === "positive" ? t.color.positive : tone === "warning" ? t.color.warning : t.color.textSecondary;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: t.space[2] }}>
      <span
        style={{
          fontFamily: t.font.body,
          fontSize: t.size.xs,
          fontWeight: t.weight.semibold,
          color: t.color.textTertiary,
          textTransform: "uppercase",
          letterSpacing: t.tracking.wider,
        }}
      >
        {label}
      </span>
      <div style={{ display: "flex", alignItems: "baseline", gap: t.space[2] }}>
        <span
          style={{
            fontFamily: t.font.display,
            fontSize: t.size.xs,
            color: t.color.textTertiary,
            fontWeight: t.weight.regular,
          }}
        >
          {baselineValue}
        </span>
        <span style={{ fontFamily: t.font.body, fontSize: t.size.xs, color: t.color.textTertiary }}>
          →
        </span>
        <span
          style={{
            fontFamily: t.font.display,
            fontSize: t.size.xl,
            fontWeight: t.weight.semibold,
            color: t.color.textPrimary,
            letterSpacing: t.tracking.tight,
            lineHeight: t.leading.tight,
          }}
        >
          {scenarioValue}
        </span>
      </div>
      <span
        style={{
          fontFamily: t.font.body,
          fontSize: t.size.sm,
          fontWeight: t.weight.semibold,
          color: toneColor,
        }}
      >
        {format(delta)}
      </span>
    </div>
  );
}

// ─── Move group ───

function MoveGroup({ label, moves, startIndex = 0 }) {
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
          <MoveCard key={m.key} move={m} index={startIndex + i} editorMode={false} />
        ))}
      </div>
    </div>
  );
}
