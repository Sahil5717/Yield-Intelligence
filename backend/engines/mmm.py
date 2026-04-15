"""
Bayesian Marketing Mix Model — Production Grade
================================================
Model: Revenue_t = baseline + Σ_c β_c · Hill(Adstock(Spend_c,t; λ_c); K_c) + season + ε_t

Libraries:
    pymc (NUTS sampler), arviz (diagnostics), scipy (MLE fallback), scikit-learn (metrics)
"""
import numpy as np
import pandas as pd
from typing import Dict, Optional
from sklearn.metrics import r2_score, mean_absolute_percentage_error
import warnings, logging
warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

def geometric_adstock(x, decay):
    out = np.zeros_like(x, dtype=np.float64)
    out[0] = x[0]
    for t in range(1, len(x)):
        out[t] = x[t] + decay * out[t - 1]
    return out

def hill_saturation(x, half_sat, slope=1.0):
    x_s = np.maximum(x, 1e-10)
    return np.power(x_s, slope) / (np.power(half_sat, slope) + np.power(x_s, slope))

def weibull_adstock(x, shape, scale, max_lag=13):
    """Weibull adstock: flexible peak+decay. shape>1=delayed peak (TV/events), shape≤1=immediate."""
    lags = np.arange(max_lag)
    w = (shape/scale)*np.power(lags/scale, shape-1)*np.exp(-np.power(lags/scale, shape))
    w = w/(w.sum()+1e-10)
    return np.convolve(x, w, mode="full")[:len(x)]

def select_best_adstock(spend, revenue):
    """Auto-select geometric vs Weibull adstock per channel."""
    if spend.sum()==0 or len(spend)<6: return "geometric", {"decay":0.5}, 0.0
    best_corr,best_type,best_params = -1,"geometric",{"decay":0.5}
    for d in np.arange(0.05,0.95,0.05):
        ad=geometric_adstock(spend,d)
        if ad.std()>0:
            corr=abs(np.corrcoef(ad,revenue)[0,1])
            if corr>best_corr: best_corr=corr; best_type="geometric"; best_params={"decay":round(d,2)}
    for shape in [0.5,1.0,1.5,2.0,3.0]:
        for scale in [1.0,2.0,3.0,5.0]:
            try:
                ad=weibull_adstock(spend,shape,scale)
                if ad.std()>0:
                    corr=abs(np.corrcoef(ad,revenue)[0,1])
                    if corr>best_corr: best_corr=corr; best_type="weibull"; best_params={"shape":shape,"scale":scale}
            except: pass
    return best_type, best_params, round(best_corr,4)

def prepare_mmm_data(df):
    time_col = "month" if "month" in df.columns else "date"
    monthly = df.groupby(time_col).agg(revenue=("revenue","sum"), total_spend=("spend","sum")).reset_index().sort_values(time_col)
    channels = sorted(df["channel"].unique())
    spend_matrix = {}
    for ch in channels:
        ch_agg = df[df["channel"]==ch].groupby(time_col)["spend"].sum()
        spend_matrix[ch] = monthly[time_col].map(ch_agg).fillna(0).values.astype(np.float64)
    if "month" in df.columns:
        month_nums = monthly["month"].apply(lambda x: int(str(x).split("-")[1]) if "-" in str(x) else 1).values
    else:
        month_nums = (np.arange(len(monthly)) % 12) + 1
    return {"revenue": monthly["revenue"].values.astype(np.float64), "spend_matrix": spend_matrix,
            "channels": channels, "n_periods": len(monthly), "month_nums": month_nums, "periods": monthly[time_col].values,
            "trend": np.arange(len(monthly), dtype=np.float64)}

