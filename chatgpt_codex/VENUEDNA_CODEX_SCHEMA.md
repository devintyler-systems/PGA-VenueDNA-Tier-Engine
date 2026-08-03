# VENUEDNA_CODEX_SCHEMA.md
# Version 1.0 | PGA VenueDNA Tier Engine | Codex Contract Layer
# Purpose: Typed contracts for all code-generation tasks in the ChatGPT project.
# This file governs what Codex produces, in what format, and what downstream systems consume.

---

## CODEX LANE DEFINITION

Codex mode engages when the task is one of the following:
- Artifact file generation (projection output, audit output, venue profile)
- JSON schema creation or validation
- Scoring module production (Python functions, class definitions)
- SQLite table creation, migration, or query generation
- Write-back diff generation from audit findings
- Artifact packaging and naming validation

Codex mode does not engage for:
- Projection reasoning
- Model Council synthesis
- Venue intelligence interpretation
- Any task where prose judgment is the primary output

When Codex mode is active, all output is fenced code blocks with language labels. No prose commentary inside blocks. Brief block-header comments only.

---

## 1. PROJECTION ARTIFACT SCHEMA

### 1a. JSON Schema: Full Tournament Projection

File naming rule: `PROJ_[VENUE_CODE]_[YYYYMMDD]_v[N].json`
Example: `PROJ_EASTLAKE_20261003_v1.json`

```json
{
  "schema_version": "1.0",
  "event": {
    "name": "string",
    "venue_code": "string",
    "venue_name": "string",
    "event_date": "YYYY-MM-DD",
    "surface": "string",
    "conditions_note": "string | null"
  },
  "projection_meta": {
    "generated_at": "ISO8601",
    "active_venue_file": "string",
    "active_event_file": "string | null",
    "scoring_spec_version": "string",
    "confidence_class": "HIGH | MEDIUM | THIN",
    "council_triggered": true | false
  },
  "tiers": {
    "tier_1": [ "PlayerProjection" ],
    "tier_2": [ "PlayerProjection" ],
    "tier_3": [ "PlayerProjection" ],
    "tier_4": [ "PlayerProjection" ],
    "tier_5": [ "PlayerProjection" ]
  },
  "anti_pattern_flags": [ "AntiPatternFlag" ],
  "risk_register": [ "RiskEntry" ],
  "council_findings": "CouncilFindings | null",
  "synthesis_changes": [ "SynthesisChange" ]
}
```

### 1b. PlayerProjection Object

```json
{
  "player_id": "string",
  "player_name": "string",
  "tier": 1,
  "neutral_skill_score": "float",
  "venue_fit_delta": "float",
  "venue_history_delta": "float",
  "penalties_applied": [ "string" ],
  "gates_applied": [ "string" ],
  "composite_score": "float",
  "confidence_band": "HIGH | MEDIUM | THIN",
  "structural_justification": "string",
  "debut_flag": true | false,
  "debut_framework_applied": "string | null"
}
```

### 1c. AntiPatternFlag Object

```json
{
  "player_name": "string",
  "anti_pattern_type": "string",
  "mechanism": "string",
  "fade_conviction": "STRONG | MODERATE"
}
```

### 1d. RiskEntry Object

```json
{
  "player_name": "string",
  "risk_type": "WEATHER | FORM | DEBUT | SURFACE | PHYSICAL | FIELD_DEPTH | OTHER",
  "risk_description": "string",
  "risk_magnitude": "HIGH | MEDIUM | LOW"
}
```

### 1e. CouncilFindings Object

```json
{
  "council_mode": "FULL | LIGHT",
  "trigger_reason": "string",
  "objections": [
    {
      "role": "string",
      "objection": "string",
      "decision": "DOWNGRADE | HOLD | PROMOTION | NO_CHANGE",
      "outcome_note": "string"
    }
  ],
  "duplicate_objections_collapsed": true | false,
  "synthesis_summary": "string"
}
```

### 1f. SynthesisChange Object

```json
{
  "player_name": "string",
  "change_type": "TIER_UP | TIER_DOWN | CONFIDENCE_ADJUSTED | PENALTY_ADDED | FLAG_ADDED",
  "from_value": "string",
  "to_value": "string",
  "reason": "string"
}
```

---

## 2. AUDIT ARTIFACT SCHEMA

File naming rule: `AUDIT_[VENUE_CODE]_[YYYYMMDD]_v[N].json`
Example: `AUDIT_EASTLAKE_20261006_v1.json`

```json
{
  "schema_version": "1.0",
  "event": {
    "name": "string",
    "venue_code": "string",
    "event_date": "YYYY-MM-DD",
    "actual_winner": "string",
    "actual_top10": [ "string" ]
  },
  "audit_meta": {
    "generated_at": "ISO8601",
    "original_projection_file": "string",
    "learning_loop_spec_version": "string",
    "council_review_triggered": true | false
  },
  "tier_accountability": [ "TierAccountabilityEntry" ],
  "significant_misses": [ "MissEntry" ],
  "anti_pattern_review": [ "AntiPatternReview" ],
  "write_back_recommendations": [ "WriteBack" ],
  "engine_rule_flags": [ "EngineRuleFlag" ]
}
```

