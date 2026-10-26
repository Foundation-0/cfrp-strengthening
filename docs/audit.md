# Audit: what each check does and does not show

## The unit tests, tests/test_track1.py

They show the checker reproduces ten numbers printed in one published
worked example, inside stated tolerances, and that the five pass or
fail design checks pass on that beam. Two cap tests call the debonding
strain formula directly, one on a synthetic input to show the 0.9 cap
is applied, and one on the Track 1 input to show it is not applied when
the formula stays under it. No test runs the full solve on a beam where
the cap binds. They also run one internal
variant, heavy steel on the same beam, only to show the solver's
concrete crushing path balances forces. That variant is not a published
result. It does not check the strength on that path, and on that path
the checker uses the parabolic stress block, not the Whitney block; see
Known weak points below.

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
strengthening limit from ACI 440.2R-17 Eq. (9.2), which with no snow
load is the same combination as ACI 562-16 Section 5.5.2, the section
the example cites. A pass
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
  and the example prints 0.3709. The reason given in expected.json,
  rounded intermediates in the example, is CONJECTURE: rounding all four
  ratios gives 0.3709, but rounding only the steel ratio, the one
  intermediate the track file records, gives 0.3707. The k tolerance is
  0.001, written in the file itself; kd's tolerance of 0.005 in already
  binds k more tightly, because kd = k d. Every other value matches
  inside its half precision.
- None of the ten matched values depends on the strengthened-section
  solve: not on the converged neutral axis, the stress block, the FRP
  reduction factor psi_f, phi, or Mn. While debonding controls, the
  effective FRP stress is Ef times efd at any depth. The match does not
  exercise that part of the checker. See #11.
- The service stresses fs,s and ff,s match the printed values only with
  the example's initial soffit strain, 0.0013, taken as an input. Derived
  by the cracked-section method from the recorded dead load, it is about
  0.00125, and ff,s then falls outside its tolerance. See #11.
- The strengthened design strength, 481.7 kip-ft, is checker output. No
  printed value for it has been read yet. See the result's PROOF.md.
- Concrete compressive stress under service loads is not checked by
  the checker, and the parts of the example read so far do not print
  it. A hand calculation from the checker's cracked section gives about
  3.38 ksi, above the Section 10.2.8 limit, 0.60 f'c = 2.40 ksi. The gap
  is disclosed in the result's Scope, and the check itself is issue #4
  item 1, for a checker pull request.

Known checker defects that can overstate strength or pass a beam that
should fail. None of them changes a number or verdict for the Track 1
beam. Until they are fixed, a PASS from the checker on any beam other
than the Track 1 beam must not be relied on.

- When concrete crushing controls, the solver uses the parabolic
  stress block instead of the ACI 318 Whitney block. phi Mn comes out
  about 3% higher than the Whitney block gives at f'c = 4 ksi, and up to
  about 21% higher at 8 ksi. Issue #4 item 3.
- Existing strength assumes the tension steel yields, with no check.
  On an over-reinforced existing section it overstates existing phi Mn,
  about 10% at As = 12 sq in on the Track 1 section, and the strengthening
  limit can pass a beam that fails it. Issue #4 item 2.
- The design demand uses 1.2D + 1.6L only and leaves out 1.4D. When
  the new live load is under one eighth of the dead load, Mu is up to
  14% low and the design strength line can pass a beam that fails.
  Issue #4 item 7.
- The section solver does not check that its bisection brackets a root
  or that forces balance at the end, and h_in is not checked against d.
  An undersized h_in (under about 7.9 in for the Track 1 beam) leaves the
  section out of equilibrium, overstates phi Mn by up to about 14%, and
  can turn a FAIL into a PASS. Issue #4 item 4.
- No minimum substrate strength gate. ACI 440.2R-17 Section 1.2.1.4
  says FRP should not be used on concrete with f'c below 2,500 psi, and
  for bond-critical uses such as flexure the pull-off strength should
  be at least 200 psi. The checker accepts any f'c and has no pull-off
  input, so a beam on 2,000 psi concrete can get all PASS. See
  #8.
- No sustained live load factor. ACI 562-16 Section 5.5.2.1 raises the
  live load factor in the strengthening limit from 0.75 to 1.0 for
  sustained live load. The checker always uses 0.75, so where the live
  load is sustained its limit moment is too low. See #8.
- No input validation. A strip width wider than the beam, a thickness
  or width entered in millimetres, or zero or negative loads are
  accepted and can turn a FAIL into a PASS. Degenerate inputs crash
  with exit code 1, the same code as a design FAIL. See #8.
