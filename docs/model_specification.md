# Model Specification
## Yield Intelligence Platform — Phase 1 Models
### Version 1.0 | April 2026

---

## 1. Response Curve Model (Power-Law)

### Mathematical Definition
```
Revenue(Spend) = a × Spend^b

Where:
  a > 0 : scale parameter (revenue per unit spend at spend=1)
  0 < b < 1 : diminishing returns exponent
```

### Fitting Method
- Transform to log-linear: log(Revenue) = log(a) + b × log(Spend)
- Solve via ordinary least squares on log-transformed monthly data
- Bounds: a ∈ (0, ∞), b ∈ (0.1, 0.95)
- Fallback: if fitting fails (R² < 0.3), use simple linear regression

### Derived Quantities
```
Marginal ROI at spend level x:
  dRevenue/dSpend = a × b × x^(b-1)

Saturation Point (where marginal ROI = 1):
  x_sat = (a × b)^(1/(1-b))

Headroom:
  Headroom% = max(0, (x_sat - x_current) / x_sat × 100)
```

### Data Requirements
- Minimum 6 months of monthly spend + revenue per channel
- At least 3 distinct spend levels (natural variation across months)
- Spend must be > 0 for all periods

### Goodness of Fit
- R² reported per channel
- If R² < 0.5: flag as low confidence
- If R² < 0.3: use linear fallback and warn user

---

## 2. Constrained Budget Optimization

### Objective Function
```
Maximize: Σ Revenue_i(Spend_i) for all channels i

Subject to:
  Σ Spend_i = Total_Budget              (budget constraint)
  Spend_i ≥ min_i                        (minimum per channel)
  Spend_i ≤ max_i                        (maximum per channel)
  Spend_locked_j = fixed_j               (locked channels)
```

### Objective Variants
| Objective | Maximize |
|-----------|----------|
| maximize_revenue | Σ Revenue_i(Spend_i) |
| maximize_roi | (Σ Revenue_i - Total_Budget) / Total_Budget |
| balanced | 0.4 × ΔRevenue% + 0.3 × ΔROI + 0.15 × Leakage_Reduction + 0.15 × Cost_Reduction |

### Solver
- **Method:** SLSQP (Sequential Least Squares Programming) via scipy.optimize.minimize
- **Fallback:** Greedy marginal equalization (iteratively move budget from lowest to highest marginal ROI)
- **Convergence:** ftol = 1e-10, maxiter = 1000

### Greedy Algorithm (Browser Implementation)
```
Initialize: Allocate proportional to current spend
Repeat 200 iterations:
  1. Compute marginal ROI for each unlocked channel
  2. If max_marginal / min_marginal < 1.05: STOP (marginals equalized)
  3. Move step_size (0.5% of budget) from lowest to highest marginal channel
  4. Respect min/max constraints
```

### Default Constraints
- Minimum per channel: 2% of total budget
- Maximum per channel: 35% of total budget
- Locked channels: excluded from reallocation

### Sensitivity Analysis
- Run optimization at budget × [0.8, 0.9, 1.0, 1.1, 1.2, 1.5]
- Report: projected revenue, projected ROI at each level
- Purpose: shows budget elasticity

---

## 3. Attribution Models

### 3.1 Last-Touch Attribution
```
For each converted journey J:
  Revenue_credit(last_touchpoint) = J.revenue
  Revenue_credit(all_others) = 0
```
- **Bias:** Overcredits bottom-funnel channels (search, retargeting)
- **Use:** Platform-reported baseline

### 3.2 Linear Multi-Touch Attribution
```
For each converted journey J with n touchpoints:
  Revenue_credit(touchpoint_i) = J.revenue / n
  Conversion_credit(touchpoint_i) = 1 / n
```
- **Bias:** Treats all touchpoints equally regardless of position
- **Use:** More balanced than last-touch; good default

### 3.3 Position-Based (U-Shaped) Attribution
```
For journey with n touchpoints:
  If n = 1: w_1 = 1.0
  If n = 2: w_1 = w_2 = 0.5
  If n ≥ 3:
    w_1 = 0.4 (first touch)
    w_n = 0.4 (last touch)
    w_i = 0.2 / (n - 2) for i ∈ {2, ..., n-1}

  Revenue_credit(touchpoint_i) = J.revenue × w_i
```
- **Bias:** Emphasizes discovery and conversion; underweights nurture
- **Use:** Most balanced for journey-aware analysis

