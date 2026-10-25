#!/usr/bin/env python3
"""Flexure checks for one concrete beam strengthened with FRP fabric.

Method: ACI 440.2R-17, Chapter 10, for externally bonded FRP flexure
strengthening of a rectangular reinforced concrete section.
The strengthening limit is the ACI 440.2R-17 Eq. (9.2) combination,
1.1 dead + 0.75 live, which is the combination the Track 1 worked
example computes. The example text cites ACI 562-16, Section 5.5.2 for
that check. That section's own combination is different. See NOTICE.
Minimum steel follows ACI 318, as cited in the same example.
Service limits: steel and concrete stress, ACI 440.2R-17
Section 10.2.8. FRP creep rupture stress, Section 10.2.9, with the
limit set by fiber type and the stress taken at the sustained moment
when the input gives one.

Units in and out: inches, ksi, kips, kip-in, kip-ft.
Standard library only. Run:
    python3 src/flexure440.py tracks/track-1/input.json
Check lines go to stderr, one per check, with the value, the limit, and
PASS or FAIL. The JSON block with every number goes to stdout, so
redirecting stdout gives a clean JSON file.

Scope limits, stated plainly:
- Rectangular section, tension steel only, no compression steel.
- Simple span under uniform load. The support condition is an input,
  and any other condition is refused, so the strength moments and the
  service moment always describe the same structure.
- One FRP system bonded to the soffit.
- No shear, no anchorage design, no deflection, no fire design.
  This does not replace the full ACI guide or the engineer of record.
"""

import json
import math
import sys

ECU = 0.003      # ultimate concrete strain, ACI 440.2R-17
PSI_F = 0.85     # extra reduction factor on the FRP part of Mn, 440.2R-17
FC_SERVICE_LIMIT = 0.45   # fc,s limit as a fraction of f'c, Section 10.2.8
CREEP_FACTORS = {"carbon": 0.55, "glass": 0.20, "aramid": 0.30}  # Section 10.2.9


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


def beta1_318(fc_ksi):
    """Whitney block depth factor, ACI 318."""
    if fc_ksi <= 4.0:
        return 0.85
    return max(0.65, 0.85 - 0.05 * (fc_ksi * 1000.0 - 4000.0) / 1000.0)


def section_state(c, inp, mat, efd):
    """Strains, stresses, stress block, and force balance at depth c.

    Two stress blocks, by mode. When concrete crushing controls, the
    Whitney block of Section 10.2.10 applies, alpha1 = 0.85 and beta1
    per ACI 318. When FRP debonding controls, the concrete strain is
    below ultimate and the strain-dependent block factors apply.
    FRP is never counted in compression: its strain is clamped at zero.
    Steel stress is clamped at yield in both directions.
    """
    b = inp["beam"]
    conc = inp["concrete"]
    steel = inp["steel"]
    frp = inp["frp"]
    ebi = inp["ebi"]
    efe_try = ECU * (b["df_in"] - c) / c - ebi
    if efe_try > efd:
        efe = efd
        ec = (efe + ebi) * c / (b["df_in"] - c)
        mode = "FRP debonding controls"
        ecp = 1.7 * conc["fc_ksi"] / conc["Ec_ksi"]
        beta = (4.0 * ecp - ec) / (6.0 * ecp - 2.0 * ec)
        alpha = (3.0 * ecp * ec - ec ** 2) / (3.0 * beta * ecp ** 2)
    else:
        efe = max(efe_try, 0.0)
        ec = ECU
        mode = "concrete crushing controls"
        alpha = 0.85
        beta = beta1_318(conc["fc_ksi"])
    es = (efe + ebi) * (b["d_in"] - c) / (b["df_in"] - c)
    fs = max(-steel["fy_ksi"], min(steel["Es_ksi"] * es, steel["fy_ksi"]))
    ffe = frp["Ef_ksi"] * efe
    comp = alpha * conc["fc_ksi"] * b["b_in"] * beta * c
    tens = steel["As_in2"] * fs + mat["Af"] * ffe
    return {
        "c_in": c, "mode": mode, "ec": ec, "efe": efe, "es": es,
        "fs_ksi": fs, "ffe_ksi": ffe, "alpha1": alpha, "beta1": beta,
        "compression_kips": comp, "tension_kips": tens,
        "balance_kips": comp - tens,
    }


