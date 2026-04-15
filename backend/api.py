"""
FastAPI Backend — Marketing ROI & Budget Optimization Engine
All imports updated to match upgraded engine function names.
Run: uvicorn api:app --reload --port 8000
"""
import os, sys, json, tempfile
from typing import Optional, Dict
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

# Auth & persistence
from auth import register_user, login_user, get_current_user, require_role, check_permission
from persistence import init_db, save_session, load_session, save_scenario, list_scenarios, load_scenario, compare_scenarios

# ═══ CORRECTED IMPORTS — matching upgraded engine function names ═══
from mock_data import generate_all_data, export_to_csv
from validator import validate_data
from engines.attribution import run_all_attribution, compute_attribution_roi
from engines.response_curves import fit_response_curves                       # ✅ unchanged
from engines.optimizer import optimize_budget, sensitivity_analysis            # ✅ unchanged
from engines.diagnostics import generate_recommendations                      # ✅ was: run_diagnostics
from engines.leakage import run_three_pillars                                 # ✅ was: calculate_all_pillars
from engines.trend_analysis import run_trend_analysis                         # ✅ was: run_full_trend_analysis
from engines.funnel_analysis import run_funnel_analysis                       # ✅ was: run_full_funnel_analysis
from engines.roi_formulas import compute_all_roi                              # ✅ was: run_full_roi_analysis
from engines.adstock import compute_channel_adstock                           # ✅ unchanged
from engines.mmm import run_mmm                                              # ✅ unchanged
from engines.markov_attribution import run_markov_attribution                 # ✅ was: markov_attribution
from engines.forecasting import run_forecast                                  # ✅ was: run_full_forecast
from engines.cross_channel import run_cross_channel_analysis                  # ✅ unchanged
from engines.shapley import compute_shapley_values                            # ✅ was: run_shapley
from engines.multi_objective import pareto_optimize                           # ✅ was: multi_objective_optimize
from engines.geo_lift import run_geo_lift                                     # ✅ was: design_geo_test
from engines.hierarchical_forecast import run_hierarchical_forecast           # ✅ was: hierarchical_forecast
from engines.automated_recs import automated_recommendations, check_model_drift, track_realization

