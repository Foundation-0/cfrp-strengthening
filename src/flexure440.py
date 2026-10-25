#!/usr/bin/env python3
"""Flexure checks for one concrete beam strengthened with carbon fiber fabric.

Method: ACI 440.2R-17, Chapter 10, for externally bonded FRP flexure
strengthening of a rectangular reinforced concrete section.
Strengthening limit and existing strength follow the form used in the
Track 1 worked example (ACI 562-16, Section 5.5.2, as cited there).
Minimum steel follows ACI 318, as cited in the same example.

Units in and out: inches, ksi, kips, kip-in, kip-ft.
Standard library only. Run:
    python3 src/flexure440.py tracks/track-1/input.json
Prints one line per check with the value, the limit, and PASS or FAIL,
then a JSON block with every number, so a test or a person can re-run it.

Scope limits, stated plainly:
- Rectangular section, tension steel only, no compression steel.
- One FRP system bonded to the soffit, full width factor taken from input.
- No shear, no anchorage design, no deflection, no fire design.
  The strengthening limit check is the load test of Section 5.5.2 form.
  It does not replace the full ACI guide or the engineer of record.
"""

import json
import math
import sys

ECU = 0.003      # ultimate concrete strain, ACI 440.2R-17
PSI_F = 0.85     # extra reduction factor on the FRP part of Mn, 440.2R-17


def design_material(inp):
    """Environmental reduction applied to reported FRP properties."""
    frp = inp["frp"]
    ce = frp["CE"]
    return {
        "ffu": ce * frp["ffu_star_ksi"],
        "efu": ce * frp["efu_star"],
        "Af": frp["plies"] * frp["tf_in"] * frp["wf_in"],
    }


def debonding_strain(inp, mat):
    """ACI 440.2R-17 Eq. for efd, capped at 0.9 efu."""
    frp = inp["frp"]
    fc_psi = inp["concrete"]["fc_ksi"] * 1000.0
    ef_psi = frp["Ef_ksi"] * 1000.0
    raw = 0.083 * math.sqrt(fc_psi / (frp["plies"] * ef_psi * frp["tf_in"]))
    return min(raw, 0.9 * mat["efu"]), raw


def section_state(c, inp, mat, efd):
    """Strains, stresses, stress block, and force balance at depth c."""
    b = inp["beam"]
    conc = inp["concrete"]
    steel = inp["steel"]
    frp = inp["frp"]
    ebi = inp["ebi"]
    ecp = 1.7 * conc["fc_ksi"] / conc["Ec_ksi"]
    efe_try = ECU * (b["df_in"] - c) / c - ebi
    if efe_try > efd:
        efe = efd
        ec = (efe + ebi) * c / (b["df_in"] - c)
        mode = "FRP debonding controls"
    else:
        efe = efe_try
        ec = ECU
        mode = "concrete crushing controls"
    es = (efe + ebi) * (b["d_in"] - c) / (b["df_in"] - c)
    fs = min(steel["Es_ksi"] * es, steel["fy_ksi"])
    ffe = frp["Ef_ksi"] * efe
    beta = (4.0 * ecp - ec) / (6.0 * ecp - 2.0 * ec)
    alpha = (3.0 * ecp * ec - ec ** 2) / (3.0 * beta * ecp ** 2)
    comp = alpha * conc["fc_ksi"] * b["b_in"] * beta * c
    tens = steel["As_in2"] * fs + mat["Af"] * ffe
    return {
        "c_in": c, "mode": mode, "ec": ec, "efe": efe, "es": es,
        "fs_ksi": fs, "ffe_ksi": ffe, "alpha1": alpha, "beta1": beta,
        "compression_kips": comp, "tension_kips": tens,
        "balance_kips": comp - tens,
    }


def solve_section(inp, mat, efd):
    """Bisect on c until compression and tension agree."""
    lo, hi = 0.05, inp["beam"]["h_in"] * 0.95
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if section_state(mid, inp, mat, efd)["balance_kips"] > 0:
            hi = mid
        else:
            lo = mid
    return section_state(0.5 * (lo + hi), inp, mat, efd)


def phi_for(es, esy):
    if es >= 0.005:
        return 0.90
    if es <= esy:
        return 0.65
    return 0.65 + 0.25 * (es - esy) / (0.005 - esy)


def existing_strength(inp):
    """Plain reinforced concrete strength, Whitney block, no FRP."""
    conc = inp["concrete"]
    steel = inp["steel"]
    b = inp["beam"]
    beta1 = 0.85 if conc["fc_ksi"] <= 4.0 else max(
        0.65, 0.85 - 0.05 * (conc["fc_ksi"] * 1000.0 - 4000.0) / 1000.0)
    a = steel["As_in2"] * steel["fy_ksi"] / (0.85 * conc["fc_ksi"] * b["b_in"])
    c = a / beta1
    es = ECU * (b["d_in"] - c) / c
    mn = steel["As_in2"] * steel["fy_ksi"] * (b["d_in"] - a / 2.0)
    return {"a_in": a, "c_in": c, "es": es,
            "Mn_kipft": mn / 12.0, "phi": phi_for(es, steel["fy_ksi"] / steel["Es_ksi"]),
            "phiMn_kipft": phi_for(es, steel["fy_ksi"] / steel["Es_ksi"]) * mn / 12.0}


