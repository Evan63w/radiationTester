import math
import unittest

from shielding import ideal_density, mass_attenuation, plot_energies, results, table, transmission, validate_recipe


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


if __name__ == "__main__":
    unittest.main()