app = FastAPI(title="Marketing ROI & Budget Optimization Engine", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

from engines.data_splitter import split_data, validate_split
from engines.insights import generate_insights, compute_qoq_yoy_trends, generate_smart_recommendations
from engines.external_data import process_competitive_data, process_market_events, process_market_trends, merge_external_recommendations

# In-memory state
_state: Dict = {
    "campaign_data": None, "journey_data": None, "validation": None,
    "curves": None, "attribution": None, "attribution_roi": None,
    "optimization": None, "diagnostics": None, "pillars": None,
    "trend_analysis": None, "funnel_analysis": None, "roi_analysis": None,
    "data_split": None,  # reporting vs training split metadata
    "reporting_data": None,  # last 12 months for ROI/KPIs
    "training_data": None,   # full history for models
    "insights": None, "smart_recs": None,
    "qoq_yoy": None, "channel_trends": None,
    "model_selections": {
        "attribution": "markov", "response_curves": "auto",
        "mmm": "auto", "forecasting": "prophet", "optimizer": "slsqp",
    },
    "external_competitive": None, "external_events": None, "external_trends": None,
    "competitive_result": None, "events_result": None, "trends_result": None,
}

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, (np.bool_,)): return bool(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        if isinstance(obj, pd.Timestamp): return obj.isoformat()
        if isinstance(obj, (bool,)): return bool(obj)
        return super().default(obj)

def _j(obj):
    """Safely serialize numpy/pandas objects to JSON."""
    return json.loads(json.dumps(obj, cls=NumpyEncoder))


def _ensure_analysis():
    """Lazy execution: auto-run analysis if data is loaded but engines haven't run."""
    if _state["campaign_data"] is not None and _state["curves"] is None:
        _run_all_engines()


def _get_data_warnings():
    """Return warnings about data quality and sufficiency."""
    warnings = []
    df = _state.get("reporting_data")
    if df is None: df = _state.get("campaign_data")
    if df is None: return ["No data loaded"]
    n_rows = len(df)
    n_channels = df["channel"].nunique() if "channel" in df.columns else 0
    n_months = df["month"].nunique() if "month" in df.columns else 0
    if n_rows < 50: warnings.append(f"Only {n_rows} rows — results may be statistically weak. Upload more data for reliable outputs.")
    if n_channels < 3: warnings.append(f"Only {n_channels} channels — optimizer needs 3+ channels for meaningful reallocation.")
    if n_months < 6: warnings.append(f"Only {n_months} months of reporting data — KPIs may not represent full seasonal cycle.")
    training = _state.get("training_data")
    if training is not None:
        t_months = training["month"].nunique() if "month" in training.columns else 0
        if t_months < 24: warnings.append(f"Only {t_months} months of training data — response curves and forecasts have wide uncertainty.")
        if t_months < 36: warnings.append(f"Only {t_months} months for MMM — Bayesian model needs 36+ months for convergent posteriors.")
    return warnings


# ═══════════════════════════════════════════════
#  CORE ENDPOINTS
# ═══════════════════════════════════════════════

@app.get("/")
def root():
    return {"status": "ok", "engine": "Marketing ROI & Budget Optimization Engine v2.0",
            "engines_loaded": True, "api_version": "2.0"}


@app.get("/api/health")
def health_check():
    """Health endpoint for deployment monitoring."""
    data_loaded = _state["campaign_data"] is not None
    engines_run = _state["curves"] is not None
    return {
        "status": "healthy" if data_loaded and engines_run else "ready" if not data_loaded else "data_loaded",
        "data_loaded": data_loaded,
        "engines_run": engines_run,
        "reporting_rows": len(_state["reporting_data"]) if _state.get("reporting_data") is not None else 0,
        "training_rows": len(_state["training_data"]) if _state.get("training_data") is not None else 0,
        "engines_available": {
            "curves": _state["curves"] is not None and len(_state["curves"]) > 0,
            "optimization": _state["optimization"] is not None,
            "diagnostics": _state["diagnostics"] is not None and len(_state["diagnostics"]) > 0,
            "pillars": _state["pillars"] is not None,
            "attribution": _state["attribution"] is not None,
        },
    }


@app.post("/api/load-mock-data")
def load_mock_data():
    """Load demo data and run all engines automatically."""
    data = generate_all_data()
    _state["campaign_data"] = data["campaign_performance"]
    _state["journey_data"] = data["user_journeys"]
    _state["validation"] = validate_data(_state["campaign_data"])
    
    # Auto-run all engines so subsequent calls work
    _run_all_engines()
    
    return _j({
        "status": "ok",
        "rows": len(_state["campaign_data"]),
        "journey_rows": len(_state["journey_data"]),
        "channels": int(_state["campaign_data"]["channel"].nunique()),
        "campaigns": int(_state["campaign_data"]["campaign"].nunique()),
        "total_spend": float(_state["campaign_data"]["spend"].sum()),
        "total_revenue": float(_state["campaign_data"]["revenue"].sum()),
        "engines_run": True,
    })


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read(); tmp.write(content); tmp_path = tmp.name
    try:
        if suffix == ".csv": df = pd.read_csv(tmp_path)
        elif suffix in (".xlsx", ".xls"): df = pd.read_excel(tmp_path)
        else: raise HTTPException(400, f"Unsupported: {suffix}")
        _state["campaign_data"] = df
        _state["validation"] = validate_data(df)
        return _j({"filename": file.filename, "rows": len(df), "columns": list(df.columns),
                    "validation": _state["validation"]})
    finally:
        os.unlink(tmp_path)


@app.post("/api/upload-journeys")
async def upload_journey_file(file: UploadFile = File(...)):
    """Upload user journey CSV/XLSX for multi-touch attribution."""
    suffix = Path(file.filename).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read(); tmp.write(content); tmp_path = tmp.name
    try:
        if suffix == ".csv": df = pd.read_csv(tmp_path)
        elif suffix in (".xlsx", ".xls"): df = pd.read_excel(tmp_path)
        else: raise HTTPException(400, f"Unsupported: {suffix}")
        _state["journey_data"] = df
        return _j({"filename": file.filename, "rows": len(df), "columns": list(df.columns),
                    "status": "Journey data loaded. Re-run /api/run-analysis to include in attribution."})
    finally:
        os.unlink(tmp_path)


@app.post("/api/upload-competitive")
async def upload_competitive(file: UploadFile = File(...)):
    """Upload competitive intelligence CSV (SEMrush/SimilarWeb export)."""
    suffix = Path(file.filename).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read(); tmp.write(content); tmp_path = tmp.name
    try:
        df = pd.read_csv(tmp_path) if suffix == ".csv" else pd.read_excel(tmp_path)
        required = {"date", "competitor", "channel", "estimated_spend"}
        missing = required - set(df.columns)
        if missing: raise HTTPException(400, f"Missing columns: {missing}. Required: {required}")
        _state["external_competitive"] = df
        # Process immediately if campaign data exists
        if _state["campaign_data"] is not None:
            reporting_df = _state["reporting_data"] if _state.get("reporting_data") is not None else _state["campaign_data"]
            _state["competitive_result"] = process_competitive_data(df, reporting_df)
            # Merge into smart recs
            if _state.get("smart_recs"):
                _state["smart_recs"] = merge_external_recommendations(
                    _state["smart_recs"], comp_result=_state["competitive_result"])
            return _j({"filename": file.filename, "rows": len(df), "competitors": int(df["competitor"].nunique()),
                        "channels": int(df["channel"].nunique()), "recommendations": len(_state["competitive_result"].get("recommendations",[])),
                        "status": "Competitive data loaded and processed"})
        return _j({"filename": file.filename, "rows": len(df), "status": "Competitive data loaded. Load campaign data first to process."})
    finally:
        os.unlink(tmp_path)

@app.post("/api/upload-events")
async def upload_events(file: UploadFile = File(...)):
    """Upload market events CSV (seasonal calendar, competitor actions, market shifts)."""
    suffix = Path(file.filename).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read(); tmp.write(content); tmp_path = tmp.name
    try:
        df = pd.read_csv(tmp_path) if suffix == ".csv" else pd.read_excel(tmp_path)
        required = {"event_date", "event_type", "event_name", "impact_direction"}
        missing = required - set(df.columns)
        if missing: raise HTTPException(400, f"Missing columns: {missing}. Required: {required}")
        _state["external_events"] = df
        if _state["campaign_data"] is not None:
            reporting_df = _state["reporting_data"] if _state.get("reporting_data") is not None else _state["campaign_data"]
            _state["events_result"] = process_market_events(df, reporting_df)
            if _state.get("smart_recs"):
                _state["smart_recs"] = merge_external_recommendations(
                    _state["smart_recs"], events_result=_state["events_result"])
            return _j({"filename": file.filename, "events": len(df),
                        "upcoming": _state["events_result"]["summary"]["upcoming_events"],
                        "recommendations": len(_state["events_result"].get("recommendations",[])),
                        "status": "Market events loaded and processed"})
        return _j({"filename": file.filename, "rows": len(df), "status": "Events loaded. Load campaign data first to process."})
    finally:
        os.unlink(tmp_path)

@app.post("/api/upload-trends")
async def upload_trends(file: UploadFile = File(...)):
    """Upload market trends CSV (CPC/CPM trends, benchmarks, Google Trends)."""
    suffix = Path(file.filename).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read(); tmp.write(content); tmp_path = tmp.name
    try:
        df = pd.read_csv(tmp_path) if suffix == ".csv" else pd.read_excel(tmp_path)
        required = {"date", "metric_type", "value"}
        missing = required - set(df.columns)
        if missing: raise HTTPException(400, f"Missing columns: {missing}. Required: {required}")
        _state["external_trends"] = df
        if _state["campaign_data"] is not None:
            reporting_df = _state["reporting_data"] if _state.get("reporting_data") is not None else _state["campaign_data"]
            _state["trends_result"] = process_market_trends(df, reporting_df)
            if _state.get("smart_recs"):
                _state["smart_recs"] = merge_external_recommendations(
                    _state["smart_recs"], trends_result=_state["trends_result"])
            return _j({"filename": file.filename, "metric_types": list(df["metric_type"].unique()),
                        "channels_covered": int(df["channel"].nunique()) if "channel" in df.columns else 0,
                        "recommendations": len(_state["trends_result"].get("recommendations",[])),
                        "status": "Market trends loaded and processed"})
        return _j({"filename": file.filename, "rows": len(df), "status": "Trends loaded. Load campaign data first to process."})
    finally:
        os.unlink(tmp_path)

@app.get("/api/external-data-status")
def get_external_data_status():
    """Check what external data is loaded."""
    return _j({
        "competitive": {"loaded": _state["external_competitive"] is not None,
            "summary": (_state.get("competitive_result") or {}).get("summary", {})},
        "events": {"loaded": _state["external_events"] is not None,
            "summary": (_state.get("events_result") or {}).get("summary", {})},
        "trends": {"loaded": _state["external_trends"] is not None,
            "summary": (_state.get("trends_result") or {}).get("summary", {})},
    })


def _normalize_date_columns(df):
    """Ensure both 'date' and 'month' columns exist for cross-engine compatibility."""
    df = df.copy()
    if "date" in df.columns and "month" not in df.columns:
        df["month"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m")
    elif "month" in df.columns and "date" not in df.columns:
        df["date"] = pd.to_datetime(df["month"].astype(str).apply(lambda x: x+"-01" if len(str(x))<=7 else x), errors="coerce")
    if "channel_type" not in df.columns:
        df["channel_type"] = df.get("ct", "online")
    for col, alt in [("conversions","conv"),("impressions","imps"),("revenue","rev"),("campaign","camp"),("channel","ch")]:
        if col not in df.columns and alt in df.columns:
            df[col] = df[alt]
    for col in ["impressions","clicks","leads","mqls","sqls","conversions","spend","revenue",
                "bounce_rate","avg_session_duration_sec","form_completion_rate","nps_score"]:
        if col not in df.columns: df[col] = 0
    if "region" not in df.columns: df["region"] = "All"
    if "product" not in df.columns: df["product"] = "All"
    return df


def _run_all_engines():
    """Run all engines. Each engine is wrapped in try/except — one failure never crashes the chain."""
    df = _state["campaign_data"]
    if df is None: return
    
    df = _normalize_date_columns(df)
    _state["campaign_data"] = df
    
    # Split data
    date_col = "month" if "month" in df.columns else "date"
    try:
        split = split_data(df, reporting_months=12, date_column=date_col)
        _state["data_split"] = split["metadata"]
        reporting_df = _normalize_date_columns(split["reporting"])
        training_df = _normalize_date_columns(split["training"])
    except Exception as e:
        print(f"[WARN] Split failed ({e}), using full dataset")
        _state["data_split"] = {"reporting_period":{"months":0},"training_period":{"months":0},"error":str(e)}
        reporting_df = df; training_df = df
    _state["reporting_data"] = reporting_df
    _state["training_data"] = training_df
    
    # Response curves
    try:
        _state["curves"] = fit_response_curves(training_df, model_type=_state.get("_model_type", "power_law"))
        print(f"[OK] Curves: {len(_state['curves'])} channels")
    except Exception as e:
        print(f"[FAIL] Curves: {e}"); _state["curves"] = {}
    
    # Attribution
    attr_dicts = {}
    try:
        if _state["journey_data"] is not None:
            _state["attribution"] = run_all_attribution(_state["journey_data"])
            _state["attribution_roi"] = compute_attribution_roi(_state["attribution"], reporting_df)
            for mn, md in _state["attribution"].items():
                try:
                    if hasattr(md, "groupby"): attr_dicts[mn] = md.groupby("channel")["attributed_revenue"].sum().to_dict()
                    elif isinstance(md, dict): attr_dicts[mn] = md
                except: pass
            print(f"[OK] Attribution: {len(attr_dicts)} models")
            # Markov attribution (needs journey data)
            try:
                from engines.markov_attribution import run_markov_attribution
                j_groups = {}
                for _, r in _state["journey_data"].iterrows():
                    jid = str(r.get("journey_id", r.get("id", "")))
                    if jid not in j_groups: j_groups[jid] = {"tps":[], "cv":False, "rv":0}
                    j_groups[jid]["tps"].append({"ch": str(r.get("channel","")), "o": int(r.get("touchpoint_order",0))})
                    j_groups[jid]["cv"] = bool(r.get("converted", False))
                    j_groups[jid]["rv"] = float(r.get("conversion_revenue", 0))
                markov_result = run_markov_attribution(list(j_groups.values()))
                markov_ch = markov_result.get("channels", {})
                if markov_ch:
                    attr_dicts["markov"] = {ch: info.get("revenue", info.get("attributed_revenue",0)) for ch, info in markov_ch.items()}
                    print(f"[OK] Markov: {len(attr_dicts['markov'])} channels")
                else:
                    print("[WARN] Markov: 0 channels returned")
            except Exception as e:
                print(f"[WARN] Markov: {e}")
    except Exception as e:
        print(f"[FAIL] Attribution: {e}"); _state["attribution"] = {}
    _state["_attr_dicts"] = attr_dicts
    
    # Optimization
    try:
        rs = float(reporting_df["spend"].sum())
        _state["optimization"] = optimize_budget(_state["curves"], rs, objective="balanced")
        print(f"[OK] Optimizer: uplift={_state['optimization'].get('summary',{}).get('uplift_pct',0):.1f}%")
    except Exception as e:
        print(f"[FAIL] Optimizer: {e}")
        _state["optimization"] = {"channels":[],"summary":{"total_budget":0,"current_revenue":0,"optimized_revenue":0,"revenue_uplift":0,"uplift_pct":0,"current_roi":0,"optimized_roi":0}}
    
    # Diagnostics
    try:
        _state["diagnostics"] = generate_recommendations(reporting_df, _state["curves"], attr_dicts)
        print(f"[OK] Recs: {len(_state['diagnostics'])}")
    except Exception as e:
        print(f"[FAIL] Recs: {e}"); _state["diagnostics"] = []
    
    # Pillars
    try:
        _state["pillars"] = run_three_pillars(reporting_df, _state["optimization"])
        print(f"[OK] Pillars: risk={_state['pillars'].get('total_value_at_risk',0):,.0f}")
    except Exception as e:
        print(f"[FAIL] Pillars: {e}")
        _state["pillars"] = {"revenue_leakage":{"total_leakage":0,"leakage_pct":0,"by_channel":[]},"experience_suppression":{"total_suppression":0,"items":[]},"avoidable_cost":{"total_avoidable_cost":0,"items":[]},"total_value_at_risk":0,"correction_potential":{"reallocation_uplift":0,"cx_fix_recovery":0,"cost_savings":0,"total_recoverable":0}}
    
    # Trend, funnel, ROI
    try: _state["trend_analysis"] = run_trend_analysis(training_df); print("[OK] Trends")
    except Exception as e: print(f"[FAIL] Trends: {e}"); _state["trend_analysis"] = {}
    try: _state["funnel_analysis"] = run_funnel_analysis(reporting_df); print("[OK] Funnel")
    except Exception as e: print(f"[FAIL] Funnel: {e}"); _state["funnel_analysis"] = {}
    try: _state["roi_analysis"] = compute_all_roi(reporting_df, _state["curves"]); print("[OK] ROI")
    except Exception as e: print(f"[FAIL] ROI: {e}"); _state["roi_analysis"] = []
    
    # Insights & Smart Recommendations
    try:
        _state["insights"] = generate_insights(
            reporting_df, _state["curves"], _state["optimization"], _state["pillars"],
            attr_dicts, _state.get("mmm_result"), _state.get("trend_analysis"), _state.get("funnel_analysis"))
        print(f"[OK] Insights: {_state['insights'].get('generated_count',0)} generated")
    except Exception as e:
        print(f"[FAIL] Insights: {e}"); _state["insights"] = {"executive_headlines":[],"channel_stories":[],"cross_model_insights":[],"risk_narratives":[],"opportunity_narratives":[],"generated_count":0}
    
    try:
        _state["smart_recs"] = generate_smart_recommendations(
            reporting_df, _state["curves"], attr_dicts, _state["optimization"],
            _state["pillars"], _state.get("trend_analysis"), _state.get("mmm_result"),
            _state.get("model_selections"))
        print(f"[OK] Smart Recs: {len(_state['smart_recs'])}")
    except Exception as e:
        print(f"[FAIL] Smart Recs: {e}"); _state["smart_recs"] = []
    
    # QoQ/YoY trends
    try:
        _state["qoq_yoy"] = compute_qoq_yoy_trends(reporting_df)
        # Per-channel trends
        ch_trends = {}
        for ch in reporting_df["channel"].unique():
            ch_trends[ch] = compute_qoq_yoy_trends(reporting_df, channel=ch)
        _state["channel_trends"] = ch_trends
        print(f"[OK] QoQ/YoY: {len(ch_trends)} channels")
    except Exception as e:
        print(f"[FAIL] QoQ/YoY: {e}"); _state["qoq_yoy"] = {}; _state["channel_trends"] = {}
    
    # External data re-processing (if loaded)
    try:
        if _state.get("external_competitive") is not None:
            _state["competitive_result"] = process_competitive_data(_state["external_competitive"], reporting_df)
            print(f"[OK] Competitive: {len(_state['competitive_result'].get('recommendations',[]))} recs")
        if _state.get("external_events") is not None:
            _state["events_result"] = process_market_events(_state["external_events"], reporting_df)
            print(f"[OK] Events: {_state['events_result']['summary']['upcoming_events']} upcoming")
        if _state.get("external_trends") is not None:
            _state["trends_result"] = process_market_trends(_state["external_trends"], reporting_df)
            print(f"[OK] Trends: {_state['trends_result']['summary']['n_recommendations']} recs")
        
        # Merge external recs into smart recs
        if _state.get("smart_recs") and any([_state.get("competitive_result"), _state.get("events_result"), _state.get("trends_result")]):
            _state["smart_recs"] = merge_external_recommendations(
                _state["smart_recs"],
                _state.get("competitive_result"), _state.get("events_result"), _state.get("trends_result"))
            print(f"[OK] Merged recs: {len(_state['smart_recs'])} total")
    except Exception as e:
        print(f"[FAIL] External data: {e}")
    
    # Persist session
    try:
        save_session("default", _state, user_id=0)
        print("[OK] Session persisted to SQLite")
    except Exception as e:
        print(f"[WARN] Session persist failed: {e}")


@app.post("/api/run-analysis")
def run_full_analysis(model_type: str = "power_law"):
    """Run all engines on current data. Accepts model_type: power_law or hill."""
    if _state["campaign_data"] is None:
        raise HTTPException(400, "No data loaded")
    _state["_model_type"] = model_type
    _run_all_engines()
    return _j({
        "status": "complete",
        "model_type": model_type,
        "response_curves_channels": list(_state["curves"].keys()) if _state["curves"] else [],
        "recommendations_count": len(_state["diagnostics"]) if _state["diagnostics"] else 0,
        "total_value_at_risk": _state["pillars"].get("total_value_at_risk", 0) if _state["pillars"] else 0,
        "optimization_uplift": _state["optimization"].get("summary",{}).get("uplift_pct",0) if _state["optimization"] else 0,
    })


# ═══════════════════════════════════════════════
#  CURRENT STATE
# ═══════════════════════════════════════════════

@app.get("/api/data-readiness")
def get_data_readiness():
    """Show what data is available, which engines can run, and what needs more data."""
    if _state["data_split"] is None:
        raise HTTPException(400, "No data loaded")
    split_meta = _state["data_split"]
    # Re-validate
    split = split_data(_state["campaign_data"], reporting_months=12,
                       date_column="month" if "month" in _state["campaign_data"].columns else "date")
    readiness = validate_split(split)
    return _j({
        "periods": split_meta,
        "engine_readiness": readiness["engine_readiness"],
        "overall_ready": readiness["overall_ready"],
        "warnings": readiness["warnings"],
        "recommendation": (
            "Upload 3+ years of historical data for reliable MMM and forecasting. "
            "Current reporting period uses the most recent 12 months for ROI and diagnostics."
        ) if not readiness["overall_ready"] else "All engines have sufficient data.",
    })


@app.get("/api/current-state")
def get_current_state(attribution_model: str = "last_touch"):
    if _state["campaign_data"] is None:
        raise HTTPException(400, "No data loaded")
    # Use REPORTING period (last 12 months) for current-state KPIs
    df = _state["reporting_data"] if _state["reporting_data"] is not None else _state["campaign_data"]
    
    total_spend = float(df["spend"].sum())
    total_revenue = float(df["revenue"].sum())
    total_conv = int(df["conversions"].sum())
    
    summary = {
        "total_spend": total_spend, "total_revenue": total_revenue,
        "roi": (total_revenue - total_spend) / max(total_spend, 1),
        "roas": total_revenue / max(total_spend, 1),
        "total_conversions": total_conv,
        "cac": total_spend / max(total_conv, 1),
    }
    
    # Channel-campaign matrix
    matrix = df.groupby(["channel", "campaign", "channel_type"]).agg(
        spend=("spend","sum"), revenue=("revenue","sum"), impressions=("impressions","sum"),
        clicks=("clicks","sum"), leads=("leads","sum"), conversions=("conversions","sum"),
    ).reset_index()
    matrix["roi"] = (matrix["revenue"] - matrix["spend"]) / matrix["spend"].clip(lower=1)
    matrix["roas"] = matrix["revenue"] / matrix["spend"].clip(lower=1)
    matrix["cac"] = matrix["spend"] / matrix["conversions"].clip(lower=1)
    
    # Monthly trends (use month if available, else date)
    time_col = "month" if "month" in df.columns else "date"
    trends = df.groupby(time_col).agg(
        spend=("spend","sum"), revenue=("revenue","sum"), conversions=("conversions","sum"),
    ).reset_index()
    trends.rename(columns={time_col: "month"}, inplace=True)
    trends["roi"] = (trends["revenue"] - trends["spend"]) / trends["spend"].clip(lower=1)
    
    # Online vs offline
    split = df.groupby("channel_type").agg(spend=("spend","sum"), revenue=("revenue","sum")).reset_index()
    
    # Attribution
    attr_data = None
    if _state["attribution_roi"] and attribution_model in _state["attribution_roi"]:
        attr_data = _state["attribution_roi"][attribution_model].to_dict(orient="records")
    
    return _j({"summary": summary, "channel_campaign_matrix": matrix.to_dict(orient="records"),
               "monthly_trends": trends.to_dict(orient="records"),
               "online_offline_split": split.to_dict(orient="records"),
               "attribution": attr_data, "attribution_model": attribution_model})


@app.get("/api/full-state")
def get_full_state():
    """
    Returns ALL data the frontend needs in a single call, shaped to match
    the frontend's internal data model. This is the primary integration endpoint.
    """
    if _state["campaign_data"] is None:
        raise HTTPException(400, "No data loaded — call POST /api/load-mock-data first")
    
    df = _state["reporting_data"] if _state["reporting_data"] is not None else _state["campaign_data"]
    
    # Build rows array matching frontend shape
    col_map = {"channel":"ch","campaign":"camp","channel_type":"ct","impressions":"imps",
               "conversions":"conv","revenue":"rev","bounce_rate":"br",
               "avg_session_duration_sec":"sd","form_completion_rate":"fc","nps_score":"nps",
               "region":"reg","product":"prod"}
    rows = []
    for _, r in df.iterrows():
        row = {}
        for col in df.columns:
            key = col_map.get(col, col)
            val = r[col]
            if isinstance(val, (np.integer,)): val = int(val)
            elif isinstance(val, (np.floating,)): val = float(val)
            row[key] = val
        # Add ml (month label) from month
        m_str = str(r.get("month", ""))
        if "-" in m_str:
            try: row["ml"] = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][int(m_str.split("-")[1])]
            except: row["ml"] = m_str
        rows.append(row)
    
    # Build optimizer in frontend shape
    opt_data = None
    if _state["optimization"] and "summary" in _state["optimization"]:
        opt = _state["optimization"]
        opt_channels = [{"channel":c["channel"], "cS":round(c.get("current_spend",0)),
            "oS":round(c.get("optimized_spend",0)), "chg":round(c.get("change_pct",0),1),
            "cR":round(c.get("current_revenue",0)), "oR":round(c.get("optimized_revenue",0)),
            "rChg":round(c.get("revenue_delta",0)),
            "cROI":round(c.get("current_roi",0),3), "oROI":round(c.get("optimized_roi",0),3),
            "mROI":round(c.get("marginal_roi",0),4), "locked":c.get("locked",False)}
            for c in opt.get("channels",[])]
        sm = opt.get("summary",{})
        opt_summary = {"cRev":round(sm.get("current_revenue",0)),
            "oRev":round(sm.get("optimized_revenue",0)),
            "uplift":round(sm.get("uplift_pct",0),2),
            "cROI":round(sm.get("current_roi",0),3),
            "oROI":round(sm.get("optimized_roi",0),3)}
        opt_data = {"channels":opt_channels, "summary":opt_summary}
    
    # Build pillars in frontend shape
    pl_data = None
    if _state["pillars"]:
        p = _state["pillars"]
        leak = p.get("revenue_leakage",{})
        exp = p.get("experience_suppression",{})
        cost = p.get("avoidable_cost",{})
        pl_data = {
            "leak":{"total":leak.get("total_leakage",0),"pct":leak.get("leakage_pct",0),
                "byCh":[{"channel":c.get("channel",""),"leakage":c.get("leakage",0),"type":c.get("type","")} 
                    for c in leak.get("by_channel",[])]},
            "exp":{"total":exp.get("total_suppression",0),
                "items":[{"ch":i.get("channel",""),"camp":i.get("campaign",""),"cvr":i.get("cvr",0),
                    "sR":i.get("suppressed_revenue",0),"br":i.get("bounce_rate",0)} for i in exp.get("items",[])]},
            "cost":{"total":cost.get("total_avoidable_cost",0),
                "items":[{"ch":i.get("channel",""),"cac":i.get("cac",0),"av":i.get("avoidable_cost",0)} for i in cost.get("items",[])]},
            "totalRisk":p.get("total_value_at_risk",0)
        }
    
    # Build recs in frontend shape
    recs_data = []
    if _state["diagnostics"]:
        for r in _state["diagnostics"]:
            recs_data.append({"type":r.get("type",""),"ch":r.get("channel",""),
                "camp":r.get("campaign",""),"rationale":r.get("rationale",""),
                "action":r.get("action",""),"impact":r.get("impact",0),
                "conf":r.get("confidence","Medium"),"effort":r.get("effort","Medium"),
                "id":r.get("id",""),"priority":r.get("priority",0)})
    
    # Attribution (use pre-built dicts from engine run, includes markov)
    attr_data = _state.get("_attr_dicts", {})
    if not attr_data and _state["attribution"]:
        for model_name, model_data in _state["attribution"].items():
            if hasattr(model_data, "groupby"):
                attr_data[model_name] = model_data.groupby("channel")["attributed_revenue"].sum().to_dict()
            elif isinstance(model_data, dict):
                attr_data[model_name] = model_data
    
    # Build curves in frontend shape
    curves_data = {}
    if _state["curves"]:
        for ch, info in _state["curves"].items():
            if "error" in info: continue
            p = info.get("params",{})
            curves_data[ch] = {"a":p.get("a",1),"b":p.get("b",0.5),
                "avgSpend":info.get("current_avg_spend",0),"satSpend":info.get("saturation_spend",0),
                "mROI":info.get("marginal_roi",0),"hd":info.get("headroom_pct",0),
                "cp":info.get("curve_points",[])}
    
    tS = float(df["spend"].sum())
    
    return _j({
        "rows": rows,
        "opt": opt_data or {"channels":[],"summary":{"cRev":0,"oRev":0,"uplift":0,"cROI":0,"oROI":0}},
        "pl": pl_data or {"leak":{"total":0,"pct":0,"byCh":[]},"exp":{"total":0,"items":[]},"cost":{"total":0,"items":[]},"totalRisk":0},
        "attr": attr_data,
        "curves": curves_data,
        "tS": tS,
        "recs": recs_data,
        "smartRecs": _state.get("smart_recs") or [],
        "insights": _state.get("insights") or {},
        "qoqYoy": _state.get("qoq_yoy") or {},
        "channelTrends": _state.get("channel_trends") or {},
        "modelSelections": _state.get("model_selections") or {},
        "modelDiagnostics": {
            "response_curves": {"model": _state.get("_model_type","power_law"), "channels": len(curves_data), "avg_r2": round(sum(c.get("r2",0) for c in (_state.get("curves") or {}).values() if "error" not in c) / max(len(curves_data),1), 3)},
            "mmm": {"method": (_state.get("mmm_result") or {}).get("method","not_run"), "r2": (_state.get("mmm_result") or {}).get("model_diagnostics",{}).get("r_squared",0)},
            "forecasting": {"method": "prophet" if _state.get("forecast") else "not_run"},
            "optimizer": {"converged": (_state.get("optimization") or {}).get("optimizer_info",{}).get("converged", True)},
        },
        "externalData": {
            "competitive": (_state.get("competitive_result") or {}).get("summary"),
            "events": (_state.get("events_result") or {}).get("summary"),
            "trends": (_state.get("trends_result") or {}).get("summary"),
            "shareOfVoice": (_state.get("competitive_result") or {}).get("share_of_voice"),
            "benchmarks": (_state.get("trends_result") or {}).get("benchmarks"),
            "costAdjustments": (_state.get("trends_result") or {}).get("cost_adjustments"),
            "eventCalendar": [e for e in ((_state.get("events_result") or {}).get("events") or []) if e.get("is_upcoming")],
            "categoryGrowth": (_state.get("trends_result") or {}).get("category_growth"),
        },
        "dataReadiness": _state.get("data_split"),
        "apiMode": True,
        "warnings": _get_data_warnings(),
    })


@app.get("/api/deep-dive/{channel}")
def get_channel_deep_dive(channel: str):
    if _state["campaign_data"] is None: raise HTTPException(400, "No data loaded")
    df = _state["campaign_data"]
    ch_data = df[df["channel"] == channel]
    if len(ch_data) == 0: raise HTTPException(404, f"Channel '{channel}' not found")
    
    trend = ch_data.groupby("month").agg(spend=("spend","sum"),revenue=("revenue","sum"),conversions=("conversions","sum"),leads=("leads","sum")).reset_index()
    trend["roi"] = (trend["revenue"] - trend["spend"]) / trend["spend"]
    regional = ch_data.groupby("region").agg(spend=("spend","sum"),revenue=("revenue","sum"),conversions=("conversions","sum")).reset_index()
    regional["roi"] = (regional["revenue"] - regional["spend"]) / regional["spend"]
    funnel = {s: int(ch_data[s].sum()) for s in ["impressions","clicks","leads","mqls","sqls","conversions"]}
    cx = {"avg_bounce_rate":float(ch_data["bounce_rate"].mean()),"avg_session_duration":float(ch_data["avg_session_duration_sec"].mean()),
          "avg_form_completion":float(ch_data["form_completion_rate"].mean()),"avg_nps":float(ch_data["nps_score"].mean())}
    curve_data = _state["curves"].get(channel) if _state["curves"] else None
    return _j({"channel":channel,"monthly_trend":trend.to_dict(orient="records"),
               "regional_breakdown":regional.to_dict(orient="records"),"funnel":funnel,"cx_signals":cx,"response_curve":curve_data})


# ═══════════════════════════════════════════════
#  ANALYSIS ENDPOINTS
# ═══════════════════════════════════════════════

@app.get("/api/validation")
def get_validation():
    if _state["validation"] is None: raise HTTPException(400, "No data loaded")
    return _j(_state["validation"])

@app.get("/api/response-curves")
def get_response_curves():
    _ensure_analysis()
    if _state["curves"] is None: raise HTTPException(400, "No data loaded — upload data or call /api/load-mock-data first")
    return _j(_state["curves"])

@app.get("/api/recommendations")
def get_recommendations():
    _ensure_analysis()
    if _state["diagnostics"] is None: raise HTTPException(400, "No data loaded — upload data or call /api/load-mock-data first")
    return _j(_state["diagnostics"])

@app.post("/api/optimize")
def run_optimization(
    total_budget: Optional[float] = None,
    objective: str = "balanced",
    model_type: str = "power_law",
    weight_revenue: float = 0.4,
    weight_roi: float = 0.3,
    weight_leakage: float = 0.15,
    weight_cost: float = 0.15,
):
    """Run optimization with custom objective, weights, and model type."""
    _ensure_analysis()
    if _state["curves"] is None: raise HTTPException(400, "No data loaded — upload data or call /api/load-mock-data first")
    
    # Re-fit curves if model type changed
    if model_type != _state.get("_model_type", "power_law"):
        _state["_model_type"] = model_type
        training_df = _state.get("training_data")
        if training_df is None: training_df = _state["campaign_data"]
        training_df = _normalize_date_columns(training_df)
        _state["curves"] = fit_response_curves(training_df, model_type=model_type)
    
    if total_budget is None: total_budget = float(_state["campaign_data"]["spend"].sum())
    weights = {"revenue": weight_revenue, "roi": weight_roi, "leakage": weight_leakage, "cost": weight_cost}
    result = optimize_budget(_state["curves"], total_budget, objective=objective, objective_weights=weights)
    _state["optimization"] = result
    reporting_df = _state.get("reporting_data")
    if reporting_df is None: reporting_df = _state["campaign_data"]
    _state["pillars"] = run_three_pillars(reporting_df, result)
    return _j(result)

@app.post("/api/model-selections")
def update_model_selections(
    attribution: str = "markov",
    response_curves: str = "auto",
    mmm: str = "auto",
    forecasting: str = "prophet",
    optimizer: str = "slsqp",
):
    """Update model selections and re-run full engine chain. Auto-triggers on model change."""
    _ensure_analysis()
    _state["model_selections"] = {
        "attribution": attribution, "response_curves": response_curves,
        "mmm": mmm, "forecasting": forecasting, "optimizer": optimizer,
    }
    # Map response curve selection to _model_type
    rc_map = {"auto":"auto","power_law":"power_law","hill":"hill","growth":"power_law","saturation":"hill"}
    _state["_model_type"] = rc_map.get(response_curves, "auto")
    # Re-run all engines with new selections
    _run_all_engines()
    return _j({"status": "re-run complete", "model_selections": _state["model_selections"],
               "smart_recs_count": len(_state.get("smart_recs") or []),
               "insights_count": (_state.get("insights") or {}).get("generated_count", 0)})

@app.get("/api/insights")
def get_insights():
    """Get all narrative insights."""
    _ensure_analysis()
    return _j({
        "insights": _state.get("insights") or {},
        "smart_recs": _state.get("smart_recs") or [],
        "qoq_yoy": _state.get("qoq_yoy") or {},
        "channel_trends": _state.get("channel_trends") or {},
        "model_selections": _state.get("model_selections") or {},
    })

@app.get("/api/sensitivity")
def get_sensitivity(objective: str = "balanced"):
    _ensure_analysis()
    if _state["curves"] is None: raise HTTPException(400, "No data loaded — upload data or call /api/load-mock-data first")
    base_budget = float(_state["campaign_data"]["spend"].sum())
    return _j(sensitivity_analysis(_state["curves"], base_budget, objective))

@app.get("/api/pillars")
def get_pillars():
    _ensure_analysis()
    if _state["pillars"] is None: raise HTTPException(400, "No data loaded — upload data or call /api/load-mock-data first")
    return _j(_state["pillars"])

@app.get("/api/business-case")
def get_business_case():
    if not all([_state["optimization"], _state["pillars"], _state["diagnostics"]]):
        raise HTTPException(400, "Run full analysis first")
    opt = _state["optimization"]; pillars = _state["pillars"]; recs = _state["diagnostics"]
    return _j({
        "optimization_summary": opt.get("summary", {}),
        "value_at_risk": pillars.get("total_value_at_risk", 0),
        "correction_potential": pillars.get("correction_potential", {}),
        "top_recommendations": recs[:5] if isinstance(recs, list) else [],
        "implementation_phases": [
            {"phase": "Immediate (0-30 days)", "actions": [r for r in recs if r.get("effort") == "Low"][:3]},
            {"phase": "Short-term (30-90 days)", "actions": [r for r in recs if r.get("effort") == "Medium"][:3]},
            {"phase": "Strategic (90+ days)", "actions": [r for r in recs if r.get("effort") == "High"][:3]},
        ] if isinstance(recs, list) else [],
    })

@app.get("/api/executive-summary")
def get_executive_summary():
    """Generate a downloadable executive summary as text."""
    if not all([_state["optimization"], _state["pillars"], _state["diagnostics"], _state["campaign_data"] is not None]):
        raise HTTPException(400, "Run full analysis first")
    df = _state["reporting_data"] if _state["reporting_data"] is not None else _state["campaign_data"]
    opt = _state["optimization"]; pil = _state["pillars"]; recs = _state["diagnostics"]
    ts = float(df["spend"].sum()); tr = float(df["revenue"].sum())
    sm = opt.get("summary", {})
    lines = [
        "YIELD INTELLIGENCE — EXECUTIVE SUMMARY",
        "=" * 50, "",
        "PORTFOLIO OVERVIEW",
        f"  Total Marketing Spend:   ${ts:,.0f}",
        f"  Total Revenue:           ${tr:,.0f}",
        f"  Portfolio ROI:           {(tr-ts)/max(ts,1):.2f}x",
        f"  ROAS:                    {tr/max(ts,1):.2f}x", "",
        "OPTIMIZATION RESULTS",
        f"  Current Revenue:         ${sm.get('current_revenue',0):,.0f}",
        f"  Optimized Revenue:       ${sm.get('optimized_revenue',0):,.0f}",
        f"  Revenue Uplift:          {sm.get('uplift_pct',0):.1f}%",
        f"  ROI Improvement:         {sm.get('current_roi',0):.2f}x → {sm.get('optimized_roi',0):.2f}x", "",
        "VALUE AT RISK",
        f"  Total Value at Risk:     ${pil.get('total_value_at_risk',0):,.0f}",
        f"  Revenue Leakage:         ${pil.get('revenue_leakage',{}).get('total_leakage',0):,.0f}",
        f"  CX Suppression:          ${pil.get('experience_suppression',{}).get('total_suppression',0):,.0f}",
        f"  Avoidable Cost:          ${pil.get('avoidable_cost',{}).get('total_avoidable_cost',0):,.0f}", "",
        "CHANNEL ALLOCATION (Top changes)", "-" * 50,
    ]
    for c in sorted(opt.get("channels",[]), key=lambda x: abs(x.get("change_pct",0)), reverse=True)[:8]:
        ch = c.get("channel","")
        lines.append(f"  {ch:20s}  ${c.get('current_spend',0):>12,.0f} → ${c.get('optimized_spend',0):>12,.0f}  ({c.get('change_pct',0):+.1f}%)")
    lines += ["", "TOP RECOMMENDATIONS", "-" * 50]
    for i, r in enumerate(recs[:8]):
        lines.append(f"  {i+1}. [{r.get('type','')}] {r.get('channel','')}: {r.get('action','')}")
        if r.get('impact',0): lines.append(f"     Impact: ${abs(r['impact']):,.0f}  Confidence: {r.get('confidence','')}")
    lines += ["", "IMPLEMENTATION ROADMAP", "-" * 50]
    for phase, effort in [("Immediate (0-30 days)","Low"),("Short-term (30-90 days)","Medium"),("Strategic (90+ days)","High")]:
        phase_recs = [r for r in recs if r.get("effort")==effort][:3]
        if phase_recs:
            lines.append(f"  {phase}")
            for r in phase_recs: lines.append(f"    - {r.get('channel','')}: {r.get('action','')}")
    lines += ["", "-" * 50, "Generated by Yield Intelligence Platform", "All estimates are directional. Validate with holdout tests before scaling."]
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("\n".join(lines), media_type="text/plain",
                            headers={"Content-Disposition": "attachment; filename=executive_summary.txt"})

@app.get("/api/trend-analysis")
def get_trend_analysis():
    if _state["trend_analysis"] is None:
        if _state["campaign_data"] is not None:
            _state["trend_analysis"] = run_trend_analysis(_state["campaign_data"])  # ✅ fixed
        else: raise HTTPException(400, "No data loaded")
    return _j(_state["trend_analysis"])

@app.get("/api/funnel-analysis")
def get_funnel_analysis():
    if _state["funnel_analysis"] is None:
        if _state["campaign_data"] is not None:
            _state["funnel_analysis"] = run_funnel_analysis(_state["campaign_data"])  # ✅ fixed
        else: raise HTTPException(400, "No data loaded")
    return _j(_state["funnel_analysis"])

@app.get("/api/roi-analysis")
def get_roi_analysis(gross_margin_pct: float = 0.65):
    if _state["campaign_data"] is None: raise HTTPException(400, "No data loaded")
    return _j(compute_all_roi(_state["campaign_data"], _state.get("curves"), gross_margin_pct))  # ✅ fixed

@app.get("/api/download-template")
def download_template():
    template_path = os.path.join(os.path.dirname(__file__), "data", "upload_template.csv")
    if os.path.exists(template_path):
        with open(template_path) as f: return JSONResponse(content={"csv": f.read()})
    raise HTTPException(404, "Template not found")


# ═══════════════════════════════════════════════
#  PHASE 2 ENDPOINTS
# ═══════════════════════════════════════════════

@app.post("/api/adstock")
def run_adstock(adstock_type: str = "geometric"):
    if _state["campaign_data"] is None: raise HTTPException(400, "No data loaded")
    return _j(compute_channel_adstock(_state["campaign_data"], adstock_type))

@app.post("/api/mmm")
def run_mmm_endpoint():
    """Run Bayesian MMM (PyMC → OLS fallback)."""
    if _state["campaign_data"] is None: raise HTTPException(400, "No data loaded")
    return _j(run_mmm(_state["campaign_data"], method="auto"))  # ✅ updated call signature

@app.get("/api/markov-attribution")
def get_markov_attribution():
    if _state["journey_data"] is None: raise HTTPException(400, "No journey data")
    j_groups = {}
    for _, row in _state["journey_data"].iterrows():
        jid = row["journey_id"]
        if jid not in j_groups:
            j_groups[jid] = {"id":jid,"tps":[],"cv":row["converted"],"rv":0,"nt":row["total_touchpoints"]}
        j_groups[jid]["tps"].append({"ch":row["channel"],"camp":row["campaign"],"o":row["touchpoint_order"]})
        if row["conversion_revenue"] > 0: j_groups[jid]["rv"] = row["conversion_revenue"]
    return _j(run_markov_attribution(list(j_groups.values())))  # ✅ fixed name

@app.get("/api/forecast")
def get_forecast(periods: int = 12):
    if _state["campaign_data"] is None: raise HTTPException(400, "No data loaded")
    return _j(run_forecast(_state["campaign_data"], "revenue", periods))  # ✅ fixed name + args

@app.get("/api/cross-channel")
def get_cross_channel():
    if _state["campaign_data"] is None: raise HTTPException(400, "No data loaded")
    return _j(run_cross_channel_analysis(_state["campaign_data"]))


# ═══════════════════════════════════════════════
#  PHASE 3 ENDPOINTS
# ═══════════════════════════════════════════════

@app.get("/api/shapley")
def get_shapley():
    """Shapley values require response curves for the value function."""
    _ensure_analysis()
    if _state["curves"] is None: raise HTTPException(400, "No data loaded — upload data or call /api/load-mock-data first")
    curves = _state["curves"]
    channels = list(curves.keys())
    def value_fn(coalition):
        total = 0
        for ch in coalition:
            if ch in curves and "params" in curves[ch]:
                p = curves[ch]["params"]
                a, b = p.get("a",1), p.get("b",0.5)
                avg = curves[ch].get("current_avg_spend", 1000)
                total += a * np.power(max(avg, 1), b) * 12
        return total
    return _j(compute_shapley_values(channels, value_fn))  # ✅ fixed name + args

@app.post("/api/multi-objective")
def run_multi_objective(n_solutions: int = 30):
    _ensure_analysis()
    if _state["curves"] is None: raise HTTPException(400, "No data loaded — upload data or call /api/load-mock-data first")
    budget = float(_state["campaign_data"]["spend"].sum())
    return _j(pareto_optimize(_state["curves"], budget, n_points=n_solutions))  # ✅ fixed name

@app.get("/api/geo-lift/{region}")
def get_geo_lift(region: str):
    if _state["campaign_data"] is None: raise HTTPException(400, "No data loaded")
    return _j(run_geo_lift(_state["campaign_data"], test_region=region))  # ✅ fixed name

@app.get("/api/hierarchical-forecast")
def get_hierarchical_forecast(periods: int = 12):
    if _state["campaign_data"] is None: raise HTTPException(400, "No data loaded")
    return _j(run_hierarchical_forecast(_state["campaign_data"], periods=periods))  # ✅ fixed name

@app.get("/api/automated-recommendations")
def get_automated_recs():
    if _state["campaign_data"] is None: raise HTTPException(400, "No data loaded")
    return _j(automated_recommendations(_state["campaign_data"],
        response_curves=_state.get("curves"), attribution_results=_state.get("attribution")))

@app.get("/api/model-health")
def get_model_health():
    _ensure_analysis()
    if _state["curves"] is None: raise HTTPException(400, "No data loaded — upload data or call /api/load-mock-data first")
    return _j(check_model_drift(_state["curves"], _state["campaign_data"]))


# ═══════════════════════════════════════════════
#  FRONTEND SERVING
# ═══════════════════════════════════════════════

from starlette.staticfiles import StaticFiles

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
# ═══════════════════════════════════════════════════════
#  AUTH ENDPOINTS
# ═══════════════════════════════════════════════════════

@app.post("/api/auth/register")
def api_register(username: str, password: str, role: str = "analyst"):
    """Register a new user. Returns JWT token."""
    return _j(register_user(username, password, role))

@app.post("/api/auth/login")
def api_login(username: str, password: str):
    """Login and get JWT token."""
    return _j(login_user(username, password))

@app.get("/api/auth/me")
async def api_me(user=Depends(get_current_user)):
    """Get current user info from token."""
    if user is None:
        return _j({"authenticated": False, "role": "anonymous"})
    return _j({"authenticated": True, "user_id": user["id"], "username": user["username"], "role": user["role"]})


# ═══════════════════════════════════════════════════════
#  SCENARIO ENDPOINTS
# ═══════════════════════════════════════════════════════

@app.post("/api/scenarios/save")
def api_save_scenario(name: str, description: str = ""):
    """Save current optimizer state as a named scenario."""
    if _state["optimization"] is None:
        raise HTTPException(400, "Run optimization first")
    opt = _state["optimization"]
    params = {
        "model_selections": _state.get("model_selections", {}),
        "model_type": _state.get("_model_type", "auto"),
        "total_budget": opt.get("summary", {}).get("total_budget", 0),
        "objective": "balanced",
    }
    results = {
        "summary": opt.get("summary", {}),
        "channels": opt.get("channels", []),
        "pillars_summary": {
            "total_value_at_risk": (_state.get("pillars") or {}).get("total_value_at_risk", 0),
            "revenue_leakage": (_state.get("pillars") or {}).get("revenue_leakage", {}).get("total_leakage", 0),
        },
        "smart_recs_count": len(_state.get("smart_recs") or []),
        "insights_count": (_state.get("insights") or {}).get("generated_count", 0),
    }
    scenario_id = save_scenario(user_id=0, session_id="default", name=name, description=description,
                                 parameters=params, results=results)
    return _j({"id": scenario_id, "name": name, "status": "saved"})

@app.get("/api/scenarios")
def api_list_scenarios():
    """List all saved scenarios."""
    scenarios = list_scenarios()
    return _j({"scenarios": scenarios, "count": len(scenarios)})

@app.get("/api/scenarios/{scenario_id}")
def api_get_scenario(scenario_id: int):
    """Load a specific scenario."""
    scenario = load_scenario(scenario_id)
    if not scenario:
        raise HTTPException(404, "Scenario not found")
    return _j(scenario)

@app.delete("/api/scenarios/{scenario_id}")
def api_delete_scenario(scenario_id: int):
    """Delete a scenario."""
    from persistence import _get_conn
    conn = _get_conn()
    conn.execute("DELETE FROM scenarios WHERE id = ?", (scenario_id,))
    conn.commit()
    conn.close()
    return _j({"deleted": scenario_id})

@app.post("/api/scenarios/compare")
def api_compare_scenarios(ids: str):
    """Compare multiple scenarios. Pass ids as comma-separated: ?ids=1,2,3"""
    id_list = [int(x.strip()) for x in ids.split(",") if x.strip()]
    if len(id_list) < 2:
        raise HTTPException(400, "Need at least 2 scenario IDs to compare")
    scenarios = compare_scenarios(id_list)
    if len(scenarios) < 2:
        raise HTTPException(404, "One or more scenarios not found")
    # Build comparison
    comparison = {
        "scenarios": scenarios,
        "metrics_comparison": [],
    }
    metrics = ["current_revenue", "optimized_revenue", "uplift_pct", "current_roi", "optimized_roi"]
    for metric in metrics:
        row = {"metric": metric}
        for s in scenarios:
            row[f"scenario_{s['id']}"] = s.get("results", {}).get("summary", {}).get(metric, 0)
        comparison["metrics_comparison"].append(row)
    
    # Channel-level comparison
    channel_comparison = {}
    for s in scenarios:
        for ch in s.get("results", {}).get("channels", []):
            ch_name = ch.get("channel", "")
            if ch_name not in channel_comparison:
                channel_comparison[ch_name] = {"channel": ch_name}
            channel_comparison[ch_name][f"spend_s{s['id']}"] = ch.get("optimized_spend", 0)
            channel_comparison[ch_name][f"rev_s{s['id']}"] = ch.get("optimized_revenue", 0)
    comparison["channel_comparison"] = list(channel_comparison.values())
    
    return _j(comparison)


# ═══════════════════════════════════════════════════════
#  STATIC FILES & FRONTEND
# ═══════════════════════════════════════════════════════

if not os.path.isdir(frontend_dir):
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")

try:
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
except Exception:
    pass

@app.get("/app", response_class=HTMLResponse)
def serve_frontend():
    for p in [os.path.join(frontend_dir, "index.html"),
              os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")]:
        if os.path.exists(p):
            with open(p) as f: return HTMLResponse(f.read())
    return HTMLResponse("<h1>Frontend not found</h1>", status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
