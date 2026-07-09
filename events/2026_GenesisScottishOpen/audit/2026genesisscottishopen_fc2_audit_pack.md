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
| Scottie Scheffler | 82.1 | 92.0 | +9.9 | 94.8 | 100.0 | 53.6 | 77.5 | 55.4 | 50.0 |
| Tommy Fleetwood | 77.0 | 83.5 | +6.5 | 76.9 | 85.3 | 52.3 | 68.9 | 77.7 | 60.5 |
| Rory Mcilroy | 83.5 | 83.5 | +0.1 | 80.7 | 84.8 | 66.0 | 71.8 | 68.5 | 55.6 |
| Matt Fitzpatrick | 80.4 | 77.0 | -3.4 | 78.5 | 75.1 | 54.2 | 68.0 | 86.1 | 59.6 |
| Kurt Kitayama | 78.2 | 76.0 | -2.2 | 73.9 | 71.5 | 62.3 | 69.0 | 71.0 | 61.0 |
| Tyrrell Hatton | 80.9 | 75.2 | -5.7 | 74.3 | 67.2 | 61.9 | 64.7 | 62.6 | 57.5 |
| Viktor Hovland | 68.2 | 74.5 | +6.3 | 70.7 | 75.9 | 55.6 | 67.5 | 52.1 | 48.9 |
| Chris Gotterup | 77.5 | 74.4 | -3.1 | 70.8 | 69.2 | 66.2 | 65.1 | 67.6 | 67.0 |
| Wyndham Clark | 91.5 | 74.2 | -17.4 | 83.6 | 61.8 | 62.2 | 61.1 | 74.3 | 63.5 |
| Nicolai Hojgaard | 76.8 | 72.1 | -4.7 | 65.5 | 67.7 | 68.9 | 65.4 | 84.7 | 70.8 |
| Alex Fitzpatrick | 70.5 | 62.5 | -7.9 | 71.5 | 53.6 | 55.0 | 63.0 | 39.7 | 38.4 |
| Rasmus Hojgaard | 53.4 | 58.0 | +4.6 | 44.2 | 60.8 | 70.6 | 60.1 | 47.3 | 46.2 |

## Top-20 Rank Movers (Pre vs Post)

| Pre-Rank | Post-Rank | Δ | Player | Pre-VTS | Post-VTS |
|---------|---------|---|--------|---------|---------|
| 3 | 1 | +2 | Scottie Scheffler | 82.1 | 92.0 |
| 8 | 2 | +6 | Tommy Fleetwood | 77.0 | 83.5 |
| 2 | 3 | -1 | Rory Mcilroy | 83.5 | 83.5 |
| 16 | 4 | +12 | Xander Schauffele | 72.0 | 78.5 |
| 14 | 5 | +9 | Jon Rahm | 72.9 | 78.1 |
| 5 | 6 | -1 | Matt Fitzpatrick | 80.4 | 77.0 |
| 11 | 7 | +4 | Ludvig Aberg | 75.1 | 76.8 |
| 24 | 8 | +16 | Patrick Cantlay | 69.4 | 76.2 |
| 6 | 9 | -3 | Kurt Kitayama | 78.2 | 76.0 |
| 22 | 10 | +12 | J.J. Spaun | 70.3 | 75.8 |
| 28 | 11 | +17 | Shane Lowry | 67.3 | 75.3 |
| 4 | 12 | -8 | Tyrrell Hatton | 80.9 | 75.2 |
| 26 | 13 | +13 | Si Woo Kim | 68.5 | 74.6 |
| 27 | 14 | +13 | Viktor Hovland | 68.2 | 74.5 |
| 7 | 15 | -8 | Chris Gotterup | 77.5 | 74.4 |
| 1 | 16 | -15 | Wyndham Clark | 91.5 | 74.2 |
| 13 | 17 | -4 | Justin Thomas | 74.4 | 73.5 |
| 10 | 18 | -8 | Aaron Rai | 75.4 | 72.8 |
| 9 | 19 | -10 | Nicolai Hojgaard | 76.8 | 72.1 |
| 34 | 20 | +14 | Doug Ghim | 63.4 | 71.3 |
| 19 | 21 | -2 | Adam Scott | 71.0 | 70.5 |
| 15 | 22 | -7 | Bud Cauley | 72.8 | 69.8 |
| 41 | 23 | +18 | Robert Macintyre | 62.3 | 69.3 |
| 17 | 24 | -7 | Kristoffer Reitan | 71.6 | 68.7 |
| 12 | 25 | -13 | Tom Kim | 74.5 | 68.0 |

## Tier Changes

| Player | Pre-Tier | Post-Tier |
|--------|---------|---------|
| Tommy Fleetwood | T2 | T1 |
| Matt Fitzpatrick | T1 | T2 |
| Tyrrell Hatton | T1 | T2 |
| Wyndham Clark | T1 | T2 |
| Doug Ghim | T3 | T2 |
| Robert Macintyre | T3 | T2 |
| Jake Knapp | T3 | T2 |
| Nick Taylor | T3 | T2 |
| Corey Conners | T3 | T2 |
| Ryan Fox | T2 | T3 |
| Victor Perez | T2 | T3 |
| Alex Fitzpatrick | T2 | T3 |
| Eric Cole | T2 | T3 |
| Matt Wallace | T2 | T3 |
| John Parry | T4 | T3 |
| Kevin Yu | T4 | T3 |
| Michael Thorbjornsen | T4 | T3 |
| Kota Kaneko | T4 | T3 |
| Tom Mckibbin | T4 | T3 |
| Hennie Du Plessis | T4 | T3 |
| Sungjae Im | T4 | T3 |
| Eugenio Chacarra | T4 | T3 |
| Martin Couvra | T4 | T3 |
| Baekjun Kim | T4 | T3 |
| Dan Bradbury | T4 | T3 |
| Padraig Harrington | T2 | T3 |
| Erik Van Rooyen | T3 | T4 |
| Alejandro Del Rey | T3 | T4 |
| Sam Stevens | T3 | T4 |
| Francesco Molinari | T3 | T4 |
| Pierceson Coody | T3 | T4 |
| Brandt Snedeker | T3 | T4 |
| Seungbin Choi | T3 | T4 |
| Grant Forrest | T3 | T4 |
| Keita Nakajima | T3 | T4 |
| Yurav Premlall | T3 | T4 |
| Joost Luiten | T5 | T4 |
| Mark Hubbard | T3 | T4 |
| Aldrich Potgieter | T3 | T4 |
| Niklas Norgaard | T3 | T4 |
| Matthieu Pavon | T5 | T4 |
| Marcel Siem | T5 | T4 |
| Julien Guerrier | T5 | T4 |
| David Ravetto | T5 | T4 |
| Adrien Saddier | T5 | T4 |
| Jordan Gumberg | T5 | T4 |
| Darius Van Driel | T5 | T4 |
| Jayden Schaper | T5 | T4 |
| Karl Vilips | T5 | T4 |
| Kevin Roy | T5 | T4 |
| Ashun Wu | T5 | T4 |
| Rikuya Hoshino | T5 | T4 |
| Adrian Otaegui | T5 | T4 |
| Joakim Lagergren | T4 | T5 |
| Taylor Moore | T4 | T5 |
| Johannes Veerman | T4 | T5 |
| Mikael Lindberg | T4 | T5 |
| Guido Migliozzi | T4 | T5 |
| Dylan Frittelli | T4 | T5 |
| Adrian Meronk | T4 | T5 |
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