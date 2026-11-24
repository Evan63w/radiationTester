"""Run an optional OpenGATE 10 monoenergetic pencil-beam slab simulation."""

import argparse
import json
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipe", type=Path, help="Recipe JSON exported by the dashboard")
    parser.add_argument("--primaries", type=int, default=100000)
    parser.add_argument("--output", type=Path, default=Path("gate-output"))
    args = parser.parse_args()
    if args.primaries < 1:
        parser.error("--primaries must be positive")
    with args.recipe.open() as file:
        recipe = json.load(file)
    validate_recipe(recipe)

    import opengate as gate

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
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.output_filename = "stats.txt"
    sim.run()
    print(f"Output directory: {args.output.resolve()}")
    print("Phase-space entries can include scattered particles, secondaries and repeat crossings; they are not a transmission fraction.")


if __name__ == "__main__":
    main()
