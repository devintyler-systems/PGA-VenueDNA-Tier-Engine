# 2026 Genesis Scottish Open — FC-2 Engine Repair Audit

**Generated:** 2026-07-07  
**Engine:** score_engine_v2.py (FC-2 repair patch)  
**Scope:** Four structural scoring bugs corrected; full field re-scored; pre/post diff documented.

---

## Executive Summary

The pre-repair board was structurally incoherent. Clark ranked #1 (VTS 91.5) despite mediocre SG:OTT (+0.06), below-average driving accuracy (-3.3pp), and modest APP 150-200 (+0.029). Scheffler ranked #3 (VTS 82.1) despite world-#1 SG:APP (+1.15), elite SG:OTT (+0.89), and a T3 podium at Renaissance.

Post-repair: Scheffler #1 (87.6), McIlroy #2 (84.9), Fitzpatrick #3 (84.0). Clark correctly drops to T2 rank #5 (79.8). The board is structurally coherent.

---

## Phase 1 — Bug Fixes Applied

### FC-2-A: NSI form double-count removed

**Bug:** `form_adj_neutral` injected up to +0.30 SG points into `neutral_skill_sg` for HOT-form players. The same form signal then received a second 0.15-weight layer via `form_score`. This double-counted form twice and overrode structural skill differences.

**Pre-repair impact (Clark):** true_sg_vs_baseline=+2.23 → form_adj_neutral=+0.30 (capped) → neutral_skill_sg inflated from 0.358 to 0.658 → NSI 83.6 instead of ~68-70.

**Fix:** `form_adj_neutral` zeroed out. NSI now reflects pure structural skill (weighted SG:APP/OTT/ARG/PUTT composite).

| Player | Pre-NSI | Post-NSI | ΔNSI |
|--------|---------|---------|------|
| Clark | 83.6 | 68.7 | **−14.9** |
| Hatton | 74.3 | 63.3 | **−11.0** |
| Scheffler | 94.8 | 98.2 | +3.4 (field redistribution) |
| McIlroy | 80.7 | 83.0 | +2.3 |

---

### FC-2-B: fit_drive_acc driving-accuracy double-count removed

**Bug:** `venue_fit_total_adj` = sum(short_game + approach + drive_dist + driving_accuracy). The formula then added `fit_drive_acc` (= driving_accuracy component) AGAIN at ×0.15 weight, giving driving accuracy an effective combined weight of 0.55 + 0.15 = **0.70**.

**Fix:** Stripped DA from total_adj before use: `venue_fit_total_adj_ex_da = venue_fit_total_adj − fit_drive_acc`.

---

### FC-2-C: Venue fit CSV driving-accuracy signal replaced

**Bug:** The venue fit CSV's `driving-accuracy` column had inverted values vs actual SG data:

| Player | DA baseline (SG CSV) | fit_drive_acc (venue fit CSV) |
|--------|---------------------|-------------------------------|
| Clark | **−3.3pp below avg** | **+0.07** (positive) |
| McIlroy | −2.8pp below avg | +0.06 (positive) |
| Scheffler | **+5.4pp above avg** | **−0.13** (negative) |

An accurate player (Scheffler +5.4pp) received a penalty; an inaccurate player (Clark −3.3pp) received a bonus. This alone shifted VFS by ~0.14 raw units in Clark's favor.

**Fix:** Replaced with canonical SG-CSV signal: `drive_acc_sg_signal = drive_acc_12m × 0.015` (strokes/round per pp of accuracy, clipped ±0.15). Scheffler now correctly receives a positive accuracy contribution.

**New VFS formula:**
```python
venue_fit_total_adj_ex_da × 0.45   # DA removed; weight reduced from 0.55
+ approach_composite_value × 0.40  # primary Renaissance trait; up from 0.30
+ drive_acc_sg_signal × 0.15       # SG-CSV canonical signal; correct sign
```

---

### FC-2-D: VHN podium/win quality bonuses added

**Bug:** `ch_adjustment` rewards consistency-vs-expected performance, not finish quality. Scheffler's T3 podium (2023) was not credited because a CUT in 2022 pulled his `versus_expected` negative (−0.311). Clark's pattern of T10/T11 scored higher (`versus_expected` = +0.905) than Scheffler's T3.

**Fix:** Explicit podium and venue-win bonuses added, independent of consistency metrics:
- `podium_bonus_vhn` = +0.08 for T2-T5 (best finish without a win)
- `win_bonus_vhn` = +0.12 for venue win
- `ch_adjustment` multiplier: 4.0 → 3.0
- `experience_adjustment` multiplier: 2.0 → 1.5

**VHN changes for key players:**

