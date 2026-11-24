"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../web-model.js");

const tables = Object.fromEntries(Object.keys(model.densities).map(name => [
  name, model.parseTable(fs.readFileSync(path.join(__dirname, "../data", `${name}.csv`), "utf8"))
]));
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
for (const energy of model.plotEnergies(tables)) {
  for (const rows of Object.values(tables)) model.massAttenuation(rows, energy);
}
console.log("Browser calculation tests passed.");
