#!/usr/bin/env python3
"""Flexure checks for one concrete beam strengthened with FRP fabric.

Method: ACI 440.2R-17, Chapter 10, for externally bonded FRP flexure
strengthening of a rectangular reinforced concrete section.
The strengthening limit is the ACI 440.2R-17 Eq. (9.2) combination,
1.1 dead + 0.75 live, which is the combination the Track 1 worked
example computes. The example text cites ACI 562-16, Section 5.5.2 for
that check, and with no snow the citation is consistent. ACI's
provisional 562-16 text gives Eq. (5.5.2) as 1.1D + 0.75L + 0.2S. ACI
webinar slides show the 562-16 draft as Eqs. (5.5.2a) 1.1D + 0.5L + 0.2S
and (5.5.2b) 1.1D + 0.75L. The 1.2D + 0.5L + 0.2S form is a different
check, the extraordinary event combination of ACI 562-16 Section 5.5.3
and ACI 562-13 Eq. (5.5.1). See NOTICE.
When the input marks the live load as sustained, the live load factor
in that limit is 1.0 (ACI 440.2R-17 9.2; ACI 562-16 5.5.2.1).
Snow is not modelled: S = 0.
Minimum steel follows ACI 318, as cited in the same example.
Service limits: steel stress 0.80 fy and concrete stress 0.60 f'c,
ACI 440.2R-17 Section 10.2.8 (the 2008 edition had 0.45 f'c). FRP creep
rupture stress, Section 10.2.9, with the limit set by fiber type and
the stress taken at the sustained moment when the input gives one.
Substrate, Section 1.2.1.4: f'c of at least 2500 psi, and a pull-off
strength of at least 200 psi when the input gives one. The substrate
condition needs a field assessment, so it is always listed as not
checked.

Units in and out: inches, ksi, kips, kip-in, kip-ft; pull-off strength
and the substrate f'c check in psi.
Standard library only. Run:
    python3 src/flexure440.py tracks/track-1/input.json
Check lines go to stderr, one per check, with the value, the limit, and
PASS or FAIL. NOT CHECKED lines follow them for each requirement the
input cannot show, and a NOTE line when the section has more than one
equilibrium. The JSON block with every number goes to stdout, so
redirecting stdout gives a clean JSON file.
Exit code: 0 every check passes, 1 a check fails, 2 the calculation
could not run (bad input, no usable equilibrium, no input path, or a
crash, which prints its traceback). A NOT CHECKED line never changes
the exit code. Exit 2 prints nothing on stdout.

Equilibrium: the force balance is scanned over 0 < c < df and every
equilibrium is kept. When there is more than one, the lowest phiMn is
used. That is conservative, but it can be a state the loading path
never reaches. When the balance changes sign only inside the jump
between the parabolic and Whitney blocks at the mode boundary, there is
no equilibrium and the run exits 2. Both rules are maintainer
decisions, not ACI text.

Scope limits, stated plainly:
- Rectangular section, tension steel only, no compression steel.
- Simple span under uniform load. The support condition is an input,
  and any other condition is refused, so the strength moments and the
  service moment always describe the same structure.
- One FRP system bonded to the soffit.
- Dead and live load only, no snow.
- No shear, no anchorage design, no deflection, no fire design.
  This does not replace the full ACI guide or the engineer of record.
"""

import json
import math
import sys
import traceback

ECU = 0.003      # ultimate concrete strain, ACI 440.2R-17
PSI_F = 0.85     # extra reduction factor on the FRP part of Mn, 440.2R-17
FC_SERVICE_LIMIT = 0.60   # fc,s limit as a fraction of f'c, Section 10.2.8
CREEP_FACTORS = {"carbon": 0.55, "glass": 0.20, "aramid": 0.30}  # Section 10.2.9
SUPPORT = "simple span, uniform load"   # the only condition w L^2 / 8 describes
SUBSTRATE_FC_PSI = 2500.0   # minimum substrate f'c, Section 1.2.1.4
PULL_OFF_PSI = 200.0        # minimum pull-off strength, Section 1.2.1.4
SCAN_POINTS = 400           # grid cells over 0 < c < df for the equilibrium scan

