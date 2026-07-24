# Ralph Loop Policy — PGA VenueDNA

**Status:** Active as of 2026-07-23. Governs any autonomous/unattended agent loop (Ralph Loop or equivalent) running against this repository.

## Rule

Unattended execution — no per-step human approval required — is permitted **only** inside:

```
events/<event>/deploy/**
```

That is: board HTML, `app.js`, `styles.css`, and client-side view logic. Presentation-layer only.

## Everything else stays gated

No exception, unattended or otherwise, for:

- `engine/*.py` — scoring/trait/probability logic
- `data/venuedna_master.db` — the master data store
- `events/<event>/input/` and `events/<event>/output/` — raw and processed data artifacts
- Any venue profile, model-rule, or weighting file

Changes in these paths require the same human-approval and write-back rules already defined for the Post-Event VenueDNA Learning Loop and VenueDNA Weekly Event Pipeline (see the Perplexity Mastermind Automation Backlog).

## Why this boundary, not a wider one

It isn't a new restriction — it's the same boundary already self-imposed in [`docs/superpowers/plans/2026-07-23-3m-open-ux-overhaul.md`](./superpowers/plans/2026-07-23-3m-open-ux-overhaul.md) under "Global Constraints":

> `deploy/` is the sole surface area — never touch `engine/`, `output/`, or `input/` files. Tier assignments, VTS scores, and probability values in `board_export.json` are read-only. Scenario (Analyst Mode) adjustments must NEVER write back to any JSON artifact.

Ralph Loop just gets to run that boundary unattended instead of task-by-task with a human confirming each step.

## Recovery

`deploy/` changes are git-tracked and Netlify deploys are a separate manual step (no CI/CD auto-deploy is currently wired — confirmed no `netlify.toml` or GitHub Actions workflow exists in this repo as of 2026-07-23). That means a bad unattended run never reaches production without a manual `git push` + manual Netlify deploy in between — a natural second checkpoint, not just git revert.

## Revisit trigger

Revisit this policy if:
- Netlify deploy becomes automated from `main` (removes the manual second checkpoint — may warrant re-tightening).
- `deploy/` scripts are ever given write access back into `output/` or `data/` (architecture change, not a policy change — should not happen silently).
