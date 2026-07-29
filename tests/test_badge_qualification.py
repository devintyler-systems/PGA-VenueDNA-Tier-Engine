"""Unit tests for badge qualification in the Rocket Classic event-local engine."""
import importlib.util
from pathlib import Path
import pytest

_ENGINE_PATH = (
    Path(__file__).resolve().parent.parent
    / "events" / "2026_rocket_classic" / "engine" / "enrich_cards.py"
)
_spec = importlib.util.spec_from_file_location("rocket_engine", _ENGINE_PATH)
_mod  = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

qualify_badges            = _mod.qualify_badges
compute_badge_percentiles = _mod.compute_badge_percentiles
build_badge_inputs        = _mod.build_badge_inputs
load_badge_policy         = _mod.load_badge_policy
_BADGE_TRAIT_AVAIL_MAP    = _mod._BADGE_TRAIT_AVAIL_MAP

_POLICY_PATH = Path(__file__).resolve().parent.parent / "config" / "badge_policy.v1.json"
BADGE_HOT_STREAK_L6_MIN_ROUNDS  = _mod.BADGE_HOT_STREAK_L6_MIN_ROUNDS
BADGE_HOT_STREAK_L24_MIN_ROUNDS = _mod.BADGE_HOT_STREAK_L24_MIN_ROUNDS


def _load_policy():
    return load_badge_policy(_POLICY_PATH)


def _inputs_stub(**overrides):
    """Minimal badge_inputs dict — all traits ineligible by default."""
    base = {
        "approach_play":    {"source_file": "f", "source_column": "c", "window": "w", "value": 0.5, "availability": "DERIVED",  "usable_for_badges": False},
        "iron_play":        {"source_file": "f", "source_column": "c", "window": "w", "value": 0.5, "availability": "DERIVED",  "usable_for_badges": False},
        "driving_distance": {"source_file": "f", "source_column": "dist_mean", "window": "L24", "value": 10.0, "rounds": 80, "availability": "MEASURED", "usable_for_badges": False},
        "driving_accuracy": {"source_file": "f", "source_column": "acc_mean",  "window": "L24", "value": 0.05, "rounds": 80, "availability": "MEASURED", "usable_for_badges": False},
        "putting":          {"source_file": "f", "source_column": "putt_mean", "window": "L24", "value": 0.40, "rounds": 80, "availability": "MEASURED", "usable_for_badges": False},
        "recent_form":      {"source_file": "f", "source_column": "total_mean delta", "window": "L6 vs L24", "value": 0.30, "l6_total_mean": 1.5, "l6_rounds": 20, "l24_total_mean": 1.2, "l24_rounds": 80, "availability": "MEASURED", "usable_for_badges": False},
        "course_history":   {"source_file": "detroit_golf_club_CH.csv", "source_column": "2021-2025", "window": "2021-2025", "detroit_starts": 0, "rounds_played": 0, "availability": "MEASURED", "usable_for_badges": True},
    }
    for k, v in overrides.items():
        if k in base and isinstance(v, dict):
            base[k].update(v)
        else:
            base[k] = v
    return base


def test_load_badge_policy_returns_list():
    badges = _load_policy()
    assert isinstance(badges, list) and len(badges) == 8


def test_load_badge_policy_missing_file(tmp_path):
    assert load_badge_policy(tmp_path / "nonexistent.json") == []


def test_debut_qualifies_when_zero_starts():
    badges = _load_policy()
    inp = _inputs_stub(course_history={"source_file": "detroit_golf_club_CH.csv", "source_column": "2021-2025", "window": "2021-2025", "detroit_starts": 0, "rounds_played": 0, "availability": "MEASURED", "usable_for_badges": True})
    result = qualify_badges(inp, badges, {})
    assert any(b["badge_id"] == "debut" for b in result)


def test_debut_not_emitted_when_one_start():
    badges = _load_policy()
    inp = _inputs_stub(course_history={"source_file": "detroit_golf_club_CH.csv", "source_column": "2021-2025", "window": "2021-2025", "detroit_starts": 1, "rounds_played": 4, "availability": "MEASURED", "usable_for_badges": True})
    result = qualify_badges(inp, badges, {})
    assert not any(b["badge_id"] == "debut" for b in result)


