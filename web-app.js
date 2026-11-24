"use strict";

const model = window.ShieldModel;
const $ = id => document.getElementById(id);
let tables;
let currentRecipe;
let savedRecipes = [];

function number(id, min, max) {
  const field = $(id);
  const value = Number(field.value);
  if (!field.value.trim() || !Number.isFinite(value) || value < min || value > max) {
    throw new Error(`${field.previousElementSibling.textContent} must be between ${min} and ${max}.`);
  }
  return value;
}

function readRecipe() {
  const tungsten = Number($("tungsten").value);
  $("bismuth").max = String(100 - tungsten);
  if (Number($("bismuth").value) > 100 - tungsten) $("bismuth").value = String(100 - tungsten);
  const bismuth = Number($("bismuth").value);
  const fractions = {polyethylene: (100 - tungsten - bismuth) / 100, tungsten: tungsten / 100, bismuth: bismuth / 100};
  $("tungsten-value").textContent = `${tungsten}%`;
  $("bismuth-value").textContent = `${bismuth}%`;
  $("polyethylene-value").textContent = `${100 - tungsten - bismuth}%`;
  const ideal = model.idealDensity(fractions);
  $("ideal-density").textContent = ideal.toFixed(3);
  $("density-field").hidden = !$("use-density").checked;
  return {
    mass_fractions: fractions,
    density_g_cm3: $("use-density").checked ? number("density", 0.001, 30) : ideal,
    thickness_mm: number("thickness", 0.001, 1000),
    energy_kev: number("energy", 1, 20000)
  };
}

const fmt = value => Number(value.toPrecision(4)).toString();

function renderChart(recipe, leadThickness) {
  const svg = $("chart");
  svg.replaceChildren();
  const ns = "http://www.w3.org/2000/svg";
  function element(tag, attributes, text) {
    const node = document.createElementNS(ns, tag);
    for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
    if (text !== undefined) node.textContent = text;
    svg.appendChild(node);
  }
  const x = e => 50 + Math.log(e) / Math.log(20000) * 690;
  const y = t => 285 - t * 250;
  for (const t of [0, 0.25, 0.5, 0.75, 1]) {
    element("line", {x1: 50, x2: 740, y1: y(t), y2: y(t), stroke: "#dce5e8"});
    element("text", {x: 43, y: y(t) + 4, "text-anchor": "end", fill: "#58707d", "font-size": 12}, String(t * 100));
  }
  for (const e of [1, 10, 100, 1000, 10000, 20000]) {
    element("text", {x: x(e), y: 306, "text-anchor": e === 1 ? "start" : e === 20000 ? "end" : "middle", fill: "#58707d", "font-size": 12}, String(e));
  }
  const energies = model.plotEnergies(tables);
  const composite = energies.map(e => `${x(e)},${y(model.calculate(tables, recipe, e).transmission)}`).join(" ");
  const lead = energies.map(e => `${x(e)},${y(Math.exp(-model.massAttenuation(tables.lead, e) * model.densities.lead * leadThickness / 10))}`).join(" ");
  element("polyline", {points: composite, fill: "none", stroke: "#087c88", "stroke-width": 2});
  element("polyline", {points: lead, fill: "none", stroke: "#c16838", "stroke-width": 2});
}

function comparisonRows(energy) {
  return savedRecipes.map(saved => {
    const result = model.calculate(tables, saved.recipe, energy);
    const f = saved.recipe.mass_fractions;
    return [saved.name, f.tungsten * 100, f.bismuth * 100, f.polyethylene * 100,
      saved.recipe.density_g_cm3, saved.recipe.thickness_mm, result.transmission * 100,
      result.mass, result.leadEquivalent];
  });
}

