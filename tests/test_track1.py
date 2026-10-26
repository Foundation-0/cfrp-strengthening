"""Track 1 checker tests.

Three kinds of test live here, and they are kept apart on purpose.

ExampleMatch compares checker output with numbers printed in the
Simpson Strong-Tie worked example. The mapping and tolerances live in
tracks/track-1/expected.json, shared with the result replay.

DesignOutcomes records what the checker computes for the example beam,
including the checks it passes and the one it fails. These are checker
outputs, not printed values, and the class name says so.

The next classes are unit tests for single behaviours the review
in issue #4 named: the concrete service stress, the yield assumption in
the existing strength, the Whitney block in crushing mode, the balance
guards, the FRP compression clamp, the 1.4D combination, the support
condition, and the fiber creep factor. Each was written against the
behaviour the old checker got wrong.

The last classes cover the audit fixes: the substrate gate, the
sustained live load factor, input validation, every force equilibrium
of the section, and the command line exit codes. They run variants of
the Track 1 beam against values worked by hand, written in the
comments. Those are not published results and prove nothing about the
example.

Run: python3 -m unittest discover -s tests -v
"""

import contextlib
import io
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CHECKER = os.path.join(ROOT, "src", "flexure440.py")
TRACK1 = os.path.join(ROOT, "tracks", "track-1", "input.json")
sys.path.insert(0, os.path.join(ROOT, "src"))

import flexure440  # noqa: E402

SUBSTRATE = "Substrate strength, f'c >= 2500 psi (ACI 440.2R-17 1.2.1.4)"
PULL_OFF = "Substrate pull-off strength >= 200 psi (ACI 440.2R-17 1.2.1.4)"
FC_SERVICE = "Service concrete stress, fc,s <= 0.60 f'c (ACI 440.2R-17 10.2.8)"


def load(name):
    with open(os.path.join(ROOT, "tracks", "track-1", name), encoding="utf-8") as fh:
        return json.load(fh)


def resolve(out, dotted):
    node = out
    for part in dotted.split("."):
        node = node[part]
    return node


def variant(**changes):
    """Input with dotted-key changes, e.g. variant(**{'steel.As_in2': 8})."""
    inp = load("input.json")
    for dotted, value in changes.items():
        node = inp
        parts = dotted.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
    return inp


def verdicts(out):
    return {name: ok for name, _v, _l, ok in out["checks"]}


class ExampleMatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inp = load("input.json")
        cls.out = flexure440.run(cls.inp)
        cls.exp = load("expected.json")

    def test_printed_values(self):
        for key, spec in self.exp["values"].items():
            got = resolve(self.out, spec["field"])
            self.assertAlmostEqual(got, spec["printed"], delta=spec["tol"],
                                   msg=f"{key}: checker {got} vs printed {spec['printed']}")

    def test_trial_state_at_c6(self):
        mat = flexure440.design_material(self.inp)
        efd, _raw = flexure440.debonding_strain(self.inp, mat)
        st = flexure440.section_state(self.exp["trial"]["c_in"], self.inp, mat, efd)
        got = {"ec": st["ec"], "efe": st["efe"], "es": st["es"],
               "ffe_ksi": st["ffe_ksi"], "fs_ksi": st["fs_ksi"]}
        for key, spec in self.exp["trial"]["values"].items():
            self.assertAlmostEqual(got[key], spec["printed"], delta=spec["tol"],
                                   msg=f"trial {key}: checker {got[key]} "
                                       f"vs printed {spec['printed']}")

    def test_force_balance(self):
        self.assertAlmostEqual(self.out["section"]["balance_kips"], 0.0, delta=0.05)


class DesignOutcomes(unittest.TestCase):
    """Checker outcomes for the example beam. Not printed values."""

    @classmethod
    def setUpClass(cls):
        cls.out = flexure440.run(load("input.json"))
        cls.checks = {name: ok for name, _v, _l, ok in cls.out["checks"]}

    def outcome(self, startswith):
        for name, ok in self.checks.items():
            if name.startswith(startswith):
                return ok
        raise AssertionError(f"no check starts with {startswith}")

    def test_passing_checks(self):
        for prefix in ("Substrate strength", "Minimum steel", "Debonding strain applied",
                       "Strengthening limit", "Design strength",
                       "Service steel stress", "Service FRP creep"):
            self.assertTrue(self.outcome(prefix), msg=prefix)

    def test_concrete_service_stress_fails(self):
        # Issue #4, item 1. The example does not print this check.
        # fc,s = Ec (fs,s/Es) kd/(d - kd)
        #      = 3605 * (46.131/29000) * 8.8991/(24 - 8.8991) = 3.379 ksi.
        # ACI 440.2R-17 10.2.8 limit 0.60 f'c = 0.60 * 4.0 = 2.40 ksi, so FAIL.
        # (0.45 f'c = 1.80 ksi was the 2008 edition.)
        self.assertFalse(self.checks[FC_SERVICE])
        self.assertAlmostEqual(self.out["service"]["fc_service_ksi"], 3.379, delta=0.001)
        self.assertAlmostEqual(self.out["service_limits"]["fc_service_ksi"], 2.40, delta=1e-9)