def test_detroit_veteran_qualifies_at_three_starts():
    badges = _load_policy()
    inp = _inputs_stub(course_history={"source_file": "detroit_golf_club_CH.csv", "source_column": "2021-2025", "window": "2021-2025", "detroit_starts": 3, "rounds_played": 12, "availability": "MEASURED", "usable_for_badges": True})
    result = qualify_badges(inp, badges, {})
    ids = [b["badge_id"] for b in result]
    assert "detroit_veteran" in ids
    assert "debut" not in ids


def test_detroit_veteran_not_emitted_at_two_starts():
    badges = _load_policy()
    inp = _inputs_stub(course_history={"source_file": "detroit_golf_club_CH.csv", "source_column": "2021-2025", "window": "2021-2025", "detroit_starts": 2, "rounds_played": 8, "availability": "MEASURED", "usable_for_badges": True})
    result = qualify_badges(inp, badges, {})
    assert not any(b["badge_id"] == "detroit_veteran" for b in result)


def test_detroit_starts_counts_cut_as_start():
    """CUT is a valid start — it must be counted, not skipped."""
    import csv, tempfile, pathlib
    cols = ["player_name",
            "2021 (Rocket Mortgage Classic)", "2022 (Rocket Mortgage Classic)",
            "2023 (Rocket Mortgage Classic)", "2024 (Rocket Mortgage Classic)",
            "2025 (Rocket Classic)",
            "rounds_played", "historical_true_sg", "versus_expected",
            "ch_adjustment", "experience_adjustment"]
    rows = [{"player_name": "Test, Player",
             "2021 (Rocket Mortgage Classic)": "CUT",
             "2022 (Rocket Mortgage Classic)": "T9",
             "2023 (Rocket Mortgage Classic)": "null",
             "2024 (Rocket Mortgage Classic)": "",
             "2025 (Rocket Classic)": "T41",
             "rounds_played": "8", "historical_true_sg": "0.5", "versus_expected": "0.3",
             "ch_adjustment": "0.02", "experience_adjustment": "0.05"}]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8") as f:
        p = pathlib.Path(f.name)
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        writer.writerows(rows)
    result = _mod.load_ch(p)
    assert result["Test, Player"]["detroit_starts"] == 3   # CUT + T9 + T41 = 3; null + "" = 0


def test_detroit_starts_counts_wd_as_start():
    import csv, tempfile, pathlib
    cols = ["player_name",
            "2021 (Rocket Mortgage Classic)", "2022 (Rocket Mortgage Classic)",
            "2023 (Rocket Mortgage Classic)", "2024 (Rocket Mortgage Classic)",
            "2025 (Rocket Classic)",
            "rounds_played", "historical_true_sg", "versus_expected",
            "ch_adjustment", "experience_adjustment"]
    rows = [{"player_name": "Test, WD",
             "2021 (Rocket Mortgage Classic)": "WD",
             "2022 (Rocket Mortgage Classic)": "", "2023 (Rocket Mortgage Classic)": "",
             "2024 (Rocket Mortgage Classic)": "", "2025 (Rocket Classic)": "",
             "rounds_played": "2", "historical_true_sg": "0.0", "versus_expected": "0.0",
             "ch_adjustment": "0.0", "experience_adjustment": "0.05"}]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8") as f:
        p = pathlib.Path(f.name)
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        writer.writerows(rows)
    result = _mod.load_ch(p)
    assert result["Test, WD"]["detroit_starts"] == 1


def test_debut_has_zero_detroit_starts():
    import csv, tempfile, pathlib
    cols = ["player_name",
            "2021 (Rocket Mortgage Classic)", "2022 (Rocket Mortgage Classic)",
            "2023 (Rocket Mortgage Classic)", "2024 (Rocket Mortgage Classic)",
            "2025 (Rocket Classic)",
            "rounds_played", "historical_true_sg", "versus_expected",
            "ch_adjustment", "experience_adjustment"]
    rows = [{"player_name": "Debut, Player",
             "2021 (Rocket Mortgage Classic)": "", "2022 (Rocket Mortgage Classic)": "null",
             "2023 (Rocket Mortgage Classic)": "null", "2024 (Rocket Mortgage Classic)": "",
             "2025 (Rocket Classic)": "",
             "rounds_played": "0", "historical_true_sg": "0.0", "versus_expected": "0.0",
             "ch_adjustment": "0.0", "experience_adjustment": "0.0"}]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8") as f:
        p = pathlib.Path(f.name)
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        writer.writerows(rows)
    result = _mod.load_ch(p)
    assert result["Debut, Player"]["detroit_starts"] == 0


