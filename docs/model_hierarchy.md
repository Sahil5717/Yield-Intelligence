# Model Hierarchy & Decision Governance
## Yield Intelligence Platform

---

## The Problem This Document Solves

This platform runs 18 analytical engines. When they disagree — and they will — the user needs to know which output to trust and present. This document defines that hierarchy.

---

## Decision Layers (top to bottom)

### Layer 1: Descriptive (What happened?)
**Confidence: High | Use: Always safe to present**

| Output | Engine | Basis | Governance |
|--------|--------|-------|------------|
| Total ROI, ROAS, CAC | roi_formulas.py | Direct arithmetic on actuals | Always correct if data is correct |
| Channel × campaign matrix | Direct aggregation | Sum of spend/revenue/conversions | No model involved — this is fact |
| Funnel conversion rates | funnel_analysis.py | Actual stage-to-stage ratios | Correct by definition |
| Monthly trends | trend_analysis.py | Observed time series | Factual; anomalies flagged by z-score |

**Rule: Present these without caveats. If someone challenges these numbers, the data is wrong, not the model.**

---

### Layer 2: Attribution (Who gets credit?)
**Confidence: Medium–High | Use: Present with model context**

| Output | Engine | When to use | When NOT to use |
|--------|--------|-------------|-----------------|
| Last-touch attribution | attribution.py | Default for teams that lack journey data | Never for media mix decisions — heavily biased to bottom-funnel |
| Linear attribution | attribution.py | When you want equal credit across touchpoints | Not useful for prioritization |
| Position-based (40/20/40) | attribution.py | Best default for most consulting presentations | Weights are assumed, not estimated |
| Markov chain attribution | markov_attribution.py | When you have rich journey data (3+ touchpoints per journey) | Not with <500 journeys — insufficient transition data |
| Shapley values | shapley.py | For game-theoretic fairness analysis | Computationally expensive with 12+ channels; use as validation, not primary |

**Rule: Always present at least 2 attribution models side by side. If they disagree by >30%, call out the variance. The "official" answer for client presentations should be position-based unless Markov data is strong.**

**If Markov and last-touch disagree:** Markov wins. Last-touch systematically overweights bottom-funnel channels.

---

### Layer 3: Econometric (What drives what?)
**Confidence: Medium | Use: Present with methodology notes**

| Output | Engine | Reliability | Minimum data |
|--------|--------|-------------|--------------|
| Response curves (power-law) | response_curves.py | Good with 24+ months | 12 months minimum, 24+ recommended |
| Response curves (Hill) | response_curves.py | Better for saturated channels | Same, but needs visible saturation in data |
| MMM channel contributions | mmm.py | Strong with 36+ months + PyMC | 24 months minimum; Bayesian needs 36+ |
| Adstock decay rates | adstock.py | Good for channels with carryover (TV, events) | 18+ months |
| Forecasting (Prophet/ARIMA) | forecasting.py | Good for stable businesses | 24+ months with consistent seasonality |

**Rule: Always show R² or model fit metric alongside econometric outputs. If R² < 0.5, flag the channel as "low-confidence model."**

**If MMM and response curves disagree on a channel's contribution:**
- MMM is more reliable for *historical* decomposition (it accounts for baseline + seasonality)
- Response curves are more reliable for *marginal* spend decisions (they estimate the derivative)
- Present MMM for "how much did this channel contribute?" and response curves for "should we spend more?"

---

### Layer 4: Optimization (What should we do?)
**Confidence: Medium | Use: Present as directional, not prescriptive**

| Output | Engine | Reliability | Caveat |
|--------|--------|-------------|--------|
| Optimized budget allocation | optimizer.py (SLSQP) | Reliable if response curves are reliable | Optimizer is only as good as the curves it uses |
| Sensitivity analysis | optimizer.py | Good for showing diminishing returns | Budget scenarios, not point estimates |
| Multi-objective Pareto | multi_objective.py | Shows tradeoffs, not "the answer" | Use to facilitate discussion, not dictate |
| Marginal ROI table | response_curves.py | Directionally correct | Exact numbers depend on curve fit quality |

**Rule: Never present the optimizer output as "the answer." Present it as "the model suggests this allocation would improve ROI by X%, subject to these assumptions." Always show the sensitivity table alongside the point estimate.**

**The optimizer's output is DIRECTIONAL, not PRESCRIPTIVE.**

---

### Layer 5: Diagnostics (What's wrong and what to fix?)
**Confidence: Medium–High | Use: Present as hypotheses to investigate**

| Output | Engine | Basis | Action |
|--------|--------|-------|--------|
| Revenue leakage | leakage.py | Gap between actual and optimized allocation | Validate with 60-day budget shift test |
| CX suppression | leakage.py | CVR gap × traffic × AOV | Validate with landing page audit |
| Avoidable cost | leakage.py | CAC above median × conversions | Validate with bid/audience review |
| Recommendations | diagnostics.py | Rules + statistical significance tests | Each rec includes confidence + effort rating |

**Rule: Recommendations are hypotheses, not instructions. Each one should be validated before scaling. The "effort" rating tells you which ones to test first.**

---

## When Models Conflict: Resolution Framework

| Conflict | Resolution |
|----------|------------|
| Last-touch vs Markov attribution | Markov wins (more methodologically sound) |
| MMM vs response curves on channel value | MMM for historical truth, curves for future decisions |
| Power-law vs Hill response curves | Use Hill when channel shows clear saturation; power-law otherwise |
| Optimizer says cut a channel, attribution says it assists | Don't cut. Maintain spend; the channel has indirect value |
| Forecast says growth, optimizer says flat | Present both; the gap is the "execution premium" — growth only happens if the plan is implemented |

---

## Confidence Tiers

| Tier | Meaning | Display |
|------|---------|---------|
| **High** | Based on direct measurement (online, pixel-tracked) | Green badge |
| **Medium** | Based on statistical model with R² > 0.5 | Amber badge |
| **Model-Estimated** | Offline channel, modeled from correlation | Orange badge |
| **Low** | Insufficient data or poor model fit | Red badge, flagged |

---

## What to Say to Clients

**"How accurate is this?"**
→ "The descriptive layer (ROI, funnel, trends) is factual. The econometric layer (response curves, MMM) is model-based with R² of X. The optimizer output is directional — it shows the best allocation *if* the curves are correct, which is why we recommend validating with a 60-day test."

**"Which attribution model should we use?"**
→ "Position-based is our default. If you have journey data with 3+ touchpoints, Markov is more accurate. We show both so you can see where they agree and where they diverge."

**"Can we trust the MMM?"**
→ "With 36+ months of data, the Bayesian MMM produces reliable channel contributions with credible intervals. With less data, we fall back to OLS regression which is directionally useful but has wider uncertainty."