class DebondingCap(unittest.TestCase):
    def test_cap_applies_when_formula_runs_past_it(self):
        inp = variant(**{"frp.tf_in": 0.01, "frp.Ef_ksi": 5000.0})
        mat = flexure440.design_material(inp)
        efd, raw = flexure440.debonding_strain(inp, mat)
        self.assertGreater(raw, 0.9 * mat["efu"])
        self.assertAlmostEqual(efd, 0.9 * mat["efu"], places=12)

    def test_example_stays_under_cap(self):
        inp = load("input.json")
        mat = flexure440.design_material(inp)
        efd, raw = flexure440.debonding_strain(inp, mat)
        self.assertLess(raw, 0.9 * mat["efu"])
        self.assertAlmostEqual(efd, raw, places=12)


class ExistingStrengthYield(unittest.TestCase):
    """Issue #4, item 2: the steel does not always yield."""

    def test_over_reinforced_section_is_not_overstated(self):
        inp = variant(**{"steel.As_in2": 12.0})
        ex = flexure440.existing_strength(inp)
        # Strain compatibility gives about 896 kip-ft. The old assumed-yield
        # block gave about 986 kip-ft.
        self.assertAlmostEqual(ex["Mn_kipft"], 896.0, delta=9.0)
        self.assertLess(ex["es"], 60.0 / 29000.0)

    def test_very_heavy_steel_stays_sane(self):
        inp = variant(**{"steel.As_in2": 40.0})
        ex = flexure440.existing_strength(inp)
        self.assertGreater(ex["Mn_kipft"], 0.0)
        self.assertLessEqual(ex["a_in"], inp["beam"]["h_in"])


class CrushingBlock(unittest.TestCase):
    """Issue #4, item 3 and test item 12: Whitney block when crushing."""

    def test_whitney_factors_and_phi(self):
        inp = variant(**{"steel.As_in2": 8.0})
        out = flexure440.run(inp)
        st = out["section"]
        self.assertEqual(st["mode"], "concrete crushing controls")
        self.assertAlmostEqual(st["alpha1"], 0.85, places=12)
        self.assertAlmostEqual(st["beta1"], 0.85, places=12)
        self.assertAlmostEqual(st["balance_kips"], 0.0, delta=0.05)
        esy = inp["steel"]["fy_ksi"] / inp["steel"]["Es_ksi"]
        self.assertAlmostEqual(out["phi"], flexure440.phi_for(st["es"], esy), places=12)

    def test_beta1_drops_at_higher_concrete_strength(self):
        inp = variant(**{"steel.As_in2": 8.0, "concrete.fc_ksi": 6.0})
        mat = flexure440.design_material(inp)
        efd, _raw = flexure440.debonding_strain(inp, mat)
        [st] = flexure440.solve_section(inp, mat, efd)
        self.assertEqual(st["mode"], "concrete crushing controls")
        self.assertAlmostEqual(st["beta1"], 0.75, places=12)


class BalanceGuards(unittest.TestCase):
    """Issue #4, item 4: no silent endpoint with a large imbalance."""

    def test_no_tension_steel_or_frp_raises(self):
        inp = variant(**{"steel.As_in2": 0.0, "frp.wf_in": 0.0})
        with self.assertRaises(flexure440.InputError):
            flexure440.run(inp)

    def test_reviewers_case_is_raised_or_balanced(self):
        inp = variant(**{"concrete.fc_ksi": 3.0, "concrete.Ec_ksi": 6000.0,
                         "steel.As_in2": 8.0})
        try:
            out = flexure440.run(inp)
        except flexure440.SolverError:
            return
        self.assertAlmostEqual(out["section"]["balance_kips"], 0.0, delta=1.0)
        self.assertLess(out["section"]["c_in"], inp["beam"]["d_in"])