POSITIVE = (
    "beam.b_in", "beam.d_in", "beam.df_in", "beam.h_in",
    "concrete.fc_ksi", "concrete.Ec_ksi",
    "steel.As_in2", "steel.fy_ksi", "steel.Es_ksi",
    "frp.tf_in", "frp.wf_in", "frp.Ef_ksi", "frp.ffu_star_ksi", "frp.efu_star",
    "span_ft", "service_moment_kipft",
)
NON_NEGATIVE = ("loads.wDL_kipft", "loads.wLL_new_kipft", "ebi")
# Every key allowed in these groups. A misspelled optional key, such as
# the sustained live load flag, would otherwise fall back to its default
# without a word.
KNOWN_KEYS = {
    "loads": ("wDL_kipft", "wLL_new_kipft", "wLL_existing_kipft", "live_load_sustained"),
    "substrate": ("pull_off_psi",),
}


class InputError(Exception):
    """The input cannot be used. The message names the field."""


class SolverError(Exception):
    """The section has no state the checker can use."""


def field(inp, dotted):
    """Value at a dotted path such as "beam.b_in"."""
    node = inp
    parts = dotted.split(".")
    for i, part in enumerate(parts):
        if not isinstance(node, dict):
            raise InputError(f"{'.'.join(parts[:i])} must be a JSON object")
        if part not in node:
            raise InputError(f"missing input {dotted}")
        node = node[part]
    return node


def number(inp, dotted):
    """Finite int or float at a dotted path. A bool is not a number."""
    x = field(inp, dotted)
    try:
        ok = not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x)
    except OverflowError:   # an int too large for a float
        ok = False
    if not ok:
        raise InputError(f"{dotted} must be a finite number, got {x!r}")
    return x


def validate(inp):
    """Refuse input the calculation cannot use, naming the field.

    Runs before any calculation, so a bad value never reaches a formula
    and never comes out as a PASS or a FAIL.
    """
    if not isinstance(inp, dict):
        raise InputError("input must be a JSON object")
    for key in POSITIVE:
        if number(inp, key) <= 0:
            raise InputError(f"{key} must be > 0, got {field(inp, key)!r}")
    for key in NON_NEGATIVE:
        if number(inp, key) < 0:
            raise InputError(f"{key} must be >= 0, got {field(inp, key)!r}")
    plies = field(inp, "frp.plies")
    if isinstance(plies, bool) or not isinstance(plies, int) or plies < 1:
        raise InputError(f"frp.plies must be a JSON integer >= 1, got {plies!r}; the "
                         "checker needs at least one ply and does not run on an "
                         "unstrengthened beam")
    ce = number(inp, "frp.CE")
    if not 0 < ce <= 0.95:
        raise InputError(f"frp.CE must be > 0 and <= 0.95 (ACI 440.2R-17 Table 9.4), "
                         f"got {ce!r}")
    beam = inp["beam"]
    if beam["df_in"] <= beam["d_in"]:
        raise InputError(f"beam.df_in must be > beam.d_in, got {beam['df_in']!r} "
                         f"and {beam['d_in']!r}")
    if beam["df_in"] > beam["h_in"]:
        raise InputError(f"beam.df_in must be <= beam.h_in, got {beam['df_in']!r} "
                         f"and {beam['h_in']!r}")
    if inp["frp"]["wf_in"] > beam["b_in"]:
        raise InputError(f"frp.wf_in must be <= beam.b_in, got {inp['frp']['wf_in']!r} "
                         f"and {beam['b_in']!r}")
    support = field(inp, "support_condition")
    if not isinstance(support, str) or " ".join(support.lower().split()) != SUPPORT:
        raise InputError(
            f"support_condition must be {SUPPORT!r}, got {support!r}; the strength "
            "moments are computed as w L^2 / 8 and no other condition is modelled")
    fiber = inp["frp"].get("fiber", "carbon")
    if not isinstance(fiber, str) or fiber not in CREEP_FACTORS:
        raise InputError(f"frp.fiber must be one of {', '.join(CREEP_FACTORS)}, "
                         f"got {fiber!r}")
    if "sustained_moment_kipft" in inp:
        sustained = number(inp, "sustained_moment_kipft")
        if not 0 <= sustained <= inp["service_moment_kipft"]:
            raise InputError(f"sustained_moment_kipft must be >= 0 and <= "
                             f"service_moment_kipft, got {sustained!r} and "
                             f"{inp['service_moment_kipft']!r}")
    for group, known in KNOWN_KEYS.items():
        node = inp.get(group, {})
        if not isinstance(node, dict):
            raise InputError(f"{group} must be a JSON object")
        for key in node:
            if key not in known:
                raise InputError(f"{group}.{key} is not a known input; expected one of "
                                 f"{', '.join(known)}")
    for group, key in (("loads", "wLL_existing_kipft"), ("substrate", "pull_off_psi")):
        if key in inp.get(group, {}) and number(inp, f"{group}.{key}") < 0:
            raise InputError(f"{group}.{key} must be >= 0, got {inp[group][key]!r}")
    sustained_ll = inp["loads"].get("live_load_sustained", False)
    if not isinstance(sustained_ll, bool):
        raise InputError(f"loads.live_load_sustained must be true or false, "
                         f"got {sustained_ll!r}")


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
    below ultimate and the strain-dependent block factors apply, written
    in x = ec/e'c: alpha1 beta1 = x - x^2/3, beta1 = (4 - x)/(6 - 2x).
    Past x = 2 that block has beta1 > 1, deeper than the neutral axis,
    which is not concrete: alpha1 and beta1 are None there, and the
    solver never accepts the state.
    FRP is never counted in compression: its stress is clamped at zero.
    Its strain is not, so the steel strain stays on the section's strain
    profile. Steel stress is clamped at yield in both directions.
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
        x = ec / ecp
        alpha_beta = x - x * x / 3.0
        beta = (4.0 - x) / (6.0 - 2.0 * x) if x <= 2.0 else None
        alpha = alpha_beta / beta if beta is not None else None
    else:
        efe = efe_try
        ec = ECU
        mode = "concrete crushing controls"
        alpha = 0.85
        beta = beta1_318(conc["fc_ksi"])
        alpha_beta = alpha * beta
    es = (efe + ebi) * (b["d_in"] - c) / (b["df_in"] - c)
    fs = max(-steel["fy_ksi"], min(steel["Es_ksi"] * es, steel["fy_ksi"]))
    ffe = frp["Ef_ksi"] * max(efe, 0.0)
    comp = alpha_beta * conc["fc_ksi"] * b["b_in"] * c
    tens = steel["As_in2"] * fs + mat["Af"] * ffe
    return {
        "c_in": c, "mode": mode, "ec": ec, "efe": efe, "es": es,
        "fs_ksi": fs, "ffe_ksi": ffe, "alpha1": alpha, "beta1": beta,
        "compression_kips": comp, "tension_kips": tens,
        "balance_kips": comp - tens,
    }