def solve_section(inp, mat, efd):
    """Bisect on c until compression and tension agree.

    Refuses when the balance has no sign change over the search range,
    and when the settled balance is not near zero. A silent endpoint
    with a large imbalance is a wrong answer, not a result.
    """
    lo, hi = 0.05, inp["beam"]["h_in"] * 0.95
    f_lo = section_state(lo, inp, mat, efd)["balance_kips"]
    f_hi = section_state(hi, inp, mat, efd)["balance_kips"]
    if f_lo == 0.0:
        return section_state(lo, inp, mat, efd)
    if f_lo * f_hi > 0:
        raise ValueError(
            "no force balance in range: balance is "
            f"{f_lo:.1f} kips at c={lo} in and {f_hi:.1f} kips at c={hi} in")
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if section_state(mid, inp, mat, efd)["balance_kips"] > 0:
            hi = mid
        else:
            lo = mid
    st = section_state(0.5 * (lo + hi), inp, mat, efd)
    scale = max(st["compression_kips"], st["tension_kips"], 1.0)
    if abs(st["balance_kips"]) > max(1.0, 0.005 * scale):
        raise ValueError(
            f"section did not balance: {st['balance_kips']:.1f} kips left over")
    return st


def phi_for(es, esy):
    if es >= 0.005:
        return 0.90
    if es <= esy:
        return 0.65
    return 0.65 + 0.25 * (es - esy) / (0.005 - esy)


def existing_strength(inp):
    """Plain reinforced concrete strength, Whitney block, no FRP.

    Steel stress comes from strain compatibility, not from an assumed
    yield: fs = Es * ecu * (d - c) / c, clamped at fy. An over-reinforced
    section, where the steel does not yield, gets its lower, correct
    strength.
    """
    conc = inp["concrete"]
    steel = inp["steel"]
    b = inp["beam"]
    beta1 = beta1_318(conc["fc_ksi"])
    esy = steel["fy_ksi"] / steel["Es_ksi"]

    def fs_at(c):
        return min(steel["Es_ksi"] * ECU * (b["d_in"] - c) / c, steel["fy_ksi"])

    def balance(c):
        return 0.85 * conc["fc_ksi"] * b["b_in"] * beta1 * c - steel["As_in2"] * fs_at(c)

    lo, hi = 0.05, b["d_in"]
    if balance(lo) * balance(hi) > 0:
        raise ValueError("existing section does not balance in range")
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if balance(mid) > 0:
            hi = mid
        else:
            lo = mid
    c = 0.5 * (lo + hi)
    a = beta1 * c
    if a > b["h_in"]:
        raise ValueError("existing section: stress block deeper than the beam")
    fs = fs_at(c)
    es = ECU * (b["d_in"] - c) / c
    mn = steel["As_in2"] * fs * (b["d_in"] - a / 2.0)
    phi = phi_for(es, esy)
    return {"a_in": a, "c_in": c, "es": es, "fs_ksi": fs,
            "Mn_kipft": mn / 12.0, "phi": phi, "phiMn_kipft": phi * mn / 12.0}


