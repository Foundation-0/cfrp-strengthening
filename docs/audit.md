# Audit: what each check does and does not show

## The unit tests, tests/test_track1.py

They show the checker reproduces ten numbers printed in one published
worked example, inside stated tolerances, and that all six design checks
pass on that beam. They also run one internal variant, heavy steel on
the same beam, only to show the solver's concrete crushing path balances
forces. That variant is not a published result.

They do not show the checker is correct on other sections, other
concrete strengths, compression steel, T-beams, or continuous beams.
None of those have a test set yet.

## The result replay, results/track-1-flexure/verify.py

It shows the numbers in the result certificate replay from the input
file with the locked checker, and that the ten printed values still
match. It does not re-derive the ACI method, and it does not check the
input file against the publisher copy. That check is a human obligation,
listed in the track file.

## The design checks inside the checker

Each check compares one computed value with one code limit, for the
input beam only. A pass means the arithmetic of ACI 440.2R-17 Chapter 10,
as the checker implements it, is satisfied for those inputs. It is not a
design approval, not a field instruction, and not a substitute for the
engineer of record.

## Known weak points, stated

- The service steel stress depends on the worked example's closed form,
  which carries the initial soffit strain on the FRP force. A plain
  transformed section gives a lower, wrong-for-this-method value. The
  failed attempt is logged in the track file.
- Tolerances in expected.json cover the example's rounding, up to 1.0
  kip-ft on moments printed as whole numbers. A match inside tolerance
  is agreement with a rounded printed number, not exact equality.
- The strengthened design strength, 481.7 kip-ft, is checker output. No
  printed value for it has been read yet. See the result's PROOF.md.
