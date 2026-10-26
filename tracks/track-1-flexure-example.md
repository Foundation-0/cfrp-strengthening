# Track 1: flexure checks, one beam

## Goal

A small Python program, no added libraries, that takes one input file and
runs the flexure checks of ACI 440.2R-17 Chapter 10 for a concrete beam
strengthened with carbon fiber fabric. For each check it prints the value,
the limit, and pass or fail.

The judge is a published worked example: the Flexural Strengthening Design
Example in Simpson Strong-Tie, Composite Strengthening Systems (CSS), 2020.
It follows ACI 440.2R-17 step by step. See NOTICE.

## Inputs, as printed in the example

KNOWN, from the example. Recorded 2026-10-25.

Beam and concrete:

- Width b = 14 in. Overall depth h = 27 in.
- Steel depth d = 24 in. FRP depth df = 27 in.
- Concrete f'c = 4,000 psi. Ec = 3,605 ksi.
- Existing strain on the soffit at FRP installation, ebi = 0.0013.
- Service moment Ms = 340 k-ft, split in the example as 215 k-ft dead and
  125 k-ft live.
- Span L = 25 ft. Loads: dead wDL = 2.75 k/ft, existing live 1.00 k/ft,
  new live wLL = 1.60 k/ft.

Steel:

- fy = 60 ksi. Es = 29,000 ksi.
- Bars: 4 No. 9, As = 4.00 sq in. Steel ratio rs = 0.0119.
- Minimum steel printed as As,min = 1.12 sq in, pass.

FRP system, one ply of fabric:

- Ply thickness tf = 0.08 in. Width wf = 12 in. Af = 0.96 sq in.
- Ef = 14,200 ksi. Reported strength ffu* = 128 ksi. Reported rupture
  strain efu* = 0.0090.
- Environmental factor CE = 0.85, as used in the example. Design values:
  ffu = 108.8 ksi, efu = 0.0077.

## Results printed in the example

KNOWN, from the example. A checker earns VERIFIED only by matching these
from the inputs alone.

- Existing strength of the beam without FRP: phi Mn = 387 k-ft.
- Strengthening limit: the existing strength must cover the limit
  moment (1.1 wDL + 0.75 wLL) L^2 / 8 = 330 k-ft. 387 covers 330, pass.
  The example text cites ACI 562-16, Section 5.5.2 for this check.
- Debonding strain efd = 0.0049. Limit 0.9 times efu = 0.0069. Debonding
  controls the design strain.
- First pass with neutral axis c = 6 in: effective FRP strain efe is capped
  at efd = 0.0049, concrete strain ec = 0.0018, steel strain es = 0.0053,
  FRP stress ffe = 70 ksi, steel stress fs = 60 ksi (steel has yielded).
- Service checks: cracked section factor k = 0.3709, so kd = 8.90 in.
  Steel stress under service loads fs,s = 46.1 ksi, limit 0.80 fy = 48 ksi,
  pass. FRP stress under service loads ff,s = 8.6 ksi, limit 0.55 ffu =
  60 ksi, pass.

