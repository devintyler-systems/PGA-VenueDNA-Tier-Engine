# 05 — PGA VenueDNA Model Council Governance

**Version:** 1.1
**Status:** Canonical
**Scope:** Governance rules, council structure, trait override gates, schema modification authority

---

## 1. PURPOSE

The Model Council is VenueDNA's built-in quality control layer. It exists to:
- Challenge the engine's tier assignments before they become canonical
- Surface systematic over-rankings and under-rankings
- Produce objection records and no-change rulings that travel with every event package
- Approve or block schema modifications proposed by learning loop findings
- Prevent the canonical engine from drifting toward soft consensus or reputation-based ranking

The Council does not overrule the engine's math. It challenges inputs, weights, and interpretation — not arithmetic. Final tier assignments remain VenueDNA_final_projection unless a specific gate is triggered (see Section 4).

---

## 2. COUNCIL COMPOSITION

The Model Council operates as a structured review pass applied at two points in the event lifecycle:

**Pre-tournament council** (required before canonical status):
- Runs after all output files are generated but before deploy package is finalized
- Scope: Tier 1 assignments, Tier 5 fades, anti-pattern flags, DG vs. VenueDNA disagreements > 15 ranks

**Post-tournament council** (required after R4):
- Runs after `{slug}_final_analysis.json` is generated
- Scope: Model accuracy review, trait validation consensus, schema change proposals

Both councils produce structured output written into `{slug}_council_findings.json` and `{slug}_council_review.md`.

---

## 3. PRE-TOURNAMENT COUNCIL REQUIRED SCOPE

Every pre-tournament council must cover exactly these four review exercises:

### 3A. Full Tournament Projection Review
- Confirm all 5 tiers are populated with at least 1 player
- Confirm T1 has 5 or fewer players (hard cap)
- Confirm no player appears in two tiers
- Confirm VenueDNA_rank ordering matches VenueDNA_final_projection descending sort

### 3B. Tier 1 Assignment Challenge
For each T1 player, the council must produce at minimum:
- One structural support statement (naming exact venue mechanism, not generic reputation)
- One objection or acknowledged risk
- A conviction rating: `"high"` / `"medium"` / `"low"`

If a T1 player's exact mechanism cannot be named from venue structural truths, that player must be reviewed for tier demotion to T2.

### 3C. Anti-Pattern / Fade Exercise
For each confirmed anti-pattern flag (`VenueDNA_flag_*`), the council must:
- Name the structural reason the flag applies to this venue
- Confirm or reject the flag (not every flagged player is an automatic fade)
- Record the ruling: `"confirmed"` / `"rejected"` / `"watchlist"`

### 3D. DG vs. VenueDNA Disagreement Review
For each player where `|VenueDNA_rank - DG_rank_implied|` > 15:
- Identify the source of disagreement
- Determine which model has better structural justification at this venue
- Record: `"VenueDNA_supported"` / `"DG_supported"` / `"inconclusive"`
- If DG is supported, log it as a watchlist item — VenueDNA rank does not change unless a hard gate is triggered

---

## 4. HARD GATES — WHEN THE ENGINE CAN BE OVERRIDDEN

A tier assignment may be manually adjusted only if ONE of these hard gates is triggered:

**Gate 1 — Data Error**: Source CSV contains a confirmed data error for this player (wrong rounds, wrong player name, corrupted value). Resolution: correct the input and rerun the engine.

**Gate 2 — Venue Structural Contradiction**: The VenueDNA score assigns T1 to a player whose profile contains every canonical anti-pattern for this venue, AND the score is driven by a single thin-sample similar-course window (W < 0.3 for all horizons). Resolution: Flag `data_depth: DEBUT` and add `VenueDNA_flag_debut_uncertainty: true`. Score stands but is labeled low confidence.

**Gate 3 — Withdrawal / Injury**: Player is confirmed withdrawn from the field after file generation. Resolution: mark player `status: "WD"` in deploy files; remove from ranking calculations.

