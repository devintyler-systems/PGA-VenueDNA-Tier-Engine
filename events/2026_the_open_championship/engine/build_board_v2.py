"""
build_board_v2.py — VenueDNA Single-File HTML Board
2026 The Open Championship · Royal Birkdale Golf Club
Reads event_payload.json, event_context.json, weather.json
Produces 2026_the_open_championship_board.html (single-file, no fetch())
"""

import json
import os
import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE     = Path(__file__).parent.parent
DATA_DIR = BASE / "deploy" / "data"
OUT_FILE = BASE / "deploy" / "2026_the_open_championship_board.html"

PAYLOAD_FILE  = DATA_DIR / "event_payload.json"
CONTEXT_FILE  = DATA_DIR / "event_context.json"
WEATHER_FILE  = DATA_DIR / "weather.json"
ANALYSIS_FILE = DATA_DIR / "final_analysis.json"

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def js(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))

# ── Load data ──────────────────────────────────────────────────────────────────
print(f"[build_board_v2] Reading data from {DATA_DIR}")
payload     = load_json(PAYLOAD_FILE)
ctx         = load_json(CONTEXT_FILE)
weather     = load_json(WEATHER_FILE)
analysis    = load_json(ANALYSIS_FILE) if ANALYSIS_FILE.exists() else {}

players     = payload.get("players", [])
value_sec   = analysis.get("value_section", {})
ap_flags    = analysis.get("anti_pattern_flags", {})
tier_counts = ctx.get("tier_counts", {})

print(f"[build_board_v2] Loaded {len(players)} players | tiers: {tier_counts}")

# ── Hardcoded constants ────────────────────────────────────────────────────────
BADGE_SCHEMA = {
    "Defending Champ":  {"type": "fit",     "color": "#c4a000", "tooltip": "Defending champion at Royal Birkdale — maximum venue calibration"},
    "Course Horse":     {"type": "fit",     "color": "#16a34a", "tooltip": "Positive venue history + course-adj — proven scorer at Royal Birkdale"},
    "Iron Edge":        {"type": "fit",     "color": "#0891b2", "tooltip": "Top-tier venue fit score (≥64) — approach profile optimally matched to Birkdale 150-200yd zone"},
    "Form Spike":       {"type": "fit",     "color": "#16a34a", "tooltip": "Current scoring pace significantly above 12-month baseline (+1.0 SG) — momentum confirmed"},
    "Elite NSI":        {"type": "fit",     "color": "#4f46e5", "tooltip": "World-class neutral skill index (≥85) — elite ball-striking profile translates to any surface"},
    "Dark Horse":       {"type": "ceiling", "color": "#7c3aed", "tooltip": "Win probability ≥2% from Tier 3 — structural ceiling underpriced by market at this venue"},
    "Ceiling Play":     {"type": "ceiling", "color": "#6d28d9", "tooltip": "Elevated win ceiling score — one elite-trait spike can produce a top-5 result from this tier"},
    "Live Longshot":    {"type": "ceiling", "color": "#7c3aed", "tooltip": "Win probability >2% from Tier 3+ — market may be underpricing this player"},
    "Fragile Favorite": {"type": "risk",    "color": "#dc2626", "tooltip": "Top-2-tier player with anti-pattern flags — structural blowup risk present"},
    "Anti-Pattern":     {"type": "risk",    "color": "#dc2626", "tooltip": "2+ recurring weak-link trait flags for this venue profile — pattern of failure here"},
    "Cut Sweat":        {"type": "risk",    "color": "#d97706", "tooltip": "Make-cut probability below 60% — weekend status structurally uncertain"},
    "False Safety":     {"type": "risk",    "color": "#a16003", "tooltip": "High cut rate but near-zero win ceiling — a positional trap for bettors"},
    "Debut Watch":      {"type": "risk",    "color": "#d97706", "tooltip": "First start at Royal Birkdale — zero venue-specific calibration data"},
    "Volatile Putter":  {"type": "risk",    "color": "#b45309", "tooltip": "High putting variance — links fescue greens can amplify or collapse this trait"},
    "Form Cold":        {"type": "risk",    "color": "#dc2626", "tooltip": "Scoring pace below seasonal baseline — negative momentum entering event"},
}

TIER_LABELS = {1: "Structural Winner", 2: "Primary Contender", 3: "Dark Horse", 4: "Fragile Path", 5: "Fade / Cut Risk"}

TRAIT_DEFS = [
    {"key": "app_150_200",      "label": "APP 150-200 (Long Iron)",   "weight": 0.30},
    {"key": "ott_positional",   "label": "OTT / Positional Drive",    "weight": 0.20},
    {"key": "app_overall",      "label": "APP Overall",               "weight": 0.15},
    {"key": "driving_accuracy", "label": "Driving Accuracy",          "weight": 0.12},
    {"key": "sg_putt",          "label": "Putting (Links-Regressed)", "weight": 0.13},
    {"key": "sg_arg",           "label": "Short Game / ARG",          "weight": 0.10},
]

# ── Render JS data blobs ───────────────────────────────────────────────────────
JS_PLAYERS      = js(players)
JS_CTX          = js(ctx)
JS_WEATHER      = js(weather)
JS_BADGE_SCHEMA = js(BADGE_SCHEMA)
JS_TIER_LABELS  = js(TIER_LABELS)
JS_TRAIT_DEFS   = js(TRAIT_DEFS)
JS_VALUE_SEC    = js(value_sec)
JS_AP_FLAGS     = js(ap_flags)

# ── Build HTML ─────────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>VenueDNA — The Open Championship 2026</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@400;600;700&display=swap" rel="stylesheet"/>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
/* ── Design Tokens ── */
:root {{
  --bg:#0f1419;--surface:#161d27;--surface2:#1e2936;--border:#2a3a4a;
  --text:#e8e0d4;--muted:#7a8fa6;--gold:#c9a84c;--gold-dim:#8a6e30;
  --green-dark:#0d2b1a;--green:#1a3a2a;
  --t1:#16a34a;--t2:#2563eb;--t3:#7c3aed;--t4:#ea580c;--t5:#dc2626;
  --radius:8px;--shadow:0 2px 16px rgba(0,0,0,0.45);
}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;font-size:14px;line-height:1.5;}}
h1,h2,h3{{font-family:'Playfair Display',serif;}}
a{{color:var(--gold);text-decoration:none;}}
button{{cursor:pointer;border:none;background:none;font-family:inherit;}}

