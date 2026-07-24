"""
Build 2026 The Open Championship HTML board.
Reads final_analysis.json, embeds all data as JS constants,
outputs single-file 2026_the_open_championship_board.html.
"""

import json
import csv
import pathlib
import re
from datetime import datetime

BASE = pathlib.Path(__file__).parent.parent
DATA_DIR = BASE / "deploy" / "data"
OUTPUT = BASE / "deploy" / "2026_the_open_championship_board.html"

with open(DATA_DIR / "final_analysis.json", encoding="utf-8") as f:
    data = json.load(f)

# ── helpers ──────────────────────────────────────────────────────────────────

def jdump(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))

# ── collect allPlayers for field table ───────────────────────────────────────
all_players = data.get("allPlayers", [])
tier_lists  = data.get("tierLists", {})
venue       = data.get("venueSummary", {})
prob_view   = data.get("probabilityView", [])
value_sect  = data.get("valueSection", {})
council_log = data.get("councilLog", [])
anti_patt   = data.get("antiPatternFlags", {})
risk_reg    = data.get("riskRegister", {})

# ── embed data as JS ─────────────────────────────────────────────────────────
js_data = f"""
const EVENT = {jdump({"event": data["event"], "venue": data["venue"],
                       "generatedAt": data["generatedAt"],
                       "engineVersion": data["engineVersion"]})};
const VENUE = {jdump(venue)};
const TIER_LISTS = {jdump(tier_lists)};
const ALL_PLAYERS = {jdump(all_players)};
const PROB_VIEW = {jdump(prob_view)};
const VALUE_SECTION = {jdump(value_sect)};
const COUNCIL_LOG = {jdump(council_log)};
const ANTI_PATTERN = {jdump(anti_patt)};
const RISK_REGISTER = {jdump(risk_reg)};
"""

# ── HTML ─────────────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VenueDNA — The Open Championship 2026 · Royal Birkdale</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
/* ── CSS custom properties ─────────────────────────────────────────────── */
:root {{
  --color-bg:         #0f1419;
  --color-surface:    #161d27;
  --color-surface2:   #1e2936;
  --color-border:     #2a3a4a;
  --color-border2:    #354a5e;
  --color-text:       #e8e0d4;
  --color-muted:      #7a8fa6;
  --color-gold:       #c9a84c;
  --color-gold-dim:   #8a6e30;
  --color-green:      #1a3a2a;
  --color-green-light:#2d6147;
  --color-cream:      #f5f0e8;
  --color-t1:         #22c55e;
  --color-t2:         #60a5fa;
  --color-t3:         #a78bfa;
  --color-t4:         #fb923c;
  --color-t5:         #f87171;
  --color-hot:        #22c55e;
  --color-warm:       #86efac;
  --color-neutral:    #94a3b8;
  --color-cool:       #fbbf24;
  --color-cold:       #f87171;
  --font-display:     'Playfair Display', Georgia, serif;
  --font-body:        'Inter', system-ui, sans-serif;
  --radius:           6px;
  --radius-lg:        10px;
  --shadow:           0 2px 12px rgba(0,0,0,0.4);
}}

* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ scroll-behavior: smooth; }}
body {{
  font-family: var(--font-body);
  background: var(--color-bg);
  color: var(--color-text);
  line-height: 1.55;
  font-size: 14px;
}}

/* ── Layout ─────────────────────────────────────────────────────────────── */
.container {{ max-width: 1440px; margin: 0 auto; padding: 0 1.5rem; }}

/* ── Header / Hero ──────────────────────────────────────────────────────── */
.hero {{
  background: linear-gradient(160deg, #0a1a10 0%, #0f1419 40%, #0c1520 100%);
  border-bottom: 2px solid var(--color-gold-dim);
  padding: 2rem 0 1.5rem;
  position: relative;
  overflow: hidden;
}}
.hero::before {{
  content: '';
  position: absolute;
  inset: 0;
  background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23c9a84c' fill-opacity='0.03'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
  opacity: 0.6;
}}
.hero-inner {{
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 1rem;
}}
.hero-title {{
  font-family: var(--font-display);
  font-size: 2.2rem;
  font-weight: 700;
  color: var(--color-gold);
  line-height: 1.1;
  letter-spacing: -0.01em;
}}
.hero-subtitle {{
  font-size: .9rem;
  color: var(--color-muted);
  margin-top: .3rem;
  font-weight: 400;
}}
.hero-subtitle span {{ color: var(--color-text); }}
.hero-badge {{
  display: inline-block;
  background: rgba(201,168,76,0.12);
  border: 1px solid var(--color-gold-dim);
  color: var(--color-gold);
  font-size: .7rem;
  font-weight: 600;
  letter-spacing: .08em;
  text-transform: uppercase;
  padding: .2rem .7rem;
  border-radius: 20px;
  margin-top: .5rem;
}}
.hero-stats {{
  display: flex;
  gap: 1.5rem;
  flex-wrap: wrap;
  align-items: center;
}}
.hero-stat {{
  text-align: center;
}}
.hero-stat-val {{
  font-family: var(--font-display);
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--color-gold);
  line-height: 1;
}}
.hero-stat-label {{
  font-size: .65rem;
  color: var(--color-muted);
  text-transform: uppercase;
  letter-spacing: .06em;
  margin-top: .15rem;
}}

/* ── Nav bar ─────────────────────────────────────────────────────────────── */
.nav-bar {{
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  position: sticky;
  top: 0;
  z-index: 100;
  padding: .5rem 0;
}}
.nav-inner {{
  display: flex;
  gap: 0;
  overflow-x: auto;
  scrollbar-width: none;
}}
.nav-inner::-webkit-scrollbar {{ display: none; }}
.nav-link {{
  font-size: .73rem;
  font-weight: 500;
  color: var(--color-muted);
  text-decoration: none;
  padding: .4rem 1rem;
  border-bottom: 2px solid transparent;
  white-space: nowrap;
  transition: color .15s, border-color .15s;
}}
.nav-link:hover {{ color: var(--color-text); }}
.nav-link.active {{ color: var(--color-gold); border-bottom-color: var(--color-gold); }}

/* ── Section ─────────────────────────────────────────────────────────────── */
.section {{
  padding: 2rem 0;
  border-bottom: 1px solid var(--color-border);
}}
.section-header {{
  display: flex;
  align-items: center;
  gap: .75rem;
  margin-bottom: 1.25rem;
}}
.section-title {{
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-gold);
}}
.section-badge {{
  font-size: .65rem;
  font-weight: 700;
  letter-spacing: .07em;
  text-transform: uppercase;
  color: var(--color-muted);
  background: var(--color-surface2);
  border: 1px solid var(--color-border);
  padding: .15rem .5rem;
  border-radius: 4px;
}}

