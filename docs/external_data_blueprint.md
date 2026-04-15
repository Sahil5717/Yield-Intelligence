# External Data Integration — Complete Blueprint
## Yield Intelligence Platform

---

## Overview

Three CSV upload types that add market context to the optimization engine.
All are user-uploaded files (not live API integrations).

---

## CSV 1: COMPETITIVE INTELLIGENCE

### Source
User exports from SEMrush Domain Overview, SimilarWeb Marketing Channels,
Meta Ad Library, or manually curates from industry reports.

### CSV Template Columns

| Column | Required | Type | Example | Description |
|--------|----------|------|---------|-------------|
| date | Yes | YYYY-MM | 2025-01 | Month of observation |
| competitor | Yes | string | "CompetitorX" | Competitor name |
| channel | Yes | string | "paid_search" | Must match our channel taxonomy |
| estimated_spend | Yes | float | 450000 | Competitor's estimated spend on this channel |
| traffic_share | No | float | 0.23 | Their share of total category traffic (0-1) |
| impression_share | No | float | 0.35 | Their share of impressions in this channel |
| keyword_overlap | No | float | 0.42 | % of their keywords that overlap with ours |
| avg_cpc | No | float | 2.85 | Their avg CPC on this channel |
| avg_cpm | No | float | 12.50 | Their avg CPM on this channel |
| new_campaigns | No | int | 3 | # of new campaigns launched this month |
| creative_volume | No | int | 47 | # of unique ad creatives running |
| domain_authority | No | float | 72 | SEMrush domain authority score |
| organic_keywords | No | int | 15400 | # of organic keywords ranking |

### What Each Engine Does With This Data

**1. Optimizer (budget allocation)**
- Computes "Competitive Pressure Index" (CPI) per channel:
  CPI = our_spend / (our_spend + sum(competitor_spend)) per channel
