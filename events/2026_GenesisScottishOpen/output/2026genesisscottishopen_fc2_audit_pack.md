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
| Scottie Scheffler | 82.1 | 87.6 | +5.5 | 94.8 | 98.2 | 53.6 | 59.7 | 55.4 | 62.8 |
| Rory Mcilroy | 83.5 | 84.9 | +1.4 | 80.7 | 83.0 | 66.0 | 63.0 | 68.5 | 78.5 |
| Matt Fitzpatrick | 80.4 | 84.0 | +3.6 | 78.5 | 80.6 | 54.2 | 59.4 | 86.1 | 89.8 |
| Tommy Fleetwood | 77.0 | 81.3 | +4.3 | 76.9 | 78.9 | 52.3 | 59.9 | 77.7 | 79.5 |
| Wyndham Clark | 91.5 | 79.8 | -11.8 | 83.6 | 68.7 | 62.2 | 59.3 | 74.3 | 70.7 |
| Kurt Kitayama | 78.2 | 79.4 | +1.2 | 73.9 | 75.7 | 62.3 | 62.8 | 71.0 | 73.8 |
| Chris Gotterup | 77.5 | 78.2 | +0.8 | 70.8 | 72.3 | 66.2 | 61.9 | 67.6 | 78.8 |
| Nicolai Hojgaard | 76.8 | 75.1 | -1.7 | 65.5 | 66.6 | 68.9 | 63.1 | 84.7 | 88.7 |
| Tyrrell Hatton | 80.9 | 72.2 | -8.7 | 74.3 | 63.3 | 61.9 | 59.9 | 62.6 | 59.7 |
| Viktor Hovland | 68.2 | 70.8 | +2.6 | 70.7 | 72.1 | 55.6 | 60.7 | 52.1 | 51.9 |
| Alex Fitzpatrick | 70.5 | 65.0 | -5.4 | 71.5 | 58.4 | 55.0 | 61.0 | 39.7 | 40.3 |
| Rasmus Hojgaard | 53.4 | 57.7 | +4.3 | 44.2 | 57.3 | 70.6 | 63.6 | 47.3 | 46.8 |

## Top-20 Rank Movers (Pre vs Post)

| Pre-Rank | Post-Rank | Δ | Player | Pre-VTS | Post-VTS |
|---------|---------|---|--------|---------|---------|
| 3 | 1 | +2 | Scottie Scheffler | 82.1 | 87.6 |
| 2 | 2 | = | Rory Mcilroy | 83.5 | 84.9 |
| 5 | 3 | +2 | Matt Fitzpatrick | 80.4 | 84.0 |
| 8 | 4 | +4 | Tommy Fleetwood | 77.0 | 81.3 |
| 1 | 5 | -4 | Wyndham Clark | 91.5 | 79.8 |
| 6 | 6 | = | Kurt Kitayama | 78.2 | 79.4 |
| 16 | 7 | +9 | Xander Schauffele | 72.0 | 79.0 |
| 7 | 8 | -1 | Chris Gotterup | 77.5 | 78.2 |
| 11 | 9 | +2 | Ludvig Aberg | 75.1 | 77.7 |
| 9 | 10 | -1 | Nicolai Hojgaard | 76.8 | 75.1 |
| 10 | 11 | -1 | Aaron Rai | 75.4 | 74.8 |
| 14 | 12 | +2 | Jon Rahm | 72.9 | 74.4 |
| 22 | 13 | +9 | J.J. Spaun | 70.3 | 73.1 |
| 26 | 14 | +12 | Si Woo Kim | 68.5 | 72.8 |
| 4 | 15 | -11 | Tyrrell Hatton | 80.9 | 72.2 |
| 24 | 16 | +8 | Patrick Cantlay | 69.4 | 72.0 |
| 12 | 17 | -5 | Tom Kim | 74.5 | 71.7 |
| 19 | 18 | +1 | Adam Scott | 71.0 | 71.6 |
| 27 | 19 | +8 | Viktor Hovland | 68.2 | 70.8 |
| 41 | 20 | +21 | Robert Macintyre | 62.3 | 70.5 |
| 28 | 21 | +7 | Shane Lowry | 67.3 | 69.2 |
| 17 | 22 | -5 | Kristoffer Reitan | 71.6 | 67.6 |
| 30 | 23 | +7 | Harris English | 66.3 | 67.2 |
| 13 | 24 | -11 | Justin Thomas | 74.4 | 67.2 |
| 34 | 25 | +9 | Doug Ghim | 63.4 | 66.7 |

## Tier Changes

| Player | Pre-Tier | Post-Tier |
|--------|---------|---------|
| Tommy Fleetwood | T2 | T1 |
| Wyndham Clark | T1 | T2 |
| Tyrrell Hatton | T1 | T2 |
| Robert Macintyre | T3 | T2 |
| Doug Ghim | T3 | T2 |
| Matt Wallace | T2 | T3 |
| Ryan Fox | T2 | T3 |
| Eric Cole | T2 | T3 |
| Tom Mckibbin | T4 | T3 |
| Dan Bradbury | T4 | T3 |
| Kota Kaneko | T4 | T3 |
| John Parry | T4 | T3 |
| Sungjae Im | T4 | T3 |
| Michael Thorbjornsen | T4 | T3 |
| Padraig Harrington | T2 | T3 |
| Andy Sullivan | T4 | T3 |
| Hennie Du Plessis | T4 | T3 |
| Baekjun Kim | T4 | T3 |
| Richard Sterne | T4 | T3 |
| Thriston Lawrence | T4 | T3 |
| Frederic Lacroix | T4 | T3 |
| Eugenio Chacarra | T4 | T3 |
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
| Taylor Moore | T4 | T5 |
| Joakim Lagergren | T4 | T5 |
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
| 1 | Scottie Scheffler | Branch 2 (podium top-5) | |
| 2 | Rory Mcilroy | Branch 1 (winner/defending) | |
| 3 | Matt Fitzpatrick | Branch 2 (podium top-5) | |
| 4 | Tommy Fleetwood | Branch 2 (podium top-5) | |
| 5 | Wyndham Clark | Branch 4 (depth-by-sample) | |
| 6 | Kurt Kitayama | Branch 2 (podium top-5) | |
| 7 | Xander Schauffele | Branch 1 (winner/defending) | |
| 8 | Chris Gotterup | Branch 1 (winner/defending) | |
| 9 | Ludvig Aberg | Branch 2 (podium top-5) | |
| 10 | Nicolai Hojgaard | Branch 2 (podium top-5) | |
| 11 | Aaron Rai | Branch 2 (podium top-5) | |
| 12 | Jon Rahm | Branch 4 (depth-by-sample) | |
| 13 | J.J. Spaun | Branch 4 (depth-by-sample) | |
| 14 | Si Woo Kim | Branch 4 (depth-by-sample) | |
| 15 | Tyrrell Hatton | Branch 4 (depth-by-sample) | |
| 16 | Patrick Cantlay | Branch 2 (podium top-5) | |
| 17 | Tom Kim | Branch 2 (podium top-5) | |
| 18 | Adam Scott | Branch 2 (podium top-5) | |
| 19 | Viktor Hovland | Branch 3 (recent top-15) | |
| 20 | Robert Macintyre | Branch 1 (winner/defending) | |
| 21 | Shane Lowry | Branch 3 (recent top-15) | |
| 22 | Kristoffer Reitan | Branch 3 (recent top-15) | |
| 23 | Harris English | Branch 4 (depth-by-sample) | |
| 24 | Justin Thomas | Branch 4 (depth-by-sample) | |
| 25 | Doug Ghim | Branch 4 (depth-by-sample) | |
| 26 | Victor Perez | Branch 4 (depth-by-sample) | |
| 27 | Bud Cauley | Branch 5 (limited fallback) | |
| 28 | Alex Fitzpatrick | Branch 4 (depth-by-sample) | |
| 29 | Matt Wallace | Branch 4 (depth-by-sample) | |
| 30 | Min Woo Lee | Branch 1 (winner/defending) | |
| 31 | Nick Taylor | Branch 4 (depth-by-sample) | |
| 32 | Jordan Smith | Branch 4 (depth-by-sample) | |
| 33 | Alex Smalley | Branch 4 (depth-by-sample) | |
| 34 | Jake Knapp | Branch 5 (limited fallback) | |
| 35 | Alex Noren | Branch 3 (recent top-15) | |
| 36 | Ryan Fox | Branch 4 (depth-by-sample) | |
| 37 | Corey Conners | Branch 4 (depth-by-sample) | |
| 38 | Sahith Theegala | Branch 2 (podium top-5) | |
| 39 | Brian Harman | Branch 4 (depth-by-sample) | |
| 40 | Ryan Gerard | Branch 5 (limited fallback) | |
| 41 | Eric Cole | Branch 4 (depth-by-sample) | |
| 42 | Ewen Ferguson | Branch 4 (depth-by-sample) | |
| 43 | Daniel Hillier | Branch 4 (depth-by-sample) | |
| 44 | Sepp Straka | Branch 3 (recent top-15) | |
| 45 | Rasmus Neergaard-Petersen | Branch 5 (limited fallback) | |
| 46 | Marco Penge | Branch 2 (podium top-5) | |
| 47 | Michael Kim | Branch 4 (depth-by-sample) | |
| 48 | Andrew Novak | Branch 3 (recent top-15) | |
| 49 | Haotong Li | Branch 4 (depth-by-sample) | |
| 50 | Thorbjorn Olesen | Branch 4 (depth-by-sample) | |
| 51 | Antoine Rozner | Branch 4 (depth-by-sample) | |
| 52 | Harry Hall | Branch 4 (depth-by-sample) | |
| 53 | Brandt Snedeker | Branch 5 (limited fallback) | |
| 54 | Matt Mccarty | Branch 5 (limited fallback) | |
| 55 | Rasmus Hojgaard | Branch 4 (depth-by-sample) | |
| 56 | Bernd Wiesberger | Branch 4 (depth-by-sample) | |
| 57 | Max Mcgreevy | Branch 5 (limited fallback) | |
| 58 | Nico Echavarria | Branch 4 (depth-by-sample) | |
| 59 | Tom Mckibbin | Branch 4 (depth-by-sample) | |
| 60 | Sam Stevens | Branch 4 (depth-by-sample) | |
| 61 | Andrew Putnam | Branch 4 (depth-by-sample) | |
| 62 | Dan Brown | Branch 4 (depth-by-sample) | |
| 63 | Austin Eckroat | Branch 4 (depth-by-sample) | |
| 64 | Dan Bradbury | Branch 4 (depth-by-sample) | |
| 65 | Chris Kirk | Branch 5 (limited fallback) | |
| 66 | Keita Nakajima | Branch 4 (depth-by-sample) | |
| 67 | John Parry | Branch 5 (limited fallback) | |
| 68 | Paul Waring | Branch 4 (depth-by-sample) | |
| 69 | Billy Horschel | Branch 4 (depth-by-sample) | |
| 70 | Sungjae Im | Branch 2 (podium top-5) | |
| 71 | Chandler Phillips | Branch 5 (limited fallback) | |
| 72 | Padraig Harrington | Branch 4 (depth-by-sample) | |
| 73 | Andy Sullivan | Branch 4 (depth-by-sample) | |
| 74 | Alejandro Del Rey | Branch 4 (depth-by-sample) | |
| 75 | Grant Forrest | Branch 4 (depth-by-sample) | |
| 76 | Mark Hubbard | Branch 5 (limited fallback) | |
| 77 | Richard Sterne | Branch 5 (debut fallback) | |
| 78 | Thriston Lawrence | Branch 4 (depth-by-sample) | |
| 79 | Frederic Lacroix | Branch 5 (limited fallback) | |
| 80 | Eugenio Chacarra | Branch 5 (limited fallback) | |
| 81 | Jesper Svensson | Branch 4 (depth-by-sample) | |
| 82 | Erik Van Rooyen | Branch 4 (depth-by-sample) | |
| 83 | Matteo Manassero | Branch 3 (recent top-15) | |
| 84 | Matti Schmid | Branch 4 (depth-by-sample) | |
| 85 | Niklas Norgaard | Branch 3 (recent top-15) | |
| 86 | Max Greyserman | Branch 4 (depth-by-sample) | |
| 87 | Kevin Yu | Branch 4 (depth-by-sample) | |
| 88 | Richard Mansell | Branch 4 (depth-by-sample) | |
| 89 | Laurie Canter | Branch 4 (depth-by-sample) | |
| 90 | Connor Syme | Branch 4 (depth-by-sample) | |
| 91 | Joost Luiten | Branch 4 (depth-by-sample) | |
| 92 | Marcel Siem | Branch 4 (depth-by-sample) | |
| 93 | Matthieu Pavon | Branch 4 (depth-by-sample) | |
| 94 | Adrien Saddier | Branch 5 (limited fallback) | |
| 95 | Julien Guerrier | Branch 4 (depth-by-sample) | |
| 96 | Shaun Norris | Branch 5 (limited fallback) | |
| 97 | Ashun Wu | Branch 4 (depth-by-sample) | |
| 98 | David Ravetto | Branch 5 (limited fallback) | |
| 99 | Aldrich Potgieter | Branch 5 (limited fallback) | |
| 100 | Darius Van Driel | Branch 4 (depth-by-sample) | |
| 101 | Nicolai Von Dellingshausen | Branch 4 (depth-by-sample) | |
| 102 | Adrian Otaegui | Branch 4 (depth-by-sample) | |
| 103 | Rikuya Hoshino | Branch 5 (limited fallback) | |
| 104 | Johannes Veerman | Branch 3 (recent top-15) | |
| 105 | Jacques Kruyswijk | Branch 5 (limited fallback) | |
| 106 | Jordan Gumberg | Branch 4 (depth-by-sample) | |
| 107 | Yuto Katsuragawa | Branch 4 (depth-by-sample) | |
| 108 | Calum Hill | Branch 4 (depth-by-sample) | |
| 109 | Taylor Moore | Branch 4 (depth-by-sample) | |
| 110 | Scott Jamieson | Branch 4 (depth-by-sample) | |
| 111 | Joakim Lagergren | Branch 4 (depth-by-sample) | |
| 112 | Junghwan Lee | Branch 4 (depth-by-sample) | |
| 113 | Guido Migliozzi | Branch 4 (depth-by-sample) | |
| 114 | Brian Campbell | Branch 5 (limited fallback) | |
| 115 | Cam Davis | Branch 4 (depth-by-sample) | |
| 116 | Dylan Naidoo | Branch 5 (limited fallback) | |
| 117 | Adrian Meronk | Branch 4 (depth-by-sample) | |
| 118 | Dylan Frittelli | Branch 4 (depth-by-sample) | |
| 119 | Joe Highsmith | Branch 5 (limited fallback) | |
| 120 | Davis Riley | Branch 4 (depth-by-sample) | |
| 121 | Charley Hoffman | Branch 4 (depth-by-sample) | |
| 122 | Danny Willett | Branch 4 (depth-by-sample) | |
| 123 | Pablo Larrazabal | Branch 4 (depth-by-sample) | |
| 124 | Ryggs Johnston | Branch 5 (limited fallback) | |
| 125 | Ockie Strydom | Branch 4 (depth-by-sample) | |