KNOWN, from ACI's published material on ACI 562-16 and ACI 562-13 and
from ACI 440.2R-17, not from the example (see NOTICE): the example's
citation of ACI 562-16 Section 5.5.2 is consistent with what it
computes. ACI's provisional text of ACI 562-16 gives Eq. (5.5.2) as
phi Rn >= 1.1D + 0.75L + 0.2S. ACI's webinar slides give Section 5.5.2
as two equations, (5.5.2a) 1.1D + 0.5L + 0.2S and (5.5.2b) 1.1D + 0.75L.
The published code has not been read here. In either form, 1.1 dead +
0.75 live with no snow load is a Section 5.5.2 combination, the same as
ACI 440.2R-17 Eq. (9.2). The result cites Eq. (9.2), with ACI 562-16
Section 5.5.2 as the same combination when S = 0. The 1.2D + 0.5L +
0.2S form is a different case: the extraordinary-event combination,
ACI 562-16 Section 5.5.3 (ACI 562-13 Eq. 5.5.1). Section 5.5.2.1 of the
provisional text raises the live load factor to 1.0 for sustained live
load. The checker does not model that (see #8).

## Open obligations

- Service concrete stress, ACI 440.2R-17 Section 10.2.8, is not
  checked, and the Track 1 beam fails it. By hand from the checker's
  cracked section, fc,s is about 3.38 ksi against the limit
  0.60 f'c = 2.40 ksi. Add the check in a checker pull request, issue #4
  item 1. Also confirm on the publisher copy whether the example checks
  fc,s. The parts of the example read so far do not print it.
- Extract the final converged neutral axis depth, the nominal moment Mn,
  and the design moment phi Mn printed in the example, from the publisher
  copy, and confirm the checker outputs below against them.
- Confirm the exposure statement behind CE = 0.85 on the publisher copy.
- Checker wording, for a future checker pull request: the checker's
  printed output lists the debonding strain beside its own cap as a pass
  or fail check. It is a definition with a cap, not a check. The result
  replay and the unit tests treat it that way already. The checker is
  hash locked, so this fix does not ride in a result pull request.
- Page-level citations for the inputs and results above, checked against
  the publisher copy. The values above were recorded from the example
  text. Any value the publisher copy does not confirm gets corrected
  here, in the open.

## Checker

src/flexure440.py, standard library only.
sha256: 77583629134777eb507a39cc6cb47b8297d1b5d3336f2bbea66345179a81d872

Run it:

```
python3 src/flexure440.py tracks/track-1/input.json
make verify
```

Checker output on the example inputs, 2026-10-25. Six tests pass
(tests/test_track1.py). The test file compares ten checker values with
the printed values in expected.json, and every one matches inside the
tolerance in expected.json. Each tolerance is half the precision the
example prints, except k, whose wider allowance is explained in that
file:

- ffu = 108.8 ksi. efd = 0.0049. ffe = 69.9 ksi, printed as 70 ksi.
- Existing phi Mn = 386.6 k-ft, printed as 387 k-ft.
- Strengthening limit demand = 330.1 k-ft, printed as 330 k-ft.
- As,min = 1.12 sq in. k = 0.3708, printed as 0.3709. kd = 8.90 in.
- Service fs,s = 46.1 ksi. Service ff,s = 8.6 ksi.

Checker outputs that are not printed in the parts of the example read so
far, so they carry no VERIFIED label yet:

- Converged neutral axis c = 7.49 in. Mode: FRP debonding controls.
- Strengthened Mn = 535.3 k-ft. phi = 0.90, so phi Mn = 481.7 k-ft.
- Design demand from the printed loads, Mu = (1.2 wDL + 1.6 wLL) L^2 / 8
  = 457.8 k-ft. phi Mn covers Mu, pass.

Result recorded 2026-10-25 in results/track-1-flexure/. The result
stands on the matched printed values alone. The strengthened phi Mn
stays labelled checker output there until the publisher copy confirms
it.

## Failed attempts

- A first service stress run with a plain transformed section gave
  fs,s = 41.8 ksi, not the printed 46.1 ksi. The plain section ignores
  the initial soffit strain on the FRP force. The example's closed form
  carries that strain, and the checker now uses it. Recorded here so the
  next reader does not repeat it.
- An earlier version of this file and of the result's PROOF.md said the
  combination of ACI 562-16 Section 5.5.2 is 1.2 dead + 0.5 live,
  320.3 k-ft on these loads, so the example mis-cites it. That was
  wrong. 1.2D + 0.5L + 0.2S is the extraordinary-event combination,
  Section 5.5.3. Section 5.5.2 contains 1.1D + 0.75L (with + 0.2S in the
  provisional text), which is what the example computes, and the
  checker docstring's citation of it is consistent. Issue #4 item 6 rests on the same mistake; see
  #9. Recorded here so the next reader does not repeat it.
