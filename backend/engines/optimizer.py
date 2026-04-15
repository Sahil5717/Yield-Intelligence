"""
Budget Optimization Engine — Production Grade
===============================================
Constrained nonlinear optimization via scipy.optimize.minimize (SLSQP).
Supports: maximize_revenue, maximize_roi, minimize_cac, balanced multi-objective.
Multi-start to escape local optima. Sensitivity analysis built in.

Libraries: scipy.optimize.minimize (SLSQP), numpy
"""
import numpy as np
from scipy.optimize import minimize
from typing import Dict, List, Optional
import logging
logger = logging.getLogger(__name__)

def _predict_revenue(spend_annual, curve):
    """Predict annual revenue from annual spend using fitted response curve."""
    monthly = spend_annual / 12
    if curve.get("model") == "hill":
        a, b, K = curve["params"]["a"], curve["params"]["b"], curve["params"]["K"]
        xb = np.power(max(monthly, 1e-6), b)
        return float(a * xb / (np.power(K, b) + xb)) * 12
    else:  # power_law
        a, b = curve["params"]["a"], curve["params"]["b"]
        return float(a * np.power(max(monthly, 1e-6), b)) * 12

def _marginal_revenue(spend_annual, curve):
    """Marginal revenue (derivative) at given spend level."""
    monthly = spend_annual / 12
    if curve.get("model") == "hill":
        a, b, K = curve["params"]["a"], curve["params"]["b"], curve["params"]["K"]
        Kb = K**b; xb = monthly**b
        return float(a * b * (monthly**(b-1)) * Kb / ((Kb + xb)**2))
    else:
        a, b = curve["params"]["a"], curve["params"]["b"]
        return float(a * b * np.power(max(monthly, 1e-6), b - 1))