**Total changed: 125 of 166 players**

---

## Detailed diff

### Scottie Scheffler

**Branch:** Branch 2 (podium top-5)

**Before:**
> VenueHistory 55.3/100 — 4 starts — podium-caliber Renaissance result (T3 in 2023) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj -0.016. 2025 recency bonus: +0.10.

**After:**
> VenueHistory 62.8/100 — 4 starts — podium-caliber Renaissance result (T3 in 2023) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj -0.016. 2025 recency bonus: +0.10.

---

### Rory Mcilroy

**Branch:** Branch 1 (winner/defending)

**Before:**
> VenueHistory 68.5/100 — 2023 winner at The Renaissance Club (4 starts) — venue win is the deepest possible course calibration. 3 top-15 results from 18 rounds. Course-history adj +0.003. 2025 recency bonus: +0.15.

**After:**
> VenueHistory 78.5/100 — 2023 winner at The Renaissance Club (4 starts) — venue win is the deepest possible course calibration. 3 top-15 results from 18 rounds. Course-history adj +0.003. 2025 recency bonus: +0.15.

---

### Matt Fitzpatrick

**Branch:** Branch 2 (podium top-5)

**Before:**
> VenueHistory 86.1/100 — 5 starts including podium-caliber Renaissance result (T2 in 2021) (2 top-5 results at this venue) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.038. 2025 recency bonus: +0.15.

**After:**
> VenueHistory 89.8/100 — 5 starts including podium-caliber Renaissance result (T2 in 2021) (2 top-5 results at this venue) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.038. 2025 recency bonus: +0.15.

---

### Tommy Fleetwood

**Branch:** Branch 2 (podium top-5)

**Before:**
> VenueHistory 77.7/100 — 5 starts including podium-caliber Renaissance result (T4 in 2022) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.054.

**After:**
> VenueHistory 79.5/100 — 5 starts including podium-caliber Renaissance result (T4 in 2022) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.054.

---

### Wyndham Clark

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 74.3/100 — depth=STRONG, 4 starts (16 rounds). Best finish: T10 (2024). Most recent: T11 (2025). Proven scorer at this venue — Renaissance-specific knowledge of tee corridors and green approach angles is a structural edge. 2025 recency bonus: +0.05.

**After:**
> VenueHistory 70.7/100 — depth=STRONG, 4 starts (16 rounds). Best finish: T10 (2024). Most recent: T11 (2025). Proven scorer at this venue — Renaissance-specific knowledge of tee corridors and green approach angles is a structural edge. 2025 recency bonus: +0.05.

---

### Kurt Kitayama

**Branch:** Branch 2 (podium top-5)

**Before:**
> VenueHistory 71.0/100 — 4 starts — podium-caliber Renaissance result (T2 in 2022) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.046.

**After:**
> VenueHistory 73.8/100 — 4 starts — podium-caliber Renaissance result (T2 in 2022) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.046.

---

### Xander Schauffele

**Branch:** Branch 1 (winner/defending)

**Before:**
> VenueHistory 72.7/100 — 2022 winner at The Renaissance Club (5 starts) — venue win is the deepest possible course calibration. 4 top-15 results from 20 rounds. Course-history adj +0.024. 2025 recency bonus: +0.10.

**After:**
> VenueHistory 81.0/100 — 2022 winner at The Renaissance Club (5 starts) — venue win is the deepest possible course calibration. 4 top-15 results from 20 rounds. Course-history adj +0.024. 2025 recency bonus: +0.10.

---

### Chris Gotterup

**Branch:** Branch 1 (winner/defending)

**Before:**
> VenueHistory 67.6/100 — defending champion (2025 winner) at The Renaissance Club (2 starts) — venue win is the deepest possible course calibration. 1 top-15 result from 6 rounds. Course-history adj +0.020. 2025 recency bonus: +0.20.

**After:**
> VenueHistory 78.8/100 — defending champion (2025 winner) at The Renaissance Club (2 starts) — venue win is the deepest possible course calibration. 1 top-15 result from 6 rounds. Course-history adj +0.020. 2025 recency bonus: +0.20.

---

### Ludvig Aberg

**Branch:** Branch 2 (podium top-5)

**Before:**
> VenueHistory 65.1/100 — 3 starts — podium-caliber Renaissance result (T4 in 2024) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.026. 2025 recency bonus: +0.10.

**After:**
> VenueHistory 71.0/100 — 3 starts — podium-caliber Renaissance result (T4 in 2024) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.026. 2025 recency bonus: +0.10.

---

### Nicolai Hojgaard

**Branch:** Branch 2 (podium top-5)

**Before:**
> VenueHistory 84.7/100 — 4 starts — podium-caliber Renaissance result (T4 in 2025) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.066. 2025 recency bonus: +0.15.

**After:**
> VenueHistory 88.6/100 — 4 starts — podium-caliber Renaissance result (T4 in 2025) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.066. 2025 recency bonus: +0.15.