def solve_section(inp, mat, efd):
    """Every force equilibrium for 0 < c < df, in order of c.

    Scans the balance on a grid of SCAN_POINTS cells and bisects every
    sign change. The grid has a point just either side of the mode
    boundary, where the parabolic and Whitney blocks meet with a jump,
    so a root next to the jump is not hidden by it. A root is kept only
    where compression and tension agree to 1e-6 of the tension force,
    1e-6 kip at least, and the stress block is physical, beta1 <= 1.
    A sign change across the jump itself is not an equilibrium.
    Refuses when no root is kept: a silent endpoint with a large
    imbalance is a wrong answer, not a result.
    """
    df = inp["beam"]["df_in"]
    # Mode boundary: the concrete reaches ECU as the FRP reaches efd.
    cb = ECU * df / (ECU + efd + inp["ebi"])
    grid = sorted([df * k / SCAN_POINTS for k in range(1, SCAN_POINTS)]
                  + [cb * (1.0 - 1e-9), cb * (1.0 + 1e-9)])
    states = [section_state(c, inp, mat, efd) for c in grid]
    roots = []
    for left, right in zip(states, states[1:]):
        left_pos = left["balance_kips"] > 0
        if left_pos == (right["balance_kips"] > 0):
            continue
        lo, hi = left["c_in"], right["c_in"]
        for _ in range(100):
            mid = 0.5 * (lo + hi)
            if (section_state(mid, inp, mat, efd)["balance_kips"] > 0) == left_pos:
                lo = mid
            else:
                hi = mid
        st = section_state(0.5 * (lo + hi), inp, mat, efd)
        tol = max(1e-6 * abs(st["tension_kips"]), 1e-6)
        if st["beta1"] is not None and abs(st["balance_kips"]) <= tol:
            roots.append(st)
    if not roots:
        raise SolverError(
            f"no force equilibrium for 0 < c < {df:g} in: the balance never changes "
            f"sign, or changes sign only across the jump between the parabolic and "
            f"Whitney blocks at the mode boundary, c = {cb:.2f} in, or only where the "
            f"parabolic block has beta1 > 1")
    return roots


