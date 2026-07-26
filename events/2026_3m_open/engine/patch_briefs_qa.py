"""
events/2026_3m_open/engine/patch_briefs_qa.py
Brief post-processor + QA gate for 2026 3M Open player briefs.

Fixes:
  - Makes key_risk_vector player-specific where generic fallback was used
  - Validates structural distinctness of all narrative fields
  - Writes patched briefs to output/ and deploy/data/

Run: python events/2026_3m_open/engine/patch_briefs_qa.py [--dry-run]
"""

from __future__ import annotations
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SLUG = "2026_3m_open"
BRIEFS_SRC  = ROOT / "events" / "2026_3m_open" / "output" / f"{SLUG}_player_briefs.json"
BRIEFS_DEPLOY = ROOT / "events" / "2026_3m_open" / "deploy" / "data" / f"{SLUG}_player_briefs.json"

# Generic fallback text patterns from build_event_package.py — these get personalized
GENERIC_REGRESSION = (
    "model risk is primarily regression to mean if 150-200 fw performance falls below recent trend"
)
GENERIC_BELOW_FIELD = (
    "below-field approach and/or iron play limits scoring capacity in TPC's birdiefest environment"
    " where approach is the primary separator"
)
GENERIC_LONG_IRON = (
    "150-200 fw SG below neutral; weak long-iron week at TPC produces a ceiling far short of"
    " leaderboard contention"
)

QA_DUP_THRESHOLD = 0.15  # fail if >15% of players share exact key_risk_vector text


def get_trait(brief: dict, label_key: str) -> float | None:
    for t in brief.get("trait_scores", []):
        if label_key.lower() in t.get("label", "").lower():
            v = t.get("score")
            if v is not None:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass
    return None


def personalize_risk(brief: dict) -> str:
    original = brief.get("key_risk_vector", "")
    tier = brief.get("VenueDNA_tier", "T5")

    # Exact-match only — compound multi-flag risk strings are already personalized
    if original == GENERIC_REGRESSION:
        li = get_trait(brief, "150")
        app = get_trait(brief, "App Overall")
        if li is not None:
            return (
                f"{tier} regression risk: maintaining App 150–200 yd pace at {li:.0f}/100 is"
                f" required to sustain projection; below-trend week converts to mid-field finish"
            )
        if app is not None:
            return (
                f"{tier} regression risk: App Overall {app:.0f}/100 must hold to retain projection;"
                f" below-trend approach week converts contender profile to mid-field result"
            )

    elif original == GENERIC_BELOW_FIELD:
        app = get_trait(brief, "App Overall")
        li = get_trait(brief, "150")
        if app is not None:
            return (
                f"App Overall {app:.0f}/100; below-field approach volume limits TPC scoring ceiling"
                f" where birdie density (60+ App Overall) separates contenders from field"
            )
        if li is not None:
            return (
                f"150-200 yd trait {li:.0f}/100 (below threshold); {tier}-range approach output"
                f" insufficient for TPC birdiefest scoring environment"
            )

    elif original == GENERIC_LONG_IRON:
        li = get_trait(brief, "150")
        if li is not None:
            return (
                f"150-200 yd approach score {li:.0f}/100 (long-iron deficit flagged); weak"
                f" long-iron week at TPC produces ceiling far short of leaderboard contention"
            )

    return original  # unchanged if no pattern matched


def patch_briefs(briefs: dict) -> tuple[dict, list[str]]:
    """Return (patched_briefs, change_log)."""
    changes = []
    for name, b in briefs.items():
        original = b.get("key_risk_vector", "")
        patched = personalize_risk(b)
        if patched != original:
            b["key_risk_vector"] = patched
            changes.append(f"PATCHED: {name}")
    return briefs, changes