---

### Aaron Rai

**Branch:** Branch 2 (podium top-5)

**Before:**
> VenueHistory 66.8/100 — 5 starts including podium-caliber Renaissance result (T4 in 2024) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.037. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 69.2/100 — 5 starts including podium-caliber Renaissance result (T4 in 2024) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.037. 2025 recency bonus: -0.05.

---

### Jon Rahm

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 39.5/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T7 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 40.2/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T7 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### J.J. Spaun

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 41.8/100 — depth=THIN, 2 starts (6 rounds). Best finish: T59 (2022). Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

**After:**
> VenueHistory 42.2/100 — depth=THIN, 2 starts (6 rounds). Best finish: T59 (2022). Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

---

### Si Woo Kim

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 47.6/100 — depth=MODERATE, 3 starts (12 rounds). Best finish: T26 (2024). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 47.0/100 — depth=MODERATE, 3 starts (12 rounds). Best finish: T26 (2024). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Tyrrell Hatton

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 62.6/100 — depth=STRONG, 3 starts (16 rounds). Best finish: T6 (2023). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration.

**After:**
> VenueHistory 59.7/100 — depth=STRONG, 3 starts (16 rounds). Best finish: T6 (2023). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration.

---

### Patrick Cantlay

**Branch:** Branch 2 (podium top-5)

**Before:**
> VenueHistory 45.3/100 — THIN sample (2 starts) but podium-caliber Renaissance result (T4 in 2022) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj -0.002.

**After:**
> VenueHistory 52.0/100 — THIN sample (2 starts) but podium-caliber Renaissance result (T4 in 2022) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj -0.002.

---

### Tom Kim

**Branch:** Branch 2 (podium top-5)

**Before:**
> VenueHistory 88.9/100 — 4 starts — podium-caliber Renaissance result (T3 in 2022) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.099. 2025 recency bonus: +0.05.

**After:**
> VenueHistory 90.0/100 — 4 starts — podium-caliber Renaissance result (T3 in 2022) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.099. 2025 recency bonus: +0.05.

---

### Adam Scott

**Branch:** Branch 2 (podium top-5)

**Before:**
> VenueHistory 66.2/100 — 3 starts — podium-caliber Renaissance result (T2 in 2024) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.042. 2025 recency bonus: +0.05.

**After:**
> VenueHistory 70.8/100 — 3 starts — podium-caliber Renaissance result (T2 in 2024) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.042. 2025 recency bonus: +0.05.

---

### Viktor Hovland

**Branch:** Branch 3 (recent top-15)

**Before:**
> VenueHistory 52.1/100 — 4 starts but recent Renaissance result T11 in 2025 marks a usable course reference at this venue. Course-history adj -0.014. 2025 recency bonus: +0.05.

**After:**
> VenueHistory 51.9/100 — 4 starts but recent Renaissance result T11 in 2025 marks a usable course reference at this venue. Course-history adj -0.014. 2025 recency bonus: +0.05.

---

### Robert Macintyre

**Branch:** Branch 1 (winner/defending)

**Before:**
> VenueHistory 81.0/100 — 2024 winner at The Renaissance Club (5 starts) — venue win is the deepest possible course calibration. 2 top-15 results from 24 rounds. Course-history adj +0.077. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 84.6/100 — 2024 winner at The Renaissance Club (5 starts) — venue win is the deepest possible course calibration. 2 top-15 results from 24 rounds. Course-history adj +0.077. 2025 recency bonus: -0.05.

---

### Shane Lowry

**Branch:** Branch 3 (recent top-15)

**Before:**
> VenueHistory 47.7/100 — limited sample (1 start) but recent Renaissance result T12 in 2023 removes true-debut uncertainty. Course-history adj +0.011.

**After:**
> VenueHistory 47.1/100 — limited sample (1 start) but recent Renaissance result T12 in 2023 removes true-debut uncertainty. Course-history adj +0.011.

---

### Kristoffer Reitan

**Branch:** Branch 3 (recent top-15)

**Before:**
> VenueHistory 52.9/100 — limited sample (1 start) but recent Renaissance result T13 in 2025 removes true-debut uncertainty. Course-history adj +0.010. 2025 recency bonus: +0.05.

**After:**
> VenueHistory 52.6/100 — limited sample (1 start) but recent Renaissance result T13 in 2025 removes true-debut uncertainty. Course-history adj +0.010. 2025 recency bonus: +0.05.

---

### Harris English

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 60.9/100 — depth=MODERATE, 3 starts (12 rounds). Best finish: T22 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 58.3/100 — depth=MODERATE, 3 starts (12 rounds). Best finish: T22 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Justin Thomas

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 42.2/100 — depth=MODERATE, 5 starts (22 rounds). Best finish: T8 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 42.4/100 — depth=MODERATE, 5 starts (22 rounds). Best finish: T8 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Doug Ghim

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 47.6/100 — depth=MODERATE, 3 starts (8 rounds). Best finish: T16 (2022). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 47.0/100 — depth=MODERATE, 3 starts (8 rounds). Best finish: T16 (2022). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Victor Perez

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 77.4/100 — depth=STRONG, 5 starts (26 rounds). Best finish: T10 (2024). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 71.1/100 — depth=STRONG, 5 starts (26 rounds). Best finish: T10 (2024). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration. 2025 recency bonus: -0.05.

---

### Bud Cauley

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 38.6/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. Best finish: T55. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 38.3/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. Best finish: T55. 2025 recency bonus: -0.05.

---

### Alex Fitzpatrick

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 39.7/100 — depth=THIN, 2 starts (4 rounds). No made-cut finish recorded. Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

**After:**
> VenueHistory 40.3/100 — depth=THIN, 2 starts (4 rounds). No made-cut finish recorded. Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

---

### Matt Wallace

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 57.4/100 — depth=STRONG, 5 starts (24 rounds). Best finish: T26 (2021). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 54.2/100 — depth=STRONG, 5 starts (24 rounds). Best finish: T26 (2021). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: -0.05.

---

### Min Woo Lee

**Branch:** Branch 1 (winner/defending)

**Before:**
> VenueHistory 49.8/100 — 2021 winner at The Renaissance Club (4 starts) — venue win is the deepest possible course calibration. 1 top-15 result from 18 rounds. Course-history adj -0.020.

**After:**
> VenueHistory 59.3/100 — 2021 winner at The Renaissance Club (4 starts) — venue win is the deepest possible course calibration. 1 top-15 result from 18 rounds. Course-history adj -0.020.

---

### Nick Taylor

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 66.4/100 — depth=STRONG, 4 starts (16 rounds). Best finish: T19 (2023). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 62.9/100 — depth=STRONG, 4 starts (16 rounds). Best finish: T19 (2023). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Jordan Smith

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 59.8/100 — depth=STRONG, 5 starts (22 rounds). Best finish: T12 (2023). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration.

**After:**
> VenueHistory 57.4/100 — depth=STRONG, 5 starts (22 rounds). Best finish: T12 (2023). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration.

---

### Alex Smalley

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 53.6/100 — depth=MODERATE, 3 starts (10 rounds). Best finish: T10 (2022). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration.

**After:**
> VenueHistory 52.1/100 — depth=MODERATE, 3 starts (10 rounds). Best finish: T10 (2022). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration.

---

### Jake Knapp

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 47.4/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. Best finish: T22.

**After:**
> VenueHistory 46.9/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. Best finish: T22.

---

### Alex Noren

**Branch:** Branch 3 (recent top-15)

**Before:**
> VenueHistory 54.4/100 — 4 starts but recent Renaissance result T10 in 2024 marks a usable course reference at this venue. Course-history adj +0.011.

**After:**
> VenueHistory 52.8/100 — 4 starts but recent Renaissance result T10 in 2024 marks a usable course reference at this venue. Course-history adj +0.011.

---

### Ryan Fox

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 50.5/100 — depth=MODERATE, 5 starts (24 rounds). Best finish: T12 (2023). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 48.4/100 — depth=MODERATE, 5 starts (24 rounds). Best finish: T12 (2023). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern. 2025 recency bonus: -0.05.

---

### Corey Conners

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 49.3/100 — depth=MODERATE, 5 starts (18 rounds). Best finish: T10 (2024). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 47.4/100 — depth=MODERATE, 5 starts (18 rounds). Best finish: T10 (2024). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern. 2025 recency bonus: -0.05.

---

### Sahith Theegala

**Branch:** Branch 2 (podium top-5)

**Before:**
> VenueHistory 49.3/100 — THIN sample (2 starts) but podium-caliber Renaissance result (T4 in 2024) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.011.

**After:**
> VenueHistory 55.5/100 — THIN sample (2 starts) but podium-caliber Renaissance result (T4 in 2024) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.011.

---

### Brian Harman

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 47.7/100 — depth=MODERATE, 4 starts (14 rounds). Best finish: T12 (2023). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 46.0/100 — depth=MODERATE, 4 starts (14 rounds). Best finish: T12 (2023). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern. 2025 recency bonus: -0.05.

---

### Ryan Gerard

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 33.3/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. Best finish: T74. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 33.8/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. Best finish: T74. 2025 recency bonus: -0.05.

---

### Eric Cole

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 46.7/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T46 (2024). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 46.2/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T46 (2024). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Ewen Ferguson

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 66.4/100 — depth=STRONG, 4 starts (16 rounds). Best finish: T12 (2023). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration.

**After:**
> VenueHistory 62.9/100 — depth=STRONG, 4 starts (16 rounds). Best finish: T12 (2023). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration.

---

### Daniel Hillier

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 56.1/100 — depth=MODERATE, 3 starts (10 rounds). Best finish: T46 (2024). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 54.2/100 — depth=MODERATE, 3 starts (10 rounds). Best finish: T46 (2024). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Sepp Straka

**Branch:** Branch 3 (recent top-15)

**Before:**
> VenueHistory 59.7/100 — 3 starts but recent Renaissance result T7 in 2025 establishes meaningful course familiarity. Course-history adj +0.014. 2025 recency bonus: +0.10.