class FrpCompressionClamp(unittest.TestCase):
    """Issue #4, item 5: FRP is never counted in compression."""

    def test_frp_stress_not_negative(self):
        # As 12, ebi 0.003, c = 20 in: efe = 0.003*(27 - 20)/20 - 0.003
        # = -0.00195, so the FRP force is dropped. The steel keeps the
        # compatible strain 0.003*(24 - 20)/20 = 0.0006, not ebi*4/7.
        inp = variant(**{"steel.As_in2": 12.0, "ebi": 0.003})
        mat = flexure440.design_material(inp)
        efd, _raw = flexure440.debonding_strain(inp, mat)
        st = flexure440.section_state(20.0, inp, mat, efd)
        self.assertAlmostEqual(st["efe"], -0.00195, places=12)
        self.assertEqual(st["ffe_ksi"], 0.0)
        self.assertAlmostEqual(st["es"], 0.0006, places=12)

    def test_no_frp_force_gives_existing_strength(self):
        # Same beam: the crushing root lies above c = 0.003*27/0.006 = 13.5 in,
        # where the FRP carries nothing, so the strengthened section is the
        # existing one: c = 15.129 in by strain compatibility, phiMn 582.6.
        inp = variant(**{"steel.As_in2": 12.0, "ebi": 0.003})
        out = flexure440.run(inp)
        self.assertEqual(out["section"]["ffe_ksi"], 0.0)
        self.assertAlmostEqual(out["section"]["c_in"], out["existing"]["c_in"], places=6)
        self.assertAlmostEqual(out["phiMn_kipft"], out["existing"]["phiMn_kipft"], places=6)
        self.assertAlmostEqual(out["phiMn_kipft"], 582.6, delta=0.1)


class DemandAndInputs(unittest.TestCase):
    """Issue #4, items 7, 8 and 9."""

    def test_mu_includes_1_4_dead(self):
        inp = variant(**{"loads.wLL_new_kipft": 0.1})
        out = flexure440.run(inp)
        self.assertAlmostEqual(out["design_demand_Mu_kipft"],
                               1.4 * 2.75 * 25.0 ** 2 / 8.0, delta=0.01)

    def test_non_simple_support_refused(self):
        # Only the condition w L^2 / 8 describes is accepted, whatever its
        # case or spacing; a point load or an overhang is not, even though
        # the text starts with "simple".
        for support in ("continuous span", "simple span, point load at midspan",
                        "simple span with cantilever overhang", "simple"):
            with self.subTest(support=support):
                with self.assertRaises(flexure440.InputError):
                    flexure440.run(variant(**{"support_condition": support}))
        out = flexure440.run(variant(**{"support_condition": "Simple  span, Uniform load"}))
        self.assertEqual(out["phiMn_kipft"], flexure440.run(variant())["phiMn_kipft"])

    def test_creep_factor_follows_fiber(self):
        inp = variant(**{"frp.fiber": "glass"})
        out = flexure440.run(inp)
        self.assertAlmostEqual(out["service_limits"]["ff_service_ksi"],
                               0.20 * out["design_material"]["ffu_ksi"], delta=1e-9)

    def test_sustained_moment_lowers_frp_stress(self):
        inp = variant(**{"sustained_moment_kipft": 215.0})
        out = flexure440.run(inp)
        self.assertLess(out["service"]["ff_service_ksi"],
                        out["service"]["ff_service_full_moment_ksi"])



class Substrate(unittest.TestCase):
    """ACI 440.2R-17 1.2.1.4: f'c >= 2500 psi, pull-off >= 200 psi."""

    def test_substrate_strength(self):
        # f'c 2.0 ksi = 2000 psi < 2500 psi, FAIL. f'c 2.5 ksi = 2500 psi, PASS
        # at the limit. Ec = 57 sqrt(f'c psi): 2549 ksi and 2850 ksi.
        for fc, ok in ((2.0, False), (2.5, True)):
            with self.subTest(fc=fc):
                out = flexure440.run(variant(**{
                    "concrete.fc_ksi": fc, "concrete.Ec_ksi": 57.0 * math.sqrt(fc * 1000.0)}))
                row = [c for c in out["checks"] if c[0] == SUBSTRATE][0]
                self.assertEqual(row[1:], (fc * 1000.0, 2500.0, ok))

    def test_pull_off(self):
        # 150 psi < 200 psi FAIL; 200 psi at the limit and 250 psi PASS.
        # With a pull-off value only the substrate condition stays not checked.
        for psi, ok in ((150.0, False), (200.0, True), (250.0, True)):
            with self.subTest(psi=psi):
                out = flexure440.run(variant(**{"substrate.pull_off_psi": psi}))
                self.assertIs(verdicts(out)[PULL_OFF], ok)
                self.assertEqual(len(out["not_checked"]), 1)
                self.assertTrue(out["not_checked"][0].startswith("Substrate condition"))

    def test_pull_off_absent_is_not_checked(self):
        out = flexure440.run(load("input.json"))
        self.assertNotIn(PULL_OFF, verdicts(out))
        self.assertEqual(len(out["not_checked"]), 2)
        self.assertTrue(out["not_checked"][0].startswith(PULL_OFF))
        self.assertTrue(out["not_checked"][1].startswith("Substrate condition"))


