"""Model/observation and case-comparison statistics."""
from __future__ import annotations
import numpy as np

def bias(model, observation, *, axis=None):
    return np.nanmean(np.asarray(model)-np.asarray(observation), axis=axis)

def mae(model, observation, *, axis=None):
    return np.nanmean(np.abs(np.asarray(model)-np.asarray(observation)), axis=axis)

def rmse(model, observation, *, axis=None):
    return np.sqrt(np.nanmean((np.asarray(model)-np.asarray(observation))**2, axis=axis))

def circular_error(model_direction, observed_direction):
    return (np.asarray(model_direction)-np.asarray(observed_direction)+180.0) % 360.0 - 180.0

def circular_mae(model_direction, observed_direction, *, axis=None):
    return np.nanmean(np.abs(circular_error(model_direction, observed_direction)), axis=axis)

def normalized_error(model, observation, *, axis=None):
    return rmse(model, observation, axis=axis) / np.nanmean(np.abs(observation), axis=axis)

def kantorovich_distance(first, second):
    """One-dimensional Earth mover distance for equally weighted samples."""
    a, b = np.sort(np.asarray(first, float).ravel()), np.sort(np.asarray(second, float).ravel())
    quantiles = np.linspace(0, 1, max(a.size, b.size))
    return np.mean(np.abs(np.quantile(a, quantiles)-np.quantile(b, quantiles)))

def correlation(model, observation, *, axis=None):
    a, b = np.asarray(model, float), np.asarray(observation, float)
    if axis is None:
        av,bv=a.ravel(),b.ravel(); am,bm=av-av.mean(),bv-bv.mean(); denominator=np.sqrt(np.sum(am**2)*np.sum(bm**2))
        return np.nan if denominator==0 else np.sum(am*bm)/denominator
    am, bm = np.nanmean(a, axis=axis, keepdims=True), np.nanmean(b, axis=axis, keepdims=True)
    numerator = np.nansum((a-am)*(b-bm), axis=axis)
    return numerator/np.sqrt(np.nansum((a-am)**2, axis=axis)*np.nansum((b-bm)**2, axis=axis))

def standard_error(values, *, axis=0):
    values = np.asarray(values, float)
    return np.nanstd(values, axis=axis, ddof=1)/np.sqrt(np.sum(np.isfinite(values), axis=axis))

def comparison_summary(model, observation):
    return {"bias": float(bias(model, observation)), "mae": float(mae(model, observation)), "rmse": float(rmse(model, observation)), "correlation": float(correlation(model, observation))}

def cluster_profiles(profiles, clusters, *, seed=None, max_iterations=100):
    """Cluster vertical profiles with deterministic NumPy k-means."""
    values=np.asarray(profiles,float)
    if values.ndim!=2 or not 1<=clusters<=values.shape[0]: raise ValueError("profiles must be 2-D and clusters valid")
    rng=np.random.default_rng(seed); centers=values[rng.choice(values.shape[0],clusters,replace=False)].copy()
    for _ in range(max_iterations):
        labels=np.argmin(((values[:,None,:]-centers[None,:,:])**2).sum(axis=2),axis=1)
        updated=np.vstack([values[labels==i].mean(axis=0) if np.any(labels==i) else centers[i] for i in range(clusters)])
        if np.allclose(updated,centers): break
        centers=updated
    return labels,centers

def spatial_scores(model, observation):
    """Return scalar statistics plus per-cell absolute and squared errors."""
    m,o=np.asarray(model,float),np.asarray(observation,float)
    if m.shape!=o.shape: raise ValueError("model and observation fields must have the same shape")
    return {**comparison_summary(m,o),"absolute_error":np.abs(m-o),"squared_error":(m-o)**2}

def rank_cases(cases, observation, *, metric="rmse"):
    functions={"rmse":rmse,"mae":mae,"bias":lambda a,b:abs(bias(a,b))}
    if metric not in functions: raise ValueError("metric must be rmse, mae, or bias")
    return sorted(((name,float(functions[metric](values,observation))) for name,values in cases.items()),key=lambda item:item[1])
