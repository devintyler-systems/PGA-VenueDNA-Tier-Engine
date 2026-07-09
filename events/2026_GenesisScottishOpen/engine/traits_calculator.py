"""
VenueDNA — GSO 2026
traits_calculator.py

Bayesian feedback loop: inspects output/cumulative_learning.json from the
previous completed round and scales validated trait weights by 1.25x before
multi-horizon score proxy computation.

Chronological isolation (target_round):
  load_adjusted_weights() requires an explicit target_round argument. A trait's
  validated status is only applied if the validation was recorded in a round
  strictly less than target_round. This prevents retrospective rebuilds from
  absorbing signals that hadn't yet occurred at the target horizon — e.g., a
  Round 1 rebuild will never see Round 2 validations.

Normalization protocol — orthogonal isolation:
  When a validated sub-driver trait is boosted, its covariance-linked parent
  traits are locked at baseline and excluded from the scaling pool. Only traits
  with zero shared shot-link data (verified orthogonal) absorb the required
  down-scale. This prevents inflating approach_150_200 while simultaneously
  penalizing sg_app_overall, which draws from the same underlying SG:APP data.

  Post-normalization: a hard assertion enforces sum == 1.0000. Any floating-
  point epsilon residual is corrected against the lowest-weighted orthogonal
  trait so the invariant is always exact.

Falls back silently to BASE_WEIGHTS if the ledger is missing, unreadable, or
no rounds have been completed (rounds_completed == 0).
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CUMULATIVE_PATH = ROOT / "output" / "cumulative_learning.json"

# Canonical venue weight matrix — mirrors score_engine_v2.py EVENT_META.
# Keys must exactly match the trait_weight_matrix exported by the score engine.
BASE_WEIGHTS: dict[str, float] = {
    "approach_150_200":  0.30,
    "sg_app_overall":    0.15,
    "sg_ott_positional": 0.20,
    "driving_accuracy":  0.12,
    "sg_putt":           0.13,
    "sg_arg_short_game": 0.10,
}

# Maps cumulative_signals keys (trait_audit naming) → BASE_WEIGHTS keys.
_AUDIT_KEY_ALIAS: dict[str, str] = {
    "app_150_200": "approach_150_200",
}

# Covariance family map: for each trait, the set of BASE_WEIGHTS traits that
# share the same underlying shot-link data dimension. When a trait is validated,
# every entry in its partner set is locked at its baseline value and excluded
# from the orthogonal scaling pool.
#
# Defined pairs (bidirectional):
#   approach_150_200 <-> sg_app_overall  (both draw from SG:APP shot-link)
#   sg_ott_positional <-> ott_distance   (future alias; ott_distance not yet in matrix)
_COVARIANCE_PARTNERS: dict[str, frozenset[str]] = {
    "approach_150_200":  frozenset({"sg_app_overall"}),
    "sg_app_overall":    frozenset({"approach_150_200"}),
    "sg_ott_positional": frozenset(),   # standalone; no sub-driver in matrix yet
    "driving_accuracy":  frozenset(),
    "sg_putt":           frozenset(),
    "sg_arg_short_game": frozenset(),
}

_VALIDATED_SCALAR = 1.25
_SUM_TOLERANCE    = 1e-6   # hard assertion gate
_EPSILON_GUARD    = 1e-9   # residual considered exact-zero below this


def load_adjusted_weights(target_round: int) -> dict[str, float]:
    """
    Return a venue weight dict adjusted for traits validated **before**
    target_round.  Only rounds_observed entries with round < target_round
    are eligible — validations at or after the active round are ignored,
    preventing retrospective back-propagation leaks during rebuilds.

    Normalization guarantee: sum(returned weights) == 1.0000 exactly
    (epsilon residual corrected against the lowest-weighted orthogonal trait).
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

    # ── Step 0: chronological gate + alias resolution ────────────────────────────
    # A trait is only promoted if its rounds_observed list contains at least one
    # entry with signal == 'validated' AND round < target_round.  Validations
    # recorded in the current or any future round are treated as baseline.
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

    weights = dict(BASE_WEIGHTS)

    # ── Step 1: boost validated traits by the scalar multiplier ─────────────────
    boost_mass = 0.0
    for k in validated_weight_keys:
        delta      = weights[k] * (_VALIDATED_SCALAR - 1.0)
        weights[k] = round(weights[k] * _VALIDATED_SCALAR, 6)
        boost_mass += delta

    # ── Step 2: orthogonal isolation — lock covariance partners ─────────────────
    # Build the locked set: traits that share shot-link data with any validated
    # trait. These stay pinned at their BASE_WEIGHTS values and are excluded from
    # the scaling pool, preventing covariance corruption.
    locked_keys: set[str] = set()
    for vk in validated_weight_keys:
        locked_keys.update(_COVARIANCE_PARTNERS.get(vk, frozenset()))

    # Orthogonal pool: neither validated (already boosted) nor locked (pinned).
    orthogonal = [
        k for k in weights
        if k not in validated_weight_keys and k not in locked_keys
    ]
    orthogonal_sum = sum(weights[k] for k in orthogonal)

    if orthogonal_sum > 0.0 and boost_mass > 0.0:
        scale = (orthogonal_sum - boost_mass) / orthogonal_sum
        for k in orthogonal:
            weights[k] = round(weights[k] * scale, 6)

    # ── Step 3: hard sum assertion + epsilon correction ──────────────────────────
    # Floating-point rounding in the per-trait round() calls can leave a residual
    # of a few ULPs. Correct it against the lowest-weighted orthogonal trait so
    # the invariant sum == 1.0000 is always exact.
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
    """Return a one-line summary of the active weight profile for logging."""
    total   = sum(weights.values())
    changed = {k: v for k, v in weights.items() if abs(v - BASE_WEIGHTS.get(k, 0)) > 1e-9}
    if not changed:
        return f"Baseline weights (sum={total:.4f})"
    parts = [
        f"{k}={v:.4f}(+)" if v > BASE_WEIGHTS.get(k, 0) else f"{k}={v:.4f}(-)"
        for k, v in changed.items()
    ]
    return f"Bayesian-adjusted (sum={total:.4f}): {', '.join(parts)}"
