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

Steel:

- fy = 60 ksi. Es = 29,000 ksi.
- Steel ratio printed as rs = 0.0119, which gives As = 4.00 sq in over
  b times d. The bar layout behind that area is an open obligation below.

FRP system, one ply of fabric:

- Ply thickness tf = 0.08 in. Width wf = 12 in. Af = 0.96 sq in.
- Ef = 14,200 ksi. Reported strength ffu* = 128 ksi. Reported rupture
  strain efu* = 0.0090.
- Environmental factor CE = 0.85, as used in the example. Design values:
  ffu = 108.8 ksi, efu = 0.0077.

## Results printed in the example

KNOWN, from the example. A checker earns VERIFIED only by matching these
from the inputs alone.

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
  copy. Record the page for each number.
- Extract the demand the example designs for, and its strengthening limit
  check, with pages.
- Confirm the steel bar layout behind As = 4.00 sq in.
- Confirm the exposure behind CE = 0.85.
- Page-level citations for the inputs and results above, checked against
  the publisher copy. The values above were recorded from the example
  text. Any value the publisher copy does not confirm gets corrected here,
  in the open, before the checker pull request opens.

## Checker

None yet. Checker hash: not recorded, because no checker exists.
The checker pull request and the first result pull request are separate,
per CONTRIBUTING.md.

## Failed attempts

None yet.