def phi_for(es, esy):
    if es >= 0.005:
        return 0.90
    if es <= esy:
        return 0.65
    return 0.65 + 0.25 * (es - esy) / (0.005 - esy)


def nominal_moment(st, inp, mat):
    """Mn in kip-in, and phi, for one section state."""
    steel = inp["steel"]
    beam = inp["beam"]
    lever = st["beta1"] * st["c_in"] / 2.0
    mn = (steel["As_in2"] * st["fs_ksi"] * (beam["d_in"] - lever)
          + PSI_F * mat["Af"] * st["ffe_ksi"] * (beam["df_in"] - lever))
    return mn, phi_for(st["es"], steel["fy_ksi"] / steel["Es_ksi"])


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
        raise SolverError("existing section does not balance in range")
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if balance(mid) > 0:
            hi = mid
        else:
            lo = mid
    c = 0.5 * (lo + hi)
    a = beta1 * c
    if a > b["h_in"]:
        raise SolverError("existing section: stress block deeper than the beam")
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
    return CREEP_FACTORS[inp["frp"].get("fiber", "carbon")]


def run(inp):
    validate(inp)
    mat = design_material(inp)
    efd, efd_raw = debonding_strain(inp, mat)
    states = solve_section(inp, mat, efd)
    moments = [nominal_moment(s, inp, mat) for s in states]
    roots = [{"c_in": s["c_in"], "mode": s["mode"], "Mn_kipft": m / 12.0,
              "phi": p, "phiMn_kipft": p * m / 12.0}
             for s, (m, p) in zip(states, moments)]
    pick = min(range(len(roots)), key=lambda i: roots[i]["phiMn_kipft"])
    st = states[pick]
    mn, phi = moments[pick]
    note = None
    if len(roots) > 1:
        note = (f"{len(roots)} force equilibria, c = "
                + ", ".join(f"{r['c_in']:.2f}" for r in roots)
                + f" in; the lowest phiMn, {phi * mn / 12.0:.1f} kip-ft at "
                f"c = {st['c_in']:.2f} in, is used as the conservative choice")
    steel = inp["steel"]
    beam = inp["beam"]
    exist = existing_strength(inp)
    svc = service(inp, mat)

    span = inp["span_ft"]
    loads = inp["loads"]
    wdl = loads["wDL_kipft"]
    wll = loads["wLL_new_kipft"]
    # Live load factor 1.0 when the live load is sustained, Section 9.2
    # and ACI 562-16 5.5.2.1. No snow term: S = 0.
    ll_factor = 1.0 if loads.get("live_load_sustained", False) else 0.75
    limit_demand = (1.1 * wdl + ll_factor * wll) * span ** 2 / 8.0
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
    # Section 1.2.1.4 also asks for a pull-off strength and a sound
    # substrate. What the input does not show is listed, never passed.
    checks = [
        ("Substrate strength, f'c >= 2500 psi (ACI 440.2R-17 1.2.1.4)",
         fc_psi, SUBSTRATE_FC_PSI, fc_psi >= SUBSTRATE_FC_PSI),
    ]
    not_checked = []
    pull_off = inp.get("substrate", {}).get("pull_off_psi")
    if pull_off is None:
        not_checked.append("Substrate pull-off strength >= 200 psi (ACI 440.2R-17 "
                           "1.2.1.4): no substrate.pull_off_psi in the input")
    else:
        checks.append(("Substrate pull-off strength >= 200 psi (ACI 440.2R-17 1.2.1.4)",
                       pull_off, PULL_OFF_PSI, pull_off >= PULL_OFF_PSI))
    not_checked.append("Substrate condition, no corroded steel or deteriorated concrete "
                       "left unrepaired (ACI 440.2R-17 1.2.1.4): needs a field assessment")
    checks += [
        ("Minimum steel, As >= As,min", steel["As_in2"], as_min,
         steel["As_in2"] >= as_min),
        ("Debonding strain applied, efd = min(formula, 0.9 efu)", efd,
         min(efd_raw, efd_cap), abs(efd - min(efd_raw, efd_cap)) < 1e-12),
        (f"Strengthening limit, phiMn existing >= 1.1DL + {ll_factor}LL moment",
         exist["phiMn_kipft"], limit_demand,
         exist["phiMn_kipft"] >= limit_demand),
        ("Design strength, phiMn >= Mu", phi * mn / 12.0, mu_design,
         phi * mn / 12.0 >= mu_design),
        ("Service steel stress, fs,s <= 0.80 fy", svc["fs_service_ksi"],
         limits["fs_service_ksi"], svc["fs_service_ksi"] <= limits["fs_service_ksi"]),
        ("Service concrete stress, fc,s <= 0.60 f'c (ACI 440.2R-17 10.2.8)",
         svc["fc_service_ksi"], limits["fc_service_ksi"],
         svc["fc_service_ksi"] <= limits["fc_service_ksi"]),
        ("Service FRP creep rupture stress, ff,s <= factor ffu",
         svc["ff_service_ksi"], limits["ff_service_ksi"],
         svc["ff_service_ksi"] <= limits["ff_service_ksi"]),
    ]
    return {
        "design_material": {"ffu_ksi": mat["ffu"], "efu": mat["efu"], "Af_in2": mat["Af"]},
        "efd": efd, "efd_uncapped": efd_raw,
        "section": st,
        "section_roots": roots,
        "section_note": note,
        "Mn_kipft": mn / 12.0, "phi": phi, "phiMn_kipft": phi * mn / 12.0,
        "existing": exist,
        "strengthening_limit": {
            "phiMn_existing_kipft": exist["phiMn_kipft"],
            "limit_demand_kipft": limit_demand,
            "live_load_factor": ll_factor,
            "pass": exist["phiMn_kipft"] >= limit_demand,
        },
        "design_demand_Mu_kipft": mu_design,
        "design_pass": phi * mn / 12.0 >= mu_design,
        "As_min_in2": as_min,
        "service": svc,
        "service_limits": limits,
        "not_checked": not_checked,
        "checks": checks,
    }