### Data Requirement
- User-level journey data with touchpoint sequence
- Minimum 1,000 converted journeys for statistical reliability
- Channel must appear in ≥ 50 journeys to be attributed

---

## 4. Diagnostic Rules Engine

### Rule Definitions

| Rule ID | Condition | Type | Confidence |
|---------|-----------|------|------------|
| D1 | ROI > median × 1.3 AND headroom > 20% AND marginal_ROI > 1.5 | SCALE | High |
| D2 | marginal_ROI < 1.5 AND headroom < 15% | REDUCE | High |
| D3 | CTR > median × 1.5 AND CVR < median × 0.6 | FIX | High |
| D4 | CVR > median × 0.9 AND CAC > median × 1.5 | RETARGET | Medium |
| D5 | linear_revenue / last_touch_revenue > 1.4 | MAINTAIN | Medium |
| D6 | Lead→MQL rate < 30% | RESEQUENCE | Medium |
| D7 | Spend correlation > 0.7 AND efficiency declining | CONSOLIDATE | Low |

### Recommendation Quality Standard
Every recommendation MUST include:
1. **Type:** SCALE / REDUCE / FIX / RETARGET / MAINTAIN / RESEQUENCE / CONSOLIDATE
2. **Channel and campaign:** Specific, not generic
3. **Rationale:** Data-driven with specific numbers
4. **Action:** Concrete, actionable step
5. **Expected impact:** Dollar amount or ROI change
6. **Confidence:** High / Medium / Low with source
7. **Effort:** Low / Medium / High

### Impact Calculation
```
SCALE impact = spend × increase% × marginal_ROI × 0.8 (conservative)
REDUCE impact = -spend × decrease% × marginal_ROI
FIX impact = clicks × (median_CVR - actual_CVR) × AOV × 0.4 (40% fix rate)
RETARGET impact = (actual_CAC - median_CAC) × conversions × 0.3
MAINTAIN impact = linear_revenue - last_touch_revenue
```

---

## 5. Trend Analysis Model

### Anomaly Detection
```
Method: Z-score on monthly aggregated values
Threshold: |z| > 1.8 → anomaly
Severity: |z| > 3.0 → high, else medium
```

### Variance Decomposition
```
Method: H1 vs H2 comparison
Channel_Change = Σ Revenue_H2(channel) - Σ Revenue_H1(channel)
Contribution% = Channel_Change / Σ All_Channel_Changes × 100
```

### ROI Consistency
```
Method: Coefficient of Variation on monthly ROI per channel
CV = σ(monthly_ROI) / |μ(monthly_ROI)|
Classification: CV < 0.15 = High, < 0.30 = Medium, ≥ 0.30 = Low
```

---

## 6. Funnel Analysis Model

### Bottleneck Detection
```
For each funnel stage i (i > 0):
  actual_rate = volume[i] / volume[i-1]
  If actual_rate < benchmark[i] × 0.7:
    Mark as bottleneck
    lost_volume = volume[i-1] × (benchmark - actual_rate)
    Severity: actual < benchmark × 0.5 → critical, else → warning
```

### Revenue Impact Quantification
```
For each bottleneck:
  cascade_rate = Π stage_rate[j] for j > i
  additional_conversions = lost_volume × cascade_rate
  additional_revenue = additional_conversions × avg_revenue_per_conversion
```

---

## 7. Phase 2 Model Roadmap (Not Yet Implemented)

| Model | Purpose | Key Dependency |
|-------|---------|---------------|
| Bayesian MMM | Offline + cross-channel contribution | PyMC, 2+ years data |
| Adstock/Carryover | Lagged media effects | Weekly granularity |
| Hill Curves | Better saturation modeling | More data points |
| Prophet/ARIMA | Time-series forecasting | 2+ years history |
| Markov Chain | Probabilistic attribution | Full path data |
| Shapley Values | Game-theory credit | Complete touchpoint data |
| Multi-Objective Optimization | Competing goals | All Phase 1-2 outputs |
| Geo-Lift Testing | Causal measurement | Regional spend variation |
