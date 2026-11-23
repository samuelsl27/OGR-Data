"""What a language model needs to know to use OGR Data correctly.

English on purpose: the reader is a model (as OGR-Slip2D's guide).
``INSTRUCTIONS`` travels with every connection; ``GUIDE`` is the full text,
served as the resource ``ogr-data://guide``. Every rule that changes a
NUMBER is in the short one.
"""

SOURCE_URL = "https://github.com/samuelsl27/OGR-Data"

INSTRUCTIONS = """\
OGR Data: rock and soil strength properties (RSData / RocData style): ten
strength criteria, envelopes and equivalent Mohr-Coulomb, Hoek-Brown from
GSI/mi/D, test data fitting and calibration, element test simulation, and
estimation without tests (GSI charts and calculator, mi, D, MR, USCS).
Units in and out: stresses kPa, unit weight kN/m3, lengths m, angles deg.
Workflow: project_new (one material) -> material_set (criterion +
parameters) -> material_compute / render_envelope -> project_save.
Pass the project_id you get back; it may be omitted while one project is
open. A material is named by its name or its 0-based index; omitted = the
selected one (material_add selects the new one).
Rules that change the number:
- material_set with a NEW criterion starts from that criterion's defaults;
  only the parameters you pass change. Parameter names: catalog('criteria').
- application_mode 'tunnel' / 'slope' (Hoek-Brown criteria only) computes
  sig3max from sigcm, unit weight and depth and overrides sig3max_kpa.
- The GHB rock-mass fit (fit_data) gives mb and s for CLASSIC Hoek-Brown.
- GSI charts: u = 0..1 from VERY GOOD to VERY POOR, v = 0..1 from the top
  structure row down; a value in an N/A cell is null.
material_copy gives the text other OGR programs paste (Slip2D, FEM2D).
Full guide: resource ogr-data://guide.
"""

GUIDE = """\
# OGR Data — guide for agents

## Units
Every value you send or receive: stresses in kPa, unit weight in kN/m3,
lengths in m, angles in degrees, strains as fractions (0.01 = 1 %). The
project's display_stress_unit only changes what the window shows and the
default unit of pictures and reports.

## Projects and materials
* project_new creates a project with one material (the first criterion of
  the registry, as the window). material_add adds one from a template:
  'material', 'rock' (Generalized Hoek-Brown + an empty failure state) or
  'soil' (Mohr-Coulomb + a test simulation and a stress path).
* material_set edits. Parameters are the registry fields of the criterion
  (catalog('criteria') lists them with unit, kind, default and choices).
  Enum fields take one of their options exactly; table fields a list of
  rows.
* sig3max_kpa is the upper limit of the envelope range (sigma3 for
  principal criteria). For Hoek-Brown criteria, application_mode 'tunnel'
  or 'slope' computes it (Hoek 2002 / Marinos-Hoek) from sigcm, the unit
  weight and the tunnel depth or slope height.
* material_compute returns the derived values: GHB mb, s, a, sigt, sigc,
  sigcm, equivalent c and phi over the range, Erm (method of the
  'modulus_method' parameter); classic HB sigcm and equivalent MC; Power
  Curve and Barton-Bandis the best-fit MC. Also the sampled envelope.

## Test data
* failure_state_set: peak test results. triaxial points are [sigma3,
  sigma1], direct shear [sigma_n, tau], both kPa; a third value true
  excludes the point. general: 6-component tensors.
* fit_data fits one criterion to x/y data (no project needed); apply_to
  writes the result into a material. calibrate fits to the failure states
  of a material (several at once) and can add the result as a new
  material (new_material_name); the source material is not changed.
* stress_path_set: measured paths; the answer lists the step columns.

## Test simulation
test_simulation_set defines an element test (uniaxial, triaxial, biaxial,
simple shear, general; drained / undrained; compression / tension; cyclic)
and test_simulation_run integrates it with the material's constitutive
model (Mohr-Coulomb, Hoek-Brown, GHB, Drucker-Prager, Cam-Clay, MCC,
Softening-Hardening, NorSand) and its stiffness (material_set stiffness).
confining_kpa is the initial effective LATERAL stress; axial = lateral / k0.

## Estimation without tests
* gsi_quantified: GSI = 1.5 JCond89 + RQD/2 and variants (Hoek, Carter &
  Diederichs 2013); RQD from core, lambda or Jv.
* gsi_chart: read a digitized chart (general 2000, flysch 2000,
  heterogeneous V. Marinos 2007) at (u, v) or at a rock-mass type.
  Digitization error up to 1.3 GSI: quote a range, not a decimal.
* table_get: sigci grades, mi, GSI ranges, D, MR (Ei = MR sigci), basic
  friction angles, soil grades, USCS compacted properties.
* classify_uscs: ASTM D2487 symbol + typical properties; create_material
  adds the Mohr-Coulomb material of the group (UFC 3-220-01N).
* barton_estimate: phi_r from Schmidt rebounds, JRC/JCS scale correction.

## Database
database_search / database_get / database_use: built-in records (Hoek
tables, CANMET 1995, MnDOT 2018) and the user's own; use 'material'
creates a GHB material (sigci, mi), 'failure_state' adds the specimens.

## Outputs
render_envelope returns a PNG; report_generate writes the HTML report
(views = materials drawn as graph views with their values).
"""
