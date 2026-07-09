"""
VenueDNA — Live Latent Model
latent_model.py

Step 2: Z-score normalisation of modulated latent vectors.
Step 3: Tempered softmax translation to Win / Top 5 / Top 10 / Top 20 probabilities.
"""

import math

# Temperature per probability tier.  Lower T → sharper winner concentration;
# higher T → broader, more distributed probability mass.
_TEMPERATURE: dict[str, float] = {
    "win":   0.30,
    "top5":  0.55,
    "top10": 0.75,
    "top20": 1.10,
}

# Hard probability ceilings — no single player may exceed these values.
_CEILING: dict[str, float] = {
    "win":   40.0,
    "top5":  90.0,
    "top10": 98.0,
    "top20": 99.5,
}


# ── Step 2: Z-score normalisation ────────────────────────────────────────────

def zscore_normalize(values: list[float]) -> list[float]:
    """Normalise a latent vector to zero mean and unit variance."""
    n = len(values)
    if n == 0:
        return []
    mu = sum(values) / n
    variance = sum((v - mu) ** 2 for v in values) / n
    sigma = math.sqrt(variance) if variance > 0.0 else 1.0
    return [(v - mu) / sigma for v in values]


# ── Step 3: Tempered softmax ──────────────────────────────────────────────────

def _softmax(scaled: list[float]) -> list[float]:
    """Numerically stable softmax returning percentage probabilities."""
    peak = max(scaled)
    exps = [math.exp(s - peak) for s in scaled]
    total = sum(exps)
    return [(e / total) * 100.0 for e in exps]


def tempered_softmax_probs(z_scores: list[float]) -> list[dict]:
    """
    Run tempered softmax at each probability tier.
    Returns one dict per player: win_pct, top5_pct, top10_pct, top20_pct.
    """
    tier_probs: dict[str, list[float]] = {}
    for tier, temp in _TEMPERATURE.items():
        tier_probs[tier] = _softmax([z / temp for z in z_scores])

    results = []
    for i in range(len(z_scores)):
        results.append({
            "win_pct":   round(min(tier_probs["win"][i],   _CEILING["win"]),   4),
            "top5_pct":  round(min(tier_probs["top5"][i],  _CEILING["top5"]),  4),
            "top10_pct": round(min(tier_probs["top10"][i], _CEILING["top10"]), 4),
            "top20_pct": round(min(tier_probs["top20"][i], _CEILING["top20"]), 4),
        })
    return results


# ── Post-softmax monotonicity guard ──────────────────────────────────────────

def enforce_monotonicity(p: dict) -> dict:
    """
    Hard clamp: P(Top20) >= P(Top10) >= P(Top5) >= P(Win).
    Any boundary violation forces the lower-tier value up to match the
    higher-tier boundary, preserving the stricter constraint.
    """
    win   = p["win_pct"]
    top5  = max(p["top5_pct"],  win)
    top10 = max(p["top10_pct"], top5)
    top20 = max(p["top20_pct"], top10)
    return {
        "win_pct":   round(win,   4),
        "top5_pct":  round(top5,  4),
        "top10_pct": round(top10, 4),
        "top20_pct": round(top20, 4),
    }


# ── Primary entry point ───────────────────────────────────────────────────────

def live_modulate(
    baselines: list[float],
    sg_tots:   list[float],
    gamma:     float,
) -> tuple[list[float], list[float], list[dict]]:
    """
    Full modulation pipeline: V_p(t) → Z-score (Step 2) → tempered softmax (Step 3).

    Formula: V_p(t) = V_p_baseline + gamma * (sg_tot - field_average_sg_tot)

    Args:
        baselines: Pre-tournament VTS baseline per player (V_p_baseline).
        sg_tots:   Live cumulative SG:Total per player for this round.
        gamma:     Performance capitalisation weight (0.35 × rounds completed).

    Returns:
        (modulated_values, z_scores, prob_dicts)
    """
    if not baselines:
        return [], [], []

    n = len(baselines)
    field_avg_sg = sum(sg_tots) / n
    modulated = [
        baselines[i] + gamma * (sg_tots[i] - field_avg_sg)
        for i in range(n)
    ]
    z_scores = zscore_normalize(modulated)
    prob_dicts = tempered_softmax_probs(z_scores)
    return modulated, z_scores, prob_dicts
