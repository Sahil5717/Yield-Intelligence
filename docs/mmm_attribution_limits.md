# Understanding MMM Attribution Output

*How to read Yield Intelligence's MMM output and what it honestly tells you*

## TL;DR

Marketing Mix Modelling (MMM) is a regression — it can only attribute revenue
to a channel when that channel's spend *varies* over time in a way correlated
with revenue. Channels you've spent the same on every month for four years
will get absorbed into the baseline, regardless of how much revenue they
actually drive. This is a property of all MMM implementations, not a flaw in
ours. What's different about Yield Intelligence is that we're explicit about
this limitation rather than hiding it behind false precision.

Pair MMM with incrementality tests (geo-lift, send-time holdouts) for a
complete attribution picture. MMM tells you *where variation lives*;
incrementality tests tell you *what's causal* on the steady-state.

## Why MMM output doesn't match "ground truth"

### What "ground truth" means here

In real client engagements there is no ground truth — nobody can directly
observe which dollar of spend produced which dollar of revenue. The best
approximation is a holdout test: run a geo-lift where one region gets
reduced spend, measure the revenue delta.

In our mock data, we know the ground truth because we generated the data.
Each channel's spend is converted into revenue through a deterministic
funnel + calibration multiplier. The "true" channel contribution is simply
the share of revenue each channel produces in the synthetic world.

### Current mock-data calibration (v14+)

Ground truth contribution in the synthetic data:

| Channel | Ground truth % | MLE MMM % | Bayesian MMM % |
|---|---|---|---|
| Paid search | 34% | 13% | 15% |
| Social paid | 19% | 10% | 2% |
| Events | 16% | 24% | 13% |
| Email | 12% | 2% | 2% |
| Organic search | 8% | < 1% | 2% |
| Video/YouTube | 6% | < 1% | 3% |
| Display | 3% | 3% | 2% |
| Direct mail | 2% | < 1% | 2% |
| (Baseline) | 0% | ~47% | ~59% |

There's a consistent pattern: **MMM over-weights channels with spiky
temporal patterns (events) and under-weights channels with steady spend
(paid search, email).** It also assigns 47-59% of revenue to "baseline"
— which by construction is zero in the synthetic data.

### Why this happens — the core mechanism

MMM fits a regression of the form:

```
Revenue(t) = baseline + β_paid_search · f(Paid_Search_Spend(t))
                     + β_events      · f(Events_Spend(t))
                     + …
                     + seasonal_terms + error
```

The regression can only *identify* a coefficient β_c when the corresponding
`f(Spend_c(t))` varies enough over time to distinguish its contribution
from everything else. Three specific failure modes:

1. **Steady channels get absorbed into baseline.** If paid search spend
   is roughly the same every month, there's no variation for the
   regression to correlate with revenue variation. The model's best-fit
   answer is "paid search contributes some constant amount per month" —
   which is mathematically indistinguishable from baseline.

2. **Highly-correlated channel pairs collapse.** If two channels both
   spike in November every year, the regression can't tell which one
   caused the November revenue lift. The collinearity inflates the
   variance of both coefficients (Bayesian produces wide HDIs; OLS
   produces unstable point estimates).

3. **Spike channels get over-weighted.** Events has clearly-identifiable
   spikes in March/September each year. Those spikes align with observable
   revenue increases. MMM correctly attributes that revenue to events.
   But it also attributes revenue that *would have happened anyway* to
   events, because the model can't distinguish "events drove this" from
   "both events and the underlying business cycle happened in March."

### What this means for client presentations

> "Your MMM says paid search is 5% of revenue, but you know it's your
> biggest channel. Is the model wrong?"

The model isn't wrong — it's saying something different than you might
think. "5%" means "5% of revenue *varies* in a way that correlates with
paid search spend." The rest of paid search's contribution is absorbed
into baseline because paid search spend didn't vary enough to identify
a coefficient.

