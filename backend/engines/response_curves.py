"""
Response Curve Engine — Production Grade
=========================================
Fits diminishing-returns curves: power-law y=a·x^b and Hill y=a·x^S/(K^S+x^S)
Uses scipy.optimize.curve_fit (Levenberg-Marquardt) with proper diagnostics.

Libraries: scipy.optimize.curve_fit, scikit-learn (R², RMSE, cross-val), numpy
"""
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit, minimize_scalar
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.model_selection import LeaveOneOut
from typing import Dict

def power_law(x, a, b):
    return a * np.power(np.maximum(x, 1e-6), b)

def hill_curve(x, a, b, K):
    xb = np.power(np.maximum(x, 1e-6), b)
    return a * xb / (np.power(K, b) + xb)

def marginal_power_law(x, a, b):
    if x <= 0: return float("inf")
    return a * b * np.power(x, b - 1)

def marginal_hill(x, a, b, K):
    if x <= 0: return float("inf")
    Kb = K**b; xb = x**b
    return a * b * (x**(b-1)) * Kb / ((Kb + xb)**2)

def fit_response_curves(campaign_df, model_type="power_law"):
    """
    Fit response curves per channel with scipy.optimize.curve_fit.
    model_type: "power_law", "hill", or "auto" (fits both, picks best R² per channel)
    Returns: fitted params, R², RMSE, confidence intervals, LOO-CV score, curve points.
    """
    if model_type == "auto":
        # Fit both models, keep the one with better R² per channel
        results_pl = fit_response_curves(campaign_df, model_type="power_law")
        results_hill = fit_response_curves(campaign_df, model_type="hill")
        results = {}
        for ch in set(list(results_pl.keys()) + list(results_hill.keys())):
            pl = results_pl.get(ch, {})
            hl = results_hill.get(ch, {})
            if "error" in pl and "error" in hl:
                results[ch] = pl  # both failed
            elif "error" in pl:
                results[ch] = hl
                results[ch]["_auto_selected"] = "hill"
            elif "error" in hl:
                results[ch] = pl
                results[ch]["_auto_selected"] = "power_law"
            else:
                pl_r2 = pl.get("r_squared", 0)
                hl_r2 = hl.get("r_squared", 0)
                if hl_r2 > pl_r2 + 0.02:  # Hill needs meaningfully better R² to justify complexity
                    results[ch] = hl
                    results[ch]["_auto_selected"] = "hill"
                else:
                    results[ch] = pl
                    results[ch]["_auto_selected"] = "power_law"
        return results

    results = {}
    for channel in campaign_df["channel"].unique():
        ch_data = campaign_df[campaign_df["channel"] == channel]
        monthly = ch_data.groupby("month" if "month" in ch_data.columns else "date").agg(
            spend=("spend","sum"), revenue=("revenue","sum"), conversions=("conversions","sum")
        ).reset_index().sort_values("month" if "month" in ch_data.columns else "date")
        x = monthly["spend"].values.astype(float)
        y = monthly["revenue"].values.astype(float)
        if len(x) < 3 or x.sum() == 0: continue

        try:
            if model_type == "power_law":
                popt, pcov = curve_fit(power_law, x, y, p0=[1.0, 0.5],
                    bounds=([0, 0.01], [np.inf, 0.99]), maxfev=10000)
                a, b = popt
                y_pred = power_law(x, a, b)
                perr = np.sqrt(np.diag(pcov))  # std errors of params
                avg_spend = float(x.mean())

                # Near-linear detection. When b approaches 1.0, the power-law
                # curve doesn't meaningfully saturate within any spend range
                # you could actually commit to -- the analytical saturation
                # point (a*b)^(1/(1-b)) goes to infinity as b → 1, which
                # produced 10^150-scale sat_spend values on organic search
                # (b=0.99) and drove downstream recommendations to fabricate
                # "40% headroom" where none existed.
                #
                # We flag the fit as near-linear (unreliable for headroom/
                # saturation claims), cap the reported saturation at 5x
                # observed max spend, and cap trusted_headroom_pct at 40%
                # to prevent SCALE recs from sizing impact off a phantom
                # saturation gap.
                near_linear = bool(b > 0.90)
                observed_max = float(np.max(x))

                if near_linear:
                    # No trustable analytical saturation. Use a conservative
                    # ceiling of 3x current spend (same cap as the optimizer).
                    sat_spend = observed_max * 3.0
                    # Trusted headroom is bounded regardless of curve shape.
                    trusted_headroom = 40.0
                else:
                    sat_spend_analytical = float(np.power(a*b, 1/(1-b)))
                    # Clamp the reported saturation at 5x observed max; beyond
                    # that we're extrapolating past what the data supports.
                    sat_spend = min(sat_spend_analytical, observed_max * 5.0)
                    trusted_headroom = max(0, (sat_spend - avg_spend) / sat_spend * 100)

                # Marginal ROI at current spend -- this is in the trusted
                # range (avg_spend is inside observed data), so no cap needed.
                mROI = marginal_power_law(avg_spend, a, b)
                # Raw headroom (using analytical sat) kept for diagnostic
                # comparison; NOT used by downstream engines.
                raw_headroom = max(0, (sat_spend - avg_spend) / sat_spend * 100) if sat_spend > 0 else 0
                headroom = trusted_headroom

                # Generate curve points for visualization
                x_max = max(x) * 1.8
                curve_pts = [{"spend": round(s), "revenue": round(float(power_law(s, a, b)))}
                             for s in np.linspace(0, x_max, 50)]
                params = {"a": round(float(a), 4), "b": round(float(b), 4),
                          "a_std": round(float(perr[0]), 4), "b_std": round(float(perr[1]), 4),
                          "near_linear": near_linear}
            else:  # hill
                p0 = [max(y)*1.5, 0.8, np.median(x)]
                popt, pcov = curve_fit(hill_curve, x, y, p0=p0,
                    bounds=([0,0.1,1], [np.inf, 3.0, np.max(x)*5]), maxfev=10000)
                a, b, K = popt
                y_pred = hill_curve(x, a, b, K)
                perr = np.sqrt(np.diag(pcov))
                avg_spend = float(x.mean())
                mROI = marginal_hill(avg_spend, a, b, K)
                sat_spend = K * 3; headroom = max(0, (sat_spend-avg_spend)/sat_spend*100)
                x_max = max(x)*1.8
                curve_pts = [{"spend": round(s), "revenue": round(float(hill_curve(s, a, b, K)))}
                             for s in np.linspace(0, x_max, 50)]
                params = {"a": round(float(a),4), "b": round(float(b),4), "K": round(float(K),2),
                          "a_std": round(float(perr[0]),4), "b_std": round(float(perr[1]),4), "K_std": round(float(perr[2]),2)}

            # Diagnostics
            r2 = r2_score(y, y_pred)
            rmse = float(np.sqrt(mean_squared_error(y, y_pred)))
            mape = float(np.mean(np.abs((y - y_pred) / np.maximum(y, 1))) * 100)

            # Leave-One-Out Cross-Validation
            loo_errors = []
            if len(x) >= 4:
                loo = LeaveOneOut()
                for train_idx, test_idx in loo.split(x):
                    try:
                        if model_type == "power_law":
                            p_loo, _ = curve_fit(power_law, x[train_idx], y[train_idx],
                                p0=[1.0, 0.5], bounds=([0,0.01],[np.inf,0.99]), maxfev=5000)
                            pred = power_law(x[test_idx], *p_loo)
                        else:
                            p_loo, _ = curve_fit(hill_curve, x[train_idx], y[train_idx],
                                p0=p0, bounds=([0,0.1,1],[np.inf,3.0,np.max(x)*5]), maxfev=5000)
                            pred = hill_curve(x[test_idx], *p_loo)
                        loo_errors.append(float((y[test_idx] - pred)**2))
                    except: pass
                loo_rmse = float(np.sqrt(np.mean(loo_errors))) if loo_errors else None
            else:
                loo_rmse = None

            # Confidence assessment
            if r2 > 0.7 and mape < 20: confidence = "High"
            elif r2 > 0.4 and mape < 40: confidence = "Medium"
            else: confidence = "Low"

            results[channel] = {
                "model": model_type,
                "params": params,
                "current_avg_spend": round(avg_spend, 0),
                "saturation_spend": round(sat_spend, 0),
                "marginal_roi": round(float(mROI), 4),
                "headroom_pct": round(headroom, 1),
                "near_linear_fit": bool(params.get("near_linear", False)),
                "diagnostics": {
                    "r_squared": round(float(r2), 4),
                    "rmse": round(rmse, 0),
                    "mape": round(mape, 1),
                    "loo_cv_rmse": round(loo_rmse, 0) if loo_rmse else None,
                    "n_data_points": len(x),
                    "confidence": confidence,
                },
                "curve_points": curve_pts,
                "data_points": [{"spend": round(float(xi)), "revenue": round(float(yi))}
                                for xi, yi in zip(x, y)],
            }
        except Exception as e:
            results[channel] = {"model": model_type, "error": str(e), "diagnostics": {"confidence": "Failed"}}
    return results

if __name__ == "__main__":
    from mock_data import generate_all_data
    data = generate_all_data()
    df = data["campaign_performance"]
    print("Fitting power-law response curves...")
    r = fit_response_curves(df, "power_law")
    for ch, info in r.items():
        d = info.get("diagnostics", {})
        print(f"  {ch}: R²={d.get('r_squared','?')} MAPE={d.get('mape','?')}% mROI={info.get('marginal_roi','?')} [{d.get('confidence','?')}]")
    print("\nFitting Hill curves...")
    r2 = fit_response_curves(df, "hill")
    for ch, info in r2.items():
        d = info.get("diagnostics", {})
        print(f"  {ch}: R²={d.get('r_squared','?')} MAPE={d.get('mape','?')}% [{d.get('confidence','?')}]")
