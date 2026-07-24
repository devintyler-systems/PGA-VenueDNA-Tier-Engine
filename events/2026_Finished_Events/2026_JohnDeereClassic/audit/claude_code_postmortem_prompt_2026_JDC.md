# 2026 John Deere Classic — Full Post-Mortem & Final Tournament Tab
## Claude Code Execution Prompt

---

## CONTEXT LOCK

**Event:** 2026 John Deere Classic  
**Venue:** TPC Deere Run, Silvis, Illinois  
**Live Board:** https://2026-johndeereclassic-venuedna.netlify.app/  
**GitHub Repo:** https://github.com/devintyler83/PGA-VenueDNA-Tier-Engine  
**Output Files Location:** `C:\PGA_VenueDNA\events\2026_JohnDeereClassic\output\final_tournament\`

**Available Final Data Files (in output/final_tournament/):**
- `final_leaderboard.csv` — Full final leaderboard, POS, player, total, R1–R4, total strokes
- `final_tournament_player_strokes_gained.csv` — Full SG breakdown (OTT, Approach, ATG, Putting, Total) with ranks
- `final_tournament_course_stats.csv` — Hole-by-hole scoring data (par, yards, avg, rank, +/-, eagles, birdies, pars, bogeys, dbl+)
- `final_tournament_course_insights_datagolf.csv` — DataGolf venue-fit insights
- Pre-tournament VTS file: `C:\PGA_VenueDNA\events\2026_JohnDeereClassic\output\2026_john_deere_classic_vts_full.csv`

**Confirmed Final Results:**
- Winner: Chris Gotterup (-20, 264) — SG: OTT +5.41 (1st), App -0.04 (52nd), ATG +2.13 (13th), Putt +5.40 (5th), Total +12.91 (1st)
- Runner-Up: Max Homa (-19, 265) — SG: OTT +1.59, App +3.43, ATG +3.81 (2nd), Putt +3.06, Total +11.91 (2nd)
- T3: Lucas Glover, Lee Hodges (-18, 266 each)
- Cut line: -2 (140 strokes)

---

## TASK 1 — FULL POST-MORTEM ANALYSIS

### Step 1: Build the Merged Audit Dataset

Join the pre-tournament VTS file to the final leaderboard using fuzzy name matching (use rapidfuzz or fuzzywuzzy, threshold 85). Produce `2026_JDC_audit_merged.csv` with these columns minimum:
- player_name, vts_rank, vts_tier, vts_final_raw, neutralskill_sg, vfd (VenueFitDelta), vhd (VenueHistoryDelta), anti_pattern_flags, anti_pattern_penalty_total, debut_flag, debut_penalty_applied, win_pct_projected, top10_pct_projected, makecut_pct_projected
- actual_pos, actual_total, actual_r1, actual_r2, actual_r3, actual_r4, actual_total_strokes
- sg_ott, sg_ott_rank, sg_approach, sg_approach_rank, sg_atg, sg_atg_rank, sg_putting, sg_putting_rank, sg_total, sg_total_rank
- made_cut (Y/N), miss_type (for notable misses), accountability_verdict

### Step 2: Accountability Verdicts

Apply this classification to every Tier 1 and Tier 2 player:
- **HIT**: Finished within projected probability range (e.g., top-10 if proj top10_pct > 35%)
- **PARTIAL HIT**: Direction correct but magnitude off (e.g., made cut but missed top 20)
- **MISS**: Finished materially below model expectation
- **JUSTIFIED MISS**: Finish below expectation but explainable by known model variance rule (e.g., debut player, thin VHD history)

### Step 3: Winner Deep Dive — Gotterup

Gotterup was **Tier 2, VTS 73.0, rank 7** pre-tournament.
- NeutralSkill: 1.44 SG (high)
- VFD: -24.8 (large negative — poor venue comp fit)
- VHD: +2.71 (positive — moderate venue history edge)
- Anti-pattern flags: `bombandspray + roughapproachliab` → -2.67 SG total penalty
- Projected win%: ~1.49%, top10%: ~29.9%

Actual result: WON at -20. SG OTT 1st in field at +5.41.

**Required analysis:**
1. Was the -24.8 VFD too aggressive? Gotterup's OTT dominated — comp courses may have undervalued his profile.
2. Was the bombandspray anti-pattern over-penalized given soft/wet course conditions that week?
3. The model had him in the contention window but not as a win favorite. Classify: was this a valid low-probability outcome, or a systematic miss that warrants a rule change?
4. Output a root-cause statement: `CAUSE: [layer] | SEVERITY: [LOW/MEDIUM/HIGH] | WRITE_BACK: [Y/N]`

### Step 4: Runner-Up Analysis — Homa

Homa was **Tier 2, VTS 70.9, rank 13** pre-tournament.
- NeutralSkill: 0.49 SG
- VFD: -11.8
- VHD: +4.21 (10 rounds history, good)
- No anti-pattern flags

Actual: 2nd place, -19. SG Approach 3.43 (20th), ATG 3.81 (2nd), Putting 3.06 (25th).

Classify as **PARTIAL HIT** — projected in contention window, delivered. Note: NeutralSkill undervalued his ATG and approach ceiling. Flag whether ATG weight in NeutralSkill calculation should increase for TPC Deere Run.

### Step 5: Top-10 Coverage Accuracy Table

Build a table: for each actual top-10 finisher (Gotterup, Homa, Glover, Hodges, Kohles, Meissner, Suber, Ghim, Hisatsune, Johnson, Blair — 11 players total in top-9 due to ties), show:
- Player | Actual Finish | Pre-Tournament Tier | Pre-Tournament VTS Rank | Projected Top10% | Result

Calculate:
- **Tier 1 players in top 10**: count and %
- **Tier 2 players in top 10**: count and %
- **Tier 3+ or NM players in top 10**: count (model misses or unmodeled)
- **Top-10 Coverage Rate**: (T1+T2 players who finished top 10) / total top-10 finishers

### Step 6: Critical Miss — Jackson Koivun (Tier 1, CUT)

Koivun was **Tier 1, VTS 82.9, rank 1** pre-tournament.
- NeutralSkill: 0.93 SG
- VFD: -5.3
- VHD: +0.04 (4 rounds — thin)
- No anti-pattern flags
- Projected makecut%: 92%, win%: 2.85%

Actual: CUT at +1 (143 total). This is the most significant model miss.

**Required analysis:**
1. Was there any in-week data (weather, tee times, pairing context) that would have explained this?
2. Is thin VHD (4 rounds) a meaningful risk factor that the model should weight higher?
3. Was NeutralSkill 0.93 validated or contradicted by his SG splits? (Note: SG data not available for cut players — state this gap)
4. Classify the miss layer: NEUTRAL_SKILL | VFD | VHD | ANTI_PATTERN | VARIANCE | DATA_QUALITY
5. Recommend a write-back flag if the layer is structural

### Step 7: Anti-Pattern Validation Table

Build `2026_JDC_antipattern_review.csv` with:
- Player | Anti-Pattern Flag | Penalty Applied | Actual Finish | Made Cut | Relevant SG Category | Predicted Correctly? | Notes

Key cases to analyze:
- **Gotterup** — `bombandspray+roughapproachliab` → -2.67 SG → WON with OTT 1st. FLAG: overcorrection in soft conditions.
- **Meissner** — `bombandspray` → -1.10 SG → T6. FLAG: partial overcorrection.
- **Spieth** — `bombandspray` → -1.24 SG → T58. Penalty correct direction, magnitude check.
- **Suber** — `roughapproachliab` → -1.11 SG → T6. FLAG: overcorrection.
- **Poston** — `roughapproachliab` → -1.18 SG → T51. Roughly correct.
- **Brennan** — `roughapproachliab` → -1.39 SG → T33. Slight overcorrection.
- **Yellamaraju** — `roughapproachliab` → -1.11 SG → CUT. Penalty directionally correct.

Verdict for each: CORRECT | OVER-PENALIZED | UNDER-PENALIZED

### Step 8: Debut Player Review

Build `2026_JDC_debut_review.csv`:
- Player | Debut Class | Debut Penalty | VTS Post-Penalty | Actual Finish | Made Cut | Verdict

Players: Bauchou (T67, -4), Brennan (T33, -11), Yellamaraju (CUT, -2)

Assess: Is the B-class debut penalty of -1.75 SG calibrated correctly? Mixed results (Brennan outperformed; Yellamaraju and Bauchou underperformed relative to non-debut tier peers).

### Step 9: VHD Validation

Build `2026_JDC_vhd_validation.csv`:
- Player | VHD Score | VHD Rounds | Actual SG Total | Actual Finish | VHD Direction Correct?

Run a simple directional test: did players with positive VHD outperform players with similar NeutralSkill but neutral/negative VHD?

Key data points:
- Homa VHD +4.21 (10 rds) → T2 (strong)
- Meissner VHD +1.99 (6 rds) → T6 (strong)
- Bradley VHD -1.82 (8 rds) → T26 (below tier expectation)
- Bezuidenhout VHD +0.58 (8 rds) → T12 (above tier expectation)
- Koivun VHD +0.04 (4 rds) → CUT (VHD thin — miss)

### Step 10: Cut Model Calibration

The model used center 48%, logistic scaling, steepness 0.07.
Actual cut: -2 (140 strokes).

Report:
- Which T1/T2 players who were projected >80% makecut actually missed?
- Which players projected <50% makecut actually made it?
- Was the center (48%) appropriate for this field and conditions?
- Recommend center adjustment if systematic bias is found.

### Step 11: Course DNA Confirmation via SG Data

Using the actual SG data, assess each course DNA claim:
| DNA Trait | Pre-Tournament Priority | Actual Winner SG Evidence | Confirmed? |
|---|---|---|---|
| Par 5 attack / birdie-fest scoring | HIGH | Lee Hodges putting 8.93 (1st), hole 2 and 14 top birdies | CONFIRM/CHALLENGE |
| Putting premium | HIGH | Gotterup putting +5.40 (5th); Hodges +8.93 (1st) | assess |
| OTT importance | MODERATE | Gotterup OTT 1st (+5.41) | assess |
| Approach proximity | MODERATE | Glover approach 9.04 (1st) | assess |
| Bomb-and-spray risk | ANTI-PATTERN | Gotterup won despite flag | CHALLENGED |

Also: map hole-by-hole scoring data to confirm which holes created the most separation. Holes 2, 10, 14, 17 are Par 5s — verify they were the top birdie sources from `final_tournament_course_stats.csv`.

### Step 12: Write-Back Flags

Build `2026_JDC_writeback_flags.csv` and include in the post-mortem document. Format:

| FLAG_ID | LAYER | CURRENT RULE | PROPOSED CHANGE | EVIDENCE | CONFIDENCE |
|---|---|---|---|---|---|
| WB-2026-JDC-001 | ANTI_PATTERN | bombandspray penalty not conditioned on course conditions | Add a soft/wet week modifier: reduce bombandspray penalty by 30-50% when course is playing soft (FW% > 65%, rough approach penalty softened) | Gotterup won with OTT 1st despite -2.67 bombandspray penalty | HIGH |
| WB-2026-JDC-002 | VFD | VFD weight at birdie-fest flat venues | Consider reducing VFD weight at venues where NeutralSkill dominance is historically higher | Top-10 winners split across VFD ranges; NeutralSkill SG correlated more cleanly | MEDIUM |
| WB-2026-JDC-003 | DEBUT | B-class debut penalty -1.75 SG | Re-evaluate B-class penalty; Brennan outperformed as debut by 2+ tiers | Single-event evidence; flag for calibration across 5+ debut events | LOW |
| WB-2026-JDC-004 | VHD | Thin VHD (<6 rounds) as variance amplifier | Apply variance band widening when VHD rounds < 6; do not allow thin VHD to support Tier 1 designation without explicit gate | Koivun Tier 1 with only 4 VHD rounds missed cut | HIGH |

Add any additional flags you identify from the data.

---

## TASK 2 — ADD FINAL TOURNAMENT TAB TO BOARD

### Instructions:

1. **Fetch the current board source** from the Netlify deploy or GitHub repo. The board is deployed from the `PGA-VenueDNA-Tier-Engine` GitHub repo. Check both the root and any `events/` or `deploy/` directories for the board HTML.

2. **Locate the tab navigation system** in the existing HTML. The board likely uses a tab pattern with buttons or anchors. Add a new tab: `"Final Tournament"` (id: `final-tournament-tab`).

3. **Build the Final Tournament tab panel** with these sections (in order):

#### A. Final Leaderboard Table
```
Columns: Pos | Tier Badge | Player | Total | R1 | R2 | R3 | R4 | Strokes | Made Cut
```
- Tier badge: pill/chip showing T1 / T2 / T3 / T4 / T5 / NM (not modeled)
- Pos 1 row: gold highlight
- Pos 2 row: silver highlight
- T3 rows: bronze highlight
- CUT rows: muted/greyed out
- Filterable dropdown by Tier
- Sortable by Total, R4, or SG Total

#### B. Strokes Gained Dashboard
- Stacked horizontal bar chart for top-10 finishers showing OTT / Approach / ATG / Putting
- Use Chart.js (already on CDN if existing board uses it, otherwise add)
- SG Category Leaders mini-table: Category | Leader | Value | Tier
- Key stat callouts as large metric cards:
  - "Winner OTT Rank: #1 (+5.41 SG)" 
  - "Winner Putting Rank: #5 (+5.40 SG)"
  - "Top-10 Coverage: [calculate]%"

#### C. Model Scorecard
Visual grid of accuracy metrics:
- Tier 1 Coverage Rate (large number + color)
- Tier 2 Coverage Rate
- Anti-Pattern Accuracy Rate
- Debut Accuracy Rate
- Cut Model Accuracy
Each as a stat card with label, value, and a PASS / WARN / FAIL badge.

#### D. Winner Profile Card — Chris Gotterup
Card layout:
- Left: Player name, final score, finish
- Right: Pre-tournament projection snapshot (Tier 2, Rank 7, Win% 1.49%, Top10% 29.9%)
- SG trait bar: OTT/App/ATG/Putt
- Anti-Pattern Alert box: "bombandspray flag applied (-2.67 SG) → Actual OTT: +5.41 (1st) → Recommended: Soft-Week Penalty Reduction"
- Model Verdict badge: LOW-PROB HIT / WRITE-BACK TRIGGERED

#### E. Miss Log Table
Columns: Player | Pre-Tier | VTS Rank | Projected Win% | Projected Top10% | Actual Finish | Miss Type | Engine Layer | Write-Back

#### F. Course DNA Confirmation Panel
- Traits listed with CONFIRMED ✓ / CHALLENGED ✗ / PARTIAL ⚠ badges
- Hole scoring bar chart (18 holes, height = birdies, color = +/- vs par)
- Label top birdie holes (2, 10, 14, 17)

#### G. Write-Back Recommendations
Card grid — one card per flag:
- Flag ID (bold)
- Layer badge
- Current rule (small text)
- Proposed change (highlighted)
- Confidence: HIGH / MEDIUM / LOW badge

### Design Requirements:
- Match the existing board's dark-mode aesthetic exactly
- Use the same CSS variables, font stack, and component patterns already in the board
- Do NOT introduce new color systems or frameworks
- All charts use the same chart library already in the board
- Tab panel should be fully responsive (mobile collapses to stacked sections)
- All tables are sortable and filterable where noted
- Loading state: skeleton loaders for any async data rendering

---

## TASK 3 — ARTIFACT FILES

Save all outputs to: `C:\PGA_VenueDNA\events\2026_JohnDeereClassic\output\final_tournament\`

| File | Type | Description |
|---|---|---|
| `2026_JDC_audit_merged.csv` | CSV | Full joined pre/post dataset |
| `2026_JDC_audit_postmortem.md` | Markdown | Full written post-mortem |
| `2026_JDC_tier_accountability.csv` | CSV | Tier-by-tier accuracy |
| `2026_JDC_antipattern_review.csv` | CSV | Anti-pattern flag outcomes |
| `2026_JDC_writeback_flags.csv` | CSV | Engine write-back recommendations |
| `2026_JDC_vhd_validation.csv` | CSV | VHD vs actual outcomes |
| `2026_JDC_debut_review.csv` | CSV | Debut player outcomes |

Also push all artifacts to the GitHub repo at:
`/events/2026_JohnDeereClassic/output/final_tournament/`

---

## TASK 4 — DEPLOY

After building and verifying the Final Tournament tab:

1. If Netlify CLI is available: `netlify deploy --prod --dir=.`
2. If not: push the updated board file to the `main` branch of the GitHub repo. Netlify should auto-deploy via the connected build hook.
3. Verify the live board at `https://2026-johndeereclassic-venuedna.netlify.app/` shows the new tab.
4. If the board source is not in the GitHub repo (e.g., it was manually uploaded), locate the local board files and rebuild from scratch using the same design system, then deploy.