function renderComparisons(energy) {
  const rows = comparisonRows(energy);
  const tbody = $("comparison").querySelector("tbody");
  tbody.replaceChildren();
  for (const row of rows) {
    const tr = document.createElement("tr");
    for (const value of row) {
      const td = document.createElement("td");
      td.textContent = typeof value === "number" ? fmt(value) : value;
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
  $("comparison").hidden = !rows.length;
  $("export-csv").disabled = !rows.length;
}

function update() {
  try {
    const recipe = readRecipe();
    const leadThickness = number("lead-thickness", 0, 1000);
    const result = model.calculate(tables, recipe);
    const leadTransmission = Math.exp(-model.massAttenuation(tables.lead, recipe.energy_kev) * model.densities.lead * leadThickness / 10);
    $("energy-heading").textContent = `At ${fmt(recipe.energy_kev)} keV`;
    $("transmission").textContent = `${fmt(result.transmission * 100)}%`;
    $("mass").textContent = `${fmt(result.mass)} kg/m²`;
    $("lead-equivalent").textContent = `${fmt(result.leadEquivalent)} mm`;
    $("coefficient").textContent = `${fmt(result.coefficient)} cm²/g`;
    $("lead-comparison").textContent = `At this energy, ${fmt(leadThickness)} mm of lead transmits ${fmt(leadTransmission * 100)}% of uncollided photons and weighs ${fmt(model.densities.lead * leadThickness)} kg/m². Lead equivalence is energy-specific and only refers to this narrow-beam calculation.`;
    renderChart(recipe, leadThickness);
    renderComparisons(recipe.energy_kev);
    currentRecipe = recipe;
    $("error").hidden = true;
    $("save").disabled = false;
    $("export-json").disabled = false;
  } catch (error) {
    currentRecipe = null;
    $("error").textContent = error.message;
    $("error").hidden = false;
    $("save").disabled = true;
    $("export-json").disabled = true;
    $("export-csv").disabled = true;
    $("energy-heading").textContent = "Results unavailable";
    for (const id of ["transmission", "mass", "lead-equivalent", "coefficient"]) $(id).textContent = "—";
    $("lead-comparison").textContent = "";
    $("chart").replaceChildren();
    $("comparison").hidden = true;
  }
}

function download(filename, data, type) {
  const url = URL.createObjectURL(new Blob([data], {type}));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function csvCell(value) {
  let text = String(value);
  if (/^[\t\r\n ]*[=+\-@]/.test(text)) text = "'" + text;
  return `"${text.replace(/"/g, '""')}"`;
}

async function init() {
  const loaded = await Promise.all(Object.keys(model.densities).map(async name => {
    const response = await fetch(`data/${name}.csv`);
    if (!response.ok) throw new Error(`Could not load ${name} NIST table (HTTP ${response.status}).`);
    return [name, model.parseTable(await response.text())];
  }));
  tables = Object.fromEntries(loaded);
  for (const id of ["tungsten", "bismuth", "use-density", "density", "thickness", "energy", "lead-thickness"]) {
    $(id).addEventListener("input", update);
  }
  $("save").addEventListener("click", () => {
    const name = $("recipe-name").value.trim();
    if (!name) {
      $("error").textContent = "Enter a recipe name.";
      $("error").hidden = false;
      return;
    }
    savedRecipes.push({name, recipe: currentRecipe});
    $("recipe-name").value = `Recipe ${savedRecipes.length + 1}`;
    update();
  });
  $("clear").addEventListener("click", () => { savedRecipes = []; update(); });
  $("export-json").addEventListener("click", () => download("recipe.json", JSON.stringify(currentRecipe, null, 2), "application/json"));
  $("export-csv").addEventListener("click", () => {
    const header = ["Energy keV", "Recipe", "W mass %", "Bi mass %", "PE mass %", "Density g/cm³", "Thickness mm", "Transmission %", "Mass kg/m²", "Lead equivalent mm"];
    const rows = comparisonRows(currentRecipe.energy_kev).map(row => [currentRecipe.energy_kev, ...row]);
    download("shield-comparison.csv", [header, ...rows].map(row => row.map(csvCell).join(",")).join("\r\n") + "\r\n", "text/csv");
  });
  update();
}

$("save").disabled = true;
$("export-json").disabled = true;
init().catch(error => {
  $("error").textContent = `Dashboard could not start: ${error.message}`;
  $("error").hidden = false;
});
