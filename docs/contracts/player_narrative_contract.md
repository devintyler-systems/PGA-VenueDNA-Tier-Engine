# VenueDNA Player Narrative Contract
Version 1
Purpose: Produce evidence-grounded, venue-specific player narratives for the
Tier Engine without allowing prose generation to alter model scores or facts.

## 1. Boundary

Narratives are a derived presentation artifact.

They:
- Explain the existing VenueDNA projection
- Use only supplied, validated player and event data
- Never calculate, modify, or imply changes to NeutralSkill, VenueFitDelta,
  VenueHistoryDelta, penalties, VTS, tier, or confidence
- Never invent injuries, course-history facts, form trends, swing changes,
  quotes, betting context, or causal explanations
- Must be generated during the build pipeline and stored with the event artifact,
  never generated dynamically in the browser

Source-of-truth hierarchy:
1. Validated event/player scoring artifact
2. Validated venue profile
3. Validated player evidence and round data
4. Generated narrative artifact
5. HTML rendering layer

The HTML board only renders `player_narrative` fields. It does not construct prose.

---

## 2. Input Contract

Each player passed to narrative generation must have this object shape.
Unavailable data must be explicit as `null`, never guessed.

```json
{
  "schema_version": "1.0",
  "event": {
    "event_id": "pga_rocket_classic_YYYY",
    "event_name": "Rocket Classic",
    "venue_id": "detroit_golf_club",
    "venue_name": "Detroit Golf Club",
    "event_phase": "pre_tournament",
    "generated_at_utc": "YYYY-MM-DDTHH:MM:SSZ",
    "data_as_of_utc": "YYYY-MM-DDTHH:MM:SSZ"
  },

  "course_dna": {
    "identity_summary": "Validated one-sentence course identity.",
    "primary_demands": [
      {
        "trait_id": "approach_play",
        "label": "Approach Play",
        "importance": 0.00,
        "rank": 1,
        "reason": "Validated evidence-backed course demand."
      }
    ],
    "scoring_opportunities": [
      "Validated opportunity statement."
    ],
    "primary_failure_modes": [
      "Validated failure-mode statement."
    ],
    "par": null,
    "yardage": null,
    "weather_context": null
  },

  "player": {
    "player_id": "stable_canonical_id",
    "display_name": "Player Name",
    "country": null,
    "handedness": null
  },

  "projection": {
    "vts": 0.0,
    "vts_rank": 1,
    "field_size": 144,
    "tier": "T1",
    "tier_rank": 1,
    "conviction": "High",
    "confidence_score": 0.0,
    "confidence_label": "High",
    "neutral_skill": 0.0,
    "venue_fit_delta": 0.0,
    "venue_history_delta": 0.0,
    "penalty_total": 0.0,
    "projection_direction": "positive",
    "projection_reason_codes": [
      "ELITE_APPROACH_FIT",
      "POSITIVE_VENUE_HISTORY"
    ]
  },

  "traits": [
    {
      "trait_id": "approach_play",
      "label": "Approach Play",
      "score": 0.0,
      "field_percentile": 0.0,
      "venue_importance": 0.0,
      "fit_contribution": 0.0,
      "direction": "strength",
      "evidence_status": "validated"
    }
  ],

  "badges": [
    {
      "badge_id": "iron_surgeon",
      "label": "Iron Surgeon",
      "qualification_reason": "Approach and iron-play thresholds satisfied.",
      "evidence_trait_ids": [
        "approach_play",
        "iron_play"
      ]
    }
  ],

  "form": {
    "sample_window": "last_N_starts",
    "form_label": "Strong",
    "form_direction": "improving",
    "form_evidence": [
      "Validated statement based on supplied data."
    ],
    "recent_results": [
      {
        "event_name": "Event Name",
        "finish": "T12",
        "date": "YYYY-MM-DD"
      }
    ]
  },

  "venue_history": {
    "starts": 0,
    "cuts_made": 0,
    "best_finish": null,
    "history_label": "No meaningful sample",
    "evidence": [
      "Validated venue-history statement."
    ]
  },

  "risk_factors": [
    {
      "risk_id": "putting_volatility",
      "label": "Putting volatility",
      "severity": "medium",
      "evidence_trait_id": "putting",
      "description": "Validated, player-specific risk statement."
    }
  ],

  "live_context": {
    "round": null,
    "position": null,
    "strokes_gained": [],
    "prediction_status": null,
    "round_evidence": []
  }
}
```

---

## 3. Required Outputs

Every player receives a narrative object—even where evidence is thin. Thin evidence
must produce a transparent low-confidence narrative, not generic filler.