**After:**
> VenueHistory 59.4/100 — 3 starts but recent Renaissance result T7 in 2025 establishes meaningful course familiarity. Course-history adj +0.014. 2025 recency bonus: +0.10.

---

### Rasmus Neergaard-Petersen

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 40.8/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 41.2/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Marco Penge

**Branch:** Branch 2 (podium top-5)

**Before:**
> VenueHistory 68.7/100 — THIN sample (1 start) but podium-caliber Renaissance result (T2 in 2025) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.041. 2025 recency bonus: +0.15.

**After:**
> VenueHistory 75.1/100 — THIN sample (1 start) but podium-caliber Renaissance result (T2 in 2025) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.041. 2025 recency bonus: +0.15.

---

### Michael Kim

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 47.4/100 — depth=THIN, 2 starts (6 rounds). Best finish: T34 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 46.9/100 — depth=THIN, 2 starts (6 rounds). Best finish: T34 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Andrew Novak

**Branch:** Branch 3 (recent top-15)

**Before:**
> VenueHistory 47.6/100 — 3 starts but recent Renaissance result T13 in 2025 establishes meaningful course familiarity. Course-history adj -0.018. 2025 recency bonus: +0.05.

**After:**
> VenueHistory 48.1/100 — 3 starts but recent Renaissance result T13 in 2025 establishes meaningful course familiarity. Course-history adj -0.018. 2025 recency bonus: +0.05.

---

### Haotong Li

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 64.7/100 — depth=STRONG, 5 starts (20 rounds). Best finish: T21 (2024). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 61.4/100 — depth=STRONG, 5 starts (20 rounds). Best finish: T21 (2024). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Thorbjorn Olesen

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 64.0/100 — depth=STRONG, 5 starts (22 rounds). Best finish: T25 (2023). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 59.8/100 — depth=STRONG, 5 starts (22 rounds). Best finish: T25 (2023). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: -0.05.

---

### Antoine Rozner

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 55.0/100 — depth=MODERATE, 5 starts (18 rounds). Best finish: T22 (2025). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 53.3/100 — depth=MODERATE, 5 starts (18 rounds). Best finish: T22 (2025). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Harry Hall

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 56.4/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T17 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: +0.05.

**After:**
> VenueHistory 55.6/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T17 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: +0.05.

---

### Brandt Snedeker

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 40.5/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 41.0/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Matt Mccarty

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 50.5/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. Best finish: T22.

**After:**
> VenueHistory 49.5/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. Best finish: T22.

---

### Rasmus Hojgaard

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 47.3/100 — depth=MODERATE, 5 starts (18 rounds). Best finish: T10 (2022). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 46.7/100 — depth=MODERATE, 5 starts (18 rounds). Best finish: T10 (2022). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Bernd Wiesberger

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 56.4/100 — depth=STRONG, 3 starts (16 rounds). Best finish: T26 (2021). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 54.5/100 — depth=STRONG, 3 starts (16 rounds). Best finish: T26 (2021). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Max Mcgreevy

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 41.4/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 41.8/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Nico Echavarria

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 49.6/100 — depth=THIN, 2 starts (6 rounds). Best finish: T22 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 48.7/100 — depth=THIN, 2 starts (6 rounds). Best finish: T22 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Tom Mckibbin

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 49.9/100 — depth=THIN, 2 starts (6 rounds). Best finish: T35 (2023). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 49.0/100 — depth=THIN, 2 starts (6 rounds). Best finish: T35 (2023). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Sam Stevens

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 32.8/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T57 (2024). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 33.5/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T57 (2024). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern. 2025 recency bonus: -0.05.

---

### Andrew Putnam

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 58.5/100 — depth=MODERATE, 3 starts (12 rounds). Best finish: T42 (2023). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 56.2/100 — depth=MODERATE, 3 starts (12 rounds). Best finish: T42 (2023). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Dan Brown

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 48.4/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T60 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 46.6/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T60 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: -0.05.

---

### Austin Eckroat

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 42.8/100 — depth=THIN, 2 starts (6 rounds). Best finish: T65 (2023). Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

**After:**
> VenueHistory 42.9/100 — depth=THIN, 2 starts (6 rounds). Best finish: T65 (2023). Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

---

### Dan Bradbury

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 30.8/100 — depth=MODERATE, 3 starts (8 rounds). Best finish: T75 (2023). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 32.8/100 — depth=MODERATE, 3 starts (8 rounds). Best finish: T75 (2023). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Chris Kirk

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 35.3/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. Best finish: T71.

**After:**
> VenueHistory 36.6/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. Best finish: T71.

---

### Keita Nakajima

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 38.9/100 — depth=THIN, 2 starts (6 rounds). Best finish: T55 (2025). Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 38.6/100 — depth=THIN, 2 starts (6 rounds). Best finish: T55 (2025). Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment. 2025 recency bonus: -0.05.

---

### John Parry

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 43.2/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. Best finish: T55. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 42.2/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. Best finish: T55. 2025 recency bonus: -0.05.

---

### Paul Waring

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 38.1/100 — depth=MODERATE, 3 starts (10 rounds). No made-cut finish recorded. Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 39.0/100 — depth=MODERATE, 3 starts (10 rounds). No made-cut finish recorded. Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Billy Horschel

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 44.2/100 — depth=MODERATE, 4 starts (12 rounds). Best finish: T54 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 44.1/100 — depth=MODERATE, 4 starts (12 rounds). Best finish: T54 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Sungjae Im

**Branch:** Branch 2 (podium top-5)

**Before:**
> VenueHistory 43.7/100 — 4 starts — podium-caliber Renaissance result (T4 in 2024) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj -0.018.

**After:**
> VenueHistory 50.7/100 — 4 starts — podium-caliber Renaissance result (T4 in 2024) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj -0.018.

---

### Chandler Phillips

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 42.6/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 42.8/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Padraig Harrington

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 67.8/100 — depth=STRONG, 5 starts (22 rounds). Best finish: T18 (2021). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 63.0/100 — depth=STRONG, 5 starts (22 rounds). Best finish: T18 (2021). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: -0.05.

---

### Andy Sullivan

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 69.9/100 — depth=STRONG, 3 starts (16 rounds). Best finish: T17 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: +0.05.

**After:**
> VenueHistory 67.0/100 — depth=STRONG, 3 starts (16 rounds). Best finish: T17 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: +0.05.

---

### Alejandro Del Rey

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 54.0/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T15 (2024). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 51.3/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T15 (2024). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration. 2025 recency bonus: -0.05.

---

### Grant Forrest

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 92.1/100 — depth=STRONG, 5 starts (26 rounds). Best finish: T11 (2023). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration.

**After:**
> VenueHistory 84.7/100 — depth=STRONG, 5 starts (26 rounds). Best finish: T11 (2023). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration.

---

### Mark Hubbard

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 37.0/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 38.1/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Richard Sterne

**Branch:** Branch 5 (debut fallback)

**Before:**
> VenueHistory 39.8/100 — Renaissance debut — links-course learning curve applies even for elite players; course-specific hole knowledge gap on rerouted closing stretch (new Hole 15).

**After:**
> VenueHistory 40.5/100 — Renaissance debut — links-course learning curve applies even for elite players; course-specific hole knowledge gap on rerouted closing stretch (new Hole 15).

---

### Thriston Lawrence

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 54.3/100 — depth=MODERATE, 4 starts (10 rounds). Best finish: T24 (2022). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 52.7/100 — depth=MODERATE, 4 starts (10 rounds). Best finish: T24 (2022). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Frederic Lacroix

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 37.3/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 38.4/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Eugenio Chacarra

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 39.8/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 40.5/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Jesper Svensson

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 49.9/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T34 (2024). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 47.9/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T34 (2024). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: -0.05.

---

### Erik Van Rooyen

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 63.7/100 — depth=STRONG, 4 starts (20 rounds). Best finish: T39 (2024). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 60.7/100 — depth=STRONG, 4 starts (20 rounds). Best finish: T39 (2024). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Matteo Manassero

**Branch:** Branch 3 (recent top-15)

**Before:**
> VenueHistory 51.8/100 — limited sample (2 starts) but recent Renaissance result T15 in 2024 removes true-debut uncertainty. Course-history adj +0.019.

**After:**
> VenueHistory 50.6/100 — limited sample (2 starts) but recent Renaissance result T15 in 2024 removes true-debut uncertainty. Course-history adj +0.019.

---

### Matti Schmid

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 52.6/100 — depth=THIN, 2 starts (6 rounds). Best finish: T17 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: +0.05.

**After:**
> VenueHistory 52.3/100 — depth=THIN, 2 starts (6 rounds). Best finish: T17 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: +0.05.

---

### Niklas Norgaard

**Branch:** Branch 3 (recent top-15)

**Before:**
> VenueHistory 50.5/100 — limited sample (2 starts) but recent Renaissance result T15 in 2024 removes true-debut uncertainty. Course-history adj +0.015.

**After:**
> VenueHistory 49.5/100 — limited sample (2 starts) but recent Renaissance result T15 in 2024 removes true-debut uncertainty. Course-history adj +0.015.

---

### Max Greyserman

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 49.0/100 — depth=THIN, 2 starts (6 rounds). Best finish: T21 (2024). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 48.2/100 — depth=THIN, 2 starts (6 rounds). Best finish: T21 (2024). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Kevin Yu

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 38.9/100 — depth=MODERATE, 3 starts (8 rounds). Best finish: T34 (2025). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 39.7/100 — depth=MODERATE, 3 starts (8 rounds). Best finish: T34 (2025). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Richard Mansell

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 61.1/100 — depth=MODERATE, 3 starts (10 rounds). Best finish: T10 (2024). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration.

**After:**
> VenueHistory 58.4/100 — depth=MODERATE, 3 starts (10 rounds). Best finish: T10 (2024). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration.

---

