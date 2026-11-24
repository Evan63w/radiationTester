# Flexible Shield Lab

A research dashboard for screening polyethylene composites with elemental
tungsten and bismuth fillers against X-ray or gamma photons. It is not designed
for neutrons, beta particles, or radiation protection decisions.

**Not safety equipment or a safety assessment.** The calculations estimate only
uncollided monoenergetic photon transmission through a uniform flat sheet at
normal incidence. Scattered photons, fluorescence, radiation spectra, dose,
seams, defects and actual use geometry are omitted. The app does not predict
flexibility, toxicity, manufacturability or durability. Any proposed material
must be measured and independently evaluated for the intended application.

## Open the dashboard

The browser version runs at <https://evan63w.github.io/radiationTester/>. It
performs the screening calculations locally in your browser and does not run
OpenGATE. Recipe comparisons are temporary unless exported.

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
