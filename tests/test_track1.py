"""Track 1 checker tests.

The example test compares the checker against numbers printed in the
Simpson Strong-Tie worked example (tracks/track-1/expected.json).
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


class ExampleMatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = flexure440.run(load("input.json"))
        cls.exp = load("expected.json")["values"]

    def check(self, key, got):
        want = self.exp[key]
        self.assertAlmostEqual(got, want["printed"], delta=want["tol"],
                               msg=f"{key}: checker {got} vs printed {want['printed']}")

    def test_printed_values(self):
        out = self.out
        self.check("ffu_ksi", out["design_material"]["ffu_ksi"])
        self.check("efd", out["efd"])
        self.check("ffe_ksi", out["section"]["ffe_ksi"])
        self.check("phiMn_existing_kipft", out["existing"]["phiMn_kipft"])
        self.check("limit_demand_kipft", out["strengthening_limit"]["limit_demand_kipft"])
        self.check("As_min_in2", out["As_min_in2"])
        self.check("k", out["service"]["k"])
        self.check("kd_in", out["service"]["kd_in"])
        self.check("fs_service_ksi", out["service"]["fs_service_ksi"])
        self.check("ff_service_ksi", out["service"]["ff_service_ksi"])

    def test_all_checks_pass(self):
        for name, _value, _limit, ok in self.out["checks"]:
            self.assertTrue(ok, msg=name)

    def test_force_balance(self):
        self.assertAlmostEqual(self.out["section"]["balance_kips"], 0.0, delta=0.05)


class CrushingModeSanity(unittest.TestCase):
    def test_heavy_steel_runs_and_balances(self):
        inp = load("input.json")
        inp["steel"]["As_in2"] = 8.0
        out = flexure440.run(inp)
        self.assertEqual(out["section"]["mode"], "concrete crushing controls")
        self.assertAlmostEqual(out["section"]["balance_kips"], 0.0, delta=0.05)


if __name__ == "__main__":
    unittest.main()