def optimize_budget(
    response_curves: Dict,
    total_budget: float,
    objective: str = "balanced",
    objective_weights: Optional[Dict] = None,
    min_spend_pct: float = 0.02,
    max_spend_pct: float = 0.40,
    locked_channels: Optional[Dict] = None,
    current_allocation: Optional[Dict] = None,
    n_restarts: int = 5,
) -> Dict:
    """
    Constrained budget optimization using scipy SLSQP solver with multi-start.

    Args:
        response_curves: from response_curves engine (fitted params per channel)
        total_budget: total annual budget
        objective: maximize_revenue | maximize_roi | minimize_cac | balanced
        locked_channels: {channel: fixed_spend}
        n_restarts: number of random starting points to escape local optima
    """
    locked = locked_channels or {}
    channels = [ch for ch in response_curves if ch not in locked and "error" not in response_curves[ch]]
    n = len(channels)
    if n == 0: return {"channels":[], "summary":{"total_budget":total_budget,"current_revenue":0,"optimized_revenue":0,"revenue_uplift":0,"uplift_pct":0,"current_roi":0,"optimized_roi":0}, "optimizer_info":{"converged":False,"warning":"No optimizable channels"}}

    locked_total = sum(locked.values())
    avail = total_budget - locked_total
    if avail <= 0: return {"channels":[], "summary":{"total_budget":total_budget,"current_revenue":0,"optimized_revenue":0,"revenue_uplift":0,"uplift_pct":0,"current_roi":0,"optimized_roi":0}, "optimizer_info":{"converged":False,"warning":"Locked spend exceeds budget"}}

    if current_allocation is None:
        current_allocation = {ch: response_curves[ch].get("current_avg_spend", avail/n/12)*12 for ch in channels}
    if objective_weights is None:
        objective_weights = {"revenue": 0.4, "roi": 0.3, "leakage": 0.15, "cost": 0.15}

    # Objective function (minimize negative objective)
    def neg_objective(x):
        total_rev = sum(_predict_revenue(x[i], response_curves[channels[i]]) for i in range(n))
        total_sp = sum(x)
        if objective == "maximize_revenue":
            return -total_rev
        elif objective == "maximize_roi":
            return -(total_rev - total_sp) / max(total_sp, 1)
        elif objective == "minimize_cac":
            # Approximate conversions from revenue / avg_order_value
            return total_sp / max(total_rev / 400, 1)  # rough CAC
        else:  # balanced
            roi = (total_rev - total_sp) / max(total_sp, 1)
            return -(objective_weights.get("revenue",0.4) * total_rev / 1e6
                   + objective_weights.get("roi",0.3) * roi * 10)

    # Constraints
    bounds = [(avail * min_spend_pct, avail * max_spend_pct) for _ in range(n)]
    constraints = [{"type": "eq", "fun": lambda x: sum(x) - avail}]

    # Multi-start optimization
    best_result = None; best_obj = float("inf")
    for restart in range(n_restarts):
        if restart == 0:
            x0 = np.array([current_allocation.get(ch, avail/n) for ch in channels])
            x0 = x0 * (avail / x0.sum())  # normalize to available budget
        else:
            x0 = np.random.dirichlet(np.ones(n)) * avail
        x0 = np.clip(x0, avail*min_spend_pct, avail*max_spend_pct)
        x0 = x0 * (avail / x0.sum())

        try:
            res = minimize(neg_objective, x0, method="SLSQP", bounds=bounds,
                          constraints=constraints, options={"maxiter": 500, "ftol": 1e-10})
            if res.fun < best_obj:
                best_obj = res.fun; best_result = res
        except Exception as e:
            logger.warning(f"Restart {restart} failed: {e}")

    if best_result is None or not best_result.success:
        logger.warning(f"Optimization did not converge: {best_result}")
        # Return current allocation as-is (no change) so downstream engines don't crash
        channel_results = []
        for ch in channels:
            cur = current_allocation.get(ch, avail/n)
            cur_rev = _predict_revenue(cur, response_curves[ch])
            mROI = _marginal_revenue(cur, response_curves[ch])
            channel_results.append({
                "channel": ch, "current_spend": round(cur, 0), "optimized_spend": round(cur, 0),
                "change_pct": 0, "current_revenue": round(cur_rev, 0), "optimized_revenue": round(cur_rev, 0),
                "revenue_delta": 0, "current_roi": round((cur_rev-cur)/max(cur,1), 3),
                "optimized_roi": round((cur_rev-cur)/max(cur,1), 3), "marginal_roi": round(mROI, 4), "locked": False,
            })
        for ch, sp in locked.items():
            if ch in response_curves and "error" not in response_curves[ch]:
                rev = _predict_revenue(sp, response_curves[ch])
                channel_results.append({"channel":ch,"current_spend":round(sp,0),"optimized_spend":round(sp,0),
                    "change_pct":0,"current_revenue":round(rev,0),"optimized_revenue":round(rev,0),
                    "revenue_delta":0,"current_roi":round((rev-sp)/max(sp,1),3),
                    "optimized_roi":round((rev-sp)/max(sp,1),3),"marginal_roi":0,"locked":True})
        total_rev = sum(c["current_revenue"] for c in channel_results)
        return {"channels": channel_results, "summary": {
            "total_budget": total_budget, "current_revenue": total_rev, "optimized_revenue": total_rev,
            "revenue_uplift": 0, "uplift_pct": 0, "current_roi": round((total_rev-total_budget)/max(total_budget,1),3),
            "optimized_roi": round((total_rev-total_budget)/max(total_budget,1),3),
        }, "optimizer_info": {"converged": False, "warning": "SLSQP did not converge. Showing current allocation."}}

    opt_spend = best_result.x

    # Build results
    channel_results = []
    for i, ch in enumerate(channels):
        cur = current_allocation.get(ch, avail/n)
        opt = float(opt_spend[i])
        opt_rev = _predict_revenue(opt, response_curves[ch])
        cur_rev = _predict_revenue(cur, response_curves[ch])
        mROI = _marginal_revenue(opt, response_curves[ch])
        channel_results.append({
            "channel": ch, "current_spend": round(cur, 0), "optimized_spend": round(opt, 0),
            "change_pct": round((opt-cur)/max(cur,1)*100, 1),
            "current_revenue": round(cur_rev, 0), "optimized_revenue": round(opt_rev, 0),
            "revenue_delta": round(opt_rev - cur_rev, 0),
            "current_roi": round((cur_rev-cur)/max(cur,1), 3),
            "optimized_roi": round((opt_rev-opt)/max(opt,1), 3),
            "marginal_roi": round(mROI, 4), "locked": False,
        })
    # Add locked channels
    for ch, sp in locked.items():
        if ch in response_curves and "error" not in response_curves[ch]:
            rev = _predict_revenue(sp, response_curves[ch])
            channel_results.append({"channel":ch,"current_spend":round(sp,0),"optimized_spend":round(sp,0),
                "change_pct":0,"current_revenue":round(rev,0),"optimized_revenue":round(rev,0),
                "revenue_delta":0,"current_roi":round((rev-sp)/max(sp,1),3),
                "optimized_roi":round((rev-sp)/max(sp,1),3),"marginal_roi":0,"locked":True})

    total_cur_rev = sum(c["current_revenue"] for c in channel_results)
    total_opt_rev = sum(c["optimized_revenue"] for c in channel_results)

    # ═══ GUARDRAILS ═══
    warnings = []
    
    # Guard 1: If optimized is worse than current, fall back to current allocation
    if total_opt_rev < total_cur_rev * 0.95:
        warnings.append("Optimizer found no improvement over current allocation. Returning current plan with analysis.")
        # Reset to current allocation
        for c in channel_results:
            if not c.get("locked"):
                c["optimized_spend"] = c["current_spend"]
                c["optimized_revenue"] = c["current_revenue"]
                c["change_pct"] = 0
                c["revenue_delta"] = 0
                c["optimized_roi"] = c["current_roi"]
        total_opt_rev = total_cur_rev
    
    # Guard 2: Cap extreme individual channel swings
    for c in channel_results:
        if c.get("locked"): continue
        if c["change_pct"] > 200:
            warnings.append(f"{c['channel']}: capped from +{c['change_pct']:.0f}% to +200%")
            c["change_pct"] = 200
        if c["change_pct"] < -80:
            warnings.append(f"{c['channel']}: capped from {c['change_pct']:.0f}% to -80%")
            c["change_pct"] = -80
    
    # Guard 3: Ensure all spends positive
    for c in channel_results:
        c["optimized_spend"] = max(0, c["optimized_spend"])
        c["current_spend"] = max(0, c["current_spend"])

    return {
        "channels": channel_results,
        "summary": {
            "total_budget": round(total_budget, 0),
            "current_revenue": round(total_cur_rev, 0),
            "optimized_revenue": round(total_opt_rev, 0),
            "revenue_uplift": round(total_opt_rev - total_cur_rev, 0),
            "uplift_pct": round((total_opt_rev-total_cur_rev)/max(total_cur_rev,1)*100, 2),
            "current_roi": round((total_cur_rev-total_budget)/max(total_budget,1), 3),
            "optimized_roi": round((total_opt_rev-total_budget)/max(total_budget,1), 3),
        },
        "optimizer_info": {
            "method": "scipy_SLSQP",
            "objective": objective,
            "n_restarts": n_restarts,
            "converged": best_result.success,
            "n_channels_optimized": n,
            "n_channels_locked": len(locked),
            "warnings": warnings,
        },
    }

def sensitivity_analysis(response_curves, base_budget, objective="balanced", steps=None):
    """Run optimizer at multiple budget levels to show sensitivity."""
    if steps is None: steps = [-30, -20, -10, 0, 10, 20, 30, 50]
    results = []
    for pct in steps:
        budget = base_budget * (1 + pct/100)
        opt = optimize_budget(response_curves, budget, objective)
        if "error" not in opt:
            results.append({"budget_change_pct": pct, "budget": round(budget,0),
                "revenue": opt["summary"]["optimized_revenue"],
                "roi": opt["summary"]["optimized_roi"],
                "uplift": opt["summary"]["revenue_uplift"]})
    return results
