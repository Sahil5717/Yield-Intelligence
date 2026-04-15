"""
Adstock & Carryover Models — Production Grade
===============================================
Geometric decay: adstock[t] = x[t] + λ·adstock[t-1]
Weibull decay: flexible shape for delayed peak effects (TV, events)
Hill saturation: y = x^S / (K^S + x^S)
Fitting: scipy.optimize.minimize for decay + half-saturation parameters.

Libraries: scipy.optimize.minimize, numpy, pandas
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize, differential_evolution
from typing import Dict, Optional

def geometric_adstock(x, decay=0.5, max_lag=8):
    out = np.zeros_like(x, dtype=float); out[0] = x[0]
    for t in range(1, len(x)): out[t] = x[t] + decay * out[t-1]
    return out

def weibull_adstock(x, shape=2.0, scale=1.0, max_lag=12):
    lags = np.arange(max_lag) + 1e-10
    kernel = (shape/scale) * (lags/scale)**(shape-1) * np.exp(-(lags/scale)**shape)
    kernel = np.nan_to_num(kernel); ks = kernel.sum()
    kernel = kernel/ks if ks > 0 else np.ones(max_lag)/max_lag
    return np.convolve(x, kernel, mode='full')[:len(x)]

def hill_saturation(x, half_saturation, slope=1.0):
    x_safe = np.maximum(x, 1e-10)
    return x_safe**slope / (half_saturation**slope + x_safe**slope)

def fit_adstock_params(spend, revenue, adstock_type="geometric"):
    """
    Fit adstock decay (and optionally Hill saturation K) by maximizing
    correlation between adstocked-saturated spend and revenue.
    Uses scipy differential_evolution for global optimization.
    """
    if spend.sum() == 0 or len(spend) < 3:
        return {"decay": 0.0, "half_saturation": 1.0, "correlation": 0.0, "carryover_pct": 0.0}

    def neg_corr(params):
        if adstock_type == "geometric":
            decay = params[0]; half_sat = params[1]
            ad = geometric_adstock(spend, decay)
        else:
            shape, scale, half_sat = params[0], params[1], params[2]
            ad = weibull_adstock(spend, shape, scale)
        sat = hill_saturation(ad, half_sat)
        if sat.std() == 0: return 0
        return -np.corrcoef(sat, revenue)[0, 1]

    if adstock_type == "geometric":
        bounds = [(0.01, 0.95), (1, float(np.median(spend[spend > 0])*5 + 1))]
    else:
        bounds = [(0.5, 5.0), (0.5, 5.0), (1, float(np.median(spend[spend > 0])*5 + 1))]

    try:
        result = differential_evolution(neg_corr, bounds, seed=42, maxiter=200, tol=1e-6)
        best_corr = -result.fun
        if adstock_type == "geometric":
            decay, half_sat = result.x
            ad = geometric_adstock(spend, decay)
            carryover = (ad.sum() - spend.sum()) / max(spend.sum(), 1) * 100
            return {"decay": round(decay, 3), "half_saturation": round(half_sat, 2),
                    "correlation": round(best_corr, 4), "carryover_pct": round(carryover, 1),
                    "effective_lag": round(1/(1-decay), 1) if decay < 1 else 99}
        else:
            shape, scale, half_sat = result.x
            return {"shape": round(shape, 3), "scale": round(scale, 3),
                    "half_saturation": round(half_sat, 2), "correlation": round(best_corr, 4)}
    except Exception as e:
        return {"decay": 0.5, "half_saturation": 1.0, "correlation": 0.0, "error": str(e)}

def compute_channel_adstock(df, adstock_type="geometric"):
    """Fit adstock params for each channel. Returns dict of fitted params + transformed series."""
    results = {}
    time_col = "month" if "month" in df.columns else "date"
    for ch in df["channel"].unique():
        ch_data = df[df["channel"] == ch]
        monthly = ch_data.groupby(time_col).agg(spend=("spend","sum"), revenue=("revenue","sum")).reset_index().sort_values(time_col)
        spend = monthly["spend"].values.astype(float); rev = monthly["revenue"].values.astype(float)
        params = fit_adstock_params(spend, rev, adstock_type)
        if adstock_type == "geometric":
            ad = geometric_adstock(spend, params.get("decay", 0.5))
        else:
            ad = weibull_adstock(spend, params.get("shape", 2.0), params.get("scale", 1.0))
        results[ch] = {"params": params, "original_spend": spend.tolist(),
            "adstocked_spend": ad.tolist(), "revenue": rev.tolist(), "periods": monthly[time_col].tolist()}
    return results
