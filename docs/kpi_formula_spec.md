# KPI Formula Specification
## Yield Intelligence Platform — Phase 1
### Version 1.0 | April 2026

---

## 1. ROI Formulas

### 1.1 Base ROI
```
Base ROI = (Revenue - Marketing Cost) / Marketing Cost
```
- **Input:** revenue (SUM), spend (SUM)
- **Output:** Ratio (e.g., 2.5 = 250% return)
- **Edge case:** If spend = 0 → return NULL (not zero, not infinity)
- **Use:** General performance reporting
- **Aggregation:** Can be computed at channel, campaign, region, or total level

### 1.2 Gross Margin ROI
```
GM ROI = (Revenue × Gross_Margin_% - Marketing Cost) / Marketing Cost
```
- **Input:** revenue (SUM), spend (SUM), gross_margin_pct (configurable, default 0.65)
- **Output:** Ratio
- **Edge case:** If spend = 0 → NULL; if GM% not configured → use 65%
- **Use:** Profitability analysis; answers "did we actually make money after COGS?"
- **Note:** Gross margin % should be set per product line if available

### 1.3 ROAS (Return on Ad Spend)
```
ROAS = Attributed Revenue / Ad Spend
```
- **Input:** revenue (SUM), spend (SUM)
- **Output:** Ratio (e.g., 3.0 = $3 revenue per $1 spent)
- **Edge case:** If spend = 0 → NULL
- **Use:** Media efficiency comparison
- **Difference from ROI:** Does not subtract cost from numerator; ROAS of 1.0 = breakeven

### 1.4 Incremental ROI
```
Incremental ROI = (ΔRevenue - ΔSpend) / ΔSpend

Where:
  ΔRevenue = (Revenue_Period2 / Months_P2) - (Revenue_Period1 / Months_P1)
  ΔSpend = (Spend_Period2 / Months_P2) - (Spend_Period1 / Months_P1)
```
- **Input:** Monthly revenue and spend data; baseline period definition
- **Baseline:** Default = first 3 months (Q1); incremental = remaining months
- **Output:** Ratio
- **Edge cases:**
  - If ΔSpend ≤ 0 → return 0 (spend decreased; incremental ROI undefined)
  - If baseline period has < 2 months → return NULL
- **Use:** True lift measurement; answers "what did additional spend produce?"
- **Limitation:** Not causal without holdout/geo-lift testing

### 1.5 Marginal ROI
```
Marginal ROI = dRevenue / dSpend = a × b × spend^(b-1)

Where response curve: Revenue = a × Spend^b
```
- **Input:** Fitted response curve parameters (a, b) per channel
- **Output:** Ratio at a specific spend level
- **Edge cases:**
  - If spend = 0 → return infinity (clamp to 999)
  - If curve not fitted (R² < 0.3) → return NULL with warning
- **Use:** Budget optimization decisions; answers "what's the return on the NEXT dollar?"
- **Critical note:** This is the most important metric for optimization. Channels should be funded until marginal ROI equalizes across channels.

---

## 2. Efficiency Formulas

### 2.1 Click-Through Rate (CTR)
```
CTR = Clicks / Impressions
```
- Edge: impressions = 0 → NULL
- Display as percentage

### 2.2 Conversion Rate (CVR)
```
CVR = Conversions / Clicks
```
- Edge: clicks = 0 → NULL

### 2.3 Cost Per Click (CPC)
```
CPC = Spend / Clicks
```

### 2.4 Cost Per Lead (CPL)
```
CPL = Spend / Leads
```

### 2.5 Cost Per Acquisition (CPA / CAC)
```
CAC = Spend / Conversions
```

### 2.6 Lead-to-Sale Rate
```
L2S = Conversions / Leads
```

---

## 3. Funnel Conversion Formulas

### 3.1 Stage Conversion Rate
```
Stage_CVR[i] = Volume[i] / Volume[i-1]
```
- Stages: Impressions → Clicks → Leads → MQLs → SQLs → Conversions
- Edge: Volume[i-1] = 0 → NULL

### 3.2 Stage Drop-Off Rate
```
Drop_Off[i] = 1 - Stage_CVR[i]
```

### 3.3 Overall Funnel Conversion
```
Overall_CVR = Conversions / Impressions
```