### Laurie Canter

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 38.9/100 — depth=MODERATE, 3 starts (12 rounds). Best finish: T34 (2025). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 39.7/100 — depth=MODERATE, 3 starts (12 rounds). Best finish: T34 (2025). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Connor Syme

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 67.0/100 — depth=STRONG, 5 starts (24 rounds). Best finish: T15 (2024). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 62.3/100 — depth=STRONG, 5 starts (24 rounds). Best finish: T15 (2024). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration. 2025 recency bonus: -0.05.

---

### Joost Luiten

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 52.7/100 — depth=MODERATE, 3 starts (16 rounds). Best finish: T54 (2023). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 51.3/100 — depth=MODERATE, 3 starts (16 rounds). Best finish: T54 (2023). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Marcel Siem

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 64.3/100 — depth=MODERATE, 3 starts (12 rounds). Best finish: T34 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 61.2/100 — depth=MODERATE, 3 starts (12 rounds). Best finish: T34 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Matthieu Pavon

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 53.8/100 — depth=MODERATE, 5 starts (20 rounds). Best finish: T12 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 52.3/100 — depth=MODERATE, 5 starts (20 rounds). Best finish: T12 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Adrien Saddier

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 37.0/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 38.1/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Julien Guerrier

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 36.3/100 — depth=MODERATE, 4 starts (13 rounds). Best finish: T70 (2024). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 37.4/100 — depth=MODERATE, 4 starts (13 rounds). Best finish: T70 (2024). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Shaun Norris

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 37.5/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 38.5/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Ashun Wu

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 64.3/100 — depth=STRONG, 4 starts (20 rounds). Best finish: T55 (2022). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 61.2/100 — depth=STRONG, 4 starts (20 rounds). Best finish: T55 (2022). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### David Ravetto

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 43.2/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 43.3/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Aldrich Potgieter

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 38.9/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 39.7/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Darius Van Driel

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 44.8/100 — depth=MODERATE, 3 starts (8 rounds). Best finish: T54 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 44.7/100 — depth=MODERATE, 3 starts (8 rounds). Best finish: T54 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Nicolai Von Dellingshausen

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 42.2/100 — depth=THIN, 2 starts (4 rounds). No made-cut finish recorded. Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

**After:**
> VenueHistory 42.4/100 — depth=THIN, 2 starts (4 rounds). No made-cut finish recorded. Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

---

### Adrian Otaegui

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 58.0/100 — depth=MODERATE, 5 starts (22 rounds). Best finish: T26 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 55.8/100 — depth=MODERATE, 5 starts (22 rounds). Best finish: T26 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Rikuya Hoshino

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 42.3/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 42.6/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Johannes Veerman

**Branch:** Branch 3 (recent top-15)

**Before:**
> VenueHistory 50.1/100 — 3 starts but recent Renaissance result T8 in 2021 establishes meaningful course familiarity. Course-history adj +0.008.

**After:**
> VenueHistory 49.1/100 — 3 starts but recent Renaissance result T8 in 2021 establishes meaningful course familiarity. Course-history adj +0.008.

---

### Jacques Kruyswijk

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 42.3/100 — limited Renaissance history (1 start, 6 rounds) — partial calibration only; no top-end venue result yet. Best finish: T65. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 41.5/100 — limited Renaissance history (1 start, 6 rounds) — partial calibration only; no top-end venue result yet. Best finish: T65. 2025 recency bonus: -0.05.

---

### Jordan Gumberg

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 48.7/100 — depth=THIN, 2 starts (4 rounds). No made-cut finish recorded. Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 47.9/100 — depth=THIN, 2 starts (4 rounds). No made-cut finish recorded. Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Yuto Katsuragawa

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 26.3/100 — depth=THIN, 2 starts (4 rounds). No made-cut finish recorded. Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

**After:**
> VenueHistory 29.0/100 — depth=THIN, 2 starts (4 rounds). No made-cut finish recorded. Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

---

### Calum Hill

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 55.5/100 — depth=MODERATE, 4 starts (19 rounds). Best finish: T25 (2023). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 53.7/100 — depth=MODERATE, 4 starts (19 rounds). Best finish: T25 (2023). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Taylor Moore

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 31.3/100 — depth=THIN, 2 starts (4 rounds). No made-cut finish recorded. Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

**After:**
> VenueHistory 33.2/100 — depth=THIN, 2 starts (4 rounds). No made-cut finish recorded. Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

---

### Scott Jamieson

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 54.4/100 — depth=MODERATE, 3 starts (14 rounds). No made-cut finish recorded. Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 52.8/100 — depth=MODERATE, 3 starts (14 rounds). No made-cut finish recorded. Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Joakim Lagergren

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 58.9/100 — depth=STRONG, 3 starts (16 rounds). Best finish: T35 (2021). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 56.6/100 — depth=STRONG, 3 starts (16 rounds). Best finish: T35 (2021). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Junghwan Lee

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 44.6/100 — depth=THIN, 2 starts (6 rounds). Best finish: T46 (2024). Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

**After:**
> VenueHistory 44.5/100 — depth=THIN, 2 starts (6 rounds). Best finish: T46 (2024). Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

---

### Guido Migliozzi

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 60.2/100 — depth=STRONG, 5 starts (22 rounds). Best finish: T35 (2021). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 57.6/100 — depth=STRONG, 5 starts (22 rounds). Best finish: T35 (2021). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Brian Campbell

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 38.3/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 39.1/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Cam Davis

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 46.5/100 — depth=THIN, 2 starts (6 rounds). Best finish: T26 (2024). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 46.1/100 — depth=THIN, 2 starts (6 rounds). Best finish: T26 (2024). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Dylan Naidoo

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 39.2/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 39.9/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Adrian Meronk

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 38.6/100 — depth=MODERATE, 3 starts (8 rounds). Best finish: T59 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 39.4/100 — depth=MODERATE, 3 starts (8 rounds). Best finish: T59 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Dylan Frittelli

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 39.7/100 — depth=MODERATE, 4 starts (10 rounds). Best finish: T47 (2022). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 40.3/100 — depth=MODERATE, 4 starts (10 rounds). Best finish: T47 (2022). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Joe Highsmith

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 34.6/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 36.0/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Davis Riley

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 44.5/100 — depth=MODERATE, 3 starts (8 rounds). Best finish: T35 (2023). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 44.4/100 — depth=MODERATE, 3 starts (8 rounds). Best finish: T35 (2023). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Charley Hoffman

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 46.8/100 — depth=MODERATE, 3 starts (10 rounds). Best finish: T57 (2024). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 46.4/100 — depth=MODERATE, 3 starts (10 rounds). Best finish: T57 (2024). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Danny Willett

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 17.3/100 — depth=MODERATE, 4 starts (10 rounds). No made-cut finish recorded. Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 21.4/100 — depth=MODERATE, 4 starts (10 rounds). No made-cut finish recorded. Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Pablo Larrazabal

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 27.0/100 — depth=MODERATE, 4 starts (16 rounds). No made-cut finish recorded. Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 29.6/100 — depth=MODERATE, 4 starts (16 rounds). No made-cut finish recorded. Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Ryggs Johnston

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 39.2/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 39.9/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Ockie Strydom

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 40.6/100 — depth=THIN, 3 starts (6 rounds). No made-cut finish recorded. Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

**After:**
> VenueHistory 41.1/100 — depth=THIN, 3 starts (6 rounds). No made-cut finish recorded. Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

---


**VH summary changes: 125 of 166 players**

---

## Detailed VH Diff

### Scottie Scheffler

**Branch:** Branch 2 (podium top-5)

**Before:**
> VenueHistory 55.3/100 — 4 starts — podium-caliber Renaissance result (T3 in 2023) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj -0.016. 2025 recency bonus: +0.10.

**After:**
> VenueHistory 62.8/100 — 4 starts — podium-caliber Renaissance result (T3 in 2023) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj -0.016. 2025 recency bonus: +0.10.

---

### Rory Mcilroy

**Branch:** Branch 1 (winner/defending)

**Before:**
> VenueHistory 68.5/100 — 2023 winner at The Renaissance Club (4 starts) — venue win is the deepest possible course calibration. 3 top-15 results from 18 rounds. Course-history adj +0.003. 2025 recency bonus: +0.15.

**After:**
> VenueHistory 78.5/100 — 2023 winner at The Renaissance Club (4 starts) — venue win is the deepest possible course calibration. 3 top-15 results from 18 rounds. Course-history adj +0.003. 2025 recency bonus: +0.15.

---

### Matt Fitzpatrick

**Branch:** Branch 2 (podium top-5)

**Before:**
> VenueHistory 86.1/100 — 5 starts including podium-caliber Renaissance result (T2 in 2021) (2 top-5 results at this venue) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.038. 2025 recency bonus: +0.15.

**After:**
> VenueHistory 89.8/100 — 5 starts including podium-caliber Renaissance result (T2 in 2021) (2 top-5 results at this venue) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.038. 2025 recency bonus: +0.15.

---

### Tommy Fleetwood

**Branch:** Branch 2 (podium top-5)

**Before:**
> VenueHistory 77.7/100 — 5 starts including podium-caliber Renaissance result (T4 in 2022) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.054.

**After:**
> VenueHistory 79.5/100 — 5 starts including podium-caliber Renaissance result (T4 in 2022) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.054.

---

### Wyndham Clark

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 74.3/100 — depth=STRONG, 4 starts (16 rounds). Best finish: T10 (2024). Most recent: T11 (2025). Proven scorer at this venue — Renaissance-specific knowledge of tee corridors and green approach angles is a structural edge. 2025 recency bonus: +0.05.

**After:**
> VenueHistory 70.7/100 — depth=STRONG, 4 starts (16 rounds). Best finish: T10 (2024). Most recent: T11 (2025). Proven scorer at this venue — Renaissance-specific knowledge of tee corridors and green approach angles is a structural edge. 2025 recency bonus: +0.05.

---

### Kurt Kitayama

**Branch:** Branch 2 (podium top-5)

**Before:**
> VenueHistory 71.0/100 — 4 starts — podium-caliber Renaissance result (T2 in 2022) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.046.

**After:**
> VenueHistory 73.8/100 — 4 starts — podium-caliber Renaissance result (T2 in 2022) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.046.

---

### Xander Schauffele

**Branch:** Branch 1 (winner/defending)

