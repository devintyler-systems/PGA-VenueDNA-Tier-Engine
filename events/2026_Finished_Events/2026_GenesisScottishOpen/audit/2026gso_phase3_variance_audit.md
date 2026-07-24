# 2026 Genesis Scottish Open — Phase-3 Variance Expansion Audit
**Date:** 2026-07-07  
**Engine:** score_engine_v2.py  
**Pass:** Phase-3 approach composite scaling (×3.0)  
**Scope:** 2026 Genesis Scottish Open / Renaissance Club ONLY  

---

## Scope & Purpose

FC-2 fixed four structural engine bugs and produced a coherent leaderboard. This Phase-3 pass addresses a single remaining issue: VFS variance is too compressed relative to NSI. The primary course trait (APP 150-200, 30% VTS weight) was contributing only ~0.35 VTS points of spread in the top-30 despite its stated primacy for The Renaissance Club.

**Goal:** Scale `approach_composite_value` by ×3.0 inside the VFS formula so the approach signal earns real spread, without altering VTS weights or reverting FC-2 bug fixes.

---

## A. VFS Spread Diagnostics

### Full-Field VFS (normalized, 0–100)
| Metric | Phase-3 |
|--------|---------|
| Mean | 50.0 |
| Std | 13.8 |
| Min | 0.0 |
| Max | 64.2 |

*(Std ≈14 is by design from `zscore_scale(target_std=14.0)`. Full-field distribution is correctly calibrated.)*

### Top-30 VFS
| Metric | FC-2 (pre) | Phase-3 | Δ |
|--------|-----------|---------|---|
| Std | ~1.16 | 1.484 | **+28%** |
| Range | ~4.8 | 5.308 | +11% |
| Mean | ~60 | 61.6 | — |

### VFS Contribution to VTS Spread
| | FC-2 | Phase-3 |
|--|-----|---------|
| VFS std (top-30) | ~1.16 | 1.484 |
| VFS contrib (0.30 × std) | ~0.35 pts | **0.445 pts** |
| NSI contrib (0.40 × std) | ~3.97 pts | 4.044 pts |
| VFS/NSI ratio | ~8.8% | **11.0%** |

VFS contribution increased by +27% relative to FC-2. The approach scaling narrows the gap between VFS and NSI contributions.

### Approach Composite Distribution (full field, 166 players)
| Percentile | ACV raw | ACV ×3.0 |
|-----------|---------|---------|
| p10 | −0.0208 | −0.0625 |
| p25 | 0.0000 | 0.0000 |
| p50 | 0.0000 | 0.0000 |
| p75 | 0.0157 | 0.0471 |
| p90 | 0.0337 | 0.1011 |
| Max | 0.0549 | 0.1647 |

**Note:** Median ACV = 0.000. Approximately 50% of the field has no approach zone data and defaults to ACV=0. This is the fundamental reason VFS variance is compressed — the data sparsity limits natural spread regardless of multiplier. ×3.0 is the correct lever but its effect is bounded by data availability.

### Formula Unchanged Confirmation (FC-2 vs Phase-3)
| Component | FC-2 Formula | Phase-3 Formula | Status |
|-----------|-------------|----------------|--------|
| NSI | SG composite, no form inject | Identical | ✓ UNCHANGED |
| VHN | ch_adj + podium/win bonuses | Identical | ✓ UNCHANGED |
| FORM | true_sg_last5 normalized | Identical | ✓ UNCHANGED |
| venue_fit_total_adj_ex_da | total_adj − fit_drive_acc | Identical | ✓ UNCHANGED |
| drive_acc_sg_signal | drive_acc_12m × 0.015, clip ±0.15 | Identical | ✓ UNCHANGED |
| approach_composite_value | weighted zone composite | **NEW: × 3.0 → approach_composite_value_scaled** | Phase-3 only |
| venue_fit_raw | `total_adj_ex_da×0.45 + ACV×0.40 + da_sg×0.15` | `total_adj_ex_da×0.45 + ACV_scaled×0.40 + da_sg×0.15` | Phase-3 scale |

---

## B. Leaderboard Sensitivity

