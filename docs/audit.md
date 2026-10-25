# Audit: what each check does and does not show

## The unit tests, tests/test_track1.py

They show the checker reproduces ten numbers printed in one published
worked example, inside stated tolerances, and that the five pass or
fail design checks pass on that beam. Two cap tests drive the debonding
strain formula on synthetic inputs to show the 0.9 cap is applied, and
not applied when the formula stays under it. They also run one internal
variant, heavy steel on the same beam, only to show the solver's
concrete crushing path balances forces. That variant is not a published
result.

They do not show the checker is correct on other sections, other
concrete strengths, compression steel, T-beams, or continuous beams.
None of those have a test set yet.

## The result replay, results/track-1-flexure/verify.py

It shows the numbers in the result certificate replay from the input
file with the locked checker, and that the ten printed values still
match. Locked means the replay compares the checker's hash with the
hash recorded in the track file, and fails on any difference, in replay
and in certificate writing alike. A failing result cannot be certified:
the write path runs the same evaluation and refuses. It does not
re-derive the ACI method, and it does not check the input file against
the publisher copy. That check is a human obligation, listed in the
track file.

## The design checks inside the checker

Each check compares one computed value with one code limit, for the
input beam only. The sources differ by check, and the result's PROOF.md
names them: three from ACI 440.2R-17, minimum steel from ACI 318, the
strengthening limit from ACI 562-16 in the form the example uses. A pass
means the arithmetic, as the checker implements it, is satisfied for
those inputs. It is not a design approval, not a field instruction, and
not a substitute for the engineer of record.

One wording debt sits in the checker itself: its printed output lists
the debonding strain beside its own cap as if it were a pass or fail
check. It is a definition. The fix belongs to a checker pull request,
because the checker is hash locked, and it is recorded as an obligation
in the track file.

## Known weak points, stated

- The service steel stress depends on the worked example's closed form,
  which carries the initial soffit strain on the FRP force. A plain
  transformed section gives a lower, wrong-for-this-method value. The
  failed attempt is logged in the track file.
- Tolerances in expected.json are half the precision the example
  prints, value by value, with one stated exception. For the cracked
  section factor k, the checker computes 0.37080 from unrounded ratios
  and the example prints 0.3709 from its rounded intermediates. The k
  tolerance is 0.001, an allowance for that difference, written in the
  file itself. Every other value matches inside its half precision.
- The strengthened design strength, 481.7 kip-ft, is checker output. No
  printed value for it has been read yet. See the result's PROOF.md.
