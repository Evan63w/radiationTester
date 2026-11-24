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
for (const energy of model.plotEnergies(tables)) {
  for (const rows of Object.values(tables)) model.massAttenuation(rows, energy);
}
console.log("Browser calculation tests passed.");