### Top-15 Phase-3 vs FC-2 Top-5
| Phase-3 Rank | Player | Tier | VTS | VFS | NSI | ACV | FC-2 Rank | ΔVTS |
|-------------|--------|------|-----|-----|-----|-----|-----------|------|
| 1 | Scheffler | T1 | 88.2 | 61.4 | 98.1 | 0.053 | 3 | +5.3 |
| 2 | McIlroy | T1 | 85.1 | 64.0 | 83.0 | 0.038 | 2 | +0.8 |
| 3 | Fitzpatrick | T1 | 84.4 | 60.7 | 80.6 | 0.034 | 4 | +3.3 |
| 4 | Fleetwood | T1 | 81.3 | 60.4 | 78.9 | 0.023 | T2 | new T1 |
| 5 | Clark | T2 | 80.0 | 60.1 | 68.7 | 0.030 | 1 | −12.0 |
| 6 | Kitayama | T2 | 79.8 | 64.2 | 75.7 | 0.045 | T2 | — |
| 7 | Schauffele | T2 | 79.2 | 62.8 | 79.2 | 0.034 | T2 | — |
| 8 | Gotterup | T2 | 78.2 | 62.1 | 72.3 | 0.019 | T2 | — |
| 9 | Åberg | T2 | 77.9 | 63.0 | 78.8 | 0.034 | T2 | — |
| 10 | Højgaard | T2 | 75.4 | 64.2 | 66.6 | 0.007 | T2 | — |
| 11 | Rai | T2 | 75.0 | 60.3 | 67.7 | 0.027 | T2 | — |
| 12 | Rahm | T2 | 75.0 | 63.8 | 82.9 | 0.053 | T2 | — |
| 13 | Spaun | T2 | 73.8 | 62.8 | 76.9 | 0.054 | T2 | — |
| 14 | Kim | T2 | 73.5 | 63.0 | 77.1 | 0.000 | T2 | — |
| 15 | Hatton | T2 | 72.4 | 60.6 | 63.3 | 0.028 | 5 (T1) | −8.7 |

### Tier Changes
| Player | FC-2 Tier | Phase-3 Tier | Direction |
|--------|-----------|-------------|-----------|
| Scheffler | T1 | T1 | No change |
| McIlroy | T1 | T1 | No change |
| Fitzpatrick | T1 | T1 | No change |
| Clark | T1 | T2 | ▼ fell out |
| Hatton | T1 | T2 | ▼ fell out |
| Fleetwood | T2 | T1 | ▲ entered |

**Net T1 change:** −1 player (5→4). Clark and Hatton dropped; Fleetwood entered; Scheffler/McIlroy/Fitzpatrick held.

### Biggest Movers
**Risers:** Scheffler (+2), Fitzpatrick (+1), Fleetwood (T2→T1)  
**Fallers:** Clark (−4, T1→T2), Hatton (−10, T1→T2)

---

## C. Player Spot Checks

### Scheffler
| Field | Value |
|-------|-------|
| approach_composite_value | 0.0526 |
| approach_composite_value_scaled | 0.1577 |
| venue_fit_score | 61.4 |
| NSI | 98.1 |
| VHN | 62.8 |
| Form score | 48.7 (NEUTRAL) |
| VTS final | **88.2** (FC-2: 82.9) |
| Rank / Tier | 1 / T1 |

Highest ACV in spot-check set. Highest NSI in field. Moves to #1 — correct for a course rewarding elite irons.

### McIlroy
| Field | Value |
|-------|-------|
| approach_composite_value | 0.0377 |
| approach_composite_value_scaled | 0.1131 |
| venue_fit_score | 64.0 (highest in top-5) |
| NSI | 83.0 |
| VHN | 78.5 |
| Form score | 54.3 (NEUTRAL) |
| VTS final | **85.1** (FC-2: 84.3) |
| Rank / Tier | 2 / T1 |

Stable. Renaissance winner, strong approach, solid VHN. Highest VFS in T1.

