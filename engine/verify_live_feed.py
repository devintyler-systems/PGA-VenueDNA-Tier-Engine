#!/usr/bin/env python3
"""
VenueDNA live-feed verification harness — 2026 The Open Championship.

Generates adversarial R1 CSV files with real-world feed edge cases and
validates the full build_round_analysis.py pipeline against them.

Edge cases covered
──────────────────
  Lowercase leaderboard headers : "player", "pos", "total"
  Colon-format SG headers       : "SG:OTT", "SG:APP", "SG:ARG", "SG:PUTT", "SG:Total"
  Diacritic player names        : Nicolai Højgaard, Rasmus Højgaard, Sebastian Söderberg
  Name mismatch                 : "Matthew Fitzpatrick" vs model "Matt Fitzpatrick"
  Period-initial alternate      : "A.J. Ruin" — tests period-strip in ascii_fold
  Late alternates               : players absent from pre-tournament model
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import unicodedata
from pathlib import Path

_ROOT    = Path(__file__).resolve().parent.parent
SLUG     = "2026_the_open_championship"
EVENT    = _ROOT / "events" / SLUG
OUT      = EVENT / "output"
DEP      = EVENT / "deploy" / "data"
R1_DIR   = OUT / "round1"
TFM_PATH = OUT / f"{SLUG}_trait_form_matrix.csv"
PAY_PATH = DEP / "event_payload.json"

TRAIT_COL_HEADERS = [
    "trait_app_150_200", "trait_driving_accuracy", "trait_ott_positional",
    "trait_app_overall",  "trait_sg_putt",          "trait_sg_arg",
]
EXPECTED_TRAIT_KEYS = {
    "app_150_200", "ott_accuracy", "ott_positional",
    "app_overall",  "sg_putt",     "sg_arg",
}

# ── Adversarial edge-case entries injected after the matched-player rows ──────
# (live_name, pos_str, score, sg_ott, sg_app, sg_arg, sg_putt, sg_tot)
_EDGE: list[tuple] = [
    # Diacritic names — survive ascii_fold ø→drop and ö→o
    ("Nicolai Højgaard",    "T6",  -4, +0.55, +0.91, +0.22, +0.38, +2.06),
    ("Rasmus Højgaard",     "T6",  -4, +0.48, +0.78, +0.19, +0.27, +1.72),
    ("Sebastian Söderberg", "T10", -3, +0.41, +0.65, +0.14, +0.44, +1.64),
    # Name mismatch: "Matthew" in live vs "Matt" in model → lands in unmatched
    ("Matthew Fitzpatrick", "T14", -2, +0.31, +1.08, -0.10, +0.21, +1.50),
    # Genuine alternates not in pre-tournament model
    ("Emilio Fernandez",    "21",  +3, -0.12, -0.25, +0.07, -0.29, -0.59),
    # Period-initial name — tests ascii_fold period stripping
    ("A.J. Ruin",           "22",  +4, -0.19, -0.33, -0.06, -0.22, -0.80),
]


# ── Normalization helpers (mirror updated build_round_analysis.py) ─────────────

def _fold(s: str) -> str:
    """ascii_fold + period strip — must stay in sync with build_round_analysis.py."""
    folded = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")
    return folded.replace('.', '')


def _lf(first: str, last: str) -> str:
    return f"{last}, {first}".strip(", ") if last else first.strip()


# ── Backup / restore ──────────────────────────────────────────────────────────

_BACKUPS: list[tuple[Path, bytes | None]] = []


def _backup(p: Path) -> None:
    _BACKUPS.append((p, p.read_bytes() if p.exists() else None))


def _restore_all() -> None:
    for p, content in _BACKUPS:
        if content is None:
            p.unlink(missing_ok=True)
        else:
            p.write_bytes(content)
    _BACKUPS.clear()


# ── Model player extraction ───────────────────────────────────────────────────

def load_model_players() -> list[dict]:
    """Read real event_payload.json and return sorted list of {first, last, rank}."""
    with open(PAY_PATH, encoding="utf-8") as f:
        payload = json.load(f)

    players: list[dict] = []
    for p in payload.get("players", []):
        last  = p.get("last_name",  "").strip()
        first = p.get("first_name", "").strip()
        if not last and not first:
            pn = p.get("player_name", "")
            if not pn:
                continue
            parts = pn.split(",", 1)
            last  = parts[0].strip()
            first = parts[1].strip() if len(parts) > 1 else ""
        players.append({"first": first, "last": last, "rank": p.get("rank", 999)})

    for t in range(1, 6):
        for p in payload.get("tiers", {}).get(f"tier_{t}", []):
            pn = p.get("player_name", "")
            if pn:
                parts = pn.split(",", 1)
                players.append({
                    "last":  parts[0].strip(),
                    "first": parts[1].strip() if len(parts) > 1 else "",
                    "rank":  p.get("rank", 999),
                })

    players.sort(key=lambda x: x["rank"])
    return players


# ── CSV writers ───────────────────────────────────────────────────────────────

def write_tfm(model: list[dict], path: Path) -> None:
    """Trait form matrix keyed by ascii-folded 'Last, First' — matches pipeline lookups."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name_key", "player_display"] + TRAIT_COL_HEADERS)
        for i, p in enumerate(model):
            display = _fold(_lf(p["first"], p["last"]))
            nk      = display.lower()
            scores  = [round(max(20.0, 78.0 - i * 0.45 + j * 1.5), 1)
                       for j in range(len(TRAIT_COL_HEADERS))]
            w.writerow([nk, display] + scores)
    print(f"[verify] Wrote TFM  ({len(model)} player rows) -> {path.name}")