def test_iron_surgeon_qualifies_at_80th_percentile():
    badges = _load_policy()
    inp = _inputs_stub(
        approach_play={"source_file": "f", "source_column": "trait_approach_raw", "window": "12m", "value": 1.2, "availability": "DERIVED", "usable_for_badges": True},
        iron_play=    {"source_file": "f", "source_column": "trait_long_iron_raw", "window": "12m", "value": 0.8, "availability": "DERIVED", "usable_for_badges": True},
    )
    result = qualify_badges(inp, badges, {"approach_play": 85, "iron_play": 82})
    assert any(b["badge_id"] == "iron_surgeon" for b in result)


def test_iron_surgeon_not_emitted_when_approach_ineligible():
    badges = _load_policy()
    inp = _inputs_stub(
        approach_play={"source_file": "f", "source_column": "c", "window": "w", "value": 1.2, "availability": "MISSING_ZERO_FILLED", "usable_for_badges": False},
        iron_play=    {"source_file": "f", "source_column": "c", "window": "w", "value": 0.8, "availability": "DERIVED", "usable_for_badges": True},
    )
    result = qualify_badges(inp, badges, {"approach_play": 90, "iron_play": 90})
    assert not any(b["badge_id"] == "iron_surgeon" for b in result)


def test_bomber_uses_dist_mean_not_decomp():
    """bomber must use dist_mean from l24.csv; driving_dist_adj is never a badge input."""
    badges = _load_policy()
    inp = _inputs_stub(
        driving_distance={"source_file": "pga_sg_query_allcourses_l24.csv", "source_column": "dist_mean", "window": "L24", "value": 15.0, "rounds": 80, "availability": "MEASURED", "usable_for_badges": True},
    )
    result = qualify_badges(inp, badges, {"driving_distance": 90})
    b_ids = [b["badge_id"] for b in result]
    assert "bomber" in b_ids
    bomber = next(b for b in result if b["badge_id"] == "bomber")
    assert "dist_mean" in bomber["qualification_reason"]
    assert "l24" in bomber["qualification_reason"].lower() or "L24" in bomber["qualification_reason"]


def test_bomber_not_emitted_when_ineligible():
    badges = _load_policy()
    inp = _inputs_stub()
    result = qualify_badges(inp, badges, {"driving_distance": 90})
    assert not any(b["badge_id"] == "bomber" for b in result)


def test_precision_driver_uses_acc_mean_not_decomp():
    badges = _load_policy()
    inp = _inputs_stub(
        driving_accuracy={"source_file": "pga_sg_query_allcourses_l24.csv", "source_column": "acc_mean", "window": "L24", "value": 0.12, "rounds": 80, "availability": "MEASURED", "usable_for_badges": True},
    )
    result = qualify_badges(inp, badges, {"driving_accuracy": 85})
    assert any(b["badge_id"] == "precision_driver" for b in result)
    pd_badge = next(b for b in result if b["badge_id"] == "precision_driver")
    assert "acc_mean" in pd_badge["qualification_reason"]


def test_putter_uses_putt_mean():
    badges = _load_policy()
    inp = _inputs_stub(
        putting={"source_file": "pga_sg_query_allcourses_l24.csv", "source_column": "putt_mean", "window": "L24", "value": 0.55, "rounds": 80, "availability": "MEASURED", "usable_for_badges": True},
    )
    result = qualify_badges(inp, badges, {"putting": 88})
    assert any(b["badge_id"] == "putter" for b in result)
    putter_b = next(b for b in result if b["badge_id"] == "putter")
    assert "putt_mean" in putter_b["qualification_reason"]


def test_hot_streak_qualifies_with_sufficient_sample():
    badges = _load_policy()
    inp = _inputs_stub(
        recent_form={"source_file": "f", "source_column": "total_mean delta", "window": "L6 vs L24", "value": 0.80, "l6_total_mean": 2.0, "l6_rounds": 20, "l24_total_mean": 1.2, "l24_rounds": 80, "availability": "MEASURED", "usable_for_badges": True},
    )
    result = qualify_badges(inp, badges, {"recent_form": 85})
    assert any(b["badge_id"] == "hot_streak" for b in result)


