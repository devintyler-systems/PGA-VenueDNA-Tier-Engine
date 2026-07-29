"""
verify_tripod_audit_parity.py
Confirms the UI-served deploy copy of the tripod audit is byte-identical
to the validated output copy. Verification only — never rewrites either file.
Exits 0 on PASS, 1 on any failure.
"""
import hashlib
import sys
from pathlib import Path

REPO_ROOT    = Path(__file__).resolve().parent.parent.parent.parent
OUTPUT_AUDIT = REPO_ROOT / "events/2026_rocket_classic/output/2026_rocket_classic_tripod_audit.json"
DEPLOY_AUDIT = REPO_ROOT / "events/2026_rocket_classic/deploy/data/2026_rocket_classic_tripod_audit.json"

def sha256(path: Path) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()

print("=== Rocket Classic Tripod Audit Sidecar Parity Check ===\n")

missing = []
for label, path in [("OUTPUT (source of truth)", OUTPUT_AUDIT), ("DEPLOY  (UI-served copy)", DEPLOY_AUDIT)]:
    if not path.exists():
        print(f"  MISSING: {path}")
        missing.append(label)

if missing:
    print(f"\n  FAIL: {len(missing)} file(s) absent — cannot verify parity")
    sys.exit(1)

h_output = sha256(OUTPUT_AUDIT)
h_deploy = sha256(DEPLOY_AUDIT)

print(f"  OUTPUT path:  {OUTPUT_AUDIT}")
print(f"  OUTPUT sha256 {h_output}")
print()
print(f"  DEPLOY path:  {DEPLOY_AUDIT}")
print(f"  DEPLOY sha256 {h_deploy}")
print()

if h_output == h_deploy:
    print("  RESULT: PASS — deploy copy is byte-identical to validated output")
    sys.exit(0)
else:
    print("  RESULT: FAIL — hashes differ; deploy copy does not match validated output")
    print("  ACTION: Do not auto-repair. Investigate divergence before release.")
    sys.exit(1)