- If CPI < 0.3 on a channel → flag as "competitively outspent"
- Adjusts min_spend_pct constraint: channels where CPI < 0.3 get
  a higher floor (don't let optimizer reduce spend on channels
  where you're already losing share of voice)
- Adjusts cost assumptions: if competitor avg_cpc is rising,
  assume our CPC will rise too → reduces predicted conversions per $

**2. Response Curves (diminishing returns)**
- Competitive spend acts as a "cost inflator" on the response curve:
  If competitors doubled spend on paid_search → our effective cost
  per click rises → our response curve shifts right (need more spend
  for same outcome)
- Adjustment: response_curve_revenue(spend) *= (1 - competitive_dampening)
  where competitive_dampening = f(competitor_spend_growth)

**3. Recommendations Engine**
- New recommendation type: "DEFEND"
  Triggered when: competitor increased spend >30% on a channel where
  we have high ROI. Action: "Maintain or increase spend on [channel]
  — [Competitor] increased spend by X%. Risk of losing impression
  share and CPC inflation."
- New recommendation type: "OPPORTUNITY"
  Triggered when: competitor DECREASED spend on a channel.
  Action: "Competitor pulled back on [channel]. Window to gain
  share at lower CPC."
- New recommendation type: "DIFFERNTIATE"
  Triggered when: keyword_overlap > 60% on paid_search.
  Action: "High keyword overlap with [Competitor]. Diversify to
  long-tail keywords or increase brand terms."

**4. Forecasting Engine**
- Adds competitor spend as an exogenous regressor in Prophet:
  model.add_regressor('competitor_spend_paid_search')
- If competitor spend is trending up → forecast adjusts CPC upward
  → predicted ROI on that channel drops

**5. Leakage / Value at Risk**
- New leakage category: "Competitive Risk"
  = revenue on channels where CPI < 0.25 (we're significantly outspent)
  This represents revenue that's at risk of being eroded by
  competitors even if our internal execution is perfect

**6. Executive Summary**
- "Competitive Landscape" section added
- Shows: Share of Voice by channel, competitive pressure index,
  which competitors are increasing/decreasing spend, head-to-head
  channel comparison

**7. Deep Dive (per channel)**
- "Competitive Positioning" card showing:
  Our spend vs competitor spend on this channel
  Our traffic share vs theirs
  CPC trend vs their CPC trend
  Keyword overlap %

### What the Frontend Shows

**New section on Executive Summary:**
- "Competitive Pressure" card with overall Share of Voice metric
- Red flag if any channel has CPI < 0.25

**New section on Optimizer:**
- "Competitive Floor" indicator per channel showing minimum spend
  needed to maintain share
- Warning when optimizer tries to cut spend on a channel where
  competitors are increasing

**New section on Deep Dive:**
- Competitive positioning chart (our spend vs top 3 competitors)
- Share of Voice over time per channel

---

## CSV 2: MARKET EVENTS & INTELLIGENCE

### Source
User curates from: industry reports, news, internal strategy docs,
analyst briefings, or their own competitive monitoring.

### CSV Template Columns

| Column | Required | Type | Example | Description |
|--------|----------|------|---------|-------------|
| event_date | Yes | YYYY-MM-DD | 2025-10-15 | When the event occurs/occurred |
| event_end_date | No | YYYY-MM-DD | 2025-10-20 | End date (for multi-day events) |
| event_type | Yes | enum | "competitor_launch" | See event types below |
| event_name | Yes | string | "CompX launches new product" | Short description |
| description | No | string | "Details..." | Longer context |
| impact_direction | Yes | enum | "negative" | positive / negative / neutral |
| impact_magnitude | No | enum | "high" | low / medium / high |
| impact_pct | No | float | -15 | Estimated % impact on our KPIs |
| affected_channels | No | string | "paid_search,display" | Comma-separated channels affected |
| affected_products | No | string | "Product A" | Our products affected |
| affected_regions | No | string | "North,South" | Regions affected |
| source | No | string | "Industry Report Q3" | Where this intelligence came from |
| confidence | No | enum | "confirmed" | confirmed / estimated / speculative |

### Event Types (event_type enum)

| Type | Description | Default Impact |
|------|-------------|----------------|
| competitor_launch | Competitor launches new product/campaign | negative on affected channels |
| competitor_exit | Competitor exits market/channel | positive (lower competition) |
| market_growth | Category/market expanding | positive (larger pie) |
| market_decline | Category/market contracting | negative (smaller pie) |
| regulation_change | New regulation affecting marketing | varies |
| seasonal_peak | Known demand peak (Diwali, Black Friday, IPL) | positive on all channels |
| seasonal_trough | Known demand trough | negative |
| cost_increase | CPM/CPC inflation expected | negative on ROI |
| cost_decrease | CPM/CPC deflation | positive on ROI |
| tech_change | Platform algorithm change (Meta, Google) | varies |
| pr_event | PR event (positive or negative) affecting brand | varies |
| economic_macro | Interest rate, inflation, GDP changes | varies |
| internal_launch | Our own product/campaign launch | positive |
| partnership | New distribution or media partnership | positive |

### What Each Engine Does With This Data

**1. Forecasting Engine (highest impact)**
- Events become Prophet "holidays" with impact windows:
  seasonal_peak events → positive holiday effect
  competitor_launch → negative holiday effect
  cost_increase → adjusts revenue forecast downward
- Each event gets a "prior_scale" based on impact_magnitude:
  low=0.05, medium=0.15, high=0.30
- Events with impact_pct override the prior_scale with
  an explicit regressor value
- Multi-day events (event_date to event_end_date) get
  the impact spread across the window

**2. Optimizer (budget phasing)**
- seasonal_peak events → optimizer increases budget weight
  for the affected months/channels
  E.g., "Diwali" in October → email and display get higher
  allocation in Sep-Oct-Nov window
- competitor_launch events → optimizer raises min_spend floor
  on affected channels during the impact window
- cost_increase events → optimizer adjusts the response curve
  predictions downward (same spend buys less)

**3. Recommendations Engine**
- New recommendation type: "PREPARE"
  Triggered by upcoming seasonal_peak or internal_launch.
  Action: "Diwali is 6 weeks out. Historically, email conversion
  rate increases 2.3x during festive periods. Pre-load creative
  and increase email budget by 40% starting [date]."
- New recommendation type: "MITIGATE"
  Triggered by upcoming competitor_launch or cost_increase.
  Action: "CompetitorX is launching [product] on [date].
  Expect 15% CPC increase on paid_search. Shift 10% of
  paid_search budget to organic content marketing."
- New recommendation type: "CAPITALIZE"
  Triggered by competitor_exit or cost_decrease.
  Action: "CPMs on display have dropped 12%. Window to acquire
  cheap reach. Increase display spend for awareness."

**4. Trend Analysis**
- Events annotated on the time-series charts as vertical markers
- Anomaly detection cross-references with events:
  "Revenue spike in October correlates with Diwali seasonal_peak event"
  "Revenue dip in March correlates with competitor_launch event"
- This makes anomalies explainable rather than just flagged

**5. Business Case**
- "Market Context" section listing upcoming events
  that affect the proposed plan
- Risk assessment: "This plan assumes no competitor launches
  in Q4. If [Competitor] launches, estimated impact: -15% on
  paid_search ROI."

**6. Leakage / Value at Risk**
- New leakage category: "Event Risk"
  = sum of (revenue_on_channel × impact_pct) for all negative
  upcoming events
  Represents value at risk from external market forces,
  not internal inefficiency

### What the Frontend Shows

**Executive Summary:**
- "Market Calendar" timeline showing upcoming events
  color-coded: green (opportunity), red (risk), yellow (neutral)
- "Event Risk" added to Value at Risk KPI

**Deep Dive:**
- Events overlaid on channel time-series charts as markers
- Tooltip shows event name, type, expected impact

**Optimizer:**
- "Event-Adjusted Allocation" mode that factors in upcoming
  events into the optimization
- Side-by-side: "BAU Plan" vs "Event-Adjusted Plan"

**Recommendations:**
- PREPARE, MITIGATE, CAPITALIZE rec types with event context
- Each includes: event name, timing, affected channels,
  recommended action, estimated impact

---

## CSV 3: MARKET TRENDS & BENCHMARKS

### Source
User exports from: Google Trends, industry benchmark reports,
eMarketer, Statista, platform analytics (Meta Business Suite,
Google Ads Performance Planner), or internal research.

### CSV Template Columns

| Column | Required | Type | Example | Description |
|--------|----------|------|---------|-------------|
| date | Yes | YYYY-MM | 2025-01 | Month of observation |
| metric_type | Yes | enum | "cpc_trend" | See metric types below |
| channel | No | string | "paid_search" | Channel this applies to (null = all) |
| region | No | string | "North" | Region (null = all) |
| value | Yes | float | 2.85 | The metric value |
| yoy_change_pct | No | float | 12.5 | Year-over-year change % |
| benchmark_source | No | string | "Google Ads" | Data source |
| category | No | string | "SaaS" | Industry category |
| notes | No | string | "Q4 spike expected" | Additional context |

### Metric Types (metric_type enum)

| Type | Unit | Description | Engines that use it |
|------|------|-------------|-------------------|
| cpc_trend | $ | Cost per click trend | Optimizer, Response Curves, Forecasting |
| cpm_trend | $ | Cost per mille trend | Optimizer, Response Curves, Forecasting |
| category_growth | % | Overall market growth rate | Forecasting, Business Case |
| category_spend | $ | Total industry ad spend | Competitive analysis |
| search_interest | index | Google Trends search interest (0-100) | Forecasting, Trend Analysis |
| consumer_sentiment | index | Consumer confidence / sentiment score | Forecasting |
| inflation_rate | % | General or media-specific inflation | Optimizer (cost adjustment) |
| channel_benchmark_ctr | % | Industry avg CTR for channel | Diagnostics, Funnel |
| channel_benchmark_cvr | % | Industry avg CVR for channel | Diagnostics, Funnel |
| channel_benchmark_cac | $ | Industry avg CAC for channel | ROI Formulas, Diagnostics |
| channel_benchmark_roas | x | Industry avg ROAS | ROI Formulas |
| media_cost_index | index | Overall media cost index (100=baseline) | Optimizer |

### What Each Engine Does With This Data

**1. Response Curves (most important)**
- CPC/CPM trends adjust the x-axis of the response curve:
  If CPC is rising 15% YoY, then $100K of paid_search spend
  next year buys what $87K bought this year.
  The curve shifts: revenue = f(spend / cost_inflation_factor)
- This changes marginal ROI, headroom, saturation point —
  the entire optimizer input changes
- Practical: the response curve fitted on historical data
  assumed 2024 CPCs. If 2025 CPCs are 15% higher, the curve
  overestimates conversions per dollar. This corrects it.

**2. Optimizer**
- Cost-adjusted optimization: instead of raw spend,
  optimizer works with "effective spend" = spend / cost_index
- If cost_index is rising for a channel, optimizer
  naturally reallocates away from it (same $ buys less)
- Category growth rate affects the baseline forecast:
  if market is growing 10%, some of "our growth" is
  just riding the wave, not media-driven
- Channel benchmark ROAS lets optimizer set realistic
  targets: don't expect 8x ROAS on display when industry
  average is 2.5x

**3. Forecasting Engine**
- Google Trends search interest becomes an exogenous
  regressor in Prophet (like holidays but continuous)
- Category growth rate adjusts the trend component:
  if category is growing 10% but our forecast shows 5%,
  we're losing share
- Consumer sentiment as regressor for revenue forecasting
- Media cost index as regressor for spend forecasting

**4. Diagnostics / Recommendations**
- New recommendation type: "BENCHMARK"
  Triggered when: our CTR/CVR/CAC is significantly worse
  than industry benchmark for that channel.
  Action: "Your paid_search CTR is 2.1% vs industry avg 3.5%.
  Below benchmark by 40%. Review ad copy and targeting."
- New recommendation type: "COST_ALERT"
  Triggered when: CPC/CPM trend shows >15% increase.
  Action: "Paid search CPC has risen 18% YoY. Expected to
  continue. Shift 10% of budget to channels with stable costs."
- Benchmark comparison adds credibility to all existing
  recs: "REDUCE display spend — your ROAS is 1.2x vs
  industry benchmark 2.5x on this channel"

**5. ROI Formulas**
- Benchmark ROAS/CAC per channel enables:
  "Relative performance" metric = our_ROAS / benchmark_ROAS
  Values >1 = outperforming industry, <1 = underperforming
- This goes into Executive Summary as a new KPI:
  "Portfolio vs Industry" score

**6. Funnel Analysis**
- Benchmark CTR/CVR per channel enables:
  Gap analysis: "Your click→lead rate is 4.2% vs industry 7.1%"
  This makes the bottleneck detection much more meaningful
  because "below median" becomes "below industry standard"

**7. Trend Analysis**
- Google Trends overlaid on our revenue time series
- Correlation analysis: does our revenue track with
  search interest? If not, we may be losing organic share
- Seasonal decomposition uses search interest as an
  external seasonal signal

**8. MMM (Marketing Mix Model)**
- Category growth rate becomes a control variable in MMM:
  Revenue = baseline + trend + media_effects + category_growth + season
  Without this, MMM attributes market-wide growth to media,
  inflating channel contributions

**9. Business Case**
- "Market Context" section:
  "Our plan assumes CPC inflation of 15% in Q4. If inflation
  is lower, upside is +$X. If higher, downside is -$Y."
- Industry benchmark comparison gives credibility:
  "Our projected ROI of 4.2x is 1.7x the industry average,
  indicating room for controlled scaling."

### What the Frontend Shows

**Executive Summary:**
- "Market Pulse" card: category growth, cost trend (up/down),
  consumer sentiment
- "vs Industry" badge on ROI KPI: "4.2x (1.7x above benchmark)"

**Performance Screen:**
- Benchmark column in channel table: our CTR vs industry CTR
  with red/green color coding
- "Cost Trend" indicator per channel (↑ rising, → stable, ↓ falling)

**Deep Dive:**
- Google Trends overlay on channel revenue chart
- Industry benchmark lines on funnel visualization
  (dashed lines showing "where you should be")

**Optimizer:**
- "Cost-Adjusted" toggle: optimize using current costs vs
  forecasted costs (with CPC/CPM inflation factored in)
- Shows: "This allocation assumes CPC inflation of X% on
  paid_search. Sensitivity: if inflation is 0%, revenue
  increases by $Y."

**Business Case:**
- Full "Market Context" section
- Risk/opportunity table from cost trends
- Industry benchmark comparison for projected ROI

---

## DATA FLOW SUMMARY

```
                    ┌─────────────────────┐
                    │   USER UPLOADS CSV   │
                    └─────┬───────────────┘
                          │
          ┌───────────────┼───────────────────┐
          ▼               ▼                   ▼
    Competitive      Market Events       Market Trends
    Intelligence     & Intelligence      & Benchmarks
          │               │                   │
          ▼               ▼                   ▼
    ┌───────────┐   ┌──────────┐       ┌──────────┐
    │ Share of  │   │ Event    │       │ Cost     │
    │ Voice     │   │ Calendar │       │ Adjuster │
    │ Engine    │   │ Engine   │       │ Engine   │
    └─────┬─────┘   └────┬─────┘       └────┬─────┘
          │               │                   │
          ▼               ▼                   ▼
    ┌─────────────────────────────────────────────┐
    │           ENRICHED ENGINE CHAIN              │
    ├──────────────────────────────────────────────┤
    │                                              │
    │  Response Curves ← cost adjustments          │
    │  MMM ← category growth as control var        │
    │  Forecasting ← events as holidays,           │
    │                 trends as regressors          │
    │  Optimizer ← competitive floors,             │
    │               cost-adjusted curves,          │
    │               event-weighted phasing          │
    │  Diagnostics ← benchmark comparisons,        │
    │                 DEFEND/PREPARE/CAPITALIZE     │
    │  Leakage ← competitive risk,                 │
    │             event risk categories             │
    │  Funnel ← industry benchmark lines           │
    │  Trend ← event annotations,                  │
    │           search interest overlay             │
    │  ROI ← vs-industry relative performance      │
    │  Business Case ← market context section,     │
    │                   risk/opportunity table      │
    │                                              │
    └──────────────────────┬───────────────────────┘
                           │
                           ▼
                   ┌───────────────┐
                   │  FRONTEND UI   │
                   │  + new cards   │
                   │  + overlays    │
                   │  + benchmarks  │
                   │  + calendar    │
                   └───────────────┘
```

---

## NEW RECOMMENDATION TYPES (summary)

| Type | Trigger Source | Example |
|------|---------------|---------|
| DEFEND | Competitive CSV | "Competitor increased paid_search spend 40%. Maintain budget." |
| OPPORTUNITY | Competitive CSV | "Competitor pulled back on display. Capture cheap reach." |
| DIFFERENTIATE | Competitive CSV | "62% keyword overlap with CompX. Diversify to long-tail." |
| PREPARE | Market Events CSV | "Diwali in 6 weeks. Email converts 2.3x higher during festive." |
| MITIGATE | Market Events CSV | "CompX launching in Oct. Expect 15% CPC inflation." |
| CAPITALIZE | Market Events CSV | "CPMs dropped 12%. Window for cheap awareness." |
| BENCHMARK | Market Trends CSV | "Your CTR 2.1% vs industry 3.5%. Review ad copy." |
| COST_ALERT | Market Trends CSV | "CPC up 18% YoY. Shift budget to stable-cost channels." |

Existing types remain: SCALE, REDUCE, FIX, RETARGET, MAINTAIN, RESEQUENCE

---

## BUILD ORDER (recommended)

### Phase 1: CSV Templates + Ingestion + Storage
- Define CSV schemas with validation
- Build upload endpoints (3 new POST endpoints)
- Store in _state alongside campaign data
- Auto-detect column formats (reuse mapping engine)
- Estimated: 1 session

### Phase 2: Engine Integration — Market Trends (highest ROI)
- Cost-adjust response curves
- Add benchmarks to diagnostics
- Add regressors to forecasting
- BENCHMARK and COST_ALERT rec types
- Estimated: 1 session

### Phase 3: Engine Integration — Market Events
- Event calendar engine
- Prophet holiday injection
- Optimizer event-weighted phasing
- PREPARE, MITIGATE, CAPITALIZE rec types
- Event annotations on charts
- Estimated: 1–2 sessions

### Phase 4: Engine Integration — Competitive Intelligence
- Share of Voice computation
- Competitive pressure index
- Optimizer competitive floors
- DEFEND, OPPORTUNITY, DIFFERENTIATE rec types
- Competitive positioning in deep dive
- Estimated: 1–2 sessions

### Phase 5: Frontend — New UI Components
- Market Calendar timeline
- Competitive positioning charts
- Benchmark overlays on existing charts
- Cost-adjusted toggle on optimizer
- Market Context section on business case
- Estimated: 1 session

---

## WHAT WE ARE NOT BUILDING
- Live API integrations (SEMrush, SimilarWeb, Google Trends API)
- Automated web scraping of competitor data
- AI/LLM-generated insights from news articles
- Real-time competitive monitoring dashboards
- Data licensing or procurement
