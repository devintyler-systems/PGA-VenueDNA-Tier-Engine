# Sedgefield Country Club — VenueDNA Venue Profile
## Canonical venue intelligence file
## Venue slug: sedgefield_country_club
## Primary event: Wyndham Championship
## Current canonical version: RECONSTRUCTED_V1 (provisional)

---

## STATUS NOTICE

**This profile is RECONSTRUCTED_V1 — a doctrine-derived, provisional
reconstruction, not a historically-validated venue record.**

It was authored from Sedgefield Country Club's well-established public
course record (architect, routing, yardage, green-complex character,
general host-venue reputation) under Phase 4.3's venue-configuration work.
It does **not** rest on a per-player DataGolf course-history export,
per-round strokes-gained decomposition, or any other structured VenueDNA
evidence source for this venue — none is currently available in this
repository (see §19 Source Note). It follows the same
"reconstructed, documentation-only, not yet activated" framing already used
by `library/venues/detroit_golf_club/detroit_golf_club_intelligence_2026_v1.json`
for Detroit Golf Club's dominant-tripod hypothesis.

Do not treat this file's mechanism claims as equivalent in evidentiary
weight to `library/venues/tpc_twin_cities/tpc_twin_cities_venue_profile.md`,
whose winning-score and SG:Approach figures are drawn from actual event
results. Historical validation against real Wyndham Championship results is
required before any trait weight, threshold, or anti-pattern claim here is
treated as high-confidence doctrine.

`engine/event_context.py`'s `require_supported_context()` capability gate
does not admit `sedgefield_country_club` in this phase — this profile and
its paired `engine/venue_config.py` `SEDGEFIELD_COUNTRY_CLUB` record are
staged for a future, separately authorized activation, not a live producer
run.

---

## 1. VENUE IDENTITY

- **Course:** Sedgefield Country Club
- **Location:** Greensboro, North Carolina
- **Primary PGA Tour event:** Wyndham Championship
- **Architect:** Donald Ross
- **Opened:** 1926
- **Par:** 70
- **Yardage:** approximately 7,100–7,150 (varies by year's tee setup)
- **Fairways:** Bermudagrass
- **Greens:** Bentgrass (small, contoured, Donald Ross-style complexes)
- **Topography:** Rolling Piedmont parkland with mature tree corridors

---

## 2. STRUCTURAL SUMMARY

Sedgefield is a classic Donald Ross design: generally forgiving off the
tee relative to a modern Tour setup, but defended almost entirely by its
green complexes — small, subtly contoured, and unforgiving of imprecise
approach play or careless pin-hunting. Unlike TPC Twin Cities (where
receptive bentgrass greens compress the putting edge and approach distance
from 175+ yards is the separator), Sedgefield's defense is concentrated at
the green, not the fairway or the tee.

This venue rewards players who can:
- control proximity and trajectory into small, well-guarded targets
- read and execute on quick, subtly breaking Ross greens
- convert scoring opportunities without needing to force a low-percentage
  approach into a tucked pin
- sustain a hot short week, since the leaderboard historically compresses

This venue punishes players who:
- rely on raw distance/power without approach precision
- misjudge Ross greens' false fronts and small effective landing areas
- need a wide-margin approach target to commit fully

---

## 3. SURFACES AND PLAYING ENVIRONMENT

### Turf / surfaces
- Fairways: Bermudagrass
- Greens: Bentgrass
- Rough: Bermudagrass, moderate

### Surface interpretation
- Bermudagrass fairways provide reliable, though occasionally firmer, lies
- Small Ross bentgrass greens demand precise trajectory control and spin,
  not just raw ball-striking quality
- Rough is playable; it is not the primary defensive mechanism at this venue

### Practical scoring effect
- A hot putting week on Sedgefield's quick, tricky greens is a genuinely
  meaningful edge here — a materially different doctrine than TPC Twin
  Cities, where putting is explicitly de-emphasized
- Precise wedge and short-iron play into small targets is the recurring
  separator among contenders

---

## 4. SCORING ENVIRONMENT

### Scoring classification (general, undated public reputation)
- Wyndham Championship is broadly known as a low-scoring, birdiefest event
  relative to Tour average, driven by generous fairway width and scoreable
  par 5s, tempered by the difficulty of holding tight pin positions on
  small greens
- GIR environment: high-scoring off the tee, more selective around the green

### VenueDNA interpretation
Low aggregate scores here do not imply the course is form-neutral. The
mechanism is:
1. precise approach play into small, well-defended greens
2. short-game and putting quality on quick, breaking surfaces
3. course-history/local-knowledge translation, given the venue's annual
   host status and green-reading complexity
4. avoiding compounding mistakes from a poorly-judged approach

---

## 5. WINNING MECHANISM (provisional hypothesis — not yet historically validated)

### Primary mechanism
**Approach precision into small Ross greens remains the most important
trait**, though the emphasis sits closer to short/mid-iron and wedge
precision than TPC Twin Cities' longer-skewed approach profile.

### Secondary mechanism
**Course history / local knowledge is more valuable here than at a typical
Tour stop.** Small, subtly-breaking Ross greens reward players with repeat
exposure to their specific contours and speeds.

### Tertiary mechanism
**Off-the-tee control matters less as a stand-alone driver than at TPC
Twin Cities.** Generous fairway width reduces total-driving's structural
weight; it remains a moderate, not dominant, factor.

### Debatable mechanism (explicitly flagged uncertainty)
**Putting/short-game quality is likely a genuine positive fit signal here,
not the anti-pattern it is at TPC Twin Cities.** This is a material
doctrinal difference from TPC's anti-pattern framework and is called out
explicitly in §11 below.

---

## 6. KEY TRAIT WEIGHTS (provisional; see `engine/venue_config.py` `SEDGEFIELD_COUNTRY_CLUB`)

### Core VenueDNA skill weights (diagnostic/display weighting only)
1. Approach play (elevated versus TPC Twin Cities)
2. Total driving (moderate; de-emphasized versus TPC Twin Cities)
3. Long/mid-iron precision (de-emphasized versus TPC Twin Cities, since the
   approach distribution skews shorter)
4. Course-history translation (elevated versus TPC Twin Cities)
5. Recent form (slightly elevated; short, compressed leaderboards reward a
   hot week)

### Weight notes
- Approach remains the highest-conviction driver, but the underlying skill
  is short/mid-iron precision into small targets, not long-iron control
  from 175+ yards
- Course history carries more weight here than at TPC Twin Cities,
  reflecting a Ross green-reading advantage for repeat competitors
- Total driving and long-iron weights are both reduced relative to TPC
  Twin Cities to reflect the shorter, more forgiving off-the-tee profile

---

## 7. APPROACH DISTANCE PROFILE

### Key distance expectation (general course-character inference, not a
measured per-round distribution)
Sedgefield's shorter overall yardage relative to TPC Twin Cities implies a
higher proportion of approaches from wedge and short/mid-iron distances
rather than TPC's 175+-yard-skewed profile. This is a structural inference
from yardage and routing, not a measured DataGolf approach-distance
breakdown for this venue.