---

## EXECUTION GUIDANCE

**Parsing notes:**
- VTS CSV header row is concatenated without spaces — parse carefully. The actual data delimiter is standard comma.
- Use rapidfuzz (preferred) for player name matching across files. Set threshold to 85, manually verify any matches below 90.
- Cut players will have null SG values in the strokes gained file. Do not drop them; mark SG fields as NULL and made_cut as "N".
- The leaderboard uses "CUT" as the POS field for cut players. Strip leading/trailing whitespace from all string fields.

**Anti-pattern column parsing:**
- The `antipatternflags` field may contain multiple flags separated by commas or spaces (e.g., `bombandspray roughapproachliab`). Split and evaluate each independently.

**Post-mortem document format:**
- Use GitHub-Flavored Markdown
- Include a TL;DR summary at the top (max 200 words)
- Each section header should match the 12 sections outlined in Task 1
- Every major claim must cite the data source column/row
- End with a "Next Event Checklist" section listing the highest-priority write-backs to apply before the next modeled event

**Do not hallucinate:**
- If SG data is missing for a player, state it explicitly
- If a player name cannot be matched at 85%+ confidence, flag the row as UNMATCHED and list it separately
- If a field is not available in the source data, do not estimate or infer — mark as N/A

---

## FINAL DELIVERABLE SUMMARY

| # | Deliverable | Format | Location |
|---|---|---|---|
| 1 | Merged audit dataset | CSV | local + GitHub |
| 2 | Full post-mortem document | MD | local + GitHub |
| 3 | Tier accountability table | CSV | local + GitHub |
| 4 | Anti-pattern review | CSV | local + GitHub |
| 5 | Write-back flags | CSV | local + GitHub |
| 6 | VHD validation | CSV | local + GitHub |
| 7 | Debut review | CSV | local + GitHub |
| 8 | Final Tournament tab on live board | HTML/JS | Netlify |
| 9 | All files committed to repo | Files | GitHub main branch |

---

*PGA VenueDNA Tier Engine — Post-Event Audit Protocol v1*  
*2026 John Deere Classic | Event complete: July 5, 2026*  
*Audit triggered by: DevinTyler*
