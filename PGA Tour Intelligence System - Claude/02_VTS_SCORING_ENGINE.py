"""
PGA Tour Intelligence System — VTS Scoring Engine
Version: June 2026

PURPOSE:
Score a full PGA Tour field against a locked venue DNA profile.
Outputs: VTS score per player, tier assignment, flag summary, 
         ordered rankings with full trace.

INPUTS REQUIRED (load from DataGolf CSVs):
  - system_rankings.csv     : Player name, world rank, OWGR
  - true_sg.csv             : tSG composite + category splits (OTT, APP, ARG, T2G, PUTT)
  - recent_form.csv         : RF index (quality-adjusted)
  - l5_event_results.csv    : Last 5 events with SG splits per event
  - venue_history.csv       : Career SG at this specific venue (if available)
  - dk_salaries.csv         : DraftKings salary for lineup optimizer

HOW TO USE:
  1. Set VENUE_DNA to the active venue profile dictionary
  2. Load player data CSVs
  3. Run score_field()
  4. Run build_dk_lineups() for DK optimization
  5. Print or export results

VENUE DNA TEMPLATE:
  Edit the VENUE_DNA dict below for each new tournament.
  Load from the venue's Intelligence Update .md file.
"""

import pandas as pd
import numpy as np
from itertools import combinations

# =============================================================================
# VENUE DNA — EDIT THIS BLOCK FOR EACH TOURNAMENT
# =============================================================================
# Load from the active venue's Intelligence Update file

VENUE_DNA = {
    "venue": "TEMPLATE — REPLACE WITH ACTIVE VENUE",
    "event": "Tournament Name",
    "surface": "bentgrass",  # or "bermuda", "poa_annua", "mixed"
    
    # Trait Weight Matrix — must sum to 100
    "weights": {
        "SG_APP":     30,   # SG: Approach (venue-specific emphasis)
        "SG_OTT":     20,   # SG: Off-the-Tee (accuracy-weighted at this venue)
        "SG_PUTT":    18,   # SG: Putting — surface-specific ONLY
        "SG_ARG":     10,   # SG: Around-the-Green (immovable on weather adjustment)
        "SG_T2G":     10,   # SG: Tee-to-Green composite
        "PAR5":        6,   # Par-5 efficiency
        "FORM":       10,   # Recent form (quality-adjusted, decay-weighted)
        # Add venue-specific weights here
        # Weights MUST sum to 100
    },
    
    # Anti-patterns: {name: {full_penalty, partial_penalty, trigger_fn}}
    # trigger_fn takes a player_row dict and returns True if triggered
    "anti_patterns": {
        # Example: bomb_and_spray
        # "bomb_and_spray": {
        #     "full_penalty": -7,
        #     "partial_penalty": -4,
        #     "description": "Top-quartile OTT distance + below-median accuracy",
        #     "condition_soft_multiplier": 0.70,  # reduces 30% on soft week
        # },
    },
    
    # Debut penalty configuration
    "debut_penalty": {
        "standard": -11,            # Default first-time starter penalty
        "elite_no_surface_data": -9, # World rank <30, no surface-specific putting data
        "comp_specialist": -6,      # Has win/T5 at high-similarity comp course
        "partial_history": -5,      # 1-4 prior rounds at this venue
    },
    
    # Comp-course framework: {venue_name: {similarity, max_adj, trigger}}
    "comp_courses": {
        # Example:
        # "harbour_town": {"similarity": 0.85, "max_adj": 4},
        # "sedgefield": {"similarity": 0.75, "max_adj": 3},
    },
    
    # Scoring band configuration
    "scoring_bands": {
        "dry_firm": {"low": -8, "high": -11},    # Winning score range
        "soft_wet": {"low": -12, "high": -15},
        "w_firm": 0.65,     # Default weather blend weight (firm)
        "w_soft": 0.35,     # Default weather blend weight (soft)
        # Override w_soft to 0.60 only if multi-day rain confirmed
    },
    
    # Finish probability by tier
    "finish_probs": {
        1: {"win": 0.15, "t10": 0.45, "t20": 0.25, "t30": 0.10, "mc": 0.05},
        2: {"win": 0.05, "t10": 0.25, "t20": 0.30, "t30": 0.25, "mc": 0.15},
        3: {"win": 0.01, "t10": 0.08, "t20": 0.20, "t30": 0.35, "mc": 0.36},
        4: {"win": 0.00, "t10": 0.03, "t20": 0.10, "t30": 0.25, "mc": 0.62},
        5: {"win": 0.00, "t10": 0.01, "t20": 0.04, "t30": 0.15, "mc": 0.80},
    }
}