### VenueDNA interpretation
The course still separates players on approach quality, but the skill
being tested is precision and spin control into small targets rather than
raw long-iron ball-striking.

---

## 8. DRIVING PROFILE

### Visual and structural read
Fairways are generally wider and more forgiving than TPC Twin Cities.
Off-the-tee is a real but secondary factor.

### VenueDNA interpretation
This is not a course where total driving decides the tournament. Balanced,
positional drivers are favored over pure bombers, but the penalty for
merely average driving distance/accuracy is milder than at TPC Twin
Cities.

---

## 9. GREEN COMPLEX PROFILE (Sedgefield's dominant structural mechanism)

Small, subtly contoured Donald Ross greens with false fronts and limited
effective landing area. This is the course's primary defensive mechanism,
replacing TPC Twin Cities' water-hazard/total-driving defense and long-iron
approach-distance defense.

### VenueDNA interpretation
- Precision trumps raw distance on approach
- Short-game touch and putting read/execution quality carry real,
  positive scoring weight
- Aggressive pin-hunting without matching precision is a genuine risk
  factor

---

## 10. PRESSURE HOLES

Hole-specific pressure-point detail (exact yardages, closing-stretch
configuration, and hazard-by-hole description) is not reconstructed in
this provisional profile. A future validated update should populate this
section from an approved course-record source before it is treated as
doctrine, consistent with §19's source-note caveat.

---

## 11. ANTI-PATTERNS (provisional; explicit doctrinal caveat)

The following player types are structurally downgraded here:

### 1. Distance-first, precision-poor players
Reason:
- generous fairway width does not compensate for imprecise approach play
  into small Ross greens
- raw distance without proximity control does not solve the course

### 2. Aggressive, low-precision pin-hunters
Reason:
- Sedgefield's small greens punish an approach that misjudges the target
  more severely than a generously-sized green complex would

### CAVEAT — do not assume TPC Twin Cities' SHORT_GAME_RELIANT anti-pattern
transfers here unchanged
At TPC Twin Cities, a short-game/putting-dependent profile is a genuine
downgrade because receptive bentgrass greens compress putting's edge. At
Sedgefield, the opposite is plausible: small, quick, breaking Ross greens
may make strong putting and short-game touch a **positive** fit signal,
not a downgrade. `engine/venue_config.py`'s `SEDGEFIELD_COUNTRY_CLUB`
anti-pattern thresholds widen the bar for flagging `SHORT_GAME_RELIANT`
(reflecting this reduced conviction) but do not yet invert or replace the
flag's underlying definition, since `engine/enrich_cards.py`'s gate logic
in this phase recognizes only the two historical flag names
(`INACCURATE_BOMBER`, `SHORT_GAME_RELIANT`) with the same trigger
direction for every venue. Resolving this properly — a Ross-green-specific
anti-pattern taxonomy — is out of scope for Phase 4.3 and is called out as
an open risk in `docs/decisions/2026_08_06_venue_config_contract.md`.

