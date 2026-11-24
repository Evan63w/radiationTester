import math
import unittest

from shielding import ideal_density, mass_attenuation, plot_energies, results, table, transmission, validate_recipe
from run_gate import attenuation_estimate, elemental_composition, uncollided_count


class ShieldingTests(unittest.TestCase):
    def test_published_values_and_mixture(self):
        self.assertAlmostEqual(mass_attenuation("lead", 100), 5.549)
        self.assertAlmostEqual(mass_attenuation("tungsten", 100), 4.438)
        recipe = {
            "mass_fractions": {"polyethylene": 0.3, "tungsten": 0.4, "bismuth": 0.3},
            "density_g_cm3": 2.5, "thickness_mm": 1.0, "energy_kev": 100.0,
        }
        mu = 0.3 * 0.1719 + 0.4 * 4.438 + 0.3 * 5.739
        out = results(recipe)
        self.assertAlmostEqual(out["mass_attenuation_cm2_g"], mu)
        self.assertAlmostEqual(out["transmission"], math.exp(-mu * 2.5 * 0.1))
        self.assertAlmostEqual(out["lead_equivalent_mm"], mu * 2.5 / (5.549 * 11.34))
        self.assertAlmostEqual(out["areal_mass_kg_m2"], 2.5)

    def test_edges_are_not_interpolated_across(self):
        rows = table("tungsten")
        i = next(i for i in range(1, len(rows)) if rows[i][0] == rows[i - 1][0])
        edge = rows[i][0]
        self.assertAlmostEqual(mass_attenuation("tungsten", edge), rows[i][1])
        self.assertAlmostEqual(mass_attenuation("tungsten", math.nextafter(edge, 0)), rows[i - 1][1])
        self.assertAlmostEqual(mass_attenuation("tungsten", math.nextafter(edge, math.inf)), rows[i][1])

    def test_interpolation_and_limits(self):
        energy = math.sqrt(100 * 150)
        self.assertAlmostEqual(mass_attenuation("lead", energy), math.sqrt(5.549 * 2.014))
        for energy in (0, 20001, float("nan")):
            with self.assertRaises(ValueError):
                mass_attenuation("lead", energy)

    def test_plot_energies_stay_inside_table_bounds(self):
        for energy in plot_energies():
            for material in ("lead", "tungsten", "bismuth", "polyethylene"):
                mass_attenuation(material, energy)

    def test_density_and_validation(self):
        fractions = {"polyethylene": 1.0, "tungsten": 0.0, "bismuth": 0.0}
        self.assertAlmostEqual(ideal_density(fractions), 0.94)
        self.assertEqual(transmission(5, 2, 0), 1)
        recipe = {"mass_fractions": fractions, "density_g_cm3": 1, "thickness_mm": 1, "energy_kev": 100}
        validate_recipe(recipe)
        for invalid in (-1, float("nan")):
            recipe["density_g_cm3"] = invalid
            with self.assertRaises(ValueError):
                validate_recipe(recipe)
        recipe["density_g_cm3"] = 1
        recipe["mass_fractions"]["tungsten"] = 0.1
        with self.assertRaises(ValueError):
            validate_recipe(recipe)

    def test_custom_elements_and_simulation_composition(self):
        recipe = {
            "mass_fractions": {"polyethylene": 0.4, "H": 0.1, "Fe": 0.5},
            "density_g_cm3": 3.0, "thickness_mm": 1.0, "energy_kev": 100.0,
        }
        validate_recipe(recipe)
        expected = 0.4 * mass_attenuation("polyethylene", 100) + 0.1 * mass_attenuation("H", 100) + 0.5 * mass_attenuation("Fe", 100)
        self.assertAlmostEqual(results(recipe)["mass_attenuation_cm2_g"], expected)
        composition = elemental_composition(recipe["mass_fractions"])
        self.assertAlmostEqual(composition["H"], 0.4 * 0.143711 + 0.1)
        self.assertAlmostEqual(composition["C"], 0.4 * 0.856289)
        self.assertAlmostEqual(composition["Fe"], 0.5)
        recipe["mass_fractions"] = {"unobtainium": 1}
        with self.assertRaises(ValueError):
            validate_recipe(recipe)

    def test_mu_from_uncollided_counts_and_limits(self):
        counts = attenuation_estimate(100000, 90000, 10)
        self.assertAlmostEqual(counts["mu_cm_inv"], -math.log(0.9))
        low, high = counts["mu_95_percent_wilson_cm_inv"]
        self.assertLess(low, counts["mu_cm_inv"])
        self.assertGreater(high, counts["mu_cm_inv"])
        none_survive = attenuation_estimate(100, 0, 10)
        self.assertIsNone(none_survive["mu_cm_inv"])
        self.assertGreater(none_survive["mu_95_percent_wilson_cm_inv"][0], 0)
        self.assertIsNone(none_survive["mu_95_percent_wilson_cm_inv"][1])
        all_survive = attenuation_estimate(100, 100, 10)
        self.assertEqual(all_survive["mu_cm_inv"], 0)
        self.assertGreater(all_survive["mu_95_percent_wilson_cm_inv"][1], 0)
        for args in ((0, 0, 1), (10, 11, 1), (10, 1, 0), (10, 1, float("nan"))):
            with self.assertRaises(ValueError):
                attenuation_estimate(*args)

    def test_primary_interactions_are_counted_once(self):
        steps = [{
            "EventID": [0, 1, 1, 2, 2, 2],
            "TrackID": [1, 1, 1, 1, 1, 2],
            "ParentID": [0, 0, 0, 0, 0, 1],
            "PDGCode": [22, 22, 22, 22, 22, 11],
            "ProcessDefinedStep": ["Transportation", "Rayl", "Transportation",
                                   "Transportation", "Transportation", "compt"],
        }]
        self.assertEqual(uncollided_count(steps, 3), 2)
        with self.assertRaises(ValueError):
            uncollided_count(steps, 4)


if __name__ == "__main__":
    unittest.main()