**Before:**
> VenueHistory 72.7/100 — 2022 winner at The Renaissance Club (5 starts) — venue win is the deepest possible course calibration. 4 top-15 results from 20 rounds. Course-history adj +0.024. 2025 recency bonus: +0.10.

**After:**
> VenueHistory 81.0/100 — 2022 winner at The Renaissance Club (5 starts) — venue win is the deepest possible course calibration. 4 top-15 results from 20 rounds. Course-history adj +0.024. 2025 recency bonus: +0.10.

---

### Chris Gotterup

**Branch:** Branch 1 (winner/defending)

**Before:**
> VenueHistory 67.6/100 — defending champion (2025 winner) at The Renaissance Club (2 starts) — venue win is the deepest possible course calibration. 1 top-15 result from 6 rounds. Course-history adj +0.020. 2025 recency bonus: +0.20.

**After:**
> VenueHistory 78.8/100 — defending champion (2025 winner) at The Renaissance Club (2 starts) — venue win is the deepest possible course calibration. 1 top-15 result from 6 rounds. Course-history adj +0.020. 2025 recency bonus: +0.20.

---

### Ludvig Aberg

**Branch:** Branch 2 (podium top-5)

**Before:**
> VenueHistory 65.1/100 — 3 starts — podium-caliber Renaissance result (T4 in 2024) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.026. 2025 recency bonus: +0.10.

**After:**
> VenueHistory 71.0/100 — 3 starts — podium-caliber Renaissance result (T4 in 2024) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.026. 2025 recency bonus: +0.10.

---

### Nicolai Hojgaard

**Branch:** Branch 2 (podium top-5)

**Before:**
> VenueHistory 84.7/100 — 4 starts — podium-caliber Renaissance result (T4 in 2025) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.066. 2025 recency bonus: +0.15.

**After:**
> VenueHistory 88.6/100 — 4 starts — podium-caliber Renaissance result (T4 in 2025) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.066. 2025 recency bonus: +0.15.

---

### Aaron Rai

**Branch:** Branch 2 (podium top-5)

**Before:**
> VenueHistory 66.8/100 — 5 starts including podium-caliber Renaissance result (T4 in 2024) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.037. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 69.2/100 — 5 starts including podium-caliber Renaissance result (T4 in 2024) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.037. 2025 recency bonus: -0.05.

---

### Jon Rahm

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 39.5/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T7 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 40.2/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T7 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### J.J. Spaun

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 41.8/100 — depth=THIN, 2 starts (6 rounds). Best finish: T59 (2022). Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

**After:**
> VenueHistory 42.2/100 — depth=THIN, 2 starts (6 rounds). Best finish: T59 (2022). Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

---

### Si Woo Kim

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 47.6/100 — depth=MODERATE, 3 starts (12 rounds). Best finish: T26 (2024). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 47.0/100 — depth=MODERATE, 3 starts (12 rounds). Best finish: T26 (2024). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Tyrrell Hatton

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 62.6/100 — depth=STRONG, 3 starts (16 rounds). Best finish: T6 (2023). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration.

**After:**
> VenueHistory 59.7/100 — depth=STRONG, 3 starts (16 rounds). Best finish: T6 (2023). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration.

---

### Patrick Cantlay

**Branch:** Branch 2 (podium top-5)

**Before:**
> VenueHistory 45.3/100 — THIN sample (2 starts) but podium-caliber Renaissance result (T4 in 2022) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj -0.002.

**After:**
> VenueHistory 52.0/100 — THIN sample (2 starts) but podium-caliber Renaissance result (T4 in 2022) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj -0.002.

---

### Tom Kim

**Branch:** Branch 2 (podium top-5)

**Before:**
> VenueHistory 88.9/100 — 4 starts — podium-caliber Renaissance result (T3 in 2022) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.099. 2025 recency bonus: +0.05.

**After:**
> VenueHistory 90.0/100 — 4 starts — podium-caliber Renaissance result (T3 in 2022) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.099. 2025 recency bonus: +0.05.

---

### Adam Scott

**Branch:** Branch 2 (podium top-5)

**Before:**
> VenueHistory 66.2/100 — 3 starts — podium-caliber Renaissance result (T2 in 2024) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.042. 2025 recency bonus: +0.05.

**After:**
> VenueHistory 70.8/100 — 3 starts — podium-caliber Renaissance result (T2 in 2024) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.042. 2025 recency bonus: +0.05.

---

### Viktor Hovland

**Branch:** Branch 3 (recent top-15)

**Before:**
> VenueHistory 52.1/100 — 4 starts but recent Renaissance result T11 in 2025 marks a usable course reference at this venue. Course-history adj -0.014. 2025 recency bonus: +0.05.

**After:**
> VenueHistory 51.9/100 — 4 starts but recent Renaissance result T11 in 2025 marks a usable course reference at this venue. Course-history adj -0.014. 2025 recency bonus: +0.05.

---

### Robert Macintyre

**Branch:** Branch 1 (winner/defending)

**Before:**
> VenueHistory 81.0/100 — 2024 winner at The Renaissance Club (5 starts) — venue win is the deepest possible course calibration. 2 top-15 results from 24 rounds. Course-history adj +0.077. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 84.6/100 — 2024 winner at The Renaissance Club (5 starts) — venue win is the deepest possible course calibration. 2 top-15 results from 24 rounds. Course-history adj +0.077. 2025 recency bonus: -0.05.

---

### Shane Lowry

**Branch:** Branch 3 (recent top-15)

**Before:**
> VenueHistory 47.7/100 — limited sample (1 start) but recent Renaissance result T12 in 2023 removes true-debut uncertainty. Course-history adj +0.011.

**After:**
> VenueHistory 47.1/100 — limited sample (1 start) but recent Renaissance result T12 in 2023 removes true-debut uncertainty. Course-history adj +0.011.

---

### Kristoffer Reitan

**Branch:** Branch 3 (recent top-15)

**Before:**
> VenueHistory 52.9/100 — limited sample (1 start) but recent Renaissance result T13 in 2025 removes true-debut uncertainty. Course-history adj +0.010. 2025 recency bonus: +0.05.

**After:**
> VenueHistory 52.6/100 — limited sample (1 start) but recent Renaissance result T13 in 2025 removes true-debut uncertainty. Course-history adj +0.010. 2025 recency bonus: +0.05.

---

### Harris English

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 60.9/100 — depth=MODERATE, 3 starts (12 rounds). Best finish: T22 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 58.3/100 — depth=MODERATE, 3 starts (12 rounds). Best finish: T22 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Justin Thomas

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 42.2/100 — depth=MODERATE, 5 starts (22 rounds). Best finish: T8 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 42.4/100 — depth=MODERATE, 5 starts (22 rounds). Best finish: T8 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Doug Ghim

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 47.6/100 — depth=MODERATE, 3 starts (8 rounds). Best finish: T16 (2022). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 47.0/100 — depth=MODERATE, 3 starts (8 rounds). Best finish: T16 (2022). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Victor Perez

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 77.4/100 — depth=STRONG, 5 starts (26 rounds). Best finish: T10 (2024). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 71.1/100 — depth=STRONG, 5 starts (26 rounds). Best finish: T10 (2024). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration. 2025 recency bonus: -0.05.

---

### Bud Cauley

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 38.6/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. Best finish: T55. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 38.3/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. Best finish: T55. 2025 recency bonus: -0.05.

---

### Alex Fitzpatrick

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 39.7/100 — depth=THIN, 2 starts (4 rounds). No made-cut finish recorded. Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

**After:**
> VenueHistory 40.3/100 — depth=THIN, 2 starts (4 rounds). No made-cut finish recorded. Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

---

### Matt Wallace

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 57.4/100 — depth=STRONG, 5 starts (24 rounds). Best finish: T26 (2021). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 54.2/100 — depth=STRONG, 5 starts (24 rounds). Best finish: T26 (2021). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: -0.05.

---

### Min Woo Lee

**Branch:** Branch 1 (winner/defending)

**Before:**
> VenueHistory 49.8/100 — 2021 winner at The Renaissance Club (4 starts) — venue win is the deepest possible course calibration. 1 top-15 result from 18 rounds. Course-history adj -0.020.

**After:**
> VenueHistory 59.3/100 — 2021 winner at The Renaissance Club (4 starts) — venue win is the deepest possible course calibration. 1 top-15 result from 18 rounds. Course-history adj -0.020.

---

### Nick Taylor

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 66.4/100 — depth=STRONG, 4 starts (16 rounds). Best finish: T19 (2023). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 62.9/100 — depth=STRONG, 4 starts (16 rounds). Best finish: T19 (2023). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Jordan Smith

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 59.8/100 — depth=STRONG, 5 starts (22 rounds). Best finish: T12 (2023). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration.

**After:**
> VenueHistory 57.4/100 — depth=STRONG, 5 starts (22 rounds). Best finish: T12 (2023). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration.

---

### Alex Smalley

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 53.6/100 — depth=MODERATE, 3 starts (10 rounds). Best finish: T10 (2022). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration.

**After:**
> VenueHistory 52.1/100 — depth=MODERATE, 3 starts (10 rounds). Best finish: T10 (2022). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration.

---

### Jake Knapp

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 47.4/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. Best finish: T22.

**After:**
> VenueHistory 46.9/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. Best finish: T22.

---

### Alex Noren

**Branch:** Branch 3 (recent top-15)

**Before:**
> VenueHistory 54.4/100 — 4 starts but recent Renaissance result T10 in 2024 marks a usable course reference at this venue. Course-history adj +0.011.

**After:**
> VenueHistory 52.8/100 — 4 starts but recent Renaissance result T10 in 2024 marks a usable course reference at this venue. Course-history adj +0.011.

---

### Ryan Fox

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 50.5/100 — depth=MODERATE, 5 starts (24 rounds). Best finish: T12 (2023). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 48.4/100 — depth=MODERATE, 5 starts (24 rounds). Best finish: T12 (2023). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern. 2025 recency bonus: -0.05.

---

