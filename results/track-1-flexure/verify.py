#!/usr/bin/env python3
"""Replay the Track 1 result and compare it with its certificate.

Run from anywhere:
    python3 results/track-1-flexure/verify.py
        Recompute every number from tracks/track-1/input.json with the
        locked checker, compare with certificate.json in this folder,
        and check the ten printed values from the worked example.
    python3 results/track-1-flexure/verify.py --write
        Regenerate certificate.json. Do this only as a deliberate change,
        and commit the new certificate with its reason.

A pass proves the numbers in the certificate replay from the input file
with this checker. It does not prove the ACI method is right, and it does
not prove any real beam is safe. See PROOF.md for what is claimed.
"""

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "src"))

import flexure440  # noqa: E402

CERT = os.path.join(HERE, "certificate.json")
INPUT = os.path.join(ROOT, "tracks", "track-1", "input.json")
EXPECTED = os.path.join(ROOT, "tracks", "track-1", "expected.json")
CHECKER = os.path.join(ROOT, "src", "flexure440.py")

PRINTED_KEYS = {
    "ffu_ksi": ("design_ffu_ksi",),
    "efd": ("efd",),
    "ffe_ksi": ("section_ffe_ksi",),
    "phiMn_existing_kipft": ("existing_phiMn_kipft",),
    "limit_demand_kipft": ("limit_demand_kipft",),
    "As_min_in2": ("As_min_in2",),
    "k": ("service_k",),
    "kd_in": ("service_kd_in",),
    "fs_service_ksi": ("service_fs_ksi",),
    "ff_service_ksi": ("service_ff_ksi",),
}


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def build(date):
    with open(INPUT, encoding="utf-8") as fh:
        inp = json.load(fh)
    with open(EXPECTED, encoding="utf-8") as fh:
        exp = json.load(fh)["values"]
    out = flexure440.run(inp)
    st = out["section"]
    values = {
        "As_min_in2": round(out["As_min_in2"], 2),
        "Mu_kipft": round(out["design_demand_Mu_kipft"], 1),
        "design_ffu_ksi": round(out["design_material"]["ffu_ksi"], 1),
        "efd": round(out["efd"], 4),
        "existing_phiMn_kipft": round(out["existing"]["phiMn_kipft"], 1),
        "limit_demand_kipft": round(out["strengthening_limit"]["limit_demand_kipft"], 1),
        "phiMn_kipft": round(out["phiMn_kipft"], 1),
        "section_Mn_kipft": round(out["Mn_kipft"], 1),
        "section_c_in": round(st["c_in"], 2),
        "section_ec": round(st["ec"], 4),
        "section_efe": round(st["efe"], 4),
        "section_es": round(st["es"], 4),
        "section_ffe_ksi": round(st["ffe_ksi"], 1),
        "section_fs_ksi": round(st["fs_ksi"], 1),
        "section_mode": st["mode"],
        "service_ff_ksi": round(out["service"]["ff_service_ksi"], 1),
        "service_fs_ksi": round(out["service"]["fs_service_ksi"], 1),
        "service_k": round(out["service"]["k"], 4),
        "service_kd_in": round(out["service"]["kd_in"], 2),
    }
    printed = {}
    for key, (vkey,) in PRINTED_KEYS.items():
        want = exp[key]
        got = values[vkey]
        printed[key] = {
            "printed": want["printed"], "checker": got, "tol": want["tol"],
            "match": abs(got - want["printed"]) <= want["tol"],
        }
    return {
        "result": "track-1-flexure",
        "date": date,
        "checker": {"path": "src/flexure440.py", "sha256": sha256(CHECKER)},
        "input": {"path": "tracks/track-1/input.json", "sha256": sha256(INPUT)},
        "source": inp["source"],
        "values": values,
        "checks_pass": {name: bool(ok) for name, _v, _l, ok in out["checks"]},
        "printed_match": printed,
    }


def main(argv):
    if "--write" in argv:
        date = "2026-10-25"
        if os.path.exists(CERT):
            with open(CERT, encoding="utf-8") as fh:
                date = json.load(fh).get("date", date)
        cert = build(date)
        with open(CERT, "w", encoding="utf-8") as fh:
            json.dump(cert, fh, indent=2, sort_keys=True)
            fh.write("\n")
        print(f"wrote {CERT}")
        return 0
    with open(CERT, encoding="utf-8") as fh:
        saved = json.load(fh)
    fresh = build(saved["date"])
    ok = True
    if fresh != saved:
        ok = False
        print("FAIL  certificate does not replay from the input file")
        for key in sorted(set(fresh) | set(saved)):
            if fresh.get(key) != saved.get(key):
                print(f"  differs: {key}")
    for key, row in fresh["printed_match"].items():
        if not row["match"]:
            ok = False
        print(f"{'PASS' if row['match'] else 'FAIL'}  printed {key}: "
              f"checker {row['checker']} vs printed {row['printed']} (tol {row['tol']})")
    for name, passed in fresh["checks_pass"].items():
        if not passed:
            ok = False
        print(f"{'PASS' if passed else 'FAIL'}  check {name}")
    print("RESULT: PASS" if ok else "RESULT: FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
