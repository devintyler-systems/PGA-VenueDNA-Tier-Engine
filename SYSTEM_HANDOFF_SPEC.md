# SYSTEM_HANDOFF_SPEC.md
# PGA VenueDNA Tier Engine
# Version 1.0
# Purpose: Define ownership and handoff rules between Claude Code, Codex, ChatGPT Project reasoning, GitHub, and the local runtime.

## SYSTEM ROLES

### ChatGPT Project and Perplexity

Shared reasoning and control plane. Either may serve as the active planning lane for doctrine interpretation, Model Council reasoning, projection synthesis, audit classification, task scoping, and code-review framing.

Both own:
- VenueDNA doctrine
- Scoring and artifact-contract interpretation
- Model Council reasoning
- Projection synthesis
- Audit classification
- Task scoping and code-review framing

Both must:
- Follow the repository authority hierarchy, active-event lifecycle, canonical standards, and data contracts.
- Treat committed GitHub state as the durable shared source of truth.
- Verify `config/active_event.json` before event-bound planning, projections, live work, audits, or implementation guidance.
- Keep NeutralSkill, VenueFitDelta, VenueHistoryDelta, penalties and gates, uncertainty/confidence, and derivatives separate.
- Not make silent code changes or mutate canonical venue intelligence without an approved write-back artifact.

When Perplexity is the active operating lane, `PERPLEXITY_OPERATING_PROTOCOL.md` additionally governs its direct creation and GitHub commit of approved non-code artifacts, including manifests, handoff prompts, live/audit artifacts, and documentation.

When ChatGPT is the active operating lane, it may plan, review, and draft those artifacts, but it must verify their committed GitHub state before instructing a local implementation agent to use them.

Neither owns:
- Undocumented repository facts
- Silent code changes
- Direct mutation of canonical venue intelligence without an approved write-back artifact

### Claude Code
Primary implementation lane for:
- Multi-file feature builds
- Engine refactors
- Pipeline changes
- Local repository execution
- Test-driven implementation
- Complex debugging requiring iterative terminal inspection

### Codex
Secondary implementation and review lane for:
- Focused patches
- Code review
- Schema validation
- SQLite query and migration drafting
- Artifact validation
- Test creation
- Isolated deploy UI changes
- Independent review of a Claude-produced diff

Codex does not redesign scoring doctrine, venue logic, or artifact contracts without an explicit task directing the change.

### GitHub
Owns:
- Committed source-of-truth code
- Commit history
- Pull requests
- Shared review surface
- Versioned standards and templates

### Local Runtime: C:\PGA_VenueDNA
Owns:
- Active local execution state
- Raw source data
- API cache
- Local SQLite runtime behavior
- Generated event artifacts before commit

A file is not treated as canonical merely because it exists locally. Commit state and the canonical standards hierarchy determine durable truth.

## HANDOFF INPUT CONTRACT

Every implementation task handed to Claude Code or Codex must state:

- Objective
- Active event slug, or `NO_ACTIVE_EVENT`
- Venue slug, if applicable
- Files authorized for modification
- Files prohibited from modification
- Expected artifact names and locations
- Required validation command or test target
- Whether the task may alter scoring logic, deploy behavior, or both
- Stop condition

If any item is unknown, inspect first. Do not infer repository paths or payload shapes.

## HANDOFF PUBLICATION AND SYNC

A Claude Code or Codex task must be based on a complete handoff artifact committed to GitHub, normally in `chatgpt_codex/` or `scripts/handoffs/`, before execution begins.

Before local execution, the operator or implementation agent must verify that the local worktree contains the referenced handoff file and is synchronized with the intended remote commit. A remote GitHub commit is not available to a local agent until the local repository fetches or pulls it.

If the referenced handoff is absent locally, the implementation agent must stop, report the missing path and any local/remote divergence, and make no substitute handoff file or unrelated worktree changes.

## HANDOFF OUTPUT CONTRACT

Every implementation response must return:

1. Files changed
2. Behavior changed
3. Files intentionally not changed
4. Validation run and result
5. Data-contract impact, if any
6. Migration requirement, if any
7. Manual deploy or artifact-copy step, if any
8. Open risk or unresolved dependency

## DATA CONTRACT RULES

- DataGolf ID is the canonical external player key.
- Preserve the internal player ID crosswalk in `players`.
- Normalize player names before joins, including diacritic folding and known encoding fallback.
- Do not use player name as the only join key when a DataGolf ID exists.
- Pre-event payloads are read-only once the live pipeline begins.
- Live round builders may create new live artifacts but may not overwrite canonical pre-event artifacts.
- JSON and CSV files consumed by `app.js` are protected contracts.
- Before renaming any deploy data file, inspect `app.js` fetch calls and update every affected reference.
- All score fields remain normalized 0-100 unless the scoring spec explicitly authorizes an exception.
- Weather remains a post-score multiplicative modifier unless the scoring spec changes.

## CHANGE OWNERSHIP

### Scoring Logic Change
Requires:
- Update to `02_PGA_VENUEDNA_SCORING_SPEC.md`
- Relevant unit or regression tests
- Before-and-after output comparison on a representative event
- Explicit classification as engine rule change, not venue write-back

### UI/UX Change

Requires:

- Inspect active deploy files, fixture harness, and consumed payloads before design work.
- Invoke the `ui-ux-pro-max` design skill for a material new or redesigned UI surface: Codex reads `.codex/skills/ui-ux-pro-max/SKILL.md` directly; Claude Code invokes the equivalent native skill via the Skill tool.
- Treat generated design-system output as guidance, not authority over scoring, artifacts, or data contracts.
- Preserve Pre-Event Model versus Live Update separation.
- Preserve exact deploy payload and fetch compatibility unless the task explicitly authorizes a contract migration.
- Validate desktop, tablet, mobile, accessibility, and fixture-harness or browser behavior.

### Venue Rule Change
Requires:
- Write-back artifact
- Evidence threshold stated
- Update only to the canonical venue profile after operator approval
- No global engine implication without an engine-rule flag

### Deploy UI Change
Requires:
- Inspect active `index.html`, `app.js`, `styles.css`, and consumed payloads
- Preserve payload compatibility unless the task explicitly changes the data contract
- Browser validation or fixture-harness validation
- No scoring logic modifications

### SQLite Schema Change
Requires:
- Idempotent migration
- Backup-safe logic
- Explicit target database: `data/venuedna_master.db` or `data/venue_dna.db`
- Verification against existing tables
- No global `*.db` gitignore rule

## LIVE EVENT SAFETY

During Round 1 through final round:
- Treat pre-event projection artifacts as immutable.
- Write live artifacts to round-specific output paths.
- Do not modify scoring weights from one live event result.
- Classify structural miss versus variance before any promotion or downgrade.
- Preserve scenario fencing between pre-event thesis and live inference.
- Do not overwrite a prior round artifact to create a later-round output.

## CONFLICT RESOLUTION

When standards, repository behavior, and task direction conflict:

1. Stop.
2. Name the exact files or instructions in conflict.
3. State the governing authority.
4. Propose the minimum safe resolution.
5. Do not write code until the conflict is resolved.

## DEFINITION OF DONE

A task is complete only when:
- The requested files are changed.
- The relevant tests or validation commands have run.
- Deploy data references remain valid.
- The output contract is preserved or documented as changed.
- The handoff output contract is returned.
- No unauthorized scoring, venue, database, or deployment behavior changed.