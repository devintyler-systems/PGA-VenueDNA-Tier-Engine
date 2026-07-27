"""
prep_r3_artifacts.py — 2026 3M Open R3 data prep
Generates round3_leaderboard.csv and round3_player_strokes_gained.csv
from available tournament data.

Inputs:
  output/final_tournament/final_leaderboard.csv  — all 4 rounds' stroke scores
  output/round2/round2_player_strokes_gained.csv — R1+R2 cumulative SG
  output/round3/live_stats_r3_values.csv         — R3 round-specific SG

Outputs:
  output/round3/round3_leaderboard.csv
  output/round3/round3_player_strokes_gained.csv
"""
from __future__ import annotations
import csv
import re
import unicodedata
from pathlib import Path

PAR = 71
EVENT_DIR = Path(__file__).resolve().parent.parent

FINAL_LB  = EVENT_DIR / "output/final_tournament/final_leaderboard.csv"
R2_SG     = EVENT_DIR / "output/round2/round2_player_strokes_gained.csv"
R3_LIVE   = EVENT_DIR / "output/round3/live_stats_r3_values.csv"
R3_LB_OUT = EVENT_DIR / "output/round3/round3_leaderboard.csv"
R3_SG_OUT = EVENT_DIR / "output/round3/round3_player_strokes_gained.csv"

_COMBINING = re.compile(r"[̀-ͯ]")


def load_csv(p: Path) -> list[dict]:
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(p, newline="", encoding=enc) as f:
                rows = list(csv.DictReader(f))
            if rows:
                return rows
        except Exception:
            continue
    return []


def asc(s: str) -> str:
    nfd = unicodedata.normalize("NFD", str(s))
    return _COMBINING.sub("", nfd).replace(".", "").lower().strip()


def lf_to_fl(name: str) -> str:
    if ", " in name:
        last, first = name.split(", ", 1)
        return f"{first.strip()} {last.strip()}"
    return name


def pf(v) -> float | None:
    s = str(v).strip()
    if s in ("", "-", "null", "N/A"):
        return None
    if s.upper() == "E":
        return 0.0
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def add_sg(a: float | None, b: float | None) -> float | None:
    if a is None and b is None:
        return None
    return round((a or 0.0) + (b or 0.0), 3)


def fmt(v: float | None) -> str:
    return f"{v:.3f}" if v is not None else ""


def ordinal(n: int) -> str:
    if n % 100 in (11, 12, 13):
        return f"({n}th)"
    sfx = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"({n}{sfx})"


def rank_col(rows: list[dict], key: str) -> dict[int, int]:
    vals = sorted(
        [(i, r[key]) for i, r in enumerate(rows) if r[key] is not None],
        key=lambda x: -x[1],
    )
    return {orig_i: rank for rank, (orig_i, _) in enumerate(vals, 1)}


# ── Load sources ───────────────────────────────────────────────────────────────
final_lb     = load_csv(FINAL_LB)
r2_sg_rows   = load_csv(R2_SG)
r3_live_rows = load_csv(R3_LIVE)

r2_sg_by = {asc(r["Player"]): r for r in r2_sg_rows if r.get("Player")}
r3_sg_by = {asc(lf_to_fl(r.get("player_name", ""))): r for r in r3_live_rows}

print(f"Loaded: {len(final_lb)} final-lb | {len(r2_sg_rows)} r2-sg | {len(r3_live_rows)} r3-live")

# ── Build through-R3 leaderboard ──────────────────────────────────────────────
active: list[dict] = []
cut_wd: list[dict] = []

for row in final_lb:
    pos  = row.get("POS", "").strip()
    name = row.get("PLAYER", "").strip()
    rd1  = pf(row.get("RD1"))
    rd2  = pf(row.get("RD2"))
    rd3  = pf(row.get("RD3"))

    if pos in ("CUT", "WD", "DQ") or rd3 is None:
        total_r2 = pf(row.get("TOTAL"))
        strokes_2r = pf(row.get("STROKES"))
        cut_wd.append({
            "POS": pos,
            "PLAYER": name,
            "TOTAL": int(total_r2) if total_r2 is not None else "-",
            "Round": "-",
            "R1": int(rd1) if rd1 is not None else "-",
            "R2": int(rd2) if rd2 is not None else "-",
            "R3": "-",
            "STROKES": int(strokes_2r) if strokes_2r is not None else "-",
            "_sort": total_r2 if total_r2 is not None else 9999,
        })
    else:
        r3_to_par = int(rd3) - PAR
        total_r3  = int(rd1 - PAR) + int(rd2 - PAR) + r3_to_par
        active.append({
            "PLAYER": name,
            "_total_r3": total_r3,
            "_r3_score": r3_to_par,
            "_rd1": int(rd1),
            "_rd2": int(rd2),
            "_rd3": int(rd3),
            "_strokes": int(rd1) + int(rd2) + int(rd3),
        })

active.sort(key=lambda r: r["_total_r3"])
cut_wd.sort(key=lambda r: r["_sort"])