---

## 12. DEBUT FRAMEWORK

### Default treatment for course debutants
- Apply a venue-history haircut (see `engine/venue_config.py`
  `SEDGEFIELD_COUNTRY_CLUB.debut_framework`)
- Widen confidence intervals
- Do not assume strong generic form auto-translates, given the outsized
  role of green-reading experience at this venue

### Reason
Small, subtly-breaking Ross greens plausibly reward repeat exposure more
than a typical Tour green complex, making first-time-venue projections
less certain than at a more neutral course.

---

## 13. VARIANCE CLASS

### Classification
**Medium-High variance** (provisional)

### Why
- generous driving corridors and scoreable par 5s compress more of the
  field into contention range
- small green complexes create real hole-location-driven swing potential
- this classification is a doctrine-consistent inference from course
  character, not a measured statistical variance study for this venue

---

## 14. COURSE-HISTORY INTEGRATION RULE

Course history should be treated as a separate layer, not merged into
baseline fit logic — consistent with `standards/02_PGA_VENUEDNA_SCORING_SPEC.md`
§7.2/§7.4: `VenueHistoryDeltaRaw` remains `0.0` pending a separately
approved bounded transform, regardless of any venue-level course-history
emphasis described in this profile.

Use:
- course-history adjustment (once a real, approved data source exists)
- experience adjustment
- player-specific over/underperformance vs. expected

Do not let course history override:
- structural venue mismatch
- current approach-precision weakness
- active penalty/gate evidence at this specific venue

---

## 15. OFFICIAL VENUEDNA SCORING INTERPRETATION

### NeutralSkill
Player's non-venue baseline level — computed identically to every other
venue by `engine/venuedna_scoring.py`; this profile has no effect on it.

### VenueFitDelta
Computed identically to every other venue by `engine/venuedna_scoring.py`
from the dual-vector Similar Courses composite; this profile has no effect
on that canonical computation. The diagnostic/display trait weighting
described in §6 above only affects `engine/enrich_cards.py`'s historical
five-addend display trait scores and narrative tags, not this canonical
layer.

### VenueHistoryDelta
Remains `0.0` (neutral) per standards/02 §7.2/§7.4 pending a separately
approved bounded transform, exactly as at every other venue.

### Penalties / Gates
No canonical formula-v2.0.0 penalty or gate is authorized for this venue
(`penalty_gate_set_id` remains `venuedna_v2_none`). The diagnostic
`INACCURATE_BOMBER` / `SHORT_GAME_RELIANT` anti-pattern flags described in
§11 are historical/diagnostic display only.

---

## 16. PLAYER TYPES MOST LIKELY TO WIN (provisional)

- precise iron and wedge players
- strong putters on quick, subtly-breaking greens
- players with repeat Sedgefield/Wyndham course history
- players comfortable making birdies in bunches without needing to force
  aggressive approaches

---

## 17. PLAYER TYPES MOST LIKELY TO UNDERPERFORM (provisional)

- distance-first players with below-average approach precision
- players who consistently misjudge small, false-front green complexes
- first-time competitors without any green-reading history at this venue

---

## 18. IMPLEMENTATION NOTES FOR EVENT BUILDS

When this file is used for a future event package:
- keep venue logic separate from DG benchmark logic
- do not use OWGR as a scoring driver
- do not replace venue fit with recent form
- do not hardcode betting or DFS logic into core projection
- do not treat this file's mechanism claims as validated doctrine until a
  real per-player Wyndham Championship course-history dataset has been
  ingested and reviewed, per §19
- `engine/event_context.py`'s capability gate must be separately and
  explicitly authorized before this venue can drive a live producer run

---

## 19. SOURCE NOTE

This venue profile was reconstructed from Sedgefield Country Club's public
course record (architect, routing character, general yardage, and
well-established Tour-venue reputation as a Donald Ross design with small,
defensive green complexes) — general knowledge available without a
structured data source, not a DataGolf export or any other approved
VenueDNA evidence file.

**No approved course-history export (`sedgefield_country_club_CH.csv`
data rows), strokes-gained decomposition, or weather dataset exists for
this venue in this repository.** Per CLAUDE.md's prohibition on
hallucinating venue history, strokes-gained splits, or weather evidence,
this repository's paired `sedgefield_country_club_CH.csv` file contains
only the canonical header row and zero fabricated player rows. Before this
venue can be activated in `engine/event_context.py`'s capability gate or
used to drive any real scoring, an approved DataGolf course-history export
covering actual Wyndham Championship results must be ingested, and this
profile's mechanism, trait-weight, anti-pattern, and variance-class claims
should be reviewed against that real evidence and, where warranted,
revised from `RECONSTRUCTED_V1` to a validated status.