def service(inp, mat):
    """Service stresses by the worked example method.

    Cracked section factor k from the modular ratios, then the steel
    stress closed form the example prints, which carries the initial
    soffit strain ebi on the FRP force.
    """
    b = inp["beam"]
    conc = inp["concrete"]
    steel = inp["steel"]
    frp = inp["frp"]
    rho_s = steel["As_in2"] / (b["b_in"] * b["d_in"])
    rho_f = mat["Af"] / (b["b_in"] * b["d_in"])
    ns_r = rho_s * steel["Es_ksi"] / conc["Ec_ksi"]
    nf_r = rho_f * frp["Ef_ksi"] / conc["Ec_ksi"]
    k = math.sqrt((ns_r + nf_r) ** 2 +
                  2.0 * (ns_r + nf_r * b["df_in"] / b["d_in"])) - (ns_r + nf_r)
    kd = k * b["d_in"]
    ms = inp["service_moment_kipft"] * 12.0
    a1 = steel["As_in2"] * steel["Es_ksi"]
    a2 = mat["Af"] * frp["Ef_ksi"]
    lev_s = b["d_in"] - kd / 3.0
    lev_f = b["df_in"] - kd / 3.0
    fs_s = ((ms + inp["ebi"] * a2 * lev_f) * (b["d_in"] - kd) * steel["Es_ksi"]
            / (a1 * lev_s * (b["d_in"] - kd) + a2 * lev_f * (b["df_in"] - kd)))
    ff_s = (fs_s * (frp["Ef_ksi"] / steel["Es_ksi"])
            * (b["df_in"] - kd) / (b["d_in"] - kd) - frp["Ef_ksi"] * inp["ebi"])
    return {"k": k, "kd_in": kd, "fs_service_ksi": fs_s, "ff_service_ksi": ff_s}


def run(inp):
    mat = design_material(inp)
    efd, efd_raw = debonding_strain(inp, mat)
    st = solve_section(inp, mat, efd)
    steel = inp["steel"]
    mn = (steel["As_in2"] * st["fs_ksi"] * (inp["beam"]["d_in"] - st["beta1"] * st["c_in"] / 2.0)
          + PSI_F * mat["Af"] * st["ffe_ksi"]
          * (inp["beam"]["df_in"] - st["beta1"] * st["c_in"] / 2.0))
    phi = phi_for(st["es"], steel["fy_ksi"] / steel["Es_ksi"])
    exist = existing_strength(inp)
    svc = service(inp, mat)

    span = inp["span_ft"]
    wdl = inp["loads"]["wDL_kipft"]
    wll = inp["loads"]["wLL_new_kipft"]
    limit_demand = (1.1 * wdl + 0.75 * wll) * span ** 2 / 8.0
    mu_design = (1.2 * wdl + 1.6 * wll) * span ** 2 / 8.0

    fc_psi = inp["concrete"]["fc_ksi"] * 1000.0
    as_min = max(3.0 * math.sqrt(fc_psi), 200.0) * inp["beam"]["b_in"] \
        * inp["beam"]["d_in"] / (steel["fy_ksi"] * 1000.0)

    out = {
        "design_material": {"ffu_ksi": mat["ffu"], "efu": mat["efu"], "Af_in2": mat["Af"]},
        "efd": efd, "efd_uncapped": efd_raw,
        "section": st,
        "Mn_kipft": mn / 12.0, "phi": phi, "phiMn_kipft": phi * mn / 12.0,
        "existing": exist,
        "strengthening_limit": {
            "phiMn_existing_kipft": exist["phiMn_kipft"],
            "limit_demand_kipft": limit_demand,
            "pass": exist["phiMn_kipft"] >= limit_demand,
        },
        "design_demand_Mu_kipft": mu_design,
        "design_pass": phi * mn / 12.0 >= mu_design,
        "As_min_in2": as_min,
        "service": svc,
        "service_limits": {
            "fs_limit_ksi": 0.80 * steel["fy_ksi"],
            "ff_limit_ksi": 0.55 * mat["ffu"],
        },
    }
    out["checks"] = [
        ("Minimum steel, As >= As,min", steel["As_in2"], as_min, steel["As_in2"] >= as_min),
        ("Debonding strain, efd <= 0.9 efu", efd, 0.9 * mat["efu"], efd <= 0.9 * mat["efu"] + 1e-12),
        ("Strengthening limit, phiMn existing >= 1.1DL + 0.75LL moment",
         exist["phiMn_kipft"], limit_demand, exist["phiMn_kipft"] >= limit_demand),
        ("Design strength, phiMn >= Mu", phi * mn / 12.0, mu_design, phi * mn / 12.0 >= mu_design),
        ("Service steel stress, fs,s <= 0.80 fy", svc["fs_service_ksi"],
         0.80 * steel["fy_ksi"], svc["fs_service_ksi"] <= 0.80 * steel["fy_ksi"]),
        ("Service FRP stress, ff,s <= 0.55 ffu", svc["ff_service_ksi"],
         0.55 * mat["ffu"], svc["ff_service_ksi"] <= 0.55 * mat["ffu"]),
    ]
    return out


def main(argv):
    with open(argv[1], encoding="utf-8") as fh:
        inp = json.load(fh)
    out = run(inp)
    for name, value, limit, ok in out["checks"]:
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {value:.2f} vs limit {limit:.2f}")
    print(json.dumps(out, indent=2))
    return 0 if all(ok for *_x, ok in out["checks"]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