```json
{
  "player_id": "stable_canonical_id",
  "event_id": "pga_rocket_classic_YYYY",
  "schema_version": "1.0",
  "generated_at_utc": "YYYY-MM-DDTHH:MM:SSZ",
  "generation_mode": "pre_tournament",

  "headline": "Short, specific venue-fit thesis",
  "story_hook": "2-3 sentences explaining why this player matters at this venue this week.",
  "venue_fit": "1-2 sentences linking the player’s strongest relevant traits to Detroit Golf Club’s primary demands.",
  "strengths": [
    {
      "label": "Approach Play",
      "statement": "Specific explanation tied to supplied trait evidence.",
      "trait_id": "approach_play"
    }
  ],
  "weaknesses": [
    {
      "label": "Putting",
      "statement": "Specific risk tied to supplied evidence.",
      "trait_id": "putting"
    }
  ],
  "win_scenario": "One conditional sentence: To win, [player] needs to...",
  "failure_scenario": "One conditional sentence: The projection breaks if...",
  "projection_explainer": "One sentence explaining the VTS/tier using supplied components only.",
  "form_note": "One evidence-bound sentence, or a transparent limited-data statement.",
  "venue_history_note": "One evidence-bound sentence, or a transparent no-meaningful-sample statement.",

  "evidence_refs": {
    "strength_trait_ids": [
      "approach_play"
    ],
    "risk_trait_ids": [
      "putting"
    ],
    "course_demand_trait_ids": [
      "approach_play"
    ],
    "projection_reason_codes": [
      "ELITE_APPROACH_FIT"
    ]
  },

  "quality": {
    "evidence_coverage": "high",
    "needs_editor_review": false,
    "validation_errors": []
  }
}
```

---

## 4. Narrative Rules

### Voice
- Write like an informed caddie, not a sportsbook ad or generic preview.
- Use direct, concrete golf language.
- Lead with the venue-specific reason the player matters.
- Avoid superlatives unless supported by an explicit rank or percentile supplied in input.
- Use “the model” only in `projection_explainer`, never as a substitute for explanation.

### Evidence discipline
- Every favorable claim must trace to one or more supplied traits, form evidence,
  venue-history evidence, or projection reason codes.
- Every risk must trace to `risk_factors`, a negative trait contribution, penalty,
  or explicit confidence limitation.
- Do not treat course history as predictive proof; describe it as supporting or
  contradictory context only.
- Do not state causation from a result unless the input explicitly contains causal evidence.
- If a trait score is unavailable, omit the trait rather than filling the slot with vague prose.
- If `venue_history.starts < 2`, state “limited venue sample” or “no meaningful venue sample.”

### Specificity rules
- `headline`: 6-12 words; no player name unless required for clarity.
- `story_hook`: 45-75 words.
- `venue_fit`: 25-45 words.
- Each strength/weakness: 16-30 words.
- `win_scenario` and `failure_scenario`: 18-35 words each.
- Do not repeat the same trait in headline, hook, fit, and strength unless it is
  the unequivocal primary driver of the projection.
- Never output a player’s VTS score in prose unless the UI separately displays it.

### Negative and uncertain profiles
- A low-tier player still gets a real story: define the viable path, the mismatch,
  and the condition that would overturn the projection.
- Low confidence is a finding, not a defect. Surface it explicitly.
- No available evidence is valid output: say so cleanly rather than inventing a story.

---

## 5. Prompt Template

System instruction for narrative generation:

"You generate PGA VenueDNA player narratives from a closed data object.
You may use only facts and relationships explicitly contained in that object.
Do not calculate scores, infer missing evidence, make medical claims, write betting
advice, or alter any model output. Explain why the supplied projection fits or
does not fit this venue. Return valid JSON matching the output schema only."

User payload:

```text
Generate one pre-tournament player narrative using this input JSON:

{{PLAYER_NARRATIVE_INPUT_JSON}}
```

---

## 6. Deterministic Validation

Reject the artifact before HTML generation if any condition is true:

- `player_id` or `event_id` differs from the source scoring artifact
- Any required output field is missing or empty
- Output includes a player, event, finish, stat, venue fact, injury, quote, or
  causal claim absent from the input object
- A strength references a trait not present in `traits`
- A weakness references a trait not present in `risk_factors` or a negative trait
- A course-fit claim references a trait absent from `course_dna.primary_demands`
- `evidence_coverage` is `high` when required source evidence is missing
- Output uses unsupported absolutes: “guaranteed,” “certain,” “cannot miss,”
  “dominant,” “automatic,” or “lock”
- Output exceeds word limits
- Output fails JSON schema validation

Validation actions:
- Schema failure: block board build
- Evidence-reference failure: block player narrative and render a visible
  `Narrative unavailable — evidence validation failed` state
- Low evidence coverage: render narrative with a `Limited evidence` label
- Editorial review flag: allow board build, but display an internal QA marker only