
# CLAUDE.md Session Init Setup

## Folder placement
Yes. Create a `tools/` folder at the project root, in the same directory as `CLAUDE.md`.

Example:

```text
PGA_VenueDNA/
├── CLAUDE.md
├── app.py
├── config.py
├── tools/
│   └── update_claude_md.py
└── data/
```

Do the same pattern for Draft-OS and DerbyEdge.

## What the script now adds
- `project_handle: <slug>` near the top of `CLAUDE.md`
- Session timestamp
- Current git branch
- Latest 5 commits
- A `Next focus` line for manual intent before the session starts

## Handle logic
The script tries to infer the handle from the first H1 in `CLAUDE.md`.
Examples:
- `# PGA VenueDNA` -> `pga_venuedna`
- `# Draft-OS` -> `draft_os`
- `# DerbyEdge` -> `derbyedge`

If there is no H1, it falls back to the folder name.

## Run command
From the project root:

```bash
python3 tools/update_claude_md.py
```

## Recommended workflow
1. Open terminal in project root.
2. Run the script.
3. Edit the `Next focus` line in `CLAUDE.md`.
4. Start Claude Code.

## Optional shell alias
```bash
alias csession='python3 tools/update_claude_md.py && ${EDITOR:-nano} CLAUDE.md'
```

Run `csession` from the repo root and it will stamp the file, then open it for a quick edit.
