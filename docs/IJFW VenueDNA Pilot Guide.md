# IJFW Pilot Guide — PGA VenueDNA Only

Scope: this file is scoped to `PGA-VenueDNA-Tier-Engine`. Do not install IJFW globally or roll it into DerbyEdge, APEX-OS, DealEngine, or any other repo until VenueDNA proves it out.

## What this is and why

[IJFW](https://github.com/FerroxLabs/ijfw) ("It Just F*cking Works") is a local-first infrastructure layer for AI coding agents — shared cross-tool memory, a plan/execute/verify workflow spine, multi-model cross-audit, and a token-routing/observability layer. MIT-licensed, 203 stars / 40 forks, active CI with real supply-chain hardening (gitleaks secret redaction, protected release gate, 9-surface version lockstep), ships a native Windows PowerShell installer (`src/install.ps1`). It runs under Claude Code and Gemini CLI — both tools already in your stack.

It directly targets two bottlenecks already flagged in the VenueDNA Registry entry:

1. **Context compression / source consolidation** — IJFW's memory engine stores decisions as plain markdown under `.ijfw/memory/`, ranks recall by recency, and only promotes a pattern to durable knowledge after three references across two sessions (no single offhand comment becomes gospel).
2. **Closing the post-event learning loop without hindsight contamination** — IJFW's cross-audit fires a second and third model (different training lineage) against a diff before it ships, and its memory model supports bi-temporal facts (what was true *as of* a point in time, not just now). That maps almost directly onto the Backlog's requirement to "prevent hindsight contamination" in the Post-Event VenueDNA Learning Loop.

## The conflict you need to test first

You already installed [Superpowers](https://github.com/obra/superpowers) (`.superpowers` in `C:\PGA_VenueDNA`) for brainstorm/plan/execute workflow. IJFW's own positioning explicitly frames itself as a replacement for that exact workflow-discipline layer, not a companion to it. Both want to own the brainstorm → plan → execute → verify sequence. Running both live risks double-gating (two systems each waiting for you to approve the same phase) or contradictory session memory.

**Do not run both engines in parallel long-term.** Pilot IJFW's memory + cross-audit engines only, and hold off on IJFW's workflow-discipline engine (`OSD`-equivalent) while Superpowers stays your driver. Decide the winner after one real week of VenueDNA work, then disable the loser's workflow commands — don't leave both wired in.

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
- **Playwright MCP / Chrome DevTools MCP** — only earn their keep if VenueDNA has a browser-facing Streamlit/web layer you need to test or debug live. **Adapt when that surface exists, skip until then.**
- **Ralph Loop** (autonomous, self-referential, unattended dev loop) — **Reject for VenueDNA as currently scoped.** The Registry and Backlog both hard-require human approval before any model-rule or venue-knowledge write-back ("No automatic write-back until approval"). An unattended agent loop is a direct policy conflict until you explicitly design an approval gate around it.
- **GitHub MCP** — already covered; GitHub connector access is already live in this session via `gh` CLI.

## Sources

- [FerroxLabs/ijfw](https://github.com/FerroxLabs/ijfw)
- [IJFW npm package](https://www.npmjs.com/package/@ijfw/install)
- [obra/superpowers](https://github.com/obra/superpowers)
- [obra/superpowers-marketplace](https://github.com/obra/superpowers-marketplace/blob/main/README.md)
