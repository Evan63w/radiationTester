"""Run an optional OpenGATE 10 monoenergetic pencil-beam slab simulation."""

import argparse
import json
import math
from pathlib import Path

from shielding import validate_recipe


def elemental_composition(fractions):
    composition = {}
    for name, weight in fractions.items():
        if weight == 0:
            continue
        if name == "polyethylene":
            components = {"H": 0.143711, "C": 0.856289}
        else:
            components = {{"tungsten": "W", "bismuth": "Bi"}.get(name, name): 1}
        for symbol, fraction in components.items():
            composition[symbol] = composition.get(symbol, 0) + weight * fraction
    return composition


def attenuation_estimate(incident, transmitted, thickness_mm):
    if not isinstance(incident, int) or incident <= 0:
        raise ValueError("Incident photon count must be a positive integer.")
    if not isinstance(transmitted, int) or not 0 <= transmitted <= incident:
        raise ValueError("Transmitted photon count must be an integer between zero and incident.")
    if not math.isfinite(thickness_mm) or thickness_mm <= 0:
        raise ValueError("Thickness must be positive and finite.")
    p = transmitted / incident
    z = 1.959963984540054
    denominator = 1 + z * z / incident
    center = (p + z * z / (2 * incident)) / denominator
    margin = z * math.sqrt(p * (1 - p) / incident + z * z / (4 * incident**2)) / denominator
    p_low = 0.0 if transmitted == 0 else max(0.0, center - margin)
    p_high = 1.0 if transmitted == incident else min(1.0, center + margin)
    thickness_cm = thickness_mm / 10
    return {
        "incident": incident,
        "uncollided_transmitted": transmitted,
        "transmission": p,
        "mu_cm_inv": -math.log(p) / thickness_cm if p > 0 else None,
        "mu_95_percent_wilson_cm_inv": [
            max(0.0, -math.log(p_high) / thickness_cm),
            -math.log(p_low) / thickness_cm if p_low > 0 else None,
        ],
    }


def uncollided_count(step_arrays, expected_events):
    seen = set()
    interacted = set()
    for arrays in step_arrays:
        for event, track, parent, particle, process in zip(
            arrays["EventID"], arrays["TrackID"], arrays["ParentID"],
            arrays["PDGCode"], arrays["ProcessDefinedStep"],
        ):
            if track != 1 or parent != 0 or particle != 22:
                continue
            event = int(event)
            seen.add(event)
            if process != "Transportation":
                interacted.add(event)
    if len(seen) != expected_events or any(event < 0 or event >= expected_events for event in seen):
        raise ValueError("Slab step records do not cover every primary event; cannot estimate attenuation.")
    return len(seen - interacted)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipe", type=Path, help="Recipe JSON exported by the dashboard")
    parser.add_argument("--primaries", type=int, default=100000)
    parser.add_argument("--output", type=Path, default=Path("gate-output"))
    parser.add_argument("--estimate-mu", action="store_true", help="Record primary slab interactions and estimate uncollided linear attenuation")
    args = parser.parse_args()
    if args.primaries < 1:
        parser.error("--primaries must be positive")
    if args.estimate_mu and args.output.exists() and any(args.output.iterdir()):
        parser.error("--estimate-mu requires a new or empty output directory")
    with args.recipe.open() as file:
        recipe = json.load(file)
    validate_recipe(recipe)

    import opengate as gate
    if args.estimate_mu:
        import uproot

    mm, keV = gate.g4_units.mm, gate.g4_units.keV
    composition = elemental_composition(recipe["mass_fractions"])
    sim = gate.Simulation()
    sim.output_dir = args.output.resolve()
    sim.world.size = [300 * mm, 300 * mm, (recipe["thickness_mm"] + 300) * mm]
    sim.world.material = "G4_Galactic"
    sim.volume_manager.material_database.add_material_weights(
        "composite", list(composition), list(composition.values()),
        recipe["density_g_cm3"] * gate.g4_units.g_cm3,
    )
    slab = sim.add_volume("Box", "slab")
    slab.size = [100 * mm, 100 * mm, recipe["thickness_mm"] * mm]
    slab.material = "composite"
    plane = sim.add_volume("Box", "scoring_plane")
    plane.size = [100 * mm, 100 * mm, 0.001 * mm]
    plane.material = "G4_Galactic"
    plane.translation = [0, 0, (recipe["thickness_mm"] / 2 + 1) * mm]
    source = sim.add_source("GenericSource", "beam")
    source.particle = "gamma"
    source.position.type = "point"
    source.position.translation = [0, 0, -(recipe["thickness_mm"] / 2 + 10) * mm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.energy.type = "mono"
    source.energy.mono = recipe["energy_kev"] * keV
    source.number_of_primaries = args.primaries
    sim.physics_manager.physics_list_name = "G4EmLivermorePhysics"
    phase = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    phase.attached_to = plane.name
    phase.output_filename = "phase-space.root"
    phase.attributes = ["PDGCode", "KineticEnergy", "PrePosition", "PreDirection"]
    if args.estimate_mu:
        hits = sim.add_actor("DigitizerHitsCollectionActor", "SlabSteps")
        hits.attached_to = slab.name
        hits.keep_zero_edep = True
        hits.output_filename = "slab-steps.root"
        hits.attributes = ["EventID", "TrackID", "ParentID", "PDGCode", "ProcessDefinedStep"]
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.output_filename = "stats.txt"
    sim.run()
    print(f"Output directory: {args.output.resolve()}")
    print("Phase-space entries can include scattered particles, secondaries and repeat crossings; they are not a transmission fraction.")
    if args.estimate_mu:
        with uproot.open(args.output / "slab-steps.root") as root_file:
            steps = root_file["SlabSteps"].iterate(library="np", step_size="50 MB")
            transmitted = uncollided_count(steps, args.primaries)
        estimate = attenuation_estimate(args.primaries, transmitted, recipe["thickness_mm"])
        estimate.update({
            "energy_kev": recipe["energy_kev"],
            "thickness_mm": recipe["thickness_mm"],
            "density_g_cm3": recipe["density_g_cm3"],
            "mass_fractions": recipe["mass_fractions"],
            "physics_list": "G4EmLivermorePhysics",
        })
        with (args.output / "mu-estimate.json").open("w") as file:
            json.dump(estimate, file, indent=2, allow_nan=False)
            file.write("\n")
        print(f"Uncollided primaries: {transmitted}/{args.primaries}")
        print(f"Linear attenuation estimate (cm^-1): {estimate['mu_cm_inv']}")
        print(f"Approximate 95% Wilson interval (cm^-1): {estimate['mu_95_percent_wilson_cm_inv']}; null upper bound means unbounded.")
        print("Monte Carlo sampling uncertainty only; this does not validate shielding or predict flexibility.")


if __name__ == "__main__":
    main()