def service(inp, mat):
    """Service stresses by the worked example method.

    Cracked section factor k from the modular ratios, then the steel
    stress closed form the example prints, which carries the initial
    soffit strain ebi on the FRP force. Concrete stress follows from
    strain compatibility with the steel stress. The FRP creep rupture
    stress is taken at the sustained moment when the input gives one,
    and at the full service moment otherwise.
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
    a1 = steel["As_in2"] * steel["Es_ksi"]
    a2 = mat["Af"] * frp["Ef_ksi"]
    lev_s = b["d_in"] - kd / 3.0
    lev_f = b["df_in"] - kd / 3.0

    def stresses(moment_kipft):
        ms = moment_kipft * 12.0
        fs_s = ((ms + inp["ebi"] * a2 * lev_f) * (b["d_in"] - kd) * steel["Es_ksi"]
                / (a1 * lev_s * (b["d_in"] - kd) + a2 * lev_f * (b["df_in"] - kd)))
        ff_s = (fs_s * (frp["Ef_ksi"] / steel["Es_ksi"])
                * (b["df_in"] - kd) / (b["d_in"] - kd) - frp["Ef_ksi"] * inp["ebi"])
        return fs_s, ff_s

    fs_s, ff_full = stresses(inp["service_moment_kipft"])
    fc_s = fs_s * (conc["Ec_ksi"] / steel["Es_ksi"]) * kd / (b["d_in"] - kd)
    sustained = inp.get("sustained_moment_kipft")
    _fs_sus, ff_s = stresses(sustained) if sustained is not None else (None, ff_full)
    return {"k": k, "kd_in": kd, "fs_service_ksi": fs_s,
            "fc_service_ksi": fc_s, "ff_service_ksi": ff_s,
            "ff_service_full_moment_ksi": ff_full,
            "ff_moment_used_kipft": sustained if sustained is not None
            else inp["service_moment_kipft"]}


def creep_factor(inp):
    fiber = inp["frp"].get("fiber", "carbon")
    if fiber not in CREEP_FACTORS:
        raise ValueError(f"unknown fiber type: {fiber}")
    return CREEP_FACTORS[fiber]


def run(inp):
    if not str(inp.get("support_condition", "")).startswith("simple"):
        raise ValueError(
            "support_condition must be a simple span; the strength moments "
            "are computed as w L^2 / 8 and no other condition is modelled")
    mat = design_material(inp)
    efd, efd_raw = debonding_strain(inp, mat)
    st = solve_section(inp, mat, efd)
    steel = inp["steel"]
    beam = inp["beam"]
    lever = st["beta1"] * st["c_in"] / 2.0
    mn = (steel["As_in2"] * st["fs_ksi"] * (beam["d_in"] - lever)
          + PSI_F * mat["Af"] * st["ffe_ksi"] * (beam["df_in"] - lever))
    phi = phi_for(st["es"], steel["fy_ksi"] / steel["Es_ksi"])
    exist = existing_strength(inp)
    svc = service(inp, mat)

    span = inp["span_ft"]
    wdl = inp["loads"]["wDL_kipft"]
    wll = inp["loads"]["wLL_new_kipft"]
    limit_demand = (1.1 * wdl + 0.75 * wll) * span ** 2 / 8.0
    mu_design = max(1.2 * wdl + 1.6 * wll, 1.4 * wdl) * span ** 2 / 8.0

    fc_psi = inp["concrete"]["fc_ksi"] * 1000.0
    as_min = max(3.0 * math.sqrt(fc_psi), 200.0) * beam["b_in"] \
        * beam["d_in"] / (steel["fy_ksi"] * 1000.0)

    limits = {
        "fs_service_ksi": 0.80 * steel["fy_ksi"],
        "fc_service_ksi": FC_SERVICE_LIMIT * inp["concrete"]["fc_ksi"],
        "ff_service_ksi": creep_factor(inp) * mat["ffu"],
    }
    efd_cap = 0.9 * mat["efu"]
    checks = [
        ("Minimum steel, As >= As,min", steel["As_in2"], as_min,
         steel["As_in2"] >= as_min),
        ("Debonding strain applied, efd = min(formula, 0.9 efu)", efd,
         min(efd_raw, efd_cap), abs(efd - min(efd_raw, efd_cap)) < 1e-12),
        ("Strengthening limit, phiMn existing >= 1.1DL + 0.75LL moment",
         exist["phiMn_kipft"], limit_demand,
         exist["phiMn_kipft"] >= limit_demand),
        ("Design strength, phiMn >= Mu", phi * mn / 12.0, mu_design,
         phi * mn / 12.0 >= mu_design),
        ("Service steel stress, fs,s <= 0.80 fy", svc["fs_service_ksi"],
         limits["fs_service_ksi"], svc["fs_service_ksi"] <= limits["fs_service_ksi"]),
        ("Service concrete stress, fc,s <= 0.45 f'c", svc["fc_service_ksi"],
         limits["fc_service_ksi"], svc["fc_service_ksi"] <= limits["fc_service_ksi"]),
        ("Service FRP creep rupture stress, ff,s <= factor ffu",
         svc["ff_service_ksi"], limits["ff_service_ksi"],
         svc["ff_service_ksi"] <= limits["ff_service_ksi"]),
    ]
    return {
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
        "service_limits": limits,
        "checks": checks,
    }


def fmt(value):
    return f"{value:.4f}" if abs(value) < 0.1 else f"{value:.2f}"


def main(argv):
    with open(argv[1], encoding="utf-8") as fh:
        inp = json.load(fh)
    out = run(inp)
    for name, value, limit, ok in out["checks"]:
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {fmt(value)} vs limit {fmt(limit)}",
              file=sys.stderr)
    print(json.dumps({k: v for k, v in out.items() if k != "checks"}, indent=2))
    return 0 if all(ok for *_x, ok in out["checks"]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