/* ── Tier badge ──────────────────────────────────────────────────────────── */
.tb {{
  display: inline-flex;
  align-items: center;
  font-size: .63rem;
  font-weight: 700;
  letter-spacing: .06em;
  padding: .18rem .5rem;
  border-radius: 4px;
  text-transform: uppercase;
  white-space: nowrap;
}}
.tb-T1 {{ background: rgba(34,197,94,0.15);  color: #4ade80; border: 1px solid rgba(34,197,94,0.3); }}
.tb-T2 {{ background: rgba(96,165,250,0.15); color: #93c5fd; border: 1px solid rgba(96,165,250,0.3); }}
.tb-T3 {{ background: rgba(167,139,250,0.15);color: #c4b5fd; border: 1px solid rgba(167,139,250,0.3); }}
.tb-T4 {{ background: rgba(251,146,60,0.15); color: #fdba74; border: 1px solid rgba(251,146,60,0.3); }}
.tb-T5 {{ background: rgba(248,113,113,0.15);color: #fca5a5; border: 1px solid rgba(248,113,113,0.3); }}

/* ── Venue DNA grid ──────────────────────────────────────────────────────── */
.venue-grid {{
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 1.5rem;
  align-items: start;
}}
@media (max-width: 900px) {{ .venue-grid {{ grid-template-columns: 1fr; }} }}
.radar-wrap {{
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1rem;
}}
.radar-title {{
  font-size: .7rem;
  text-transform: uppercase;
  letter-spacing: .07em;
  color: var(--color-muted);
  text-align: center;
  margin-bottom: .75rem;
}}
.venue-facts {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: .75rem;
}}
.fact-card {{
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: .8rem 1rem;
}}
.fact-label {{
  font-size: .65rem;
  text-transform: uppercase;
  letter-spacing: .07em;
  color: var(--color-muted);
  margin-bottom: .25rem;
}}
.fact-value {{
  font-size: .9rem;
  font-weight: 600;
  color: var(--color-text);
}}
.fact-sub {{ font-size: .75rem; color: var(--color-muted); margin-top: .15rem; }}
.mechanism-list {{
  list-style: none;
  margin-top: .75rem;
  display: flex;
  flex-direction: column;
  gap: .4rem;
}}
.mechanism-list li {{
  font-size: .78rem;
  color: var(--color-muted);
  padding-left: 1rem;
  position: relative;
}}
.mechanism-list li::before {{
  content: '›';
  position: absolute;
  left: 0;
  color: var(--color-gold);
}}

/* ── Tier board ──────────────────────────────────────────────────────────── */
.tier-section {{
  margin-bottom: 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}}
.tier-header {{
  display: flex;
  align-items: center;
  gap: .75rem;
  padding: .75rem 1rem;
  cursor: pointer;
  background: var(--color-surface);
  user-select: none;
  transition: background .15s;
}}
.tier-header:hover {{ background: var(--color-surface2); }}
.tier-name {{
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 600;
}}
.tier-count {{
  font-size: .7rem;
  color: var(--color-muted);
  margin-left: auto;
}}
.tier-chevron {{
  font-size: .8rem;
  color: var(--color-muted);
  transition: transform .2s;
}}
.tier-body {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: .75rem;
  padding: .75rem;
  background: var(--color-bg);
}}
.tier-body.collapsed {{ display: none; }}

/* ── Player card ─────────────────────────────────────────────────────────── */
.player-card {{
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: .8rem 1rem;
  cursor: pointer;
  transition: border-color .15s, background .15s;
  position: relative;
}}
.player-card:hover {{
  border-color: var(--color-gold-dim);
  background: var(--color-surface2);
}}
.player-card-top {{
  display: flex;
  align-items: center;
  gap: .5rem;
  margin-bottom: .5rem;
}}
.player-rank {{
  font-size: .65rem;
  font-weight: 700;
  color: var(--color-muted);
  min-width: 1.4rem;
}}
.player-name {{
  font-weight: 600;
  font-size: .88rem;
  flex: 1;
  color: var(--color-text);
}}
.player-country {{
  font-size: .65rem;
  color: var(--color-muted);
  background: var(--color-surface2);
  padding: .1rem .35rem;
  border-radius: 3px;
}}
.player-vts {{
  font-family: var(--font-display);
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-gold);
  margin-right: .25rem;
}}
.player-stats {{
  display: flex;
  gap: .75rem;
  margin-top: .35rem;
}}
.pstat {{
  font-size: .7rem;
  color: var(--color-muted);
}}
.pstat span {{ color: var(--color-text); font-weight: 500; }}
.player-trait-row {{
  display: flex;
  flex-wrap: wrap;
  gap: .3rem;
  margin-top: .45rem;
}}
.trait-chip {{
  font-size: .6rem;
  font-weight: 600;
  padding: .1rem .4rem;
  border-radius: 3px;
  text-transform: uppercase;
  letter-spacing: .04em;
}}
.trait-up   {{ background: rgba(34,197,94,0.12);  color: #86efac; }}
.trait-down {{ background: rgba(248,113,113,0.12); color: #fca5a5; }}
.form-dot {{
  display: inline-block;
  width: 7px; height: 7px;
  border-radius: 50%;
  margin-right: .25rem;
  vertical-align: middle;
}}
.form-hot     {{ background: var(--color-hot); }}
.form-warm    {{ background: var(--color-warm); }}
.form-neutral {{ background: var(--color-neutral); }}
.form-cool    {{ background: var(--color-cool); }}
.form-cold    {{ background: var(--color-cold); }}
.debut-flag {{
  position: absolute;
  top: .4rem;
  right: .4rem;
  font-size: .55rem;
  font-weight: 700;
  color: #fbbf24;
  background: rgba(251,191,36,0.12);
  border: 1px solid rgba(251,191,36,0.3);
  padding: .05rem .3rem;
  border-radius: 3px;
  letter-spacing: .05em;
}}

/* ── Probability / Leaderboard ───────────────────────────────────────────── */
.prob-chart-wrap {{
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1rem 1.25rem;
  margin-bottom: 1.25rem;
}}
.prob-chart-title {{
  font-size: .7rem;
  text-transform: uppercase;
  letter-spacing: .07em;
  color: var(--color-muted);
  margin-bottom: .75rem;
}}

/* ── Field explorer ──────────────────────────────────────────────────────── */
.filter-row {{
  display: flex;
  gap: .5rem;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 1rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: .6rem .75rem;
}}
.filter-row label {{
  font-size: .7rem;
  color: var(--color-muted);
  white-space: nowrap;
}}
.filter-row input,
.filter-row select {{
  background: var(--color-surface2);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  color: var(--color-text);
  font-size: .75rem;
  padding: .3rem .55rem;
}}
.filter-row input:focus,
.filter-row select:focus {{
  outline: none;
  border-color: var(--color-gold-dim);
}}
.table-wrap {{
  overflow-x: auto;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
}}
table.field-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: .76rem;
}}
table.field-table thead th {{
  background: var(--color-surface2);
  color: var(--color-muted);
  font-size: .65rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: .06em;
  padding: .55rem .75rem;
  text-align: left;
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
  cursor: pointer;
  user-select: none;
}}
table.field-table thead th:hover {{ color: var(--color-gold); }}
table.field-table thead th.sorted-asc::after  {{ content: ' ▲'; }}
table.field-table thead th.sorted-desc::after {{ content: ' ▼'; }}
table.field-table tbody tr {{
  border-bottom: 1px solid var(--color-border);
  transition: background .1s;
  cursor: pointer;
}}
table.field-table tbody tr:hover {{ background: var(--color-surface); }}
table.field-table tbody td {{
  padding: .45rem .75rem;
  white-space: nowrap;
}}
td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
td.pos {{ font-weight: 700; color: var(--color-muted); text-align: center; }}
.win-bar {{
  display: inline-flex;
  align-items: center;
  gap: .4rem;
}}
.win-bar-track {{
  width: 60px;
  height: 5px;
  background: var(--color-border);
  border-radius: 3px;
  overflow: hidden;
}}
.win-bar-fill {{
  height: 100%;
  background: var(--color-gold);
  border-radius: 3px;
}}
.sg-pos {{ color: #4ade80; }}
.sg-neg {{ color: #f87171; }}

/* ── Panel grid ──────────────────────────────────────────────────────────── */
.two-col {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}}
@media (max-width: 768px) {{ .two-col {{ grid-template-columns: 1fr; }} }}
.panel {{
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1rem 1.25rem;
}}
.panel-title {{
  font-size: .7rem;
  text-transform: uppercase;
  letter-spacing: .07em;
  color: var(--color-muted);
  margin-bottom: .75rem;
  font-weight: 600;
}}
.panel-row {{
  display: flex;
  align-items: flex-start;
  gap: .5rem;
  padding: .4rem 0;
  border-bottom: 1px solid var(--color-border);
  font-size: .78rem;
}}
.panel-row:last-child {{ border-bottom: none; }}
.panel-row-name {{ font-weight: 600; min-width: 130px; }}
.panel-row-detail {{ color: var(--color-muted); font-size: .73rem; flex: 1; }}

/* ── Council log ─────────────────────────────────────────────────────────── */
.council-entry {{
  background: var(--color-surface);
  border-left: 3px solid var(--color-border2);
  border-radius: 0 var(--radius) var(--radius) 0;
  padding: .7rem 1rem;
  margin-bottom: .5rem;
  font-size: .78rem;
}}
.council-entry.confirm {{ border-left-color: #22c55e; }}
.council-entry.flag    {{ border-left-color: #f59e0b; }}
.council-entry.override {{ border-left-color: #f87171; }}
.council-role {{
  font-size: .65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .07em;
  margin-bottom: .25rem;
}}
.council-role.DevilsAdvocate {{ color: #60a5fa; }}
.council-role.Contrarian     {{ color: #f59e0b; }}
.council-role.CalibrationAuditor {{ color: #a78bfa; }}
.council-action {{ font-weight: 700; margin-right: .35rem; }}
.action-Confirm   {{ color: #22c55e; }}
.action-Flag      {{ color: #f59e0b; }}
.action-Override  {{ color: #f87171; }}
.council-player   {{ color: var(--color-gold); font-weight: 600; }}
.council-finding  {{ color: var(--color-muted); margin-top: .25rem; line-height: 1.4; }}

/* ── Anti-pattern panel ──────────────────────────────────────────────────── */
.gate-chip {{
  display: inline-block;
  font-size: .65rem;
  font-weight: 700;
  padding: .2rem .5rem;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: .04em;
}}
.gate-hard {{ background: rgba(248,113,113,0.2); color: #fca5a5; border: 1px solid rgba(248,113,113,0.4); }}
.gate-soft {{ background: rgba(251,191,36,0.15); color: #fde68a; border: 1px solid rgba(251,191,36,0.3); }}

/* ── Modal ────────────────────────────────────────────────────────────────── */
.modal-backdrop {{
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.75);
  z-index: 200;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}}
.modal-backdrop.open {{ display: flex; }}
.modal {{
  background: var(--color-surface);
  border: 1px solid var(--color-border2);
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 640px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: var(--shadow);
  animation: modal-in .15s ease;
}}
@keyframes modal-in {{
  from {{ opacity: 0; transform: translateY(12px); }}
  to   {{ opacity: 1; transform: translateY(0); }}
}}
.modal-header {{
  padding: 1rem 1.25rem .75rem;
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: flex-start;
  gap: .75rem;
}}
.modal-player-name {{
  font-family: var(--font-display);
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--color-gold);
  flex: 1;
}}
.modal-close {{
  background: none;
  border: none;
  color: var(--color-muted);
  font-size: 1.2rem;
  cursor: pointer;
  padding: .1rem .3rem;
  line-height: 1;
}}
.modal-close:hover {{ color: var(--color-text); }}
.modal-body {{ padding: 1rem 1.25rem; }}
.modal-grid {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: .6rem;
  margin-bottom: 1rem;
}}
.modal-stat {{
  background: var(--color-surface2);
  border-radius: var(--radius);
  padding: .5rem .75rem;
}}
.modal-stat-label {{
  font-size: .63rem;
  text-transform: uppercase;
  letter-spacing: .06em;
  color: var(--color-muted);
  margin-bottom: .2rem;
}}
.modal-stat-val {{
  font-size: .95rem;
  font-weight: 600;
  color: var(--color-text);
}}
.modal-section-title {{
  font-size: .65rem;
  text-transform: uppercase;
  letter-spacing: .07em;
  color: var(--color-muted);
  font-weight: 600;
  margin: .75rem 0 .35rem;
  border-top: 1px solid var(--color-border);
  padding-top: .6rem;
}}
.modal-text {{
  font-size: .8rem;
  color: var(--color-muted);
  line-height: 1.5;
}}
.modal-text strong {{ color: var(--color-text); font-weight: 600; }}
.sg-row {{
  display: grid;
  grid-template-columns: 70px 1fr auto;
  align-items: center;
  gap: .5rem;
  margin-bottom: .35rem;
}}
.sg-label {{ font-size: .7rem; color: var(--color-muted); }}
.sg-bar-track {{
  height: 5px;
  background: var(--color-border);
  border-radius: 3px;
  overflow: visible;
  position: relative;
}}
.sg-bar-fill {{
  height: 100%;
  border-radius: 3px;
  transition: width .3s;
}}
.sg-bar-pos {{ background: #22c55e; }}
.sg-bar-neg {{ background: #f87171; }}
.sg-val {{ font-size: .72rem; font-variant-numeric: tabular-nums; min-width: 40px; text-align: right; }}

/* ── Value section ───────────────────────────────────────────────────────── */
.value-cols {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}}
@media (max-width: 768px) {{ .value-cols {{ grid-template-columns: 1fr; }} }}
.value-card {{
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: .9rem 1.1rem;
}}
.value-card-title {{
  font-size: .65rem;
  text-transform: uppercase;
  letter-spacing: .07em;
  color: var(--color-muted);
  font-weight: 600;
  margin-bottom: .5rem;
}}
.value-item {{
  padding: .35rem 0;
  border-bottom: 1px solid var(--color-border);
  font-size: .78rem;
  display: flex;
  align-items: flex-start;
  gap: .5rem;
}}
.value-item:last-child {{ border-bottom: none; }}
.value-item-name {{ font-weight: 600; min-width: 120px; }}
.value-item-reason {{ color: var(--color-muted); font-size: .73rem; }}
.model-over  {{ border-left: 2px solid #22c55e; padding-left: .5rem; }}
.model-under {{ border-left: 2px solid #f87171; padding-left: .5rem; }}
.struct-fade {{ border-left: 2px solid #f59e0b; padding-left: .5rem; }}

/* ── Footer ──────────────────────────────────────────────────────────────── */
footer {{
  background: var(--color-surface);
  border-top: 1px solid var(--color-border);
  padding: 1.5rem 0;
  margin-top: 2rem;
  text-align: center;
  font-size: .72rem;
  color: var(--color-muted);
  line-height: 1.6;
}}
footer strong {{ color: var(--color-gold); }}

/* ── Utility ─────────────────────────────────────────────────────────────── */
.text-gold {{ color: var(--color-gold); }}
.text-muted {{ color: var(--color-muted); }}
.text-sm {{ font-size: .78rem; }}
.mt-half {{ margin-top: .5rem; }}
.flex {{ display: flex; }}
.gap-sm {{ gap: .5rem; }}
.items-center {{ align-items: center; }}
.divider {{ border: none; border-top: 1px solid var(--color-border); margin: 1rem 0; }}
.pill {{
  display: inline-block;
  font-size: .6rem;
  font-weight: 600;
  padding: .1rem .4rem;
  border-radius: 20px;
  text-transform: uppercase;
  letter-spacing: .04em;
}}
.pill-gold {{ background: rgba(201,168,76,0.15); color: var(--color-gold); border: 1px solid var(--color-gold-dim); }}
.no-results {{
  text-align: center;
  color: var(--color-muted);
  padding: 2rem;
  font-size: .85rem;
}}
</style>
</head>
<body>

<!-- ── DATA ─────────────────────────────────────────────────────────────── -->
<script>
{js_data}
</script>

<!-- ── HERO ─────────────────────────────────────────────────────────────── -->
<div class="hero">
  <div class="container">
    <div class="hero-inner">
      <div>
        <div class="hero-badge">VenueDNA · Pre-Tournament Analysis</div>
        <h1 class="hero-title">The Open Championship 2026</h1>
        <p class="hero-subtitle">
          <span>Royal Birkdale Golf Club</span> &nbsp;·&nbsp; Par 70 · 7,223 yds
          &nbsp;·&nbsp; Southport, England &nbsp;·&nbsp; July 17–20, 2026
        </p>
      </div>
      <div class="hero-stats" id="hero-stats">
        <!-- filled by JS -->
      </div>
    </div>
  </div>
</div>

<!-- ── NAV ──────────────────────────────────────────────────────────────── -->
<nav class="nav-bar">
  <div class="container">
    <div class="nav-inner">
      <a href="#venue"    class="nav-link active">Venue DNA</a>
      <a href="#tiers"    class="nav-link">Tier Board</a>
      <a href="#probs"    class="nav-link">Probabilities</a>
      <a href="#field"    class="nav-link">Field Explorer</a>
      <a href="#council"  class="nav-link">Council Review</a>
      <a href="#patterns" class="nav-link">Anti-Patterns</a>
      <a href="#value"    class="nav-link">Value Bets</a>
    </div>
  </div>
</nav>

<!-- ── VENUE DNA ────────────────────────────────────────────────────────── -->
<section class="section" id="venue">
  <div class="container">
    <div class="section-header">
      <h2 class="section-title">Venue DNA</h2>
      <span class="section-badge">Royal Birkdale</span>
    </div>
    <div class="venue-grid">
      <div>
        <div class="radar-wrap">
          <div class="radar-title">Skill Weight Profile</div>
          <canvas id="radar-chart" width="260" height="220"></canvas>
        </div>
      </div>
      <div>
        <div class="venue-facts" id="venue-facts"><!-- filled by JS --></div>
        <ul class="mechanism-list" id="mechanism-list"></ul>
      </div>
    </div>
    <div class="two-col mt-half" style="margin-top:1rem">
      <div class="panel">
        <div class="panel-title">Upgrade Traits</div>
        <div id="upgrade-traits"></div>
      </div>
      <div class="panel">
        <div class="panel-title">Downgrade Traits</div>
        <div id="downgrade-traits"></div>
      </div>
    </div>
  </div>
</section>

<!-- ── TIER BOARD ───────────────────────────────────────────────────────── -->
<section class="section" id="tiers">
  <div class="container">
    <div class="section-header">
      <h2 class="section-title">Tier Board</h2>
      <span class="section-badge" id="tier-field-count"></span>
    </div>
    <div id="tier-board"><!-- filled by JS --></div>
  </div>
</section>

<!-- ── PROBABILITIES ────────────────────────────────────────────────────── -->
<section class="section" id="probs">
  <div class="container">
    <div class="section-header">
      <h2 class="section-title">Win Probability — Top 20</h2>
      <span class="section-badge">Softmax VTS Model</span>
    </div>
    <div class="prob-chart-wrap">
      <div class="prob-chart-title">Win % by Player (top 20 ranked)</div>
      <canvas id="prob-chart" height="100"></canvas>
    </div>
    <div class="prob-chart-wrap">
      <div class="prob-chart-title">Top-10 % by Player (top 20 ranked)</div>
      <canvas id="t10-chart" height="100"></canvas>
    </div>
  </div>
</section>

<!-- ── FIELD EXPLORER ───────────────────────────────────────────────────── -->
<section class="section" id="field">
  <div class="container">
    <div class="section-header">
      <h2 class="section-title">Field Explorer</h2>
      <span class="section-badge" id="field-count-badge">156 players</span>
    </div>
    <div class="filter-row">
      <label>Search</label>
      <input type="search" id="field-search" placeholder="Player name…" autocomplete="off">
      <label>Tier</label>
      <select id="field-tier">
        <option value="">All Tiers</option>
        <option>T1</option><option>T2</option><option>T3</option>
        <option>T4</option><option>T5</option>
      </select>
      <label>Country</label>
      <select id="field-country"><option value="">All</option></select>
      <label>Form</label>
      <select id="field-form">
        <option value="">All</option>
        <option>hot</option><option>warm</option><option>neutral</option>
        <option>cool</option><option>cold</option>
      </select>
      <label>Debut</label>
      <select id="field-debut">
        <option value="">All</option>
        <option value="yes">Debut Only</option>
        <option value="no">Non-Debut</option>
      </select>
    </div>
    <div class="table-wrap">
      <table class="field-table" id="field-table">
        <thead>
          <tr>
            <th data-col="rank" class="sorted-asc">Rank</th>
            <th data-col="playerName">Player</th>
            <th data-col="tier">Tier</th>
            <th data-col="vtsFinal" class="num">VTS</th>
            <th data-col="winPct"  class="num">Win%</th>
            <th data-col="top10Pct" class="num">Top10%</th>
            <th data-col="makeCutPct" class="num">MakeCut%</th>
            <th data-col="sgAPP_L12" class="num">SG:APP</th>
            <th data-col="sgOTT_L12" class="num">SG:OTT</th>
            <th data-col="sgARG_L12" class="num">SG:ARG</th>
            <th data-col="sgPUTT_L12" class="num">SG:PUTT</th>
            <th data-col="formTrend">Form</th>
            <th data-col="r1TeeTime">R1 Tee</th>
          </tr>
        </thead>
        <tbody id="field-tbody"></tbody>
      </table>
    </div>
    <div id="field-no-results" class="no-results" style="display:none">No players match your filters.</div>
  </div>
</section>

<!-- ── COUNCIL REVIEW ───────────────────────────────────────────────────── -->
<section class="section" id="council">
  <div class="container">
    <div class="section-header">
      <h2 class="section-title">Council Review</h2>
      <span class="section-badge">Devil's Advocate · Contrarian · Calibration</span>
    </div>
    <div id="council-log"></div>
  </div>
</section>

<!-- ── ANTI-PATTERNS ────────────────────────────────────────────────────── -->
<section class="section" id="patterns">
  <div class="container">
    <div class="section-header">
      <h2 class="section-title">Anti-Pattern Flags</h2>
      <span class="section-badge">Gates &amp; Risk Register</span>
    </div>
    <div class="two-col">
      <div class="panel">
        <div class="panel-title">Hard Gate Triggers</div>
        <div id="hard-gates"></div>
      </div>
      <div class="panel">
        <div class="panel-title">Soft Gate Triggers (sample)</div>
        <div id="soft-gates"></div>
      </div>
    </div>
    <div class="panel" style="margin-top:1rem">
      <div class="panel-title">Anti-Pattern Narratives</div>
      <div id="anti-narratives"></div>
    </div>
  </div>
</section>

<!-- ── VALUE BETS ────────────────────────────────────────────────────────── -->
<section class="section" id="value">
  <div class="container">
    <div class="section-header">
      <h2 class="section-title">Value &amp; Disagreement</h2>
      <span class="section-badge">Model vs Market</span>
    </div>
    <div class="value-cols" id="value-cols"><!-- filled by JS --></div>
    <div class="panel" style="margin-top:1rem">
      <div class="panel-title">Disclaimer</div>
      <p class="modal-text" id="value-disclaimer"></p>
    </div>
  </div>
</section>

<!-- ── FOOTER ────────────────────────────────────────────────────────────── -->
<footer>
  <div class="container">
    <strong>VenueDNA</strong> · The Open Championship 2026 · Royal Birkdale Golf Club<br>
    <span id="footer-meta"></span><br>
    Pre-tournament baseline · For analytical use only · Not financial betting advice
  </div>
</footer>

<!-- ── PLAYER MODAL ──────────────────────────────────────────────────────── -->
<div class="modal-backdrop" id="modal-backdrop">
  <div class="modal" id="modal">
    <div class="modal-header">
      <div>
        <div class="modal-player-name" id="modal-name"></div>
        <div style="display:flex;gap:.5rem;align-items:center;margin-top:.3rem" id="modal-badges"></div>
      </div>
      <button class="modal-close" id="modal-close">✕</button>
    </div>
    <div class="modal-body" id="modal-body"></div>
  </div>
</div>

<!-- ── JAVASCRIPT ────────────────────────────────────────────────────────── -->
<script>
// ── helpers ─────────────────────────────────────────────────────────────────
const fmt1 = v => (v == null ? '—' : (+v).toFixed(1));
const fmt2 = v => (v == null ? '—' : (+v).toFixed(2));
const fmt3 = v => (v == null ? '—' : (+v).toFixed(3));
const fmtPct = v => (v == null ? '—' : (+v).toFixed(1) + '%');
const sgClass = v => (+v) >= 0 ? 'sg-pos' : 'sg-neg';
const formClass = f => 'form-' + (f || 'neutral');
const tierColor = t => ({{T1:'#22c55e',T2:'#60a5fa',T3:'#a78bfa',T4:'#fb923c',T5:'#f87171'}})[t] || '#94a3b8';

function tierLabel(t) {{
  return `<span class="tb tb-${{t}}">${{t}}</span>`;
}}

// ── Hero stats ───────────────────────────────────────────────────────────────
(function buildHero() {{
  const t = TIER_LISTS;
  const total = ALL_PLAYERS.length;
  const html = [
    [total, 'Field'],
    [t.tier1.length, 'Tier 1'],
    [t.tier2.length, 'Tier 2'],
    [(t.tier3||[]).length + (t.tier4||[]).length + (t.tier5||[]).length, 'T3-5'],
  ].map(([v,l]) => `<div class="hero-stat"><div class="hero-stat-val">${{v}}</div><div class="hero-stat-label">${{l}}</div></div>`).join('');
  document.getElementById('hero-stats').innerHTML = html;
  document.getElementById('footer-meta').innerHTML =
    `Engine v${{EVENT.engineVersion}} · Generated ${{new Date(EVENT.generatedAt).toLocaleDateString('en-GB',{{dateStyle:'long'}})}}`;
}})();

// ── Venue DNA ───────────────────────────────────────────────────────────────
(function buildVenue() {{
  const v = VENUE;

  // radar chart
  new Chart(document.getElementById('radar-chart'), {{
    type: 'radar',
    data: {{
      labels: ['SG:APP\\n(0.40×1.25)', 'SG:OTT\\n(0.25×1.15)', 'SG:ARG\\n(0.20×1.20)', 'SG:PUTT\\n(0.15×0.95)', 'Wind Mgmt', 'Links Exp'],
      datasets: [{{
        label: 'Birkdale Weight',
        data: [5.0, 2.88, 2.40, 1.43, 4.5, 3.5],
        backgroundColor: 'rgba(201,168,76,0.15)',
        borderColor: '#c9a84c',
        borderWidth: 2,
        pointBackgroundColor: '#c9a84c',
        pointRadius: 3,
      }}]
    }},
    options: {{
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        r: {{
          min: 0, max: 6,
          ticks: {{ display: false }},
          grid: {{ color: 'rgba(255,255,255,0.07)' }},
          pointLabels: {{
            color: '#7a8fa6',
            font: {{ size: 9 }},
          }},
          angleLines: {{ color: 'rgba(255,255,255,0.07)' }},
        }}
      }}
    }}
  }});

  // fact cards
  const facts = [
    ['Par', 'Par ' + v.par, v.yardage + ' yds'],
    ['Winning Score', 'Expected ' + v.expectedWinningScore, '±' + v.sigmaWinningScore + ' sigma'],
    ['Primary Separator', v.primarySeparator, ''],
    ['Secondary Separator', v.secondarySeparator, ''],
    ['Variance Class', v.varianceClass, 'High environment variance'],
    ['Wind Role', 'CRITICAL', v.windRole],
    ['Putting Role', 'Dampened', v.puttingRole],
    ['Condition Forecast', '10-25mph W/NW', '15-19°C · Firm/Fast forecast'],
  ];
  document.getElementById('venue-facts').innerHTML = facts.map(([l,v,s]) => `
    <div class="fact-card">
      <div class="fact-label">${{l}}</div>
      <div class="fact-value">${{v}}</div>
      ${{s ? `<div class="fact-sub">${{s}}</div>` : ''}}
    </div>`).join('');

  // mechanisms
  document.getElementById('mechanism-list').innerHTML =
    (v.keyMechanisms||[]).map(m => `<li>${{m}}</li>`).join('');

  // traits
  const upFmt = t => `<span class="trait-chip trait-up" style="margin:.15rem">${{t}}</span>`;
  const dnFmt = t => `<span class="trait-chip trait-down" style="margin:.15rem">${{t}}</span>`;
  document.getElementById('upgrade-traits').innerHTML   = (v.upgradeTraits||[]).map(upFmt).join('');
  document.getElementById('downgrade-traits').innerHTML = (v.downgradeTraits||[]).map(dnFmt).join('');
}})();

// ── Tier board ───────────────────────────────────────────────────────────────
(function buildTierBoard() {{
  const tiers = [
    {{ key:'tier1', label:'Tier 1', desc:'Elite Venue Fit + Dominant Skill', color:'#22c55e' }},
    {{ key:'tier2', label:'Tier 2', desc:'Strong Contenders', color:'#60a5fa' }},
    {{ key:'tier3', label:'Tier 3', desc:'Capable — Limited Edge', color:'#a78bfa' }},
    {{ key:'tier4', label:'Tier 4', desc:'Below Field Average', color:'#fb923c' }},
    {{ key:'tier5', label:'Tier 5', desc:'Structural Disadvantage', color:'#f87171' }},
  ];
  let total = 0;
  const html = tiers.map((t, ti) => {{
    const players = TIER_LISTS[t.key] || [];
    total += players.length;
    const cards = players.map(p => buildPlayerCard(p, t.key.replace('tier','T'))).join('');
    const collapsed = ti >= 4 ? ' collapsed' : '';
    return `
      <div class="tier-section">
        <div class="tier-header" onclick="toggleTier(this)">
          <span class="tb tb-T${{ti+1}}">${{t.label}}</span>
          <span style="color:var(--color-muted);font-size:.78rem">${{t.desc}}</span>
          <span class="tier-count">${{players.length}} players</span>
          <span class="tier-chevron">${{collapsed ? '▶' : '▼'}}</span>
        </div>
        <div class="tier-body${{collapsed}}">${{cards}}</div>
      </div>`;
  }}).join('');
  document.getElementById('tier-board').innerHTML = html;
  document.getElementById('tier-field-count').textContent = total + ' players';
}})();

function toggleTier(hdr) {{
  const body = hdr.nextElementSibling;
  const chev = hdr.querySelector('.tier-chevron');
  const collapsed = body.classList.toggle('collapsed');
  chev.textContent = collapsed ? '▶' : '▼';
}}

function buildPlayerCard(p, tier) {{
  const upgrades = (p.traitFlagsUpgrade||[]).slice(0,3).map(t => `<span class="trait-chip trait-up">${{t}}</span>`).join('');
  const downgrades = (p.traitFlagsDowngrade||[]).slice(0,2).map(t => `<span class="trait-chip trait-down">${{t}}</span>`).join('');
  const debutFlag = p.isDebut ? '<span class="debut-flag">DEBUT</span>' : '';
  const form = p.formTrend || 'neutral';
  const histRds = p.venueHistoryRounds || 0;
  return `
    <div class="player-card" onclick="openModal(${{JSON.stringify(p.playerName)}})">
      ${{debutFlag}}
      <div class="player-card-top">
        <span class="player-rank">#${{p._rank || ''}}</span>
        <span class="player-name">${{p.playerName}}</span>
        <span class="player-country">${{p.country||''}}</span>
      </div>
      <div style="display:flex;align-items:center;gap:.5rem">
        <span class="player-vts">${{fmt3(p.vtsFinal)}}</span>
        ${{tierLabel(tier)}}
        <span style="font-size:.7rem;color:var(--color-muted);margin-left:auto">Win <strong style="color:var(--color-text)">${{fmtPct(p.winPct)}}</strong></span>
      </div>
      <div class="player-stats">
        <span class="pstat">APP <span class="${{sgClass(p.sgAPP_L12)}}">${{fmt3(p.sgAPP_L12)}}</span></span>
        <span class="pstat">OTT <span class="${{sgClass(p.sgOTT_L12)}}">${{fmt3(p.sgOTT_L12)}}</span></span>
        <span class="pstat">ARG <span class="${{sgClass(p.sgARG_L12)}}">${{fmt3(p.sgARG_L12)}}</span></span>
        <span class="pstat"><span class="form-dot ${{formClass(form)}}"></span>${{form}}</span>
      </div>
      ${{histRds > 0 ? `<div style="font-size:.65rem;color:var(--color-muted);margin-top:.3rem">Birkdale: ${{histRds}} rds · SG ${{fmt2(p.venueHistorySG)}}</div>` : ''}}
      <div class="player-trait-row">${{upgrades}}${{downgrades}}</div>
    </div>`;
}}

// ── Probability charts ───────────────────────────────────────────────────────
(function buildProbCharts() {{
  const pv = PROB_VIEW.slice(0, 20);
  const labels = pv.map(p => p.playerName.split(' ').pop());
  const colors = pv.map(p => tierColor(p.tier));
  const cfg = (data, label, id) => {{
    new Chart(document.getElementById(id), {{
      type: 'bar',
      data: {{
        labels,
        datasets: [{{ label, data, backgroundColor: colors, borderRadius: 4 }}]
      }},
      options: {{
        plugins: {{
          legend: {{ display: false }},
          tooltip: {{
            callbacks: {{
              label: ctx => ctx.dataset.label + ': ' + ctx.raw.toFixed(1) + '%',
              title: ctx => pv[ctx[0].dataIndex].playerName
            }}
          }}
        }},
        scales: {{
          x: {{ ticks: {{ color: '#7a8fa6', font: {{ size: 10 }} }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
          y: {{ ticks: {{ color: '#7a8fa6', font: {{ size: 10 }}, callback: v => v + '%' }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }}
        }}
      }}
    }});
  }};
  cfg(pv.map(p => p.winPct),   'Win %',    'prob-chart');
  cfg(pv.map(p => p.top10Pct), 'Top-10 %', 't10-chart');
}})();

// ── Field explorer ──────────────────────────────────────────────────────────
(function buildFieldExplorer() {{
  // populate country filter
  const countries = [...new Set(ALL_PLAYERS.map(p => p.country).filter(Boolean))].sort();
  const cSel = document.getElementById('field-country');
  countries.forEach(c => {{ const o = document.createElement('option'); o.value = c; o.textContent = c; cSel.appendChild(o); }});

  // sort state
  let sortCol = 'rank', sortAsc = true;

  // map _rank from all players for field table
  const players = ALL_PLAYERS.map(p => ({{...p, rank: p._rank}}));

  function render() {{
    const search  = document.getElementById('field-search').value.toLowerCase();
    const tier    = document.getElementById('field-tier').value;
    const country = document.getElementById('field-country').value;
    const form    = document.getElementById('field-form').value;
    const debut   = document.getElementById('field-debut').value;

    let rows = players.filter(p => {{
      if (search  && !p.playerName.toLowerCase().includes(search)) return false;
      if (tier    && p.tier !== tier) return false;
      if (country && p.country !== country) return false;
      if (form    && p.formTrend !== form) return false;
      if (debut === 'yes' && !p.isDebut) return false;
      if (debut === 'no'  &&  p.isDebut) return false;
      return true;
    }});

    // sort
    rows.sort((a, b) => {{
      let av = a[sortCol], bv = b[sortCol];
      if (av == null) av = sortAsc ? Infinity : -Infinity;
      if (bv == null) bv = sortAsc ? Infinity : -Infinity;
      if (typeof av === 'string') return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
      return sortAsc ? av - bv : bv - av;
    }});

    const badge = document.getElementById('field-count-badge');
    badge.textContent = rows.length + ' / ' + players.length + ' players';

    const noRes = document.getElementById('field-no-results');
    if (rows.length === 0) {{ noRes.style.display = ''; document.getElementById('field-tbody').innerHTML = ''; return; }}
    noRes.style.display = 'none';

    const winMax = Math.max(...rows.map(p => p.winPct || 0));
    document.getElementById('field-tbody').innerHTML = rows.map(p => {{
      const sg = v => `<span class="${{sgClass(v)}}">${{fmt3(v)}}</span>`;
      const winBar = `<div class="win-bar">
        <div class="win-bar-track"><div class="win-bar-fill" style="width:${{((p.winPct||0)/winMax*100).toFixed(0)}}%"></div></div>
        <span style="font-size:.7rem">${{fmtPct(p.winPct)}}</span>
      </div>`;
      return `<tr onclick="openModal('${{p.playerName.replace(/'/g,"\\\\'")}}')" >
        <td class="pos">${{p._rank||''}}</td>
        <td style="font-weight:500">${{p.playerName}}${{p.isDebut ? ' <span class="pill pill-gold" style="font-size:.55rem">D</span>' : ''}}</td>
        <td>${{tierLabel(p.tier)}}</td>
        <td class="num">${{fmt3(p.vtsFinal)}}</td>
        <td class="num">${{winBar}}</td>
        <td class="num">${{fmtPct(p.top10Pct)}}</td>
        <td class="num">${{fmtPct(p.makeCutPct)}}</td>
        <td class="num">${{sg(p.sgAPP_L12)}}</td>
        <td class="num">${{sg(p.sgOTT_L12)}}</td>
        <td class="num">${{sg(p.sgARG_L12)}}</td>
        <td class="num">${{sg(p.sgPUTT_L12)}}</td>
        <td><span class="form-dot ${{formClass(p.formTrend)}}"></span>${{p.formTrend||''}}</td>
        <td style="color:var(--color-muted)">${{p.r1TeeTime||''}}</td>
      </tr>`;
    }}).join('');
  }}

  // sort on header click
  document.getElementById('field-table').querySelectorAll('th[data-col]').forEach(th => {{
    th.addEventListener('click', () => {{
      const col = th.dataset.col;
      if (sortCol === col) sortAsc = !sortAsc;
      else {{ sortCol = col; sortAsc = col === 'rank'; }}
      document.querySelectorAll('th[data-col]').forEach(h => h.classList.remove('sorted-asc','sorted-desc'));
      th.classList.add(sortAsc ? 'sorted-asc' : 'sorted-desc');
      render();
    }});
  }});

  ['field-search','field-tier','field-country','field-form','field-debut'].forEach(id => {{
    document.getElementById(id).addEventListener('input', render);
    document.getElementById(id).addEventListener('change', render);
  }});

  render();
}})();

// ── Council log ──────────────────────────────────────────────────────────────
(function buildCouncil() {{
  const actionClass = a => ({{Confirm:'confirm', Flag:'flag', Override:'override'}})[a] || '';
  document.getElementById('council-log').innerHTML = COUNCIL_LOG.map(e => `
    <div class="council-entry ${{actionClass(e.action)}}">
      <div class="council-role ${{e.role}}">${{e.role}}</div>
      <div>
        <span class="council-action action-${{e.action}}">${{e.action}}</span>
        <span class="council-player">${{e.playerAffected||'Field'}}</span>
        ${{e.magnitude ? `<span style="color:var(--color-muted);font-size:.72rem">· ${{e.magnitude}}</span>` : ''}}
      </div>
      <div class="council-finding">${{e.finding}}</div>
      ${{e.notes ? `<div style="font-size:.7rem;color:var(--color-gold-dim);margin-top:.25rem">${{e.notes}}</div>` : ''}}
    </div>`).join('');
}})();

// ── Anti-patterns ─────────────────────────────────────────────────────────────
(function buildAntiPatterns() {{
  const hp = (ANTI_PATTERN.hardGatePlayers||[]);
  document.getElementById('hard-gates').innerHTML = hp.map(p => `
    <div class="panel-row">
      <span class="panel-row-name">${{p.playerName}}</span>
      <span><span class="gate-chip gate-hard">${{p.gate}}</span></span>
      <span class="panel-row-detail" style="text-align:right">${{p.penaltyApplied > 0 ? '+' : ''}}${{fmt2(p.penaltyApplied)}} VTS</span>
    </div>`).join('') || '<div class="text-muted text-sm" style="padding:.5rem 0">None triggered.</div>';

  const sp = (ANTI_PATTERN.softGatePlayers||[]).slice(0,10);
  document.getElementById('soft-gates').innerHTML = sp.map(p => `
    <div class="panel-row">
      <span class="panel-row-name">${{p.playerName}}</span>
      <span><span class="gate-chip gate-soft">${{p.gate}}</span></span>
      <span class="panel-row-detail" style="text-align:right">${{fmt2(p.penaltyApplied)}} VTS</span>
    </div>`).join('') || '<div class="text-muted text-sm" style="padding:.5rem 0">None triggered.</div>';

  const narr = ANTI_PATTERN.antiPatternNarratives || [];
  const narrArr = Array.isArray(narr) ? narr : Object.entries(narr).map(([k,v]) => ({{pattern:k, ...v}}));
  document.getElementById('anti-narratives').innerHTML = narrArr.slice(0,8).map(n => `
    <div class="panel-row" style="flex-direction:column;align-items:flex-start;gap:.25rem">
      <span class="gate-chip gate-hard">${{n.pattern||n.antiPattern||'Pattern'}}</span>
      <span class="modal-text" style="margin-top:.25rem">${{n.narrative||n.description||''}}</span>
    </div>`).join('') || '<div class="text-muted text-sm" style="padding:.5rem 0">No narratives available.</div>';
}})();

// ── Value section ──────────────────────────────────────────────────────────────
(function buildValue() {{
  const vs = VALUE_SECTION;
  const over  = (vs.modelOver||[]);
  const under = (vs.modelUnder||[]);
  const fades = (vs.structuralFades||[]);

  const mkCard = (title, items, cls) => `
    <div class="value-card">
      <div class="value-card-title">${{title}}</div>
      ${{items.map(it => `
        <div class="value-item ${{cls}}">
          <span class="value-item-name ${{cls === 'model-over' ? 'sg-pos' : cls === 'model-under' ? 'sg-neg' : 'text-gold'}}">${{it.playerName}}</span>
          <span class="value-item-reason">${{it.reason||it.narrative||''}}</span>
        </div>`).join('') || '<div class="text-muted text-sm" style="padding:.35rem 0">None flagged.</div>'}}
    </div>`;

  document.getElementById('value-cols').innerHTML =
    mkCard('Model Over (Value Plays)', over, 'model-over') +
    mkCard('Model Under (Fade Candidates)', under, 'model-under');

  if (fades.length > 0) {{
    const fadeHtml = `<div class="value-card" style="margin-top:1rem;grid-column:1/-1">
      <div class="value-card-title">Structural Fades</div>
      ${{fades.map(it => `<div class="value-item struct-fade"><span class="value-item-name text-gold">${{it.playerName}}</span><span class="value-item-reason">${{it.reason||it.narrative||''}}</span></div>`).join('')}}
    </div>`;
    document.getElementById('value-cols').innerHTML += fadeHtml;
  }}

  document.getElementById('value-disclaimer').innerHTML = vs.disclaimer || '';
}})();

// ── Player modal ──────────────────────────────────────────────────────────────
const playerMap = Object.fromEntries(ALL_PLAYERS.map(p => [p.playerName, p]));

function openModal(name) {{
  const p = playerMap[name];
  if (!p) return;

  document.getElementById('modal-name').textContent = p.playerName;
  const badges = [
    tierLabel(p.tier),
    `<span class="pill pill-gold">Rank #${{p._rank}}</span>`,
    p.isDebut ? '<span class="pill" style="background:rgba(251,191,36,0.15);color:#fbbf24;border:1px solid rgba(251,191,36,0.3)">DEBUT</span>' : '',
    `<span style="font-size:.7rem;color:var(--color-muted)">${{p.country||''}}</span>`,
  ].join(' ');
  document.getElementById('modal-badges').innerHTML = badges;

  const sgBarHtml = (label, val, max) => {{
    const v = val || 0;
    const w = Math.min(100, Math.abs(v) / (max||2) * 100);
    const cls = v >= 0 ? 'sg-bar-pos' : 'sg-bar-neg';
    const margin = v >= 0 ? 0 : (100 - w);
    return `<div class="sg-row">
      <span class="sg-label">${{label}}</span>
      <div class="sg-bar-track"><div class="sg-bar-fill ${{cls}}" style="width:${{w.toFixed(0)}}%;margin-left:${{v<0?((100-w).toFixed(0))+'%':'0'}}"></div></div>
      <span class="sg-val ${{v>=0?'sg-pos':'sg-neg'}}">${{v>=0?'+':''}}${{fmt3(v)}}</span>
    </div>`;
  }};

  const pens = (p.penaltiesApplied||[]).map(x => `<span class="gate-chip ${{x.includes('-') ? 'gate-soft' : 'gate-soft'}}" style="margin:.1rem">${{x}}</span>`).join('') || '—';
  const traits_up = (p.traitFlagsUpgrade||[]).map(t => `<span class="trait-chip trait-up" style="margin:.1rem">${{t}}</span>`).join('');
  const traits_dn = (p.traitFlagsDowngrade||[]).map(t => `<span class="trait-chip trait-down" style="margin:.1rem">${{t}}</span>`).join('');

  document.getElementById('modal-body').innerHTML = `
    <div class="modal-grid">
      <div class="modal-stat"><div class="modal-stat-label">VTS Final</div><div class="modal-stat-val text-gold">${{fmt3(p.vtsFinal)}}</div></div>
      <div class="modal-stat"><div class="modal-stat-label">Win %</div><div class="modal-stat-val">${{fmtPct(p.winPct)}}</div></div>
      <div class="modal-stat"><div class="modal-stat-label">Top-5 %</div><div class="modal-stat-val">${{fmtPct(p.top5Pct)}}</div></div>
      <div class="modal-stat"><div class="modal-stat-label">Top-10 %</div><div class="modal-stat-val">${{fmtPct(p.top10Pct)}}</div></div>
      <div class="modal-stat"><div class="modal-stat-label">Make Cut %</div><div class="modal-stat-val">${{fmtPct(p.makeCutPct)}}</div></div>
      <div class="modal-stat"><div class="modal-stat-label">Neutral Skill SG</div><div class="modal-stat-val">${{fmt3(p.neutralSkillSG)}}</div></div>
      <div class="modal-stat"><div class="modal-stat-label">Venue Fit Delta</div><div class="modal-stat-val ${{p.venueFitDelta>=0?'sg-pos':'sg-neg'}}">${{fmt3(p.venueFitDelta)}}</div></div>
      <div class="modal-stat"><div class="modal-stat-label">History Rounds</div><div class="modal-stat-val">${{p.venueHistoryRounds||0}} rds</div></div>
    </div>

    <div class="modal-section-title">Strokes Gained (L12 weeks)</div>
    ${{sgBarHtml('SG:APP', p.sgAPP_L12, 1.5)}}
    ${{sgBarHtml('SG:OTT', p.sgOTT_L12, 1.5)}}
    ${{sgBarHtml('SG:ARG', p.sgARG_L12, 1.0)}}
    ${{sgBarHtml('SG:PUTT', p.sgPUTT_L12, 1.0)}}
    ${{sgBarHtml('SG:TOTAL', p.sgTotal_L12, 3.0)}}

    <div class="modal-section-title">Scoring Layers</div>
    <div class="modal-grid" style="grid-template-columns:1fr 1fr 1fr">
      <div class="modal-stat"><div class="modal-stat-label">Pre-Penalty VTS</div><div class="modal-stat-val">${{fmt3(p.prePenaltyVTS)}}</div></div>
      <div class="modal-stat"><div class="modal-stat-label">Penalty Total</div><div class="modal-stat-val ${{(p.penaltyTotal||0)<0?'sg-neg':'sg-pos'}}">${{fmt2(p.penaltyTotal||0)}}</div></div>
      <div class="modal-stat"><div class="modal-stat-label">Blend Class</div><div class="modal-stat-val">${{p.blendClass||'—'}}</div></div>
    </div>
    <div style="margin-top:.35rem;font-size:.72rem;color:var(--color-muted)">Penalties applied: ${{pens}}</div>

    ${{p.convictionStatement ? `
    <div class="modal-section-title">Conviction</div>
    <p class="modal-text"><strong>Edge:</strong> ${{p.convictionStatement}}</p>
    <p class="modal-text mt-half"><strong>Risk:</strong> ${{p.failureCondition||'—'}}</p>
    ` : ''}}

    ${{(traits_up || traits_dn) ? `
    <div class="modal-section-title">Trait Flags</div>
    <div style="margin-bottom:.35rem">${{traits_up}}</div>
    <div>${{traits_dn}}</div>
    ` : ''}}

    ${{p.bettingPath ? `
    <div class="modal-section-title">Betting Path (Use Case: ${{p.bettingUseCase||''}})</div>
    <p class="modal-text">${{p.bettingPath}}</p>
    ` : ''}}

    ${{p.councilNote ? `
    <div class="modal-section-title">Council Note</div>
    <p class="modal-text">${{p.councilNote}}</p>
    ` : ''}}

    <div class="modal-section-title">Tee Times</div>
    <div class="modal-grid" style="grid-template-columns:1fr 1fr">
      <div class="modal-stat"><div class="modal-stat-label">R1 Tee · Hole</div><div class="modal-stat-val">${{p.r1TeeTime||'—'}} · #${{p.r1StartHole||''}}</div></div>
      <div class="modal-stat"><div class="modal-stat-label">R2 Tee · Hole</div><div class="modal-stat-val">${{p.r2TeeTime||'—'}} · #${{p.r2StartHole||''}}</div></div>
    </div>

    <div style="margin-top:.75rem;font-size:.7rem;color:var(--color-muted)">
      Form: ${{p.formTrend}} · Volatility: ${{p.volatilityIndex}} · Fragility: ${{p.fragility}} · OWGR: #${{p.owgr||'N/A'}}
    </div>`;

  document.getElementById('modal-backdrop').classList.add('open');
  document.getElementById('modal').scrollTop = 0;
}}

document.getElementById('modal-close').addEventListener('click', closeModal);
document.getElementById('modal-backdrop').addEventListener('click', e => {{
  if (e.target === document.getElementById('modal-backdrop')) closeModal();
}});
document.addEventListener('keydown', e => {{ if (e.key === 'Escape') closeModal(); }});

function closeModal() {{
  document.getElementById('modal-backdrop').classList.remove('open');
}}

// ── Nav highlight ─────────────────────────────────────────────────────────────
(function initNav() {{
  const sections = document.querySelectorAll('.section[id]');
  const links    = document.querySelectorAll('.nav-link');
  const obs = new IntersectionObserver(entries => {{
    entries.forEach(e => {{
      if (e.isIntersecting) {{
        links.forEach(l => l.classList.toggle('active', l.getAttribute('href') === '#' + e.target.id));
      }}
    }});
  }}, {{ rootMargin: '-40% 0px -55% 0px' }});
  sections.forEach(s => obs.observe(s));
}})();
</script>
</body>
</html>
"""

OUTPUT.write_text(html, encoding="utf-8")
size = OUTPUT.stat().st_size
print(f"Board written -> {OUTPUT}")
print(f"Size: {size:,} bytes ({size/1024:.0f} KB)")
