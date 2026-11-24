"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../web-model.js");

const tables = Object.fromEntries(Object.keys(model.densities).map(name => [
  name, model.parseTable(fs.readFileSync(path.join(__dirname, "../data", `${name}.csv`), "utf8"))
]));
const elements = JSON.parse(fs.readFileSync(path.join(__dirname, "../data", "elements.json"), "utf8"));
for (const [symbol, entry] of Object.entries(elements)) {
  tables[symbol] = model.parseTable(entry.rows.map(row => row.join(",")).join("\n"));
}
const close = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-10 * Math.max(1, Math.abs(expected)), `${actual} != ${expected}`);
close(model.massAttenuation(tables.lead, 100), 5.549);
close(model.massAttenuation(tables.lead, Math.sqrt(100 * 150)), Math.sqrt(5.549 * 2.014));
const tungsten = tables.tungsten;
const i = tungsten.findIndex((row, index) => index > 0 && row[0] === tungsten[index - 1][0]);
const edge = tungsten[i][0];
close(model.massAttenuation(tungsten, edge), tungsten[i][1]);
close(model.massAttenuation(tungsten, edge * (1 - 1e-12)), tungsten[i - 1][1]);
const recipe = {mass_fractions: {polyethylene: 0.3, tungsten: 0.4, bismuth: 0.3}, density_g_cm3: 2.5, thickness_mm: 1, energy_kev: 100};
const mu = 0.3 * 0.1719 + 0.4 * 4.438 + 0.3 * 5.739;
const result = model.calculate(tables, recipe);
close(result.coefficient, mu);
close(result.transmission, Math.exp(-mu * 2.5 / 10));
close(result.leadEquivalent, mu * 2.5 / (5.549 * 11.34));
close(result.mass, 2.5);
assert.throws(() => model.massAttenuation(tables.lead, 20001));
assert.throws(() => model.parseTable("bad,data"));
const water = model.customFractions([{name: "H", amount: 2}, {name: "O", amount: 1}], "atoms", elements);
close(water.H, (2 / elements.H.z_over_a) / (2 / elements.H.z_over_a + 8 / elements.O.z_over_a));
close(water.H + water.O, 1);
const custom = {mass_fractions: water, density_g_cm3: 1, thickness_mm: 10, energy_kev: 100};
close(model.calculate(tables, custom).coefficient, water.H * model.massAttenuation(tables.H, 100) + water.O * model.massAttenuation(tables.O, 100));
assert.throws(() => model.customFractions([{name: "H", amount: 50}], "mass", elements));
assert.throws(() => model.customFractions([{name: "H", amount: 50}, {name: "H", amount: 50}], "mass", elements));
assert.throws(() => model.customFractions([{name: "polyethylene", amount: 1}], "atoms", elements));
const candidates = [{name: "W", maxPercent: 20}, {name: "Bi", maxPercent: 60}, {name: "H", maxPercent: 100}];
const optimum = model.optimizeFractions(candidates, 30, tables, 100, elements);
close(optimum.polyethylene, 0.3);
close(optimum.Bi, 0.6);
close(optimum.W, 0.1);
close(Object.values(optimum).reduce((a, b) => a + b, 0), 1);
const best = model.calculate(tables, {...recipe, mass_fractions: optimum}).coefficient;
for (let bi = 0; bi <= 60; bi += 10) {
  for (let w = 0; w <= 20; w += 10) {
    const h = 70 - bi - w;
    if (h < 0) continue;
    const fractions = {polyethylene: 0.3, Bi: bi / 100, W: w / 100, H: h / 100};
    assert.ok(best >= model.calculate(tables, {...recipe, mass_fractions: fractions}).coefficient - 1e-12);
  }
}
const energyTables = {H: [[1, 10], [10, 1]], O: [[1, 1], [10, 10]]};
const pair = [{name: "H", maxPercent: 100}, {name: "O", maxPercent: 100}];
assert.deepEqual(model.optimizeFractions(pair, 0, energyTables, 1, elements), {H: 1});
assert.deepEqual(model.optimizeFractions(pair, 0, energyTables, 10, elements), {O: 1});
assert.deepEqual(model.optimizeFractions(pair, 100, energyTables, 1, elements), {polyethylene: 1});
const rounding = model.optimizeFractions([{name: "W", maxPercent: 0.7}], 99.3, tables, 100, elements);
close(rounding.polyethylene + rounding.W, 1);
assert.throws(() => model.optimizeFractions([], 0, tables, 100, elements));
assert.throws(() => model.optimizeFractions(candidates, -1, tables, 100, elements));
assert.throws(() => model.optimizeFractions([{name: "W", maxPercent: 69}], 30, tables, 100, elements));
assert.throws(() => model.optimizeFractions([{name: "W", maxPercent: 101}], 0, tables, 100, elements));
assert.throws(() => model.optimizeFractions([{name: "W", maxPercent: 100}, {name: "W", maxPercent: 100}], 0, tables, 100, elements));
assert.throws(() => model.optimizeFractions([{name: "polyethylene", maxPercent: 100}], 0, tables, 100, elements));
const tested = [
  {name: "tungsten", recipe: {...recipe, mass_fractions: {W: 1}}, bendTest: {radius: 5, method: "test A"}},
  {name: "bismuth", recipe: {...recipe, mass_fractions: {Bi: 1}}, bendTest: {radius: 10, method: "test A"}},
  {name: "untested", recipe: {...recipe, mass_fractions: {Bi: 1}, density_g_cm3: 30}, bendTest: null}
];
assert.equal(model.bestTestedRecipe(tested, 5, tables, 100).name, "tungsten");
assert.equal(model.bestTestedRecipe(tested, 10, tables, 100).name, "bismuth");
assert.equal(model.bestTestedRecipe(tested, 4, tables, 100), null);
assert.throws(() => model.bestTestedRecipe(tested, 0, tables, 100));
const saturated = tested.slice(0, 2).map(item => ({...item, recipe: {...item.recipe, density_g_cm3: 30, thickness_mm: 1000}}));
assert.equal(model.calculate(tables, saturated[0].recipe, 1).transmission, 0);
assert.equal(model.calculate(tables, saturated[1].recipe, 1).transmission, 0);
const expected = model.massAttenuation(tables.W, 1) > model.massAttenuation(tables.Bi, 1) ? "tungsten" : "bismuth";
assert.equal(model.bestTestedRecipe(saturated, 10, tables, 1).name, expected);
for (const energy of model.plotEnergies(tables)) {
  for (const rows of Object.values(tables)) model.massAttenuation(rows, energy);
}
console.log("Browser calculation tests passed.");
