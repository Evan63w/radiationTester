# Flexible Shield Lab

A research dashboard for screening candidate elemental mixtures and
polyethylene composites against X-ray or gamma photons. It is not designed for
neutrons, beta particles, or radiation protection decisions.

**Not safety equipment or a safety assessment.** The calculations estimate only
uncollided monoenergetic photon transmission through a uniform flat sheet at
normal incidence. Scattered photons, fluorescence, radiation spectra, dose,
seams, defects and actual use geometry are omitted. The app does not predict
atomic arrangements, bonds, crystal structure, particle dispersion,
flexibility, toxicity, manufacturability or durability. Some listed elements
are radioactive, toxic or otherwise unsuitable. Any proposed material
must be measured and independently evaluated for the intended application.

## Open the dashboard

The browser version runs at <https://evan63w.github.io/radiationTester/>. It
performs the screening calculations locally in your browser and does not run
OpenGATE. The default mode screens a carbon nanotube (CNT) and polyethylene
matrix composite. Enter the CNT mass percentage, a measured or explicitly
assumed **bulk composite density**, sheet thickness and photon energy. The
remaining mass is polyethylene. Default values are illustrative, not a tested
recipe. Polyethylene is an example, not a validated
matrix choice; the CNTs are approximated as homogeneous elemental carbon using
the NIST carbon table. Neither the nanotube architecture, bonding, dispersion,
agglomeration nor the actual material flexibility is predicted. The custom mode
can explore other elemental recipes, but does not provide specific polymer
matrix material models besides polyethylene.

The results show mass attenuation in cm²/g and **linear** attenuation μ in
cm⁻¹, where μ = (μ/ρ) × density. The target comparison defaults to 0.08 cm⁻¹,
not cm²/g; it does not search for or certify a material meeting that target.
At 0.08 cm⁻¹, a 1 mm sheet has approximately 99.2% uncollided transmission
and the half-value thickness is about 8.66 cm. A larger μ reduces transmission
at fixed thickness and energy; neither μ nor a numerical target alone establishes
actual shielding performance.

The optimizer mode lets you select candidate elements, set each
element's maximum mass percentage, specify a fixed polyethylene binder mass
percentage, and enter an assumed bulk density. At the selected photon energy
and thickness it minimizes uncollided transmission by assigning the remaining
mass to elements in descending order of their NIST mass attenuation
coefficients, up to their limits. The limits must allow the remaining mass to
total 100%. Elements need not appear in the result. With no restrictive limits
the result is typically just the strongest element plus the specified binder.
The density is held fixed across all compositions, not predicted from them;
the resulting density and mixture may be physically unattainable. Changing the
energy may change the optimum. The optimizer does not assess flexibility,
toxicity, cost, stability, or manufacturability.

For a flexibility constraint, save actual tested samples using their composition,
measured density and thickness. Optionally enter each sample's measured minimum
bend radius without damage and its test method and conditions. The tested
recipe screen selects the lowest modeled photon transmission among saved
samples whose measured radius is at or below a user-specified limit. Only
compare consistent test conditions (including temperature, bend cycles and
damage criteria). This ranks only the supplied samples and one mechanical
measurement; it cannot predict flexibility of new mixtures, confirm long-term
durability, or validate shielding. Comparing results at a different photon
energy recalculates attenuation, not the mechanical test.

Choose the preset or custom mode to explore mixtures of the 92 NIST
elements and polyethylene, by mass percentage or by relative atom count
(elements only). Atom counts are converted to mass fractions using approximate
atomic masses derived from NIST's rounded Z/A values; isotopic composition and
chemical bonding are not modeled. In custom mode provide a measured or
explicitly assumed bulk density. Recipe comparisons are temporary unless
exported. Chemical bonds, particle size, dispersion, layers, and other spatial
arrangements cannot be determined from element choices alone. Evaluating them
requires a specified structure or geometry and suitable physical models or
simulations, followed by measurements; this homogeneous model does not resolve
them.

## Run the Python dashboard locally

Requires Python 3.9 or newer. From this directory:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Adjust the mass fractions, thickness, photon energy, and lead reference in the
sidebar. The density is an ideal void-free additive-volume estimate, not a
measurement; use the measured density when available. Save several recipes to
compare them at the currently selected energy, then download the comparison CSV.
Saved recipes exist only for the current browser session. Export a simulation
recipe separately if you want to keep those inputs.

## Optional OpenGATE simulation

