# Score-Decomposition Parity (P1)

Date: 2026-08-04. Scope: read-only parity harness over the root-level, event-hardcoded 3M Open enrichment pathway (`engine/enrich_cards.py`). `config/active_event.json` reports `NO_ACTIVE_EVENT`; no event artifact was created or changed. Branch `main` at `833cc1cf7608e3f24417b195fcb46f4d171caa98`.

This document reports what the current implementation computes. It does not choose a canonical formula, does not resolve the doctrine conflict below, and authorizes no scoring, weight, or rule change.

**2026-08-04 remediation note (post-Codex review):** an earlier draft of this document and of `combine_raw_score()` itself described the extraction as "verbatim" with the "same summation order." That was imprecise. The initial extraction computed `pre_gate_raw_total` via `sum(contributions.values())` over the returned diagnostic dict — a different evaluation path than the original inline expression, because `sum()` implicitly starts from integer `0`, and `0 + (-0.0) == +0.0` silently flips the sign of an all-negative-zero result relative to the original left-associated `a + b + c + d + e + f` expression. Codex caught this. `combine_raw_score()` has been corrected: the production total is now calculated directly through the same literal left-associated expression, operand order, grouping, and numeric literals as the pre-change inline code (`git show 833cc1cf7608e3f24417b195fcb46f4d171caa98:engine/enrich_cards.py`), never through the dict, `sum()`, a loop, or any other reduction. The per-component dict is still returned for diagnostics, but it does not itself compute or alter the production total. Bit-level signed-zero parity between the corrected function and the original inline expression, including the all-`-0.0` case, is now covered by regression tests in `tests/test_scoring_decomposition.py`.

