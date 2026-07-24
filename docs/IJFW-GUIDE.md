# IJFW Pilot Guide — PGA VenueDNA Only

Scope: this file is scoped to `PGA-VenueDNA-Tier-Engine`. Do not install IJFW globally or roll it into DerbyEdge, APEX-OS, DealEngine, or any other repo until VenueDNA proves it out.

## What this is and why

[IJFW](https://github.com/FerroxLabs/ijfw) ("It Just F*cking Works") is a local-first infrastructure layer for AI coding agents — shared cross-tool memory, a plan/execute/verify workflow spine, multi-model cross-audit, and a token-routing/observability layer. MIT-licensed, 203 stars / 40 forks, active CI with real supply-chain hardening (gitleaks secret redaction, protected release gate, 9-surface version lockstep), ships a native Windows PowerShell installer (`src/install.ps1`). It runs under Claude Code and Gemini CLI — both tools already in your stack.

It directly targets two bottlenecks already flagged in the VenueDNA Registry entry:

1. **Context compression / source consolidation** — IJFW's memory engine stores decisions as plain markdown under `.ijfw/memory/`, ranks recall by recency, and only promotes a pattern to durable knowledge after three references across two sessions (no single offhand comment becomes gospel).
2. **Closing the post-event learning loop without hindsight contamination** — IJFW's cross-audit fires a second and third model (different training lineage) against a diff before it ships, and its memory model supports bi-temporal facts (what was true *as of* a point in time, not just now). That maps almost directly onto the Backlog's requirement to "prevent hindsight contamination" in the Post-Event VenueDNA Learning Loop.

## Coexistence test: checked out (static analysis, 2026-07-23)

Compared actual hook registrations between the two plugins directly via GitHub:

| Event | Superpowers | IJFW |
|---|---|---|
| `SessionStart` | matcher `startup\|clear\|compact` | no matcher — fires on all |
| `PreCompact` | — | ✅ |
| `Stop` | — | ✅ |
| `PreToolUse` | — | ✅ (3 scripts + `Read\|Bash` matcher) |
| `PostToolUse` | — | ✅ |
| `UserPromptSubmit` | — | ✅ |

Claude Code merges hook arrays across all enabled plugins — no exclusivity, no file overwrite, no crash risk. **Only overlap is `SessionStart`**, where both will fire every session start/clear/compact. That's stacked latency, not a conflict.

**One real check still required locally (not verifiable via GitHub alone):** after installing IJFW, open a fresh session and read both banners. If IJFW's `session-start.sh` output and Superpowers' output give *contradictory* workflow instructions (e.g., IJFW pushing its own routing framework while Superpowers pushes `/superpowers:brainstorm`), that's a one-time prompt-tuning fix, not a reason to uninstall either. Still pilot IJFW's memory + cross-audit engines only — hold off on its workflow-discipline engine while Superpowers stays your driver for brainstorm → plan → execute. Decide the winner after one real week of VenueDNA work.

**Scope boundary:** IJFW's memory/routing layer should respect the same blast-radius rule as everything else touching this repo — full read access anywhere, but no autonomous write access outside `events/<event>/deploy/` without the same approval gate defined in `RALPH-LOOP-POLICY.md`.

## Install (Windows PowerShell)

Run from `C:\PGA_VenueDNA`:

```powershell
cd C:\PGA_VenueDNA
npm install -g @ijfw/install
ijfw-install
```

The installer detects Claude Code and Gemini CLI on your machine and configures both automatically — nothing to hand-edit. It will not touch `.superpowers` or any other plugin config (confirmed in its own docs: "Your other plugins, MCP servers, and per-project trust settings stay untouched").

Verify:

```powershell
ijfw preflight
```

## Pilot checklist (do this before trusting it on real venue logic)

1. Install, then open a fresh Claude Code session in `PGA_VenueDNA` and confirm the session-start hook loads (`ijfw` shows in `/help` or the hook log).
2. Have a normal working session — mention a real project decision ("VenueFitDelta uses course-history weighting, not field-strength weighting"). Close the session.
3. Open a new session in Claude Code, ask an unrelated question that should surface that fact. Confirm recall works and is attributed correctly.
4. Repeat step 2–3 from Gemini CLI instead of Claude Code — confirm the same fact recalls across tools. This cross-tool recall is IJFW's actual differentiator; if it doesn't work, there's no reason to keep it over Superpowers alone.
5. Make one real scoring-logic change (e.g., a VenueFitDelta or confidence-flag tweak) and run cross-audit against it before merging:
   ```powershell
   ijfw cross-audit
   ```
   Review consensus vs. contested findings. Do not accept a finding as fact — the Registry rule stands: no field or logic change becomes confirmed without evidence.
6. Check the local dashboard once (binds to `localhost` only, no external calls):
   ```powershell
   ijfw dashboard
   ```

## Kill switch

If it fights with Superpowers or produces noise:

```powershell
ijfw personalize off      # disable personalization only
ijfw-uninstall            # full removal, backs up every modified file with a .bak.<timestamp>, memory data preserved by default
```

## What NOT to install yet from the same research pass

From the "10 Claude Code Plugins" reference image, three more tools came up. Verdict, VenueDNA-specific:

- **Context7** (`/plugin install context7`) — pulls live, version-pinned docs into context instead of stale training data. Cheap, low-risk, genuinely useful while writing Python/Streamlit code. **Adopt**, independent of the IJFW decision.
- **Playwright MCP — Adopt (2026-07-23).** VenueDNA does have a browser-facing layer: the live per-event HTML boards deployed to Netlify. Confirmed a real defect this exact tool would have caught: the `Form` sparkline column shipped blank on the live 3M Open board even though the fix landed in commit `9009e2d` — because there's no CI/CD (no `netlify.toml`, no GitHub Actions) and the existing UX overhaul plan's verification only checks the JSON payload, never the rendered page. See `docs/superpowers/specs/2026-07-23-playwright-verification-gate.md` for the exact gate and install command. Chrome DevTools MCP stays the escape hatch for deep JS/console debugging if a Playwright screenshot surfaces something that needs root-causing — not a default addition.
- **Ralph Loop — Scoped yes (2026-07-23).** Unattended runs permitted only inside `events/<event>/deploy/` (HTML/CSS/JS presentation layer) — mirrors the Global Constraints the UX overhaul plan already self-imposes. `engine/`, `data/venuedna_master.db`, `input/`, `output/`, and any venue-knowledge/model-rule file remain fully gated, no exception. Full policy: `RALPH-LOOP-POLICY.md`. The Automation Backlog's Post-Event VenueDNA Learning Loop entry has been updated with this exact carve-out.
- **GitHub MCP** — already covered; GitHub connector access is already live in this session via `gh` CLI.

## Sources

- [FerroxLabs/ijfw](https://github.com/FerroxLabs/ijfw)
- [IJFW npm package](https://www.npmjs.com/package/@ijfw/install)
- [obra/superpowers](https://github.com/obra/superpowers)
- [obra/superpowers-marketplace](https://github.com/obra/superpowers-marketplace/blob/main/README.md)