**Hard block**: The council cannot adjust a player's VenueDNA_rank simply because it disagrees with DG, public opinion, or recent form not captured in the SG windows. If the math says T1, and no hard gate is triggered, the player stays in T1.

---

## 5. COUNCIL OUTPUT FORMAT

`{slug}_council_findings.json`:
```json
{
  "schema_version": "1.1",
  "event": "2026 3M Open",
  "council_type": "pre_tournament",
  "generated_at": "<ISO 8601 UTC>",
  "objections": [
    {
      "player": "Player, Name",
      "VenueDNA_rank": 3,
      "objection": "...",
      "ruling": "no_change",
      "rationale": "..."
    }
  ],
  "changes_made": [],
  "no_change_rulings": [],
  "anti_pattern_review": [],
  "dg_disagreements": [],
  "final_synthesis": "...",
  "council_sign_off": "pre_tournament_complete"
}
```

`{slug}_council_review.md` is a human-readable narrative summary of the same findings, written in prose. It should name specific players, name specific venue mechanisms, and record any notable surprises.

---

## 6. SCHEMA MODIFICATION AUTHORITY

Schema modifications (new traits, removed traits, changed weights, changed tier boundaries) require:

1. **Learning loop evidence**: ≥3 events at similar venue types showing consistent trait validation consensus
2. **Council proposal**: written proposal in `{slug}_council_review.md` with specific evidence cited
3. **Approval gate**: schema changes take effect in `standards/02_PGA_VENUEDNA_SCORING_SPEC.md` and `engine/enrich_cards.py` only after both files are updated in the same commit
4. **Test suite pass**: `pytest tests/test_enrich_cards.py` must pass after the change
5. **Version bump**: schema version increments from 1.1 → 1.2, etc.

No schema change may be applied mid-tournament. No schema change may be applied based on a single event's results.

---

## 7. GOVERNANCE RULES — WHAT THE COUNCIL CANNOT DO

The council cannot:
- Replace VenueDNA_final_projection with DG_finalprediction_benchmark as the ranking field
- Add or remove players from the field list
- Adjust probability outputs (winPct, top10Pct, etc.) without rerunning the engine
- Override `data_depth: DEBUT` status for a player who genuinely has no similar-course rounds
- Approve a tier assignment change without a triggered hard gate
- Produce a "soft consensus" ranking that blends VenueDNA and DG scores

The council can:
- Add `council_flags` to players who warrant monitoring
- Record DG disagreements as watchlist items
- Log missing-data blockers
- Propose (not apply) schema changes
- Write post-tournament accuracy analysis

---

## 8. ANTI-PATTERN GOVERNANCE

The following anti-pattern flags are canonical for TPC Twin Cities. The council must review each flagged player:

| Flag                              | TPC Twin Cities Structural Basis                              |
|-----------------------------------|---------------------------------------------------------------|
| `VenueDNA_flag_accuracy_risk`     | 9 of 14 driving holes have water; spray drivers face compounding errors |
| `VenueDNA_flag_short_game_only`   | Easy greens reduce short-game leverage; poor ball-strikers cannot compensate |
| `VenueDNA_flag_putting_dependency`| Bentgrass greens are receptive; putting-only profiles lack the ball-striking foundation needed here |
| `VenueDNA_flag_long_iron_deficit` | 150–225 yard approach accuracy is the highest-weight trait; deficiency here is disqualifying for T1 |
| `VenueDNA_flag_debut_uncertainty` | No similar-course rounds — all venue-fit signal is imputed from baseline; actual course-type affinity unknown |

---

## 9. COUNCIL TIMING REQUIREMENTS

```
Pre-tournament council:     Required before deploy package is finalized
R2 council check:           Required after R2 if Spearman rho < 0.20
Post-tournament council:    Required after R4, before final_analysis is marked complete
```

If a pre-tournament council is not run, the deploy package must include:
```json
"council_sign_off": "MISSING — package not fully council-reviewed"
```
