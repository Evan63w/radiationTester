"""Photon screening calculations based on NIST mass attenuation tables."""

import bisect
import csv
import json
import math
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).parent / "data"
DENSITIES = {"polyethylene": 0.94, "tungsten": 19.3, "bismuth": 9.78, "lead": 11.34}
MATERIALS = ("polyethylene", "tungsten", "bismuth")


@lru_cache(maxsize=1)
def elements():
    with (DATA / "elements.json").open() as file:
        return json.load(file)


@lru_cache(maxsize=None)
def table(material):
    if material in elements():
        rows = [(energy * 1000, mu) for energy, mu in elements()[material]["rows"]]
    elif material in DENSITIES:
        with (DATA / f"{material}.csv").open(newline="") as file:
            rows = [(float(energy) * 1000, float(mu)) for energy, mu in csv.reader(file)]
    else:
        raise ValueError(f"Unknown material: {material}")
    if not rows or any(e <= 0 or mu <= 0 for e, mu in rows):
        raise ValueError(f"Invalid attenuation table for {material}")
    if any(rows[i][0] > rows[i + 1][0] for i in range(len(rows) - 1)):
        raise ValueError(f"Unsorted attenuation table for {material}")
    return tuple(rows)


def mass_attenuation(material, energy_kev):
    """Log-log interpolation, using the upper value at an absorption edge."""
    rows = table(material)
    if not math.isfinite(energy_kev) or not rows[0][0] <= energy_kev <= rows[-1][0]:
        raise ValueError("Photon energy must be between 1 and 20,000 keV")
    energies = [row[0] for row in rows]
    i = bisect.bisect_right(energies, energy_kev)
    if i == len(rows) or energies[i - 1] == energy_kev:
        return rows[i - 1][1]
    e1, mu1 = rows[i - 1]
    e2, mu2 = rows[i]
    fraction = math.log(energy_kev / e1) / math.log(e2 / e1)
    return math.exp(math.log(mu1) + fraction * math.log(mu2 / mu1))


def validate_recipe(recipe):
    fractions = recipe["mass_fractions"]
    if not fractions or any(name not in elements() and name not in MATERIALS for name in fractions):
        raise ValueError("Recipe must contain known elements or polyethylene")
    if any(not math.isfinite(v) or v < 0 or v > 1 for v in fractions.values()):
        raise ValueError("Mass fractions must be finite values between 0 and 1")
    if not math.isclose(sum(fractions.values()), 1, abs_tol=1e-9):
        raise ValueError("Mass fractions must sum to 1")
    for key in ("density_g_cm3", "thickness_mm", "energy_kev"):
        if not math.isfinite(recipe[key]) or recipe[key] <= 0:
            raise ValueError(f"{key} must be positive and finite")
    if not 1 <= recipe["energy_kev"] <= 20000:
        raise ValueError("Photon energy must be between 1 and 20,000 keV")


def ideal_density(fractions):
    return 1 / sum(fractions[name] / DENSITIES[name] for name in MATERIALS)


def mixture_mu(fractions, energy_kev):
    return sum(weight * mass_attenuation(name, energy_kev) for name, weight in fractions.items() if weight)


def transmission(mu_mass, density, thickness_mm):
    return math.exp(-mu_mass * density * thickness_mm / 10)


def results(recipe, energy_kev=None):
    validate_recipe(recipe)
    energy = recipe["energy_kev"] if energy_kev is None else energy_kev
    mu = mixture_mu(recipe["mass_fractions"], energy)
    optical_depth = mu * recipe["density_g_cm3"] * recipe["thickness_mm"] / 10
    lead_mu = mass_attenuation("lead", energy)
    return {
        "mass_attenuation_cm2_g": mu,
        "transmission": math.exp(-optical_depth),
        "areal_mass_kg_m2": recipe["density_g_cm3"] * recipe["thickness_mm"],
        "lead_equivalent_mm": optical_depth / (lead_mu * DENSITIES["lead"]) * 10,
    }


def plot_energies():
    energies = {10 ** (i * (math.log10(20000) / 300)) for i in range(1, 300)}
    for material in DENSITIES:
        rows = table(material)
        for i in range(1, len(rows)):
            if rows[i][0] == rows[i - 1][0]:
                edge = rows[i][0]
                energies.update((math.nextafter(edge, 0), edge))
    energies.update((1.0, 20000.0))
    return sorted(energies)
