"""Model/observation and case-comparison statistics."""
from __future__ import annotations
import numpy as np

def _paired(model, observation):
    a,b=np.asarray(model,float),np.asarray(observation,float)
    if a.shape!=b.shape:
        raise ValueError("Paired samples must have identical shapes; collocate/align first")
    valid=np.isfinite(a)&np.isfinite(b)
    return np.where(valid,a,np.nan),np.where(valid,b,np.nan)

def bias(model, observation, *, axis=None):
    """Mean model-minus-observation error over finite paired samples."""
    a,b=_paired(model,observation)
    return np.nanmean(a-b, axis=axis)

def mae(model, observation, *, axis=None):
    """Mean absolute error over finite paired samples; same units as input."""
    a,b=_paired(model,observation)
    return np.nanmean(np.abs(a-b), axis=axis)

def rmse(model, observation, *, axis=None):
    """Root-mean-square error over finite paired samples, not uncertainty."""
    a,b=_paired(model,observation)
    return np.sqrt(np.nanmean((a-b)**2, axis=axis))

def circular_error(model_direction, observed_direction):
    """Wrapped model-minus-observed direction difference in [-180,180) degrees."""
    a,b = _paired(model_direction,observed_direction)
    return (a-b+180.0) % 360.0 - 180.0

def circular_mae(model_direction, observed_direction, *, axis=None):
    """Mean absolute wrapped directional error, in degrees."""
    return np.nanmean(np.abs(circular_error(model_direction, observed_direction)), axis=axis)

def normalized_error(model, observation, *, axis=None):
    """RMSE divided by mean absolute observed value on the SAME valid pairs."""
    a,b=_paired(model,observation)
    scale=np.nanmean(np.abs(b),axis=axis)
    return np.divide(rmse(a,b,axis=axis),scale,out=np.full(np.shape(scale),np.nan),where=scale>0)

def kantorovich_distance(first, second):
    """Exact empirical 1-D Wasserstein-1 distance; equal weights per sample.

    Integrates |F-G| on the union of sample locations, including unequal
    record lengths. See scipy.stats.wasserstein_distance and its CDF identity.
    Non-finite samples are excluded independently (these are distributions,
    not paired observations). Empty distributions raise ValueError.
    """
    a, b = np.sort(np.asarray(first, float).ravel()), np.sort(np.asarray(second, float).ravel())
    a,b=a[np.isfinite(a)],b[np.isfinite(b)]
    if not a.size or not b.size: raise ValueError("Both distributions need finite samples")
    locations=np.sort(np.concatenate([a,b])); widths=np.diff(locations)
    fa=np.searchsorted(a,locations[:-1],side="right")/a.size
    fb=np.searchsorted(b,locations[:-1],side="right")/b.size
    return float(np.sum(np.abs(fa-fb)*widths))

def correlation(model, observation, *, axis=None):
    """Pearson correlation using finite pairs; constants/<2 pairs return NaN."""
    a, b = _paired(model,observation)
    if axis is None:
        a,b=a.ravel(),b.ravel(); axis=0
    am, bm = np.nanmean(a, axis=axis, keepdims=True), np.nanmean(b, axis=axis, keepdims=True)
    numerator = np.nansum((a-am)*(b-bm), axis=axis)
    denominator=np.sqrt(np.nansum((a-am)**2, axis=axis)*np.nansum((b-bm)**2, axis=axis))
    count=np.sum(np.isfinite(a),axis=axis)
    return np.divide(numerator,denominator,out=np.full(np.shape(denominator),np.nan),where=(denominator>0)&(count>=2))

def standard_error(values, *, axis=0):
    """IID sample-mean standard error, s/sqrt(n); NOT autocorrelation corrected."""
    values = np.asarray(values, float)
    return np.nanstd(values, axis=axis, ddof=1)/np.sqrt(np.sum(np.isfinite(values), axis=axis))

def comparison_summary(model, observation):
    """Paired finite-sample deterministic scores; no observation QC is inferred."""
    return {"bias": float(bias(model, observation)), "mae": float(mae(model, observation)), "rmse": float(rmse(model, observation)), "correlation": float(correlation(model, observation))}

def cluster_profiles(profiles, clusters, *, seed=None, max_iterations=100):
    """Cluster vertical profiles with deterministic NumPy k-means."""
    values=np.asarray(profiles,float)
    if values.ndim!=2 or not isinstance(clusters,(int,np.integer)) or not 1<=clusters<=values.shape[0] or not values.shape[1] or not np.isfinite(values).all():
        raise ValueError("profiles must be finite nonempty 2-D arrays and clusters a valid integer")
    if not isinstance(max_iterations,(int,np.integer)) or max_iterations<1:
        raise ValueError("max_iterations must be a positive integer")
    rng=np.random.default_rng(seed); centers=values[rng.choice(values.shape[0],clusters,replace=False)].copy()
    for _ in range(max_iterations):
        labels=np.argmin(((values[:,None,:]-centers[None,:,:])**2).sum(axis=2),axis=1)
        updated=np.vstack([values[labels==i].mean(axis=0) if np.any(labels==i) else centers[i] for i in range(clusters)])
        if np.allclose(updated,centers): break
        centers=updated
    # The iteration limit may stop after centers change; labels must describe
    # the returned centers, not the previous iteration's assignment.
    labels=np.argmin(((values[:,None,:]-centers[None,:,:])**2).sum(axis=2),axis=1)
    return labels,centers

def spatial_scores(model, observation):
    """Return scalar statistics plus per-cell absolute and squared errors."""
    m,o=np.asarray(model,float),np.asarray(observation,float)
    if m.shape!=o.shape: raise ValueError("model and observation fields must have the same shape")
    return {**comparison_summary(m,o),"absolute_error":np.abs(m-o),"squared_error":(m-o)**2}

def rank_cases(cases, observation, *, metric="rmse"):
    """Rank by finite deterministic scores; unavailable cases raise, never rank.

    No uncertainty ranking or observation quality control is inferred.
    """
    functions={"rmse":rmse,"mae":mae,"bias":lambda a,b:abs(bias(a,b))}
    if metric not in functions: raise ValueError("metric must be rmse, mae, or bias")
    scores=[(name,float(functions[metric](values,observation))) for name,values in cases.items()]
    if any(not np.isfinite(score) for _,score in scores):
        raise ValueError("Cannot rank unavailable scores; require finite matched pairs for every case")
    return sorted(scores,key=lambda item:item[1])