The dashboard's simulation recipe can be passed to the included OpenGATE 10
script. Use Python 3.10 or later; see the [installation guide](https://opengate-python.readthedocs.io/en/master/user_guide/user_guide_installation.html)
for platform and Python requirements. Download `recipe.json` from the dashboard,
then create a separate environment and run from this directory (substitute
your compatible Python interpreter if necessary):

```sh
python3.12 -m venv .gate-venv
source .gate-venv/bin/activate
python -m pip install -r requirements-gate.txt
python run_gate.py /path/to/recipe.json --primaries 100000 --output gate-output
```

For an independent Geant4 interaction-count estimate of linear μ, use a **new
or empty** output directory:

```sh
python run_gate.py /path/to/recipe.json --primaries 100000 --estimate-mu --output gate-mu-output
```

The optional estimator records all primary-photon steps in the slab, including
zero-energy-deposition steps, and counts unique primary events with no
non-transport interaction. For this fixed normal pencil beam and homogeneous
slab, it estimates `mu = -ln(uncollided / primaries) / thickness_cm`. It writes
the counts, μ and an approximate 95% Wilson binomial interval transformed to
μ in `mu-estimate.json`; `null` for μ and the upper interval bound means zero
uncollided photons were observed and no finite upper estimate is available.
If all photons are uncollided, the point estimate is zero but the upper
interval remains positive. The interval reflects Monte Carlo sampling only,
not uncertainties in the Geant4 physics, material model or real-world
measurements. Small collision counts at low μ or low transmission can make
the estimate imprecise; increase the number of primaries and inspect the
interval. The saved `slab-steps.root` can be large.

Compare results across several slab thicknesses and with narrow-beam
measurements; a single simulation is not a material characterization. Geant4
uses elemental composition and a homogeneous density, not individual CNTs,
their contacts, orientations, matrix interfaces or mechanical properties.
Independently measure the actual sample's density and bend behavior under
defined conditions. The simulation does not establish that the matrix is
flexible or that the composite is safe.

The first run may download Geant4 physics data. The script models a homogeneous,
100 mm square slab in vacuum, a normally incident monoenergetic pencil beam,
and a 100 mm square phase-space plane just behind it. It writes simulation
statistics and, when particles reach the plane, a ROOT phase-space file. Entries
can include scattered particles, secondaries and repeat crossings, so their
count divided by primaries is **not** necessarily a transmission fraction. The
simulation is a starting point for expert analysis, not a validated dose or
shielding evaluation; examine the geometry, physics settings, production cuts
and convergence for the intended study. It does not model flexibility.

## Calculation and sources

The bundled CSV tables are the energy (MeV) and mass attenuation coefficient
(cm²/g) columns of the NIST X-Ray Mass Attenuation Coefficients tables for
[polyethylene](https://physics.nist.gov/PhysRefData/XrayMassCoef/ComTab/polyethylene.html),
[tungsten](https://physics.nist.gov/PhysRefData/XrayMassCoef/ElemTab/z74.html),
[bismuth](https://physics.nist.gov/PhysRefData/XrayMassCoef/ElemTab/z83.html),
and [lead](https://physics.nist.gov/PhysRefData/XrayMassCoef/ElemTab/z82.html).
The elemental dataset contains the same columns from
[NIST's element tables](https://physics.nist.gov/PhysRefData/XrayMassCoef/tab3.html)
for Z=1 through 92, plus the Z/A values in
[NIST Table 1](https://physics.nist.gov/PhysRefData/XrayMassCoef/tab1.html).
The tables approximate atomic absorption edges but do not include chemical
absorption-edge fine structure.
The app uses log-log interpolation, treating absorption-edge discontinuities
separately and using the upper value exactly at an edge.

For mass fractions `w_i`, the mixture rule is `(mu/rho) = sum(w_i * (mu/rho)_i)`.
Uncollided transmission is `exp(-(mu/rho) * density * thickness)`, with
thickness in cm. Areal mass in kg/m² equals density in g/cm³ times thickness in
mm. Lead equivalent is the thickness of lead giving the same uncollided
transmission **at the selected energy**; it is not a broad-spectrum rating.
Ideal density assumes additive component volumes: `1 / sum(w_i / density_i)`.
The polyethylene elemental mass fractions in the OpenGATE script come from
[NIST's composition table](https://physics.nist.gov/cgi-bin/Star/compos.pl?matno=221).

Run Python tests with `python -m unittest discover -s tests` and browser
calculation tests with `node tests/test_web_model.js`.
