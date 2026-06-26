import pandas as pd
from pathlib import Path

output_dir = Path("output")
output_dir.mkdir(exist_ok=True)

# --- Course Profile ---
course_profile = pd.DataFrame([{
    "course_name": "TPC River Highlands",
    "location": "Cromwell, Connecticut, USA",
    "designers": "Pete Dye (1982 redesign); Bobby Weed renovations",
    "par": 70,
    "yardage_min": 6841,
    "yardage_max": 6844,
    "rating_gold": 73.0,
    "slope_gold": 131,
    "turf_fairways": "Bentgrass with Poa annua",
    "turf_rough": "Kentucky bluegrass with fescue (~4\" tournament)",
    "turf_greens": "Bentgrass/Poa annua blend",
    "avg_green_size_sqft": 5000,
    "stimp_tournament": 12,
    "water_holes_count": 5,
    "signature_stretch_description": (
        "Closing stretch 15-17 around 4-acre lake; reachable risk-reward par-4 15th."
    ),
    "course_record_score": 58,
    "course_record_player": "Jim Furyk",
    "course_record_year": 2016,
}])

course_profile_path = output_dir / "Course_Profile.csv"
course_profile.to_csv(course_profile_path, index=False)

# --- Historical Scoring Stats ---
historical_stats = pd.DataFrame([{
    "event_name": "Travelers Championship",
    "event_id": 34,
    "scoring_avg_to_par_mean": -0.76,
    "scoring_avg_to_par_sd": 0.06,
    "course_yardage_mean": 6813,
    "course_yardage_sd": 416,
    "driving_distance_mean": 287.4,
    "driving_distance_sd": 5.5,
    "driving_accuracy_mean_pct": 62.5,
    "driving_accuracy_sd_pct": 1.7,
    "avg_fairway_width_mean_yds": 35.1,
    "avg_fairway_width_sd_yds": 0.9,
    "birdie_fest_flag": True,
}])

historical_stats_path = output_dir / "Historical_Scoring_Stats.csv"
historical_stats.to_csv(historical_stats_path, index=False)

# --- Hole-by-Hole ---
pars = [4, 4, 4, 4, 3, 5, 4, 3, 4, 4, 3, 4, 5, 4, 4, 3, 4, 4]

water_holes = {15, 16, 17}
risk_reward_map = {15: 3, 16: 2, 17: 2}

holes = []
for i, par in enumerate(pars, start=1):
    holes.append({
        "hole_number": i,
        "par": par,
        "yardage_gold": None,
        "yardage_blue": None,
        "handicap_rank": None,
        "water_flag": "Y" if i in water_holes else "N",
        "risk_reward_score": risk_reward_map.get(i, 0),
    })

hole_by_hole = pd.DataFrame(holes)

hole_by_hole_path = output_dir / "Hole_By_Hole.csv"
hole_by_hole.to_csv(hole_by_hole_path, index=False)

print("Seed files written:")
print(f"  {course_profile_path}")
print(f"  {historical_stats_path}")
print(f"  {hole_by_hole_path}")
