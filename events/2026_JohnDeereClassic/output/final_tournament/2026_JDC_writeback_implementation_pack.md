# 2026 JDC Write-Back Implementation Pack
*PGA VenueDNA Tier Engine | Source: 2026_JDC_audit_postmortem.md | Applied: 2026-07-05*

---

## Overview

This pack translates the HIGH-confidence write-back flags from the 2026 John Deere Classic post-mortem into exact, paste-ready changes for the scoring spec, learning loop, and Deere Run venue file. Only HIGH-confidence write-backs are applied here. MEDIUM and LOW flags are staged for multi-event confirmation.

Applied flags: WB-2026-JDC-001 (HIGH), WB-2026-JDC-004 (HIGH), WB-2026-JDC-006 (HIGH)
Staged for tracking: WB-2026-JDC-002 (MEDIUM), WB-2026-JDC-003 (LOW), WB-2026-JDC-005 (MEDIUM)

---

## WB-2026-JDC-001 — bomb_and_spray Soft/Wet Week Modifier

**Target file:** `library/engine/02_PGA_VENUEDNA_SCORING_SPEC.md` — Section 7.2.1

**Current rule:**
> Setup modifiers must be explicit, not intuitive. When `bomb_and_spray` is active and `fairway_width_class = wide`, reduce penalty by a bounded venue-defined percentage.

**Change applied:**
Added setup-conditional sizing guidance for `bomb_and_spray` and `rough_approach_liab`:

- `bomb_and_spray`: when weekly course conditions are classified `soft_wet` (rain-softened rough, adj_penalties < 0.20, or rough_moisture_class = wet), apply a 30–50% base penalty reduction. This is a venue-file modifier — not a global override. The concept remains valid; the magnitude is conditionally sized.
- `rough_approach_liab`: when rough is playing soft/wet (FW% > 65% OR rough_moisture_class = wet), apply a 20–40% base penalty reduction. The structural punishment of rough_approach_liab depends on rough severity and moisture; wet rough materially reduces penalty applicability.

**Evidence:**
- Gotterup (bomb_and_spray+rough_approach_liab, -2.67 SG penalty) WON at -20. OTT +5.41 (1st in field). Soft/wet week neutralized rough liability.
- Meissner (bomb_and_spray, -1.10 SG) finished T6 despite soft conditions.
- Spieth (bomb_and_spray, -1.24 SG) finished T58. Penalty directionally correct in drier conditions.
- Suber (rough_approach_liab, -1.11 SG) finished T6. Approach SG +3.73 (16th in field) in soft week.
- Anti-pattern over-penalized rate in this event: 4 of 7 applications (57%).

**Rollback condition:** If bomb_and_spray players again underperform at Deere in soft conditions over 2+ events, hold modifier. If they outperform in dry conditions, modifier is setup-specific and holds.

---

## WB-2026-JDC-004 — Thin-VHD Variance Band Widening

**Target file:** `library/engine/02_PGA_VENUEDNA_SCORING_SPEC.md` — Section 7.6 (new)

**Current rule:**
> VHD rounds 1–2: mention qualitatively only. VHD rounds 3–4: partial, blend conservatively.

**Change applied:**
Added explicit thin-VHD Tier 1 gate with variance band widening:

- VHD rounds < 6: VHD contribution capped at ±1.0 VTS points; may not positively support Tier 1.
- VHD rounds < 8 AND VHD ≤ +1.0: Tier 1 eligibility blocked unless venue file provides explicit override with documented justification.

**Evidence:**
- Koivun (Tier 1, VHD +0.024, 4 rounds) missed cut at +1. Only Tier 1 player; sole failure.
- VHD directional accuracy at ≥6 rounds: 5/5 (100%) in 2026 JDC.
- Homa (VHD +4.208, 10 rounds → T2), Meissner (VHD +1.986, 6 rounds → T6), Zach Johnson (VHD +2.135, 82 rounds → T9): all VHD correct at depth.

---

## WB-2026-JDC-006 — Tier 1 Gate: VHD Depth Requirement

**Target file:** `library/engine/02_PGA_VENUEDNA_SCORING_SPEC.md` — Section 9.1

**Current rule:**
> Tier eligibility precedence does not include a VHD-depth gate.

**Change applied:**
Added thin-VHD Tier 1 gate to the tier eligibility precedence order. Placement: between venue-specific anti-pattern cap and VenueFit minimum threshold.

**Evidence:** Same as WB-2026-JDC-004. The gate prevents a high-NeutralSkill player with thin venue history from occupying the engine's top tier slot.

---

## Staged Write-Backs (Not Yet Applied)

| Flag | Layer | Confidence | Status | Trigger for application |
|------|-------|------------|--------|------------------------|
| WB-2026-JDC-002 | VFD | MEDIUM | Staged | 2+ birdie-fest events showing NeutralSkill > VFD predictive power |
| WB-2026-JDC-003 | DEBUT | LOW | Staged | 5+ debut-player events with B-class penalty applied |
| WB-2026-JDC-005 | NEUTRAL_SKILL | MEDIUM | Staged | ATG weight uplift at Deere Run profile — test against Travelers results first |

---

## Birdie-Fest Tier 3 Probability Trigger

**Target file:** `library/engine/03_PGA_VENUEDNA_LEARNING_LOOP.md` — Section 12

**Current rule:**
> Probability calibration review asks: were longshot top-10 outcomes underrepresented?

**Change applied:**
Added explicit birdie-fest venue flag to the calibration review checklist: at venues with high birdie conversion rate and standard variance class, Tier 3 top-10 probability floors may be too compressed. The NeutralSkill advantage gap compresses at scoring-fest tracks — Tier 3 players require higher top-10 probability than at tight/penal venues.

**Evidence:** 5 of 11 top-10 finishers at 2026 JDC were Tier 3 players. No structural model fix — but probability floors need venue-class adjustment.

---

## Deere Run Venue File Append

**Target file:** `events/2026_JohnDeereClassic/output/TPC_DEERE_RUN_INTELLIGENCE_2026_v1.md`

Post-event write-back block appended confirming:
- Birdie-fest conversion venue: confirmed.
- bomb_and_spray and rough_approach_liab: concepts valid, magnitudes setup-conditional.
- Soft/wet Deere weeks: apply penalty reductions for both anti-patterns.
- Tier 3 probability review trigger: active for next Deere event.

---

*Implementation pack generated: 2026-07-05 | Audited by: VenueDNA Engine Post-Event Protocol v1*
