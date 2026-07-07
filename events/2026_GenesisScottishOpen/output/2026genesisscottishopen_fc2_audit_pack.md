# 2026 Genesis Scottish Open — FC-2 Engine Repair Audit

Generated: 2026-07-07  |  Engine: score_engine_v2.py (FC-2 repair patch)

## Scope
FC-2 engine repair — four structural bugs corrected:
1. **NSI form double-count removed**: `form_adj_neutral` (up to +0.30 SG boost) no longer injected into NSI; form belongs only in the FORM layer.
2. **VFS driving-accuracy double-count removed**: `fit_drive_acc` was already inside `venue_fit_total_adj`; adding it again at ×0.15 gave DA an effective weight of 0.70.
3. **Venue fit CSV DA signal replaced**: `fit_drive_acc` values were inverted vs actual SG data (accurate players penalised, inaccurate rewarded). Replaced with canonical SG-CSV-derived signal (`drive_acc_12m × 0.015`).
4. **VHN podium/win quality bonuses added**: `ch_adjustment` rewards consistency-vs-expected but ignored finish quality. Scheffler T3 podium now credited via `podium_bonus_vhn=+0.08`; McIlroy venue win via `win_bonus_vhn=+0.12`.

## Pre/Post VTS Decomposition — Key Players

| Player | Pre-VTS | Post-VTS | ΔVTS | Pre-NSI | Post-NSI | Pre-VFS | Post-VFS | Pre-VHN | Post-VHN |
|--------|---------|---------|------|---------|---------|---------|---------|---------|---------|

## Change summary

| # | Player | Branch fired | Notes |
|---|---|---|---|
| Scottie Scheffler | 82.1 | 88.2 | +6.1 | 94.8 | 98.2 | 53.6 | 61.4 | 55.4 | 62.8 |
| Rory Mcilroy | 83.5 | 85.2 | +1.7 | 80.7 | 83.0 | 66.0 | 64.0 | 68.5 | 78.5 |
| Matt Fitzpatrick | 80.4 | 84.4 | +4.0 | 78.5 | 80.6 | 54.2 | 60.7 | 86.1 | 89.8 |
| Tommy Fleetwood | 77.0 | 81.3 | +4.3 | 76.9 | 78.9 | 52.3 | 60.4 | 77.7 | 79.5 |
| Wyndham Clark | 91.5 | 80.0 | -11.6 | 83.6 | 68.7 | 62.2 | 60.1 | 74.3 | 70.7 |
| Kurt Kitayama | 78.2 | 79.8 | +1.6 | 73.9 | 75.7 | 62.3 | 64.2 | 71.0 | 73.8 |
| Chris Gotterup | 77.5 | 78.2 | +0.7 | 70.8 | 72.3 | 66.2 | 62.1 | 67.6 | 78.8 |
| Nicolai Hojgaard | 76.8 | 75.4 | -1.3 | 65.5 | 66.6 | 68.9 | 64.2 | 84.7 | 88.7 |
| Tyrrell Hatton | 80.9 | 72.4 | -8.5 | 74.3 | 63.3 | 61.9 | 60.6 | 62.6 | 59.7 |
| Viktor Hovland | 68.2 | 71.2 | +3.0 | 70.7 | 72.1 | 55.6 | 61.8 | 52.1 | 51.9 |
| Alex Fitzpatrick | 70.5 | 65.4 | -5.1 | 71.5 | 58.4 | 55.0 | 61.9 | 39.7 | 40.3 |
| Rasmus Hojgaard | 53.4 | 57.5 | +4.1 | 44.2 | 57.3 | 70.6 | 63.3 | 47.3 | 46.8 |

## Top-20 Rank Movers (Pre vs Post)

| Pre-Rank | Post-Rank | Δ | Player | Pre-VTS | Post-VTS |
|---------|---------|---|--------|---------|---------|
| 3 | 1 | +2 | Scottie Scheffler | 82.1 | 88.2 |
| 2 | 2 | = | Rory Mcilroy | 83.5 | 85.2 |
| 5 | 3 | +2 | Matt Fitzpatrick | 80.4 | 84.4 |
| 8 | 4 | +4 | Tommy Fleetwood | 77.0 | 81.3 |
| 1 | 5 | -4 | Wyndham Clark | 91.5 | 80.0 |
| 6 | 6 | = | Kurt Kitayama | 78.2 | 79.8 |
| 16 | 7 | +9 | Xander Schauffele | 72.0 | 79.2 |
| 7 | 8 | -1 | Chris Gotterup | 77.5 | 78.2 |
| 11 | 9 | +2 | Ludvig Aberg | 75.1 | 77.9 |
| 9 | 10 | -1 | Nicolai Hojgaard | 76.8 | 75.4 |
| 10 | 11 | -1 | Aaron Rai | 75.4 | 75.0 |
| 14 | 12 | +2 | Jon Rahm | 72.9 | 75.0 |
| 22 | 13 | +9 | J.J. Spaun | 70.3 | 73.8 |
| 26 | 14 | +12 | Si Woo Kim | 68.5 | 73.5 |
| 4 | 15 | -11 | Tyrrell Hatton | 80.9 | 72.4 |
| 24 | 16 | +8 | Patrick Cantlay | 69.4 | 72.4 |
| 19 | 17 | +2 | Adam Scott | 71.0 | 71.9 |
| 12 | 18 | -6 | Tom Kim | 74.5 | 71.9 |
| 27 | 19 | +8 | Viktor Hovland | 68.2 | 71.2 |
| 41 | 20 | +21 | Robert Macintyre | 62.3 | 70.1 |
| 28 | 21 | +7 | Shane Lowry | 67.3 | 69.5 |
| 17 | 22 | -5 | Kristoffer Reitan | 71.6 | 67.4 |
| 13 | 23 | -10 | Justin Thomas | 74.4 | 67.1 |
| 30 | 24 | +6 | Harris English | 66.3 | 67.0 |
| 15 | 25 | -10 | Bud Cauley | 72.8 | 66.4 |