def fit_bayesian_mmm(data, n_draws=1000, n_tune=500, n_chains=2):
    """Full Bayesian MMM. Adstock decay is sampled jointly with betas via NUTS."""
    import pymc as pm
    import arviz as az
    revenue = data["revenue"]; channels = data["channels"]; n_ch = len(channels); T = data["n_periods"]
    spend_raw = np.column_stack([data["spend_matrix"][ch] for ch in channels])
    spend_scales = spend_raw.max(axis=0) + 1e-10
    spend_normed = spend_raw / spend_scales
    sin_s = np.sin(2*np.pi*data["month_nums"]/12); cos_s = np.cos(2*np.pi*data["month_nums"]/12)
    rev_mean, rev_std = revenue.mean(), revenue.std()+1e-10

    with pm.Model():
        baseline = pm.Normal("baseline", mu=rev_mean, sigma=rev_std)
        betas = pm.HalfNormal("betas", sigma=rev_std*0.5, shape=n_ch)
        decays = pm.Beta("decays", alpha=3, beta=3, shape=n_ch)
        half_sats = pm.LogNormal("half_sats", mu=-0.7, sigma=0.5, shape=n_ch)
        gamma = pm.Normal("gamma", mu=0, sigma=rev_std*0.1, shape=2)
        sigma = pm.HalfNormal("sigma", sigma=rev_std*0.3)
        mu = baseline + gamma[0]*sin_s + gamma[1]*cos_s
        for c in range(n_ch):
            ad_list = [spend_normed[0, c]]
            for t in range(1, T):
                ad_list.append(spend_normed[t, c] + decays[c]*ad_list[-1])
            ad_tensor = pm.math.stack(ad_list)
            sat = ad_tensor / (half_sats[c] + ad_tensor)
            mu = mu + betas[c] * sat * spend_scales[c]
        pm.Normal("obs", mu=mu, sigma=sigma, observed=revenue)
        trace = pm.sample(draws=n_draws, tune=n_tune, chains=n_chains, cores=1,
                          target_accept=0.9, return_inferencedata=True, progressbar=False, random_seed=42)

    summary = az.summary(trace, var_names=["betas","decays","baseline"])
    rhat_max = float(summary["r_hat"].max()); ess_min = float(summary["ess_bulk"].min())
    try: loo_score = float(az.loo(trace).loo)
    except: loo_score = None
    beta_means = trace.posterior["betas"].values.mean(axis=(0,1))
    beta_stds = trace.posterior["betas"].values.std(axis=(0,1))
    beta_hdi = az.hdi(trace, var_names=["betas"], hdi_prob=0.9)["betas"].values
    decay_means = trace.posterior["decays"].values.mean(axis=(0,1))
    decay_stds = trace.posterior["decays"].values.std(axis=(0,1))
    baseline_mean = float(trace.posterior["baseline"].values.mean())

    contributions = {}; total_media = 0
    for c, ch in enumerate(channels):
        spend = data["spend_matrix"][ch]; d = float(decay_means[c])
        hs = float(trace.posterior["half_sats"].values.mean(axis=(0,1))[c])
        ad = geometric_adstock(spend/spend_scales[c], d); sat = hill_saturation(ad, hs)
        contrib = max(0, float(beta_means[c]) * sat.sum() * spend_scales[c]); total_media += contrib
        contributions[ch] = {"contribution": round(contrib,0), "beta_mean": round(float(beta_means[c]),4),
            "beta_std": round(float(beta_stds[c]),4), "beta_hdi_90": [round(float(beta_hdi[c,0]),4), round(float(beta_hdi[c,1]),4)],
            "decay_mean": round(d,3), "decay_std": round(float(decay_stds[c]),3),
            "spend": round(float(spend.sum()),0)}

    total_rev = float(revenue.sum()); bl_contrib = max(0, total_rev - total_media)
    y_pred = np.full(T, baseline_mean)
    y_pred += float(trace.posterior["gamma"].values.mean(axis=(0,1))[0])*sin_s
    y_pred += float(trace.posterior["gamma"].values.mean(axis=(0,1))[1])*cos_s
    for c, ch in enumerate(channels):
        ad = geometric_adstock(data["spend_matrix"][ch]/spend_scales[c], float(decay_means[c]))
        hs = float(trace.posterior["half_sats"].values.mean(axis=(0,1))[c])
        y_pred += float(beta_means[c]) * hill_saturation(ad, hs) * spend_scales[c]
    for ch in channels:
        cc = contributions[ch]; cc["contribution_pct"] = round(cc["contribution"]/max(total_rev,1)*100,1)
        cc["mmm_roas"] = round(cc["contribution"]/max(cc["spend"],1),2)
        ci_w = cc["beta_std"]/max(cc["beta_mean"],0.001)
        cc["confidence"] = "High" if ci_w<0.25 else ("Medium" if ci_w<0.5 else "Low")
    return {"method":"bayesian_pymc","contributions":contributions,
        "baseline_contribution":round(bl_contrib,0),"baseline_pct":round(bl_contrib/max(total_rev,1)*100,1),
        "total_revenue":round(total_rev,0),
        "model_diagnostics":{"r_squared":round(float(r2_score(revenue,y_pred)),4),
            "mape":round(float(mean_absolute_percentage_error(revenue,y_pred)*100),2),
            "r_hat_max":round(rhat_max,4),"converged":rhat_max<1.05,"ess_min":round(ess_min,0),
            "loo_cv":loo_score,"n_draws":n_draws,"n_chains":n_chains,"n_periods":T},
        "fitted_values":y_pred.tolist(),"actual_values":revenue.tolist(),
        "channels":channels,"periods":[str(p) for p in data["periods"]]}