# =============================================================================
# RESULT QUALITY MULTIPLIER (do not edit — cross-venue engine rule)
# =============================================================================

RESULT_QUALITY_MULTIPLIER = {
    "pga_tour":      1.00,
    "dp_world_tour": 0.90,
    "co_sanctioned": 0.85,
    "liv_golf":      0.60,
    "developmental": 0.50,
    "unknown":       0.75,  # default for unclassified events
}

# =============================================================================
# FORM WINDOW DECAY MODEL (do not edit — cross-engine rule)
# =============================================================================

FORM_DECAY_WEIGHTS = {
    "event_1": 0.35,  # Most recent
    "event_2": 0.25,
    "event_3": 0.10,
    "event_4": 0.10,
    "event_5": 0.10,
    "event_6": 0.10,
}

# =============================================================================
# CORE SCORING FUNCTIONS
# =============================================================================

def apply_result_quality_multiplier(result_score: float, tour_type: str) -> float:
    """Apply result quality multiplier before form window weighting."""
    multiplier = RESULT_QUALITY_MULTIPLIER.get(tour_type.lower(), 0.75)
    return result_score * multiplier


def compute_form_score(events: list) -> float:
    """
    Compute weighted form score from last 6 events.
    
    Args:
        events: list of dicts, each with:
                {'sg_total': float, 'tour_type': str, 'weeks_ago': int}
                Ordered by recency (index 0 = most recent)
    
    Returns:
        float: quality-adjusted, decay-weighted form score
    """
    decay_keys = ["event_1", "event_2", "event_3", "event_4", "event_5", "event_6"]
    total_weight = 0
    weighted_sum = 0
    
    for i, event in enumerate(events[:6]):
        if event.get("sg_total") is None:
            continue
        quality_score = apply_result_quality_multiplier(
            event["sg_total"], 
            event.get("tour_type", "pga_tour")
        )
        weight = FORM_DECAY_WEIGHTS[decay_keys[i]]
        weighted_sum += quality_score * weight
        total_weight += weight
    
    if total_weight == 0:
        return 0.0
    return weighted_sum / total_weight


def apply_single_event_regression(event_split: float, true_sg: float) -> float:
    """
    Cross-venue rule: if event SG split exceeds true SG by >0.5 in any category,
    apply 0.7x multiplier to that split.
    Evidence: Novak APP +0.99 vs tSG +0.81 → reverted R3/R4, T54 Colonial
    """
    if (event_split - true_sg) > 0.5:
        return event_split * 0.7
    return event_split