lb_out: list[dict] = []
i = 0
while i < len(active):
    j = i
    while j < len(active) - 1 and active[j + 1]["_total_r3"] == active[i]["_total_r3"]:
        j += 1
    tie  = (j - i + 1) > 1
    pos_str = f"T{i + 1}" if tie else str(i + 1)
    for k in range(i, j + 1):
        a = active[k]
        lb_out.append({
            "POS":    pos_str,
            "PLAYER": a["PLAYER"],
            "TOTAL":  a["_total_r3"],
            "Round":  a["_r3_score"],
            "R1":     a["_rd1"],
            "R2":     a["_rd2"],
            "R3":     a["_rd3"],
            "STROKES": a["_strokes"],
        })
    i = j + 1

for r in cut_wd:
    r.pop("_sort", None)
    lb_out.append(r)

with open(R3_LB_OUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["POS", "PLAYER", "TOTAL", "Round", "R1", "R2", "R3", "STROKES"])
    writer.writeheader()
    writer.writerows(lb_out)
print(f"[OK] Wrote {len(lb_out)} rows -> {R3_LB_OUT.name}")

# ── Build round3_player_strokes_gained.csv ────────────────────────────────────
sg_data: list[dict] = []
for row in lb_out:
    name = row["PLAYER"]
    pos  = row["POS"]
    key  = asc(name)
    r2r  = r2_sg_by.get(key)
    r3r  = r3_sg_by.get(key)

    if pos in ("CUT", "WD", "DQ"):
        sg_data.append({
            "POS": pos, "Player": name,
            "TOT": row["TOTAL"], "THRU": "CUT", "R3": "-",
            "sg_ott":  pf(r2r.get("SG-Off the Tee")) if r2r else None,
            "sg_app":  pf(r2r.get("SG-Approach to Green")) if r2r else None,
            "sg_arg":  pf(r2r.get("SG-Around the Green")) if r2r else None,
            "sg_putt": pf(r2r.get("SG-Putting")) if r2r else None,
            "sg_tot":  pf(r2r.get("SG Total")) if r2r else None,
        })
    else:
        sg_data.append({
            "POS": pos, "Player": name,
            "TOT": row["TOTAL"], "THRU": "F", "R3": row["R3"],
            "sg_ott":  add_sg(pf(r2r.get("SG-Off the Tee")) if r2r else None,
                              pf(r3r.get("sg_ott")) if r3r else None),
            "sg_app":  add_sg(pf(r2r.get("SG-Approach to Green")) if r2r else None,
                              pf(r3r.get("sg_app")) if r3r else None),
            "sg_arg":  add_sg(pf(r2r.get("SG-Around the Green")) if r2r else None,
                              pf(r3r.get("sg_arg")) if r3r else None),
            "sg_putt": add_sg(pf(r2r.get("SG-Putting")) if r2r else None,
                              pf(r3r.get("sg_putt")) if r3r else None),
            "sg_tot":  add_sg(pf(r2r.get("SG Total")) if r2r else None,
                              pf(r3r.get("sg_total")) if r3r else None),
        })
        if not r2r:
            print(f"  [warn] No R2 SG for active player: {name}")
        if not r3r:
            print(f"  [warn] No R3 SG for active player: {name}")

active_sg = [r for r in sg_data if r["POS"] not in ("CUT", "WD", "DQ")]

ott_ranks  = rank_col(active_sg, "sg_ott")
app_ranks  = rank_col(active_sg, "sg_app")
arg_ranks  = rank_col(active_sg, "sg_arg")
putt_ranks = rank_col(active_sg, "sg_putt")
tot_ranks  = rank_col(active_sg, "sg_tot")

SG_FIELDS = [
    "POS", "Player", "TOT", "THRU", "R3",
    "SG-Off the Tee", "SG-Off the Tee (Rank)",
    "SG-Approach to Green", "SG-Approach to Green (Rank)",
    "SG-Around the Green", "SG-Around the Green (Rank)",
    "SG-Putting", "SG-Putting (Rank)",
    "SG Total", "SG Total (Rank)",
]

with open(R3_SG_OUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=SG_FIELDS)
    writer.writeheader()
    active_counter = 0
    for r in sg_data:
        is_active = r["POS"] not in ("CUT", "WD", "DQ")
        ai = active_counter if is_active else None
        if is_active:
            active_counter += 1
        writer.writerow({
            "POS": r["POS"], "Player": r["Player"],
            "TOT": r["TOT"], "THRU": r["THRU"], "R3": r["R3"],
            "SG-Off the Tee":              fmt(r["sg_ott"]),
            "SG-Off the Tee (Rank)":       ordinal(ott_ranks[ai]) if (ai is not None and ai in ott_ranks) else "",
            "SG-Approach to Green":        fmt(r["sg_app"]),
            "SG-Approach to Green (Rank)": ordinal(app_ranks[ai]) if (ai is not None and ai in app_ranks) else "",
            "SG-Around the Green":         fmt(r["sg_arg"]),
            "SG-Around the Green (Rank)":  ordinal(arg_ranks[ai]) if (ai is not None and ai in arg_ranks) else "",
            "SG-Putting":                  fmt(r["sg_putt"]),
            "SG-Putting (Rank)":           ordinal(putt_ranks[ai]) if (ai is not None and ai in putt_ranks) else "",
            "SG Total":                    fmt(r["sg_tot"]),
            "SG Total (Rank)":             ordinal(tot_ranks[ai]) if (ai is not None and ai in tot_ranks) else "",
        })

print(f"[OK] Wrote {len(sg_data)} rows -> {R3_SG_OUT.name}")
print("\nNext step: python engine/build_round_analysis.py --event_slug 2026_3m_open --round 3")