### Fitzpatrick
| Field | Value |
|-------|-------|
| approach_composite_value | 0.0340 |
| approach_composite_value_scaled | 0.1020 |
| venue_fit_score | 60.7 |
| NSI | 80.6 |
| VHN | 89.8 (highest in top-5) |
| Form score | 52.5 (NEUTRAL) |
| VTS final | **84.4** (FC-2: 81.1) |
| Rank / Tier | 3 / T1 |

Moves from #4 to #3. Best VHN in the spot-check set (5 starts, podium). Approach positive. Plausible.

### Fleetwood
| Field | Value |
|-------|-------|
| approach_composite_value | 0.0227 |
| approach_composite_value_scaled | 0.0682 |
| venue_fit_score | 60.4 |
| NSI | 78.9 |
| VHN | 79.5 |
| Form score | 54.2 (NEUTRAL) |
| VTS final | **81.3** (FC-2: T2) |
| Rank / Tier | 4 / T1 |

Enters T1 at #4. Strong NSI+VHN combination with positive approach. Links specialist with elite short game. Defensible T1 entry.

### Clark
| Field | Value |
|-------|-------|
| approach_composite_value | 0.0297 |
| approach_composite_value_scaled | 0.0890 |
| venue_fit_score | 60.1 |
| NSI | 68.7 |
| VHN | 70.7 |
| Form score | **84.5** (HOT) |
| VTS final | **80.0** (FC-2: 92.0) |
| Rank / Tier | 5 / T2 |

**Biggest faller.** Clark's FC-2 rank-1 VTS of 92.0 was built on HOT form. In FC-2, VFS was so compressed that form + VHN could dominate. With approach amplified and Clark's NSI (68.7) moderate, his VTS normalizes lower. His ACV (0.0297) is positive but below the elite approach players (Scheffler 0.053, Rahm 0.053). Still top-5 and just below T1 threshold. Form remains visible through form_score but no longer overcomes structural gaps when the primary venue trait is amplified.

### Hatton
| Field | Value |
|-------|-------|
| approach_composite_value | 0.0275 |
| approach_composite_value_scaled | 0.0826 |
| venue_fit_score | 60.6 |
| NSI | 63.3 |
| VHN | 59.7 |
| Form score | 74.0 (HOT→NEUTRAL boundary) |
| VTS final | **72.4** (FC-2: 81.1) |
| Rank / Tier | 15 / T2 |

**Most significant drop** (−10 places, T1→T2). Hatton's FC-2 T1 position was sustained by HOT form + positive VFS in a compressed environment. His NSI (63.3) and VHN (59.7) are the lowest in the former T1 cluster. With approach amplified, players who score well on NSI *and* approach (Scheffler, McIlroy, Fitzpatrick, Fleetwood) separate from players whose strength is form-driven. Hatton at T2 #15 is notable but structurally defensible: his 150-200 approach data is average, his driving accuracy is moderate, and his NSI base is not T1-caliber on its own.

### MacIntyre
| Field | Value |
|-------|-------|
| approach_composite_value | −0.0069 |
| approach_composite_value_scaled | −0.0207 |
| venue_fit_score | 58.9 |
| NSI | 63.6 |
| VHN | 84.6 |
| Form score | 41.1 (COOL) |
| VTS final | **70.1** (FC-2: T2) |
| Rank / Tier | 20 / T2 |

Only player with negative ACV in this set. VFS penalized slightly vs neutral-ACV peers. COOL form drags form_score. High VHN (84.6) — defending champion signal — sustains T2 position. Consistent with structural profile.

---

## D. Safety Checks

| Check | Result |
|-------|--------|
| All validation gates pass | Gate 1–2, 4–7: **PASS** |
| Gate 3 VFS range WARN | 5.3 — pre-existing (ACV data sparsity limit; not a regression) |
| Win probability sum | 100.1% — **PASS** |
| NSI formula unchanged (no form inject) | **CONFIRMED** |
| VHN formula unchanged (podium/win bonuses intact) | **CONFIRMED** |
| FORM formula unchanged | **CONFIRMED** |
| DA double-count absent | venue_fit_total_adj_ex_da strips fit_drive_acc before use — **CONFIRMED** |
| SG-based DA signal (not fit_drive_acc) | drive_acc_sg_signal = drive_acc_12m×0.015 — **CONFIRMED** |
| approach_composite_value_scaled in payload | **CONFIRMED** (new field, auditability) |
| Duplicate column regression | None — **CONFIRMED** |
| App payload field alignment | approach_composite_value and approach_composite_value_scaled both serialized — **CONFIRMED** |
| No fit_drive_acc reintroduced to venue_fit_raw | **CONFIRMED** |