def compute_vts_score(
    player: dict,
    venue_dna: dict,
    is_debut: bool = False,
    debut_category: str = "standard",
    career_venue_sg: float = None,
    career_venue_starts: int = 0,
    is_soft_conditions: bool = False,
    comp_course_bonus: float = 0.0,
    recent_form_index: float = None,
) -> dict:
    """
    Compute Venue Trait Score for a single player.
    
    Returns dict with:
      - vts_raw: raw score before modifiers
      - vts_final: score after all penalties/bonuses
      - tier: 1–5
      - penalties_applied: list of (name, value, reason)
      - flags: list of active flags
    """
    weights = venue_dna["weights"]
    penalties = []
    flags = []
    
    # --- BASE TRAIT SCORE ---
    # Map player trait values (0–10 scale normalized against field) to weighted score
    trait_score = 0.0
    
    sg_app = player.get("sg_app", 0)
    sg_ott = player.get("sg_ott", 0)
    sg_putt = player.get("sg_putt_surface", player.get("sg_putt", 0))  # Prefer surface-specific
    sg_arg = player.get("sg_arg", 0)
    sg_t2g = player.get("sg_t2g", 0)
    par5 = player.get("par5_sg", 0)
    
    # Apply single-event regression to splits if needed
    true_sg_app = player.get("true_sg_app", sg_app)
    sg_app = apply_single_event_regression(sg_app, true_sg_app)
    
    true_sg_ott = player.get("true_sg_ott", sg_ott)
    sg_ott = apply_single_event_regression(sg_ott, true_sg_ott)
    
    # Normalize to 0–100 scale (field-relative z-score then scale)
    # In practice: pass pre-normalized values from DataGolf percentile ranks (0–100)
    trait_contributions = {
        "SG_APP":  sg_app  * weights.get("SG_APP", 0),
        "SG_OTT":  sg_ott  * weights.get("SG_OTT", 0),
        "SG_PUTT": sg_putt * weights.get("SG_PUTT", 0),
        "SG_ARG":  sg_arg  * weights.get("SG_ARG", 0),
        "SG_T2G":  sg_t2g  * weights.get("SG_T2G", 0),
        "PAR5":    par5    * weights.get("PAR5", 0),
    }
    
    # Form window (use career venue SG if 5+ starts)
    if career_venue_starts >= 5 and career_venue_sg is not None:
        form_score = career_venue_sg  # career venue SG overrides form
        flags.append("CAREER_VENUE_SG_OVERRIDE")
    else:
        form_score = player.get("form_score_adjusted", 0)
    
    trait_contributions["FORM"] = form_score * weights.get("FORM", 0)
    
    vts_raw = sum(trait_contributions.values()) / 10.0  # normalize to 0–100 range
    
    # --- MODIFIERS ---
    vts_modified = vts_raw
    
    # 1. Debut penalty
    if is_debut:
        debut_penalty = venue_dna["debut_penalty"].get(debut_category, -11)
        penalties.append(("DEBUT", debut_penalty, f"First-time starter ({debut_category})"))
        vts_modified += debut_penalty
        flags.append("DEBUT_PENALTY_APPLIED")
    
    # 2. Anti-pattern penalties
    for ap_name, ap_config in venue_dna.get("anti_patterns", {}).items():
        if "trigger_fn" in ap_config:
            trigger_result = ap_config["trigger_fn"](player)
            if trigger_result == "full":
                penalty = ap_config["full_penalty"]
                if is_soft_conditions:
                    penalty = round(penalty * (1 - ap_config.get("soft_reduction", 0.30)))
                penalties.append((ap_name.upper(), penalty, "Full anti-pattern trigger"))
                vts_modified += penalty
                flags.append(f"AP_{ap_name.upper()}_FULL")
            elif trigger_result == "partial":
                penalty = ap_config.get("partial_penalty", ap_config["full_penalty"] // 2)
                if is_soft_conditions:
                    penalty = round(penalty * (1 - ap_config.get("soft_reduction", 0.30)))
                penalties.append((ap_name.upper(), penalty, "Partial anti-pattern trigger"))
                vts_modified += penalty
                flags.append(f"AP_{ap_name.upper()}_PARTIAL")
    
    # 3. Comp-course bonus/penalty
    if comp_course_bonus != 0:
        penalties.append(("COMP_COURSE", comp_course_bonus, "Historical comp performance"))
        vts_modified += comp_course_bonus
    
    # 4. Recent form hard gate (cross-venue rule)
    if recent_form_index is not None:
        if recent_form_index < -0.5:
            vts_modified = min(vts_modified, 64)  # Tier 3 floor
            flags.append("RF_HARD_GATE_TIER3_FLOOR")
            penalties.append(("RF_GATE", 0, f"RF {recent_form_index:.2f} < -0.5 → Tier 3 floor"))
        elif recent_form_index < 0.0:
            rf_penalty = -4
            vts_modified += rf_penalty
            penalties.append(("RF_PENALTY", rf_penalty, f"RF {recent_form_index:.2f} < 0.0 → −4 VTS"))
            flags.append("RF_NEGATIVE_PENALTY")
    
    # 5. Cap at 100
    vts_final = max(0, min(100, vts_modified))
    
    # --- TIER ASSIGNMENT ---
    if vts_final >= 80:
        tier = 1
    elif vts_final >= 65:
        tier = 2
    elif vts_final >= 50:
        tier = 3
    elif vts_final >= 35:
        tier = 4
    else:
        tier = 5
    
    return {
        "vts_raw": round(vts_raw, 1),
        "vts_final": round(vts_final, 1),
        "tier": tier,
        "trait_contributions": {k: round(v, 2) for k, v in trait_contributions.items()},
        "penalties_applied": penalties,
        "flags": flags,
    }


def score_field(players_df: pd.DataFrame, venue_dna: dict, conditions: str = "firm") -> pd.DataFrame:
    """
    Score the full field.
    
    Args:
        players_df: DataFrame with one row per player, columns matching player dict spec
        venue_dna: Active venue DNA dict
        conditions: "firm", "soft", or "mixed"
    
    Returns:
        DataFrame sorted by VTS descending with all scoring columns
    """
    is_soft = (conditions == "soft")
    results = []
    
    for _, player in players_df.iterrows():
        player_dict = player.to_dict()
        
        score_result = compute_vts_score(
            player=player_dict,
            venue_dna=venue_dna,
            is_debut=player_dict.get("is_debut", False),
            debut_category=player_dict.get("debut_category", "standard"),
            career_venue_sg=player_dict.get("career_venue_sg"),
            career_venue_starts=player_dict.get("career_venue_starts", 0),
            is_soft_conditions=is_soft,
            comp_course_bonus=player_dict.get("comp_course_bonus", 0.0),
            recent_form_index=player_dict.get("recent_form_index"),
        )
        
        result_row = {
            "player": player_dict.get("name", "Unknown"),
            "world_rank": player_dict.get("world_rank"),
            "dk_salary": player_dict.get("dk_salary"),
            "vts_raw": score_result["vts_raw"],
            "vts_final": score_result["vts_final"],
            "tier": score_result["tier"],
            "penalties": "; ".join([f"{p[0]}: {p[1]}" for p in score_result["penalties_applied"]]),
            "flags": "; ".join(score_result["flags"]),
        }
        
        # Attach finish probability
        probs = venue_dna["finish_probs"].get(score_result["tier"], venue_dna["finish_probs"][5])
        result_row.update({f"prob_{k}": v for k, v in probs.items()})
        
        results.append(result_row)
    
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values("vts_final", ascending=False).reset_index(drop=True)
    results_df.index += 1  # 1-based ranking
    
    return results_df


# =============================================================================
# DK LINEUP OPTIMIZER (brute-force, 6-player, $50K cap)
# =============================================================================

def build_dk_lineups(
    scored_df: pd.DataFrame,
    salary_cap: int = 50000,
    lineup_count: int = 3,
    max_tier: int = 2,
    dk_floor_ott_sg: float = -0.20,
    course_yards: int = 0,
) -> list:
    """
    Brute-force combinatorial DK lineup optimizer.
    
    Rules enforced:
    - $50,000 salary cap exactly or under
    - 6 players per lineup
    - Filters players below dk_floor_ott_sg at long courses (7200+ yards)
    - Returns top N lineups by projected points
    
    Args:
        scored_df: Output of score_field() with dk_salary column
        salary_cap: Default 50000
        lineup_count: Number of lineups to return
        max_tier: Only include players at or above this tier (default Tier 1+2)
        dk_floor_ott_sg: Minimum OTT SG for courses 7200+ yards
        course_yards: Course yardage (triggers OTT floor if 7200+)
    
    Returns:
        List of lineup dicts with players, total salary, projected points
    """
    # Filter to eligible players
    eligible = scored_df[scored_df["tier"] <= max_tier].copy()
    eligible = eligible.dropna(subset=["dk_salary"])
    eligible["dk_salary"] = eligible["dk_salary"].astype(int)
    
    # Apply DK OTT floor at long courses
    if course_yards >= 7200 and "sg_ott" in eligible.columns:
        before = len(eligible)
        eligible = eligible[eligible["sg_ott"] >= dk_floor_ott_sg]
        removed = before - len(eligible)
        if removed > 0:
            print(f"DK floor rule: removed {removed} players with OTT SG < {dk_floor_ott_sg}")
    
    # Projected DK points (proxy: VTS final score as pts basis)
    # In practice: replace with actual DK pts projection
    eligible["proj_pts"] = eligible["vts_final"] * 2.5  # placeholder multiplier
    
    players = eligible.to_dict("records")
    
    valid_lineups = []
    
    print(f"Evaluating combinations from {len(players)} eligible players...")
    
    for combo in combinations(players, 6):
        total_salary = sum(p["dk_salary"] for p in combo)
        if total_salary > salary_cap:
            continue
        
        total_pts = sum(p["proj_pts"] for p in combo)
        valid_lineups.append({
            "players": [p["player"] for p in combo],
            "salaries": [p["dk_salary"] for p in combo],
            "total_salary": total_salary,
            "projected_pts": round(total_pts, 1),
            "tiers": [p["tier"] for p in combo],
        })
    
    # Sort by projected points descending
    valid_lineups.sort(key=lambda x: x["projected_pts"], reverse=True)
    
    print(f"Valid lineups found: {len(valid_lineups)}")
    print(f"Returning top {lineup_count}")
    
    return valid_lineups[:lineup_count]


# =============================================================================
# OUTPUT FORMATTING
# =============================================================================

def print_tier_rankings(scored_df: pd.DataFrame, venue_name: str) -> None:
    """Print formatted tier rankings to console."""
    print(f"\n{'='*70}")
    print(f"VTS FIELD RANKINGS — {venue_name.upper()}")
    print(f"{'='*70}\n")
    
    for tier_num in range(1, 6):
        tier_labels = {
            1: "TIER 1 — COURSE ARCHITECTS (VTS 80+)",
            2: "TIER 2 — CONTENTION WINDOWS (VTS 65–79)",
            3: "TIER 3 — TOP-10 RANGE (VTS 50–64)",
            4: "TIER 4 — CUT-LINE PLAYERS (VTS 35–49)",
            5: "TIER 5 — COURSE MISMATCHES (Below 35)",
        }
        
        tier_players = scored_df[scored_df["tier"] == tier_num]
        
        if len(tier_players) == 0:
            continue
        
        print(f"\n{tier_labels[tier_num]}")
        print("-" * 55)
        
        for _, player in tier_players.iterrows():
            flag_str = f" [{player['flags']}]" if player['flags'] else ""
            penalty_str = f" | Penalties: {player['penalties']}" if player['penalties'] else ""
            print(f"  {player['player']:<25} VTS: {player['vts_final']:>5.1f}{flag_str}{penalty_str}")


def export_to_csv(scored_df: pd.DataFrame, output_path: str) -> None:
    """Export scored field to CSV for further analysis."""
    scored_df.to_csv(output_path, index=True)
    print(f"Exported to: {output_path}")


# =============================================================================
# EDGE TABLE BUILDER
# =============================================================================

def build_edge_table(
    scored_df: pd.DataFrame,
    odds_dict: dict,  # {player_name: american_odds}
) -> pd.DataFrame:
    """
    Build model-vs-market edge table.
    
    Classification:
    - Strong Bet: model win prob > 2x implied odds
    - Bet: model win prob > 1.5x implied odds
    - Pass: within 20% of each other
    - Fade: implied odds > model by 1.5x
    
    Args:
        scored_df: Output of score_field()
        odds_dict: {player_name: american_odds (e.g., +2500, -110)}
    
    Returns:
        DataFrame with edge classification
    """
    def american_to_implied(odds: int) -> float:
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return abs(odds) / (abs(odds) + 100)
    
    edge_rows = []
    
    for _, player in scored_df.iterrows():
        name = player["player"]
        if name not in odds_dict:
            continue
        
        model_win_prob = player.get("prob_win", 0)
        market_implied = american_to_implied(odds_dict[name])
        
        if market_implied == 0:
            continue
        
        ratio = model_win_prob / market_implied
        
        if ratio >= 2.0:
            classification = "STRONG BET"
        elif ratio >= 1.5:
            classification = "BET"
        elif ratio <= 0.5:
            classification = "FADE"
        else:
            classification = "PASS"
        
        edge_rows.append({
            "player": name,
            "tier": player["tier"],
            "vts": player["vts_final"],
            "model_win_pct": f"{model_win_prob*100:.1f}%",
            "market_implied_pct": f"{market_implied*100:.1f}%",
            "edge_ratio": round(ratio, 2),
            "american_odds": odds_dict[name],
            "classification": classification,
        })
    
    edge_df = pd.DataFrame(edge_rows)
    edge_df = edge_df.sort_values("edge_ratio", ascending=False)
    return edge_df


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Example: load and score a field
    # In practice, load real DataGolf CSVs
    
    example_players = pd.DataFrame([
        {
            "name": "Example Player A",
            "world_rank": 3,
            "dk_salary": 11200,
            "sg_app": 8.5,      # percentile rank 0–10 vs field
            "sg_ott": 7.2,
            "sg_putt_surface": 6.8,
            "sg_arg": 7.0,
            "sg_t2g": 7.8,
            "par5_sg": 7.5,
            "form_score_adjusted": 7.2,
            "true_sg_app": 7.9,
            "true_sg_ott": 7.0,
            "is_debut": False,
            "career_venue_starts": 6,
            "career_venue_sg": 0.8,
            "recent_form_index": 1.2,
            "comp_course_bonus": 2.0,
        },
        {
            "name": "Example Player B",
            "world_rank": 45,
            "dk_salary": 8800,
            "sg_app": 7.8,
            "sg_ott": 5.2,
            "sg_putt_surface": 7.5,
            "sg_arg": 6.5,
            "sg_t2g": 6.8,
            "par5_sg": 6.2,
            "form_score_adjusted": 7.8,
            "true_sg_app": 7.2,
            "true_sg_ott": 5.0,
            "is_debut": True,
            "debut_category": "standard",
            "career_venue_starts": 0,
            "career_venue_sg": None,
            "recent_form_index": 0.3,
            "comp_course_bonus": 0.0,
        },
    ])
    
    # Score the field
    results = score_field(example_players, VENUE_DNA, conditions="firm")
    print_tier_rankings(results, VENUE_DNA["venue"])
    print("\n", results[["player", "vts_final", "tier", "penalties", "flags"]].to_string())
