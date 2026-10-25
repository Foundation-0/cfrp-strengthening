"""Track 1 checker tests.

Three kinds of test live here, and they are kept apart on purpose.

ExampleMatch compares checker output with numbers printed in the
Simpson Strong-Tie worked example. The mapping and tolerances live in
tracks/track-1/expected.json, shared with the result replay.

DesignOutcomes records what the checker computes for the example beam,
including the checks it passes and the one it fails. These are checker
outputs, not printed values, and the class name says so.

The remaining classes are unit tests for single behaviours the review
in issue #4 named: the concrete service stress, the yield assumption in
the existing strength, the Whitney block in crushing mode, the balance
guards, the FRP compression clamp, the 1.4D combination, the support
condition, and the fiber creep factor. Each was written against the
behaviour the old checker got wrong.

Run: python3 -m unittest discover -s tests -v
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

import flexure440  # noqa: E402


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
            node = node[part]
        node[parts[-1]] = value
    return inp


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
        for prefix in ("Minimum steel", "Debonding strain applied",
                       "Strengthening limit", "Design strength",
                       "Service steel stress", "Service FRP creep"):
            self.assertTrue(self.outcome(prefix), msg=prefix)

    def test_concrete_service_stress_fails(self):
        # Issue #4, item 1. The example does not print this check.
        self.assertFalse(self.outcome("Service concrete stress"))
        self.assertAlmostEqual(self.out["service"]["fc_service_ksi"], 3.38, delta=0.02)
        self.assertAlmostEqual(self.out["service_limits"]["fc_service_ksi"], 1.8, delta=1e-9)


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
        st = flexure440.solve_section(inp, mat, efd)
        self.assertEqual(st["mode"], "concrete crushing controls")
        self.assertAlmostEqual(st["beta1"], 0.75, places=12)


class BalanceGuards(unittest.TestCase):
    """Issue #4, item 4: no silent endpoint with a large imbalance."""

    def test_no_tension_steel_or_frp_raises(self):
        inp = variant(**{"steel.As_in2": 0.0, "frp.wf_in": 0.0})
        with self.assertRaises(ValueError):
            flexure440.run(inp)

    def test_reviewers_case_is_raised_or_balanced(self):
        inp = variant(**{"concrete.fc_ksi": 3.0, "concrete.Ec_ksi": 6000.0,
                         "steel.As_in2": 8.0})
        try:
            out = flexure440.run(inp)
        except ValueError:
            return
        self.assertAlmostEqual(out["section"]["balance_kips"], 0.0, delta=1.0)
        self.assertLess(out["section"]["c_in"], inp["beam"]["d_in"])


class FrpCompressionClamp(unittest.TestCase):
    """Issue #4, item 5: FRP is never counted in compression."""

    def test_frp_stress_not_negative(self):
        inp = variant(**{"steel.As_in2": 12.0, "ebi": 0.003})
        mat = flexure440.design_material(inp)
        efd, _raw = flexure440.debonding_strain(inp, mat)
        st = flexure440.section_state(20.0, inp, mat, efd)
        self.assertEqual(st["efe"], 0.0)
        self.assertEqual(st["ffe_ksi"], 0.0)


class DemandAndInputs(unittest.TestCase):
    """Issue #4, items 7, 8 and 9."""

    def test_mu_includes_1_4_dead(self):
        inp = variant(**{"loads.wLL_new_kipft": 0.1})
        out = flexure440.run(inp)
        self.assertAlmostEqual(out["design_demand_Mu_kipft"],
                               1.4 * 2.75 * 25.0 ** 2 / 8.0, delta=0.01)

    def test_non_simple_support_refused(self):
        inp = variant(**{"support_condition": "continuous span"})
        with self.assertRaises(ValueError):
            flexure440.run(inp)

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


if __name__ == "__main__":
    unittest.main()