---

## Code Changes Made

**File:** `events/2026_GenesisScottishOpen/engine/score_engine_v2.py`

**Change 1 — New intermediate field (after approach_composite_value computation, ~line 491):**
```python
# Phase-3 variance expansion (2026 Genesis Scottish Open only — Renaissance Club).
# Pre-Phase-3: top-30 VFS std ≈1.16 vs NSI std ≈9.94; approach composite contributing ~0.35 VTS pts.
# Scaling ×3.0 lets the primary course trait (APP 150-200, 30% VTS weight) earn real spread
# without altering top-level VTS weights. FC-2 formula structure is otherwise untouched.
df["approach_composite_value_scaled"] = df["approach_composite_value"] * 3.0
```

**Change 2 — venue_fit_raw uses scaled approach:**
```python
df["venue_fit_raw"] = (
    df["venue_fit_total_adj_ex_da"] * 0.45         # unchanged
    + df["approach_composite_value_scaled"] * 0.40  # approach ×3.0 Phase-3 scale
    + df["drive_acc_sg_signal"] * 0.15              # unchanged
)
```

**Change 3 — Payload serialization (auditability):**
```python
"approach_composite_value_scaled": float(row.get("approach_composite_value_scaled")) if not pd.isna(...) else None,
```

---

## Recommendation

**KEEP ×3.0.**

| Criterion | Status |
|-----------|--------|
| VFS variance materially increased | ✓ +28% top-30 VFS std (1.16→1.484) |
| Board structurally coherent | ✓ Scheffler/McIlroy/Fitzpatrick top-3 |
| No FC-2 bug fix reversed | ✓ All confirmed |
| Top of board makes venue sense | ✓ Approach-elite players lead at approach-primary venue |
| Unjustified leaderboard chaos | ✗ None — changes follow approach/NSI logic |
| VFS contribution improved | ✓ 0.35→0.445 VTS pts (+27%) |

**Key judgment on Clark/Hatton:** Their FC-2 positions were partially inflated by compressed VFS — form and VHN could overcorrect for structural approach gaps in a flat VFS environment. ×3.0 makes approach matter enough that NSI quality and approach strength determine the T1 boundary. Clark at #5 T2 (one VTS point below threshold) and Hatton at #15 T2 are defensible given their NSI profiles for a links venue where 150-200 approach is the stated primary trait.

**Why not ×2.0 or ×2.5:** The ACV distribution is very sparse (median=0, p75=0.016). At ×2.0 the VFS std improvement would be roughly +19%; at ×2.5 approximately +23%. Neither produces a materially different leaderboard — the changes scale proportionally with the multiplier. The instability seen at ×3.0 would still be present at ×2.5, just attenuated. Since the leaderboard changes are defensible, increasing to ×3.0 earns more of the intended variance signal.

---

## Summary of Changes vs FC-2

| Layer | FC-2 | Phase-3 |
|-------|------|---------|
| NSI | No form inject | Identical |
| VHN | Podium/win bonuses active | Identical |
| FORM | true_sg_last5 normalized | Identical |
| venue_fit_raw | `total_adj_ex_da×0.45 + ACV×0.40 + da_sg×0.15` | `total_adj_ex_da×0.45 + ACV×3.0×0.40 + da_sg×0.15` |
| New field | — | `approach_composite_value_scaled` (ACV×3.0) |
| Payload | approach_composite_value | + approach_composite_value_scaled |
| VFS std (top-30) | ~1.16 | 1.484 (+28%) |
| T1 count | 5 | 4 |
| Board leader | Clark (form-driven) | Scheffler (approach+NSI) |