def fmt(value):
    return f"{value:.4f}" if abs(value) < 0.1 else f"{value:.2f}"


def unique_keys(pairs):
    """json object_pairs_hook: a duplicate key is an error, not last-one-wins."""
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise InputError(f"duplicate key {key!r} in input")
        obj[key] = value
    return obj


def read_input(path):
    """Parsed input file, with or without a UTF-8 byte order mark."""
    try:
        with open(path, encoding="utf-8-sig") as fh:
            return json.load(fh, object_pairs_hook=unique_keys)
    except UnicodeDecodeError as exc:
        raise InputError(f"{path}: not UTF-8 text: {exc}") from exc
    except ValueError as exc:
        raise InputError(f"{path}: not valid JSON: {exc}") from exc
    except RecursionError as exc:
        raise InputError(f"{path}: JSON nested too deeply") from exc
    except OSError as exc:
        raise InputError(f"{path}: {exc.strerror or exc}") from exc


def main(argv):
    if len(argv) != 2:
        print("usage: python3 src/flexure440.py INPUT.json", file=sys.stderr)
        return 2
    try:
        out = run(read_input(argv[1]))
        report = {k: v for k, v in out.items() if k != "checks"}
        report["checks"] = [{"name": name, "value": value, "limit": limit, "pass": ok}
                            for name, value, limit, ok in out["checks"]]
        report["all_pass"] = all(ok for *_x, ok in out["checks"])
        report = json.dumps(report, indent=2)
    except (InputError, SolverError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception:   # a crash is never a verdict, so never exit 1
        traceback.print_exc()
        print("ERROR: the checker crashed; no result", file=sys.stderr)
        return 2
    for name, value, limit, ok in out["checks"]:
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {fmt(value)} vs limit {fmt(limit)}",
              file=sys.stderr)
    for item in out["not_checked"]:
        print(f"NOT CHECKED  {item}", file=sys.stderr)
    if out["section_note"]:
        print(f"NOTE  {out['section_note']}", file=sys.stderr)
    print(report)
    return 0 if all(ok for *_x, ok in out["checks"]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
