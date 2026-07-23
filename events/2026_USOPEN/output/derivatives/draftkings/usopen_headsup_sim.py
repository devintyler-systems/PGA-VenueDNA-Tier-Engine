import random
import numpy as np

# Live state
clark_start_score = -4
burns_start_score = -3
clark_holes_left = 11
burns_holes_left = 8

# Per-hole probabilities
p_burns = {"B": 0.20, "P": 0.55, "BOG": 0.25}
p_clark = {"B": 0.10, "P": 0.55, "BOG": 0.35}

def draw_outcome(probs, rng):
    r = rng.random()
    if r < probs["B"]:
        return -1
    elif r < probs["B"] + probs["P"]:
        return 0
    else:
        return 1

N = 100_000
rng = random.Random(42)

burns_wins = 0
clark_wins = 0
burns_scores = []
clark_scores = []

for _ in range(N):
    cs = clark_start_score
    bs = burns_start_score

    for _ in range(burns_holes_left):
        bs += draw_outcome(p_burns, rng)

    for _ in range(clark_holes_left):
        cs += draw_outcome(p_clark, rng)

    burns_scores.append(bs)
    clark_scores.append(cs)

    if cs < bs:
        clark_wins += 1
    elif bs < cs:
        burns_wins += 1
    else:  # tie -> playoff coin flip
        if rng.random() < 0.5:
            clark_wins += 1
        else:
            burns_wins += 1

burns_arr = np.array(burns_scores)
clark_arr = np.array(clark_scores)

print("=" * 42)
print("  2026 U.S. Open — Clark vs Burns Sim")
print("=" * 42)
print(f"Simulations: {N:,}")
print(f"Clark start: {clark_start_score:+d}, {clark_holes_left} holes left")
print(f"Burns start: {burns_start_score:+d}, {burns_holes_left} holes left")
print()
print(f"Burns win %:  {burns_wins / N:.4f}  ({burns_wins:,}/{N:,})")
print(f"Clark win %:  {clark_wins / N:.4f}  ({clark_wins:,}/{N:,})")
print()

def describe(arr, name):
    print(f"{name} median finish:      {np.median(arr):+.1f}")
    print(f"{name} 10th pct (best):    {np.percentile(arr, 10):+.1f}")
    print(f"{name} 90th pct (worst):   {np.percentile(arr, 90):+.1f}")

describe(burns_arr, "Burns")
print()
describe(clark_arr, "Clark")

# Margin distribution (Burns - Clark final score; negative = Burns leads)
print()
print("--- Final margin distribution (Burns score minus Clark score) ---")
margin = burns_arr - clark_arr
for delta in range(-5, 6):
    pct = np.mean(margin == delta) * 100
    bar = "#" * int(pct / 0.5)
    label = f"Burns {abs(delta):+d}" if delta < 0 else (f"Clark {abs(delta):+d}" if delta > 0 else "Tie     ")
    print(f"  {label:10s} ({delta:+d}): {pct:5.1f}%  {bar}")