class SustainedLiveLoad(unittest.TestCase):
    """ACI 440.2R-17 9.2, ACI 562-16 5.5.2.1: 1.0 on sustained live load."""

    def test_factor_and_label(self):
        # Not sustained: (1.1*2.75 + 0.75*1.6) * 25^2/8 = 4.225*78.125 = 330.08 kip-ft.
        # Sustained:     (1.1*2.75 + 1.0*1.6) * 25^2/8 = 4.625*78.125 = 361.33 kip-ft.
        # Existing phiMn 386.62 covers both.
        for sustained, factor, demand in ((False, 0.75, 330.078125), (True, 1.0, 361.328125)):
            with self.subTest(sustained=sustained):
                out = flexure440.run(variant(**{"loads.live_load_sustained": sustained}))
                lim = out["strengthening_limit"]
                self.assertEqual(lim["live_load_factor"], factor)
                self.assertAlmostEqual(lim["limit_demand_kipft"], demand, places=9)
                label = f"Strengthening limit, phiMn existing >= 1.1DL + {factor}LL moment"
                self.assertTrue(verdicts(out)[label])

    def test_factor_flips_verdict(self):
        # wLL_new = 2.5 kip/ft, existing phiMn = 386.62 kip-ft:
        # 0.75: (3.025 + 1.875) * 78.125 = 382.81 kip-ft, PASS.
        # 1.0:  (3.025 + 2.5) * 78.125 = 431.64 kip-ft, FAIL.
        for sustained, demand, ok in ((False, 382.8125, True), (True, 431.640625, False)):
            with self.subTest(sustained=sustained):
                out = flexure440.run(variant(**{"loads.wLL_new_kipft": 2.5,
                                                "loads.live_load_sustained": sustained}))
                self.assertAlmostEqual(out["strengthening_limit"]["limit_demand_kipft"],
                                       demand, places=9)
                self.assertIs(out["strengthening_limit"]["pass"], ok)