### 2a. TierAccountabilityEntry Object

```json
{
  "player_name": "string",
  "projected_tier": 1,
  "actual_finish": "integer | MC | WD",
  "result_class": "CONFIRM | SOFT_MISS | HARD_MISS | ANTI_PATTERN_CONFIRMED",
  "notes": "string"
}
```

### 2b. MissEntry Object

```json
{
  "player_name": "string",
  "projected_tier": 1,
  "actual_finish": "integer | MC | WD",
  "miss_layer": "NEUTRAL_SKILL | VENUE_FIT | VENUE_HISTORY | PENALTY | GATE | DEBUT | COUNCIL",
  "miss_type": "OVER_PROJECTION | UNDER_PROJECTION | WRONG_MECHANISM",
  "root_cause": "string",
  "write_back_required": true | false
}
```

### 2c. AntiPatternReview Object

```json
{
  "player_name": "string",
  "anti_pattern_flagged": true | false,
  "fade_confirmed": true | false,
  "mechanism_validated": true | false,
  "notes": "string"
}
```

### 2d. WriteBack Object

```json
{
  "target_file": "string",
  "target_section": "string",
  "change_type": "VENUE_RULE_UPDATE | DEBUT_FRAMEWORK_UPDATE | PENALTY_THRESHOLD_UPDATE | ENGINE_RULE_FLAG",
  "current_value": "string",
  "proposed_value": "string",
  "evidence_basis": "string",
  "evidence_threshold_met": true | false
}
```

### 2e. EngineRuleFlag Object

```json
{
  "rule_reference": "string",
  "flag_type": "INCONSISTENT_APPLICATION | MISSING_DATA_HANDLED_INCORRECTLY | COUNCIL_BYPASS | DERIVATIVE_CONTAMINATION",
  "description": "string",
  "recommended_action": "string"
}
```

---

## 3. SQLITE TABLE DEFINITIONS

### 3a. Projections Table

```sql
CREATE TABLE IF NOT EXISTS projections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_name TEXT NOT NULL,
    venue_code TEXT NOT NULL,
    event_date TEXT NOT NULL,
    player_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    tier INTEGER NOT NULL CHECK (tier BETWEEN 1 AND 5),
    neutral_skill_score REAL,
    venue_fit_delta REAL,
    venue_history_delta REAL,
    composite_score REAL,
    confidence_band TEXT CHECK (confidence_band IN ('HIGH','MEDIUM','THIN')),
    debut_flag INTEGER DEFAULT 0,
    penalties_applied TEXT,
    gates_applied TEXT,
    structural_justification TEXT,
    projection_file TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
```

### 3b. Audit Results Table

```sql
CREATE TABLE IF NOT EXISTS audit_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_name TEXT NOT NULL,
    venue_code TEXT NOT NULL,
    event_date TEXT NOT NULL,
    player_name TEXT NOT NULL,
    projected_tier INTEGER,
    actual_finish TEXT,
    result_class TEXT CHECK (result_class IN ('CONFIRM','SOFT_MISS','HARD_MISS','ANTI_PATTERN_CONFIRMED')),
    miss_layer TEXT,
    miss_type TEXT,
    root_cause TEXT,
    write_back_required INTEGER DEFAULT 0,
    audit_file TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
```

### 3c. Write-Back Log Table

```sql
CREATE TABLE IF NOT EXISTS write_back_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_name TEXT NOT NULL,
    venue_code TEXT NOT NULL,
    event_date TEXT NOT NULL,
    target_file TEXT NOT NULL,
    target_section TEXT,
    change_type TEXT,
    current_value TEXT,
    proposed_value TEXT,
    evidence_basis TEXT,
    evidence_threshold_met INTEGER DEFAULT 0,
    applied INTEGER DEFAULT 0,
    applied_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
```

### 3d. Venue Anti-Pattern Registry Table

```sql
CREATE TABLE IF NOT EXISTS anti_pattern_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venue_code TEXT NOT NULL,
    player_name TEXT NOT NULL,
    anti_pattern_type TEXT NOT NULL,
    mechanism TEXT NOT NULL,
    event_count INTEGER DEFAULT 1,
    confirmed_count INTEGER DEFAULT 0,
    last_seen TEXT,
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);
```

---

## 4. PYTHON CLASS SIGNATURES

### 4a. PlayerProjection Dataclass

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class PlayerProjection:
    player_id: str
    player_name: str
    tier: int
    neutral_skill_score: float
    venue_fit_delta: float
    venue_history_delta: float
    composite_score: float
    confidence_band: str  # HIGH | MEDIUM | THIN
    structural_justification: str
    penalties_applied: list[str] = field(default_factory=list)
    gates_applied: list[str] = field(default_factory=list)
    debut_flag: bool = False
    debut_framework_applied: Optional[str] = None
```

### 4b. VenueProjectionArtifact Dataclass

```python
from dataclasses import dataclass, field
from typing import Optional
from datetime import date

