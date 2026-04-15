"""
Mock Data Generator for Marketing ROI & Budget Optimization Engine
Generates realistic multi-channel marketing data including:
- Campaign-level performance (spend, impressions, clicks, leads, conversions, revenue)
- User-level journey data (touchpoints per conversion for attribution)
- CX signals (bounce rate, session depth, NPS, unsubscribe rate)
- Monthly granularity across 12 months, 8 channels, ~30 campaigns
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json

np.random.seed(42)

# --- Channel & Campaign Definitions ---

CHANNELS = {
    "paid_search": {"type": "online", "base_cpc": 2.5, "base_cvr": 0.035, "saturation_point": 150000},
    "organic_search": {"type": "online", "base_cpc": 0, "base_cvr": 0.042, "saturation_point": None},
    "social_paid": {"type": "online", "base_cpc": 1.8, "base_cvr": 0.018, "saturation_point": 120000},
    "display": {"type": "online", "base_cpc": 0.9, "base_cvr": 0.008, "saturation_point": 80000},
    "email": {"type": "online", "base_cpc": 0.15, "base_cvr": 0.055, "saturation_point": 40000},
    "video_youtube": {"type": "online", "base_cpc": 3.2, "base_cvr": 0.012, "saturation_point": 100000},
    "events": {"type": "offline", "base_cpc": 45, "base_cvr": 0.08, "saturation_point": 200000},
    "direct_mail": {"type": "offline", "base_cpc": 5.5, "base_cvr": 0.025, "saturation_point": 60000},
}

CAMPAIGNS_PER_CHANNEL = {
    "paid_search": ["PS_Brand", "PS_Generic", "PS_Competitor", "PS_Product"],
    "organic_search": ["SEO_Blog", "SEO_Product_Pages"],
    "social_paid": ["Social_Meta_Awareness", "Social_Meta_Retargeting", "Social_LinkedIn_LeadGen", "Social_TikTok_Brand"],
    "display": ["Display_Programmatic", "Display_Retargeting", "Display_Native"],
    "email": ["Email_Newsletter", "Email_Nurture", "Email_Promo", "Email_Winback"],
    "video_youtube": ["YT_PreRoll", "YT_Discovery", "YT_Shorts"],
    "events": ["Events_TradeShow", "Events_Webinar", "Events_Conference"],
    "direct_mail": ["DM_Catalog", "DM_PostCard"],
}

REGIONS = ["North", "South", "East", "West"]
PRODUCTS = ["Product_A", "Product_B", "Product_C"]

MONTHS = pd.date_range("2022-01-01", periods=48, freq="MS")  # 4 years for model training

# Seasonality multipliers (index 0 = Jan)
SEASONALITY = [0.85, 0.80, 0.95, 1.05, 1.10, 1.00, 0.90, 0.88, 1.05, 1.15, 1.25, 1.30]


def _diminishing_returns(spend: float, saturation: float, alpha: float = 0.6) -> float:
    """Power-law diminishing returns: response = spend^alpha, scaled by saturation."""
    if saturation is None or saturation == 0:
        return spend
    normalized = spend / saturation
    return saturation * (normalized ** alpha)


def _add_noise(value: float, noise_pct: float = 0.1) -> float:
    return max(0, value * (1 + np.random.normal(0, noise_pct)))


def generate_campaign_performance() -> pd.DataFrame:
    """Generate monthly campaign-level performance data."""
    rows = []
    
    for month_idx, month in enumerate(MONTHS):
        season = SEASONALITY[month_idx % 12]  # Repeat yearly pattern
        
        for channel_name, channel_props in CHANNELS.items():
            campaigns = CAMPAIGNS_PER_CHANNEL[channel_name]
            
            for campaign in campaigns:
                for region in REGIONS:
                    # Base monthly spend varies by channel and campaign
                    base_spend = _get_base_spend(channel_name, campaign)
                    # Apply seasonality and regional variation
                    regional_mult = {"North": 1.1, "South": 0.9, "East": 1.0, "West": 1.05}[region]
                    monthly_spend = _add_noise(base_spend * season * regional_mult, 0.12)
                    
                    if channel_name == "organic_search":
                        monthly_spend = _add_noise(2000 * regional_mult, 0.05)  # minimal SEO cost
                    
                    # Apply diminishing returns to get effective output
                    effective_output = _diminishing_returns(
                        monthly_spend, channel_props["saturation_point"]
                    )
                    
                    # Calculate funnel metrics
                    impressions = _add_noise(effective_output * _get_impression_mult(channel_name), 0.15)
                    clicks = _add_noise(impressions * _get_ctr(channel_name, campaign), 0.12)
                    leads = _add_noise(clicks * _get_lead_rate(channel_name), 0.15)
                    mqls = _add_noise(leads * np.random.uniform(0.3, 0.6), 0.1)
                    sqls = _add_noise(mqls * np.random.uniform(0.25, 0.5), 0.1)
                    conversions = _add_noise(sqls * channel_props["base_cvr"] * season * 10, 0.18)
                    
                    # Revenue per conversion varies by product mix
                    avg_order_value = _add_noise(_get_aov(channel_name), 0.1)
                    revenue = conversions * avg_order_value
                    
                    # CX signals
                    bounce_rate = _get_bounce_rate(channel_name, campaign)
                    avg_session_duration = _add_noise(_get_session_duration(channel_name), 0.2)
                    form_completion_rate = _add_noise(_get_form_rate(channel_name, campaign), 0.1)
                    unsubscribe_rate = _get_unsub_rate(channel_name) if channel_name == "email" else 0
                    nps = _add_noise(_get_nps(channel_name), 0.05)
                    
                    # Confidence tier
                    confidence = "High" if channel_props["type"] == "online" else "Medium"
                    if channel_name in ("events", "direct_mail"):
                        confidence = "Model-Estimated"
                    
                    rows.append({
                        "date": month,
                        "month": month.strftime("%Y-%m"),
                        "channel": channel_name,
                        "channel_type": channel_props["type"],
                        "campaign": campaign,
                        "region": region,
                        "product": np.random.choice(PRODUCTS, p=[0.45, 0.35, 0.20]),
                        "spend": round(monthly_spend, 2),
                        "impressions": int(max(0, impressions)),
                        "clicks": int(max(0, clicks)),
                        "leads": int(max(0, leads)),
                        "mqls": int(max(0, mqls)),
                        "sqls": int(max(0, sqls)),
                        "conversions": int(max(0, conversions)),
                        "revenue": round(max(0, revenue), 2),
                        "bounce_rate": round(min(1, max(0, bounce_rate)), 3),
                        "avg_session_duration_sec": round(max(0, avg_session_duration), 1),
                        "form_completion_rate": round(min(1, max(0, form_completion_rate)), 3),
                        "unsubscribe_rate": round(min(0.1, max(0, unsubscribe_rate)), 4),
                        "nps_score": round(min(100, max(-100, nps)), 1),
                        "confidence_tier": confidence,
                    })
    
    return pd.DataFrame(rows)


def generate_user_journeys(campaign_df: pd.DataFrame, n_journeys: int = 5000) -> pd.DataFrame:
    """
    Generate user-level journey data for attribution modeling.
    Each journey has 1-7 touchpoints across channels before conversion.
    """
    # Weight channels by their share of conversions
    channel_conv = campaign_df.groupby("channel")["conversions"].sum()
    channel_weights = (channel_conv / channel_conv.sum()).to_dict()
    channels = list(channel_weights.keys())
    weights = [channel_weights[c] for c in channels]
    
    journeys = []
    
    for journey_id in range(n_journeys):
        # Number of touchpoints: weighted toward 2-4
        n_touchpoints = np.random.choice([1, 2, 3, 4, 5, 6, 7], p=[0.1, 0.25, 0.3, 0.2, 0.08, 0.05, 0.02])
        
        # Pick channels for each touchpoint (with some sequential logic)
        journey_channels = []
        for tp in range(n_touchpoints):
            if tp == 0:
                # First touch biased toward awareness channels
                awareness_weights = _adjust_weights_for_stage(weights, channels, "awareness")
                ch = np.random.choice(channels, p=awareness_weights)
            elif tp == n_touchpoints - 1:
                # Last touch biased toward conversion channels
                conv_weights = _adjust_weights_for_stage(weights, channels, "conversion")
                ch = np.random.choice(channels, p=conv_weights)
            else:
                ch = np.random.choice(channels, p=weights)
            journey_channels.append(ch)
        
        # Assign campaigns from each channel
        base_date = pd.Timestamp(np.random.choice(MONTHS))
        converted = np.random.random() < 0.35  # 35% conversion rate for journeys
        revenue = _add_noise(np.random.choice([500, 1200, 2500, 5000]), 0.3) if converted else 0
        
        for tp_idx, ch in enumerate(journey_channels):
            campaigns = CAMPAIGNS_PER_CHANNEL[ch]
            campaign = np.random.choice(campaigns)
            
            tp_date = base_date + timedelta(days=int(tp_idx) * int(np.random.randint(1, 14)))
            
            journeys.append({
                "journey_id": f"J{journey_id:05d}",
                "touchpoint_order": tp_idx + 1,
                "total_touchpoints": n_touchpoints,
                "date": tp_date,
                "channel": ch,
                "campaign": campaign,
                "converted": converted,
                "conversion_revenue": round(revenue, 2) if tp_idx == n_touchpoints - 1 and converted else 0,
            })
    
    return pd.DataFrame(journeys)


# --- Helper functions ---

def _get_base_spend(channel: str, campaign: str) -> float:
    base_spends = {
        "paid_search": 35000, "social_paid": 28000, "display": 18000,
        "email": 5000, "video_youtube": 22000, "events": 45000, "direct_mail": 15000,
        "organic_search": 2000,
    }
    # Vary by campaign within channel
    campaign_mult = 0.6 + hash(campaign) % 100 / 100 * 0.8
    return base_spends.get(channel, 10000) * campaign_mult


def _get_impression_mult(channel: str) -> float:
    return {"paid_search": 8, "organic_search": 12, "social_paid": 15,
            "display": 25, "email": 3, "video_youtube": 10,
            "events": 0.5, "direct_mail": 0.8}.get(channel, 5)


def _get_ctr(channel: str, campaign: str) -> float:
    base = {"paid_search": 0.045, "organic_search": 0.035, "social_paid": 0.012,
            "display": 0.004, "email": 0.22, "video_youtube": 0.008,
            "events": 0.5, "direct_mail": 0.15}.get(channel, 0.02)
    return _add_noise(base, 0.15)


def _get_lead_rate(channel: str) -> float:
    return {"paid_search": 0.08, "organic_search": 0.06, "social_paid": 0.05,
            "display": 0.02, "email": 0.12, "video_youtube": 0.03,
            "events": 0.35, "direct_mail": 0.08}.get(channel, 0.05)


def _get_aov(channel: str) -> float:
    return {"paid_search": 1800, "organic_search": 2200, "social_paid": 1200,
            "display": 900, "email": 1500, "video_youtube": 1100,
            "events": 5500, "direct_mail": 2000}.get(channel, 1500)


def _get_bounce_rate(channel: str, campaign: str) -> float:
    base = {"paid_search": 0.38, "organic_search": 0.42, "social_paid": 0.55,
            "display": 0.65, "email": 0.30, "video_youtube": 0.50,
            "events": 0.15, "direct_mail": 0.45}.get(channel, 0.45)
    # Some campaigns have deliberately bad landing pages (for diagnostics)
    if "Retargeting" in campaign:
        base *= 0.75  # retargeting bounces less
    if "Awareness" in campaign or "Brand" in campaign:
        base *= 1.15  # awareness traffic bounces more
    return _add_noise(base, 0.1)


def _get_session_duration(channel: str) -> float:
    return {"paid_search": 145, "organic_search": 195, "social_paid": 85,
            "display": 55, "email": 165, "video_youtube": 70,
            "events": 300, "direct_mail": 120}.get(channel, 100)


def _get_form_rate(channel: str, campaign: str) -> float:
    base = {"paid_search": 0.12, "organic_search": 0.09, "social_paid": 0.06,
            "display": 0.025, "email": 0.18, "video_youtube": 0.04,
            "events": 0.45, "direct_mail": 0.10}.get(channel, 0.08)
    # Deliberately create good-engagement-poor-conversion signals for some
    if campaign in ("Social_TikTok_Brand", "Display_Native"):
        base *= 0.4  # high CTR but poor form completion
    return base


def _get_unsub_rate(channel: str) -> float:
    return _add_noise(0.004, 0.3)


def _get_nps(channel: str) -> float:
    return {"paid_search": 35, "organic_search": 52, "social_paid": 28,
            "display": 18, "email": 42, "video_youtube": 30,
            "events": 65, "direct_mail": 25}.get(channel, 30)


def _adjust_weights_for_stage(weights, channels, stage):
    """Adjust channel weights based on funnel stage."""
    adjusted = np.array(weights, dtype=float)
    for i, ch in enumerate(channels):
        if stage == "awareness":
            if ch in ("display", "social_paid", "video_youtube"):
                adjusted[i] *= 2.0
            elif ch in ("email", "direct_mail"):
                adjusted[i] *= 0.4
        elif stage == "conversion":
            if ch in ("paid_search", "email", "organic_search"):
                adjusted[i] *= 2.5
            elif ch in ("display", "video_youtube"):
                adjusted[i] *= 0.5
    adjusted = adjusted / adjusted.sum()
    return adjusted


def generate_all_data() -> Dict[str, pd.DataFrame]:
    """Generate all mock datasets and return as dict of DataFrames."""
    print("Generating campaign performance data...")
    campaign_df = generate_campaign_performance()
    
    print("Generating user journey data...")
    journey_df = generate_user_journeys(campaign_df)
    
    print(f"Campaign data: {len(campaign_df)} rows")
    print(f"Journey data: {len(journey_df)} rows")
    print(f"Channels: {campaign_df['channel'].nunique()}")
    print(f"Campaigns: {campaign_df['campaign'].nunique()}")
    print(f"Date range: {campaign_df['date'].min()} to {campaign_df['date'].max()}")
    print(f"Total spend: ${campaign_df['spend'].sum():,.0f}")
    print(f"Total revenue: ${campaign_df['revenue'].sum():,.0f}")
    print(f"Overall ROI: {(campaign_df['revenue'].sum() - campaign_df['spend'].sum()) / campaign_df['spend'].sum():.2f}x")
    
    return {
        "campaign_performance": campaign_df,
        "user_journeys": journey_df,
    }


def export_to_csv(data: Dict[str, pd.DataFrame], output_dir: str = "./data"):
    """Export all datasets to CSV files."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    for name, df in data.items():
        path = os.path.join(output_dir, f"{name}.csv")
        df.to_csv(path, index=False)
        print(f"Exported {name} to {path} ({len(df)} rows)")


if __name__ == "__main__":
    data = generate_all_data()
    export_to_csv(data)
