"""
VenueDNA — The Open Championship 2026 (Royal Troon)
traits_calculator.py

Bayesian feedback loop: inspects output/cumulative_learning.json from the
previous completed round and scales validated trait weights before multi-horizon
score proxy computation.

Royal Troon weight specification (locked):
  sg_ott_positional  20% — positional driving essential on narrow links corridors
  sg_arg_short_game  15% — scrambling from gorse/rough critical to survival rounds
  approach_150_200   25% — mid-iron approach control primary scoring mechanism
  driving_accuracy   15% — tight Troon fairways with gorse carry consequence
  sg_app_overall     12% — covariance partner of approach_150_200 (SG:APP sub-driver)
  sg_putt            13% — firm, running greens reduce putting variance vs typical tour

Defensive 24-month links prior:
  _LINKS_PRIOR_COEFFICIENT dampens the validated scalar to prevent standard-deviation
  compression artifacts when a player's 24-month links history appears low-variance
  (small N + consistent performance → artificially narrow SD → inflated confidence).
  Effective max scalar = _VALIDATED_SCALAR * _LINKS_PRIOR_COEFFICIENT ≈ 1.145.

Chronological isolation (target_round):
  load_adjusted_weights() requires an explicit target_round argument. Validations
  at or after target_round are ignored — prevents retrospective back-propagation.

Normalization guarantee: sum(returned weights) == 1.0000 exactly.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CUMULATIVE_PATH = ROOT / "output" / "cumulative_learning.json"

BASE_WEIGHTS: dict[str, float] = {
    "approach_150_200":  0.25,
    "sg_ott_positional": 0.20,
    "driving_accuracy":  0.15,
    "sg_arg_short_game": 0.15,
    "sg_putt":           0.13,
    "sg_app_overall":    0.12,
}

SG_PROXY_MAP: dict[str, str] = {
    "approach_150_200":  "sg_app",
    "sg_ott_positional": "sg_ott",
    "driving_accuracy":  "sg_ott",
    "sg_arg_short_game": "sg_arg",
    "sg_putt":           "sg_putt",
    "sg_app_overall":    "sg_app",
}

_AUDIT_KEY_ALIAS: dict[str, str] = {
    "app_150_200": "approach_150_200",
}

_COVARIANCE_PARTNERS: dict[str, frozenset[str]] = {
    "approach_150_200":  frozenset({"sg_app_overall"}),
    "sg_app_overall":    frozenset({"approach_150_200"}),
    "sg_ott_positional": frozenset({"driving_accuracy"}),
    "driving_accuracy":  frozenset({"sg_ott_positional"}),
    "sg_arg_short_game": frozenset(),
    "sg_putt":           frozenset(),
}

# Defensive links prior: caps effective Bayesian scalar to prevent SD compression
# when 24-month historical links data shows low variance (artificially high confidence).
_LINKS_PRIOR_WINDOW_MONTHS: int  = 24
_LINKS_PRIOR_COEFFICIENT: float  = 0.82   # caps max boost: 1.40 * 0.82 ≈ 1.148
_VALIDATED_SCALAR: float         = 1.40   # pre-cap scalar (higher than GSO 1.25 to
                                           # compensate — effective cap keeps it safe)
_SUM_TOLERANCE:    float         = 1e-6
_EPSILON_GUARD:    float         = 1e-9


def load_adjusted_weights(target_round: int) -> dict[str, float]:
    """
    Return venue weights adjusted for traits validated before target_round.
    Applies the defensive links prior coefficient to cap the effective scalar,
    preventing standard-deviation compression in 24-month historical data.

    Normalization guarantee: sum(returned weights) == 1.0000 exactly.
    """
    try:
        with open(CUMULATIVE_PATH, encoding="utf-8") as f:
            ledger = json.load(f)
    except (OSError, json.JSONDecodeError):
        return dict(BASE_WEIGHTS)

    if ledger.get("rounds_completed", 0) < 1:
        return dict(BASE_WEIGHTS)

    cumulative_signals: dict = ledger.get("cumulative_signals", {})
    if not cumulative_signals:
        return dict(BASE_WEIGHTS)

    # Chronological gate: only accept validations recorded before target_round.
    validated_weight_keys: set[str] = set()
    for audit_key, signal_entry in cumulative_signals.items():
        if not isinstance(signal_entry, dict):
            continue
        rounds_observed: list = signal_entry.get("rounds_observed", [])
        has_prior_validation = any(
            isinstance(obs, dict)
            and obs.get("signal") == "validated"
            and isinstance(obs.get("round"), int)
            and obs["round"] < target_round
            for obs in rounds_observed
        )
        if not has_prior_validation:
            continue
        weight_key = _AUDIT_KEY_ALIAS.get(audit_key, audit_key)
        if weight_key in BASE_WEIGHTS:
            validated_weight_keys.add(weight_key)

    if not validated_weight_keys:
        return dict(BASE_WEIGHTS)

    # Apply defensive links prior: cap the effective scalar.
    effective_scalar = _VALIDATED_SCALAR * _LINKS_PRIOR_COEFFICIENT

    weights = dict(BASE_WEIGHTS)

    # Step 1: boost validated traits by the effective (capped) scalar.
    boost_mass = 0.0
    for k in validated_weight_keys:
        delta      = weights[k] * (effective_scalar - 1.0)
        weights[k] = round(weights[k] * effective_scalar, 6)
        boost_mass += delta

    # Step 2: lock covariance partners; build orthogonal scaling pool.
    locked_keys: set[str] = set()
    for vk in validated_weight_keys:
        locked_keys.update(_COVARIANCE_PARTNERS.get(vk, frozenset()))

    orthogonal = [
        k for k in weights
        if k not in validated_weight_keys and k not in locked_keys
    ]
    orthogonal_sum = sum(weights[k] for k in orthogonal)

    if orthogonal_sum > 0.0 and boost_mass > 0.0:
        scale = (orthogonal_sum - boost_mass) / orthogonal_sum
        for k in orthogonal:
            weights[k] = round(weights[k] * scale, 6)

    # Step 3: hard sum assertion + epsilon correction.
    total    = sum(weights.values())
    residual = round(1.0 - total, 9)

    if abs(residual) > _EPSILON_GUARD:
        if orthogonal:
            anchor = min(orthogonal, key=lambda k: weights[k])
            weights[anchor] = round(weights[anchor] + residual, 6)

    total_final = sum(weights.values())
    if abs(total_final - 1.0) > _SUM_TOLERANCE:
        raise ArithmeticError(
            f"Weight matrix sum invariant violated: got {total_final:.8f}, expected 1.0"
        )

    return weights


def describe_adjustment(weights: dict[str, float]) -> str:
    """One-line summary of the active weight profile for logging."""
    total   = sum(weights.values())
    changed = {k: v for k, v in weights.items() if abs(v - BASE_WEIGHTS.get(k, 0)) > 1e-9}
    if not changed:
        return f"Baseline weights Royal Troon (sum={total:.4f})"
    parts = [
        f"{k}={v:.4f}(+)" if v > BASE_WEIGHTS.get(k, 0) else f"{k}={v:.4f}(-)"
        for k, v in changed.items()
    ]
    effective_scalar = round(_VALIDATED_SCALAR * _LINKS_PRIOR_COEFFICIENT, 4)
    return (
        f"Bayesian-adjusted Royal Troon "
        f"(sum={total:.4f}, eff_scalar={effective_scalar}): {', '.join(parts)}"
    )
