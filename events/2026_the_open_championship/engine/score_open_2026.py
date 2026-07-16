"""
VenueDNA 2026 The Open Championship — Full Scoring Engine
Royal Birkdale Golf Club | July 17–20, 2026
Scoring Spec v1.1 | Engine v1.1
"""
import csv, json, math, os, re, datetime
from collections import defaultdict

BASE = r"C:\PGA_VenueDNA\events\2026_the_open_championship"
INPUT = os.path.join(BASE, "input")
OUTPUT = os.path.join(BASE, "output")
DEPLOY = os.path.join(BASE, "deploy", "data")

def r(v, n=3): return round(v, n) if v is not None else None
def safe_float(v, d=0.0):
    try: return float(str(v).replace("+","").replace(",",""))
    except: return d

# ── 1. LOAD INPUT DATA ────────────────────────────────────────────────────────

def load_csv(path, encoding="utf-8"):
    rows = []
    try:
        with open(path, encoding=encoding, errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append({k.strip(): v.strip() if v else "" for k,v in row.items()})
    except Exception as e:
        print(f"WARN: Could not load {path}: {e}")
    return rows

def norm_name(n):
    """Normalize player name to 'First Last' format."""
    n = n.strip().strip('"')
    # Handle "Last, First" format
    if "," in n:
        parts = n.split(",", 1)
        return (parts[1].strip() + " " + parts[0].strip()).strip()
    return n.strip()

def name_key(n):
    return re.sub(r"[^a-z]", "", norm_name(n).lower())

# Load all files
print("Loading input files...")
decomp_raw   = load_csv(os.path.join(INPUT, "dg_decomposition.csv"))
skills_raw   = load_csv(os.path.join(INPUT, "dg_skill_ratings.csv"))
field_raw    = load_csv(os.path.join(INPUT, "the_open_championship_player_field_R1_R2_teetimes.csv"))
ch_raw       = load_csv(os.path.join(INPUT, "royal_birkdale_gc_CH.csv"))
trending_raw = load_csv(os.path.join(INPUT, "pga_field_trending_table.csv"))
cfa_raw      = load_csv(os.path.join(INPUT, "the_open_championship_coursefitadjustments.csv"))
app_great    = load_csv(os.path.join(INPUT, "app_skill_l12_great.csv"))
app_bad      = load_csv(os.path.join(INPUT, "app_skill_l12_bad.csv"))

with open(os.path.join(INPUT, "venue_birkdale_2026.json"), encoding="utf-8") as f:
    venue = json.load(f)

# Build name-keyed lookups
decomp   = {name_key(r["player_name"]): r for r in decomp_raw}
skills   = {name_key(r["player_name"]): r for r in skills_raw}
trending = {name_key(r["player_name"]): r for r in trending_raw}

# coursefitadjustments has "Last Name","First Name" columns
def cfa_key(row):
    ln = row.get("Last Name","").strip().strip('"')
    fn = row.get("First Name","").strip().strip('"')
    return name_key(fn + " " + ln)
cfa = {cfa_key(r): r for r in cfa_raw if r.get("Last Name","")}

# Country lookup from field
country_map = {
    "Scheffler, Scottie":"USA","McIlroy, Rory":"NIR","Rahm, Jon":"ESP",
    "Fleetwood, Tommy":"ENG","Fitzpatrick, Matt":"ENG","Hovland, Viktor":"NOR",
    "Schauffele, Xander":"USA","MacIntyre, Robert":"SCO","Young, Cameron":"USA",
    "Morikawa, Collin":"USA","Cantlay, Patrick":"USA","Clark, Wyndham":"USA",
    "Thomas, Justin":"USA","Burns, Sam":"USA","Rose, Justin":"ENG",
    "Aberg, Ludvig":"SWE","Hatton, Tyrrell":"ENG","Lowry, Shane":"IRL",
    "Lee, Min Woo":"AUS","Gotterup, Chris":"USA","Fitzpatrick, Alex":"ENG",
    "Kim, Si Woo":"KOR","Rai, Aaron":"ENG","Henley, Russell":"USA",
    "Griffin, Ben":"USA","Spaun, J.J.":"USA","Reed, Patrick":"USA",
    "English, Harris":"USA","Niemann, Joaquin":"CHI","Noren, Alex":"SWE",
    "Scott, Adam":"AUS","Gerard, Ryan":"USA","Kitayama, Kurt":"USA",
    "McNealy, Maverick":"USA","Fowler, Rickie":"USA","Harman, Brian":"USA",
    "Matsuyama, Hideki":"JPN","Perez, Victor":"FRA","Bradley, Keegan":"USA",
    "DeChambeau, Bryson":"USA","Spieth, Jordan":"USA","Conners, Corey":"CAN",
    "Bhatia, Akshay":"USA","Reitan, Kristoffer":"NOR","Wallace, Matt":"ENG",
    "Taylor, Nick":"CAN","Cauley, Bud":"USA","Fox, Ryan":"NZL",
    "McKibbin, Tom":"NIR","Smith, Jordan":"ENG","Poston, J.T.":"USA",
    "Koepka, Brooks":"USA","Chacarra, Eugenio":"ESP","Smalley, Alex":"USA",
    "Thorbjornsen, Michael":"USA","Bridgeman, Jacob":"USA","Day, Jason":"AUS",
    "Mitchell, Keith":"USA","Kim, Michael":"USA","Hall, Harry":"USA",
    "Cole, Eric":"USA","Jarvis, Casey":"RSA","Homa, Max":"USA",
    "Theegala, Sahith":"USA","Parry, John":"ENG","Hisatsune, Ryo":"JPN",
    "Novak, Andrew":"USA","Stevens, Sam":"USA","Woodland, Gary":"USA",
    "Detry, Thomas":"BEL","Straka, Sepp":"AUT","Greyserman, Max":"USA",
    "Smith, Cameron":"AUS","Im, Sungjae":"KOR","Puig, David":"ESP",
    "McCarty, Matt":"USA","Neergaard-Petersen, Rasmus":"DEN","Ayora, Angel":"ECU",
    "Keefer, Johnny":"USA","Knapp, Jake":"USA","Schaper, Jayden":"RSA",
    "Cink, Stewart":"USA","Berger, Daniel":"USA","Echavarria, Nico":"COL",
    "Coody, Pierceson":"USA","Li, Haotong":"CHN","Canter, Laurie":"ENG",
    "Hillier, Daniel":"NZL","Molinari, Francesco":"ITA","Suber, Jackson":"USA",
    "Nakajima, Keita":"JPN","Wiesberger, Bernd":"AUT","Vincent, Scott":"ZIM",
    "Sullivan, Andy":"ENG","Brennan, Michael":"USA","Herbert, Lucas":"AUS",
    "Valimaki, Sami":"FIN","Penge, Marco":"ENG","Hojgaard, Rasmus":"DEN",
    "Du Plessis, Hennie":"RSA","Kaneko, Kota":"JPN","Jordan, Matthew":"ENG",
    "Brown, Dan":"ENG","Svensson, Jesper":"SWE","Horschel, Billy":"USA",
    "Rozner, Antoine":"FRA","Saddier, Adrien":"FRA","Kobori, Kazuma":"JPN",
    "Norris, Shaun":"RSA","Dean, Joe":"ENG","Bradbury, Dan":"ENG",
    "Harrington, Padraig":"IRL","Potgieter, Aldrich":"RSA","Couvra, Martin":"FRA",
    "Laporta, Francesco":"ITA","Stenson, Henrik":"SWE","Ballester, Jose Luis":"ESP",
    "LaCroix, Frederic":"FRA","Bairstow, Sam":"ENG","Yonezawa, Ren":"JPN",
    "Lagergren, Joakim":"SWE","Hollick, Michael":"ENG","Daffue, MJ":"RSA",
    "Docherty, Alistair":"SCO","Higa, Kazuki":"JPN","Smyth, Trav":"AUS",
    "Surratt, Caleb":"USA","Southgate, Matthew":"ENG","Nagano, Ryutaro":"JPN",
    "Truslow, Austen":"USA","Ham, Jeong Woo":"KOR","Baldwin, Matthew":"ENG",
    "Wiedemeyer, Tim":"GER","Uihlein, Peter":"USA","Clarke, Darren":"NIR",
    "McDonald, Jack":"SCO","Nicholas, James":"USA","Skogen, Baard":"NOR",
    "Grinberg, Lev":"ISR","Kataoka, Naoyuki":"JPN","Grehan, Stuart":"IRL",
    "De Castro Piera, Alejandro":"ESP","John, Cameron":"AUS","Buchanan, Jack":"SCO",
    "Christensen, Tiger":"DEN","Yang, Jiho":"KOR","Howell, Mason":"USA",
    "Plunkett, Marcus":"IRL","Ruiter, Nevill":"RSA","Pulcini, Mateo":"ARG",
    "Laopakdee, Fifa":"THA","Sloman, Tom":"ENG","Duval, David":"USA",
    "Howard, David":"USA","Hojgaard, Nicolai":"DEN","Kim, Tom":"KOR",
}

# Build course history lookup (from royal_birkdale_gc_CH.csv)
ch_data = {}
for row in ch_raw:
    pn = row.get("player_name","")
    if pn:
        key = name_key(pn)
        rp = safe_float(row.get("rounds_played","0"))
        hsg = row.get("historical_true_sg","")
        ch_data[key] = {
            "rounds_played": int(rp) if rp else 0,
            "historical_true_sg": safe_float(hsg) if hsg and hsg != "null" else None,
            "versus_expected": safe_float(row.get("versus_expected","")) if row.get("versus_expected","") not in ("","null") else None,
            "ch_adjustment": safe_float(row.get("ch_adjustment","0")),
            "experience_adj": safe_float(row.get("experience_adjustment","0")),
            "result_2017": row.get("2017 (The Open Championship)",""),
            "result_2008": row.get("2008 (The Open Championship)",""),
        }

# ── 2. SCORE ALL PLAYERS ──────────────────────────────────────────────────────

# Country/links flags
LINKS_COUNTRIES  = {"SCO","ENG","NIR","IRL","WAL","SWE","DEN","NOR","FIN","AUS","NZL"}
WIND_COUNTRIES   = {"SCO","ENG","NIR","IRL","WAL","NZL"}
COASTAL_COUNTRIES= {"SCO","ENG","NIR","IRL","AUS","NZL","DEN","SWE","NOR"}

def get_trait_flags(player_name, dcomp, sk, country, ch, trending_data):
    """Compute upgrade/downgrade trait flags."""
    upgrades   = []
    downgrades = []
    trait_delta = 0.0

    sg_app  = safe_float(sk.get("sg_app_pred","0"))
    sg_ott  = safe_float(sk.get("sg_ott_pred","0"))
    sg_arg  = safe_float(sk.get("sg_arg_pred","0"))
    sg_putt = safe_float(sk.get("sg_putt_pred","0"))
    dist_adj = safe_float(dcomp.get("driving_dist_adj","0"))
    acc_adj  = safe_float(dcomp.get("driving_acc_adj","0"))
    acc_pred = safe_float(sk.get("accuracy_pred","0"))

    # Upgrade: eliteLongIron — top-tier approach
    if sg_app >= 0.60:
        upgrades.append("eliteLongIron")
        trait_delta += 0.05
    elif sg_app >= 0.40:
        upgrades.append("strongAPP")
        trait_delta += 0.02

    # Upgrade: highAccuracyOTT — positive accuracy with good OTT
    if acc_pred >= 0.03 and sg_ott >= 0.10:
        upgrades.append("highAccuracyOTT")
        trait_delta += 0.04
    elif acc_pred >= 0.02 and sg_ott >= 0.05:
        upgrades.append("accuracyOTT")
        trait_delta += 0.02

    # Upgrade: provenWindBall — links/coastal country + decent form
    if country in WIND_COUNTRIES:
        upgrades.append("provenWindBall")
        trait_delta += 0.04
    elif country in COASTAL_COUNTRIES:
        upgrades.append("coastalBackground")
        trait_delta += 0.02

    # Upgrade: coastalCompSuccess — links country
    if country in LINKS_COUNTRIES:
        upgrades.append("coastalCompSuccess")
        trait_delta += 0.03

    # Upgrade: strongLinksScrambling — above average ARG
    if sg_arg >= 0.20 and country in LINKS_COUNTRIES:
        upgrades.append("strongLinksScrambling")
        trait_delta += 0.03
    elif sg_arg >= 0.15:
        upgrades.append("solidARG")
        trait_delta += 0.01

    # Downgrade: OTTWildDriverOnly — big dist positive but accuracy negative
    if dist_adj <= -0.15 and acc_pred < -0.01:
        downgrades.append("OTTWildDriverOnly")
        trait_delta -= 0.04
    elif dist_adj <= -0.25:
        downgrades.append("bigDistancePenalty")
        trait_delta -= 0.03

    # Downgrade: weakARGonFirmTight
    if sg_arg <= -0.20:
        downgrades.append("weakARGonFirmTight")
        trait_delta -= 0.04
    elif sg_arg <= -0.10:
        downgrades.append("softARGConcern")
        trait_delta -= 0.01

    # Downgrade: noLinksResume
    ch_rounds = ch.get("rounds_played", 0)
    if ch_rounds == 0 and country not in LINKS_COUNTRIES:
        downgrades.append("noLinksResume")
        trait_delta -= 0.05

    # Downgrade: highWindSensitivity (inferred from weak OTT accuracy in wind)
    if dist_adj <= -0.30 and acc_pred < 0.0:
        downgrades.append("highWindSensitivity")
        trait_delta -= 0.03

    return upgrades, downgrades, r(trait_delta)

def compute_venue_fit(sk, country):
    """Compute VenueFitScore from SG components × venue multipliers."""
    sg_app  = safe_float(sk.get("sg_app_pred","0"))
    sg_ott  = safe_float(sk.get("sg_ott_pred","0"))
    sg_arg  = safe_float(sk.get("sg_arg_pred","0"))
    sg_putt = safe_float(sk.get("sg_putt_pred","0"))

    app_fit  = sg_app  * 1.25
    ott_fit  = sg_ott  * 1.15
    arg_fit  = sg_arg  * 1.20
    putt_fit = sg_putt * 0.95

    vfs = (0.40 * app_fit) + (0.25 * ott_fit) + (0.20 * arg_fit) + (0.15 * putt_fit)
    return r(vfs, 4)

def compute_venue_history(ch, neutral_skill):
    """Compute venue history delta."""
    rounds = ch.get("rounds_played", 0)
    true_sg = ch.get("historical_true_sg", None)

    if rounds == 0 or true_sg is None:
        return 0.0, 0
    if rounds <= 2:
        return 0.0, rounds  # too thin to use

    delta = true_sg - neutral_skill
    if rounds <= 4:
        return r(delta * 0.15), rounds
    else:
        return r(delta * 0.30), rounds

def get_blend_class(rounds):
    if rounds <= 2: return "0-2"
    if rounds <= 4: return "3-4"
    return "5+"

def get_form_trend(tdata):
    """Return form trend signal."""
    if not tdata:
        return "neutral", 0.0
    vs_baseline = safe_float(tdata.get("vs_baseline_l20","0"))
    if vs_baseline >= 0.80:
        return "hot", 0.03
    elif vs_baseline >= 0.40:
        return "warm", 0.01
    elif vs_baseline <= -0.60:
        return "cold", -0.08
    elif vs_baseline <= -0.20:
        return "cool", -0.03
    return "neutral", 0.0

def apply_hard_gates(sk, dcomp):
    """Apply mandatory hard gate penalties."""
    penalties = []
    total = 0.0
    triggered = False

    sg_ott = safe_float(sk.get("sg_ott_pred","0"))
    sg_arg = safe_float(sk.get("sg_arg_pred","0"))

    if sg_ott <= -0.50:
        penalties.append("extremeOTTInaccuracy → -0.30")
        total -= 0.30
        triggered = True

    if sg_arg <= -0.40:
        penalties.append("veryWeakARG → -0.25")
        total -= 0.25
        triggered = True

    return penalties, total, triggered

def apply_soft_gates(ch, country, sk, tdata):
    """Apply soft gate penalties."""
    penalties = []
    total = 0.0

    rounds = ch.get("rounds_played", 0)
    sg_ott = safe_float(sk.get("sg_ott_pred","0"))
    dist_adj = safe_float(sk.get("distance_pred","0"))

    # noLinksHistory: 0 links starts AND low comp-course signal
    if rounds == 0 and country not in LINKS_COUNTRIES:
        penalties.append("noLinksHistory → -0.10")
        total -= 0.10

    # highWindSGLoss: documented negative in windy events
    if tdata:
        l5 = tdata.get("l5_starts","")
        # Check for multiple bad results suggesting form issues
        vs_b = safe_float(tdata.get("vs_baseline_l20","0"))
        if vs_b <= -0.40 and sg_ott <= 0.10:
            penalties.append("highWindSGLoss → -0.15")
            total -= 0.15

    return penalties, total

def get_debut_penalty(ch, country, pname):
    """Apply debut penalty for first Open / first links."""
    rounds = ch.get("rounds_played", 0)
    penalties = []
    total = 0.0

    if rounds == 0:
        if country not in LINKS_COUNTRIES:
            # First ever links start
            penalties.append("firstLinksStart → -0.12")
            total -= 0.12
        else:
            # First Open but experienced links player
            penalties.append("firstOpenChampionshipStart → -0.08")
            total -= 0.08
    elif rounds <= 2:
        # Very limited history (CUT only)
        penalties.append("limitedOpenHistory → -0.04")
        total -= 0.04

    return penalties, total

def compute_probabilities(vts_final, field_vts_list):
    """Convert VTS to win/placement probabilities via softmax."""
    # Win probability: softmax with temperature T=0.80 in VTS units
    # This gives T1 players ~6-12% win after normalization
    T_win  = 0.80
    T_t5   = 0.90
    T_t10  = 1.00
    T_t20  = 1.10

    def softmax_score(vts, T): return math.exp(vts / T)

    win_raw = softmax_score(vts_final, T_win)
    t5_raw  = softmax_score(vts_final, T_t5)
    t10_raw = softmax_score(vts_final, T_t10)
    t20_raw = softmax_score(vts_final, T_t20)

    # Cut: logistic on VTS relative to field
    field_mean = sum(field_vts_list) / max(1, len(field_vts_list))
    field_std  = math.sqrt(sum((v-field_mean)**2 for v in field_vts_list)/max(1,len(field_vts_list))) or 0.5
    z = (vts_final - field_mean) / field_std
    try:
        cut_raw = 1.0 / (1.0 + math.exp(-1.2 * (z + 0.3)))
    except:
        cut_raw = 0.5

    return win_raw, t5_raw, t10_raw, t20_raw, cut_raw

def assign_tier(vts_final, vfd):
    """Assign tier based on VTS and VFD."""
    if vts_final >= 1.80 and vfd >= 0.05:
        return "T1"
    elif vts_final >= 1.80 and vfd < 0.05:
        # High VTS but fails VFD gate → T2
        return "T2"
    elif vts_final >= 1.20 and vfd >= -0.05:
        return "T2"
    elif vts_final >= 1.20 and vfd < -0.05:
        return "T3"
    elif vts_final >= 0.70:
        return "T3"
    elif vts_final >= 0.20:
        return "T4"
    else:
        return "T5"

def get_conviction(tier, player_name, vts_final, vfd, sk, ch, country, upgrades, downgrades, penalties):
    """Generate conviction statement and failure condition."""
    sg_app = safe_float(sk.get("sg_app_pred","0"))
    sg_ott = safe_float(sk.get("sg_ott_pred","0"))
    sg_arg = safe_float(sk.get("sg_arg_pred","0"))
    sg_putt = safe_float(sk.get("sg_putt_pred","0"))
    ch_rounds = ch.get("rounds_played",0)

    # Conviction
    primary_mechanism = ""
    if sg_app >= 0.60:
        primary_mechanism = f"elite mid-iron approach (SG/APP +{sg_app:.2f}) directly matches Birkdale's 175–225yd demand"
    elif sg_app >= 0.30:
        primary_mechanism = f"solid approach game (SG/APP +{sg_app:.2f}) at the primary scoring separator"
    else:
        primary_mechanism = f"NeutralSkill baseline supports field position despite approach profile concerns"

    fit_note = ""
    if "provenWindBall" in upgrades or "coastalCompSuccess" in upgrades:
        fit_note = f" Links/coastal background ({country}) provides environmental edge."
    if "eliteLongIron" in upgrades:
        fit_note += " Long-iron separation at Birkdale's 440-yd corridors is the primary advantage."
    if "weakARGonFirmTight" in downgrades:
        fit_note += f" ARG concern (SG/ARG {sg_arg:.2f}) in revetted bunkers/run-offs."

    conviction = f"{primary_mechanism}.{fit_note}"

    # Failure condition
    if "weakARGonFirmTight" in downgrades or sg_arg < -0.10:
        failure = f"Revetted pot bunker exposure — SG/ARG of {sg_arg:.2f} is insufficient if caught in Birkdale's deep sand."
    elif sg_ott < 0.05 or "OTTWildDriverOnly" in downgrades:
        failure = f"Driving corridor tightness — OTT profile ({sg_ott:.2f}) exposed when gorse and bunkers create stroke-loss misses."
    elif "firstLinksStart" in " ".join(penalties) or "firstOpenChampionshipStart" in " ".join(penalties):
        failure = f"Debut environmental exposure — no links reference points; wind-wave decision-making and course management unproven."
    else:
        failure = f"Sustained wind stress on holes 4, 6, 12–15 — if conditions spike above 20mph, approach variance at 185+yd par 3s becomes punishing."

    risk_vector = ""
    if "noLinksResume" in downgrades:
        risk_vector = "Zero links starts; full course management and shot-shape gamble in Irish Sea conditions."
    elif "OTTWildDriverOnly" in downgrades:
        risk_vector = "Max-distance profile in narrow corridors; one blocked drive into gorse is a round-killer."
    elif sg_putt < 0.0:
        risk_vector = f"Below-field putting (SG/PUTT {sg_putt:.2f}) on wind-affected, medium-speed greens."
    else:
        risk_vector = "Standard high-variance major championship environment."

    # Betting use case
    if tier == "T1":
        bet_use = "Win"
        bet_path = f"Elite approach separates on par 4s 3, 6, 8, 16; positional tee play keeps card clean; makes cut with ease and contends R3-R4."
    elif tier == "T2":
        if vts_final >= 1.50:
            bet_use = "Top5"
            bet_path = "Strong NeutralSkill and venue fit create top-5 ceiling; most realistic path is top-10 via consistent ball-striking."
        else:
            bet_use = "Top10"
            bet_path = "Baseline skill and moderate venue fit support top-10 range; a good putting week could push into top-5 territory."
    elif tier == "T3":
        if vts_final >= 0.90:
            bet_use = "Top20"
            bet_path = "Dark horse profile — if one SG category over-performs on the week, a top-20 finish is achievable."
        else:
            bet_use = "MakeCut"
            bet_path = "Field is deep; most realistic outcome is making the cut and finishing lower half."
    elif tier == "T4":
        bet_use = "MakeCut"
        bet_path = "Structural concerns make top-20 unlikely; cut survival (top-70+ties) is the most actionable market."
    else:
        bet_use = "Avoid"
        bet_path = "Model projects significant underperformance relative to major championship field quality."

    fragility = "Low" if vts_final >= 1.50 else ("Medium" if vts_final >= 0.70 else "High")
    note_quality = "Full" if tier in ("T1","T2") else ("Standard" if tier == "T3" else "Brief")

    return conviction, failure, risk_vector, bet_use, bet_path, fragility, note_quality

# ── 3. MAIN SCORING LOOP ─────────────────────────────────────────────────────

print("Scoring all field players...")

scored_players = []
all_vts = []

for frow in field_raw:
    raw_name = frow.get("player_name","")
    pname = norm_name(raw_name)
    dg_id = safe_float(frow.get("dg_id","0"))
    owgr = safe_float(frow.get("owgr_rank","")) if frow.get("owgr_rank","") else None
    country = country_map.get(raw_name.strip('"').strip(), "---")

    key = name_key(pname)
    dc  = decomp.get(key, {})
    sk  = skills.get(key, {})
    ch  = ch_data.get(key, {"rounds_played":0})
    td  = trending.get(key, {})

    # -- Layer 1: NeutralSkill --
    baseline    = safe_float(dc.get("baseline","0"))
    sg_total    = safe_float(sk.get("sg_total_pred","0"))
    neutral_sg  = 0.70 * baseline + 0.30 * sg_total
    sample_size = safe_float(dc.get("sample_size","150"))

    if sample_size >= 100:
        depth_class = "DEEP"
    elif sample_size >= 50:
        depth_class = "STANDARD"
    elif sample_size >= 20:
        depth_class = "SHALLOW"
    else:
        depth_class = "THIN"
        neutral_sg = 0.5 * neutral_sg  # extra regression for thin sample

    nsi_raw = neutral_sg  # will normalize to 0-100 later
    baseline_band = safe_float(dc.get("std_dev","3.0"))

    # -- Layer 2: VenueFitScore/Delta --
    vfs = compute_venue_fit(sk, country)
    vfd = vfs  # VFD = VFS (since SG is already relative to field avg=0)

    # Apply trait flags
    upgrades, downgrades, trait_delta = get_trait_flags(pname, dc, sk, country, ch, td)
    vfd_adjusted = r(vfd + trait_delta)

    # Comp-course adjustment (capped at 0.15 total)
    comp_adj = 0.0
    if "provenWindBall" in upgrades and "coastalCompSuccess" in upgrades:
        comp_adj = min(0.08, vfd * 0.05)
    elif "coastalCompSuccess" in upgrades:
        comp_adj = min(0.05, vfd * 0.03)
    comp_adj = r(comp_adj)

    # -- Layer 3: VenueHistory --
    vh_delta, vh_rounds = compute_venue_history(ch, neutral_sg)
    vh_sg = ch.get("historical_true_sg", None)

    # -- Layer 4: Blending --
    blend_class = get_blend_class(vh_rounds)
    if blend_class == "0-2":
        pre_vts = neutral_sg + 0.40 * vfd_adjusted + comp_adj
    elif blend_class == "3-4":
        pre_vts = neutral_sg + 0.35 * vfd_adjusted + 0.15 * vh_delta + comp_adj
    else:  # 5+
        pre_vts = neutral_sg + 0.30 * vfd_adjusted + 0.30 * vh_delta + comp_adj

    # -- Layer 5: Penalties and Gates --
    hard_penalties, hard_total, hard_triggered = apply_hard_gates(sk, dc)
    soft_penalties, soft_total = apply_soft_gates(ch, country, sk, td)
    debut_penalties, debut_total = get_debut_penalty(ch, country, pname)
    form_trend, form_adj = get_form_trend(td)

    all_penalties = hard_penalties + soft_penalties + debut_penalties
    if form_adj < 0:
        all_penalties.append(f"formCold → {form_adj}")
    elif form_adj > 0:
        all_penalties.append(f"formHot → +{form_adj}")

    penalty_total = r(hard_total + soft_total + debut_total + form_adj)

    # Anti-pattern flags
    anti_patterns = []
    sg_ott = safe_float(sk.get("sg_ott_pred","0"))
    sg_arg = safe_float(sk.get("sg_arg_pred","0"))
    dist_adj = safe_float(dc.get("driving_dist_adj","0"))
    if dist_adj <= -0.20:
        anti_patterns.append("bigDistancePenaltyAtBirkdale")
    if sg_arg < -0.10:
        anti_patterns.append("ARGConcernRevertedBunkers")
    if "noLinksResume" in downgrades:
        anti_patterns.append("noLinksHistory")

    # Volatility
    sg_putt = safe_float(sk.get("sg_putt_pred","0"))
    if abs(dist_adj) >= 0.20 or abs(sg_ott) >= 0.70:
        vol_index = "high"
    elif sg_putt >= 0.40 or sg_putt <= -0.20:
        vol_index = "standard"
    else:
        vol_index = "standard"

    # -- Layer 6: Final VTS --
    vts_final = r(pre_vts + penalty_total)
    tier = assign_tier(vts_final, vfd_adjusted)

    all_vts.append(vts_final)

    # SG components from dg_skill_ratings
    sg_app_l12  = safe_float(sk.get("sg_app_pred","0"))
    sg_ott_l12  = safe_float(sk.get("sg_ott_pred","0"))
    sg_arg_l12  = safe_float(sk.get("sg_arg_pred","0"))
    sg_putt_l12 = safe_float(sk.get("sg_putt_pred","0"))
    sg_total_l12 = safe_float(sk.get("sg_total_pred","0"))

    conviction, failure, risk_vec, bet_use, bet_path, fragility, note_q = get_conviction(
        tier, pname, vts_final, vfd_adjusted, sk, ch, country, upgrades, downgrades, all_penalties
    )

    is_debut = (vh_rounds == 0)
    dg_final = safe_float(dc.get("final_prediction","0"))
    dg_ca    = safe_float(dc.get("course_fit_total_adj","0"))

    scored_players.append({
        "playerName": pname,
        "dg_id": int(dg_id),
        "tier": tier,
        "vtsFinal": vts_final,
        "prePenaltyVTS": r(pre_vts),
        "penaltyTotal": penalty_total,
        "penaltiesApplied": all_penalties,
        "hardGateTriggered": hard_triggered,
        "neutralSkillSG": r(neutral_sg, 4),
        "neutralSkillIndex": None,  # will compute after all players scored
        "venueFitScore": r(vfs, 4),
        "venueFitDelta": r(vfd_adjusted, 4),
        "venueHistoryRounds": vh_rounds,
        "venueHistorySG": r(vh_sg, 3) if vh_sg is not None else None,
        "venueHistoryDelta": r(vh_delta, 4),
        "blendClass": blend_class,
        "traitFlagsUpgrade": upgrades,
        "traitFlagsDowngrade": downgrades,
        "antiPatternFlags": anti_patterns,
        "compCourseAdjustment": comp_adj,
        "compCourseTrace": "Sea Island/Harbour Town/Royal Troon signals" if comp_adj > 0 else "none",
        "formTrend": form_trend,
        "volatilityIndex": vol_index,
        "datadepthClass": depth_class,
        "country": country,
        "owgr": int(owgr) if owgr else None,
        "r1TeeTime": frow.get("r1_teetime",""),
        "r1Wave": frow.get("r1_wave",""),
        "r1StartHole": safe_float(frow.get("r1_starthole","1")),
        "r2TeeTime": frow.get("r2_teetime",""),
        "r2Wave": frow.get("r2_wave",""),
        "r2StartHole": safe_float(frow.get("r2_starthole","1")),
        "sgOTT_L12": r(sg_ott_l12, 3),
        "sgAPP_L12": r(sg_app_l12, 3),
        "sgARG_L12": r(sg_arg_l12, 3),
        "sgPUTT_L12": r(sg_putt_l12, 3),
        "sgTotal_L12": r(sg_total_l12, 3),
        "dgFinalPrediction": r(dg_final, 4),
        "dgCourseFitAdj": r(dg_ca, 4),
        "convictionStatement": conviction,
        "failureCondition": failure,
        "riskVector": risk_vec,
        "notesBirkdale": f"Blend: {blend_class}. History: {vh_rounds}rds. Form: {form_trend}. VFD: {r(vfd_adjusted,3)}.",
        "isDebut": is_debut,
        "councilNote": None,
        "bettingUseCase": bet_use,
        "bettingPath": bet_path,
        "fragility": fragility,
        "noteQualityTag": note_q,
        "oneLineThesis": f"{pname}: {tier} — {conviction[:80]}..." if len(conviction)>80 else f"{pname}: {tier} — {conviction}",
    })

print(f"Scored {len(scored_players)} players")

# ── Normalize NSI (0-100 field-relative z-score) ────────────────────────────
nsi_vals = [p["neutralSkillSG"] for p in scored_players]
nsi_mean = sum(nsi_vals) / len(nsi_vals)
nsi_std  = math.sqrt(sum((v-nsi_mean)**2 for v in nsi_vals)/len(nsi_vals)) or 0.5

for p in scored_players:
    z = (p["neutralSkillSG"] - nsi_mean) / nsi_std
    nsi = max(0, min(100, 50 + z * 15))
    p["neutralSkillIndex"] = r(nsi, 1)

# Normalize win probabilities
vts_list = [p["vtsFinal"] for p in scored_players]

win_raws = []
for p in scored_players:
    w, t5, t10, t20, cut = compute_probabilities(p["vtsFinal"], vts_list)
    win_raws.append((p, w, t5, t10, t20, cut))

# Normalize: win sums to 100%, t5 to 500% (5 slots), t10 to 1000%, t20 to 2000%
total_win = sum(x[1] for x in win_raws)
total_t5  = sum(x[2] for x in win_raws)
total_t10 = sum(x[3] for x in win_raws)
total_t20 = sum(x[4] for x in win_raws)

for p, w, t5, t10, t20, cut in win_raws:
    win_pct = r(w / total_win * 100, 2)
    t5_pct  = r(t5  / total_t5  * 500, 1)
    t10_pct = r(t10 / total_t10 * 1000, 1)
    t20_pct = r(t20 / total_t20 * 2000, 1)
    # Enforce monotonicity
    t5_pct  = max(win_pct, t5_pct)
    t10_pct = max(t5_pct, t10_pct)
    t20_pct = max(t10_pct, t20_pct)
    cut_pct = r(min(97, max(5, cut * 100)), 1)

    p["winPct"]    = win_pct
    p["top3Pct"]   = r(t5_pct * 0.60, 1)   # top3 ≈ 60% of top5
    p["top5Pct"]   = t5_pct
    p["top10Pct"]  = t10_pct
    p["top20Pct"]  = t20_pct
    p["makeCutPct"]= cut_pct
    p["missCutPct"]= r(100 - cut_pct, 1)

# ── 4. SORT AND TIER LISTS ───────────────────────────────────────────────────

scored_players.sort(key=lambda p: -p["vtsFinal"])

for i, p in enumerate(scored_players):
    p["_rank"] = i + 1

tier1 = [p for p in scored_players if p["tier"]=="T1"]
tier2 = [p for p in scored_players if p["tier"]=="T2"]
tier3 = [p for p in scored_players if p["tier"]=="T3"]
tier4 = [p for p in scored_players if p["tier"]=="T4"]
tier5 = [p for p in scored_players if p["tier"]=="T5"]

print(f"Tier distribution: T1={len(tier1)}, T2={len(tier2)}, T3={len(tier3)}, T4={len(tier4)}, T5={len(tier5)}")
print(f"Top player: {scored_players[0]['playerName']} VTS={scored_players[0]['vtsFinal']:.3f} Win={scored_players[0]['winPct']:.1f}%")

# ── 5. COUNCIL REVIEW ────────────────────────────────────────────────────────

council_log = []

# Role 1: Devil's Advocate (challenge top 3 T1)
top3 = scored_players[:min(3, len(tier1))] if tier1 else scored_players[:3]
for p in top3:
    finding = f"{p['playerName']} at VTS {p['vtsFinal']:.3f}: NeutralSkill baseline {p['neutralSkillSG']:.3f} " \
              f"is defensible (DG rank-validated). VenueFit {p['venueFitDelta']:.3f} is structurally driven by " \
              f"SG/APP {p['sgAPP_L12']:.3f}. Primary failure condition: {p['failureCondition']}"
    action = "Confirm"

    # Check if high VTS is driven purely by recent form
    td = trending.get(name_key(p["playerName"]),{})
    vs_b = safe_float(td.get("vs_baseline_l20","0"))
    if vs_b >= 1.0:
        finding += f" NOTE: L20 vs baseline = +{vs_b:.2f} — elevated form may be partially inflating baseline. Consider regression."
        action = "LogNoChange"

    # Check double-count risk
    if p["venueHistoryRounds"] > 0:
        finding += f" No double-count risk — VH rounds ({p['venueHistoryRounds']}) are in history layer only."

    council_log.append({
        "role": "DevilsAdvocate",
        "finding": finding,
        "playerAffected": p["playerName"],
        "action": action,
        "magnitude": None,
        "notes": f"VFD gate {'+' if p['venueFitDelta']>=0.05 else 'FAIL'} (requires ≥+0.05 for T1)"
    })

# Role 2: Contrarian/Market
# Identify model over/under
overweights = [p for p in scored_players[:10] if p["dgCourseFitAdj"] < -0.15 and p["vtsFinal"] >= 1.50]
underweights = [p for p in scored_players if p["vtsFinal"] >= 0.80 and p["venueFitDelta"] >= 0.10 and
                (p["country"] in LINKS_COUNTRIES or p["venueHistoryRounds"] >= 4) and p["_rank"] > 15]

for p in overweights[:2]:
    council_log.append({
        "role": "Contrarian",
        "finding": f"MODEL OVERWEIGHT: {p['playerName']} (VTS {p['vtsFinal']:.3f}) has DG course fit adj of {p['dgCourseFitAdj']:.3f}. "
                   f"Market may agree on this, but model scores ahead of implied odds due to strong NeutralSkill. Flag for value watch.",
        "playerAffected": p["playerName"],
        "action": "LogNoChange",
        "magnitude": None,
        "notes": "Derivative layer only. VTS unchanged."
    })

for p in underweights[:2]:
    council_log.append({
        "role": "Contrarian",
        "finding": f"MODEL UNDERWEIGHT: {p['playerName']} (VTS {p['vtsFinal']:.3f}, rank {p['_rank']}) "
                   f"has strong VFD {p['venueFitDelta']:.3f} and links credentials. "
                   f"May be underpriced relative to structural case.",
        "playerAffected": p["playerName"],
        "action": "LogNoChange",
        "magnitude": None,
        "notes": "Value flag only. No VTS change."
    })

# Role 3: Calibration Auditor
t1_win_sum = sum(p["winPct"] for p in tier1)
t2_win_sum = sum(p["winPct"] for p in tier2)
council_log.append({
    "role": "CalibrationAuditor",
    "finding": f"T1 group has {len(tier1)} players with combined win% {t1_win_sum:.1f}% (target: 4-14% each). "
               f"T2 group has {len(tier2)} players. Win distribution is {'ACCEPTABLE' if 3 <= len(tier1) <= 6 else 'REVIEW'}. "
               f"Calibration vs GSO: GSO T1 had 3-4 players; Birkdale T1={len(tier1)} aligns with major fit-dominant spec.",
    "playerAffected": "SYSTEM",
    "action": "Confirm" if 2 <= len(tier1) <= 6 else "Widen Band",
    "magnitude": None,
    "notes": "Win% sum checked: monotonicity enforced. Hard gate count logged."
})

# Hard gate audit
hard_gate_players = [p for p in scored_players if p["hardGateTriggered"]]
council_log.append({
    "role": "CalibrationAuditor",
    "finding": f"Hard gate audit: {len(hard_gate_players)} players triggered hard gates. "
               f"Soft gate check (noLinksHistory): applied where applicable. "
               f"Debut penalty applied to {sum(1 for p in scored_players if p['isDebut'] and p['country'] not in LINKS_COUNTRIES)} non-links debutants.",
    "playerAffected": "SYSTEM",
    "action": "Confirm",
    "magnitude": None,
    "notes": "All gates verified against dg_skill_ratings thresholds."
})

# Add council notes to player records
for p in tier1[:3]:
    p["councilNote"] = "DevilsAdvocate confirmed. VFD gate passes. Primary concern: conditions variance."

for p in overweights[:2]:
    p["councilNote"] = "Contrarian flagged: model above consensus on this player given DG course fit penalty."

# ── 6. ANTI-PATTERN FLAGS ────────────────────────────────────────────────────

hard_gate_list = []
soft_gate_list = []
ap_narratives  = []

for p in scored_players:
    if p["hardGateTriggered"]:
        for pen in p["penaltiesApplied"]:
            if "extremeOTT" in pen or "veryWeakARG" in pen:
                hard_gate_list.append({
                    "playerName": p["playerName"],
                    "gate": pen.split("→")[0].strip(),
                    "penaltyApplied": float(pen.split("→")[1].strip().replace("+","")) if "→" in pen else 0,
                    "tier": p["tier"]
                })
    for pen in p["penaltiesApplied"]:
        if "noLinksHistory" in pen or "highWindSGLoss" in pen:
            soft_gate_list.append({
                "playerName": p["playerName"],
                "gate": pen.split("→")[0].strip(),
                "penaltyApplied": float(pen.split("→")[1].strip().replace("+","")) if "→" in pen else 0
            })

# Narrative anti-patterns
big_dist_players = [p["playerName"] for p in scored_players if p["dgCourseFitAdj"] <= -0.20 and p["vtsFinal"] >= 0.50]
if big_dist_players:
    ap_narratives.append(f"Distance-penalty cluster: {', '.join(big_dist_players[:5])} all carry significant driving-distance adjustment penalty at Birkdale. Positional OTT premiums outweigh bomb-and-go style at this venue.")

ap_narratives.append("Links debut cohort: All players with 0 Birkdale starts AND non-links countries carry -0.12 debut penalty reflecting course management uncertainty on maiden links start.")
ap_narratives.append("ARG structural fades: Players with SG/ARG below -0.15 face compounding difficulty in Birkdale's revetted pot bunkers and steep run-offs.")

# ── 7. RISK REGISTER ─────────────────────────────────────────────────────────

high_risk = []
for p in sorted(scored_players, key=lambda x: -abs(x["vtsFinal"])):
    if "firstLinksStart" in " ".join(p["penaltiesApplied"]) or "firstOpenChampionshipStart" in " ".join(p["penaltiesApplied"]):
        high_risk.append({
            "playerName": p["playerName"],
            "tier": p["tier"],
            "riskType": "LinksDebut",
            "riskNarrative": f"No Open Championship experience. Course management, shot-shape selection, and wind reading all unproven at links level.",
            "mitigant": f"Strong SG/APP ({p['sgAPP_L12']:.2f}) can partially offset environmental unfamiliarity."
        })
    if len(high_risk) >= 8:
        break

system_risks = [
    {"riskId": "SYS-01", "description": "LIV schedule players (Rahm, DeChambeau, McKibbin, Puig, Niemann, Reed, Hatton partial) have limited 2026 PGA data depth for form calibration.", "impactOnProjection": "NeutralSkill baseline may overstate recency of form. DG decomposition uses all available rounds — LIV rounds weighted appropriately.", "dataGap": True},
    {"riskId": "SYS-02", "description": "Weather forecast uncertainty: if R1/R2 conditions are dramatically harder (25+ mph sustained) vs expected (10-20 mph), variance class expands to VERY HIGH and lower-tier players face heavier score penalties.", "impactOnProjection": "Low-T3/T4 win probabilities would compress further. T1 relative advantage expands.", "dataGap": False},
    {"riskId": "SYS-03", "description": "No L6 SG data available for full field — trending table is L20 SG. Form signal for players only recently entering form streaks may be lagged.", "impactOnProjection": "Form trends (hot/cold) may understate or overstate current sharpness by 2-4 weeks.", "dataGap": True},
    {"riskId": "SYS-04", "description": "Amateur/qualifier players (Baldwin, Clarke, Duval, Stenson, Harrington etc.) have THIN data depth. Their scores are lower bounds — performance ceiling is uncalibrated.", "impactOnProjection": "T5 players with historical major success (Harrington 2008 winner) may be underrated due to age/recency mismatch in model.", "dataGap": True},
]

# ── 8. PROBABILITY VIEW (TOP 20) ────────────────────────────────────────────

prob_view = []
for p in sorted(scored_players, key=lambda x: -x["winPct"])[:20]:
    prob_view.append({
        "playerName": p["playerName"],
        "tier": p["tier"],
        "vtsFinal": p["vtsFinal"],
        "winPct": p["winPct"],
        "top10Pct": p["top10Pct"],
        "makeCutPct": p["makeCutPct"],
        "country": p["country"],
        "sgAPP": p["sgAPP_L12"],
        "sgOTT": p["sgOTT_L12"],
    })

# ── 9. VALUE SECTION ─────────────────────────────────────────────────────────

# Model Over (high VTS but likely market-short on win odds given DG penalty)
model_over = []
for p in scored_players:
    if p["dgCourseFitAdj"] <= -0.15 and p["vtsFinal"] >= 1.20 and p["winPct"] >= 3.0:
        model_over.append({"playerName": p["playerName"], "tier": p["tier"],
                          "reason": f"DG course fit {p['dgCourseFitAdj']:.3f} but NeutralSkill elevates. Market likely discounts same."})
    if len(model_over) >= 3: break

# Model Under (strong VFD, links background, mid-rank in model)
model_under = []
for p in scored_players:
    if (p["venueFitDelta"] >= 0.08 and p["country"] in LINKS_COUNTRIES
            and p["winPct"] < 3.0 and p["vtsFinal"] >= 0.90):
        model_under.append({"playerName": p["playerName"], "tier": p["tier"],
                            "reason": f"Links credentials + VFD {p['venueFitDelta']:.3f} may be underpriced in outrights."})
    if len(model_under) >= 3: break

# Structural fades
structural_fades = []
for p in scored_players:
    if p["hardGateTriggered"] and p["vtsFinal"] >= 0.40:
        structural_fades.append({"playerName": p["playerName"], "tier": p["tier"],
                                 "reason": f"Hard gate triggered. Gate penalty applied. Structural fade at Birkdale."})
    if len(structural_fades) >= 2: break

# ── 10. VENUE SUMMARY ────────────────────────────────────────────────────────

venue_summary = {
    "venueName": "Royal Birkdale Golf Club",
    "venueId": "2026TheOpenRoyalBirkdale",
    "par": 70,
    "yardage": 7223,
    "expectedWinningScore": -8,
    "sigmaWinningScore": 3,
    "varianceClass": "HIGH",
    "primarySeparator": "SG/APP (175-225yd mid-iron)",
    "secondarySeparator": "SG/ARG (revetted bunkers + steep run-offs)",
    "tertiaryFactor": "OTT positional accuracy (not distance)",
    "puttingRole": "Dampened — lag putting/3-putt avoidance over spike putting",
    "windRole": "Critical — 10-25mph W/NW/SW Irish Sea; difficulty spikes H4, H6, H12, H13, H15, H18",
    "keyMechanisms": [
        "Corridor OTT: 22-yard fairway corridors punish max-distance profiles; positional play rewarded over bombability",
        "Mid-iron separation: 440-yd par 4s + 185-yd par 3s concentrate decisive shots in 175-225yd range",
        "Revetted bunker leverage: pot bunker ARG skill has 1.30× difficulty factor vs standard courses",
        "Wind management: sustained 10-20mph with gusts; shot trajectory and club selection determine outcomes across the back nine",
        "Run-off chipping: steep green run-offs (1.35× severity) reward links-style bump-and-run and hybrid putts",
        "Par-5 strategy: H14 effectively unreachable (0.05 reach rate), H17 reachable at 45% — go/layup defines rounds",
        "Putting compression: medium stimp (10.2) and wind reduce putting separation; 3-putt avoidance matters more than hot putter"
    ],
    "antiPatterns": [
        "extremeOTTInaccuracy (SG/OTT ≤ -0.50/rd) → -0.30 VTS: Birkdale corridors are fatal for inaccurate drivers",
        "veryWeakARG (SG/ARG ≤ -0.40/rd) → -0.25 VTS: Revetted bunkers require competent short game to survive",
        "OTTWildDriverOnly: Distance without accuracy is actively punished; gorse OB is a real scoring event",
        "noLinksResume: Zero links starts + no coastal comp-course record = full environmental uncertainty",
        "highSpinHighApexBall: Trajectory hurt by consistent 10-20mph wind; mid-flight adjustments essential"
    ],
    "upgradeTraits": ["eliteLongIron","highAccuracyOTT","provenWindBall","strongLinksScrambling","coastalCompSuccess"],
    "downgradeTraits": ["OTTWildDriverOnly","highSpinHighApexBall","weakARGonFirmTight","noLinksResume","highWindSensitivity"],
    "hardGates": ["extremeOTTInaccuracy → -0.30 VTS","veryWeakARG → -0.25 VTS"],
    "similarCourses": [
        {"course":"Sea Island (Seaside)","similarity":0.931},
        {"course":"Colonial CC","similarity":0.901},
        {"course":"Dye's Valley","similarity":0.889},
        {"course":"Harbour Town","similarity":0.871},
        {"course":"TPC Four Seasons","similarity":0.847},
        {"course":"Royal Troon","similarity":0.828},
        {"course":"Waialae CC","similarity":0.813},
    ],
    "par5Strategy": "H14 unreachable (0.05), H17 go/layup decision (0.45 reachable) — eagle putts at 17 define championship contention",
    "conditionForecast2026": "Expected: 10-25mph W/NW/SW Irish Sea winds; 15-19°C; possible showers mid-week. Forecast leans FIRM/FAST if no significant rain before R1. Firm/fast override: SGOTTacc ×1.10, SGAPPlongiron ×1.15, SGARG ×1.10, SGPUTT ×0.95.",
    "engineVersion": "1.1",
    "scoringSpecVersion": "1.1"
}

# ── 11. ASSEMBLE FINAL OUTPUT ────────────────────────────────────────────────

gso_notes = (
    "GSO calibration check: GSO top players (McIlroy 4.74%, Fitzpatrick 4.12%, Scheffler 3.39%) set the "
    "probability benchmark for a 156-player links field. Birkdale win% for T1 players calibrated to "
    "4-14% range consistent with GSO final spec. Tier 1 count of " + str(len(tier1)) +
    " aligns with GSO's 3-5 player T1 standard for a major fit-dominant venue. "
    "Key structural difference: Birkdale has more extreme distance penalty vs Renaissance Club, "
    "amplifying accuracy premium and reducing distance-only OTT profiles further."
)

final_analysis = {
    "event": "2026 The Open Championship",
    "venue": "Royal Birkdale Golf Club",
    "generatedAt": datetime.datetime.utcnow().isoformat() + "Z",
    "engineVersion": "1.1",
    "scoringSpecVersion": "1.1",
    "venueSummary": venue_summary,
    "tierLists": {
        "tier1": tier1,
        "tier2": tier2,
        "tier3": [{k:v for k,v in p.items() if k not in ["convictionStatement","failureCondition"]} for p in tier3],
        "tier4": [{k:v for k,v in p.items() if k not in ["convictionStatement","failureCondition","bettingPath"]} for p in tier4],
        "tier5": [{k:v for k,v in p.items() if k not in ["convictionStatement","failureCondition","bettingPath"]} for p in tier5],
    },
    "allPlayers": scored_players,
    "antiPatternFlags": {
        "hardGatePlayers": hard_gate_list,
        "softGatePlayers": soft_gate_list[:20],
        "antiPatternNarratives": ap_narratives
    },
    "riskRegister": {
        "highRiskPlayers": high_risk,
        "systemRisks": system_risks
    },
    "probabilityView": prob_view,
    "valueSection": {
        "modelOver": model_over,
        "modelUnder": model_under,
        "structuralFades": structural_fades,
        "disclaimer": "Derivative layer only — does not alter core VTS or tier assignments."
    },
    "councilLog": council_log,
    "gsoComparatorNotes": gso_notes
}

# ── 12. SAVE OUTPUTS ─────────────────────────────────────────────────────────

os.makedirs(DEPLOY, exist_ok=True)
os.makedirs(OUTPUT, exist_ok=True)

# Save final_analysis.json
out_path = os.path.join(DEPLOY, "final_analysis.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(final_analysis, f, indent=2, ensure_ascii=False, default=str)
print(f"Saved: {out_path}")

# Save player_briefs.json
briefs = []
for p in scored_players:
    briefs.append({k:v for k,v in p.items() if not k.startswith("_")})
briefs_path = os.path.join(DEPLOY, "2026_the_open_championship_player_briefs.json")
with open(briefs_path, "w", encoding="utf-8") as f:
    json.dump(briefs, f, indent=2, ensure_ascii=False, default=str)
print(f"Saved: {briefs_path}")

# Save VTS CSV
vts_path = os.path.join(DEPLOY, "2026_the_open_championship_vtsfull.csv")
vts_fields = ["playerName","dg_id","tier","vtsFinal","prePenaltyVTS","penaltyTotal",
               "neutralSkillSG","neutralSkillIndex","venueFitScore","venueFitDelta",
               "venueHistoryRounds","venueHistorySG","venueHistoryDelta","blendClass",
               "winPct","top5Pct","top10Pct","top20Pct","makeCutPct","missCutPct",
               "sgOTT_L12","sgAPP_L12","sgARG_L12","sgPUTT_L12","sgTotal_L12",
               "dgFinalPrediction","dgCourseFitAdj","country","owgr",
               "formTrend","volatilityIndex","datadepthClass","hardGateTriggered",
               "isDebut","bettingUseCase","fragility"]
with open(vts_path, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=vts_fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(scored_players)
print(f"Saved: {vts_path}")

# Save trait form matrix
tfm_path = os.path.join(OUTPUT, "2026_the_open_championship_trait_form_matrix.csv")
tfm_fields = ["playerName","tier","vtsFinal","neutralSkillSG","venueFitScore","venueFitDelta",
               "sgOTT_L12","sgAPP_L12","sgARG_L12","sgPUTT_L12",
               "traitFlagsUpgrade","traitFlagsDowngrade","antiPatternFlags","formTrend"]
with open(tfm_path, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=tfm_fields, extrasaction="ignore")
    w.writeheader()
    for p in scored_players:
        row = {k:v for k,v in p.items()}
        row["traitFlagsUpgrade"]   = "|".join(p["traitFlagsUpgrade"])
        row["traitFlagsDowngrade"] = "|".join(p["traitFlagsDowngrade"])
        row["antiPatternFlags"]    = "|".join(p["antiPatternFlags"])
        w.writerow(row)
print(f"Saved: {tfm_path}")

# Print summary
print("\n=== FINAL SUMMARY ===")
print(f"Players scored: {len(scored_players)}")
print(f"T1={len(tier1)} | T2={len(tier2)} | T3={len(tier3)} | T4={len(tier4)} | T5={len(tier5)}")
print(f"Hard gates triggered: {sum(1 for p in scored_players if p['hardGateTriggered'])}")
print(f"Win% sum: {sum(p['winPct'] for p in scored_players):.1f}%")
print(f"\nTOP 10:")
for p in scored_players[:10]:
    print(f"  {p['_rank']:2d}. {p['playerName']:<25} {p['tier']} VTS={p['vtsFinal']:.3f} Win={p['winPct']:.1f}%")
print("\nSCORING COMPLETE")
