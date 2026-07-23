# Claude Code Prompt 05 — Ask the Model without an LLM

You are implementing a deterministic `Ask the Model` query layer for the PGA VenueDNA app.

Goal: give users natural-language-style access to filters and structured questions without calling an external LLM.

## Principle
This is a parser and filter engine, not a chatbot.

## Scope
- Add a compact query bar
- Parse common requests into structured filters
- Return filtered rows/cards instantly from local data

## Query types to support
- tier filters, such as `show tier 2`
- exclusion filters, such as `without flags`
- probability filters, such as `win pct above 3`
- structural filters, such as `debut players`, `links specialists`, `high VFS`
- rule filters, such as `show R4 penalties`
- combined filters, such as `tier 2 with VFS above 88 and no flags`

## Rules
- No generated prose analysis required
- Return interpretable results and the parsed filter tokens
- Unknown query parts should fail gracefully and ask for a tighter structured query
- Must work from local payload fields only

## Output
Return:
1. implementation summary
2. files changed
3. supported query grammar
4. next best extensions for phase 2