### Corey Conners

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 49.3/100 — depth=MODERATE, 5 starts (18 rounds). Best finish: T10 (2024). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 47.4/100 — depth=MODERATE, 5 starts (18 rounds). Best finish: T10 (2024). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern. 2025 recency bonus: -0.05.

---

### Sahith Theegala

**Branch:** Branch 2 (podium top-5)

**Before:**
> VenueHistory 49.3/100 — THIN sample (2 starts) but podium-caliber Renaissance result (T4 in 2024) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.011.

**After:**
> VenueHistory 55.5/100 — THIN sample (2 starts) but podium-caliber Renaissance result (T4 in 2024) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.011.

---

### Brian Harman

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 47.7/100 — depth=MODERATE, 4 starts (14 rounds). Best finish: T12 (2023). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 46.0/100 — depth=MODERATE, 4 starts (14 rounds). Best finish: T12 (2023). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern. 2025 recency bonus: -0.05.

---

### Ryan Gerard

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 33.3/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. Best finish: T74. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 33.8/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. Best finish: T74. 2025 recency bonus: -0.05.

---

### Eric Cole

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 46.7/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T46 (2024). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 46.2/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T46 (2024). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Ewen Ferguson

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 66.4/100 — depth=STRONG, 4 starts (16 rounds). Best finish: T12 (2023). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration.

**After:**
> VenueHistory 62.9/100 — depth=STRONG, 4 starts (16 rounds). Best finish: T12 (2023). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration.

---

### Daniel Hillier

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 56.1/100 — depth=MODERATE, 3 starts (10 rounds). Best finish: T46 (2024). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 54.2/100 — depth=MODERATE, 3 starts (10 rounds). Best finish: T46 (2024). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Sepp Straka

**Branch:** Branch 3 (recent top-15)

**Before:**
> VenueHistory 59.7/100 — 3 starts but recent Renaissance result T7 in 2025 establishes meaningful course familiarity. Course-history adj +0.014. 2025 recency bonus: +0.10.

**After:**
> VenueHistory 59.4/100 — 3 starts but recent Renaissance result T7 in 2025 establishes meaningful course familiarity. Course-history adj +0.014. 2025 recency bonus: +0.10.

---

### Rasmus Neergaard-Petersen

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 40.8/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 41.2/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Marco Penge

**Branch:** Branch 2 (podium top-5)

**Before:**
> VenueHistory 68.7/100 — THIN sample (1 start) but podium-caliber Renaissance result (T2 in 2025) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.041. 2025 recency bonus: +0.15.

**After:**
> VenueHistory 75.1/100 — THIN sample (1 start) but podium-caliber Renaissance result (T2 in 2025) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj +0.041. 2025 recency bonus: +0.15.

---

### Michael Kim

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 47.4/100 — depth=THIN, 2 starts (6 rounds). Best finish: T34 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 46.9/100 — depth=THIN, 2 starts (6 rounds). Best finish: T34 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Andrew Novak

**Branch:** Branch 3 (recent top-15)

**Before:**
> VenueHistory 47.6/100 — 3 starts but recent Renaissance result T13 in 2025 establishes meaningful course familiarity. Course-history adj -0.018. 2025 recency bonus: +0.05.

**After:**
> VenueHistory 48.1/100 — 3 starts but recent Renaissance result T13 in 2025 establishes meaningful course familiarity. Course-history adj -0.018. 2025 recency bonus: +0.05.

---

### Haotong Li

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 64.7/100 — depth=STRONG, 5 starts (20 rounds). Best finish: T21 (2024). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 61.4/100 — depth=STRONG, 5 starts (20 rounds). Best finish: T21 (2024). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Thorbjorn Olesen

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 64.0/100 — depth=STRONG, 5 starts (22 rounds). Best finish: T25 (2023). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 59.8/100 — depth=STRONG, 5 starts (22 rounds). Best finish: T25 (2023). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: -0.05.

---

### Antoine Rozner

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 55.0/100 — depth=MODERATE, 5 starts (18 rounds). Best finish: T22 (2025). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 53.3/100 — depth=MODERATE, 5 starts (18 rounds). Best finish: T22 (2025). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Harry Hall

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 56.4/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T17 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: +0.05.

**After:**
> VenueHistory 55.6/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T17 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: +0.05.

---

### Brandt Snedeker

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 40.5/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 41.0/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Matt Mccarty

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 50.5/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. Best finish: T22.

**After:**
> VenueHistory 49.5/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. Best finish: T22.

---

### Rasmus Hojgaard

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 47.3/100 — depth=MODERATE, 5 starts (18 rounds). Best finish: T10 (2022). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 46.7/100 — depth=MODERATE, 5 starts (18 rounds). Best finish: T10 (2022). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Bernd Wiesberger

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 56.4/100 — depth=STRONG, 3 starts (16 rounds). Best finish: T26 (2021). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 54.5/100 — depth=STRONG, 3 starts (16 rounds). Best finish: T26 (2021). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Max Mcgreevy

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 41.4/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 41.8/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Nico Echavarria

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 49.6/100 — depth=THIN, 2 starts (6 rounds). Best finish: T22 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 48.7/100 — depth=THIN, 2 starts (6 rounds). Best finish: T22 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Tom Mckibbin

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 49.9/100 — depth=THIN, 2 starts (6 rounds). Best finish: T35 (2023). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 49.0/100 — depth=THIN, 2 starts (6 rounds). Best finish: T35 (2023). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Sam Stevens

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 32.8/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T57 (2024). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 33.5/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T57 (2024). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern. 2025 recency bonus: -0.05.

---

### Andrew Putnam

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 58.5/100 — depth=MODERATE, 3 starts (12 rounds). Best finish: T42 (2023). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 56.2/100 — depth=MODERATE, 3 starts (12 rounds). Best finish: T42 (2023). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Dan Brown

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 48.4/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T60 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 46.6/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T60 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: -0.05.

---

### Austin Eckroat

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 42.8/100 — depth=THIN, 2 starts (6 rounds). Best finish: T65 (2023). Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

**After:**
> VenueHistory 42.9/100 — depth=THIN, 2 starts (6 rounds). Best finish: T65 (2023). Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

---

### Dan Bradbury

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 30.8/100 — depth=MODERATE, 3 starts (8 rounds). Best finish: T75 (2023). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 32.8/100 — depth=MODERATE, 3 starts (8 rounds). Best finish: T75 (2023). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Chris Kirk

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 35.3/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. Best finish: T71.

**After:**
> VenueHistory 36.6/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. Best finish: T71.

---

### Keita Nakajima

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 38.9/100 — depth=THIN, 2 starts (6 rounds). Best finish: T55 (2025). Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 38.6/100 — depth=THIN, 2 starts (6 rounds). Best finish: T55 (2025). Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment. 2025 recency bonus: -0.05.

---

### John Parry

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 43.2/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. Best finish: T55. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 42.2/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. Best finish: T55. 2025 recency bonus: -0.05.

---

### Paul Waring

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 38.1/100 — depth=MODERATE, 3 starts (10 rounds). No made-cut finish recorded. Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 39.0/100 — depth=MODERATE, 3 starts (10 rounds). No made-cut finish recorded. Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Billy Horschel

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 44.2/100 — depth=MODERATE, 4 starts (12 rounds). Best finish: T54 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 44.1/100 — depth=MODERATE, 4 starts (12 rounds). Best finish: T54 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Sungjae Im

**Branch:** Branch 2 (podium top-5)

**Before:**
> VenueHistory 43.7/100 — 4 starts — podium-caliber Renaissance result (T4 in 2024) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj -0.018.

**After:**
> VenueHistory 50.7/100 — 4 starts — podium-caliber Renaissance result (T4 in 2024) — top-5 finish provides real venue-specific proof independent of sample volume. Course-history adj -0.018.

---

### Chandler Phillips

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 42.6/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 42.8/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Padraig Harrington

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 67.8/100 — depth=STRONG, 5 starts (22 rounds). Best finish: T18 (2021). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 63.0/100 — depth=STRONG, 5 starts (22 rounds). Best finish: T18 (2021). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: -0.05.

---

### Andy Sullivan

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 69.9/100 — depth=STRONG, 3 starts (16 rounds). Best finish: T17 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: +0.05.

**After:**
> VenueHistory 67.0/100 — depth=STRONG, 3 starts (16 rounds). Best finish: T17 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: +0.05.

---

### Alejandro Del Rey

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 54.0/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T15 (2024). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 51.3/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T15 (2024). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration. 2025 recency bonus: -0.05.

---

### Grant Forrest

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 92.1/100 — depth=STRONG, 5 starts (26 rounds). Best finish: T11 (2023). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration.

**After:**
> VenueHistory 84.7/100 — depth=STRONG, 5 starts (26 rounds). Best finish: T11 (2023). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration.

---

### Mark Hubbard

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 37.0/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 38.1/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Richard Sterne

**Branch:** Branch 5 (debut fallback)

**Before:**
> VenueHistory 39.8/100 — Renaissance debut — links-course learning curve applies even for elite players; course-specific hole knowledge gap on rerouted closing stretch (new Hole 15).

**After:**
> VenueHistory 40.5/100 — Renaissance debut — links-course learning curve applies even for elite players; course-specific hole knowledge gap on rerouted closing stretch (new Hole 15).

---

### Thriston Lawrence

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 54.3/100 — depth=MODERATE, 4 starts (10 rounds). Best finish: T24 (2022). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 52.7/100 — depth=MODERATE, 4 starts (10 rounds). Best finish: T24 (2022). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Frederic Lacroix

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 37.3/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 38.4/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Eugenio Chacarra

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 39.8/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 40.5/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Jesper Svensson

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 49.9/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T34 (2024). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 47.9/100 — depth=MODERATE, 2 starts (8 rounds). Best finish: T34 (2024). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: -0.05.

---

### Erik Van Rooyen

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 63.7/100 — depth=STRONG, 4 starts (20 rounds). Best finish: T39 (2024). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 60.7/100 — depth=STRONG, 4 starts (20 rounds). Best finish: T39 (2024). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Matteo Manassero

**Branch:** Branch 3 (recent top-15)

