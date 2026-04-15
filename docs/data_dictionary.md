# Data Dictionary
## Yield Intelligence Platform — Marketing ROI & Budget Optimization Engine
### Version 1.0 | Phase 1 | April 2026

---

## 1. Input Data Schema

### 1.1 Campaign Performance File (Required)

| Column | Data Type | Required | Validation Rules | Description |
|--------|-----------|----------|------------------|-------------|
| date | DATE (YYYY-MM-DD) | Yes | Must parse as valid date; range: last 3 years | Reporting period start date |
| channel | STRING | Yes | Non-null; maps to standard channel taxonomy | Marketing channel identifier |
| campaign | STRING | Yes | Non-null; max 200 chars | Campaign name or identifier |
| spend | NUMERIC (≥0) | Yes | Non-negative; no nulls; currency in base unit | Total media + production cost |
| revenue | NUMERIC (≥0) | Yes | Non-negative | Attributed revenue from this channel-campaign |
| impressions | INTEGER (≥0) | No | Non-negative integer | Ad impressions served |
| clicks | INTEGER (≥0) | No | Non-negative; clicks ≤ impressions | Clicks or visits from this source |
| leads | INTEGER (≥0) | No | Non-negative; leads ≤ clicks | Form submissions, inquiries, sign-ups |
| mqls | INTEGER (≥0) | No | Non-negative; mqls ≤ leads | Marketing qualified leads |
| sqls | INTEGER (≥0) | No | Non-negative; sqls ≤ mqls | Sales qualified leads |
| conversions | INTEGER (≥0) | No | Non-negative; conversions ≤ sqls | Completed purchases or deals |
| region | STRING | No | Maps to standard region taxonomy | Geographic region |
| product | STRING | No | Maps to standard product taxonomy | Product line or business unit |
| bounce_rate | DECIMAL (0-1) | No | 0 ≤ value ≤ 1 | Bounce rate for traffic from this source |
| avg_session_duration_sec | NUMERIC (≥0) | No | Non-negative; in seconds | Average session duration |
| form_completion_rate | DECIMAL (0-1) | No | 0 ≤ value ≤ 1 | Form start-to-complete rate |
| nps_score | INTEGER (-100 to 100) | No | -100 ≤ value ≤ 100 | Net Promoter Score |
| unsubscribe_rate | DECIMAL (0-1) | No | 0 ≤ value ≤ 0.1; email channel only | Email unsubscribe rate |

**Grain:** One row per Date × Channel × Campaign × Region combination.
**Minimum rows:** 100 (for meaningful analysis)
**Recommended:** 6+ months, 500+ rows

### 1.2 User Journey File (Optional — required for multi-touch attribution)

| Column | Data Type | Required | Validation Rules | Description |
|--------|-----------|----------|------------------|-------------|
| journey_id | STRING | Yes | Unique per user journey | User/session identifier |
| touchpoint_order | INTEGER (≥1) | Yes | Sequential within journey | Position in journey |
| total_touchpoints | INTEGER (≥1) | Yes | Consistent within journey_id | Total touchpoints in this journey |
| date | DATE | Yes | Valid date | Touchpoint date |
| channel | STRING | Yes | Maps to channel taxonomy | Channel of this touchpoint |
| campaign | STRING | Yes | Maps to campaign taxonomy | Campaign of this touchpoint |
| converted | BOOLEAN | Yes | TRUE/FALSE | Did this journey result in conversion? |
| conversion_revenue | NUMERIC (≥0) | Yes | >0 only on last touchpoint if converted | Revenue attributed to conversion |

**Grain:** One row per Journey × Touchpoint.

---

## 2. Standard Taxonomies

### 2.1 Channel Taxonomy

| Standard Channel | Type | Common Raw Values (Auto-Mapped) |
|-----------------|------|--------------------------------|
| paid_search | Online | "paid search", "ppc", "sem", "google ads", "bing ads", "adwords" |
| organic_search | Online | "organic search", "seo", "organic", "natural search" |
| social_paid | Online | "paid social", "facebook ads", "meta ads", "linkedin ads", "tiktok ads" |
| display | Online | "display", "banner", "programmatic", "gdn", "dv360" |
| email | Online | "email", "email marketing", "newsletter", "edm" |
| video_youtube | Online | "video", "youtube", "ott", "pre-roll", "video ads" |
| events | Offline | "events", "trade show", "conference", "webinar" |
| direct_mail | Offline | "direct mail", "postal", "mailer", "catalog" |
| affiliate | Online | "affiliate", "referral", "partner" |
| content | Online | "content", "content marketing", "blog" |

