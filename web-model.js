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

  function optimizeFractions(components, binderPercent, tables, energy, elements) {
    if (!components.length) throw new Error("Add at least one candidate element.");
    if (!Number.isFinite(binderPercent) || binderPercent < 0 || binderPercent > 100) {
      throw new Error("Binder percentage must be between 0 and 100.");
    }
    const seen = new Set();
    const candidates = components.map(({name, maxPercent}) => {
      if (seen.has(name)) throw new Error(`Candidate ${name} is listed more than once.`);
      seen.add(name);
      if (!Object.hasOwn(elements, name) || !Object.hasOwn(tables, name)) throw new Error(`Unknown candidate element: ${name}`);
      if (!Number.isFinite(maxPercent) || maxPercent < 0 || maxPercent > 100) {
        throw new Error(`Maximum percentage for ${name} must be between 0 and 100.`);
      }
      return {name, maxPercent, coefficient: massAttenuation(tables[name], energy)};
    });
    const required = 100 - binderPercent;
    const tolerance = Number.EPSILON * 100 * (candidates.length + 2);
    if (candidates.reduce((sum, candidate) => sum + candidate.maxPercent, 0) < required - tolerance) {
      throw new Error("Candidate maximum percentages cannot fill the remaining mass after the binder.");
    }
    candidates.sort((a, b) => b.coefficient - a.coefficient);
    const fractions = {};
    if (binderPercent > 0) fractions.polyethylene = binderPercent / 100;
    let remaining = required;
    for (const candidate of candidates) {
      const amount = Math.min(candidate.maxPercent, Math.max(remaining, 0));
      if (amount > 0) fractions[candidate.name] = amount / 100;
      remaining -= amount;
    }
    return fractions;
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

  function bestTestedRecipe(savedRecipes, maxRadius, tables, energy) {
    if (!Number.isFinite(maxRadius) || maxRadius <= 0) throw new Error("Maximum bend radius must be greater than zero.");
    let best = null, bestDepth = -Infinity;
    for (const saved of savedRecipes) {
      if (!saved.bendTest || saved.bendTest.radius > maxRadius) continue;
      const result = calculate(tables, saved.recipe, energy);
      const depth = result.coefficient * saved.recipe.density_g_cm3 * saved.recipe.thickness_mm / 10;
      if (depth > bestDepth) {
        best = saved;
        bestDepth = depth;
      }
    }
    return best;
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
  const api = {densities, materials, parseTable, massAttenuation, idealDensity, customFractions, optimizeFractions, calculate, bestTestedRecipe, plotEnergies};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.ShieldModel = api;
})(globalThis);
