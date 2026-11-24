(function (root) {
  "use strict";
  const densities = {polyethylene: 0.94, tungsten: 19.3, bismuth: 9.78, lead: 11.34};
  const materials = ["polyethylene", "tungsten", "bismuth"];

  function parseTable(text) {
    const rows = text.trim().split(/\r?\n/).map(line => {
      const parts = line.split(",");
      if (parts.length !== 2 || parts.some(x => !x.trim())) throw new Error("Invalid NIST table row");
      return parts.map(Number);
    }).map(([energy, mu]) => [energy * 1000, mu]);
    if (!rows.length || rows.some(([e, mu], i) =>
      !Number.isFinite(e) || !Number.isFinite(mu) || e <= 0 || mu <= 0 || (i > 0 && e < rows[i - 1][0]))) {
      throw new Error("Invalid or unsorted NIST table");
    }
    return rows;
  }

  function massAttenuation(rows, energy) {
    if (!Number.isFinite(energy) || energy < rows[0][0] || energy > rows[rows.length - 1][0]) {
      throw new Error("Photon energy must be between 1 and 20,000 keV.");
    }
    let low = 0, high = rows.length;
    while (low < high) {
      const mid = Math.floor((low + high) / 2);
      if (rows[mid][0] <= energy) low = mid + 1;
      else high = mid;
    }
    const [e1, mu1] = rows[low - 1];
    if (low === rows.length || e1 === energy) return mu1;
    const [e2, mu2] = rows[low];
    const fraction = Math.log(energy / e1) / Math.log(e2 / e1);
    return Math.exp(Math.log(mu1) + fraction * Math.log(mu2 / mu1));
  }

  function idealDensity(fractions) {
    return 1 / materials.reduce((sum, name) => sum + fractions[name] / densities[name], 0);
  }

  function customFractions(components, basis, elements) {
    if (!components.length) throw new Error("Add at least one component.");
    const weights = {};
    for (const {name, amount} of components) {
      if (Object.hasOwn(weights, name)) throw new Error(`Component ${name} is listed more than once.`);
      if (!(name in elements) && name !== "polyethylene") throw new Error(`Unknown component: ${name}`);
      if (basis === "atoms" && name === "polyethylene") throw new Error("Atom-count mode accepts elements only, not polyethylene.");
      if (!Number.isFinite(amount) || amount <= 0) throw new Error("Each component amount must be greater than zero.");
      weights[name] = basis === "atoms" ? amount * elements[name].number / elements[name].z_over_a : amount;
    }
    const total = Object.values(weights).reduce((a, b) => a + b, 0);
    if (!Number.isFinite(total) || total <= 0) throw new Error("Component total must be positive and finite.");
    if (basis === "mass" && Math.abs(total - 100) > 1e-6) throw new Error(`Mass percentages must total 100% (currently ${total.toFixed(3)}%).`);
    return Object.fromEntries(Object.entries(weights).map(([name, weight]) => [name, weight / total]));
  }

  function calculate(tables, recipe, energy = recipe.energy_kev) {
    const f = recipe.mass_fractions;
    const mu = Object.entries(f).reduce((sum, [name, weight]) => sum + (weight ? weight * massAttenuation(tables[name], energy) : 0), 0);
    const depth = mu * recipe.density_g_cm3 * recipe.thickness_mm / 10;
    return {
      coefficient: mu,
      transmission: Math.exp(-depth),
      mass: recipe.density_g_cm3 * recipe.thickness_mm,
      leadEquivalent: depth / (massAttenuation(tables.lead, energy) * densities.lead) * 10
    };
  }

  function plotEnergies(tables) {
    const values = [1, 20000];
    for (let i = 1; i < 300; i++) values.push(10 ** (i * Math.log10(20000) / 300));
    for (const rows of Object.values(tables)) {
      for (let i = 1; i < rows.length; i++) {
        if (rows[i][0] === rows[i - 1][0]) values.push(rows[i][0] * (1 - 1e-12), rows[i][0]);
      }
    }
    return [...new Set(values)].sort((a, b) => a - b);
  }
  const api = {densities, materials, parseTable, massAttenuation, idealDensity, customFractions, calculate, plotEnergies};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.ShieldModel = api;
})(globalThis);