/* ── Header ── */
.header{{background:linear-gradient(135deg,#0d1a24 0%,#1a2d3f 100%);border-bottom:2px solid var(--gold-dim);padding:1.5rem 1.2rem 1.2rem;}}
.header-inner{{max-width:1400px;margin:0 auto;}}
.header h1{{font-size:clamp(1.3rem,3vw,2rem);color:var(--gold);letter-spacing:.02em;}}
.header h1 span{{color:#fff;}}
.header-sub{{font-size:.82rem;color:var(--muted);margin-top:.3rem;letter-spacing:.03em;}}
.header-stats{{display:flex;gap:1.2rem;flex-wrap:wrap;margin-top:.9rem;}}
.stat-pill{{background:var(--surface2);border:1px solid var(--border);border-radius:20px;padding:.22rem .75rem;font-size:.75rem;color:var(--text);}}
.stat-pill span{{color:var(--gold);font-weight:700;margin-left:.25rem;}}

/* ── Conditions ── */
.conditions-section{{max-width:1400px;margin:1.2rem auto;padding:0 1rem;}}
.conditions-section h2{{color:var(--gold);font-size:1.1rem;margin-bottom:.8rem;}}
.weather-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:.75rem;margin-bottom:.9rem;}}
.weather-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:.85rem 1rem;}}
.weather-card-tag{{display:inline-block;padding:.15rem .55rem;border-radius:12px;font-size:.67rem;font-weight:700;color:#000;margin-bottom:.4rem;}}
.weather-card-date{{font-size:.72rem;color:var(--muted);margin-bottom:.3rem;}}
.weather-card-wind{{font-size:1rem;font-weight:700;color:var(--text);}}
.weather-card-dir{{font-size:.72rem;color:var(--muted);margin-bottom:.3rem;}}
.weather-card-note{{font-size:.73rem;color:var(--muted);font-style:italic;}}
.conditions-risk{{background:var(--surface2);border:1px solid var(--gold-dim);border-radius:var(--radius);padding:.75rem 1rem;font-size:.8rem;color:var(--text);}}
.conditions-risk b{{color:var(--gold);}}

/* ── Controls Bar ── */
.controls-sticky{{position:sticky;top:0;z-index:50;background:var(--surface);border-bottom:1px solid var(--border);padding:.55rem 1rem;}}
.controls-bar{{max-width:1400px;margin:0 auto;display:flex;gap:.5rem;flex-wrap:wrap;align-items:center;}}
.search-wrap{{position:relative;flex:1;min-width:180px;max-width:340px;}}
.search-wrap input{{width:100%;background:var(--surface2);border:1px solid var(--border);border-radius:20px;padding:.38rem .9rem .38rem 2rem;color:var(--text);font-size:.82rem;outline:none;}}
.search-wrap input:focus{{border-color:var(--gold-dim);}}
.search-icon{{position:absolute;left:.65rem;top:50%;transform:translateY(-50%);color:var(--muted);font-size:.9rem;pointer-events:none;}}
.search-clear{{position:absolute;right:.5rem;top:50%;transform:translateY(-50%);color:var(--muted);font-size:.9rem;background:none;border:none;cursor:pointer;display:none;}}
.ctrl-btn{{background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:.38rem .75rem;font-size:.78rem;color:var(--text);transition:border-color .15s,background .15s;white-space:nowrap;}}
.ctrl-btn:hover{{border-color:var(--gold-dim);background:var(--green);}}
.ctrl-btn.active{{border-color:var(--gold);color:var(--gold);}}
.ctrl-btn-muted{{color:var(--muted);}}
.fav-count{{color:var(--gold);font-weight:700;}}
.preset-wrap{{position:relative;}}
.preset-dropdown{{position:absolute;top:calc(100% + 4px);left:0;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);z-index:100;min-width:180px;box-shadow:var(--shadow);}}
.preset-item{{display:block;width:100%;text-align:left;padding:.5rem .9rem;font-size:.78rem;color:var(--text);border-bottom:1px solid var(--border);}}
.preset-item:hover{{background:var(--surface2);color:var(--gold);}}
.preset-divider{{height:1px;background:var(--border);}}
.filter-badge{{background:var(--gold);color:#000;border-radius:10px;padding:0 .45rem;font-size:.67rem;font-weight:700;margin-left:.3rem;}}
.active-pills{{max-width:1400px;margin:.3rem auto 0;display:flex;flex-wrap:wrap;gap:.3rem;}}
.pill{{background:var(--surface2);border:1px solid var(--gold-dim);border-radius:14px;padding:.18rem .6rem;font-size:.72rem;color:var(--gold);display:inline-flex;align-items:center;gap:.3rem;}}
.pill button{{color:var(--muted);font-size:.75rem;line-height:1;}}
.pill button:hover{{color:var(--gold);}}

/* ── Filter Drawer ── */
.filter-drawer{{max-width:1400px;margin:.5rem auto;padding:0 1rem;display:none;}}
.filter-drawer-inner{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:1rem 1.2rem;}}
.filter-drawer h3{{color:var(--gold);font-size:.9rem;margin-bottom:.8rem;display:flex;justify-content:space-between;align-items:center;}}
.fp-close{{color:var(--muted);font-size:1rem;}}
.fp-close:hover{{color:var(--gold);}}
.filter-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:.75rem;margin-bottom:.8rem;}}
.filter-group{{display:flex;flex-direction:column;gap:.2rem;}}
.filter-group label{{font-size:.72rem;color:var(--muted);}}
.filter-group input[type=range]{{accent-color:var(--gold);}}
.filter-group .range-val{{font-size:.78rem;color:var(--gold);font-weight:700;}}
.trait-toggles{{display:flex;flex-wrap:wrap;gap:.4rem;margin-bottom:.6rem;}}
.trait-toggle{{background:var(--surface2);border:1px solid var(--border);border-radius:14px;padding:.22rem .65rem;font-size:.72rem;color:var(--text);cursor:pointer;transition:all .15s;}}
.trait-toggle.on{{border-color:var(--gold);color:var(--gold);background:var(--green-dark);}}
.imputed-row{{font-size:.72rem;color:var(--muted);display:flex;align-items:center;gap:.5rem;margin-top:.4rem;}}
.imputed-row input{{accent-color:var(--gold);}}

/* ── Tier Board ── */
.tier-board{{max-width:1400px;margin:1.2rem auto;padding:0 1rem;}}
.tier-board-header{{color:var(--gold);font-size:1.1rem;margin-bottom:.8rem;}}
.tier-accordion{{display:flex;flex-direction:column;gap:.5rem;}}
.tier-section{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;}}
.tier-section-header{{display:flex;align-items:center;gap:.75rem;padding:.75rem 1rem;cursor:pointer;user-select:none;transition:background .15s;}}
.tier-section-header:hover{{background:var(--surface2);}}
.tier-badge-big{{padding:.2rem .65rem;border-radius:5px;font-size:.7rem;font-weight:700;color:#fff;}}
.tier-badge-big.t1{{background:var(--t1);}}
.tier-badge-big.t2{{background:var(--t2);}}
.tier-badge-big.t3{{background:var(--t3);}}
.tier-badge-big.t4{{background:var(--t4);}}
.tier-badge-big.t5{{background:var(--t5);}}
.tier-header-label{{font-family:'Playfair Display',serif;font-size:.95rem;color:var(--text);flex:1;}}
.tier-header-meta{{font-size:.72rem;color:var(--muted);display:flex;gap:1rem;}}
.tier-header-meta span{{color:var(--text);}}
.tier-arrow{{color:var(--muted);font-size:.75rem;transition:transform .2s;}}
.tier-section.open .tier-arrow{{transform:rotate(90deg);}}
.tier-cards{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:.65rem;padding:.75rem 1rem 1rem;display:none;}}
.tier-section.open .tier-cards{{display:grid;}}
.player-card{{background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius);padding:.75rem;cursor:pointer;transition:border-color .15s,transform .1s;}}
.player-card:hover{{border-color:var(--gold-dim);transform:translateY(-1px);}}
.card-name{{font-weight:700;font-size:.87rem;color:var(--text);margin-bottom:.25rem;display:flex;align-items:center;gap:.4rem;flex-wrap:wrap;}}
.card-tier-badge{{padding:.1rem .4rem;border-radius:4px;font-size:.62rem;font-weight:700;color:#fff;}}
.card-tier-badge.t1{{background:var(--t1);}}
.card-tier-badge.t2{{background:var(--t2);}}
.card-tier-badge.t3{{background:var(--t3);}}
.card-tier-badge.t4{{background:var(--t4);}}
.card-tier-badge.t5{{background:var(--t5);}}
.debut-badge{{background:#7c3aed;color:#fff;padding:.08rem .35rem;border-radius:4px;font-size:.6rem;font-weight:700;}}
.card-metrics{{display:grid;grid-template-columns:1fr 1fr;gap:.25rem .5rem;margin:.4rem 0;}}
.card-metric{{font-size:.72rem;color:var(--muted);}}
.card-metric span{{color:var(--text);font-weight:600;}}
.card-badges{{display:flex;flex-wrap:wrap;gap:.2rem;margin:.35rem 0;}}
.badge-pill{{padding:.1rem .4rem;border-radius:10px;font-size:.58rem;font-weight:700;color:#fff;}}
.form-dot{{width:8px;height:8px;border-radius:50%;display:inline-block;flex-shrink:0;}}
.form-dot.hot{{background:#16a34a;}}
.form-dot.warm{{background:#86efac;}}
.form-dot.neutral{{background:#6b7280;}}
.form-dot.cool{{background:#fcd34d;}}
.form-dot.cold{{background:#dc2626;}}
.card-view-btn{{font-size:.72rem;color:var(--gold);margin-top:.4rem;display:block;}}

/* ── Field Explorer Table ── */
.field-section{{max-width:1400px;margin:1.5rem auto;padding:0 1rem;}}
.field-header{{display:flex;align-items:center;gap:.75rem;margin-bottom:.75rem;flex-wrap:wrap;}}
.field-header h2{{color:var(--gold);font-size:1.1rem;}}
.filter-count-badge{{background:var(--surface2);border:1px solid var(--gold-dim);border-radius:12px;padding:.15rem .55rem;font-size:.72rem;color:var(--gold);}}
.table-container{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);overflow:auto;max-height:600px;}}
table.field-table{{width:100%;border-collapse:collapse;font-size:.75rem;}}
table.field-table thead{{position:sticky;top:0;z-index:10;background:var(--surface2);}}
table.field-table th{{padding:.5rem .55rem;text-align:left;color:var(--muted);font-weight:600;border-bottom:1px solid var(--border);white-space:nowrap;cursor:pointer;user-select:none;}}
table.field-table th:hover{{color:var(--text);}}
table.field-table th.sort-asc::after{{content:' ▲';color:var(--gold);font-size:.6rem;}}
table.field-table th.sort-desc::after{{content:' ▼';color:var(--gold);font-size:.6rem;}}
table.field-table td{{padding:.45rem .55rem;border-bottom:1px solid rgba(42,58,74,0.5);color:var(--text);white-space:nowrap;}}
table.field-table tr:hover td{{background:var(--surface2);}}
.player-name-link{{color:var(--text);cursor:pointer;font-weight:600;}}
.player-name-link:hover{{color:var(--gold);}}
.tier-dot{{padding:.1rem .38rem;border-radius:4px;font-size:.62rem;font-weight:700;color:#fff;}}
.tier-dot.t1{{background:var(--t1);}}
.tier-dot.t2{{background:var(--t2);}}
.tier-dot.t3{{background:var(--t3);}}
.tier-dot.t4{{background:var(--t4);}}
.tier-dot.t5{{background:var(--t5);}}
.win-bar-wrap{{display:flex;align-items:center;gap:.3rem;}}
.win-bar{{height:5px;border-radius:3px;background:var(--gold);min-width:2px;}}
.fav-star-btn{{color:var(--muted);font-size:.9rem;cursor:pointer;background:none;border:none;}}
.fav-star-btn.active{{color:var(--gold);}}
.empty-state{{text-align:center;padding:3rem;color:var(--muted);}}
.empty-state button{{margin-top:.75rem;background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:.45rem 1rem;color:var(--text);font-size:.8rem;cursor:pointer;}}

/* ── Player Modal ── */
.modal-overlay{{position:fixed;inset:0;background:rgba(0,0,0,0.75);z-index:200;display:none;align-items:center;justify-content:center;padding:1rem;}}
.modal-overlay.open{{display:flex;}}
.modal{{background:var(--surface);border:1px solid var(--border);border-radius:12px;max-width:720px;width:100%;max-height:90vh;overflow:hidden;display:flex;flex-direction:column;box-shadow:0 8px 48px rgba(0,0,0,0.6);}}
.modal-wide{{max-width:1000px;}}
.modal-header{{padding:1rem 1.2rem;border-bottom:1px solid var(--border);display:flex;align-items:flex-start;gap:.75rem;}}
.modal-header-text{{flex:1;}}
.modal-header h2{{font-size:1.2rem;color:var(--gold);}}
.modal-header-sub{{font-size:.75rem;color:var(--muted);margin-top:.2rem;display:flex;gap:.5rem;flex-wrap:wrap;align-items:center;}}
.modal-close{{color:var(--muted);font-size:1.2rem;padding:.2rem .4rem;border-radius:4px;flex-shrink:0;}}
.modal-close:hover{{color:var(--gold);background:var(--surface2);}}
.modal-body{{overflow-y:auto;padding:1.1rem 1.2rem;flex:1;}}
.metrics-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:.6rem;margin-bottom:1rem;}}
.metric-cell{{background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius);padding:.55rem .7rem;}}
.metric-label{{font-size:.65rem;color:var(--muted);margin-bottom:.2rem;}}
.metric-val{{font-size:1rem;font-weight:700;color:var(--text);}}
.section-title{{font-size:.8rem;color:var(--gold);font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin:.9rem 0 .45rem;border-bottom:1px solid var(--border);padding-bottom:.3rem;}}
.betting-path{{display:flex;align-items:center;gap:.6rem;margin-bottom:.6rem;}}
.lane-label{{font-size:.85rem;font-weight:700;color:var(--text);}}
.viability-tag{{padding:.15rem .6rem;border-radius:10px;font-size:.68rem;font-weight:700;}}
.viability-winner{{background:#16a34a22;border:1px solid #16a34a;color:#16a34a;}}
.viability-top5{{background:#2563eb22;border:1px solid #2563eb;color:#6ea8fe;}}
.viability-top10{{background:#7c3aed22;border:1px solid #7c3aed;color:#a78bfa;}}
.viability-top20{{background:#ea580c22;border:1px solid #ea580c;color:#fb923c;}}
.viability-cut{{background:#6b728022;border:1px solid #6b7280;color:#9ca3af;}}
.viability-pass{{background:#dc262622;border:1px solid #dc2626;color:#f87171;}}
.trait-bars{{display:flex;flex-direction:column;gap:.45rem;}}
.trait-bar-row{{display:flex;align-items:center;gap:.6rem;}}
.trait-bar-label{{font-size:.72rem;color:var(--muted);width:160px;flex-shrink:0;}}
.trait-bar-outer{{flex:1;height:8px;background:var(--surface2);border-radius:4px;overflow:hidden;}}
.trait-bar-inner{{height:100%;border-radius:4px;transition:width .3s;}}
.trait-bar-inner.high{{background:#2563eb;}}
.trait-bar-inner.mid{{background:#16a34a;}}
.trait-bar-inner.low{{background:#dc2626;}}
.trait-bar-val{{font-size:.72rem;color:var(--text);font-weight:600;width:32px;text-align:right;flex-shrink:0;}}
.sg-block{{display:flex;flex-direction:column;gap:.35rem;}}
.sg-row{{display:flex;align-items:center;gap:.6rem;}}
.sg-label{{font-size:.72rem;color:var(--muted);width:100px;flex-shrink:0;}}
.sg-bar-outer{{flex:1;position:relative;height:6px;background:var(--surface2);border-radius:3px;overflow:hidden;}}
.sg-bar-pos{{position:absolute;left:50%;height:100%;background:#16a34a;border-radius:0 3px 3px 0;}}
.sg-bar-neg{{position:absolute;right:50%;height:100%;background:#dc2626;border-radius:3px 0 0 3px;}}
.sg-val{{font-size:.72rem;font-weight:600;width:60px;text-align:right;flex-shrink:0;}}
.sg-val.pos{{color:#4ade80;}}
.sg-val.neg{{color:#f87171;}}
.flag-list{{display:flex;flex-direction:column;gap:.3rem;}}
.flag-row{{background:rgba(220,38,38,0.1);border:1px solid rgba(220,38,38,0.3);border-radius:6px;padding:.4rem .65rem;font-size:.75rem;}}
.flag-row .flag-name{{color:#f87171;font-weight:700;}}
.flag-row .flag-desc{{color:var(--muted);}}
.risk-block{{font-size:.78rem;color:var(--text);background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:.5rem .75rem;margin-bottom:.4rem;}}
.risk-block b{{color:var(--gold);}}
.conviction-block{{background:var(--green-dark);border:1px solid var(--green);border-radius:var(--radius);padding:.65rem .85rem;}}
.conviction-stmt{{font-size:.82rem;color:var(--text);margin-bottom:.4rem;}}
.conviction-traits{{list-style:none;display:flex;flex-direction:column;gap:.2rem;}}
.conviction-traits li{{font-size:.72rem;color:var(--muted);padding-left:.8rem;position:relative;}}
.conviction-traits li::before{{content:'•';position:absolute;left:0;color:var(--gold);}}
.scoring-block{{display:grid;grid-template-columns:repeat(3,1fr);gap:.5rem;margin-bottom:.4rem;}}
.scoring-cell{{background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:.45rem .6rem;text-align:center;}}
.scoring-cell .sc-label{{font-size:.65rem;color:var(--muted);}}
.scoring-cell .sc-val{{font-size:.95rem;font-weight:700;color:var(--text);}}
.scoring-band{{font-size:.72rem;color:var(--muted);font-style:italic;text-align:center;margin-top:.2rem;}}
.tee-row{{display:flex;gap:1rem;flex-wrap:wrap;font-size:.75rem;}}
.tee-item{{background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:.35rem .65rem;}}
.tee-item .ti-label{{color:var(--muted);font-size:.67rem;}}
.tee-item .ti-val{{color:var(--text);font-weight:600;}}

/* ── Anti-Pattern Panel ── */
.ap-section{{max-width:1400px;margin:1.5rem auto;padding:0 1rem;}}
.ap-section h2{{color:var(--gold);font-size:1.1rem;margin-bottom:.8rem;}}
.ap-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:.75rem;}}
.ap-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:.85rem 1rem;}}
.ap-card-header{{display:flex;align-items:center;gap:.5rem;margin-bottom:.4rem;}}
.ap-flag-label{{font-size:.82rem;font-weight:700;color:#f87171;}}
.ap-count-badge{{background:rgba(220,38,38,0.15);border:1px solid rgba(220,38,38,0.4);border-radius:10px;padding:.1rem .45rem;font-size:.67rem;color:#f87171;font-weight:700;}}
.ap-desc{{font-size:.73rem;color:var(--muted);margin-bottom:.45rem;}}
.ap-players{{display:flex;flex-wrap:wrap;gap:.25rem;}}
.ap-player-chip{{background:var(--surface2);border:1px solid var(--border);border-radius:12px;padding:.12rem .5rem;font-size:.67rem;color:var(--text);cursor:pointer;}}
.ap-player-chip:hover{{border-color:var(--gold-dim);color:var(--gold);}}

/* ── Value & Disagreement ── */
.value-section{{max-width:1400px;margin:1.5rem auto;padding:0 1rem;}}
.value-section h2{{color:var(--gold);font-size:1.1rem;margin-bottom:.8rem;}}
.value-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:.75rem;}}
.value-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:.85rem 1rem;}}
.value-card h3{{font-size:.82rem;color:var(--gold);margin-bottom:.5rem;font-family:'Inter',sans-serif;font-weight:700;}}
.value-item{{display:flex;align-items:flex-start;gap:.5rem;padding:.35rem 0;border-bottom:1px solid rgba(42,58,74,0.6);}}
.value-item:last-child{{border-bottom:none;}}
.value-name{{font-size:.8rem;font-weight:700;color:var(--text);cursor:pointer;}}
.value-name:hover{{color:var(--gold);}}
.value-vts{{font-size:.7rem;color:var(--muted);}}
.value-reason{{font-size:.7rem;color:var(--muted);flex:1;}}

/* ── Glossary Modal ── */
.gloss-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;}}
.gloss-col h3{{font-size:.85rem;color:var(--gold);font-family:'Inter',sans-serif;font-weight:700;margin-bottom:.5rem;border-bottom:1px solid var(--border);padding-bottom:.3rem;}}
.gloss-item{{margin-bottom:.4rem;font-size:.72rem;}}
.gloss-item .gi-term{{color:var(--text);font-weight:600;}}
.gloss-item .gi-def{{color:var(--muted);}}

/* ── Footer ── */
footer{{text-align:center;padding:1.5rem;color:var(--muted);font-size:.72rem;border-top:1px solid var(--border);margin-top:2rem;}}

/* ── Nav highlight ── */
.nav-section{{scroll-margin-top:60px;}}

/* ── Responsive ── */
@media(max-width:600px){{
  .metrics-grid{{grid-template-columns:repeat(2,1fr);}}
  .scoring-block{{grid-template-columns:repeat(2,1fr);}}
  .gloss-grid{{grid-template-columns:1fr;}}
  .tier-header-meta{{flex-direction:column;gap:.1rem;}}
}}
</style>
</head>
<body>

<!-- ══ DATA INJECTION ══════════════════════════════════════════════════════ -->
<script>
const PLAYERS = {JS_PLAYERS};
const EVENT_CONTEXT = {JS_CTX};
const WEATHER_DATA = {JS_WEATHER};
const BADGE_SCHEMA = {JS_BADGE_SCHEMA};
const TIER_LABELS = {JS_TIER_LABELS};
const TRAIT_DEFS = {JS_TRAIT_DEFS};
const VALUE_SECTION = {JS_VALUE_SEC};
const AP_FLAGS = {JS_AP_FLAGS};
</script>

<!-- ══ 1. HEADER ══════════════════════════════════════════════════════════ -->
<header class="header">
  <div class="header-inner">
    <h1><span>VenueDNA</span> — The Open Championship 2026</h1>
    <div class="header-sub">Royal Birkdale Golf Club · Par 70 · 7,223 yds · July 17–20, 2026 · Southport, England</div>
    <div class="header-stats" id="header-stats">
      <div class="stat-pill">Field<span id="stat-field">156</span></div>
      <div class="stat-pill">T1 Structural Winners<span id="stat-t1">–</span></div>
      <div class="stat-pill">T2 Contenders<span id="stat-t2">–</span></div>
      <div class="stat-pill">T3 Dark Horses<span id="stat-t3">–</span></div>
      <div class="stat-pill">T4 Fragile<span id="stat-t4">–</span></div>
      <div class="stat-pill">T5 Fade/Cut Risk<span id="stat-t5">–</span></div>
    </div>
  </div>
</header>

<!-- ══ 2. CONDITIONS PANEL ══════════════════════════════════════════════════ -->
<section class="conditions-section nav-section" id="sec-conditions">
  <h2>Forecast — Royal Birkdale</h2>
  <div class="weather-grid" id="weather-grid"></div>
  <div class="conditions-risk">
    <b>Conditions Risk:</b> Irish Sea W/NW winds create sustained 10–25mph conditions across all four rounds. Birkdale's exposed corridors on holes 4, 6, 12, 13, 15, and 18 amplify wind penalty. Approach precision from 150–200yds and links ARG skill are the primary separators. Trajectory control and wind management represent the decisive edges for championship contention.
  </div>
</section>

<!-- ══ 3. STICKY CONTROLS ════════════════════════════════════════════════════ -->
<div class="controls-sticky" id="controls-sticky">
  <div class="controls-bar">
    <div class="search-wrap">
      <span class="search-icon">⌕</span>
      <input type="text" id="search-input" placeholder="Search golfer by name…" autocomplete="off"/>
      <button class="search-clear" id="search-clear">✕</button>
    </div>
    <button class="ctrl-btn" id="btn-filter">Filters <span class="filter-badge" id="filter-badge" style="display:none">0</span></button>
    <button class="ctrl-btn" id="btn-favonly">★ Favorites (<span class="fav-count" id="fav-count">0</span>)</button>
    <div class="preset-wrap">
      <button class="ctrl-btn" id="btn-presets">Views ▾</button>
      <div class="preset-dropdown" id="preset-dropdown" style="display:none">
        <button class="preset-item" data-preset="top-equity">Top Win Equity</button>
        <button class="preset-item" data-preset="iron-elites">Iron Elites</button>
        <button class="preset-item" data-preset="long-iron-fits">Long-Iron Fits</button>
        <button class="preset-item" data-preset="positional-drivers">Positional Drivers</button>
        <button class="preset-item" data-preset="safe-cut-makers">Safe Cut Makers</button>
        <button class="preset-item" data-preset="longshot-dogs">Longshot Dogs</button>
        <div class="preset-divider"></div>
        <button class="preset-item" data-preset="clean-flags">No Risk Flags</button>
        <div class="preset-divider"></div>
        <button class="preset-item" data-preset="favorites">My Card ★</button>
      </div>
    </div>
    <button class="ctrl-btn ctrl-btn-muted" id="btn-glossary">? Glossary</button>
    <button class="ctrl-btn ctrl-btn-muted" id="btn-reset">Reset all</button>
  </div>
  <div class="active-pills" id="active-pills" style="display:none"></div>
</div>

<!-- ══ 4. FILTER DRAWER ═══════════════════════════════════════════════════════ -->
<div class="filter-drawer" id="filter-drawer">
  <div class="filter-drawer-inner">
    <h3>Filters — The Open Championship <button class="fp-close" id="fp-close">✕</button></h3>
    <div class="filter-grid">
      <div class="filter-group">
        <label>VTS min: <span class="range-val" id="lbl-vts">0</span></label>
        <input type="range" id="sl-vts" min="0" max="100" value="0" step="1"/>
      </div>
      <div class="filter-group">
        <label>Win% min: <span class="range-val" id="lbl-win">0</span>%</label>
        <input type="range" id="sl-win" min="0" max="20" value="0" step="0.25"/>
      </div>
      <div class="filter-group">
        <label>Top10% min: <span class="range-val" id="lbl-t10">0</span>%</label>
        <input type="range" id="sl-t10" min="0" max="50" value="0" step="0.5"/>
      </div>
      <div class="filter-group">
        <label>Make Cut% min: <span class="range-val" id="lbl-cut">0</span>%</label>
        <input type="range" id="sl-cut" min="0" max="100" value="0" step="1"/>
      </div>
    </div>
    <div style="font-size:.72rem;color:var(--muted);margin-bottom:.4rem;">Trait Filters (require score ≥ 60):</div>
    <div class="trait-toggles" id="trait-toggles"></div>
    <div class="imputed-row">
      <input type="checkbox" id="fp-include-imputed"/>
      <label for="fp-include-imputed">Include debut / imputed players in filtered results</label>
    </div>
  </div>
</div>

<!-- ══ 5. TIER BOARD ══════════════════════════════════════════════════════════ -->
<section class="tier-board nav-section" id="sec-tiers">
  <h2 class="tier-board-header">Tier Board — Royal Birkdale</h2>
  <div class="tier-accordion" id="tier-accordion"></div>
</section>

<!-- ══ 6. FIELD EXPLORER ═════════════════════════════════════════════════════ -->
<section class="field-section nav-section" id="sec-field">
  <div class="field-header">
    <h2>Field Explorer (156 players)</h2>
    <span class="filter-count-badge" id="field-count-badge">156 shown</span>
    <button class="ctrl-btn ctrl-btn-muted" id="btn-glossary2" style="font-size:.72rem;">? Glossary</button>
  </div>
  <div class="table-container">
    <table class="field-table" id="field-table">
      <thead>
        <tr>
          <th data-col="rank">Rank</th>
          <th data-col="player_name">Player</th>
          <th data-col="tier">Tier</th>
          <th data-col="vts_final">VTS</th>
          <th data-col="win_pct">Win%</th>
          <th data-col="top5_pct">Top5%</th>
          <th data-col="top10_pct">Top10%</th>
          <th data-col="top20_pct">Top20%</th>
          <th data-col="make_cut_prob">Cut%</th>
          <th data-col="sg_app_12m">SG:APP</th>
          <th data-col="sg_ott_12m">SG:OTT</th>
          <th data-col="sg_arg_12m">SG:ARG</th>
          <th data-col="sg_putt_12m">SG:PUTT</th>
          <th data-col="brie_score">BRIE</th>
          <th data-col="tvl_score">TVL</th>
          <th data-col="vfr_score">VFR</th>
          <th data-col="hew_score">HEW</th>
          <th data-col="form_class">Form</th>
          <th data-col="r1_teetime">R1 Tee</th>
          <th>Badges</th>
          <th>★</th>
        </tr>
      </thead>
      <tbody id="field-tbody">
        <tr><td colspan="21" style="text-align:center;color:var(--muted);padding:2rem">Loading…</td></tr>
      </tbody>
    </table>
  </div>
  <div class="empty-state" id="empty-state" style="display:none">
    <div style="font-size:2rem;margin-bottom:.5rem;">⌕</div>
    <div>No players match your filters.</div>
    <button id="empty-reset">Reset all filters</button>
  </div>
</section>

<!-- ══ 9. ANTI-PATTERN PANEL ══════════════════════════════════════════════════ -->
<section class="ap-section nav-section" id="sec-antipattern">
  <h2>Anti-Pattern Analysis — Royal Birkdale</h2>
  <div class="ap-grid" id="ap-grid"></div>
</section>

<!-- ══ 10. VALUE & DISAGREEMENT ══════════════════════════════════════════════ -->
<section class="value-section nav-section" id="sec-value">
  <h2>Value &amp; Disagreement</h2>
  <div class="value-grid" id="value-grid"></div>
</section>

<!-- ══ 11. FOOTER ═════════════════════════════════════════════════════════════ -->
<footer>VenueDNA v2 · The Open Championship 2026 · Royal Birkdale Golf Club · Pre-tournament baseline · Not betting advice</footer>

<!-- ══ PLAYER MODAL ══════════════════════════════════════════════════════════ -->
<div class="modal-overlay" id="player-modal-overlay">
  <div class="modal">
    <div class="modal-header">
      <div class="modal-header-text">
        <h2 id="modal-player-name">–</h2>
        <div class="modal-header-sub" id="modal-player-sub"></div>
      </div>
      <button class="modal-close" id="player-modal-close">✕</button>
    </div>
    <div class="modal-body" id="player-modal-body"></div>
  </div>
</div>

<!-- ══ GLOSSARY MODAL ════════════════════════════════════════════════════════ -->
<div class="modal-overlay" id="glossary-modal-overlay">
  <div class="modal modal-wide">
    <div class="modal-header">
      <div class="modal-header-text">
        <h2 style="color:var(--gold)">Glossary &amp; Key — The Open Championship</h2>
      </div>
      <button class="modal-close" id="glossary-modal-close">✕</button>
    </div>
    <div class="modal-body">
      <div class="gloss-grid">
        <div class="gloss-col">
          <h3>Scores &amp; Metrics</h3>
          <div class="gloss-item"><span class="gi-term">VTS 0-100</span><div class="gi-def">Venue Tier Score: NSI 40% + VFS 30% + VHN 15% + Form 15%</div></div>
          <div class="gloss-item"><span class="gi-term">NSI</span><div class="gi-def">Neutral Skill Index — baseline skill on standard course (0-100)</div></div>
          <div class="gloss-item"><span class="gi-term">VFS</span><div class="gi-def">Venue Fit Score — trait alignment to Royal Birkdale profile (0-100)</div></div>
          <div class="gloss-item"><span class="gi-term">VHN</span><div class="gi-def">Venue History Normalized — Birkdale-specific course history calibration</div></div>
          <div class="gloss-item"><span class="gi-term">Win%</span><div class="gi-def">Model win probability (%)</div></div>
          <div class="gloss-item"><span class="gi-term">Top5/10/20%</span><div class="gi-def">Finish probability for each bracket</div></div>
          <div class="gloss-item"><span class="gi-term">MakeCut%</span><div class="gi-def">36-hole cut survival probability (Top 70 + ties)</div></div>
          <div class="gloss-item"><span class="gi-term">Flags</span><div class="gi-def">Anti-pattern risk count — structural mismatches to this venue</div></div>
        </div>
        <div class="gloss-col">
          <h3>Projected Scoring</h3>
          <div class="gloss-item"><span class="gi-term">Expected</span><div class="gi-def">72-hole score vs par — model median projection</div></div>
          <div class="gloss-item"><span class="gi-term">Ceiling</span><div class="gi-def">Best-case 72-hole score (high-side scenario)</div></div>
          <div class="gloss-item"><span class="gi-term">Floor</span><div class="gi-def">Worst-case 72-hole score (low-side / missed cut risk)</div></div>
          <div class="gloss-item"><span class="gi-term">Band</span><div class="gi-def">Narrative classification of overall scoring profile</div></div>
          <div class="gloss-item"><span class="gi-term">SG values</span><div class="gi-def">Strokes gained L12 months vs field average</div></div>
          <div class="gloss-item"><span class="gi-term">BRIE</span><div class="gi-def">Approach proficiency (SG:APP component)</div></div>
          <div class="gloss-item"><span class="gi-term">TVL</span><div class="gi-def">Off-tee positional value (OTT component)</div></div>
          <div class="gloss-item"><span class="gi-term">HEW</span><div class="gi-def">Ball-striking composite (T2G component)</div></div>
          <div class="gloss-item"><span class="gi-term">VFR</span><div class="gi-def">ARG / short game proficiency</div></div>
        </div>
        <div class="gloss-col">
          <h3>Best Betting Lane</h3>
          <div class="gloss-item"><span class="gi-term">Winner</span><div class="gi-def">Win% ≥ 4% — outright contention structurally supported</div></div>
          <div class="gloss-item"><span class="gi-term">Top 5</span><div class="gi-def">Top5% ≥ 12% — contention ceiling but win slightly below threshold</div></div>
          <div class="gloss-item"><span class="gi-term">Top 10</span><div class="gi-def">Top10% ≥ 20% — consistent podium-range profile</div></div>
          <div class="gloss-item"><span class="gi-term">Top 20</span><div class="gi-def">Top20% ≥ 30% — weekend presence likely</div></div>
          <div class="gloss-item"><span class="gi-term">Make Cut</span><div class="gi-def">MakeCut% ≥ 65% — weekend play only bet</div></div>
          <div class="gloss-item"><span class="gi-term">Pass / No Edge</span><div class="gi-def">No structural edge identified — avoid</div></div>
        </div>
        <div class="gloss-col">
          <h3>Tiers &amp; Traits</h3>
          <div class="gloss-item"><span class="gi-term">T1 ≥ 78</span><div class="gi-def">Structural Winner — elite VTS, multi-trait fit</div></div>
          <div class="gloss-item"><span class="gi-term">T2 63–77</span><div class="gi-def">Primary Contender — strong fit, minor gaps</div></div>
          <div class="gloss-item"><span class="gi-term">T3 50–62</span><div class="gi-def">Dark Horse — ceiling plays, patchy fit</div></div>
          <div class="gloss-item"><span class="gi-term">T4 37–49</span><div class="gi-def">Fragile Path — conditional scenarios only</div></div>
          <div class="gloss-item"><span class="gi-term">T5 &lt; 37</span><div class="gi-def">Fade / Cut Risk — structural misalignment</div></div>
          <div style="margin-top:.5rem;font-size:.7rem;color:var(--muted);font-weight:700;">Trait Abbreviations</div>
          <div class="gloss-item"><span class="gi-term">APP 150-200</span><div class="gi-def">Approach from 150–200yd zone (30% weight)</div></div>
          <div class="gloss-item"><span class="gi-term">OTT/Positional</span><div class="gi-def">Off-tee positional accuracy (20%)</div></div>
          <div class="gloss-item"><span class="gi-term">APP Overall</span><div class="gi-def">Approach overall (15%)</div></div>
          <div class="gloss-item"><span class="gi-term">DA</span><div class="gi-def">Driving Accuracy (12%)</div></div>
          <div class="gloss-item"><span class="gi-term">SG:PUTT</span><div class="gi-def">Putting — links-regressed (13%)</div></div>
          <div class="gloss-item"><span class="gi-term">SG:ARG</span><div class="gi-def">Around-the-green scrambling (10%)</div></div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ══ MAIN JAVASCRIPT ════════════════════════════════════════════════════════ -->
<script>
/* ── State ── */
let filteredPlayers = [];
let sortCol = 'rank';
let sortDir = 1;
let searchQuery = '';
let favorites = new Set(JSON.parse(localStorage.getItem('vdna_open26_favs') || '[]'));
let favOnly = false;
let activePreset = null;
let filterVTS = 0, filterWin = 0, filterT10 = 0, filterCut = 0;
let activeTraitFilters = new Set();
let includeImputed = false;
let tierFilter = null; // null = all

/* AP meta labels */
const AP_META = {{
  bomb_and_spray:      {{ label: 'Bomb + Spray',       desc: 'Elite distance but below-field driving accuracy — Birkdale 22-yd corridors fatal for wide drivers.' }},
  approach_liability:  {{ label: 'Approach Liability', desc: 'Below-field approach in 150-200yd zone — the decisive scoring range at Birkdale par 4s.' }},
  long_iron_weakness:  {{ label: 'Long-Iron Weakness', desc: 'Below 35th percentile in 150-200yd FW — highest-weighted trait at Royal Birkdale.' }},
  poor_links_putter:   {{ label: 'Poor Links Putter',  desc: 'Below-field putting on links fescue — 3-putt avoidance critical.' }},
  debut_risk:          {{ label: 'Debut Risk',         desc: 'No Birkdale or Open history — wind-reading and course management unproven at links level.' }},
  weak_arg_links:      {{ label: 'Weak ARG (Links)',   desc: 'Below-field ARG in links context — revetted pot bunkers require specialized technique.' }},
}};

/* ── Helpers ── */
function fmtVTS(v)  {{ return v != null ? (+v).toFixed(1) : '–'; }}
function fmtPct(v)  {{ return v != null ? (+v).toFixed(2) + '%' : '–'; }}
function fmtSG(v)   {{ if (v == null) return '–'; const n=+v; return (n>=0?'+':'')+n.toFixed(3); }}
function fmtN1(v)   {{ return v != null ? (+v).toFixed(1) : '–'; }}

function tierClass(t)  {{ return 't' + Math.min(5, Math.max(1, +t)); }}
function tierColor(t)  {{
  const m = {{ 1:'var(--t1)', 2:'var(--t2)', 3:'var(--t3)', 4:'var(--t4)', 5:'var(--t5)' }};
  return m[+t] || 'var(--muted)';
}}

function formDotClass(fc) {{
  if (!fc) return 'neutral';
  const s = String(fc).toUpperCase();
  if (s.includes('HOT'))     return 'hot';
  if (s.includes('WARM'))    return 'warm';
  if (s.includes('COOL'))    return 'cool';
  if (s.includes('COLD'))    return 'cold';
  return 'neutral';
}}

function playerDisplayName(p) {{
  const ln = (p.last_name || '').trim();
  const fn = (p.first_name || '').trim();
  if (ln && fn) return fn + ' ' + ln;
  return p.player_id || '?';
}}

function getTraitScore(p, key) {{
  if (!p.trait_scores) return null;
  const t = p.trait_scores.find(t => t.key === key);
  return t ? t.score : null;
}}

function getPlayerFlags(p) {{
  const f = p.anti_pattern_flags || '';
  if (!f || f === 'none' || f === 'None') return [];
  return f.split(',').map(s => s.trim()).filter(Boolean);
}}

function saveFavs() {{
  localStorage.setItem('vdna_open26_favs', JSON.stringify([...favorites]));
}}

/* ── Init header stats ── */
function initStats() {{
  const tc = EVENT_CONTEXT.tier_counts || {{}};
  document.getElementById('stat-t1').textContent = tc['1'] || tc[1] || 0;
  document.getElementById('stat-t2').textContent = tc['2'] || tc[2] || 0;
  document.getElementById('stat-t3').textContent = tc['3'] || tc[3] || 0;
  document.getElementById('stat-t4').textContent = tc['4'] || tc[4] || 0;
  document.getElementById('stat-t5').textContent = tc['5'] || tc[5] || 0;
}}

/* ── Weather cards ── */
function renderWeather() {{
  const el = document.getElementById('weather-grid');
  if (!el || !WEATHER_DATA.rounds) return;
  el.innerHTML = WEATHER_DATA.rounds.map(r => `
    <div class="weather-card">
      <div class="weather-card-tag" style="background:${{r.color}}">R${{r.round}}: ${{r.tag}}</div>
      <div class="weather-card-date">${{r.date}}</div>
      <div class="weather-card-wind">${{r.wind_mph}} mph</div>
      <div class="weather-card-dir">${{r.wind_dir}}</div>
      <div class="weather-card-note">${{r.note}}</div>
    </div>`).join('');
}}

/* ── Trait toggles ── */
function renderTraitToggles() {{
  const el = document.getElementById('trait-toggles');
  if (!el) return;
  el.innerHTML = TRAIT_DEFS.map(t =>
    `<button class="trait-toggle" data-trait="${{t.key}}" onclick="toggleTraitFilter('${{t.key}}')">${{t.label}}</button>`
  ).join('');
}}

function toggleTraitFilter(key) {{
  if (activeTraitFilters.has(key)) activeTraitFilters.delete(key);
  else activeTraitFilters.add(key);
  document.querySelectorAll('.trait-toggle').forEach(btn => {{
    btn.classList.toggle('on', activeTraitFilters.has(btn.dataset.trait));
  }});
  applyFilters();
}}

/* ── Filter logic ── */
function applyFilters() {{
  let list = PLAYERS.slice();

  /* Search */
  if (searchQuery) {{
    const q = searchQuery.toLowerCase();
    list = list.filter(p => playerDisplayName(p).toLowerCase().includes(q));
  }}

  /* Favorites */
  if (favOnly) list = list.filter(p => favorites.has(p.player_id));

  /* Tier preset */
  if (tierFilter) list = list.filter(p => String(p.tier) === String(tierFilter));

  /* VTS */
  if (filterVTS > 0) list = list.filter(p => +(p.vts_final || 0) >= filterVTS);

  /* Win% */
  if (filterWin > 0) list = list.filter(p => +(p.win_prob || p.win_pct || 0) >= filterWin);

  /* Top10% */
  if (filterT10 > 0) list = list.filter(p => +(p.top10_prob || p.top10_pct || 0) >= filterT10);

  /* Cut% */
  if (filterCut > 0) list = list.filter(p => +(p.make_cut_prob || 0) >= filterCut);

  /* Trait filters */
  for (const key of activeTraitFilters) {{
    list = list.filter(p => +(getTraitScore(p, key) || 0) >= 60);
  }}

  /* Sort */
  list.sort((a, b) => {{
    let av = a[sortCol], bv = b[sortCol];
    if (av == null) av = sortDir === 1 ? Infinity : -Infinity;
    if (bv == null) bv = sortDir === 1 ? Infinity : -Infinity;
    if (sortCol === 'player_name') {{
      av = playerDisplayName(a);
      bv = playerDisplayName(b);
      return sortDir * av.localeCompare(bv);
    }}
    if (sortCol === 'form_class') return sortDir * String(av).localeCompare(String(bv));
    return sortDir * (+av - +bv);
  }});

  filteredPlayers = list;
  renderTable(list);
  updateFilterBadge();
  updatePills();
  document.getElementById('field-count-badge').textContent = list.length + ' shown';
  const empty = document.getElementById('empty-state');
  const container = document.querySelector('.table-container');
  if (list.length === 0) {{
    empty.style.display = 'block';
    container.style.display = 'none';
  }} else {{
    empty.style.display = 'none';
    container.style.display = '';
  }}
}}

/* ── Table render ── */
function renderTable(list) {{
  const tbody = document.getElementById('field-tbody');
  if (!tbody) return;

  tbody.innerHTML = list.map(p => {{
    const name = playerDisplayName(p);
    const tier = +p.tier || 5;
    const tc   = tierClass(tier);
    const wp   = +(p.win_prob || p.win_pct || 0);
    const barW = Math.min(100, wp * 5); // max bar at 20%
    const fc   = formDotClass(p.form_class);
    const flags = getPlayerFlags(p);
    const isFav = favorites.has(p.player_id);
    const badges = (p.badges || []).slice(0, 2);
    return `<tr>
      <td>${{p.rank || '–'}}</td>
      <td><span class="player-name-link" onclick="openModal('${{p.player_id}}')">${{name}}</span></td>
      <td><span class="tier-dot ${{tc}}">T${{tier}}</span></td>
      <td>${{fmtVTS(p.vts_final)}}</td>
      <td><div class="win-bar-wrap"><div class="win-bar" style="width:${{barW}}px"></div><span>${{fmtPct(wp)}}</span></div></td>
      <td>${{fmtPct(p.top5_prob || p.top5_pct)}}</td>
      <td>${{fmtPct(p.top10_prob || p.top10_pct)}}</td>
      <td>${{fmtPct(p.top20_prob || p.top20_pct)}}</td>
      <td>${{fmtPct(p.make_cut_prob)}}</td>
      <td>${{fmtSG(p.sg_app_12m)}}</td>
      <td>${{fmtSG(p.sg_ott_12m)}}</td>
      <td>${{fmtSG(p.sg_arg_12m)}}</td>
      <td>${{fmtSG(p.sg_putt_12m)}}</td>
      <td>${{fmtSG(p.brie_score)}}</td>
      <td>${{fmtSG(p.tvl_score)}}</td>
      <td>${{fmtSG(p.vfr_score)}}</td>
      <td>${{fmtSG(p.hew_score)}}</td>
      <td><span class="form-dot ${{fc}}"></span></td>
      <td>${{p.r1_teetime || p.tee_time || '–'}}</td>
      <td>${{badges.map(b => `<span class="badge-pill" style="background:${{(BADGE_SCHEMA[b]||{{}}).color||'#475569'}}">${{b}}</span>`).join(' ')}}</td>
      <td><button class="fav-star-btn ${{isFav?'active':''}}" onclick="toggleFav('${{p.player_id}}',this)" title="Favorite">★</button></td>
    </tr>`;
  }}).join('');
}}

/* ── Sort ── */
function sortBy(col) {{
  if (sortCol === col) sortDir = -sortDir;
  else {{ sortCol = col; sortDir = col === 'rank' ? 1 : -1; }}
  document.querySelectorAll('#field-table th').forEach(th => {{
    th.classList.remove('sort-asc','sort-desc');
    if (th.dataset.col === col) th.classList.add(sortDir === 1 ? 'sort-asc' : 'sort-desc');
  }});
  applyFilters();
}}

/* ── Favorites ── */
function toggleFav(id, btn) {{
  if (favorites.has(id)) {{ favorites.delete(id); btn.classList.remove('active'); }}
  else {{ favorites.add(id); btn.classList.add('active'); }}
  saveFavs();
  document.getElementById('fav-count').textContent = favorites.size;
  if (favOnly) applyFilters();
}}

/* ── Filter badge & pills ── */
function updateFilterBadge() {{
  const cnt = (filterVTS>0?1:0)+(filterWin>0?1:0)+(filterT10>0?1:0)+(filterCut>0?1:0)+activeTraitFilters.size+(favOnly?1:0)+(tierFilter?1:0);
  const badge = document.getElementById('filter-badge');
  badge.textContent = cnt;
  badge.style.display = cnt > 0 ? '' : 'none';
}}

function updatePills() {{
  const el = document.getElementById('active-pills');
  const pills = [];
  if (filterVTS>0)  pills.push({{label:`VTS ≥ ${{filterVTS}}`,clear:()=>{{filterVTS=0;document.getElementById('sl-vts').value=0;document.getElementById('lbl-vts').textContent=0;applyFilters();}}}});
  if (filterWin>0)  pills.push({{label:`Win% ≥ ${{filterWin}}%`,clear:()=>{{filterWin=0;document.getElementById('sl-win').value=0;document.getElementById('lbl-win').textContent=0;applyFilters();}}}});
  if (filterT10>0)  pills.push({{label:`Top10% ≥ ${{filterT10}}%`,clear:()=>{{filterT10=0;document.getElementById('sl-t10').value=0;document.getElementById('lbl-t10').textContent=0;applyFilters();}}}});
  if (filterCut>0)  pills.push({{label:`Cut% ≥ ${{filterCut}}%`,clear:()=>{{filterCut=0;document.getElementById('sl-cut').value=0;document.getElementById('lbl-cut').textContent=0;applyFilters();}}}});
  for (const k of activeTraitFilters) {{
    const td = TRAIT_DEFS.find(t=>t.key===k);
    pills.push({{label:`${{td?td.label:k}} ≥ 60`,clear:()=>{{activeTraitFilters.delete(k);document.querySelectorAll('.trait-toggle').forEach(b=>b.classList.toggle('on',activeTraitFilters.has(b.dataset.trait)));applyFilters();}}}});
  }}
  if (favOnly) pills.push({{label:'Favorites only',clear:()=>{{favOnly=false;document.getElementById('btn-favonly').classList.remove('active');applyFilters();}}}});
  if (tierFilter) pills.push({{label:`Tier ${{tierFilter}} only`,clear:()=>{{tierFilter=null;applyFilters();}}}});

  if (pills.length === 0) {{ el.style.display='none'; return; }}
  el.style.display='flex';
  el.innerHTML = pills.map((pill,i)=>
    `<span class="pill">${{pill.label}}<button onclick="pillClear(${{i}})">✕</button></span>`
  ).join('');
  window._pillClearFns = pills.map(p=>p.clear);
}}

function pillClear(i) {{ window._pillClearFns[i](); }}

/* ── Tier Board ── */
function renderTierBoard() {{
  const container = document.getElementById('tier-accordion');
  if (!container) return;

  const byTier = {{1:[],2:[],3:[],4:[],5:[]}};
  for (const p of PLAYERS) {{
    const t = Math.min(5, Math.max(1, +p.tier));
    byTier[t].push(p);
  }}

  container.innerHTML = [1,2,3,4,5].map(tier => {{
    const ps = byTier[tier];
    const avgVTS = ps.length ? (ps.reduce((s,p)=>s+ +(p.vts_final||0),0)/ps.length).toFixed(1) : '–';
    const avgWin = ps.length ? (ps.reduce((s,p)=>s+ +(p.win_prob||p.win_pct||0),0)/ps.length).toFixed(2) : '–';
    const tc = tierClass(tier);
    const label = TIER_LABELS[tier] || 'Tier '+tier;

    const cards = ps.map(p => {{
      const name  = playerDisplayName(p);
      const flags = getPlayerFlags(p);
      const fc    = formDotClass(p.form_class);
      const badges = (p.badges||[]).slice(0,2);
      return `<div class="player-card" onclick="openModal('${{p.player_id}}')">
        <div class="card-name">
          <span class="form-dot ${{fc}}"></span>
          ${{name}}
          <span class="card-tier-badge ${{tc}}">T${{tier}}</span>
          ${{p.debut_flag ? '<span class="debut-badge">DEBUT</span>' : ''}}
        </div>
        <div class="card-metrics">
          <div class="card-metric">VTS <span>${{fmtVTS(p.vts_final)}}</span></div>
          <div class="card-metric">Win <span>${{fmtPct(p.win_prob||p.win_pct)}}</span></div>
          <div class="card-metric">Top10 <span>${{fmtPct(p.top10_prob||p.top10_pct)}}</span></div>
          <div class="card-metric">SG:APP <span>${{fmtSG(p.sg_app_12m)}}</span></div>
        </div>
        <div class="card-badges">
          ${{badges.map(b=>`<span class="badge-pill" style="background:${{(BADGE_SCHEMA[b]||{{}}).color||'#475569'}}">${{b}}</span>`).join('')}}
        </div>
        <span class="card-view-btn">View details →</span>
      </div>`;
    }}).join('');

    return `<div class="tier-section" id="tier-section-${{tier}}">
      <div class="tier-section-header" onclick="toggleTier(${{tier}})">
        <span class="tier-badge-big ${{tc}}">T${{tier}}</span>
        <span class="tier-header-label">${{label}}</span>
        <div class="tier-header-meta">
          <span>${{ps.length}} players</span>
          <span>Avg VTS <b>${{avgVTS}}</b></span>
          <span>Avg Win <b>${{avgWin}}%</b></span>
        </div>
        <span class="tier-arrow">▶</span>
      </div>
      <div class="tier-cards">${{cards}}</div>
    </div>`;
  }}).join('');
}}

function toggleTier(tierNum) {{
  const el = document.getElementById('tier-section-'+tierNum);
  if (!el) return;
  const isOpen = el.classList.contains('open');
  el.classList.toggle('open', !isOpen);
  if (!isOpen) {{
    setTimeout(()=>el.scrollIntoView({{behavior:'smooth',block:'start'}}),50);
  }}
}}

/* ── Player Modal ── */
function openModal(playerId) {{
  const p = PLAYERS.find(x => x.player_id === playerId);
  if (!p) return;

  document.getElementById('modal-player-name').textContent = playerDisplayName(p);

  const tier = +p.tier || 5;
  const tc = tierClass(tier);
  const tierLabel = TIER_LABELS[tier] || 'Tier '+tier;
  const sub = document.getElementById('modal-player-sub');
  sub.innerHTML = `
    <span class="tier-dot ${{tc}}" style="font-size:.7rem">T${{tier}} — ${{tierLabel}}</span>
    <span>Rank #${{p.rank||'–'}}</span>
    ${{p.debut_flag ? '<span class="debut-badge">DEBUT</span>' : ''}}
    ${{p.tour_affiliation ? '<span>'+p.tour_affiliation+'</span>' : ''}}
  `;

  const flags = getPlayerFlags(p);
  const decomp = p.decomposition || {{}};
  const scoring = p.scoring || {{}};

  /* Build modal body */
  let html = '';

  /* Metrics grid */
  const nsi = p.neutral_skill_index || decomp.neutral_skill_index;
  const vhn = p.venue_history_normalized || decomp.venue_history_delta;
  html += `<div class="metrics-grid">
    <div class="metric-cell"><div class="metric-label">VTS Final</div><div class="metric-val">${{fmtVTS(p.vts_final)}}</div></div>
    <div class="metric-cell"><div class="metric-label">Win %</div><div class="metric-val">${{fmtPct(p.win_prob||p.win_pct)}}</div></div>
    <div class="metric-cell"><div class="metric-label">Top 5 %</div><div class="metric-val">${{fmtPct(p.top5_prob||p.top5_pct)}}</div></div>
    <div class="metric-cell"><div class="metric-label">Top 10 %</div><div class="metric-val">${{fmtPct(p.top10_prob||p.top10_pct)}}</div></div>
    <div class="metric-cell"><div class="metric-label">Top 20 %</div><div class="metric-val">${{fmtPct(p.top20_prob||p.top20_pct)}}</div></div>
    <div class="metric-cell"><div class="metric-label">Make Cut %</div><div class="metric-val">${{fmtPct(p.make_cut_prob)}}</div></div>
    <div class="metric-cell"><div class="metric-label">NSI</div><div class="metric-val">${{fmtVTS(nsi)}}</div></div>
    <div class="metric-cell"><div class="metric-label">VHN</div><div class="metric-val">${{fmtVTS(vhn)}}</div></div>
  </div>`;

  /* Betting path */
  const lane = p.best_betting_lane || 'Pass';
  const laneKey = lane.toLowerCase().replace(/[ ]+/g,'');
  const viabilityClass = laneKey.includes('winner') ? 'winner'
    : laneKey.includes('top5') ? 'top5'
    : laneKey.includes('top10') ? 'top10'
    : laneKey.includes('top20') ? 'top20'
    : laneKey.includes('cut') ? 'cut' : 'pass';
  html += `<div class="section-title">Betting Path</div>
  <div class="betting-path">
    <span class="lane-label">${{lane}}</span>
    <span class="viability-tag viability-${{viabilityClass}}">${{p.conviction_level || 'MODERATE'}}</span>
  </div>`;

  /* Trait Profile */
  html += `<div class="section-title">Trait Profile</div><div class="trait-bars">`;
  for (const td of TRAIT_DEFS) {{
    const score = getTraitScore(p, td.key);
    const s = score != null ? +score : 0;
    const colorClass = s >= 65 ? 'high' : s >= 35 ? 'mid' : 'low';
    html += `<div class="trait-bar-row">
      <span class="trait-bar-label">${{td.label}}</span>
      <div class="trait-bar-outer"><div class="trait-bar-inner ${{colorClass}}" style="width:${{s}}%"></div></div>
      <span class="trait-bar-val">${{s.toFixed(0)}}</span>
    </div>`;
  }}
  html += `</div>`;

  /* SG Splits */
  const sgFields = [
    ['sg_app_12m','SG:APP'],['sg_ott_12m','SG:OTT'],['sg_arg_12m','SG:ARG'],
    ['sg_putt_12m','SG:PUTT'],['sg_t2g_12m','SG:T2G'],
  ];
  const maxSG = 2.5;
  html += `<div class="section-title">Strokes Gained (L12 Months)</div><div class="sg-block">`;
  for (const [field, label] of sgFields) {{
    const v = p[field];
    if (v == null) continue;
    const n = +v;
    const pct = Math.min(100, Math.abs(n) / maxSG * 100);
    const isPos = n >= 0;
    html += `<div class="sg-row">
      <span class="sg-label">${{label}}</span>
      <div class="sg-bar-outer">
        ${{isPos ? `<div class="sg-bar-pos" style="width:${{pct/2}}%"></div>` : `<div class="sg-bar-neg" style="width:${{pct/2}}%"></div>`}}
      </div>
      <span class="sg-val ${{isPos?'pos':'neg'}}">${{fmtSG(n)}}</span>
    </div>`;
  }}
  html += `</div>`;

  /* Anti-patterns */
  if (flags.length > 0) {{
    const apNarratives = (AP_FLAGS.antiPatternNarratives) || {{}};
    html += `<div class="section-title">Anti-Patterns (${{flags.length}})</div><div class="flag-list">`;
    for (const flag of flags) {{
      const meta = AP_META[flag] || {{ label: flag, desc: '' }};
      const narrative = apNarratives[flag];
      const desc = (narrative && narrative.description) || meta.desc || '';
      html += `<div class="flag-row"><span class="flag-name">${{meta.label}}</span><div class="flag-desc">${{desc}}</div></div>`;
    }}
    html += `</div>`;
  }}

  /* Risk & Failure */
  if (p.risk_vector || p.failure_condition) {{
    html += `<div class="section-title">Risk Profile</div>`;
    if (p.risk_vector) html += `<div class="risk-block"><b>Risk vector:</b> ${{p.risk_vector}}</div>`;
    if (p.failure_condition) html += `<div class="risk-block"><b>Failure condition:</b> ${{p.failure_condition}}</div>`;
  }}

  /* Conviction */
  if (p.conviction_statement || (p.top_traits && p.top_traits.length)) {{
    html += `<div class="section-title">Council / Conviction</div>
    <div class="conviction-block">
      ${{p.conviction_statement ? `<div class="conviction-stmt">${{p.conviction_statement}}</div>` : ''}}
      ${{p.top_traits && p.top_traits.length ? `<ul class="conviction-traits">${{p.top_traits.map(t=>`<li>${{t}}</li>`).join('')}}</ul>` : ''}}
    </div>`;
  }}

  /* Scoring */
  if (scoring.expected != null || scoring.band) {{
    html += `<div class="section-title">Projected Scoring (vs Par 70)</div>
    <div class="scoring-block">
      <div class="scoring-cell"><div class="sc-label">Expected</div><div class="sc-val">${{scoring.expected != null ? (scoring.expected > 0 ? '+' : '') + scoring.expected : '–'}}</div></div>
      <div class="scoring-cell"><div class="sc-label">Ceiling</div><div class="sc-val">${{scoring.ceiling != null ? (scoring.ceiling > 0 ? '+' : '') + scoring.ceiling : '–'}}</div></div>
      <div class="scoring-cell"><div class="sc-label">Floor</div><div class="sc-val">${{scoring.floor != null ? (scoring.floor > 0 ? '+' : '') + scoring.floor : '–'}}</div></div>
    </div>
    ${{scoring.band ? `<div class="scoring-band">${{scoring.band}}</div>` : ''}}`;
  }}

  /* Tee Times */
  if (p.r1_teetime || p.r2_teetime) {{
    html += `<div class="section-title">Tee Times</div><div class="tee-row">
      ${{p.r1_teetime ? `<div class="tee-item"><div class="ti-label">R1</div><div class="ti-val">${{p.r1_teetime}} · Wave: ${{p.r1_wave||'–'}} · Hole ${{p.r1_starthole||'1'}}</div></div>` : ''}}
      ${{p.r2_teetime ? `<div class="tee-item"><div class="ti-label">R2</div><div class="ti-val">${{p.r2_teetime}} · Wave: ${{p.r2_wave||'–'}} · Hole ${{p.r2_starthole||'1'}}</div></div>` : ''}}
    </div>`;
  }}

  document.getElementById('player-modal-body').innerHTML = html;
  document.getElementById('player-modal-overlay').classList.add('open');
}}

function closeModal() {{
  document.getElementById('player-modal-overlay').classList.remove('open');
}}

/* ── Anti-Pattern Panel ── */
function renderAPPanel() {{
  const el = document.getElementById('ap-grid');
  if (!el) return;

  /* Aggregate flags from player data */
  const flagMap = {{}};
  for (const p of PLAYERS) {{
    const flags = getPlayerFlags(p);
    for (const flag of flags) {{
      if (!flagMap[flag]) flagMap[flag] = [];
      flagMap[flag].push(p);
    }}
  }}

  const narratives = (AP_FLAGS && AP_FLAGS.antiPatternNarratives) || {{}};

  const entries = Object.entries(flagMap).sort((a,b) => b[1].length - a[1].length);
  if (entries.length === 0) {{
    el.innerHTML = '<p style="color:var(--muted);font-size:.8rem">No anti-pattern flags found in field.</p>';
    return;
  }}

  el.innerHTML = entries.map(([flag, ps]) => {{
    const meta = AP_META[flag] || {{ label: flag, desc: '' }};
    const desc = (narratives[flag] && narratives[flag].description) || meta.desc || '';
    const chips = ps.slice(0, 20).map(p =>
      `<span class="ap-player-chip" onclick="openModal('${{p.player_id}}')">${{playerDisplayName(p)}}</span>`
    ).join('');
    return `<div class="ap-card">
      <div class="ap-card-header">
        <span class="ap-flag-label">${{meta.label}}</span>
        <span class="ap-count-badge">${{ps.length}}</span>
      </div>
      <div class="ap-desc">${{desc}}</div>
      <div class="ap-players">${{chips}}</div>
    </div>`;
  }}).join('');
}}

/* ── Value Panel ── */
function renderValuePanel() {{
  const el = document.getElementById('value-grid');
  if (!el) return;

  const modelOver = (VALUE_SECTION && VALUE_SECTION.modelOver) || [];
  const structFades = (VALUE_SECTION && VALUE_SECTION.structuralFades) || [];

  /* Filter structural fades: only T4/T5 OR players with 2+ anti-pattern flags */
  const validFades = structFades.filter(f => {{
    const p = PLAYERS.find(x => x.last_name && playerDisplayName(x).includes(f.playerName.split(' ').pop()));
    const tier = +f.tier;
    if (tier >= 4) return true;
    /* Check anti-pattern flag count */
    const found = PLAYERS.find(x => playerDisplayName(x) === f.playerName ||
      (x.last_name && f.playerName.includes(x.last_name)));
    if (found) return getPlayerFlags(found).length >= 2;
    return tier >= 4;
  }});

  function makeValueItem(item) {{
    const p = PLAYERS.find(x => {{
      const n = playerDisplayName(x);
      return n === item.playerName || n.includes(item.playerName.split(' ').pop());
    }});
    const pid = p ? p.player_id : null;
    return `<div class="value-item">
      <div>
        <span class="value-name" ${{pid?`onclick="openModal('${{pid}}')"`:''}}>${{item.playerName}}</span>
        <div class="value-vts">VTS ${{fmtVTS(item.vts)}} · T${{item.tier}}</div>
      </div>
      <div class="value-reason">${{item.reason}}</div>
    </div>`;
  }}

  el.innerHTML = `
    <div class="value-card">
      <h3>Model Over (Value Plays)</h3>
      ${{modelOver.map(makeValueItem).join('') || '<div style="color:var(--muted);font-size:.75rem">None identified.</div>'}}
    </div>
    <div class="value-card">
      <h3>Structural Fades</h3>
      ${{validFades.slice(0,8).map(makeValueItem).join('') || '<div style="color:var(--muted);font-size:.75rem">None identified.</div>'}}
    </div>`;
}}

/* ── Glossary ── */
function openGlossary() {{
  document.getElementById('glossary-modal-overlay').classList.add('open');
}}

function closeGlossary() {{
  document.getElementById('glossary-modal-overlay').classList.remove('open');
}}

/* ── Preset views ── */
const VIEW_PRESETS = {{
  'top-equity':        {{ sort: 'win_prob', dir: -1 }},
  'iron-elites':       {{ trait: 'app_150_200', sort: 'vts_final', dir: -1 }},
  'long-iron-fits':    {{ traits: ['app_150_200','app_overall'], sort: 'vts_final', dir: -1 }},
  'positional-drivers':{{ trait: 'ott_positional', sort: 'vts_final', dir: -1 }},
  'safe-cut-makers':   {{ sort: 'make_cut_prob', dir: -1 }},
  'longshot-dogs':     {{ tierF: '3', sort: 'win_prob', dir: -1 }},
  'clean-flags':       {{ noFlags: true, sort: 'vts_final', dir: -1 }},
  'favorites':         {{ favs: true }},
}};

function applyPreset(key) {{
  /* Reset first */
  resetAll(true);
  activePreset = key;
  const preset = VIEW_PRESETS[key];
  if (!preset) return;
  if (preset.sort) {{
    sortCol = preset.sort;
    sortDir = preset.dir || -1;
  }}
  if (preset.trait) activeTraitFilters.add(preset.trait);
  if (preset.traits) preset.traits.forEach(t => activeTraitFilters.add(t));
  if (preset.tierF) tierFilter = preset.tierF;
  if (preset.favs) {{ favOnly = true; document.getElementById('btn-favonly').classList.add('active'); }}
  if (preset.noFlags) {{
    /* will filter in applyFilters via noFlags flag */
    window._noFlagsActive = true;
  }}
  document.querySelectorAll('.trait-toggle').forEach(b =>
    b.classList.toggle('on', activeTraitFilters.has(b.dataset.trait))
  );
  document.querySelectorAll('#field-table th').forEach(th => {{
    th.classList.remove('sort-asc','sort-desc');
    if (th.dataset.col === sortCol) th.classList.add(sortDir === 1 ? 'sort-asc' : 'sort-desc');
  }});
  applyFilters();
}}

function resetAll(silent) {{
  searchQuery = '';
  filterVTS = 0; filterWin = 0; filterT10 = 0; filterCut = 0;
  activeTraitFilters.clear();
  favOnly = false;
  tierFilter = null;
  activePreset = null;
  window._noFlagsActive = false;
  sortCol = 'rank'; sortDir = 1;
  document.getElementById('search-input').value = '';
  document.getElementById('sl-vts').value = 0; document.getElementById('lbl-vts').textContent = '0';
  document.getElementById('sl-win').value = 0; document.getElementById('lbl-win').textContent = '0';
  document.getElementById('sl-t10').value = 0; document.getElementById('lbl-t10').textContent = '0';
  document.getElementById('sl-cut').value = 0; document.getElementById('lbl-cut').textContent = '0';
  document.querySelectorAll('.trait-toggle').forEach(b => b.classList.remove('on'));
  document.getElementById('btn-favonly').classList.remove('active');
  document.getElementById('search-clear').style.display = 'none';
  document.querySelectorAll('#field-table th').forEach(th => {{
    th.classList.remove('sort-asc','sort-desc');
    if (th.dataset.col === 'rank') th.classList.add('sort-asc');
  }});
  if (!silent) applyFilters();
}}

/* Override applyFilters to handle noFlags preset */
const _origApply = applyFilters;
// Patch: add noFlags filter
(function() {{
  const orig = applyFilters;
  applyFilters = function() {{
    let list = PLAYERS.slice();
    if (searchQuery) {{
      const q = searchQuery.toLowerCase();
      list = list.filter(p => playerDisplayName(p).toLowerCase().includes(q));
    }}
    if (favOnly) list = list.filter(p => favorites.has(p.player_id));
    if (tierFilter) list = list.filter(p => String(p.tier) === String(tierFilter));
    if (filterVTS > 0) list = list.filter(p => +(p.vts_final||0) >= filterVTS);
    if (filterWin > 0) list = list.filter(p => +(p.win_prob||p.win_pct||0) >= filterWin);
    if (filterT10 > 0) list = list.filter(p => +(p.top10_prob||p.top10_pct||0) >= filterT10);
    if (filterCut > 0) list = list.filter(p => +(p.make_cut_prob||0) >= filterCut);
    for (const key of activeTraitFilters) {{
      list = list.filter(p => +(getTraitScore(p, key)||0) >= 60);
    }}
    if (window._noFlagsActive) {{
      list = list.filter(p => getPlayerFlags(p).length === 0);
    }}
    list.sort((a, b) => {{
      let av = a[sortCol], bv = b[sortCol];
      if (av == null) av = sortDir === 1 ? Infinity : -Infinity;
      if (bv == null) bv = sortDir === 1 ? Infinity : -Infinity;
      if (sortCol === 'player_name') {{ av = playerDisplayName(a); bv = playerDisplayName(b); return sortDir * av.localeCompare(bv); }}
      if (sortCol === 'form_class') return sortDir * String(av).localeCompare(String(bv));
      return sortDir * (+av - +bv);
    }});
    filteredPlayers = list;
    renderTable(list);
    updateFilterBadge();
    updatePills();
    document.getElementById('field-count-badge').textContent = list.length + ' shown';
    const empty = document.getElementById('empty-state');
    const container = document.querySelector('.table-container');
    if (list.length === 0) {{ empty.style.display='block'; container.style.display='none'; }}
    else {{ empty.style.display='none'; container.style.display=''; }}
  }};
}})();

/* ── Wire up events ── */
function wireEvents() {{
  /* Search */
  const si = document.getElementById('search-input');
  const sc = document.getElementById('search-clear');
  si.addEventListener('input', () => {{
    searchQuery = si.value.trim();
    sc.style.display = searchQuery ? '' : 'none';
    applyFilters();
  }});
  sc.addEventListener('click', () => {{
    si.value = ''; searchQuery = '';
    sc.style.display = 'none';
    applyFilters();
  }});

  /* Filter drawer toggle */
  document.getElementById('btn-filter').addEventListener('click', () => {{
    const d = document.getElementById('filter-drawer');
    d.style.display = d.style.display === 'none' ? 'block' : 'none';
  }});
  document.getElementById('fp-close').addEventListener('click', () => {{
    document.getElementById('filter-drawer').style.display = 'none';
  }});

  /* Range sliders */
  const slVTS = document.getElementById('sl-vts');
  slVTS.addEventListener('input', () => {{
    filterVTS = +slVTS.value;
    document.getElementById('lbl-vts').textContent = filterVTS;
    applyFilters();
  }});
  const slWin = document.getElementById('sl-win');
  slWin.addEventListener('input', () => {{
    filterWin = +slWin.value;
    document.getElementById('lbl-win').textContent = filterWin;
    applyFilters();
  }});
  const slT10 = document.getElementById('sl-t10');
  slT10.addEventListener('input', () => {{
    filterT10 = +slT10.value;
    document.getElementById('lbl-t10').textContent = filterT10;
    applyFilters();
  }});
  const slCut = document.getElementById('sl-cut');
  slCut.addEventListener('input', () => {{
    filterCut = +slCut.value;
    document.getElementById('lbl-cut').textContent = filterCut;
    applyFilters();
  }});

  /* Favorites */
  document.getElementById('btn-favonly').addEventListener('click', () => {{
    favOnly = !favOnly;
    document.getElementById('btn-favonly').classList.toggle('active', favOnly);
    applyFilters();
  }});

  /* Presets dropdown */
  const btnPre = document.getElementById('btn-presets');
  const preDD  = document.getElementById('preset-dropdown');
  btnPre.addEventListener('click', (e) => {{
    e.stopPropagation();
    preDD.style.display = preDD.style.display === 'none' ? 'block' : 'none';
  }});
  document.querySelectorAll('.preset-item').forEach(btn => {{
    btn.addEventListener('click', () => {{
      applyPreset(btn.dataset.preset);
      preDD.style.display = 'none';
    }});
  }});

  /* Glossary */
  document.getElementById('btn-glossary').addEventListener('click', openGlossary);
  document.getElementById('btn-glossary2').addEventListener('click', openGlossary);
  document.getElementById('glossary-modal-close').addEventListener('click', closeGlossary);
  document.getElementById('glossary-modal-overlay').addEventListener('click', (e) => {{
    if (e.target === document.getElementById('glossary-modal-overlay')) closeGlossary();
  }});

  /* Reset */
  document.getElementById('btn-reset').addEventListener('click', () => resetAll(false));
  document.getElementById('empty-reset').addEventListener('click', () => resetAll(false));

  /* Modal close */
  document.getElementById('player-modal-close').addEventListener('click', closeModal);
  document.getElementById('player-modal-overlay').addEventListener('click', (e) => {{
    if (e.target === document.getElementById('player-modal-overlay')) closeModal();
  }});

  /* Escape key */
  document.addEventListener('keydown', (e) => {{
    if (e.key === 'Escape') {{ closeModal(); closeGlossary(); }}
  }});

  /* Table sort */
  document.querySelectorAll('#field-table th[data-col]').forEach(th => {{
    th.addEventListener('click', () => sortBy(th.dataset.col));
  }});

  /* Click outside presets */
  document.addEventListener('click', () => {{ preDD.style.display = 'none'; }});

  /* Include imputed toggle */
  document.getElementById('fp-include-imputed').addEventListener('change', (e) => {{
    includeImputed = e.target.checked;
    applyFilters();
  }});
}}

/* ── Main init ── */
window._noFlagsActive = false;

document.addEventListener('DOMContentLoaded', () => {{
  initStats();
  renderWeather();
  renderTraitToggles();
  renderTierBoard();
  renderAPPanel();
  renderValuePanel();
  wireEvents();

  /* Default sort indicator */
  const rankTh = document.querySelector('#field-table th[data-col="rank"]');
  if (rankTh) rankTh.classList.add('sort-asc');

  /* Initial render */
  applyFilters();

  /* Update fav count */
  document.getElementById('fav-count').textContent = favorites.size;
}});
</script>
</body>
</html>"""

# ── Write output ───────────────────────────────────────────────────────────────
OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
print(f"[build_board_v2] Writing output to {OUT_FILE}")
with open(OUT_FILE, 'w', encoding='utf-8') as f:
    f.write(html)

size_kb = OUT_FILE.stat().st_size / 1024
print(f"[build_board_v2] Done. File size: {size_kb:.1f} KB ({OUT_FILE.stat().st_size:,} bytes)")

# ── Verification summary ────────────────────────────────────────────────────────
print("\n=== VERIFICATION ===")
print(f"Output: {OUT_FILE}")
print(f"Size: {size_kb:.1f} KB")
print(f"Players embedded: {len(players)}")
print(f"Tier counts: {tier_counts}")
print("\nTop 5 players by rank:")
top5 = sorted(players, key=lambda p: p.get('rank', 999))[:5]
for p in top5:
    name = f"{p.get('first_name','')} {p.get('last_name','')}".strip()
    print(f"  #{p['rank']:>2}  {name:<25}  VTS={p['vts_final']:.2f}  T{p['tier']}")
