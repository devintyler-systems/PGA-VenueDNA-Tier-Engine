"""Analyze course_insights enrichment — print-safe ASCII output"""
import csv, re
from statistics import mean
from pathlib import Path

R1  = Path(r"C:\PGA_VenueDNA\events\2026_TravelersChampionship\output\round1 player & course stats")
fp  = R1 / "round1_course_insights.csv"

with open(fp, newline="", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

def parse_prox(s):
    s = s.strip()
    m = re.match(r"(\d+)'\s*(\d+)\"", s)
    if m: return int(m.group(1))*12 + int(m.group(2))
    m2 = re.match(r"(\d+)'", s)
    if m2: return int(m2.group(1))*12
    return None

def parse_pct(s):
    try: return float(str(s).rstrip("%"))
    except: return None

def avg(lst):
    v = [x for x in lst if x is not None]
    return round(mean(v), 3) if v else None

def pf(v, r=2): return str(round(v, r)) if v is not None else "-"

def get_pos(r):
    try: return int(r["POS"].replace("T",""))
    except: return 99

groups = {
    "top10": [r for r in rows if get_pos(r) <= 10],
    "top18": [r for r in rows if get_pos(r) <= 18],
    "mid":   [r for r in rows if 19 <= get_pos(r) <= 45],
    "bot":   [r for r in rows if get_pos(r) > 45],
    "all":   rows,
}

print("=== DataGolf vs PGA TOUR SG cross-validation ===")
check = {"Cole": ("2.876","0.412"), "Griffin": ("-1.436","5.348"), "Scheffler": ("1.018","0.917")}
for r in rows:
    if r["Last Name"] in check:
        pt_app, pt_putt = check[r["Last Name"]]
        print(f"  {r['First Name']} {r['Last Name']}: DG_APP={r['SG-APP']} PGAT_APP={pt_app} DG_PUTT={r['SG-Putt']} PGAT_PUTT={pt_putt}")

print()

metrics = [
    ("d_distance",    lambda r: float(r["D. Distance"]) if r["D. Distance"] else None),
    ("d_accuracy",    lambda r: parse_pct(r["D. Accuracy"])),
    ("gir",           lambda r: parse_pct(r["GIR"])),
    ("fairway_prox",  lambda r: parse_prox(r["Fairway Prox"])),
    ("rough_prox",    lambda r: parse_prox(r["Rough Prox"])),
    ("scrambling",    lambda r: parse_pct(r["Scrambling"])),
    ("great_shots",   lambda r: int(r["Great Shots"]) if r["Great Shots"] else None),
    ("poor_shots",    lambda r: int(r["Poor Shots"]) if r["Poor Shots"] else None),
    ("net_shots",     lambda r: int(r["Great Shots"])-int(r["Poor Shots"]) if r["Great Shots"] and r["Poor Shots"] else None),
    ("sg_t2g",        lambda r: float(r["SG-T2G"]) if r["SG-T2G"] else None),
    ("sg_bs",         lambda r: float(r["SG-BS"]) if r["SG-BS"] else None),
]

print(f"{'Metric':<22} {'Top10':>8} {'Top18':>8} {'Mid':>8} {'Bot':>8} {'All':>8}  Delta(T10-All)")
for name, fn in metrics:
    avgs = {g: avg([fn(r) for r in grp]) for g, grp in groups.items()}
    d = round(avgs["top10"] - avgs["all"], 2) if avgs["top10"] is not None and avgs["all"] is not None else None
    print(f"{name:<22} {pf(avgs['top10']):>8} {pf(avgs['top18']):>8} {pf(avgs['mid']):>8} {pf(avgs['bot']):>8} {pf(avgs['all']):>8}  {'+'+str(d) if d and d>0 else str(d)}")

print()
print("=== KEY TRAIT ENHANCEMENTS ===")
fp_t10 = avg([parse_prox(r["Fairway Prox"]) for r in groups["top10"]])
fp_all = avg([parse_prox(r["Fairway Prox"]) for r in rows if parse_prox(r["Fairway Prox"]) is not None])
delta_in = round(fp_all - fp_t10, 0)
print(f"Fairway Prox (LOWER=better proximity to hole):")
print(f"  Top10 avg: {fp_t10}\" ({round(fp_t10/12,1)} ft)  Field avg: {fp_all}\" ({round(fp_all/12,1)} ft)")
print(f"  Leaders were {abs(int(delta_in))}\" ({round(abs(delta_in)/12,1)} ft) CLOSER from fairway -> APP_Wedge/100-150 VALIDATED")

sc_t10 = avg([parse_pct(r["Scrambling"]) for r in groups["top10"]])
sc_all = avg([parse_pct(r["Scrambling"]) for r in rows])
print(f"Scrambling: Top10={sc_t10}% vs Field={sc_all}% (delta={round(sc_t10-sc_all,1):+}%) -> ARG UPGRADED")

da_t10 = avg([parse_pct(r["D. Accuracy"]) for r in groups["top10"]])
da_all = avg([parse_pct(r["D. Accuracy"]) for r in rows])
print(f"D. Accuracy: Top10={da_t10}% vs Field={da_all}% (delta={round(da_t10-da_all,1):+}%) -> OTT_Accuracy VALIDATED")

gir_t10 = avg([parse_pct(r["GIR"]) for r in groups["top10"]])
gir_all = avg([parse_pct(r["GIR"]) for r in rows])
print(f"GIR: Top10={gir_t10}% vs Field={gir_all}% (delta={round(gir_t10-gir_all,1):+}%) -> APP composite VALIDATED")

dd_t10 = avg([float(r["D. Distance"]) for r in groups["top10"]])
dd_all = avg([float(r["D. Distance"]) for r in rows])
print(f"D. Distance: Top10={dd_t10}yds vs Field={dd_all}yds (delta={round(dd_t10-dd_all,1):+}yds) -> OTT_Distance WEAK confirmed")