def fit_ols_mmm(data):
    """OLS fallback with bootstrap uncertainty. Used when PyMC unavailable."""
    from numpy.linalg import lstsq
    revenue = data["revenue"]; channels = data["channels"]; T = data["n_periods"]
    best_decays = {}
    for ch in channels:
        spend = data["spend_matrix"][ch]
        if spend.sum()==0: best_decays[ch]=0.0; continue
        best_c, best_d = -1, 0.5
        for d in np.arange(0.05, 0.95, 0.05):
            ad = geometric_adstock(spend, d)
            if ad.std()>0:
                corr = np.corrcoef(ad, revenue)[0,1]
                if corr>best_c: best_c=corr; best_d=d
        best_decays[ch] = round(best_d, 2)
    X = np.zeros((T, len(channels)))
    half_sats = {}
    for c, ch in enumerate(channels):
        ad = geometric_adstock(data["spend_matrix"][ch], best_decays[ch])
        hs = float(np.median(ad[ad>0])) if np.any(ad>0) else 1.0
        half_sats[ch] = hs
        X[:,c] = hill_saturation(ad, hs)
    sin_s = np.sin(2*np.pi*data["month_nums"]/12); cos_s = np.cos(2*np.pi*data["month_nums"]/12)
    X_full = np.column_stack([np.ones(T), X, sin_s, cos_s])
    coeffs,_,_,_ = lstsq(X_full, revenue, rcond=None)
    baseline_mean = float(coeffs[0]); beta_means = np.abs(coeffs[1:1+len(channels)])
    n_boot=100; beta_boot=np.zeros((n_boot,len(channels)))
    for b in range(n_boot):
        idx=np.random.choice(T,T,replace=True)
        try: cb,_,_,_=lstsq(X_full[idx],revenue[idx],rcond=None); beta_boot[b]=np.abs(cb[1:1+len(channels)])
        except: beta_boot[b]=beta_means
    beta_stds = beta_boot.std(axis=0)
    y_pred = X_full @ coeffs
    contributions = {}; total_media=0
    for c, ch in enumerate(channels):
        contrib=max(0,float(beta_means[c]*X[:,c].sum())); total_media+=contrib
        contributions[ch]={"contribution":round(contrib,0),"beta_mean":round(float(beta_means[c]),4),
            "beta_std":round(float(beta_stds[c]),4),"decay_mean":best_decays[ch],
            "half_saturation":half_sats[ch],
            "spend":round(float(data["spend_matrix"][ch].sum()),0)}
    total_rev=float(revenue.sum()); bl=max(0,total_rev-total_media)
    for ch in channels:
        cc=contributions[ch]; cc["contribution_pct"]=round(cc["contribution"]/max(total_rev,1)*100,1)
        cc["mmm_roas"]=round(cc["contribution"]/max(cc["spend"],1),2)
        ci_w=cc["beta_std"]/max(cc["beta_mean"],0.001)
        cc["confidence"]="High" if ci_w<0.3 else ("Medium" if ci_w<0.6 else "Low")
    return {"method":"ols_bootstrap","contributions":contributions,
        "baseline_contribution":round(bl,0),"baseline_pct":round(bl/max(total_rev,1)*100,1),
        "total_revenue":round(total_rev,0),
        "model_diagnostics":{"r_squared":round(float(r2_score(revenue,y_pred)),4),
            "mape":round(float(mean_absolute_percentage_error(revenue,y_pred)*100),2),
            "n_bootstrap":n_boot,"n_periods":T,
            "warning":"OLS fallback — no Bayesian uncertainty. CIs are bootstrap approximations."},
        "fitted_values":y_pred.tolist(),"actual_values":revenue.tolist(),
        "channels":channels,"periods":[str(p) for p in data["periods"]]}

