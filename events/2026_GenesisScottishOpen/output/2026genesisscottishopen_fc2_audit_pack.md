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
| Scottie Scheffler | 82.1 | 90.3 | +8.2 | 94.8 | 100.0 | 53.6 | 60.7 | 55.4 | 62.8 |
| Rory Mcilroy | 83.5 | 86.3 | +2.8 | 80.7 | 82.0 | 66.0 | 65.2 | 68.5 | 78.5 |
| Tommy Fleetwood | 77.0 | 83.8 | +6.8 | 76.9 | 82.3 | 52.3 | 58.9 | 77.7 | 79.5 |
| Matt Fitzpatrick | 80.4 | 80.9 | +0.5 | 78.5 | 73.6 | 54.2 | 59.9 | 86.1 | 89.8 |
| Kurt Kitayama | 78.2 | 79.6 | +1.4 | 73.9 | 73.2 | 62.3 | 65.0 | 71.0 | 73.8 |
| Nicolai Hojgaard | 76.8 | 77.6 | +0.9 | 65.5 | 67.9 | 68.9 | 65.7 | 84.7 | 88.7 |
| Tyrrell Hatton | 80.9 | 76.6 | -4.3 | 74.3 | 68.9 | 61.9 | 61.1 | 62.6 | 59.7 |
| Chris Gotterup | 77.5 | 75.5 | -2.0 | 70.8 | 65.7 | 66.2 | 63.2 | 67.6 | 78.8 |
| Wyndham Clark | 91.5 | 74.4 | -17.1 | 83.6 | 57.9 | 62.2 | 60.4 | 74.3 | 70.7 |
| Viktor Hovland | 68.2 | 73.5 | +5.2 | 70.7 | 75.5 | 55.6 | 61.2 | 52.1 | 51.9 |
| Alex Fitzpatrick | 70.5 | 62.3 | -8.2 | 71.5 | 53.3 | 55.0 | 61.3 | 39.7 | 40.3 |
| Rasmus Hojgaard | 53.4 | 57.4 | +4.0 | 44.2 | 56.3 | 70.6 | 64.6 | 47.3 | 46.8 |

## Top-20 Rank Movers (Pre vs Post)

| Pre-Rank | Post-Rank | Δ | Player | Pre-VTS | Post-VTS |
|---------|---------|---|--------|---------|---------|
| 3 | 1 | +2 | Scottie Scheffler | 82.1 | 90.3 |
| 2 | 2 | = | Rory Mcilroy | 83.5 | 86.3 |
| 8 | 3 | +5 | Tommy Fleetwood | 77.0 | 83.8 |
| 16 | 4 | +12 | Xander Schauffele | 72.0 | 82.0 |
| 5 | 5 | = | Matt Fitzpatrick | 80.4 | 80.9 |
| 6 | 6 | = | Kurt Kitayama | 78.2 | 79.6 |
| 9 | 7 | +2 | Nicolai Hojgaard | 76.8 | 77.6 |
| 4 | 8 | -4 | Tyrrell Hatton | 80.9 | 76.6 |
| 11 | 9 | +2 | Ludvig Aberg | 75.1 | 76.6 |
| 10 | 10 | = | Aaron Rai | 75.4 | 75.9 |
| 22 | 11 | +11 | J.J. Spaun | 70.3 | 75.8 |
| 14 | 12 | +2 | Jon Rahm | 72.9 | 75.8 |
| 7 | 13 | -6 | Chris Gotterup | 77.5 | 75.5 |
| 24 | 14 | +10 | Patrick Cantlay | 69.4 | 74.9 |
| 26 | 15 | +11 | Si Woo Kim | 68.5 | 74.5 |
| 1 | 16 | -15 | Wyndham Clark | 91.5 | 74.4 |
| 27 | 17 | +10 | Viktor Hovland | 68.2 | 73.5 |
| 19 | 18 | +1 | Adam Scott | 71.0 | 72.7 |
| 12 | 19 | -7 | Tom Kim | 74.5 | 72.6 |
| 13 | 20 | -7 | Justin Thomas | 74.4 | 72.4 |
| 34 | 21 | +13 | Doug Ghim | 63.4 | 72.3 |
| 28 | 22 | +6 | Shane Lowry | 67.3 | 71.0 |
| 41 | 23 | +18 | Robert Macintyre | 62.3 | 70.5 |
| 15 | 24 | -9 | Bud Cauley | 72.8 | 68.8 |
| 18 | 25 | -7 | Victor Perez | 71.3 | 67.7 |

## Tier Changes

| Player | Pre-Tier | Post-Tier |
|--------|---------|---------|
| Tommy Fleetwood | T2 | T1 |
| Xander Schauffele | T2 | T1 |
| Tyrrell Hatton | T1 | T2 |
| Wyndham Clark | T1 | T2 |
| Doug Ghim | T3 | T2 |
| Robert Macintyre | T3 | T2 |
| Nick Taylor | T3 | T2 |
| Corey Conners | T3 | T2 |
| Harris English | T2 | T3 |
| Alex Fitzpatrick | T2 | T3 |
| Matt Wallace | T2 | T3 |
| Kevin Yu | T4 | T3 |
| Eric Cole | T2 | T3 |
| Padraig Harrington | T2 | T3 |
| John Parry | T4 | T3 |
| Tom Mckibbin | T4 | T3 |
| Michael Thorbjornsen | T4 | T3 |
| Hennie Du Plessis | T4 | T3 |
| Sungjae Im | T4 | T3 |
| Dan Bradbury | T4 | T3 |
| Martin Couvra | T4 | T3 |
| Thriston Lawrence | T4 | T3 |
| Frederic Lacroix | T4 | T3 |
| Matteo Manassero | T4 | T3 |
| Yurav Premlall | T3 | T4 |
| Jimmy Stanger | T3 | T4 |
| Niklas Norgaard | T3 | T4 |
| Marcel Siem | T5 | T4 |
| Sam Stevens | T3 | T4 |
| Joost Luiten | T5 | T4 |
| Brandt Snedeker | T3 | T4 |
| Keita Nakajima | T3 | T4 |
| Cam Davis | T5 | T4 |
| Adrien Saddier | T5 | T4 |
| Pierceson Coody | T3 | T4 |
| Matthieu Pavon | T5 | T4 |
| David Ravetto | T5 | T4 |
| Charley Hoffman | T5 | T4 |
| Guido Migliozzi | T4 | T5 |
| Ricky Castillo | T4 | T5 |
| Nicolai Von Dellingshausen | T4 | T5 |
| Calum Hill | T4 | T5 |
| Dylan Frittelli | T4 | T5 |
| Shaun Norris | T4 | T5 |
| David Puig | T4 | T5 |
| Adrian Meronk | T4 | T5 |
| Mikael Lindberg | T4 | T5 |
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