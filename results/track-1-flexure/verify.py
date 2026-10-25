#!/usr/bin/env python3
"""Replay the Track 1 result and compare it with its certificate.

Run from anywhere:
    python3 results/track-1-flexure/verify.py
        Recompute every number from tracks/track-1/input.json with the
        checker, compare with certificate.json in this folder, and check
        the ten printed values from the worked example.
    python3 results/track-1-flexure/verify.py --write
        Regenerate certificate.json, but only if the result passes.
        A failing result is never certified: the run prints the failures
        and exits non-zero without writing.

Checker lock: the checker hash recorded in
tracks/track-1-flexure-example.md is the lock. If src/flexure440.py
differs from that hash by one byte, both modes fail. A checker change
must land in its own pull request, which updates the lock there, before
any result can be certified against it.

The printed-value match compares unrounded checker output with the
printed values, the same comparison the unit tests make. Rounded values
in the certificate are for reading, not for matching.

A pass proves the numbers in the certificate replay from the input file
with the locked checker. It does not prove the ACI method is right, and
it does not prove any real beam is safe. See PROOF.md for what is
claimed.
"""

import hashlib
import json
import os
import re
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "src"))

import flexure440  # noqa: E402

CERT = os.path.join(HERE, "certificate.json")
INPUT = os.path.join(ROOT, "tracks", "track-1", "input.json")
EXPECTED = os.path.join(ROOT, "tracks", "track-1", "expected.json")
CHECKER = os.path.join(ROOT, "src", "flexure440.py")
TRACK = os.path.join(ROOT, "tracks", "track-1-flexure-example.md")


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def locked_checker_hash():
    with open(TRACK, encoding="utf-8") as fh:
        found = re.search(r"sha256: ([0-9a-f]{64})", fh.read())
    return found.group(1) if found else None


def resolve(out, dotted):
    node = out
    for part in dotted.split("."):
        node = node[part]
    return node


def build(when):
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
    for key, spec in exp.items():
        raw = resolve(out, spec["field"])
        printed[key] = {
            "printed": spec["printed"], "checker": round(raw, 6),
            "tol": spec["tol"], "match": abs(raw - spec["printed"]) <= spec["tol"],
        }
    checks = {name: bool(ok) for name, _v, _l, ok in out["checks"]
              if not name.startswith("Debonding strain")}
    cap = 0.9 * out["design_material"]["efu"]
    checks["Debonding cap applied, efd = min(formula, 0.9 efu)"] = (
        abs(out["efd"] - min(out["efd_uncapped"], cap)) < 1e-12)
    return {
        "result": "track-1-flexure",
        "date": when,
        "checker": {"path": "src/flexure440.py", "sha256": sha256(CHECKER)},
        "input": {"path": "tracks/track-1/input.json", "sha256": sha256(INPUT)},
        "source": inp["source"],
        "values": values,
        "checks_pass": checks,
        "printed_match": printed,
    }


def failures(cert):
    """Every reason this certificate must not be trusted or written."""
    bad = []
    locked = locked_checker_hash()
    if locked is None:
        bad.append("no checker hash locked in the track file")
    elif cert["checker"]["sha256"] != locked:
        bad.append("checker differs from the hash locked in the track file")
    for key, row in cert["printed_match"].items():
        if not row["match"]:
            bad.append(f"printed {key}: checker {row['checker']} "
                       f"vs printed {row['printed']} (tol {row['tol']})")
    for name, passed in cert["checks_pass"].items():
        if not passed:
            bad.append(f"check failed: {name}")
    return bad


def main(argv):
    if "--write" in argv:
        saved = None
        if os.path.exists(CERT):
            with open(CERT, encoding="utf-8") as fh:
                saved = json.load(fh)
        cert = build(saved["date"] if saved else date.today().isoformat())
        bad = failures(cert)
        if bad:
            for line in bad:
                print(f"FAIL  {line}")
            print("certificate not written")
            return 1
        if saved is not None and saved != cert:
            cert = build(date.today().isoformat())
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
    for line in failures(fresh):
        ok = False
        print(f"FAIL  {line}")
    for key, row in fresh["printed_match"].items():
        print(f"{'PASS' if row['match'] else 'FAIL'}  printed {key}: "
              f"checker {row['checker']} vs printed {row['printed']} (tol {row['tol']})")
    for name, passed in fresh["checks_pass"].items():
        print(f"{'PASS' if passed else 'FAIL'}  check {name}")
    print("RESULT: PASS" if ok else "RESULT: FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