def fit_mle_mmm(data):
    """MLE fallback using scipy.optimize. Intermediate between Bayesian and OLS."""
    from scipy.optimize import minimize as sp_minimize
    revenue=data["revenue"]; channels=data["channels"]; n_ch=len(channels); T=data["n_periods"]
    trend=data["trend"]/(T+1); sin_s=np.sin(2*np.pi*data["month_nums"]/12); cos_s=np.cos(2*np.pi*data["month_nums"]/12)
    spend_raw=np.column_stack([data["spend_matrix"][ch] for ch in channels])
    spend_scales=spend_raw.max(axis=0)+1e-10; spend_normed=spend_raw/spend_scales
    # Warm start from OLS
    from numpy.linalg import lstsq
    _X=np.column_stack([np.ones(T),trend,spend_normed,sin_s,cos_s])
    _c,_,_,_=lstsq(_X,revenue,rcond=None)
    def neg_ll(p):
        bl=p[0]; tc=p[1]; gs=p[2]; gc=p[3]; ls=p[4]
        betas=np.abs(p[5:5+n_ch]); decays=1/(1+np.exp(-p[5+n_ch:5+2*n_ch])); hs=np.exp(p[5+2*n_ch:5+3*n_ch])
        mu=bl+tc*trend+gs*sin_s+gc*cos_s
        for c in range(n_ch):
            ad=geometric_adstock(spend_normed[:,c],decays[c]); mu=mu+betas[c]*hill_saturation(ad,hs[c])*spend_scales[c]
        sig=np.exp(ls); res=revenue-mu
        return 0.5*T*np.log(2*np.pi)+T*np.log(sig)+0.5*np.sum(res**2)/sig**2+0.001*np.sum(betas**2)*T
    x0=np.zeros(5+3*n_ch); x0[0]=_c[0]; x0[1]=_c[1]; x0[2]=_c[-2]; x0[3]=_c[-1]
    x0[4]=np.log(np.std(revenue-_X@_c)+1e-10); x0[5:5+n_ch]=np.abs(_c[2:2+n_ch])*0.5; x0[5+2*n_ch:5+3*n_ch]=np.log(0.5)
    best_res,best_nll=None,np.inf
    for r in range(5):
        xr=x0.copy()+(np.random.randn(len(x0))*0.2 if r>0 else 0)
        try:
            res=sp_minimize(neg_ll,xr,method="L-BFGS-B",options={"maxiter":2000})
            if res.fun<best_nll: best_nll=res.fun; best_res=res
        except: pass
    if best_res is None: raise ValueError("MLE failed to converge")
    p=best_res.x; betas=np.abs(p[5:5+n_ch]); decays=1/(1+np.exp(-p[5+n_ch:5+2*n_ch])); hs_vals=np.exp(p[5+2*n_ch:5+3*n_ch])
    y_pred=p[0]+p[1]*trend+p[2]*sin_s+p[3]*cos_s
    for c in range(n_ch):
        ad=geometric_adstock(spend_normed[:,c],decays[c]); y_pred+=betas[c]*hill_saturation(ad,hs_vals[c])*spend_scales[c]
    contributions={}; total_media=0
    for c,ch in enumerate(channels):
        spend=data["spend_matrix"][ch]; ad=geometric_adstock(spend/spend_scales[c],decays[c])
        sat=hill_saturation(ad,hs_vals[c]); cts=betas[c]*sat*spend_scales[c]; ct=max(0,float(cts.sum())); total_media+=ct
        contributions[ch]={"contribution":round(ct,0),"beta_mean":round(float(betas[c]),4),
            "decay_mean":round(float(decays[c]),3),"half_saturation":round(float(hs_vals[c]),4),
            "spend":round(float(spend.sum()),0),"adstock_type":"geometric"}
    total_rev=float(revenue.sum()); bl=max(0,total_rev-total_media)
    for ch in channels:
        cc=contributions[ch]; cc["contribution_pct"]=round(cc["contribution"]/max(total_rev,1)*100,1)
        cc["mmm_roas"]=round(cc["contribution"]/max(cc["spend"],1),2)
        cc["confidence"]="Medium"
    return {"method":"mle_scipy","contributions":contributions,
        "baseline_contribution":round(bl,0),"baseline_pct":round(bl/max(total_rev,1)*100,1),
        "total_revenue":round(total_rev,0),
        "model_diagnostics":{"r_squared":round(float(r2_score(revenue,y_pred)),4),
            "mape":round(float(mean_absolute_percentage_error(revenue,y_pred)*100),2),
            "converged":best_res.success,"n_restarts":5,"n_periods":T,
            "note":"MLE with L2 regularization. Intermediate between Bayesian and OLS."},
        "fitted_values":y_pred.tolist(),"actual_values":revenue.tolist(),
        "channels":channels,"periods":[str(p) for p in data["periods"]]}