### 3.4 Bottleneck Detection
```
Bottleneck = TRUE if Stage_CVR[i] < Benchmark[i] × 0.7

Benchmarks:
  Impression→Click: 2.0%
  Click→Lead: 8.0%
  Lead→MQL: 45.0%
  MQL→SQL: 38.0%
  SQL→Conversion: 25.0%
```
- Severity: "critical" if actual < benchmark × 0.5, else "warning"

### 3.5 Funnel Revenue Impact
```
Lost_Volume[i] = Volume[i-1] × (Benchmark_Rate - Actual_Rate)
Cascade_Rate = Product(Stage_CVR[j]) for j = i+1 to n
Additional_Conversions = Lost_Volume × Cascade_Rate
Additional_Revenue = Additional_Conversions × Avg_Revenue_Per_Conversion
```

---

## 4. Trend & Variance Formulas

### 4.1 Month-over-Month Change
```
MoM_Change_% = (Value[t] - Value[t-1]) / Value[t-1] × 100
```

### 4.2 Moving Average
```
MA_n[t] = (1/n) × Σ Value[t-k] for k = 0 to n-1
```
- Windows: n = 3 (short-term), n = 6 (medium-term)

### 4.3 Anomaly Detection (Z-Score)
```
z[t] = (Value[t] - μ) / σ
Anomaly = TRUE if |z| > 1.8

Where:
  μ = mean of all periods
  σ = standard deviation of all periods
```
- Severity: "high" if |z| > 3.0, "medium" if |z| > 1.8
- Direction: "spike" if z > 0, "dip" if z < 0

### 4.4 ROI Consistency (Coefficient of Variation)
```
CV = σ(ROI) / |μ(ROI)|

Consistency:
  "High" if CV < 0.15
  "Medium" if CV < 0.30
  "Low" if CV ≥ 0.30
```

### 4.5 Variance Decomposition
```
Channel_Contribution_% = Channel_Change / Total_Change × 100

Where:
  Channel_Change = Channel_Revenue_H2 - Channel_Revenue_H1
  Total_Change = Σ Channel_Change for all channels
```

---

## 5. Three Pillar Impact Formulas

### 5.1 Revenue Leakage
```
Total_Leakage = Optimized_Revenue - Actual_Revenue

Channel_Leakage[ch] = max(0, Optimized_Revenue[ch] - Actual_Revenue[ch])
```
- Uses same response curve model for both actual and optimized calculations
- Defensible because counterfactual uses identical model

### 5.2 Conversion Suppression (Experience Impact)
```
For campaigns where CTR > median_CTR AND CVR < median_CVR × 0.7:

  CVR_Gap = Median_CVR - Actual_CVR
  Suppressed_Conversions = Clicks × CVR_Gap
  Suppressed_Revenue = Suppressed_Conversions × (Revenue / Conversions)
```
- Only flagged for campaigns with > 1,000 clicks (statistical significance)

### 5.3 Avoidable Cost
```
For channels where CAC > Median_CAC × 1.3:

  Excess_CAC = Actual_CAC - Median_CAC
  Avoidable_Cost = Excess_CAC × Conversion_Volume
```

### 5.4 Correction Potential
```
Revenue_Uplift = Leakage × 0.6 (conservative recovery rate)
Experience_Recovery = Suppressed_Revenue × 0.4
Cost_Savings = Avoidable_Cost × 0.7
Total_Recoverable = Revenue_Uplift + Experience_Recovery + Cost_Savings
```

---

## 6. Payback Period
```
Payback_Month = min(t) where Σ Revenue[1..t] ≥ Σ Spend[1..t]
```
- If never reached within data range → return total months
- Computed per channel

---

## 7. Attribution Formulas

### 7.1 Last-Touch
```
Credit[last_touchpoint] = 100% of conversion revenue
Credit[all_other_touchpoints] = 0%
```

### 7.2 Linear Multi-Touch
```
Credit[each_touchpoint] = Conversion_Revenue / Total_Touchpoints
```

### 7.3 Position-Based (U-Shaped)
```
If touchpoints = 1: Credit = 100%
If touchpoints = 2: Credit = 50% each
If touchpoints ≥ 3:
  Credit[first] = 40%
  Credit[last] = 40%
  Credit[middle_each] = 20% / (Total_Touchpoints - 2)
```