The right follow-up is: **test incrementality.** Either run a geo-lift
on paid search (cut spend in one region for a month, measure the revenue
gap), or use platform-side holdout experiments. That test gives you the
incremental value of paid search at current spend, which is the number
you actually want for budget decisions.

## How Yield Intelligence handles this

### Confidence tiers, surfaced per channel

Every MMM output carries a confidence tier:

- **High**: CI width < 25% of point estimate. Coefficient is stable;
  number is defensible to a CFO.
- **Medium**: CI width 25-50%. Directional signal only; recommend in
  conjunction with other evidence.
- **Low**: CI width > 50%. Data does not identify this channel. Present
  as "inconclusive" and push for an incrementality test.

On the calibrated mock data, events typically comes back High, paid
search Medium, small/steady channels Low. That's the honest picture.

### Three-tier Bayesian → MLE → OLS fallback

The auto chain tries Bayesian first. If Bayesian doesn't converge
(r-hat > 1.05 or ESS < 100), it falls through to MLE. If MLE fits
badly (R² < 0), it falls through to OLS with NNLS. Each tier's
diagnostics are reported:

```json
{
  "method": "bayesian_pymc",
  "model_diagnostics": {
    "r_squared": 0.86,
    "mape": 4.73,
    "r_hat_max": 1.01,
    "ess_min": 313,
    "converged": true
  }
}
```

A technical reviewer can see exactly which method produced the numbers
and how trustworthy the fit is.

### Optimizer respects the extrapolation envelope

The optimizer doesn't push channels more than 3x their observed spend
range, because the fitted response curve stops being trustworthy beyond
that point (see `DEFAULT_EXTRAPOLATION_CAP` in `backend/engines/optimizer.py`).
When a user requests a total budget larger than the channels can absorb
within that envelope, the optimizer returns a capacity warning:

> "Requested budget ($500M) exceeds what the fitted curves can
> trustworthily absorb ($87M at 3x current spend per channel). Beyond-
> capacity spend has no predicted return — a larger sample of historical
> data at higher spend levels is needed before extrapolating."

No silent extrapolation; no optimizer recommending a +4,657% reallocation.

### Presenter talking points

For the pitch, lead with the limitation instead of hiding it. The
honest framing is a *differentiator* against black-box competitors:

1. **MMM is directional, not absolute.** Use it for relative channel
   comparisons and budget reallocation decisions, not as the sole
   source of truth for any single channel's contribution.

2. **Pair MMM with incrementality.** For each of the client's top 3-5
   channels, design and run a holdout test in the first 90 days. This
   gives you a causal anchor to calibrate MMM against.

3. **Watch the confidence tier column.** Recommendations for Low-tier
   channels should always say "test before acting." Recommendations
   for High-tier channels are safe to execute.

4. **Baseline is not "nothing."** A 50% baseline doesn't mean half your
   revenue has no driver — it means half your revenue has drivers the
   MMM can't see (brand equity, pipeline maturation, non-marketing
   factors). Treat it as the unassigned remainder, not as "we don't
   know."

## What NOT to claim

- **Don't claim MMM gives a per-channel ROAS that matches incrementality
  tests.** On most data they will disagree, and the disagreement is
  informative.

- **Don't claim MMM "proves" what drives revenue.** It's regression, not
  experiment. It shows correlation-with-a-model.

- **Don't claim the tool will find hidden contributions in channels
  with flat spend.** It fundamentally can't, and hand-waving this is
  what got previous consultancy MMMs reputations for unreliability.

## Further reading

- Meta's Robyn open-source MMM documentation explicitly discusses the
  identifiability issue: https://facebookexperimental.github.io/Robyn/
- Google's LightweightMMM paper discusses Bayesian priors as an
  identifiability aid: https://github.com/google/lightweight_mmm
- "Challenges And Opportunities In Media Mix Modelling", Chan et al.
  (Google Research, 2017) is the canonical reference for the
  baseline-absorption problem.
