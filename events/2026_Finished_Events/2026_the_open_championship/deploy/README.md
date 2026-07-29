# 2026 Open Championship deploy pack

Run the packaging layer from the repository root:

```powershell
# build_dry_run_pack.py removed in cleanup commit 58f8302 — see git history
python events\2026_the_open_championship\engine\build_board_v3.py
```

The package preserves the v3 scorer's rankings and values. It writes the canonical event artifacts to `output/`, refreshes `deploy/data/`, and supplies a browser-compatible `board_export.json` adapter. Fields that the v3 source does not emit are marked unavailable or left unpopulated; they are never inferred in packaging.

For the static site, mirror `deploy/` to `public/`. Serve `public/` over HTTP and open `index.html`.