| Player | Pre-VHN | Post-VHN | Reason |
|--------|---------|---------|--------|
| Matt Fitzpatrick | 86.1 | 89.8 | podium_bonus (T2 in 2021) + strong ch_adj |
| McIlroy | 68.5 | 78.5 | win_bonus (+0.12) + 2025 T2 recency |
| Scheffler | 55.4 | 62.8 | podium_bonus (+0.08 for T3) |
| Clark | 74.3 | 70.7 | ch_adj multiplier reduction |
| Hatton | 62.6 | 59.7 | ch_adj multiplier reduction |

---

## Phase 2 — Pre/Post Diff

### Key Player Decomposition

| Player | Pre-VTS | Post-VTS | ΔVTS | Pre-NSI | Post-NSI | Pre-VFS | Post-VFS | Pre-VHN | Post-VHN | Pre-T | Post-T |
|--------|---------|---------|------|---------|---------|---------|---------|---------|---------|-------|--------|
| **Scottie Scheffler** | 82.1 | **87.6** | **+5.5** | 94.8 | 98.2 | 53.6 | 59.7 | 55.4 | 62.8 | T1 | T1 |
| **Rory McIlroy** | 83.5 | **84.9** | +1.4 | 80.7 | 83.0 | 66.0 | 63.0 | 68.5 | 78.5 | T1 | T1 |
| **Matt Fitzpatrick** | 80.4 | **84.0** | +3.6 | 78.5 | 80.6 | 54.2 | 59.4 | 86.1 | 89.8 | T1 | T1 |
| **Tommy Fleetwood** | 77.0 | **81.3** | +4.3 | 76.9 | 78.9 | 52.3 | 59.9 | 77.7 | 79.5 | T2 | **T1** |
| **Wyndham Clark** | 91.5 | **79.8** | **−11.8** | 83.6 | 68.7 | 62.2 | 59.3 | 74.3 | 70.7 | T1 | **T2** |
| **Tyrrell Hatton** | 80.9 | **72.2** | **−8.7** | 74.3 | 63.3 | 61.9 | 59.9 | 62.6 | 59.7 | T1 | **T2** |

**Clark's −11.8 VTS decomposed:**
- NSI drop (form double-count removed): (83.6→68.7) × 0.40 weight = −5.96 pre-norm
- VFS drop (DA double-count/sign fix): (62.2→59.3) × 0.30 = −0.87 pre-norm
- VHN drop (ch_adj multiplier): (74.3→70.7) × 0.15 = −0.54 pre-norm
- Total pre-norm drop: ~−7.4 → ~−11.8 VTS after zscore amplification

---

### Top-20 Rank Movers

| Pre-Rank | Post-Rank | Δ | Player | Pre-VTS | Post-VTS |
|---------|---------|---|--------|---------|---------|
| 3 | **1** | +2 | Scottie Scheffler | 82.1 | **87.6** |
| 2 | 2 | = | Rory McIlroy | 83.5 | 84.9 |
| 5 | **3** | +2 | Matt Fitzpatrick | 80.4 | **84.0** |
| 8 | **4** | +4 | Tommy Fleetwood | 77.0 | **81.3** |
| **1** | 5 | **−4** | Wyndham Clark | **91.5** | 79.8 |
| 6 | 6 | = | Kurt Kitayama | 78.2 | 79.4 |
| 16 | **7** | +9 | Xander Schauffele | 72.0 | **79.0** |
| 7 | 8 | −1 | Chris Gotterup | 77.5 | 78.2 |
| 11 | **9** | +2 | Ludvig Åberg | 75.1 | 77.7 |
| 9 | 10 | −1 | Nicolai Højgaard | 76.8 | 75.1 |
| 26 | **14** | **+12** | Si Woo Kim | 68.5 | 72.8 |
| 22 | **13** | +9 | J.J. Spaun | 70.3 | 73.1 |
| **4** | 15 | **−11** | Tyrrell Hatton | 80.9 | 72.2 |
| 41 | **20** | **+21** | Robert MacIntyre | 62.3 | 70.5 |
| 24 | **16** | +8 | Patrick Cantlay | 69.4 | 72.0 |

---

### Tier Changes

| Player | Pre-Tier | Post-Tier | Reason |
|--------|---------|---------|--------|
| Tommy Fleetwood | T2 | **T1** | NSI+VHN uplift without form double-count distortion |
| Wyndham Clark | T1 | **T2** | form double-count removed; true NSI ~68 |
| Tyrrell Hatton | T1 | **T2** | form double-count removed; true NSI ~63 |

---

## Phase 3 — Weight Balance Assessment

### Layer Spread in Top-30 (post-repair)

| Layer | Range (top-30) | Std (top-30) | Weight | Effective VTS spread contribution |
|-------|---------------|-------------|--------|----------------------------------|
| **NSI** | 46.6 | 9.94 | 0.40 | ~3.97 VTS pts |
| **VHN** | 51.7 | 16.13 | 0.15 | ~2.42 VTS pts |
| **FORM** | 47.3 | 11.39 | 0.15 | ~1.71 VTS pts |
| **VFS** | **3.9** | **1.16** | **0.30** | **~0.35 VTS pts** |

