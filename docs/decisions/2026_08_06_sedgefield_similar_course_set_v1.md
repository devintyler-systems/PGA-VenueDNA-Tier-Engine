# Sedgefield Similar-Course Set v1

**PROVENANCE DECISION — NOT A SOURCE MANIFEST**

**NOT EVENT INITIALIZATION**

**NOT AUTHORIZATION TO RUN WYNDHAM**

## Decision

This records the operator-supplied Sedgefield Country Club comparison-course
universe for a future governed intake. It does not state or assume the source
algorithm used to generate the similarity scores.

```text
similar_course_set_id:
  sedgefield_country_club_similarity_top21

set_version:
  1.0

set_provenance:
  Operator-supplied Course Similarity Scores for Sedgefield Country Club;
  top-21 ranked course universe recorded in
  docs/decisions/2026_08_06_sedgefield_similar_course_set_v1.md;
  supplied 2026-08-06.

horizon_months:
  6 / 12 / 24, matching each respective source-manifest role.
```

## Recorded operator-supplied universe

| Rank | Course | Similarity score |
| ---: | --- | ---: |
| 1 | TPC Sawgrass (THE PLAYERS Stadium Course) | 91.2 |
| 2 | TPC River Highlands | 87.7 |
| 3 | TPC Twin Cities | 84.9 |
| 4 | Sherwood Country Club | 84.8 |
| 5 | Oakdale Golf & Country Club | 82.5 |
| 6 | Innisbrook Resort (Copperhead Course) | 81.9 |
| 7 | The Concession Golf Club | 81.8 |
| 8 | Muirfield Village Golf Club | 81.4 |
| 9 | Dye's Valley Course | 81.0 |
| 10 | The Country Club | 80.2 |
| 11 | Montreux Golf & Country Club | 79.2 |
| 12 | East Lake Golf Club | 78.9 |
| 13 | Royal Troon | 78.5 |
| 14 | TPC Deere Run | 78.3 |
| 15 | PGA West (Nicklaus) | 77.9 |
| 16 | Robert Trent Jones GC | 77.0 |
| 17 | Sea Island Golf Club (Plantation Course) | 76.6 |
| 18 | El Cardonal at Diamante | 76.3 |
| 19 | TPC Potomac at Avenel Farm | 76.1 |
| 20 | Albany GC | 75.7 |
| 21 | Shinnecock Hills GC | 75.1 |

## Scope limits

This decision does not create, modify, or authorize a `source_manifest.json`.
It does not authorize Sedgefield as `PRODUCTION_SUPPORTED`, create an event,
change venue trait weights, scoring, penalties, gates, or player projections.
Any future event-specific manifest must separately bind physical sources and
repeat the recorded metadata for each `venue_fit.similar_sg.{6m,12m,24m}` role,
with `horizon_months` equal to 6, 12, and 24 respectively.