**Before:**
> VenueHistory 51.8/100 — limited sample (2 starts) but recent Renaissance result T15 in 2024 removes true-debut uncertainty. Course-history adj +0.019.

**After:**
> VenueHistory 50.6/100 — limited sample (2 starts) but recent Renaissance result T15 in 2024 removes true-debut uncertainty. Course-history adj +0.019.

---

### Matti Schmid

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 52.6/100 — depth=THIN, 2 starts (6 rounds). Best finish: T17 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: +0.05.

**After:**
> VenueHistory 52.3/100 — depth=THIN, 2 starts (6 rounds). Best finish: T17 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure. 2025 recency bonus: +0.05.

---

### Niklas Norgaard

**Branch:** Branch 3 (recent top-15)

**Before:**
> VenueHistory 50.5/100 — limited sample (2 starts) but recent Renaissance result T15 in 2024 removes true-debut uncertainty. Course-history adj +0.015.

**After:**
> VenueHistory 49.5/100 — limited sample (2 starts) but recent Renaissance result T15 in 2024 removes true-debut uncertainty. Course-history adj +0.015.

---

### Max Greyserman

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 49.0/100 — depth=THIN, 2 starts (6 rounds). Best finish: T21 (2024). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 48.2/100 — depth=THIN, 2 starts (6 rounds). Best finish: T21 (2024). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Kevin Yu

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 38.9/100 — depth=MODERATE, 3 starts (8 rounds). Best finish: T34 (2025). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 39.7/100 — depth=MODERATE, 3 starts (8 rounds). Best finish: T34 (2025). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Richard Mansell

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 61.1/100 — depth=MODERATE, 3 starts (10 rounds). Best finish: T10 (2024). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration.

**After:**
> VenueHistory 58.4/100 — depth=MODERATE, 3 starts (10 rounds). Best finish: T10 (2024). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration.

---

### Laurie Canter

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 38.9/100 — depth=MODERATE, 3 starts (12 rounds). Best finish: T34 (2025). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 39.7/100 — depth=MODERATE, 3 starts (12 rounds). Best finish: T34 (2025). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Connor Syme

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 67.0/100 — depth=STRONG, 5 starts (24 rounds). Best finish: T15 (2024). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 62.3/100 — depth=STRONG, 5 starts (24 rounds). Best finish: T15 (2024). Course familiarity established with at least one strong Renaissance result — partial structural edge from venue-specific calibration. 2025 recency bonus: -0.05.

---

### Joost Luiten

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 52.7/100 — depth=MODERATE, 3 starts (16 rounds). Best finish: T54 (2023). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 51.3/100 — depth=MODERATE, 3 starts (16 rounds). Best finish: T54 (2023). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Marcel Siem

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 64.3/100 — depth=MODERATE, 3 starts (12 rounds). Best finish: T34 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 61.2/100 — depth=MODERATE, 3 starts (12 rounds). Best finish: T34 (2025). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Matthieu Pavon

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 53.8/100 — depth=MODERATE, 5 starts (20 rounds). Best finish: T12 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 52.3/100 — depth=MODERATE, 5 starts (20 rounds). Best finish: T12 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Adrien Saddier

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 37.0/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 38.1/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Julien Guerrier

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 36.3/100 — depth=MODERATE, 4 starts (13 rounds). Best finish: T70 (2024). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 37.4/100 — depth=MODERATE, 4 starts (13 rounds). Best finish: T70 (2024). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Shaun Norris

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 37.5/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 38.5/100 — limited Renaissance history (1 start, 4 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Ashun Wu

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 64.3/100 — depth=STRONG, 4 starts (20 rounds). Best finish: T55 (2022). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 61.2/100 — depth=STRONG, 4 starts (20 rounds). Best finish: T55 (2022). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### David Ravetto

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 43.2/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 43.3/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Aldrich Potgieter

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 38.9/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 39.7/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Darius Van Driel

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 44.8/100 — depth=MODERATE, 3 starts (8 rounds). Best finish: T54 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 44.7/100 — depth=MODERATE, 3 starts (8 rounds). Best finish: T54 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Nicolai Von Dellingshausen

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 42.2/100 — depth=THIN, 2 starts (4 rounds). No made-cut finish recorded. Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

**After:**
> VenueHistory 42.4/100 — depth=THIN, 2 starts (4 rounds). No made-cut finish recorded. Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

---

### Adrian Otaegui

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 58.0/100 — depth=MODERATE, 5 starts (22 rounds). Best finish: T26 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 55.8/100 — depth=MODERATE, 5 starts (22 rounds). Best finish: T26 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Rikuya Hoshino

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 42.3/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 42.6/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Johannes Veerman

**Branch:** Branch 3 (recent top-15)

**Before:**
> VenueHistory 50.1/100 — 3 starts but recent Renaissance result T8 in 2021 establishes meaningful course familiarity. Course-history adj +0.008.

**After:**
> VenueHistory 49.1/100 — 3 starts but recent Renaissance result T8 in 2021 establishes meaningful course familiarity. Course-history adj +0.008.

---

### Jacques Kruyswijk

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 42.3/100 — limited Renaissance history (1 start, 6 rounds) — partial calibration only; no top-end venue result yet. Best finish: T65. 2025 recency bonus: -0.05.

**After:**
> VenueHistory 41.5/100 — limited Renaissance history (1 start, 6 rounds) — partial calibration only; no top-end venue result yet. Best finish: T65. 2025 recency bonus: -0.05.

---

### Jordan Gumberg

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 48.7/100 — depth=THIN, 2 starts (4 rounds). No made-cut finish recorded. Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 47.9/100 — depth=THIN, 2 starts (4 rounds). No made-cut finish recorded. Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Yuto Katsuragawa

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 26.3/100 — depth=THIN, 2 starts (4 rounds). No made-cut finish recorded. Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

**After:**
> VenueHistory 29.0/100 — depth=THIN, 2 starts (4 rounds). No made-cut finish recorded. Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

---

### Calum Hill

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 55.5/100 — depth=MODERATE, 4 starts (19 rounds). Best finish: T25 (2023). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 53.7/100 — depth=MODERATE, 4 starts (19 rounds). Best finish: T25 (2023). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Taylor Moore

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 31.3/100 — depth=THIN, 2 starts (4 rounds). No made-cut finish recorded. Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

**After:**
> VenueHistory 33.2/100 — depth=THIN, 2 starts (4 rounds). No made-cut finish recorded. Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

---

### Scott Jamieson

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 54.4/100 — depth=MODERATE, 3 starts (14 rounds). No made-cut finish recorded. Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 52.8/100 — depth=MODERATE, 3 starts (14 rounds). No made-cut finish recorded. Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Joakim Lagergren

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 58.9/100 — depth=STRONG, 3 starts (16 rounds). Best finish: T35 (2021). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 56.6/100 — depth=STRONG, 3 starts (16 rounds). Best finish: T35 (2021). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Junghwan Lee

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 44.6/100 — depth=THIN, 2 starts (6 rounds). Best finish: T46 (2024). Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

**After:**
> VenueHistory 44.5/100 — depth=THIN, 2 starts (6 rounds). Best finish: T46 (2024). Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

---

### Guido Migliozzi

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 60.2/100 — depth=STRONG, 5 starts (22 rounds). Best finish: T35 (2021). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 57.6/100 — depth=STRONG, 5 starts (22 rounds). Best finish: T35 (2021). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Brian Campbell

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 38.3/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 39.1/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Cam Davis

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 46.5/100 — depth=THIN, 2 starts (6 rounds). Best finish: T26 (2024). Partial calibration of venue-specific scoring patterns through repeated course exposure.

**After:**
> VenueHistory 46.1/100 — depth=THIN, 2 starts (6 rounds). Best finish: T26 (2024). Partial calibration of venue-specific scoring patterns through repeated course exposure.

---

### Dylan Naidoo

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 39.2/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 39.9/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Adrian Meronk

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 38.6/100 — depth=MODERATE, 3 starts (8 rounds). Best finish: T59 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 39.4/100 — depth=MODERATE, 3 starts (8 rounds). Best finish: T59 (2021). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Dylan Frittelli

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 39.7/100 — depth=MODERATE, 4 starts (10 rounds). Best finish: T47 (2022). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 40.3/100 — depth=MODERATE, 4 starts (10 rounds). Best finish: T47 (2022). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Joe Highsmith

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 34.6/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 36.0/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Davis Riley

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 44.5/100 — depth=MODERATE, 3 starts (8 rounds). Best finish: T35 (2023). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 44.4/100 — depth=MODERATE, 3 starts (8 rounds). Best finish: T35 (2023). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Charley Hoffman

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 46.8/100 — depth=MODERATE, 3 starts (10 rounds). Best finish: T57 (2024). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 46.4/100 — depth=MODERATE, 3 starts (10 rounds). Best finish: T57 (2024). Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Danny Willett

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 17.3/100 — depth=MODERATE, 4 starts (10 rounds). No made-cut finish recorded. Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 21.4/100 — depth=MODERATE, 4 starts (10 rounds). No made-cut finish recorded. Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Pablo Larrazabal

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 27.0/100 — depth=MODERATE, 4 starts (16 rounds). No made-cut finish recorded. Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

**After:**
> VenueHistory 29.6/100 — depth=MODERATE, 4 starts (16 rounds). No made-cut finish recorded. Deep course familiarity but historical scoring below expectation at Renaissance — volume of starts does not translate to a consistent contending pattern.

---

### Ryggs Johnston

**Branch:** Branch 5 (limited fallback)

**Before:**
> VenueHistory 39.2/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

**After:**
> VenueHistory 39.9/100 — limited Renaissance history (1 start, 2 rounds) — partial calibration only; no top-end venue result yet. No made-cut finish recorded.

---

### Ockie Strydom

**Branch:** Branch 4 (depth-by-sample)

**Before:**
> VenueHistory 40.6/100 — depth=THIN, 3 starts (6 rounds). No made-cut finish recorded. Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

**After:**
> VenueHistory 41.1/100 — depth=THIN, 3 starts (6 rounds). No made-cut finish recorded. Historical scoring below expectation at Renaissance — limited sample with negative course-history adjustment.

---

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