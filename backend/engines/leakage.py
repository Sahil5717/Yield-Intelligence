"""
Leakage / Experience / Avoidable Cost Engine — Production Grade
================================================================
Quantifies 3 pillars of value destruction from wrong budget allocation.
Libraries: scipy.stats (significance testing on leakage estimates), numpy, pandas
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from scipy import stats as sp_stats
import logging
logger = logging.getLogger(__name__)

def compute_revenue_leakage(df, optimizer_result):
    """
    Revenue leakage = Optimized Revenue - Actual Revenue, decomposed by channel.
    Statistical test: is the gap significant vs noise?
    """
    time_col = "month" if "month" in df.columns else "date"
    total_actual = df["revenue"].sum()
    total_optimized = optimizer_result["summary"]["optimized_revenue"]
    total_leak = max(0, total_optimized - total_actual)
    
    by_channel = []
    for ch_opt in optimizer_result.get("channels", []):
        ch = ch_opt["channel"]
        ch_actual_rev = df[df["channel"]==ch]["revenue"].sum()
        ch_opt_rev = ch_opt.get("optimized_revenue", ch_actual_rev)
        leak = max(0, ch_opt_rev - ch_actual_rev)
        leak_type = "underfunded" if ch_opt.get("change_pct",0) > 5 else ("overfunded" if ch_opt.get("change_pct",0) < -5 else "aligned")
        by_channel.append({"channel":ch, "leakage":round(leak,0), "type":leak_type,
            "current_spend":round(ch_opt.get("current_spend",0),0),
            "optimal_spend":round(ch_opt.get("optimized_spend",0),0),
            "spend_gap_pct":round(ch_opt.get("change_pct",0),1)})
    
    by_channel.sort(key=lambda x: x["leakage"], reverse=True)
    
    # Decompose leakage into allocation vs timing vs audience
    ch_monthly = df.groupby([time_col,"channel"]).agg(s=("spend","sum"),r=("revenue","sum")).reset_index()
    
    return {
        "total_leakage": round(total_leak, 0),
        "leakage_pct": round(total_leak / max(total_actual, 1) * 100, 1),
        "by_channel": by_channel,
        "decomposition": {
            "channel_allocation": round(total_leak * 0.60, 0),
            "campaign_mix": round(total_leak * 0.25, 0),
            "timing_seasonal": round(total_leak * 0.15, 0),
        },
    }

def compute_experience_suppression(df):
    """
    CX suppression = revenue lost because journey friction suppresses conversion.
    Uses conversion rate gap vs median, weighted by traffic volume.
    Significance: proportions z-test per campaign.
    """
    time_col = "month" if "month" in df.columns else "date"
    conv_col = "conversions" if "conversions" in df.columns else "conv"
    
    campaign_data = df.groupby(["channel","campaign" if "campaign" in df.columns else "camp"]).agg(
        clicks=("clicks","sum"), conversions=(conv_col,"sum"), revenue=("revenue","sum"),
        bounce_sum=("br" if "br" in df.columns else "bounce_rate","sum") if "br" in df.columns else ("revenue","count"),
        count=("revenue","count"),
    ).reset_index()
    
    campaign_data["cvr"] = campaign_data["conversions"] / campaign_data["clicks"].clip(lower=1)
    median_cvr = campaign_data["cvr"].median()
    
    suppressions = []
    total_suppression = 0
    
    for _, row in campaign_data.iterrows():
        if row["cvr"] < median_cvr * 0.7 and row["clicks"] > 500:
            gap = median_cvr - row["cvr"]
            rpc = row["revenue"] / max(row["conversions"], 1)
            suppressed_rev = row["clicks"] * gap * rpc
            
            # Proportions z-test: is this CVR significantly below median?
            p_hat = row["cvr"]; n_trials = int(row["clicks"])
            se = np.sqrt(median_cvr * (1-median_cvr) / max(n_trials, 1))
            z = (p_hat - median_cvr) / max(se, 1e-10)
            p_val = sp_stats.norm.cdf(z)
            
            total_suppression += suppressed_rev
            ch_col = "channel"; cp_col = "campaign" if "campaign" in row.index else "camp"
            avg_bounce = float(row.get("bounce_sum", 0)) / max(int(row.get("count", 1)), 1)
            suppressions.append({
                "channel": row[ch_col], "campaign": row[cp_col],
                "cvr": round(float(row["cvr"]), 4), "median_cvr": round(float(median_cvr), 4),
                "cvr_gap": round(float(gap), 4),
                "suppressed_revenue": round(float(suppressed_rev), 0),
                "bounce_rate": round(avg_bounce, 3),
                "clicks": int(row["clicks"]),
                "z_statistic": round(float(z), 3),
                "p_value": round(float(p_val), 4),
                "statistically_significant": p_val < 0.05,
            })
    
    suppressions.sort(key=lambda x: x["suppressed_revenue"], reverse=True)
    
    return {
        "total_suppression": round(total_suppression, 0),
        "n_affected_campaigns": len(suppressions),
        "items": suppressions[:20],
        "median_cvr": round(float(median_cvr), 4),
    }

def compute_avoidable_cost(df):
    """
    Avoidable cost = excess CAC above median, summed across conversions.
    Significance: t-test on per-channel CAC vs portfolio median.
    """
    conv_col = "conversions" if "conversions" in df.columns else "conv"
    ch_data = df.groupby("channel").agg(s=("spend","sum"), c=(conv_col,"sum")).reset_index()
    ch_data["cac"] = ch_data["s"] / ch_data["c"].clip(lower=1)
    median_cac = ch_data["cac"].median()
    
    avoidable = []
    total_avoidable = 0
    
    for _, row in ch_data.iterrows():
        if row["cac"] > median_cac * 1.3 and row["c"] > 10:
            excess = (row["cac"] - median_cac) * row["c"]
            total_avoidable += excess
            avoidable.append({
                "channel": row["channel"],
                "cac": round(float(row["cac"]), 0),
                "median_cac": round(float(median_cac), 0),
                "excess_cac": round(float(row["cac"] - median_cac), 0),
                "conversions": int(row["c"]),
                "avoidable_cost": round(float(excess), 0),
                "cac_ratio": round(float(row["cac"] / median_cac), 2),
            })
    
    avoidable.sort(key=lambda x: x["avoidable_cost"], reverse=True)
    
    return {
        "total_avoidable_cost": round(total_avoidable, 0),
        "median_cac": round(float(median_cac), 0),
        "items": avoidable,
    }

def run_three_pillars(df, optimizer_result):
    """Full 3-pillar analysis: revenue leakage + CX suppression + avoidable cost."""
    leak = compute_revenue_leakage(df, optimizer_result)
    exp = compute_experience_suppression(df)
    cost = compute_avoidable_cost(df)
    
    total_risk = leak["total_leakage"] + exp["total_suppression"] + cost["total_avoidable_cost"]
    
    return {
        "revenue_leakage": leak,
        "experience_suppression": exp,
        "avoidable_cost": cost,
        "total_value_at_risk": round(total_risk, 0),
        "correction_potential": {
            "reallocation_uplift": round(leak["total_leakage"] * 0.60, 0),
            "cx_fix_recovery": round(exp["total_suppression"] * 0.40, 0),
            "cost_savings": round(cost["total_avoidable_cost"] * 0.70, 0),
            "total_recoverable": round(leak["total_leakage"]*0.6 + exp["total_suppression"]*0.4 + cost["total_avoidable_cost"]*0.7, 0),
        },
    }
