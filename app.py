import csv
import io
import json

import altair as alt
import pandas as pd
import streamlit as st

from shielding import DENSITIES, ideal_density, plot_energies, results, mass_attenuation, transmission

st.set_page_config(page_title="Flexible Shield Lab", page_icon="🛡️", layout="wide")
st.title("Flexible Shield Lab")
st.caption("Explore candidate photon-shielding composites before laboratory testing.")
st.warning(
    "Research screening only — not a safety assessment. Estimates cover uncollided, "
    "monoenergetic X-ray/gamma photons only. They exclude scatter, fluorescence, "
    "geometry, energy spectra, defects and mechanical performance. Never use these "
    "results alone to select protective equipment."
)

with st.sidebar:
    st.header("Recipe")
    st.caption("Polyethylene binder with elemental metal fillers. Percentages are by mass, not volume.")
    tungsten = st.slider("Tungsten (mass %)", 0, 100, 40)
    if tungsten == 100:
        bismuth = 0
        st.caption("Bismuth: 0% (all mass is tungsten)")
    else:
        bismuth = st.slider("Bismuth (mass %)", 0, 100 - tungsten, min(30, 100 - tungsten))
    fractions = {
        "polyethylene": (100 - tungsten - bismuth) / 100,
        "tungsten": tungsten / 100,
        "bismuth": bismuth / 100,
    }
    st.write(f"Polyethylene: **{fractions['polyethylene'] * 100:.0f}%**")
    estimated_density = ideal_density(fractions)
    st.caption(f"Ideal, void-free density estimate: {estimated_density:.3f} g/cm³")
    use_measured = st.checkbox("Use measured composite density")
    density = st.number_input("Measured density (g/cm³)", min_value=0.001, max_value=30.0,
                              value=float(round(estimated_density, 3)), format="%.3f") if use_measured else estimated_density
    thickness = st.number_input("Sheet thickness (mm)", min_value=0.001, max_value=1000.0, value=1.0)
    energy = st.number_input("Photon energy (keV)", min_value=1.0, max_value=20000.0, value=100.0)
    lead_thickness = st.number_input("Lead reference thickness (mm)", min_value=0.0, max_value=1000.0, value=0.25)

recipe = {"mass_fractions": fractions, "density_g_cm3": density,
          "thickness_mm": thickness, "energy_kev": energy}
out = results(recipe)
lead_t = transmission(mass_attenuation("lead", energy), DENSITIES["lead"], lead_thickness)
lead_mass = DENSITIES["lead"] * lead_thickness

st.subheader(f"At {energy:g} keV")
a, b, c, d = st.columns(4)
a.metric("Uncollided transmission", f"{out['transmission'] * 100:.3g}%")
b.metric("Areal mass", f"{out['areal_mass_kg_m2']:.3g} kg/m²")
c.metric("Lead-equivalent thickness", f"{out['lead_equivalent_mm']:.3g} mm")
d.metric("Mass attenuation coefficient", f"{out['mass_attenuation_cm2_g']:.4g} cm²/g")
st.caption(
    f"At this energy, {lead_thickness:g} mm of lead transmits {lead_t * 100:.3g}% "
    f"of uncollided photons and weighs {lead_mass:.3g} kg/m². Lead equivalence "
    "is energy-specific and only refers to this narrow-beam calculation."
)

st.subheader("Transmission across photon energies")
curves = []
for e in plot_energies():
    curves.append({"Energy (keV)": e, "Transmission (%)": results(recipe, e)["transmission"] * 100, "Material": "Composite"})
    curves.append({"Energy (keV)": e, "Transmission (%)": transmission(mass_attenuation("lead", e), DENSITIES["lead"], lead_thickness) * 100, "Material": "Lead reference"})
chart = alt.Chart(pd.DataFrame(curves)).mark_line().encode(
    x=alt.X("Energy (keV):Q", scale=alt.Scale(type="log"), title="Photon energy (keV, log scale)"),
    y=alt.Y("Transmission (%):Q", scale=alt.Scale(domain=[0, 100])),
    color="Material:N",
    tooltip=["Material:N", alt.Tooltip("Energy (keV):Q", format=".4g"), alt.Tooltip("Transmission (%):Q", format=".4g")],
).properties(height=340)
st.altair_chart(chart, use_container_width=True)
st.caption("Lines use log-log interpolation of NIST tables; sharp jumps are absorption edges. Exact edge values use the upper side.")

st.subheader("Compare recipes")
if "recipes" not in st.session_state:
    st.session_state.recipes = []
name = st.text_input("Recipe name", value=f"Recipe {len(st.session_state.recipes) + 1}")
col1, col2 = st.columns(2)
if col1.button("Save current recipe"):
    if not name.strip():
        st.error("Enter a recipe name.")
    else:
        st.session_state.recipes.append({"name": name.strip(), **recipe})
if col2.button("Clear saved recipes"):
    st.session_state.recipes = []
if st.session_state.recipes:
    rows = []
    for saved in st.session_state.recipes:
        comparison = results(saved, energy)
        rows.append({
            "Recipe": saved["name"], "W mass %": saved["mass_fractions"]["tungsten"] * 100,
            "Bi mass %": saved["mass_fractions"]["bismuth"] * 100,
            "PE mass %": saved["mass_fractions"]["polyethylene"] * 100,
            "Density g/cm³": saved["density_g_cm3"], "Thickness mm": saved["thickness_mm"],
            "Transmission %": comparison["transmission"] * 100,
            "Mass kg/m²": comparison["areal_mass_kg_m2"],
            "Lead equivalent mm": comparison["lead_equivalent_mm"],
        })
    st.caption(f"All saved recipes are recalculated at the current energy ({energy:g} keV). Saved recipes last for this browser session; export them to keep the results.")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["Energy keV"] + list(rows[0]))
    writer.writeheader()
    writer.writerows({"Energy keV": energy, **row} for row in rows)
    st.download_button("Download comparison CSV", buffer.getvalue(), "shield-comparison.csv", "text/csv")

st.subheader("OpenGATE simulation")
st.write(
    "Export the current recipe for the included optional OpenGATE/Geant4 slab simulation. "
    "It records a phase-space file for a monoenergetic pencil beam; it is not a complete "
    "protective-equipment assessment. See the README for installation and execution."
)
st.download_button("Download simulation recipe", json.dumps(recipe, indent=2), "recipe.json", "application/json")

with st.expander("Methods and data sources"):
    st.markdown("""
    * Mass fractions are combined by the mixture rule. Density defaults to the ideal
      additive-volume estimate, assuming no porosity; replace it with a measured value.
    * Transmission is exp(-μ/ρ × density × thickness), for a uniform sheet at normal incidence.
      The lead equivalent is calculated at the selected energy, not over a spectrum.
    * Flexibility, toxicity, manufacturing feasibility, and dose are **not** predicted.
    * NIST mass attenuation tables: [polyethylene](https://physics.nist.gov/PhysRefData/XrayMassCoef/ComTab/polyethylene.html),
      [tungsten](https://physics.nist.gov/PhysRefData/XrayMassCoef/ElemTab/z74.html),
      [bismuth](https://physics.nist.gov/PhysRefData/XrayMassCoef/ElemTab/z83.html),
      [lead](https://physics.nist.gov/PhysRefData/XrayMassCoef/ElemTab/z82.html).
    """)
