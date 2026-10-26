# cfrp-strengthening

Carbon fiber fabric can make a weak concrete beam carry more load. The design checks for that work sit in ACI 440.2R, the guide for externally bonded FRP strengthening. This project turns those checks into small public calculations that anyone can re-run, step by step, from the inputs alone.

Status: Active. One result is recorded, for Track 1.

## What this is

- One beam at a time. The first track is a reinforced concrete beam strengthened in bending with one carbon fiber fabric system.
- Every number comes from a stated input file. A small Python program, src/flexure440.py, runs the checks it implements and prints, for each, the value, the limit, and pass or fail. Run it with `python3 src/flexure440.py tracks/track-1/input.json`. Its known gaps and defects are listed in docs/audit.md.
- Every claim carries a label: PROVEN, VERIFIED, KNOWN, or CONJECTURE. The labels are defined in CONTRIBUTING.md.

## What is known and what is ours

KNOWN, and not ours: the design method. It comes from ACI 440.2R, written by ACI Committee 440. Section numbers in this repo follow the 2017 edition, ACI 440.2R-17, which ACI PRC-440.2-23 has since superseded; see NOTICE. For the existing, unstrengthened section the checker uses the ACI 318 Whitney stress block. For the strengthened section it uses the stress block factors of ACI 440.2R-17 Chapter 10.

Ours: the code, the tests, the plain language notes, and any errors in them. This repo does not copy the text or the figures of the ACI guide. It cites the guide and uses its method.

The test for our code is a published worked example. A calculation that cannot match a published example is wrong, and this repo will say so in the open. See tracks/track-1-flexure-example.md.

## Results

| Result | Claim | Label |
|---|---|---|
| [Track 1 flexure](results/track-1-flexure/PROOF.md) | The checker reproduces the Simpson Strong-Tie worked example on ten printed quantities. Five pass or fail checks pass on that beam, with the source of each named in the result. The strengthened design strength, 481.7 kip-ft against a demand of 457.8 kip-ft, is checker output, stated as such in the result. Service concrete stress is not checked, and a hand calculation puts it above its limit; the result discloses this and does not claim serviceability. | VERIFIED for the ten printed quantities |

## Open tracks

- Track 1: flexure checks for one beam, tested against the Simpson Strong-Tie worked example. Result recorded. See tracks/README.md.
- Later tracks are listed in tracks/README.md. They open one at a time.

## Who signs for this work

Shahid Arifuddin, a civil engineer whose daily work is carbon fiber strengthening and repair of concrete and masonry structures. He directs this project and signs for its results. AI agents do code, tests, and writing under his direction, and each pull request says which agent and model did the work. See CONTRIBUTORS.md.

## Licence

Code: MIT. Text and site content: CC BY 4.0. See LICENSE and NOTICE.