**2026-08-04 second remediation note (post-Codex re-review, gate sequencing):** a second, independent Codex review found a remaining diagnostic-only defect in `engine/scoring_decomposition.py`, not in `engine/enrich_cards.py`: `engine.enrich_cards.apply_gates()` applies each firing gate's multiplier **sequentially** — `raw *= PENALTY_BOMBER`, then, if it also fires, `raw *= PENALTY_SG_DEP`, each reassigning `raw` in place. The diagnostic reconstruction instead precomputed a **combined** multiplier (`m1 * m2`) and applied it once (`pre_total * (m1 * m2)`). Because IEEE-754 float multiplication is not associative, `pre_total * (m1 * m2)` can differ from `(pre_total * m1) * m2` by one ULP. Codex's counterexample: for `raw = 5.358820043066892` with both gates active, production's sequential result is `0x1.1bf97ed7d5cdfp+2`; the former combined-multiplier reconstruction produced `0x1.1bf97ed7d5ce0p+2`. No archived 3M Open player has both gates active simultaneously, so this defect did not affect the archived-parity results reported below — it was only reachable in the general case. `engine/scoring_decomposition.py` has been corrected: a new `apply_gate_sequence_to_total()` function applies each recognized gate's multiplier to the running total one at a time, in `PRODUCTION_GATE_ORDER` (mirroring `apply_gates()`'s literal source order exactly), and `decompose_player()` now uses it to calculate `post_gate_raw_total`. `gate_effect_from_flags()`'s aggregate `multiplier` field is retained as descriptive metadata only — it is no longer, and must never be, used to calculate a post-gate total. Production `engine/enrich_cards.py` was not touched by this correction; `apply_gates()`'s order, conditions, and multiplier values are unchanged.

---

## 1. Implemented formula

Root producer: `engine/enrich_cards.py`, function `combine_raw_score()` (new). The production `pre_gate_raw_total` retains the original literal left-associated arithmetic path previously inlined in `main()` — same terms, same operand order, same grouping, same numeric literals, calculated directly rather than through the returned dict. Component contributions (`approach`, `long_iron`, `ott`, `course_history`, `recent_form`, `sg_similar_composite`) are exposed separately in the same returned dict, for diagnostic decomposition only; that collection does not calculate or alter the production total. Consumed by the per-player loop before gates and field-wide z-scoring.

```
pre_gate_raw_total =
    sg_similar_composite
  + 0.40 * trait_approach_raw      (VW_APPROACH)
  + 0.25 * trait_long_iron_raw     (VW_LONG_IRON)
  + 0.20 * ott_true                (VW_OTT)
  + 0.10 * ch_adjustment           (VW_CH)
  + 0.05 * true_sg_l20             (VW_FORM)

post_gate_raw_total = pre_gate_raw_total, then, for each recognized gate flag
                       that fired, in production's fixed application order,
                       one sequential in-place multiplication:
                         if INACCURATE_BOMBER fired:  total *= 0.92
                         if SHORT_GAME_RELIANT fired: total *= 0.90
                       (never a single multiplication by a precomputed
                       combined multiplier — see the second remediation
                       note above)

vts_final         = z_score_scale(post_gate_raw_total across the full field), rounded 1dp
neutralSkillIndex = z_score_scale(sg_base_composite across the full field), rounded 1dp
prepenalty_vts    = z_score_scale(pre_gate_raw_total across the full field), rounded 1dp
                     (emitted only when a gate fired for that player, else null)
```

`sg_similar_composite` (`SG_Sim_Comp`) is itself `SG_Base_Comp + Delta_Fit_Comp`:

```
SG_Base_Comp   = 0.20*SG_Base_6m + 0.30*SG_Base_12m + 0.50*SG_Base_24m   (BASE_WEIGHT_*)
Delta_Fit_Raw  = 0.50*Delta_Fit_6m + 0.30*Delta_Fit_12m + 0.20*Delta_Fit_24m  (DELTA_WEIGHT_*)
Delta_Fit_Comp = clamp(Delta_Fit_Raw, -0.50, +0.50)                     (DELTA_CLAMP)
```

Gate multipliers (`apply_gates()`, applied sequentially, in this exact source order, before z-scoring — `INACCURATE_BOMBER`'s `raw *= PENALTY_BOMBER` is evaluated first; if `SHORT_GAME_RELIANT` also fires, its `raw *= PENALTY_SG_DEP` is applied to that already-updated `raw`, not to the original pre-gate value):

| Order | Flag | Multiplier | Trigger (unchanged; decided only in `apply_gates()`) |
|---|---|---|---|
| 1 | `INACCURATE_BOMBER` | 0.92 (`PENALTY_BOMBER`) | `driving_dist_adj > 0.15` and `driving_acc_adj < -0.05` |
| 2 | `SHORT_GAME_RELIANT` | 0.90 (`PENALTY_SG_DEP`) | `app_true < 0.20` and `(putt_true + arg_true) > 1.00` |

The diagnostic reconstruction layer (`engine/scoring_decomposition.py`, `PRODUCTION_GATE_ORDER` / `apply_gate_sequence_to_total()`) applies each recognized flag in this same fixed order, one multiplication at a time, against the running total — never a single multiplication by a precomputed combined multiplier (`PENALTY_BOMBER * PENALTY_SG_DEP`). IEEE-754 float multiplication is not associative, so the combined-multiplier shortcut can diverge from production by one ULP when both gates fire on the same player (see the second remediation note above; this was a diagnostic-reconstruction defect, corrected, not a doctrine conflict).

Formula identifier as emitted in the payload envelope: `schemaVersion: "3m-enriched-v2.0"` (pre-event/non-live build; live-round builds emit `3m-live-{round}-v1.0` with the same `combine_raw_score()` formula, differing only in downstream wave-adjustment and softmax-temperature scaling).

## 2. Canonical formula (doctrine, unchanged by this task)

`standards/02_PGA_VENUEDNA_SCORING_SPEC.md` §7: `VTS_Raw = SG_Sim_Comp` — no additional addends.

## 3. Component and paired weights

| Component | Weight | Canonical status |
|---|---|---|
| `sg_similar_composite` | 1.0 (implicit base) | Matches doctrine as the *only* authorized term. |
| `approach` (`trait_approach_raw`) | 0.40 | Not authorized by §7 as a VTS addend at all. |
| `long_iron` (`trait_long_iron_raw`) | 0.25 | Same. |
| `ott` (`ott_true`) | 0.20 | Same. |
| `course_history` (`ch_adjustment`) | 0.10 | Same. |
| `recent_form` (`true_sg_l20`) | 0.05 | Same. |
| **approach + long_iron (coupled pair)** | **0.65** | **Exceeds §17.4 coupled-trait cap of 0.50.** No documented venue-specific override exists in the repository. |
| direct putting + around-the-green | **0.00** | Below §17.4 birdie-race-context floor of 0.20–0.25. Putting/ARG appear only as display traits (`_d_putt`, `_d_composure`) and gate inputs (`putt_true`, `arg_true` in `apply_gates()`), never as combined-score addends. |

## 4. Confirmed conflicts

1. **VTS_Raw formula mismatch.** Implemented `pre_gate_raw_total` is `SG_Sim_Comp` plus five additional weighted addends; §7 defines `VTS_Raw` as `SG_Sim_Comp` alone.
2. **Coupled-pair weight over cap.** `approach + long_iron = 0.65 > 0.50` (§17.4), no override on file.
3. **Short-game/putting floor unmet.** `0.00 < 0.20–0.25` (§17.4, birdie-race venue context).
4. **Root producer is event-specific, not canonical.** `engine/enrich_cards.py` hardcodes 2026 3M Open filenames (`SIM_COURSES_FILES`, `tpc_twin_cities_CH.csv`) and constants; its root-level location does not make it canonical across events.
5. **Open v3 uses an unrelated formula** (below), so cross-event VTS values are not comparable as-is.

No doctrine conflict is resolved by this task; all five remain open pending an explicit doctrine decision.

## 5. Source-confidence gaps

- **Not implemented.** No per-component confidence field (NeutralSkill / VenueFitDelta / VenueHistoryDelta / data-completeness / weather / debut-framework, per `AGENTS.md` §Confidence Discipline) is computed or emitted anywhere in `enrich_cards.py`.
- The only dispersion signals in the payload are the aggregate `std_dev`, `vts_floor`, and `vts_ceil` fields — a single number per player, not decomposed by source.
- `identity_provenance.source_matches` (from the ID-first resolver) records match *method* (`exact_dg_id` / `exact_name` / `encoding_fallback` / `missing`) per source family, but this is identity provenance, not a scoring-confidence signal, and is not consumed by any confidence calculation.

## 6. Missing-data behavior (unchanged; recorded, not altered)

- Missing supplementary source rows receive zero-valued defaults: `_EMPTY_SKILL`, `_EMPTY_PERF`, `_EMPTY_DECOMP`, `_EMPTY_TREND` in `enrich_cards.main()`.
- Missing course-history data defaults to the DEBUT haircut (`DEBUT_CH_HAIRCUT = -0.25`) for `data_depth == "DEBUT"` players, or `0.0` for non-debut players with no CH row.
- Missing proximity data is imputed to the field mean (`prox_z_raw = 0.0`), not to a documented field-neutral trait value.
- `field_stats()` (used for z-scoring and for proximity mean/std) excludes exact-zero values from its own mean/std computation — a zero-filled missing value does not silently pull the field distribution toward itself, but it is still indistinguishable downstream from a genuine zero measurement.
- Verified by `tests/test_scoring_decomposition.py::test_missing_source_zero_default_yields_zero_contribution_only_for_that_component`: a missing component contributes exactly `0.0` and does not perturb any other component's contribution.

## 7. DG benchmark-field dependency status

**None.** `load_decomp()` reads only `driving_acc_adj`, `driving_dist_adj`, and `std_dev` from `dg_decomposition.csv`, used solely as internal gate/composure inputs — never exposed as `DG_*_benchmark` output fields (contrast `standards/04_PGA_VENUEDNA_ARTIFACT_SCHEMA.md` §2B/§3A, which defines a `DG_*_benchmark` output contract this producer's `board_export`/`event_payload` output does not implement). Every other `dg_decomposition.csv` column (`baseline`, `country_adj`, `age`, `age_adj`, `true_sg_adj`, `timing_adj`, `sg_category_adj`, `course_history_adj`, `fit_other_adj`, `course_fit_total_adj`, `final_prediction`) is parsed by `csv.DictReader` but never consumed by any loader. `driving_acc_adj`/`driving_dist_adj` are **not** benchmark-only for the purposes of this report — they are approved source trait fields consumed by `apply_gates()`.

Verified by `tests/test_scoring_decomposition.py::test_benchmark_isolation_unused_dg_columns_do_not_change_vts`: populating every unused `dg_decomposition.csv` column with extreme values (999.9) leaves `vts_final`, `rank`, `tier`, `neutralSkillIndex`, `winPct`, and `anti_pattern_flags` byte-identical.

## 8. Open v3 comparison

`events/2026_Finished_Events/2026_the_open_championship/engine/score_open_2026_v3.py` implements an unrelated, independently-hardcoded formula:

```
VTS = 0.40*NSI + 0.30*VFS + 0.15*VHN + 0.15*form      (W_NSI, W_VFS, W_VHN, W_FORM, :470-475)
VFS = clamp(Σ TRAIT_WEIGHT[t]*trait_score[t], 0, 100) + cfa_sg_adj*5.0 + dg_cfa*1.5 + links_delta   (:408-417)
TRAIT_WEIGHT = app_150_200:0.30, ott_positional:0.20, app_overall:0.15,
               driving_accuracy:0.12, sg_putt:0.13, sg_arg:0.10           (:268-276)
```

- Open v3's VFS blends `dg_cfa*1.5` directly into its official score — the root 3M pathway does not blend any DataGolf field into `vts_final` at all (§7 above).
- Open v3's own trait weights *do* allocate directly to putting (0.13) and ARG (0.10) inside VFS, unlike the root 3M pathway's 0.00.
- Open v3 uses independent softmax temperatures (14/17.5/21/27) and a logistic cut model, versus the root pathway's tempered-softmax temperatures (3.5/5/7/10) and linear cut model — cross-event probability values are not comparable.
- Both pathways are event-hardcoded; neither is the canonical reusable engine.

## 9. Tests performed

New: `tests/test_scoring_decomposition.py` (64 tests), all passing:

- Descriptor-vs-production constant equality (no duplicated weights, horizon weights, or gate multipliers).
- Descriptor immutability (`frozen=True` dataclass + `MappingProxyType` component weights).
- Coupled-pair-over-cap and putting/ARG-under-floor findings, asserted numerically.
- `combine_raw_score()` / `decompose_player()` against independently hand-derived expected values (not computed by calling the function under test).
- **Bit-level parity** (5 tests) between `combine_raw_score()`'s production total and an independent re-implementation of the pre-remediation literal expression, including ordinary representative values, real archived input values, and the all-`-0.0` case (`float.hex()` and `math.copysign()` equality) — plus a direct regression proving `sum()` over the diagnostic dict would reintroduce the sign bug the literal path avoids.
- Missing-source zero-default diagnostic (component-level).
- Benchmark isolation (full synthetic pipeline run, before/after unused-column mutation).
- **Exhaustive gate-coverage parity, sequential reconstruction** (18 tests) between `apply_gate_sequence_to_total()`/`GATE_MULTIPLIERS`/`PRODUCTION_GATE_ORDER` and production `apply_gates()`:
  - Every current gate scenario (none / bomber-only / short-game-reliant-only / both) crossed against six raw values — `1.0`, `5.358820043066892`, `-7.25`, `1e-300`, `-0.0`, `0.0` — asserted bit-identical via `float.hex()`, not ordinary equality alone. Sequential reconstruction now applies one multiplication per active production gate, in `PRODUCTION_GATE_ORDER` (mirroring `apply_gates()`'s literal source order: `INACCURATE_BOMBER` first, `SHORT_GAME_RELIANT` second), against the running total — never a precomputed combined multiplier applied once.
  - A dedicated test pins the exact Codex counterexample: `raw = 5.358820043066892`, both gates active, production `0x1.1bf97ed7d5cdfp+2`, corrected sequential reconstruction `0x1.1bf97ed7d5cdfp+2` (exact match), and the former combined-multiplier approach independently recomputed inline as `0x1.1bf97ed7d5ce0p+2` (asserted unequal to production) — a genuine canary against regressing to the old implementation, not merely a re-assertion of the fix.
  - An end-to-end test through `decompose_player()` reproduces the same Codex value and confirms `post_gate_raw_total` is bit-identical to `apply_gates()`'s output.
  - `apply_gate_sequence_to_total()` and `gate_effect_from_flags()`'s descriptive `applied`/`multiplier` fields are proven order-invariant to the *caller's* input flag-list order, because both always iterate the fixed `PRODUCTION_GATE_ORDER` internally rather than the input list order.
  - Source-introspection registry coverage in both directions (a production flag with no registry entry fails; a registry entry with no matching production flag fails) and defined behavior for a flag name outside the current production set.
  - `PRODUCTION_GATE_ORDER == ("INACCURATE_BOMBER", "SHORT_GAME_RELIANT")` is asserted directly against the value read from `apply_gates()`'s own literal evaluation order.
  - The registry-coverage tests read `apply_gates()`'s own source at test time via `inspect.getsource()` and a regex over `flags.append("...")` literals. This is a **test-only, current-implementation drift sentinel** — it detects a future new gate flag with no matching `GATE_MULTIPLIERS` entry, or a stale registry entry with no matching production flag, without requiring any change to `apply_gates()` itself. It is not a general-purpose Python parser and is not consulted by `engine/scoring_decomposition.py` at runtime or by `engine/enrich_cards.py` at all — it has no production authority; it only fails a test if the two sources of truth (production code, diagnostic registry) drift apart. It currently documents and covers exactly the two production gates (`INACCURATE_BOMBER`, `SHORT_GAME_RELIANT`).
- Read-only archived-3M parity (8 tests) against the frozen `events/2026_Finished_Events/2026_3m_open/deploy/data/2026_3m_open_event_payload.json` fixture (144 real players):
  - Tier-from-rank and make-cut-probability exact pure-function reconstruction.
  - Probability monotonicity.
  - Decomposition-reconstructed `vts_final` and the gated player's `prepenalty_vts`, asserted for **exact equality** after rounding the reconstruction to the same one decimal place the archive itself was stored at (`round(reconstructed, 1) == archived_value`) — no tolerance. All 144 `vts_final` values and the one gated `prepenalty_vts` value are exact, maximum residual `0.0`. Failure messages report player, expected archived value, reconstructed value, and residual. No archived 3M Open player has both gates active simultaneously, so the sequential-vs-combined gate defect corrected in this remediation was not independently exercised by these particular archived-equality checks — it required the dedicated non-unit, both-gates bit-level tests above.
  - Decomposition-reconstructed ranking is monotonically consistent with stored rank, including a genuine display-precision tie (`Mitchell, Keith` / `Meissner, Mac`, both rounding to `69.3`) verified by hand-inspection.
  - All observed `anti_pattern_flags` values are members of the parity layer's known gate registry.

Narrow addition (unchanged this remediation): `tests/test_enrich_cards.py::test_combine_raw_score_extraction_matches_pipeline_prepenalty_vts` — confirms `combine_raw_score()` reproduces the existing golden fixture's gated-player behavior.

Existing suites, unchanged and passing: `tests/test_enrich_cards.py` (46), `tests/test_identity_resolver.py` (68).

Full suite: `python -m pytest tests/ -q` → **357 passed** (334 prior baseline + 23 new gate-sequencing/bit-parity tests).

## 10. No-change certification

- `git diff --exit-code -- config/active_event.json standards events data docs/data_contracts.md engine/identity_resolver.py config/deploy_contracts tools .github` → all clean (no output, exit 0).
- `engine/enrich_cards.py` and `tests/test_enrich_cards.py` are **byte-identical** (SHA-256 hash comparison) to their state at the start of this remediation — this task modified neither file. Their `git diff` against the original `833cc1cf76…` HEAD still shows the earlier, already-authorized phase's changes (named horizon-weight constants, `combine_raw_score()` extraction, one narrow test addition); nothing from this remediation is in that diff.
- `engine/scoring_decomposition.py` change: `post_gate_raw_total` is now calculated by `apply_gate_sequence_to_total()`, which applies each recognized gate's multiplier to the running total **sequentially**, one multiplication per active gate, in `PRODUCTION_GATE_ORDER` — never a single multiplication by a precomputed combined multiplier. `gate_effect_from_flags()`'s aggregate `multiplier` field is retained for descriptive/reporting purposes only and is explicitly documented as not usable to calculate a total. The returned dict shapes of `gate_effect_from_flags()` and `decompose_player()` are unchanged; only the internal calculation path for `post_gate_raw_total` changed, plus one new exported pure function (`apply_gate_sequence_to_total`) and one new exported constant (`PRODUCTION_GATE_ORDER`).
- `python -m compileall engine tests` → clean.
- `git diff --check` → clean (no whitespace errors).
- No score, rank, tier, probability, gate, identity, deploy, or database behavior changed in production (no production scoring behavior changed in engine/enrich_cards.py). No archived file touched. No payload migration performed. Archived-3M exact-equality results (§9) are unaffected because no archived player exercises the combined-gate path.

## 11. Recommended doctrine decision points

These are reported, not resolved, per task scope:

1. Whether `standards/02_PGA_VENUEDNA_SCORING_SPEC.md` §7 should be amended to authorize the five additional addends currently implemented in `enrich_cards.py`, or whether `enrich_cards.py` should be brought into conformance with `VTS_Raw = SG_Sim_Comp`.
2. Whether the 3M Open venue qualifies for a documented §17.4 coupled-trait-cap override (0.65 vs. 0.50), and if so, its evidence basis.
3. Whether a direct putting/ARG addend belongs in this pathway's combined score for birdie-race venues, per the §17.4 floor.
4. Whether `engine/enrich_cards.py` should be generalized into a reusable canonical engine (per `docs/audits/2026_08_03_engine_ui_audit/04_target_architecture.md` item 4), which explicitly requires this decomposition-parity reconciliation to land first.
5. Whether per-component source confidence (§Confidence Discipline) should be added as a new, explicitly-authorized additive payload field — out of scope here since it would require an additive metadata migration.
