"""Track 1 checker tests.

The example test compares the checker against numbers printed in the
Simpson Strong-Tie worked example (tracks/track-1/expected.json). The
mapping from each printed value to a checker output, and its tolerance,
live in that file, so these tests and the result replay in
results/track-1-flexure/verify.py check the same set of values.
The cap test confirms the debonding strain cap is really applied, on a
synthetic input whose uncapped strain runs far past the cap.
The mode test is an internal sanity check only. It uses a much heavier
steel area on the same beam to confirm the solver also runs the concrete
crushing mode with a small force balance error. It is not a published
result and proves nothing about the example.

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


class ExampleMatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = flexure440.run(load("input.json"))
        cls.exp = load("expected.json")["values"]

    def test_printed_values(self):
        for key, spec in self.exp.items():
            got = resolve(self.out, spec["field"])
            self.assertAlmostEqual(got, spec["printed"], delta=spec["tol"],
                                   msg=f"{key}: checker {got} vs printed {spec['printed']}")

    def test_all_checks_pass(self):
        for name, _value, _limit, ok in self.out["checks"]:
            self.assertTrue(ok, msg=name)

    def test_force_balance(self):
        self.assertAlmostEqual(self.out["section"]["balance_kips"], 0.0, delta=0.05)


class DebondingCap(unittest.TestCase):
    def test_cap_applies_when_formula_runs_past_it(self):
        inp = load("input.json")
        inp["frp"]["tf_in"] = 0.01
        inp["frp"]["Ef_ksi"] = 5000.0
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


class CrushingModeSanity(unittest.TestCase):
    def test_heavy_steel_runs_and_balances(self):
        inp = load("input.json")
        inp["steel"]["As_in2"] = 8.0
        out = flexure440.run(inp)
        self.assertEqual(out["section"]["mode"], "concrete crushing controls")
        self.assertAlmostEqual(out["section"]["balance_kips"], 0.0, delta=0.05)


if __name__ == "__main__":
    unittest.main()