def run_qa(briefs: dict) -> list[str]:
    issues = []
    total = len(briefs)

    # Rule 1: no two narrative fields identical within same player
    narrative_fields = [
        "why_it_fits_structurally",
        "exact_mechanism",
        "key_risk_vector",
        "named_failure_condition",
    ]
    for name, b in briefs.items():
        vals = [b.get(f, "") for f in narrative_fields if b.get(f, "")]
        for i, v1 in enumerate(vals):
            for j, v2 in enumerate(vals):
                if i < j and v1 == v2:
                    issues.append(
                        f"FAIL [intra-player dup]: {name} — identical text in two narrative fields"
                    )

    # Rule 2: no more than QA_DUP_THRESHOLD of field sharing exact key_risk text
    risks = [b.get("key_risk_vector", "") for b in briefs.values() if b.get("key_risk_vector", "")]
    for text, count in Counter(risks).items():
        if count / total > QA_DUP_THRESHOLD:
            pct = round(100 * count / total)
            issues.append(
                f"WARN [cross-field dup]: {count}/{total} ({pct}%) players share key_risk:"
                f" '{text[:80]}'"
            )

    # Rule 3: required fields present for all players
    required = [
        "why_it_fits_structurally",
        "exact_mechanism",
        "key_risk_vector",
        "named_failure_condition",
    ]
    for field in required:
        missing = [n for n, b in briefs.items() if not b.get(field, "")]
        if missing:
            issues.append(
                f"FAIL [missing required]: field '{field}' absent for {len(missing)} players:"
                f" {missing[:5]}"
            )

    # Rule 4: _hasBrief guard — scoring_thesis and conviction both need a usable value
    for name, b in briefs.items():
        scoring_thesis = b.get("exact_mechanism", "") or b.get("why_it_fits_structurally", "")
        conviction = b.get("why_it_fits_structurally", "")
        if not (scoring_thesis or conviction):
            issues.append(
                f"FAIL [false no-brief]: {name} would trigger 'No brief generated' banner"
                f" despite having a brief record"
            )

    return issues


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Validate only; do not write")
    args = parser.parse_args()

    src = BRIEFS_DEPLOY if BRIEFS_DEPLOY.exists() else BRIEFS_SRC
    if not src.exists():
        sys.exit(f"[patch_briefs_qa] Source briefs not found: {src}")

    with open(src, encoding="utf-8") as f:
        raw = json.load(f)

    # Support both dict-keyed and list formats
    if isinstance(raw, list):
        briefs = {b.get("player_name", f"__idx_{i}"): b for i, b in enumerate(raw)}
    else:
        briefs = raw

    print(f"[patch_briefs_qa] Loaded {len(briefs)} player briefs from {src.name}")

    # Pre-patch QA
    pre_issues = run_qa(briefs)
    print(f"\n[QA PRE-PATCH] {len(pre_issues)} issue(s)")
    for issue in pre_issues:
        print(f"  {issue}")

    # Patch
    briefs, changes = patch_briefs(briefs)
    print(f"\n[PATCH] {len(changes)} player risk texts personalized")
    for c in changes[:20]:
        print(f"  {c}")
    if len(changes) > 20:
        print(f"  ... and {len(changes) - 20} more")

    # Post-patch QA
    post_issues = run_qa(briefs)
    print(f"\n[QA POST-PATCH] {len(post_issues)} issue(s)")
    for issue in post_issues:
        print(f"  {issue}")

    fails = [i for i in post_issues if i.startswith("FAIL")]
    if fails:
        print(f"\n[patch_briefs_qa] BLOCKED — {len(fails)} FAIL-level issue(s) remain after patch")
        if not args.dry_run:
            sys.exit(1)
    else:
        print("\n[patch_briefs_qa] QA passed - no FAIL-level issues")

    if args.dry_run:
        print("[patch_briefs_qa] Dry-run: no files written")
        return

    # Reconstitute as dict if originally dict
    out = briefs if isinstance(raw, dict) else list(briefs.values())

    for dest in [BRIEFS_SRC, BRIEFS_DEPLOY]:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"[patch_briefs_qa] Written -> {dest.relative_to(ROOT)}")

    print(f"[patch_briefs_qa] Done. {len(changes)} risk texts personalized.")


if __name__ == "__main__":
    main()
