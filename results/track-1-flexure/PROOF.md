# Track 1 result: flexure checks for the worked example beam

## Statement

For the beam in tracks/track-1/input.json, the checker in this repo
reproduces the published worked example it was tested against, on the
ten quantities listed under Evidence below. That match is the result.
What the checker then computes for design strength on this beam is
stated separately, as checker output, in the same section.

The beam: 14 in wide, 27 in deep, 4 No. 9 bars, concrete 4,000 psi, one
ply of carbon fabric on the soffit. Source of every input: Simpson
Strong-Tie, Composite Strengthening Systems (CSS), Flexural
Strengthening Design Example, 2020. See NOTICE.

## Evidence and labels

VERIFIED, by finite check: ten quantities the example prints. The
checker, run from the input file alone, matches each one inside the
tolerance in tracks/track-1/expected.json. verify.py in this folder
replays the match. The ten: design FRP strength, debonding strain, FRP
stress, existing design strength, strengthening limit demand, minimum
steel, cracked section factor k, kd, service steel stress, service FRP
stress. One of the ten needs its note: the FRP stress is the capped
stress, Ef times the debonding strain. The example prints it at a trial
depth. The cap makes it the same value at the converged depth, and the
match is a match of that capped stress.

Computed by that checker, and labelled as checker output, not as
printed values: the converged section and the strengthened strength.
The parts of the example read so far do not print them. The open
obligation to confirm them against the publisher copy stays open in
tracks/track-1-flexure-example.md, and this result does not depend on
closing it, because the match above stands on the printed values alone.

KNOWN: the method. ACI 440.2R-17, by ACI Committee 440. Nothing in this
result is a new method, and nothing here claims novelty.

## Numbers

From certificate.json in this folder. Reproduce with verify.py.

| Quantity | Value | Label |
|---|---|---|
| Design FRP strength ffu | 108.8 ksi | VERIFIED, printed |
| Debonding strain efd | 0.0049, limit 0.0069 | VERIFIED, printed |
| Neutral axis c | 7.49 in | checker output |
| Governing mode | FRP debonding controls | checker output |
| Capped FRP stress ffe | 69.9 ksi | VERIFIED, printed 70 at a trial depth |
| Existing design strength | 386.6 kip-ft | VERIFIED, printed 387 |
| Strengthening limit demand | 330.1 kip-ft | VERIFIED, printed 330 |
| Minimum steel As,min | 1.12 sq in | VERIFIED, printed |
| Strengthened nominal Mn | 535.3 kip-ft | checker output |
| Strengthened design phi Mn | 481.7 kip-ft | checker output |
| Design demand Mu | 457.8 kip-ft | from printed loads |
| Service steel stress | 46.1 ksi, limit 48 | VERIFIED, printed |
| Service FRP stress | 8.6 ksi, limit 59.8 | VERIFIED, printed |

Five pass or fail checks pass on this beam, each with its source:

| Check | Source |
|---|---|
| Design strength, phi Mn against Mu | ACI 440.2R-17, Chapter 10 |
| Service steel stress | ACI 440.2R-17, Section 10.2.8, steel limit only |
| Service FRP stress | ACI 440.2R-17, Section 10.2.9 |
| Minimum steel | ACI 318, as the example cites it |
| Strengthening limit | ACI 440.2R-17, Eq. (9.2), as the example computes it |

The combination the example computes for the strengthening limit is
1.1 dead + 0.75 live, which is Eq. (9.2). The example text cites
ACI 562-16, Section 5.5.2 for the check. That section's own combination
is different: 1.2 dead + 0.5 live gives 320.3 kip-ft here, not the
printed 330. Track 2 covers the fire case and the rest of Section 9.2.

The debonding strain is a definition, not a sixth check: the formula
value, capped at 0.9 times the design rupture strain. The replay asserts
the cap is applied, and a unit test drives an input whose uncapped
strain runs far past the cap to prove the cap holds.

## How the numbers are derived

The checker follows the example's own steps. Design FRP values take the
environmental factor 0.85 off the reported strength and rupture strain.
The debonding strain uses the ACI 440.2R-17 formula and is capped at
0.9 times the design rupture strain. The section is solved by bisection
on the neutral axis: strain compatibility gives the FRP, steel, and
concrete strains at each trial depth, the strain-based stress block
gives the compression, and the depth settles where compression and
tension agree. Moment strength adds the steel part and the FRP part,
with the 0.85 factor on the FRP part, then the strength reduction
factor from the steel strain. Existing strength uses the plain Whitney
block with no FRP. Service stresses use the cracked section factor and
the example's closed form, which carries the initial soffit strain,
0.0013, on the FRP force.

Full formulas and limits are in the checker, src/flexure440.py, whose
hash is locked in the track file and in certificate.json.

## Scope

Rectangular section, tension steel only, one fabric system on the
soffit. No shear, no anchorage, no deflection, no fire design. One beam,
one published example. A match on one example shows the checker follows
the method on that example. It does not show the checker is right on
beams unlike this one, and it is not a design for any real structure.

One gap is stated plainly. Section 10.2.8 also limits concrete
compressive stress under service loads, and neither the checker nor the
example's printed checks cover it. By hand from the checker's cracked
section (kd = 8.90 in, service steel stress 46.1 ksi) the concrete
stress is about 3.38 ksi. That is above the limit, 1.8 ksi at
0.45 f'c and 2.4 ksi at 0.60 f'c. So on that one service limit this
beam fails, and this result does not claim serviceability. Adding the
check belongs to the checker pull request; it is item 1 of issue #4.

## Reproduce

```
python3 results/track-1-flexure/verify.py
make verify
```

## Open obligations

- Add the service concrete stress check (Section 10.2.8) in a checker
  pull request, issue #4 item 1. The result then gets regenerated.
- Confirm the strengthened phi Mn and converged c against the publisher
  copy of the example, and record the pages.
- Confirm the exposure statement behind the factor 0.85.
- Add page citations for the printed values.
