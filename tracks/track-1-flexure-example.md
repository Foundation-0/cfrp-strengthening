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
- Support condition: simple span under uniform load. Fiber: carbon.

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
  The example text cites ACI 562-16, Section 5.5.2 for this check, but
  the combination it computes, 1.1 dead + 0.75 live, is ACI 440.2R-17
  Eq. (9.2). The 562 combination (1.2 dead + 0.5 live) gives 320.3 k-ft,
  not the printed 330. The result cites Eq. (9.2), as computed.
- Debonding strain efd = 0.0049. Limit 0.9 times efu = 0.0069. Debonding
  controls the design strain.
- First pass with neutral axis c = 6 in: effective FRP strain efe is capped
  at efd = 0.0049, concrete strain ec = 0.0018, steel strain es = 0.0053,
  FRP stress ffe = 70 ksi, steel stress fs = 60 ksi (steel has yielded).
- Service checks: cracked section factor k = 0.3709, so kd = 8.90 in.
  Steel stress under service loads fs,s = 46.1 ksi, limit 0.80 fy = 48 ksi,
  pass. FRP stress under service loads ff,s = 8.6 ksi, limit 0.55 ffu =
  60 ksi, pass.

## Open obligations

- Extract the final converged neutral axis depth, the nominal moment Mn,
  and the design moment phi Mn printed in the example, from the publisher
  copy, and confirm the checker outputs below against them.
- Confirm the exposure statement behind CE = 0.85 on the publisher copy.
- Checker wording, done in the issue #4 checker pull request: the
  checker's printed output now names the debonding strain line as the
  definition it is, prints strains at four decimals, and sends its JSON
  to stdout with the check lines on stderr.
- Page-level citations for the inputs and results above, checked against
  the publisher copy. The values above were recorded from the example
  text. Any value the publisher copy does not confirm gets corrected
  here, in the open.

## Checker

src/flexure440.py, standard library only.
sha256: 4e6b31184ac13508bb22e676149d072f8ca90ae72c3976a73a16b48100caf42c

Run it:

```
python3 src/flexure440.py tracks/track-1/input.json
make verify
```

Checker output on the example inputs, 2026-10-25. Eighteen tests pass
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

Checker revision, 2026-10-25, for issue #4. The checker changed, and
its hash above is the new lock. What changed: the service concrete
stress check of Section 10.2.8 is in, and this beam fails it (3.38 ksi
against a limit of 1.8 ksi). The existing strength no longer assumes
the steel yields. The crushing mode uses the Whitney block. The solver
refuses an unbalanced section instead of reporting one. FRP strain is
clamped at zero. Mu includes the 1.4 dead load combination. The
support condition and the fiber type are inputs, and the creep rupture
stress is taken at the sustained moment when one is given. The printed
values this track is tested against did not change. The result in
results/track-1-flexure/ still belongs to the old checker until a
result pull request regenerates its certificate against this one.

## Failed attempts

- A first service stress run with a plain transformed section gave
  fs,s = 41.8 ksi, not the printed 46.1 ksi. The plain section ignores
  the initial soffit strain on the FRP force. The example's closed form
  carries that strain, and the checker now uses it. Recorded here so the
  next reader does not repeat it.