def run_mmm(df, method="auto", n_draws=1000):
    """Public API: Bayesian → MLE → OLS fallback chain."""
    data = prepare_mmm_data(df)
    if data["n_periods"]<6: logger.warning(f"Only {data['n_periods']} periods — MMM needs 12+ for reliability")
    warnings_list = []
    T = data["n_periods"]
    if T<12: warnings_list.append(f"Only {T} periods. MMM needs 12+ for reliability.")
    elif T<24: warnings_list.append(f"{T} periods. Curves may overfit. 24+ recommended.")
    elif T<36: warnings_list.append(f"{T} periods. OLS/MLE solid. Bayesian needs 36+.")
    result = None
    if method=="auto":
        if T>=24:
            try:
                result = fit_bayesian_mmm(data, n_draws=n_draws)
                logger.info(f"Bayesian MMM: R²={result['model_diagnostics']['r_squared']:.3f}")
            except Exception as e:
                logger.warning(f"Bayesian failed ({e}), trying MLE")
        if result is None:
            try:
                result = fit_mle_mmm(data)
                r2 = result['model_diagnostics']['r_squared']
                if r2 < 0:
                    logger.warning(f"MLE R²={r2:.3f} — negative, discarding. Falling back to OLS.")
                    result = None
                else:
                    logger.info(f"MLE MMM: R²={r2:.3f}")
            except Exception as e:
                logger.warning(f"MLE failed ({e}), OLS fallback")
        if result is None:
            result = fit_ols_mmm(data)
            logger.info(f"OLS MMM: R²={result['model_diagnostics']['r_squared']:.3f}")
    elif method=="bayesian": result = _finalize(fit_bayesian_mmm(data, n_draws=n_draws))
    elif method=="mle": result = _finalize(fit_mle_mmm(data))
    elif method=="ols": result = _finalize(fit_ols_mmm(data))
    else: raise ValueError(f"Unknown method: {method}")
    result["data_warnings"] = warnings_list
    # Adstock selection per channel
    adstock_sel = {}
    for ch in data["channels"]:
        at,ap,ac = select_best_adstock(data["spend_matrix"][ch], data["revenue"])
        adstock_sel[ch] = {"best_type":at,"params":ap,"correlation":ac}
    result["adstock_selection"] = adstock_sel
    return _finalize(result)