## Tier Changes

| Player | Pre-Tier | Post-Tier |
|--------|---------|---------|
| Tommy Fleetwood | T2 | T1 |
| Wyndham Clark | T1 | T2 |
| Tyrrell Hatton | T1 | T2 |
| Robert Macintyre | T3 | T2 |
| Doug Ghim | T3 | T2 |
| Ryan Fox | T2 | T3 |
| Eric Cole | T2 | T3 |
| Tom Mckibbin | T4 | T3 |
| Dan Bradbury | T4 | T3 |
| Kota Kaneko | T4 | T3 |
| John Parry | T4 | T3 |
| Michael Thorbjornsen | T4 | T3 |
| Padraig Harrington | T2 | T3 |
| Sungjae Im | T4 | T3 |
| Andy Sullivan | T4 | T3 |
| Hennie Du Plessis | T4 | T3 |
| Baekjun Kim | T4 | T3 |
| Richard Sterne | T4 | T3 |
| Thriston Lawrence | T4 | T3 |
| Eugenio Chacarra | T4 | T3 |
| Frederic Lacroix | T4 | T3 |
| Yurav Premlall | T3 | T4 |
| Erik Van Rooyen | T3 | T4 |
| Matti Schmid | T3 | T4 |
| Niklas Norgaard | T3 | T4 |
| Max Greyserman | T3 | T4 |
| Richard Mansell | T3 | T4 |
| Seungbin Choi | T3 | T4 |
| Joost Luiten | T5 | T4 |
| Marcel Siem | T5 | T4 |
| Matthieu Pavon | T5 | T4 |
| Adrien Saddier | T5 | T4 |
| Julien Guerrier | T5 | T4 |
| Ashun Wu | T5 | T4 |
| David Ravetto | T5 | T4 |
| Aldrich Potgieter | T3 | T4 |
| Darius Van Driel | T5 | T4 |
| Jayden Schaper | T5 | T4 |
| Nicolai Von Dellingshausen | T4 | T5 |
| Johannes Veerman | T4 | T5 |
| Calum Hill | T4 | T5 |
| Joakim Lagergren | T4 | T5 |
| Taylor Moore | T4 | T5 |
| David Puig | T4 | T5 |
| Guido Migliozzi | T4 | T5 |
| Mikael Lindberg | T4 | T5 |
| Adrian Meronk | T4 | T5 |
| Dylan Frittelli | T4 | T5 |
| Davis Riley | T4 | T5 |

---

## Venue History Summary Changes (FC-1 baseline + FC-2 VHN refactor)

| # | Player | Branch fired | Notes |
|---|---|---|---|

**Total changed: 0 of 166 players**

---

## Detailed diff


**VH summary changes: 0 of 166 players**

---

## Detailed VH Diff

## Engine Repair Changelog

| Fix | Location | Change |
|-----|----------|--------|
| FC-2-A | Step 2 NSI | Removed `form_adj_neutral` injection (was +0.30 for HOT form) — NSI now reflects pure structural skill |
| FC-2-B | Step 3 VFS | Stripped DA from `venue_fit_total_adj_ex_da`; replaced `fit_drive_acc×0.15` with `drive_acc_sg_signal×0.15` |
| FC-2-C | Step 3 VFS | VFS formula rebalanced: total_adj×0.45 (was 0.55) + approach_composite×0.40 (was 0.30) + da_sg×0.15 (was fit_acc×0.15) |
| FC-2-D | Step 4 VHN | Added podium_bonus_vhn (+0.08) and win_bonus_vhn (+0.12); ch_adj multiplier 4→3, exp_adj 2→1.5 |
| FC-2-E | AP Flag 2 | Now uses `drive_acc_sg_signal < -0.03` instead of `fit_drive_acc < 0` (canonical SG source) |
| FC-2-F | Narratives | drag_traits, failure_condition, venue_fit_summary, tier3_dark_horse all now use `drive_acc_12m` |

## Validation Guards

- `best_finish_renaissance == 1` → summary contains winner/defending champion language ✓
- `best_finish_renaissance <= 5` → no limited-history wording without podium language ✓
- `last_finish_renaissance <= 15` → does not read like debut/no-history ✓
- NSI: form signal removed; purely SG-APP/OTT/ARG/PUTT weighted composite ✓
- VFS: driving accuracy non-redundant; approach_composite primary (40%) ✓
- VHN: podium/win quality credited independently of consistency-vs-expected ✓