class Validation(unittest.TestCase):
    """Bad input stops before any calculation, naming the field."""

    def test_bad_inputs_name_the_field(self):
        cases = [
            ("frp.wf_in", {"frp.wf_in": 15.0}),
            ("beam.df_in", {"beam.df_in": 23.0}),
            ("beam.df_in", {"beam.df_in": 24.0}),
            ("beam.h_in", {"beam.h_in": 26.0}),
            ("frp.CE", {"frp.CE": 0.96}),
            ("frp.CE", {"frp.CE": 0}),
            ("frp.plies", {"frp.plies": 1.5}),
            ("frp.plies", {"frp.plies": True}),
            ("frp.plies", {"frp.plies": -1}),
            ("steel.As_in2", {"steel.As_in2": True}),
            ("steel.As_in2", {"steel.As_in2": "4.0"}),
            ("concrete.fc_ksi", {"concrete.fc_ksi": float("nan")}),
            ("frp.efu_star", {"frp.efu_star": float("inf")}),
            ("span_ft", {"span_ft": 10 ** 400}),
            ("loads.wDL_kipft", {"loads.wDL_kipft": -1.0}),
            ("loads.wLL_new_kipft", {"loads.wLL_new_kipft": -1.0}),
            ("loads.wLL_existing_kipft", {"loads.wLL_existing_kipft": -1.0}),
            ("ebi", {"ebi": -0.001}),
            ("beam", {"beam": 5}),
            ("support_condition", {"support_condition": "cantilever"}),
            ("support_condition", {"support_condition": None}),
            ("frp.fiber", {"frp.fiber": "basalt"}),
            ("frp.fiber", {"frp.fiber": ["carbon"]}),
            ("sustained_moment_kipft", {"sustained_moment_kipft": -1.0}),
            ("sustained_moment_kipft", {"sustained_moment_kipft": 341.0}),
            ("sustained_moment_kipft", {"sustained_moment_kipft": None}),
            ("loads.live_load_sustained", {"loads.live_load_sustained": "yes"}),
            ("loads.live_load_sustained", {"loads.live_load_sustained": 1}),
            ("loads.live_load_sustaned", {"loads.live_load_sustaned": True}),
            ("substrate.pull_off_psi", {"substrate.pull_off_psi": -5.0}),
            ("substrate.pull_off_psi", {"substrate.pull_off_psi": True}),
            ("substrate.pulloff_psi", {"substrate.pulloff_psi": 250.0}),
            ("substrate", {"substrate": []}),
        ]
        for name in flexure440.POSITIVE:
            cases += [(name, {name: 0}), (name, {name: -1.0})]
        for name, changes in cases:
            with self.subTest(changes=changes):
                with self.assertRaises(flexure440.InputError) as ctx:
                    flexure440.run(variant(**changes))
                self.assertIn(name, str(ctx.exception))

    def test_plies_zero_is_refused_with_a_reason(self):
        # Issue #6, item 3: plies 0 used to divide by zero in the efd formula.
        with self.assertRaises(flexure440.InputError) as ctx:
            flexure440.run(variant(**{"frp.plies": 0}))
        self.assertIn("frp.plies must be a JSON integer >= 1, got 0", str(ctx.exception))
        self.assertIn("unstrengthened", str(ctx.exception))

    def test_unknown_loads_key_is_refused(self):
        # A typo must not silently drop the sustained factor back to 0.75.
        with self.assertRaises(flexure440.InputError) as ctx:
            flexure440.run(variant(**{"loads.live_load_sustaned": True}))
        self.assertIn("loads.live_load_sustaned is not a known input", str(ctx.exception))

    def test_missing_keys(self):
        for group, key in (("concrete", "Ec_ksi"), ("frp", "plies"), (None, "ebi"),
                           (None, "support_condition")):
            with self.subTest(key=key):
                inp = load("input.json")
                del (inp[group] if group else inp)[key]
                with self.assertRaises(flexure440.InputError) as ctx:
                    flexure440.run(inp)
                self.assertIn(f"missing input {group + '.' if group else ''}{key}",
                              str(ctx.exception))

    def test_boundary_values_are_accepted(self):
        # CE = 0.95 is the ACI 440.2R-17 Table 9.4 maximum, wf = b is full
        # width, df = h is the soffit, and the sustained moment may equal Ms.
        for changes in ({"frp.CE": 0.95}, {"frp.wf_in": 14.0}, {"beam.df_in": 27.0},
                        {"sustained_moment_kipft": 340.0}, {"frp.fiber": "aramid"},
                        {"substrate.pull_off_psi": 0}):
            with self.subTest(changes=changes):
                flexure440.run(variant(**changes))

    def test_duplicate_key_and_byte_order_mark(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        with open(TRACK1, encoding="utf-8") as fh:
            text = fh.read()
        dup = text.replace('"As_in2":4.0', '"As_in2":2.0,"As_in2":4.0')
        self.assertNotEqual(dup, text)
        dup_path = os.path.join(tmp.name, "dup.json")
        bom_path = os.path.join(tmp.name, "bom.json")
        with open(dup_path, "w", encoding="utf-8") as fh:
            fh.write(dup)
        with open(bom_path, "w", encoding="utf-8-sig") as fh:
            fh.write(text)
        with self.assertRaises(flexure440.InputError) as ctx:
            flexure440.read_input(dup_path)
        self.assertIn("duplicate key 'As_in2'", str(ctx.exception))
        self.assertEqual(flexure440.read_input(bom_path), load("input.json"))


class Equilibria(unittest.TestCase):
    """Every force equilibrium on 0 < c < df; the lowest phiMn is used."""

    def residuals_ok(self, inp, out):
        mat = flexure440.design_material(inp)
        efd, _raw = flexure440.debonding_strain(inp, mat)
        for root in out["section_roots"]:
            st = flexure440.section_state(root["c_in"], inp, mat, efd)
            self.assertLessEqual(abs(st["balance_kips"]), 1e-6 * st["tension_kips"])

    def check_roots(self, out, hand):
        roots = out["section_roots"]
        self.assertEqual(len(roots), len(hand))
        for root, (mode, c, phimn) in zip(roots, hand):
            with self.subTest(c=c):
                self.assertEqual(root["mode"], mode)
                self.assertAlmostEqual(root["c_in"], c, delta=0.001)
                self.assertAlmostEqual(root["phiMn_kipft"], phimn, delta=0.02)

    def test_track1_has_one_root(self):
        out = flexure440.run(load("input.json"))
        self.assertEqual(len(out["section_roots"]), 1)
        self.assertIsNone(out["section_note"])
        self.assertAlmostEqual(out["phiMn_kipft"], 481.74, delta=0.01)

    def test_debonding_and_crushing_roots(self):
        # Track 1 beam with As = 4.829 in^2. efd = 0.004925, ebi = 0.0013.
        # Mode boundary c = 0.003*27/(0.003 + 0.004925 + 0.0013) = 8.7804 in.
        # At ec = 0.003 the parabolic block (x = 0.003/0.001886 = 1.590,
        # alpha1 beta1 = x - x^2/3 = 0.748) is stronger than Whitney's
        # 0.85*0.85 = 0.7225, so the balance drops across the boundary.
        # Debonding root: tension 4.829*60 + 0.96*14200*0.004925 = 356.88 kips,
        # 4*14*c*(x - x^2/3) = 356.88 with x = 0.006225 c/(27 - c)/0.001886
        # gives c = 8.498 in, x = 1.516, beta1 = (4 - x)/(6 - 2x) = 0.8369,
        # es = 0.006225*(24 - c)/(27 - c) = 0.005216, phi = 0.90,
        # Mn = (289.74*(24 - 3.556) + 0.816*69.94*(27 - 3.556))/12 = 605.11,
        # phiMn = 544.60 kip-ft.
        # Crushing root: 40.46 c = 289.74 + 13.632*(0.081/c - 0.0043),
        # 40.46 c^2 - 231.12 c - 1104.19 = 0, so c = 8.810 in, between the
        # boundary and the grid point above it, 27*131/400 = 8.8425 in.
        # efe = 0.081/c - 0.0043 = 0.004894 < efd, es = 0.003*(24 - c)/c
        # = 0.005172, phi = 0.90, ffe = 69.49 ksi, beta1 c/2 = 3.744 in,
        # Mn = (289.74*(24 - 3.744) + 0.816*69.49*(27 - 3.744))/12 = 598.97,
        # phiMn = 539.08 kip-ft, the lower one, so it is used.
        inp = variant(**{"steel.As_in2": 4.829})
        out = flexure440.run(inp)
        self.check_roots(out, [("FRP debonding controls", 8.498, 544.60),
                               ("concrete crushing controls", 8.810, 539.08)])
        self.assertEqual(out["section"]["mode"], "concrete crushing controls")
        self.assertAlmostEqual(out["phiMn_kipft"], 539.08, delta=0.02)
        self.assertEqual(out["section_note"],
                         "2 force equilibria, c = 8.50, 8.81 in; the lowest phiMn, "
                         "539.1 kip-ft at c = 8.81 in, is used as the conservative choice")
        self.residuals_ok(inp, out)

    def test_two_debonding_roots_in_one_cell(self):
        # f'c = 2.5 ksi, Ec = 2850 ksi, As = 2.95 in^2.
        # efd = 0.083*sqrt(2500/(14.2e6*0.08)) = 0.003894, e'c = 1.7*2.5/2850 = 0.001491.
        # Mode boundary c = 0.081/(0.003 + 0.003894 + 0.0013) = 9.886 in.
        # Tension 2.95*60 + 0.96*14200*0.003894 = 230.08 kips (the steel yields).
        # Compression 2.5*14*c*(x - x^2/3) with x = 0.005194 c/(27 - c)/0.001491.
        # c = 8.995 in: x = 1.740, 0.7308*35*8.995 = 230.1 kips, balance rising.
        # c = 9.828 in: x = 1.993, 0.6688*35*9.828 = 230.1 kips, balance falling:
        # past x = 1.5 the parabolic block softens.
        # Whitney above the boundary: 0.7225*35*9.886 = 250.0 > 230.08, no root.
        # c = 8.995: beta1 = 0.8968, es = 0.004328, phi = 0.8427, phiMn = 320.95.
        # c = 9.828: beta1 = 0.9967, es = 0.004286, phi = 0.8391,
        # Mn = (177*(24 - 4.898) + 0.816*55.29*(27 - 4.898))/12 = 364.85 kip-ft,
        # phiMn = 306.16, the lower one, so it is used.
        inp = variant(**{"concrete.fc_ksi": 2.5, "concrete.Ec_ksi": 2850.0,
                         "steel.As_in2": 2.95})
        out = flexure440.run(inp)
        self.check_roots(out, [("FRP debonding controls", 8.995, 320.95),
                               ("FRP debonding controls", 9.828, 306.16)])
        self.assertAlmostEqual(out["phiMn_kipft"], 306.16, delta=0.02)
        self.assertIn("2 force equilibria", out["section_note"])
        self.residuals_ok(inp, out)

    def test_parabolic_block_past_x_2_is_rejected(self):
        # f'c = 2.0 ksi, Ec = 57*sqrt(2000) = 2549 ksi, As = 2.0 in^2.
        # efd = 0.083*sqrt(2000/(14.2e6*0.08)) = 0.003483, e'c = 1.7*2/2549 = 0.001334.
        # Debonding: ec = 0.004783 c/(27 - c), tension 2*60 + 0.96*14200*0.003483
        # = 167.48 kips (the steel yields).
        # c = 7.975 in: x = 1.503, alpha1 beta1 = 0.750, 0.750*2*14*7.975 = 167.5,
        # beta1 = (4 - x)/(6 - 2x) = 0.834.
        # c = 10.305 in: x = 2.213, 0.580*2*14*10.305 = 167.5 kips too, but
        # beta1 = 1.136 > 1 is not a concrete stress block: rejected.
        # Mode boundary c = 0.081/(0.003 + 0.003483 + 0.0013) = 10.408 in; above it
        # Whitney gives 0.7225*2*14*10.408 = 210.6 > 167.48, no crushing root.
        # es = 0.004783*(24 - 7.975)/19.025 = 0.004028, phi = 0.8171,
        # Mn = (120*(24 - 3.326) + 0.816*49.45*(27 - 3.326))/12 = 286.36 kip-ft,
        # phiMn = 233.99 kip-ft.
        inp = variant(**{"concrete.fc_ksi": 2.0, "concrete.Ec_ksi": 57.0 * math.sqrt(2000.0),
                         "steel.As_in2": 2.0})
        out = flexure440.run(inp)
        self.check_roots(out, [("FRP debonding controls", 7.975, 233.99)])
        self.assertAlmostEqual(out["section"]["beta1"], 0.834, delta=0.001)
        mat = flexure440.design_material(inp)
        efd, _raw = flexure440.debonding_strain(inp, mat)
        self.assertIsNone(flexure440.section_state(10.305, inp, mat, efd)["beta1"])

    def test_no_equilibrium_raises(self):
        # f'c = 3 ksi, Ec = 57*sqrt(3000) = 3122 ksi, As = 3.8 in^2.
        # efd = 0.083*sqrt(3000/(14.2e6*0.08)) = 0.004265.
        # Mode boundary c = 0.081/(0.003 + 0.004265 + 0.0013) = 9.457 in.
        # e'c = 1.7*3/3122 = 0.001634, x = 0.003/e'c = 1.836,
        # parabolic alpha1 beta1 = 1.836 - 1.836^2/3 = 0.7123 < Whitney 0.7225.
        # Tension at the boundary 3.8*60 + 0.96*14200*0.004265 = 286.14 kips.
        # Compression just below 0.7123*3*14*9.457 = 282.90, just above 286.97.
        # The balance changes sign only across the jump: no equilibrium.
        # PR #7's single bisection settled on the jump, 0.8 kips out.
        inp = variant(**{"concrete.fc_ksi": 3.0, "concrete.Ec_ksi": 57.0 * math.sqrt(3000.0),
                         "steel.As_in2": 3.8})
        with self.assertRaises(flexure440.SolverError) as ctx:
            flexure440.run(inp)
        self.assertIn("c = 9.46 in", str(ctx.exception))


class CommandLine(unittest.TestCase):
    """Exit 0 every check passes, 1 a check fails, 2 the run could not finish."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        with open(TRACK1, encoding="utf-8") as fh:
            self.track1 = fh.read()

    def write(self, name, text, encoding="utf-8"):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding=encoding) as fh:
            fh.write(text)
        return path

    def cli(self, *args):
        return subprocess.run([sys.executable, CHECKER, *args],
                              capture_output=True, text=True, check=False)

    def test_track1_exits_1(self):
        res = self.cli(TRACK1)
        self.assertEqual(res.returncode, 1, res.stderr)
        lines = res.stderr.splitlines()
        self.assertIn(f"FAIL  {FC_SERVICE}: 3.38 vs limit 2.40", lines)
        self.assertIn(f"PASS  {SUBSTRATE}: 4000.00 vs limit 2500.00", lines)
        self.assertEqual(sum(line.startswith("NOT CHECKED  ") for line in lines), 2)
        self.assertFalse(any(line.startswith("NOTE  ") for line in lines))
        report = json.loads(res.stdout)
        self.assertEqual(report["not_checked"][0][:len(PULL_OFF)], PULL_OFF)
        # The saved JSON carries every verdict, so the concrete FAIL is not
        # lost when only stdout is kept.
        verdicts = {c["name"]: c["pass"] for c in report["checks"]}
        self.assertFalse(report["all_pass"])
        self.assertFalse(verdicts[FC_SERVICE])
        self.assertEqual([name for name, ok in verdicts.items() if not ok], [FC_SERVICE])

    def test_all_pass_exits_0(self):
        # b = 30 in. Cracked section: ns = 4*29000/(30*24*3605) = 0.04469,
        # nf = 0.96*14200/(30*24*3605) = 0.00525, k = 0.2721, kd = 6.530 in.
        # fs,s = 44.77 <= 48 ksi, ff,s = 7.22 <= 59.84 ksi,
        # fc,s = 3605*(44.77/29000)*6.530/(24 - 6.530) = 2.08 <= 2.40 ksi.
        # Existing c = 240/(0.85*4*0.85*30) = 2.768 in, phiMn = 0.9*240*(24 - 1.176)/12
        # = 410.82 >= 330.08. phiMn 509.59 >= Mu 457.81. As,min 2.40 <= 4.0.
        # Without a pull-off value the NOT CHECKED lines still print, and
        # they do not change the exit code.
        for changes, not_checked in (({"beam.b_in": 30.0}, 2),
                                     ({"beam.b_in": 30.0, "substrate.pull_off_psi": 250.0}, 1)):
            with self.subTest(changes=changes):
                res = self.cli(self.write("pass.json", json.dumps(variant(**changes))))
                self.assertEqual(res.returncode, 0, res.stderr)
                self.assertNotIn("FAIL", res.stderr)
                self.assertEqual(res.stderr.count("NOT CHECKED  "), not_checked)

    def test_byte_order_mark_is_read(self):
        res = self.cli(self.write("bom.json", self.track1, encoding="utf-8-sig"))
        self.assertEqual(res.returncode, 1, res.stderr)
        json.loads(res.stdout)

    def test_multiple_equilibria_print_note(self):
        res = self.cli(self.write("roots.json",
                                  json.dumps(variant(**{"steel.As_in2": 4.829}))))
        self.assertEqual(res.returncode, 1, res.stderr)
        self.assertIn("NOTE  2 force equilibria, c = 8.50, 8.81 in; the lowest phiMn, "
                      "539.1 kip-ft at c = 8.81 in, is used as the conservative choice",
                      res.stderr.splitlines())

    def test_could_not_run_exits_2(self):
        dup = self.track1.replace('"As_in2":4.0', '"As_in2":2.0,"As_in2":4.0')
        self.assertNotEqual(dup, self.track1)
        no_root = variant(**{"concrete.fc_ksi": 3.0,
                             "concrete.Ec_ksi": 57.0 * math.sqrt(3000.0), "steel.As_in2": 3.8})
        cases = {
            "missing file": ([os.path.join(self.tmp, "nope.json")], "No such file or directory"),
            "not JSON": ([self.write("bad.json", "{beam")], "not valid JSON"),
            "duplicate key": ([self.write("dup.json", dup)], "ERROR: duplicate key 'As_in2'"),
            "NaN literal": ([self.write("nan.json", self.track1.replace(
                '"fc_ksi":4.0', '"fc_ksi":NaN'))], "concrete.fc_ksi must be a finite number"),
            "bad field": ([self.write("wf.json", json.dumps(variant(**{"frp.wf_in": 20.0})))],
                          "frp.wf_in must be <= beam.b_in"),
            "plies 0": ([self.write("plies.json", json.dumps(variant(**{"frp.plies": 0})))],
                        "frp.plies must be a JSON integer >= 1, got 0"),
            "unknown loads key": ([self.write("typo.json", json.dumps(variant(
                **{"loads.live_load_sustaned": True})))], "loads.live_load_sustaned"),
            "no equilibrium": ([self.write("noroot.json", json.dumps(no_root))],
                               "no force equilibrium"),
            "not UTF-8": ([self.write("latin1.json", self.track1.replace(
                "Simpson", "Simpsén"), encoding="latin-1")], "not UTF-8 text"),
            "nested too deeply": ([self.write("deep.json", "[" * 100000 + "]" * 100000)],
                                  "nested too deeply"),
        }
        for name, (args, message) in cases.items():
            with self.subTest(name):
                res = self.cli(*args)
                self.assertEqual(res.returncode, 2, res.stderr)
                self.assertEqual(res.stdout, "")
                # a handled error is one ERROR line, never the crash handler
                self.assertTrue(res.stderr.startswith("ERROR: "), res.stderr)
                self.assertEqual(len(res.stderr.strip().splitlines()), 1, res.stderr)
                self.assertIn(message, res.stderr)

    def test_usage_error_exits_2(self):
        for args in ((), (TRACK1, TRACK1)):
            with self.subTest(args=len(args)):
                res = self.cli(*args)
                self.assertEqual(res.returncode, 2, res.stderr)
                self.assertEqual(res.stdout, "")
                self.assertIn("usage", res.stderr)

    def test_crash_exits_2_with_traceback(self):
        err = io.StringIO()
        with mock.patch.object(flexure440, "run", side_effect=RuntimeError("boom")), \
                contextlib.redirect_stderr(err):
            code = flexure440.main(["flexure440.py", TRACK1])
        self.assertEqual(code, 2)
        self.assertIn("Traceback", err.getvalue())
        self.assertIn("RuntimeError: boom", err.getvalue())
        self.assertIn("ERROR: the checker crashed", err.getvalue())


if __name__ == "__main__":
    unittest.main()
