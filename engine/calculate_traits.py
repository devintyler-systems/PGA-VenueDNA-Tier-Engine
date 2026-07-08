"""
Venue-fitness trait engine — CSV-backed.

Derives the four rolling trait scores directly from DataGolf True SG CSV
exports placed in an event's input/ directory.  No database connection required.

Expected files (all exported from DataGolf → True Strokes Gained):
  dg_true_sg_6m.csv   — 6-month rolling window
  dg_true_sg_12m.csv  — 12-month rolling window
  dg_true_sg_24m.csv  — 24-month rolling window

Trait definitions:
  tvl_score  — SG:OTT (12 months)        off-the-tee consistency over a full year
  hew_score  — Ball Striking (6 months)   combined OTT+APP over the recent window
  brie_score — SG:APP (24 months)         approach precision over a 2-year base
  vfr_score  — SG:ARG (6 months)          around-the-green adaptability
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

MIN_ROUNDS = 10

_CSV_FILES = {
    "6m":  "dg_true_sg_6m.csv",
    "12m": "dg_true_sg_12m.csv",
    "24m": "dg_true_sg_24m.csv",
}

# trait → (source column in the True SG CSV, time horizon key)
_TRAIT_MAP = {
    "tvl_score":  ("ott_mean", "12m"),
    "hew_score":  ("bs_mean",  "6m"),
    "brie_score": ("app_mean", "24m"),
    "vfr_score":  ("arg_mean", "6m"),
}

_KEEP_COLS = [
    "player_name", "rounds_played",
    "ott_mean", "arg_mean", "app_mean", "bs_mean",
    "putt_mean", "t2g_mean", "total_mean",
]


# ── public API ────────────────────────────────────────────────────────────────

def load_trait_inputs(input_dir: Path | str) -> pd.DataFrame:
    """
    Read and merge the three True SG CSV files from *input_dir*.

    Returns a DataFrame indexed by player_name with all numeric columns
    suffixed by the time horizon (_6m / _12m / _24m).

    Raises FileNotFoundError if any of the three required CSVs are absent.
    """
    input_dir = Path(input_dir)
    frames: dict[str, pd.DataFrame] = {}
    for horizon, filename in _CSV_FILES.items():
        path = input_dir / filename
        if not path.exists():
            raise FileNotFoundError(
                f"Missing required input file: {path}\n"
                f"Export it from DataGolf → True Strokes Gained → {horizon.upper()} window."
            )
        df = pd.read_csv(path, usecols=_KEEP_COLS)
        df = df.rename(
            columns={c: f"{c}_{horizon}" for c in df.columns if c != "player_name"}
        )
        frames[horizon] = df

    merged = frames["6m"]
    for h in ("12m", "24m"):
        merged = merged.merge(frames[h], on="player_name", how="outer")
    return merged.set_index("player_name")


def compute_traits(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute the four trait scores from the merged DataFrame returned by
    :func:`load_trait_inputs`.

    A trait is set to ``None`` when the player has fewer than MIN_ROUNDS
    qualifying rounds in that horizon's window, or when the source value
    is unavailable.
    """
    out = pd.DataFrame(index=df.index)
    for trait, (col, horizon) in _TRAIT_MAP.items():
        value_col  = f"{col}_{horizon}"
        rounds_col = f"rounds_played_{horizon}"
        series     = df[value_col].copy().astype(float)
        # Treat missing rounds as zero so the gate fires on NaN too
        has_enough = df[rounds_col].fillna(0) >= MIN_ROUNDS
        series[~has_enough] = None
        out[trait] = series.round(4)
    return out


def compute_player_traits(
    player_name: str,
    input_dir: Path | str,
) -> dict:
    """
    Return the four trait scores for a single *player_name* from the
    CSV files in *input_dir*.

    All four traits are ``None`` if the player is absent from the input
    files or has insufficient rounds in a given window.
    """
    df_raw = load_trait_inputs(input_dir)
    df_out = compute_traits(df_raw)

    base = {
        "player_name": player_name,
        "tvl_score":   None,
        "hew_score":   None,
        "brie_score":  None,
        "vfr_score":   None,
    }
    if player_name not in df_out.index:
        return base

    row = df_out.loc[player_name]
    return {
        "player_name": player_name,
        **{k: (None if pd.isna(v) else round(float(v), 4)) for k, v in row.items()},
    }


# ── smoke test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    ROOT      = Path(__file__).resolve().parent.parent
    INPUT_DIR = ROOT / "events" / "2026_GenesisScottishOpen" / "input"

    print(f"Input directory: {INPUT_DIR}\n")

    df_raw    = load_trait_inputs(INPUT_DIR)
    df_traits = compute_traits(df_raw)

    print(f"Trait scores — {len(df_traits)} players")
    print(df_traits.head(10).to_string())

    # Single-player lookup
    test_player = "McIlroy, Rory"
    result = compute_player_traits(test_player, INPUT_DIR)
    print(f"\n{test_player}:")
    print(json.dumps(result, indent=2))

    # Edge case: unknown player must return all None
    unknown = compute_player_traits("Fictional, Player", INPUT_DIR)
    assert all(v is None for k, v in unknown.items() if k != "player_name"), \
        "Expected all None for unknown player"
    print("\nEdge-case assertion passed — unknown player returns all None.")