@dataclass
class VenueProjectionArtifact:
    event_name: str
    venue_code: str
    venue_name: str
    event_date: date
    surface: str
    active_venue_file: str
    scoring_spec_version: str
    confidence_class: str  # HIGH | MEDIUM | THIN
    council_triggered: bool
    tiers: dict[int, list[PlayerProjection]]  # keys 1-5
    anti_pattern_flags: list[dict] = field(default_factory=list)
    risk_register: list[dict] = field(default_factory=list)
    council_findings: Optional[dict] = None
    synthesis_changes: list[dict] = field(default_factory=list)
    conditions_note: Optional[str] = None
    active_event_file: Optional[str] = None

    def to_filename(self, version: int = 1) -> str:
        date_str = self.event_date.strftime("%Y%m%d")
        return f"PROJ_{self.venue_code}_{date_str}_v{version}.json"
```

### 4c. AuditArtifact Dataclass

```python
@dataclass
class AuditArtifact:
    event_name: str
    venue_code: str
    event_date: date
    actual_winner: str
    actual_top10: list[str]
    original_projection_file: str
    learning_loop_spec_version: str
    council_review_triggered: bool
    tier_accountability: list[dict] = field(default_factory=list)
    significant_misses: list[dict] = field(default_factory=list)
    anti_pattern_review: list[dict] = field(default_factory=list)
    write_back_recommendations: list[dict] = field(default_factory=list)
    engine_rule_flags: list[dict] = field(default_factory=list)

    def to_filename(self, version: int = 1) -> str:
        date_str = self.event_date.strftime("%Y%m%d")
        return f"AUDIT_{self.venue_code}_{date_str}_v{version}.json"
```

### 4d. Scoring Engine Signature

```python
def score_player(
    player_id: str,
    player_name: str,
    neutral_skill_inputs: dict,
    venue_profile: dict,
    venue_history: dict | None,
    event_context: dict,
    debut: bool = False
) -> PlayerProjection:
    """
    Applies NeutralSkill, VenueFitDelta, VenueHistoryDelta, penalties, and gates.
    Returns a fully populated PlayerProjection.
    venue_history=None triggers THIN confidence band automatically.
    """
    ...
```

---

## 5. FILE NAMING REGISTRY

| Artifact Type | Pattern | Example |
|---|---|---|
| Pre-event projection | `PROJ_[VENUE]_[YYYYMMDD]_v[N].json` | `PROJ_QUAILHOLLOW_20261020_v1.json` |
| Post-event audit | `AUDIT_[VENUE]_[YYYYMMDD]_v[N].json` | `AUDIT_QUAILHOLLOW_20261023_v1.json` |
| Venue profile | `VENUE_[VENUE]_PROFILE.md` | `VENUE_QUAILHOLLOW_PROFILE.md` |
| Event context | `EVENT_[NAME]_[YEAR]_CONTEXT.md` | `EVENT_BMWCHAMPIONSHIP_2026_CONTEXT.md` |
| Write-back diff | `WRITEBACK_[VENUE]_[YYYYMMDD].md` | `WRITEBACK_QUAILHOLLOW_20261023.md` |
| Council log | `COUNCIL_[VENUE]_[YYYYMMDD].md` | `COUNCIL_QUAILHOLLOW_20261020.md` |

Venue codes must be uppercase, no spaces, no special characters. Use the same code consistently across all files for the same course. Never invent a new naming pattern when a canonical one exists above.

---

## 6. WRITE-BACK DIFF FORMAT

When Codex generates a write-back diff, use this structure:

```markdown
## WRITE-BACK DIFF
Target file: VENUE_[VENUE]_PROFILE.md
Target section: [section name]
Change type: [VENUE_RULE_UPDATE | DEBUT_FRAMEWORK_UPDATE | PENALTY_THRESHOLD_UPDATE]
Evidence threshold met: YES | NO

CURRENT:
[exact current text]

PROPOSED:
[exact replacement text]

Evidence basis:
[specific event reference, miss layer, sample size]
```

Write-back diffs are never applied automatically. They are produced as named files and applied manually after operator review.

---

## 7. VALIDATION RULES FOR CODEX OUTPUT

Before producing any artifact, Codex must validate:

1. `venue_code` matches an active venue profile file name.
2. All five tiers are populated or explicitly marked empty with a reason.
3. Every `PlayerProjection` with `tier=1` has a non-empty `structural_justification`.
4. Every `PlayerProjection` with `confidence_band=THIN` has a non-empty explanation of what data is missing.
5. `council_triggered=true` requires a non-null `council_findings` block.
6. No `composite_score` is produced without all three components (`neutral_skill_score`, `venue_fit_delta`, `venue_history_delta`) being present or explicitly zeroed with a reason.
7. File names match the naming registry in Section 5 exactly.

If any validation fails, Codex outputs a `VALIDATION_ERROR` block before the artifact and does not produce the artifact until the gap is resolved.

```json
{
  "VALIDATION_ERROR": {
    "rule_violated": "string",
    "missing_field": "string",
    "resolution_required": "string"
  }
}
```