**Finding:** VFS has the largest assigned weight (0.30) but contributes the least top-30 differentiation (std=1.16 vs NSI std=9.94). Despite carrying 30% of the VTS formula, VFS generates less than 10% of the actual spread between top players.

**Root cause of VFS compression:**
1. `approach_composite_value` operates in strokes-per-shot units (max ≈ +0.10). Across 166 players including 52 with null→0 data, the top-30 approach composites cluster in a narrow +0.03 to +0.06 range.
2. `venue_fit_total_adj_ex_da` values cluster at −0.10 to −0.15 for most elite PGA Tour players — the venue fit model predicts similar fit for all elite players.
3. `drive_acc_sg_signal` range of ±0.15 is small absolute contribution.

### Phase 3 Verdict: Conditional rebalance recommended

**Current weights:** NSI×0.40 + VFS×0.30 + VHN×0.15 + FORM×0.15

**The current leaderboard is structurally correct.** The Phase 1-2 fixes resolved the incoherence. VFS compression is a calibration limitation, not a correctness bug.

**Recommended rebalance (if approved):**

| Layer | Current | Proposed | Rationale |
|-------|---------|---------|-----------|
| NSI | 0.40 | **0.43** | Pure structural skill; broadest discriminating spread |
| VFS | 0.30 | **0.25** | Honest acknowledgment of compression; still venue-doctrine |
| VHN | 0.15 | **0.18** | Strongest post-repair discriminating layer; course history IS a real edge |
| FORM | 0.15 | **0.14** | Form already fully represented; slight reduction preserves balance |

**Estimated leaderboard impact:**
- Top 3 unchanged (Scheffler, McIlroy, Fitzpatrick all NSI-driven)
- VHN increase benefits MacIntyre (+0.03 VHN weight × 84.6 VHN = +0.16 pre-norm), Højgaard, McIlroy
- VFS decrease is neutral (so little spread it barely moves anyone)
- Total expected rank changes: 3-5 players shift ±1-2 positions, no dramatic changes

**Calibration risk:** LOW — the rebalance acknowledges data reality without changing the doctrine. The only risk is underselling VFS if the venue fit CSV is eventually corrected/improved; in that case the 0.25 weight would undervalue it.

**Alternative if not rebalancing:** Scale `approach_composite_value × 3.0` in the VFS formula to expand approach signal range from ~0.04 to ~0.12 for elite players → VFS std ≈ 4-6 → effective contribution ~0.6-1.0 VTS pts. This is the more principled fix (venue fit model should reflect approach data) and would make the VFS weight earn its 0.30 allocation.

---

## Validation Gates (post-repair)

| Gate | Status | Value |
|------|--------|-------|
| Top-30 VTS unique values | ✅ PASS | 30/30 |
| Win prob sum | ✅ PASS | 100.0% |
| Tier 1 count (3-6) | ✅ PASS | 4 |
| Anti-pattern players | ✅ PASS | 24 |
| Scheffler rank | ✅ PASS | #1 T1 |
| McIlroy rank | ✅ PASS | #2 T1 |
| Clark rank | ✅ PASS | #5 T2 (was #1 T1) |
| Gate 3 VFS top-30 range | ⚠️ WARN | 3.9 (compression noted, Phase 3) |

---

## Concise Changelog

| Ref | File | Change |
|-----|------|--------|
| FC-2-A | score_engine_v2.py L411 | `form_adj_neutral` = 0.0 (removed form injection from NSI) |
| FC-2-B | score_engine_v2.py L469 | `venue_fit_total_adj_ex_da` = total_adj − fit_drive_acc (DA removed from base) |
| FC-2-C | score_engine_v2.py L471 | `drive_acc_sg_signal = drive_acc_12m × 0.015`; VFS weights 0.55/0.30/0.15 → 0.45/0.40/0.15 |
| FC-2-D | score_engine_v2.py L580 | `podium_bonus_vhn` (+0.08), `win_bonus_vhn` (+0.12); ch_adj ×4→×3; exp_adj ×2→×1.5 |
| FC-2-E | score_engine_v2.py L495 | AP Flag 2 now uses `drive_acc_sg_signal < -0.03` (canonical source) |
| FC-2-F | score_engine_v2.py L1220+ | drag_traits, failure_condition, venue_fit_summary, tier3_dark_horse use `drive_acc_12m` |
| FC-2-G | score_engine_v2.py L894 | corridor_discipline computed from `drive_acc_sg_signal` |
| deploy | deploy/data/*.json/.csv | event_payload, player_briefs, vts_full.csv redeployed |