def _finalize(r):
    if "contributions" not in r: return r
    total_rev = r.get("total_revenue", 1)
    # Normalize: if total media > total revenue, scale proportionally
    total_media = sum(c["contribution"] for c in r["contributions"].values())
    if total_media > total_rev * 0.95 and total_rev > 0:
        # Cap media at 70% of revenue (30% baseline minimum for realistic MMM)
        target_media = total_rev * 0.70
        scale = target_media / max(total_media, 1)
        for ch, cc in r["contributions"].items():
            cc["contribution"] = round(cc["contribution"] * scale, 0)
            cc["contribution_pct"] = round(cc["contribution"] / max(total_rev, 1) * 100, 1)
            cc["mmm_roas"] = round(cc["contribution"] / max(cc["spend"], 1), 2)
            cc["_normalized"] = True
        r["baseline_contribution"] = round(total_rev - sum(c["contribution"] for c in r["contributions"].values()), 0)
        r["baseline_pct"] = round(r["baseline_contribution"] / max(total_rev, 1) * 100, 1)
        if "model_diagnostics" in r:
            r["model_diagnostics"]["contribution_normalized"] = True
            r["model_diagnostics"]["raw_media_pct"] = round(total_media / max(total_rev, 1) * 100, 1)
    # Incremental ROAS (marginal return at current spend)
    inc_roas = {}
    for ch, cc in r["contributions"].items():
        beta = cc.get("beta_mean", 0)
        hs = cc.get("half_saturation", 0.5)
        spend = cc.get("spend", 0)
        decay = cc.get("decay_mean", 0.5)
        if spend > 0 and beta > 0:
            avg_monthly = spend / 12
            # Compute adstocked spend at current level
            ad_cur = avg_monthly / (1 - decay + 1e-10)  # steady-state adstock
            sat_cur = hill_saturation(np.array([ad_cur]), max(hs, 1e-6))[0]
            # +10% spend
            ad_plus = (avg_monthly * 1.1) / (1 - decay + 1e-10)
            sat_plus = hill_saturation(np.array([ad_plus]), max(hs, 1e-6))[0]
            # Incremental contribution for +10% spend
            contrib_per_period = cc["contribution"] / 12
            if sat_cur > 0:
                inc_rev = contrib_per_period * (sat_plus - sat_cur) / sat_cur * 12
            else:
                inc_rev = 0
            inc_spend = avg_monthly * 0.1 * 12
            inc_roas[ch] = {
                "incremental_roas": round(inc_rev / max(inc_spend, 1), 2),
                "saturation_pct": round(sat_cur * 100, 1),
                "current_spend": round(spend, 0),
                "headroom": "High" if sat_cur < 0.4 else ("Medium" if sat_cur < 0.7 else "Low"),
            }
        else:
            inc_roas[ch] = {"incremental_roas": 0, "saturation_pct": 0, "headroom": "N/A"}
    r["incremental_roas"] = inc_roas
    # Ranked
    sc = sorted(r["contributions"].items(), key=lambda x: x[1]["contribution"], reverse=True)
    r["ranked_contributions"] = [{"rank":i+1,"channel":ch,**info} for i,(ch,info) in enumerate(sc)]
    return r