### 2.2 Confidence Tiers

| Tier | Description | Channels | Methodology |
|------|-------------|----------|-------------|
| High | Directly tracked with user-level data | Paid search, social paid, email, display, website | Platform APIs + multi-touch attribution |
| Medium | Partially linked via matching or proxies | Events (with registration), call center (with tracking) | Code/UTM matching, CRM linkage |
| Model-Estimated | No user-level tracking; modeled contribution | TV, radio, OOH, print, brand campaigns | MMM (Phase 2), geo-lift, time-lag correlation |

---

## 3. Computed Metrics

### 3.1 Volume Metrics
| Metric | Formula | Type |
|--------|---------|------|
| Total Spend | SUM(spend) | Aggregation |
| Total Revenue | SUM(revenue) | Aggregation |
| Total Conversions | SUM(conversions) | Aggregation |

### 3.2 Efficiency Metrics
| Metric | Formula | Edge Case |
|--------|---------|-----------|
| CTR | clicks / impressions | If impressions = 0, return NULL |
| CPC | spend / clicks | If clicks = 0, return NULL |
| CPL | spend / leads | If leads = 0, return NULL |
| CPA | spend / conversions | If conversions = 0, return NULL |
| CAC | spend / conversions | Alias of CPA in this context |
| CVR | conversions / clicks | If clicks = 0, return NULL |
| Lead-to-Sale Rate | conversions / leads | If leads = 0, return NULL |

### 3.3 ROI Metrics (5 formulas)
| Metric | Formula | Edge Case | Best For |
|--------|---------|-----------|----------|
| Base ROI | (revenue - spend) / spend | If spend = 0, return NULL | General reporting |
| Gross Margin ROI | (revenue × GM% - spend) / spend | GM% configurable (default 65%) | Profitability |
| ROAS | revenue / spend | If spend = 0, return NULL | Media efficiency |
| Incremental ROI | (Δrevenue - Δspend) / Δspend | Baseline = Q1; if Δspend ≤ 0, return 0 | True lift |
| Marginal ROI | dRevenue/dSpend | From response curve derivative | Budget decisions |

### 3.4 Diagnostic Metrics
| Metric | Formula | Threshold |
|--------|---------|-----------|
| Revenue Leakage | Optimized Revenue - Actual Revenue | Flag if > 5% of revenue |
| Conversion Suppression | (Expected CVR - Actual CVR) × Traffic × AOV | Flag if CVR < 70% of median |
| Avoidable Cost | (Actual CAC - Benchmark CAC) × Conversion Volume | Flag if CAC > 130% of median |
| Payback Period | Month where cumulative revenue ≥ cumulative spend | Flag if > 6 months |

---

## 4. Output Tables

### 4.1 Fact_Optimization
| Column | Type | Description |
|--------|------|-------------|
| scenario_id | STRING | Optimization scenario identifier |
| channel | STRING | Standard channel name |
| current_spend | NUMERIC | Current annual spend |
| optimized_spend | NUMERIC | Recommended annual spend |
| change_pct | NUMERIC | % change from current |
| projected_revenue | NUMERIC | Model-projected revenue at optimized spend |
| projected_roi | NUMERIC | Projected ROI at optimized spend |
| marginal_roi | NUMERIC | Marginal return at optimized spend level |
| confidence | STRING | High / Medium / Model-Estimated |

### 4.2 Fact_Recommendations
| Column | Type | Description |
|--------|------|-------------|
| rec_id | STRING | Recommendation identifier (REC-001) |
| type | STRING | SCALE / REDUCE / FIX / RETARGET / MAINTAIN / RESEQUENCE / CONSOLIDATE |
| channel | STRING | Affected channel |
| campaign | STRING | Affected campaign (if applicable) |
| rationale | STRING | Structured explanation |
| action | STRING | Specific recommended action |
| expected_impact | NUMERIC | Estimated revenue impact |
| confidence | STRING | High / Medium / Low |
| effort | STRING | Low / Medium / High / None |
| status | STRING | pending / approved / rejected / parked |
