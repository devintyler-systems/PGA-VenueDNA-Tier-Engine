# VTS SYSTEM — QUICK REFERENCE CARD
## One-Page Cheat Sheet | June 2026

---

## THE ONE QUESTION THAT DRIVES EVERYTHING
> Given what THIS venue rewards and punishes — who in this field wins HERE?

---

## 5-TIER STRUCTURE
| Tier | VTS | Label | Bet? |
|------|-----|-------|------|
| 1 | 80+ | Course Architects | YES |
| 2 | 65–79 | Contention Windows | SITUATION |
| 3 | 50–64 | Top-10 Range | NO |
| 4 | 35–49 | Cut-Line Players | FADE |
| 5 | <35 | Mismatches | FADE HARD |

---

## DATA YOU NEED EVERY WEEK (DataGolf)
- True SG (tSG) — stabilized, not season avg
- Recent Form Index (RF)
- L5 event SG splits (OTT/APP/ARG/T2G/PUTT)
- Career venue SG (if 5+ starts → overrides form window)
- DK salary file

---

## RESULT QUALITY — APPLY BEFORE ANYTHING ELSE
- PGA Tour: 1.0x | DP World: 0.9x | Co-sanctioned: 0.85x | LIV: 0.6x | Dev: 0.5x

---

## FORM WINDOW DECAY
35% / 25% / 10% / 10% / 10% / 10% (recent → oldest)

---

## HARD GATES (non-negotiable)
- RF < 0.0 → −4 VTS penalty (any Tier 2 pick)
- RF < −0.5 → Tier 3 floor (regardless of tSG)
- Debut, elite player, no surface putting data → −9 minimum (not reducible on rank)
- Event split > tSG by 0.5+ → apply 0.7x regression to that split
- tSG >1.5 AND RF >1.0 → BET (even without event SG splits)

---

## AP PENALTIES: CONDITION-SENSITIVE
- All AP penalties: −30% on confirmed soft week (multi-day rain, saturated)
- ARG weight: IMMOVABLE — never decreases on weather adjustment
- Double discount (AP flag + LIV): hold MC, don't revise up without counter-evidence

---

## WEATHER BAND RULE
- Apply soft/firm blend to 36-hole scoring ONLY
- Recalibrate at the cut with actual conditions
- Single morning shower ≠ soft week (Aronimink lesson)
- Default: w_firm = 0.65 unless multi-day rain confirmed

---

## DEBUT PENALTY TABLE
| Category | Penalty |
|----------|---------|
| Standard (no history) | −11 |
| Elite (rank <30, no surface data) | −9 min |
| Comp specialist (win/T5 at similar venue) | −6 to −7 |
| Partial history (1–4 rounds) | −4 to −5 |

---

## LOCKED VENUE LIBRARY (June 2026)
| Venue | Event | Weight Matrix Lead Trait |
|-------|-------|--------------------------|
| Colonial CC | Charles Schwab | APP 30%, Par-4 16%, Putt 14% |
| Aronimink | PGA Championship | APP 34%, OTT 24%, LI 14% |
| TPC Craig Ranch | CJ Cup Byron Nelson | Putt 24%, APP, OTT |
| Harbour Town | RBC Heritage | [load from file] |
| Muirfield Village | Memorial | [load from file] |

---

## DK LINEUP RULES
- $50K cap, 6 players, brute-force combinations
- Scheffler at $13,500 = correctly priced — often outcompeted on pts/$ by 5 Tier 1/2 fits
- OTT SG floor: exclude < −0.20 at courses 7,200+ yards

---

## R1 DIAGNOSTIC HOLD PROTOCOL
- Do NOT downgrade Tier 2 after ONE bad R1
- Downgrade gate: 3+ strokes outside range AND structural miss (wrong zones, not noise)
- Promote any outside-projection player whose R1 warrants it

---

## POST-TOURNAMENT AUDIT (10 sections — MANDATORY)
1. Event ID + conditions
2. Accuracy metrics (T1→T10 rate, AP hit rate)
3. Tier 1/2 player review
4. Anti-pattern outcomes
5. Weight matrix adjustments
6. Model miss log
7. Debut penalty recalibration
8. Form/result quality review
9. R1 diagnostic review
10. Library write-back

---

## 5 FAILURE TESTS (run before every output)
1. Generic test — could this work without venue DNA?
2. Softness test — any hedging language?
3. Behavior delta test — are VTS differences meaningful?
4. Conviction test — do anti-pattern fades hold?
5. Audit test — can every projection be checked against an outcome?

---

## VTS vs. WORLD RANK EDGE SIGNAL
>40-spot gap between VTS tier and world rank = real edge. Press it.
(Cole world 117 / VTS Tier 2 → 2nd Colonial. Meissner world 108 / VTS Tier 2 → T3.)
