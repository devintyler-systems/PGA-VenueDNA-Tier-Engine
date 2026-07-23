# Codex-Standard Round Learning UI Spec

This spec defines the preferred Round Learning interface standard for PGA VenueDNA event Boards after the 2026 Open Championship dry run. It should be treated as the implementation benchmark for Round 1, Round 2, Round 3, and Final review tabs in future event builds. [file:1][file:25]

## Purpose

The Round Learning UI exists to answer one question clearly: what did the live round evidence validate, weaken, or leave unresolved relative to the pre-tournament venue model. The interface should privilege operator scan speed, signal hierarchy, and audit traceability over raw data completeness. [file:1][file:25]

## Core UI principle

The best round tab is not the one that shows the most rows. It is the one that makes the strongest validated traits, confidence states, and trajectory changes obvious within a few seconds, while still preserving access to the full cumulative record when needed. This is more aligned with the VenueDNA operating model than a flat table that gives identical visual weight to validated and non-testable traits. [file:1][file:25]

## Required sections

Each round tab should render these blocks in this order:

1. **Live Lean strip** — compact chips for the highest-signal trait updates from the active round file, including trait key, directional delta, and confidence/state label. This supports fast operator interpretation before deep review. [file:25][file:1]
2. **Round context line** — one-line summary including prior-round consensus reference and the relevant horizon statistic such as rho or separation note when available. [file:25]
3. **Cumulative Learning grid** — the canonical multi-round trait table showing trait key, consensus state, absolute magnitude, proxy confidence, and trajectory marks. The blueprint defines this as a five-column grid and should remain the structural anchor of the tab. [file:1]
4. **Stub or extension zones** — optional diagnostics, round snapshot, or source notes may appear below the grid, but they must not visually overpower the learning table. [file:1][file:25]

## Live Lean strip standard

The Live Lean strip should behave like a prioritized alert ribbon, not a full report. Only traits with meaningful round relevance should appear as chips in the top band; low-information or unresolved traits should stay in the grid rather than crowd the top strip. [file:1][file:25]

### Chip content

Each chip should include:

- Trait key or normalized trait label
- Directional cue such as upward or downward delta
- Short reason or state tag such as `validated`, `proxy-confirmed`, `not-testable`, or condition override language when explicitly supported by the round file [file:25]

### Chip rules

- Show validated and proxy-confirmed traits first. [file:25]
- Show not-testable traits only when they are still operationally important to the live interpretation, such as when a venue override remains active despite weak direct evidence. [file:25]
- Do not dump every trait into the strip. The strip is for prioritization, not exhaustiveness. [file:1]
- Keep the strip visually compact and single-pass readable on desktop. [file:1]

## Cumulative Learning grid standard

The Cumulative Learning grid is the audit spine of the round tab. It should preserve the blueprint’s five required columns and use styling hierarchy to separate signal from noise. [file:1]

| Column | Requirement |
|---|---|
| Trait Model Key | Machine-readable or normalized trait slug; keep stable across rounds. [file:1] |
| Consensus State | Badge-based state such as bullish, neutral, bearish, validated, mixed, or not-testable depending on the active round schema. [file:1][file:25] |
| Abs Magnitude | Numeric absolute delta formatted consistently, ideally to 2 decimals when available. [file:1] |
| Proxy Confidence | High/medium/low or explicit states like proxy-confirmed and not-testable, depending on source schema. [file:1][file:25] |
| Trajectory Marks | Per-round directional marks, sparkline, or dot sequence showing persistence across rounds. [file:1] |

### Display hierarchy

- Traits with validated or proxy-confirmed live evidence should sort to the top when the grid is presented in summary mode. [file:25]
- Traits with neutral consensus and zero or blank magnitude should render at reduced opacity, consistent with the blueprint guidance. [file:1]
- Traits that remain not-testable should stay accessible, but should not visually compete with traits that moved the round read. [file:1][file:25]

## Preferred Codex behavior

The 2026 Open Championship Codex implementation established the preferred behavior for the round-review tabs:

- Lead with the most decision-relevant validated traits. [file:25]
- Collapse visual noise by de-emphasizing non-testable rows instead of letting them dominate the same visual plane. [file:1]
- Preserve the cumulative-learning record without forcing the operator to parse a long undifferentiated table first. [file:1][file:25]
- Keep the round tab usable as both a quick operator panel and an audit checkpoint. [file:25]

This is the standard to keep. In practice, it outperforms a flat full-table presentation where every trait row appears equally important regardless of validation state. [file:1][file:25]

## Anti-patterns

Avoid these implementation mistakes:

- Rendering all traits with identical visual emphasis in the first viewport, even when most are not testable. [file:1]
- Filling the Live Lean strip with every trait instead of only the strongest round signals. [file:1][file:25]
- Showing magnitude dashes or empty trajectory marks in a way that crowds out validated rows. [file:25]
- Letting diagnostics blocks or narrative notes push the cumulative-learning grid below the fold unnecessarily. [file:1]
- Replacing canonical trait keys or consensus fields with ad hoc UI labels that break audit traceability. [file:1][file:25]

## Sort and emphasis rules

When the round file contains mixed evidence quality, use this emphasis order:

1. Validated
2. Proxy-confirmed
3. Mixed or neutral with non-zero magnitude
4. Not-testable but operationally relevant
5. Not-testable and inactive

This ordering keeps the interface aligned with VenueDNA’s requirement to separate structural signal from thin evidence and unresolved noise. [file:25][file:1]

## Data-binding rules

The round-review UI should read directly from the canonical round-analysis and cumulative-learning artifacts rather than hardcoded tables. The architecture blueprint specifies pre-tournament and round tabs sourced from `eventpayload.json`, `r1analysis.json`, `r2analysis.json`, `r3analysis.json`, and `r4analysis.json` or `finalanalysis.json`, with the cumulative learning grid populated from `cumulativelearning.json`. [file:1][file:25]

Required behavior:

- Disable future-round tabs until their files exist. [file:1]
- Render a stub state for unavailable round data rather than hallucinating content. [file:1][file:25]
- Preserve machine-readable trait keys internally even if a friendlier label is displayed. [file:1]
- Keep round-state logic data-driven, not manually edited per event. [file:23][file:25]

## Implementation checklist

Use this checklist for future event Board builds:

- Round tabs source only canonical round files and cumulative-learning artifacts. [file:1][file:25]
- Live Lean strip is concise and prioritized. [file:25]
- Validated traits appear first in the first viewport. [file:25]
- Not-testable traits are visually de-emphasized rather than removed. [file:1]
- The cumulative-learning grid preserves the five-column blueprint structure. [file:1]
- Future-round tabs are disabled until data exists. [file:1]
- No narrative or decorative component overrides the audit table’s primary role. [file:1][file:25]

## Adoption recommendation

Store this spec beside the architecture blueprint as an implementation addendum for future VenueDNA event builds. The blueprint remains the structural contract, while this document captures the stronger Round Learning presentation behavior proven by the 2026 Open Championship Codex dry run. [file:1][file:25]