def write_leaderboard(model: list[dict], path: Path) -> None:
    """Lowercase headers ('player','pos','total') with edge cases appended."""
    base = model[:20]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["player", "pos", "total"])          # ← lowercase headers
        for i, p in enumerate(base):
            fl    = f"{p['first']} {p['last']}".strip()
            score = -8 + i
            pos   = "1" if i == 0 else f"T{i + 1}"
            w.writerow([fl, pos, score])
        for e in _EDGE:
            w.writerow([e[0], e[1], e[2]])
    n = len(base) + len(_EDGE)
    print(f"[verify] Wrote LB   ({n} rows, lowercase headers) -> {path.name}")


def write_sg(model: list[dict], path: Path) -> None:
    """Colon-format SG headers ('SG:OTT','SG:APP',...) — tests column alias normalization."""
    base = model[:20]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Player", "SG:OTT", "SG:APP", "SG:ARG", "SG:PUTT", "SG:Total"])
        for i, p in enumerate(base):
            fl = f"{p['first']} {p['last']}".strip()
            w.writerow([
                fl,
                round(0.80 - i * 0.040, 3),
                round(1.20 - i * 0.065, 3),
                round(0.30 - i * 0.018, 3),
                round(0.50 - i * 0.028, 3),
                round(2.80 - i * 0.151, 3),
            ])
        for e in _EDGE:
            w.writerow([e[0], e[3], e[4], e[5], e[6], e[7]])
    n = len(base) + len(_EDGE)
    print(f"[verify] Wrote SG   ({n} rows, SG:COL headers) -> {path.name}")


# ── Pipeline runner ───────────────────────────────────────────────────────────

def run_pipeline() -> int:
    cmd = [
        sys.executable,
        str(_ROOT / "engine" / "build_round_analysis.py"),
        "--round", "1",
        "--event", SLUG,
    ]
    result = subprocess.run(cmd, text=True, cwd=str(_ROOT))
    return result.returncode


# ── Output validator ──────────────────────────────────────────────────────────

def validate() -> bool:
    out_path = DEP / "r1_analysis.json"
    if not out_path.exists():
        print("[FAIL] r1_analysis.json not written", file=sys.stderr)
        return False

    with open(out_path, encoding="utf-8") as f:
        d = json.load(f)

    errors: list[str] = []

    if d.get("schema_version") != "1.1":
        errors.append(f"schema_version={d.get('schema_version')!r} (expected '1.1')")

    actual_traits = set(d.get("trait_audit", {}).keys())
    missing = EXPECTED_TRAIT_KEYS - actual_traits
    if missing:
        errors.append(f"Missing trait_audit keys: {sorted(missing)}")

    mm = d.get("match_summary", {})
    if mm.get("matched", 0) < 5:
        errors.append(
            f"Critically low match count {mm.get('matched')}/{mm.get('total_r1')} "
            "— header normalization may have failed"
        )

    snap_names = {r["r1_name"] for r in d.get("leaderboard_snapshot", [])}
    for diac in ("Nicolai Højgaard", "Rasmus Højgaard", "Sebastian Söderberg"):
        if diac not in snap_names:
            errors.append(f"Diacritic player '{diac}' absent from leaderboard_snapshot")

    unmatched = mm.get("unmatched", [])
    if "Matthew Fitzpatrick" not in unmatched:
        print("[warn] 'Matthew Fitzpatrick' not in unmatched — model may use full 'Matthew' spelling")

    if errors:
        print("\n[FAIL] Validation errors:")
        for e in errors:
            print(f"  [x] {e}")
        return False

    print(f"\n[PASS] schema v1.1 | traits: {sorted(actual_traits)}")
    print(f"       matched {mm.get('matched')}/{mm.get('total_r1')} | "
          f"unmatched: {unmatched}")
    return True


# ── Cleanup ───────────────────────────────────────────────────────────────────

def cleanup(generated: list[Path]) -> None:
    for p in generated:
        p.unlink(missing_ok=True)
    for d in [R1_DIR]:
        try:
            d.rmdir()
        except Exception:
            pass
    _restore_all()
    print(f"[verify] Cleaned {len(generated)} generated input files; backups restored")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> int:
    print("=" * 62)
    print("  VenueDNA Live-Feed Verification Harness")
    print(f"  Event : {SLUG}")
    print("=" * 62)
    print()

    if not PAY_PATH.exists():
        print(f"[FAIL] event_payload.json not found: {PAY_PATH}", file=sys.stderr)
        return 1

    model = load_model_players()
    if not model:
        print("[FAIL] No players extracted from event_payload.json", file=sys.stderr)
        return 1
    print(f"[verify] Loaded {len(model)} model players from event_payload.json")

    # Track generated files for cleanup
    generated: list[Path] = []

    # Backup and generate TFM
    _backup(TFM_PATH)
    write_tfm(model, TFM_PATH)
    generated.append(TFM_PATH)

    # Backup cumulative_learning.json (we'll restore it after)
    _backup(DEP / "cumulative_learning.json")
    _backup(OUT / f"{SLUG}_cumulative_learning.json")

    # Generate adversarial round1 CSVs
    lb_path = R1_DIR / "round1_leaderboard.csv"
    sg_path = R1_DIR / "round1_player_strokes_gained.csv"
    write_leaderboard(model, lb_path)
    write_sg(model, sg_path)
    generated += [lb_path, sg_path]

    print()
    print("-- Running pipeline ---------------------------------------------")
    rc = run_pipeline()

    print()
    if rc != 0:
        print(f"[FAIL] Pipeline exited with code {rc}", file=sys.stderr)
        cleanup(generated)
        return 1

    print("-- Validating output --------------------------------------------")
    ok = validate()

    # Clean up generated inputs; leave r1_analysis.json for node validation command
    cleanup(generated)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