def test_hot_streak_rejected_insufficient_l6_rounds():
    badges = _load_policy()
    inp = _inputs_stub(
        recent_form={"source_file": "f", "source_column": "total_mean delta", "window": "L6 vs L24", "value": None, "l6_total_mean": 2.0, "l6_rounds": 4, "l24_total_mean": 1.2, "l24_rounds": 80, "availability": "INSUFFICIENT_SAMPLE", "usable_for_badges": False},
    )
    result = qualify_badges(inp, badges, {"recent_form": 90})
    assert not any(b["badge_id"] == "hot_streak" for b in result)


def test_hot_streak_rejected_insufficient_l24_rounds():
    badges = _load_policy()
    inp = _inputs_stub(
        recent_form={"source_file": "f", "source_column": "total_mean delta", "window": "L6 vs L24", "value": None, "l6_total_mean": 2.0, "l6_rounds": 20, "l24_total_mean": 1.2, "l24_rounds": 8, "availability": "INSUFFICIENT_SAMPLE", "usable_for_badges": False},
    )
    result = qualify_badges(inp, badges, {"recent_form": 90})
    assert not any(b["badge_id"] == "hot_streak" for b in result)


def test_par5_predator_never_emitted():
    badges = _load_policy()
    inp = _inputs_stub()
    result = qualify_badges(inp, badges, {"par5_scoring": 95})
    assert not any(b["badge_id"] == "par5_predator" for b in result)


def test_all_emitted_badges_have_source_backed_reasons():
    badges = _load_policy()
    inp = _inputs_stub(
        course_history={"source_file": "detroit_golf_club_CH.csv", "source_column": "2021-2025", "window": "2021-2025", "detroit_starts": 0, "rounds_played": 0, "availability": "MEASURED", "usable_for_badges": True},
    )
    result = qualify_badges(inp, badges, {})
    for b in result:
        assert len(b["qualification_reason"]) > 10, f"badge {b['badge_id']} has thin reason"
        assert "source" in b["qualification_reason"].lower() or any(
            kw in b["qualification_reason"] for kw in ["detroit", "Detroit", ".csv", "L24", "L6", "12m"]
        ), f"badge {b['badge_id']} reason lacks source provenance"


def test_top_player_gets_highest_percentile():
    players = [
        {"trait_approach_raw": 2.0, "trait_long_iron_raw": 2.0,
         "trait_availability": {"trait_approach_raw": {"usable_for_badges": True},
                                "trait_long_iron_raw": {"usable_for_badges": True}}},
        {"trait_approach_raw": 1.0, "trait_long_iron_raw": 1.0,
         "trait_availability": {"trait_approach_raw": {"usable_for_badges": True},
                                "trait_long_iron_raw": {"usable_for_badges": True}}},
        {"trait_approach_raw": 0.0, "trait_long_iron_raw": 0.0,
         "trait_availability": {"trait_approach_raw": {"usable_for_badges": False},
                                "trait_long_iron_raw": {"usable_for_badges": False}}},
    ]
    badge_inputs = [
        {"approach_play": {"value": 2.0, "usable_for_badges": True},
         "iron_play": {"value": 2.0, "usable_for_badges": True},
         "driving_distance": {"value": None, "usable_for_badges": False},
         "driving_accuracy": {"value": None, "usable_for_badges": False},
         "putting": {"value": None, "usable_for_badges": False},
         "recent_form": {"value": None, "usable_for_badges": False}},
        {"approach_play": {"value": 1.0, "usable_for_badges": True},
         "iron_play": {"value": 1.0, "usable_for_badges": True},
         "driving_distance": {"value": None, "usable_for_badges": False},
         "driving_accuracy": {"value": None, "usable_for_badges": False},
         "putting": {"value": None, "usable_for_badges": False},
         "recent_form": {"value": None, "usable_for_badges": False}},
        {"approach_play": {"value": 0.0, "usable_for_badges": False},
         "iron_play": {"value": 0.0, "usable_for_badges": False},
         "driving_distance": {"value": None, "usable_for_badges": False},
         "driving_accuracy": {"value": None, "usable_for_badges": False},
         "putting": {"value": None, "usable_for_badges": False},
         "recent_form": {"value": None, "usable_for_badges": False}},
    ]
    result = compute_badge_percentiles(players, badge_inputs)
    assert result[0].get("approach_play", 0) >= result[1].get("approach_play", 0)
    assert "approach_play" not in result[2]
