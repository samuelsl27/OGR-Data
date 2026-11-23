"""The MCP tools: one per operation of ``ogr_data.api``, written by hand.

By hand (as OGR-Slip2D's ``ogr_mcp.server``) because a tool's description
and parameter types are the whole interface a language model sees.
``tests/test_mcp_server.py`` keeps tools and operations from drifting:
every operation has a tool, every tool parameter reaches its operation.

Every tool body runs inside :func:`_errors`, which turns an ``OgrApiError``
into its coded message and anything else into ``[E_INTERNAL]`` with its
type: the SDK would otherwise send a bare "Error executing tool".

This module imports the SDK; ``ogr_data/mcp_server/__init__.py`` does not.
"""

from __future__ import annotations

import contextlib
import inspect
import json
import logging
from typing import Annotated, Any, Literal, Optional

from mcp.server.mcpserver import Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from .. import __version__
from ..api import OgrApiError, call
from ..api.errors import internal_error
from .guide import GUIDE, INSTRUCTIONS, SOURCE_URL

log = logging.getLogger("ogr_data.mcp")

_READ = ToolAnnotations(readOnlyHint=True, idempotentHint=True)
_EDIT = ToolAnnotations(readOnlyHint=False, destructiveHint=False)
_DESTRUCTIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=True)

# ---------------------------------------------------------------- shared parameter types
ProjectId = Annotated[Optional[str], Field(description="Project handle from project_new/project_open. May be omitted while only one project is open.")]
MaterialRef = Annotated[Optional[str], Field(description="Material name, or its 0-based index as text; default: the selected material.")]
Name = Annotated[str, Field(description="Name of the item (created if it does not exist, replaced if it does).")]
Overwrite = Annotated[bool, Field(description="Replace an existing file.")]
Params = Annotated[Optional[dict[str, Any]], Field(description="Registry parameters by key (kPa, deg), e.g. {'sigci': 50000, 'gsi': 45}. Keys and choices: catalog('criteria').")]
Criterion = Annotated[Optional[str], Field(description="Criterion key, e.g. 'generalized_hoek_brown', 'mohr_coulomb' (catalog('criteria')).")]


def _tool_description(fn) -> str | None:
    return inspect.cleandoc(fn.__doc__) if fn.__doc__ else None


@contextlib.contextmanager
def _errors():
    """Every failure as a message a model can act on."""

    try:
        yield
    except ToolError:
        raise
    except OgrApiError as exc:
        raise ToolError(str(exc)) from None
    except Exception as exc:  # noqa: BLE001 - reported with its type
        log.exception("tool failed")
        raise ToolError(str(internal_error(exc))) from None


def _strip(kwargs: dict) -> dict:
    """Drop the arguments not given, so each operation's own default applies."""

    return {k: v for k, v in kwargs.items() if v is not None}


def build_server(ws) -> MCPServer:
    """An ``MCPServer`` publishing every operation over workspace ``ws``."""

    srv = MCPServer("ogr-data", title="OGR Data",
                    description="Rock and soil strength properties: criteria, envelopes, fitting, test simulation and estimation without tests.",
                    instructions=INSTRUCTIONS, version=__version__, website_url=SOURCE_URL)
    registered: list[str] = []

    def tool(name: str, annotations: ToolAnnotations):
        def deco(fn):
            srv.tool(name=name, annotations=annotations, description=_tool_description(fn))(fn)
            registered.append(name)
            return fn
        return deco

    def run(op_name: str, /, **kwargs) -> dict:
        with _errors():
            return call(ws, op_name, **_strip(kwargs))

    # ------------------------------------------------------------ info
    @tool("server_info", _READ)
    def server_info() -> dict[str, Any]:
        """What this server is, its units and rules, and the open projects. Call it first."""
        return {"server": "ogr-data", "version": __version__, "units": "kPa (stresses), kN/m3 (unit weight), m, degrees",
                "workdir": str(ws.workdir) if ws.workdir else None,
                "open_projects": [{"project_id": h.id, "title": h.project.title, "materials": len(h.project.materials)}
                                  for h in ws.projects.values()],
                "tools": list(registered), "guide": INSTRUCTIONS, "source_code": SOURCE_URL, "licence": "AGPL-3.0-or-later"}

    @tool("catalog", _READ)
    def catalog(kind: Annotated[Literal["criteria", "templates", "application_modes", "modulus_methods", "fits", "calibration",
                                        "failure_states", "stress_paths", "test_simulations", "tables", "gsi_charts",
                                        "stress_units", "report_sections", "symbols"],
                                Field(description="What to list.")] = "criteria") -> dict[str, Any]:
        """What the program offers: criteria with their parameters (unit, kind, default, choices), fits, test types, tables, GSI charts..."""
        return run("catalog", kind=kind)

    # ------------------------------------------------------------ projects
    @tool("project_new", _EDIT)
    def project_new(title: Annotated[Optional[str], Field(description="Project title.")] = None) -> dict[str, Any]:
        """Create a project with one material; returns its project_id."""
        return run("project_new", title=title)

    @tool("project_open", _EDIT)
    def project_open(path: Annotated[str, Field(description="Path of a .ogrdata file, absolute or relative to the server's working folder.")]) -> dict[str, Any]:
        """Open a .ogrdata project; returns its project_id and materials."""
        return run("project_open", path=path)

    @tool("project_save", _EDIT)
    def project_save(project_id: ProjectId = None,
                     path: Annotated[Optional[str], Field(description="Where to save (.ogrdata added if missing); default: its own file.")] = None,
                     overwrite: Overwrite = False) -> dict[str, Any]:
        """Save a project as .ogrdata (the file the window opens)."""
        return run("project_save", project_id=project_id, path=path, overwrite=overwrite)

    @tool("project_close", _DESTRUCTIVE)
    def project_close(project_id: ProjectId = None) -> dict[str, Any]:
        """Close a project; unsaved changes are lost."""
        return run("project_close", project_id=project_id)

    @tool("project_list", _READ)
    def project_list() -> dict[str, Any]:
        """The open projects: project_id, title, file and number of materials."""
        return run("project_list")

    @tool("project_summary", _READ)
    def project_summary(project_id: ProjectId = None) -> dict[str, Any]:
        """Title, file, display unit and the list of materials of a project."""
        return run("project_summary", project_id=project_id)

    @tool("project_set", _EDIT)
    def project_set(project_id: ProjectId = None,
                    title: Annotated[Optional[str], Field(description="Project title.")] = None,
                    display_stress_unit: Annotated[Optional[str], Field(description="Unit the window shows: 'kPa', 'MPa', ... (catalog('stress_units')). Values here stay kPa.")] = None,
                    selected_material: Annotated[Optional[str], Field(description="Material to select (name or 0-based index).")] = None) -> dict[str, Any]:
        """Project title, display stress unit and selected material."""
        return run("project_set", project_id=project_id, title=title, display_stress_unit=display_stress_unit,
                   selected_material=selected_material)

    @tool("project_history", _EDIT)
    def project_history(project_id: ProjectId = None,
                        action: Annotated[Literal["list", "undo", "redo"], Field(description="What to do.")] = "list",
                        steps: Annotated[int, Field(description="How many steps to undo or redo.")] = 1) -> dict[str, Any]:
        """Undo or redo edits of a project, or list them. Every editing tool call is one step."""
        return run("project_history", project_id=project_id, action=action, steps=steps)

    # ------------------------------------------------------------ materials
    @tool("material_add", _EDIT)
    def material_add(project_id: ProjectId = None,
                     template: Annotated[Literal["material", "rock", "soil"], Field(description="'rock': GHB + empty failure state; 'soil': Mohr-Coulomb + test simulation and stress path.")] = "material",
                     name: Annotated[Optional[str], Field(description="Material name (made unique).")] = None,
                     criterion: Criterion = None, parameters: Params = None) -> dict[str, Any]:
        """Add a material from a template and select it; criterion and parameters optional."""
        return run("material_add", project_id=project_id, template=template, name=name, criterion=criterion, parameters=parameters)

    @tool("material_get", _READ)
    def material_get(project_id: ProjectId = None, material: MaterialRef = None) -> dict[str, Any]:
        """Everything about a material: criterion, parameters with units, sig3max, application, test data names."""
        return run("material_get", project_id=project_id, material=material)

    @tool("material_set", _EDIT)
    def material_set(project_id: ProjectId = None, material: MaterialRef = None,
                     name: Annotated[Optional[str], Field(description="New name.")] = None,
                     criterion: Criterion = None, parameters: Params = None,
                     sig3max_kpa: Annotated[Optional[float], Field(description="Envelope range upper limit (kPa); needs application_mode 'custom'.")] = None,
                     application_mode: Annotated[Optional[Literal["custom", "tunnel", "slope"]], Field(description="'tunnel'/'slope' compute sig3max (Hoek-Brown criteria only).")] = None,
                     unit_weight_kn_m3: Annotated[Optional[float], Field(description="Rock mass unit weight for the application (kN/m3).")] = None,
                     depth_m: Annotated[Optional[float], Field(description="Tunnel depth or slope height (m).")] = None,
                     stiffness: Annotated[Optional[dict[str, Any]], Field(description="Stiffness keys to change (catalog('test_simulations') default_stiffness), e.g. {'young': 2e7, 'poisson': 0.25} in kPa.")] = None,
                     color: Annotated[Optional[str], Field(description="Display colour '#rrggbb' ('' = theme colour).")] = None,
                     symbol: Annotated[Optional[str], Field(description="Point symbol of its test data: o, s, ^, D, v.")] = None,
                     visible: Annotated[Optional[bool], Field(description="Drawn in the plots.")] = None) -> dict[str, Any]:
        """Edit a material. A NEW criterion starts from its defaults; only the parameters given change."""
        return run("material_set", project_id=project_id, material=material, name=name, criterion=criterion,
                   parameters=parameters, sig3max_kpa=sig3max_kpa, application_mode=application_mode,
                   unit_weight_kn_m3=unit_weight_kn_m3, depth_m=depth_m, stiffness=stiffness, color=color,
                   symbol=symbol, visible=visible)

    @tool("material_delete", _DESTRUCTIVE)
    def material_delete(project_id: ProjectId = None, material: MaterialRef = None) -> dict[str, Any]:
        """Delete a material (a project keeps at least one)."""
        return run("material_delete", project_id=project_id, material=material)

    @tool("material_duplicate", _EDIT)
    def material_duplicate(project_id: ProjectId = None, material: MaterialRef = None) -> dict[str, Any]:
        """Duplicate a material with its test data under a new name."""
        return run("material_duplicate", project_id=project_id, material=material)

    @tool("material_compute", _READ)
    def material_compute(project_id: ProjectId = None, material: MaterialRef = None,
                         points: Annotated[int, Field(description="Envelope points returned (2-500).")] = 11) -> dict[str, Any]:
        """Derived values (GHB mb, s, a, sigt, sigc, sigcm, equivalent c/phi, Erm; best-fit MC...) and the envelope, kPa."""
        return run("material_compute", project_id=project_id, material=material, points=points)

    @tool("material_copy", _READ)
    def material_copy(project_id: ProjectId = None, material: MaterialRef = None,
                      format: Annotated[Literal["ogr", "tabular"], Field(description="'ogr': the material contract other OGR programs paste; 'tabular': name/value lines for a spreadsheet.")] = "ogr") -> dict[str, Any]:
        """The text Copy Material / Copy Data put on the clipboard."""
        return run("material_copy", project_id=project_id, material=material, format=format)

    @tool("material_paste", _EDIT)
    def material_paste(text: Annotated[str, Field(description="Clipboard text starting with OGR-DATA-MATERIAL:")],
                       project_id: ProjectId = None) -> dict[str, Any]:
        """Add a material from OGR material clipboard text."""
        return run("material_paste", text=text, project_id=project_id)

    @tool("material_import_roc", _EDIT)
    def material_import_roc(path: Annotated[str, Field(description="Path of a RocData .roc file.")],
                            project_id: ProjectId = None) -> dict[str, Any]:
        """Import a RocData file as a new material."""
        return run("material_import_roc", path=path, project_id=project_id)

    # ------------------------------------------------------------ test data and fitting
    @tool("failure_state_set", _EDIT)
    def failure_state_set(name: Name, project_id: ProjectId = None, material: MaterialRef = None,
                          test_type: Annotated[Optional[Literal["triaxial", "direct_shear", "general"]], Field(description="Default triaxial.")] = None,
                          points: Annotated[Optional[list[list[float]]], Field(description="[[sigma3, sigma1], ...] (triaxial) or [[sigma_n, tau], ...] (direct shear), kPa; a 3rd value 1 excludes the point.")] = None,
                          tensors: Annotated[Optional[list[list[float]]], Field(description="general: [[sxx, syy, szz, txy, tyz, txz], ...] kPa.")] = None,
                          color: Annotated[Optional[str], Field(description="'#rrggbb'.")] = None,
                          visible: Annotated[Optional[bool], Field(description="Drawn in the plots.")] = None) -> dict[str, Any]:
        """Create or replace a failure state (peak test results) of a material."""
        return run("failure_state_set", name=name, project_id=project_id, material=material, test_type=test_type,
                   points=points, tensors=tensors, color=color, visible=visible)

    @tool("failure_state_delete", _DESTRUCTIVE)
    def failure_state_delete(name: Annotated[str, Field(description="Failure state name.")], project_id: ProjectId = None,
                             material: MaterialRef = None) -> dict[str, Any]:
        """Delete a failure state."""
        return run("failure_state_delete", name=name, project_id=project_id, material=material)

    @tool("stress_path_set", _EDIT)
    def stress_path_set(name: Name, project_id: ProjectId = None, material: MaterialRef = None,
                        test_type: Annotated[Optional[Literal["uniaxial", "triaxial", "biaxial", "simple_shear"]], Field(description="Test type.")] = None,
                        seepage: Annotated[Optional[Literal["Drained", "Undrained"]], Field(description="Seepage condition.")] = None,
                        loading: Annotated[Optional[Literal["None", "Axial", "Lateral"]], Field(description="Loading direction (triaxial / biaxial).")] = None,
                        strain_type: Annotated[Optional[Literal["None", "Volumetric", "Lateral"]], Field(description="Strain type (uniaxial).")] = None,
                        lateral_stress_kpa: Annotated[Optional[float], Field(description="Initial effective lateral stress (kPa).")] = None,
                        k0: Annotated[Optional[float], Field(description="Initial effective K0.")] = None,
                        steps: Annotated[Optional[list[list[float]]], Field(description="Rows of the step table; its columns come back in the answer (set the configuration first).")] = None,
                        color: Annotated[Optional[str], Field(description="'#rrggbb'.")] = None,
                        visible: Annotated[Optional[bool], Field(description="Drawn in the plots.")] = None) -> dict[str, Any]:
        """Create or replace a measured stress path of a material; answers the step columns."""
        return run("stress_path_set", name=name, project_id=project_id, material=material, test_type=test_type,
                   seepage=seepage, loading=loading, strain_type=strain_type, lateral_stress_kpa=lateral_stress_kpa,
                   k0=k0, steps=steps, color=color, visible=visible)

    @tool("stress_path_delete", _DESTRUCTIVE)
    def stress_path_delete(name: Annotated[str, Field(description="Stress path name.")], project_id: ProjectId = None,
                           material: MaterialRef = None) -> dict[str, Any]:
        """Delete a stress path."""
        return run("stress_path_delete", name=name, project_id=project_id, material=material)

    @tool("fit_data", _EDIT)
    def fit_data(criterion: Annotated[Literal["mohr_coulomb", "hoek_brown", "generalized_hoek_brown", "barton_bandis", "power_curve"], Field(description="Criterion to fit.")],
                 data_kind: Annotated[Literal["triaxial", "direct"], Field(description="triaxial: x = sigma3, y = sigma1; direct: x = normal, y = shear stress.")],
                 x: Annotated[list[float], Field(description="x data (kPa).")],
                 y: Annotated[list[float], Field(description="y data (kPa).")],
                 method: Annotated[Literal["linear", "levenberg_marquardt", "simplex"], Field(description="Linear regression (closed form) or a non-linear solver.")] = "linear",
                 sigci_kpa: Annotated[Optional[float], Field(description="generalized_hoek_brown: fixed sigci (kPa).")] = None,
                 disturbance: Annotated[Optional[float], Field(description="generalized_hoek_brown: fixed D (0-1).")] = None,
                 phi_b_deg: Annotated[Optional[float], Field(description="barton_bandis: basic friction angle (deg).")] = None,
                 apply_to: Annotated[Optional[str], Field(description="Material (name or index) to write the result into; omitted: only report it.")] = None,
                 project_id: ProjectId = None) -> dict[str, Any]:
        """Fit a criterion to test data (Fit to Data); the GHB rock-mass fit gives mb, s for classic Hoek-Brown."""
        return run("fit_data", criterion=criterion, data_kind=data_kind, x=x, y=y, method=method, sigci_kpa=sigci_kpa,
                   disturbance=disturbance, phi_b_deg=phi_b_deg, apply_to=apply_to, project_id=project_id)

    @tool("calibrate", _EDIT)
    def calibrate(project_id: ProjectId = None, material: MaterialRef = None,
                  states: Annotated[Optional[list[str]], Field(description="Failure states to use; default all of the material.")] = None,
                  strength_type: Annotated[Literal["mohr_coulomb", "generalized_hoek_brown", "power_curve", "barton_bandis"], Field(description="Criterion to calibrate.")] = "generalized_hoek_brown",
                  algorithm: Annotated[Literal["linear", "levenberg_marquardt", "simplex"], Field(description="Solver.")] = "levenberg_marquardt",
                  error_type: Annotated[Literal["Absolute", "Relative"], Field(description="Residuals minimised.")] = "Absolute",
                  data_type: Annotated[Literal["Lab Data", "Rock Mass Data"], Field(description="GHB: lab data fits sigci, mi; rock mass data fits GSI, mi with sigci, D fixed.")] = "Lab Data",
                  sigci_kpa: Annotated[Optional[float], Field(description="Rock Mass Data: sigci (kPa).")] = None,
                  disturbance: Annotated[Optional[float], Field(description="Rock Mass Data: D (0-1).")] = None,
                  phi_b_deg: Annotated[Optional[float], Field(description="Barton-Bandis: basic friction angle (deg).")] = None,
                  new_material_name: Annotated[Optional[str], Field(description="Add the result as a new material with this name.")] = None) -> dict[str, Any]:
        """Calibrate a criterion to the failure states of a material (Calibration); optionally add it as a new material."""
        return run("calibrate", project_id=project_id, material=material, states=states, strength_type=strength_type,
                   algorithm=algorithm, error_type=error_type, data_type=data_type, sigci_kpa=sigci_kpa,
                   disturbance=disturbance, phi_b_deg=phi_b_deg, new_material_name=new_material_name)

    # ------------------------------------------------------------ test simulation
    @tool("test_simulation_set", _EDIT)
    def test_simulation_set(name: Name, project_id: ProjectId = None, material: MaterialRef = None,
                            test_type: Annotated[Optional[Literal["uniaxial", "triaxial", "biaxial", "simple_shear", "general"]], Field(description="Test type.")] = None,
                            seepage: Annotated[Optional[Literal["Drained", "Undrained"]], Field(description="Seepage condition.")] = None,
                            loading: Annotated[Optional[Literal["Compression", "Tension"]], Field(description="Loading.")] = None,
                            max_strain: Annotated[Optional[float], Field(description="Maximum strain (fraction, 0-1).")] = None,
                            steps: Annotated[Optional[int], Field(description="Number of steps.")] = None,
                            cyclic: Annotated[Optional[bool], Field(description="Load and unload.")] = None,
                            cycles: Annotated[Optional[int], Field(description="Number of cycles.")] = None,
                            confining_kpa: Annotated[Optional[float], Field(description="Initial effective lateral stress (kPa).")] = None,
                            k0: Annotated[Optional[float], Field(description="Initial effective K0 (axial = lateral / K0).")] = None,
                            strain_ratio: Annotated[Optional[list[float]], Field(description="general: strain direction [EpsilonZZ, EpsilonXX, EpsilonYY, GammaZX, GammaXY, GammaZY].")] = None,
                            color: Annotated[Optional[str], Field(description="'#rrggbb'.")] = None,
                            visible: Annotated[Optional[bool], Field(description="Drawn in the plots.")] = None) -> dict[str, Any]:
        """Create or replace a test simulation of a material."""
        return run("test_simulation_set", name=name, project_id=project_id, material=material, test_type=test_type,
                   seepage=seepage, loading=loading, max_strain=max_strain, steps=steps, cyclic=cyclic, cycles=cycles,
                   confining_kpa=confining_kpa, k0=k0, strain_ratio=strain_ratio, color=color, visible=visible)

    @tool("test_simulation_delete", _DESTRUCTIVE)
    def test_simulation_delete(name: Annotated[str, Field(description="Test simulation name.")], project_id: ProjectId = None,
                               material: MaterialRef = None) -> dict[str, Any]:
        """Delete a test simulation."""
        return run("test_simulation_delete", name=name, project_id=project_id, material=material)

    @tool("test_simulation_run", _READ)
    def test_simulation_run(name: Annotated[str, Field(description="Test simulation name.")], project_id: ProjectId = None,
                            material: MaterialRef = None,
                            samples: Annotated[int, Field(description="Points of each returned curve (2-2000).")] = 21) -> dict[str, Any]:
        """Run a test simulation with the material's model: peak, final state, first yield and sampled curves (kPa)."""
        return run("test_simulation_run", name=name, project_id=project_id, material=material, samples=samples)

    # ------------------------------------------------------------ estimation
    @tool("gsi_quantified", _READ)
    def gsi_quantified(rqd: Annotated[Optional[float], Field(description="RQD (%) from core.")] = None,
                       discontinuities_per_m: Annotated[Optional[float], Field(description="lambda (1/m): RQD by Priest & Hudson.")] = None,
                       jv: Annotated[Optional[float], Field(description="Volumetric joint count Jv (joints/m3).")] = None,
                       jv_equation: Annotated[Literal["palmstrom_2005", "palmstrom_1982"], Field(description="RQD from Jv equation.")] = "palmstrom_2005",
                       jcond89: Annotated[Optional[float], Field(description="Bieniawski 1989 joint condition (0-30).")] = None,
                       jcond89_ratings: Annotated[Optional[dict[str, float]], Field(description="The five ratings 0-6: persistence, aperture, roughness, infilling, weathering.")] = None,
                       jcond76: Annotated[Optional[float], Field(description="Bieniawski 1976 joint condition (0-25).")] = None,
                       jr: Annotated[Optional[float], Field(description="Q-system Jr (with ja).")] = None,
                       ja: Annotated[Optional[float], Field(description="Q-system Ja (with jr).")] = None) -> dict[str, Any]:
        """GSI from RQD + joint condition (Hoek, Carter & Diederichs 2013): one RQD source and one joint condition."""
        return run("gsi_quantified", rqd=rqd, discontinuities_per_m=discontinuities_per_m, jv=jv, jv_equation=jv_equation,
                   jcond89=jcond89, jcond89_ratings=jcond89_ratings, jcond76=jcond76, jr=jr, ja=ja)

    @tool("gsi_chart", _READ)
    def gsi_chart(chart: Annotated[Literal["general_2000", "flysch_2000", "heterogeneous_marinos_2007"], Field(description="Digitized GSI chart.")] = "general_2000",
                  u: Annotated[Optional[float], Field(description="0 = VERY GOOD edge .. 1 = VERY POOR edge.")] = None,
                  v: Annotated[Optional[float], Field(description="0 = top structure row .. 1 = bottom row.")] = None,
                  rock_type: Annotated[Optional[str], Field(description="Instead of u, v: a type of the chart (flysch A-H, heterogeneous I-XI).")] = None,
                  language: Annotated[Literal["en", "es"], Field(description="Language of the descriptions.")] = "en") -> dict[str, Any]:
        """GSI read on a digitized chart, with the cell, rock-mass type and their descriptions; null in N/A cells."""
        return run("gsi_chart", chart=chart, u=u, v=v, rock_type=rock_type, language=language)

    @tool("table_get", _READ)
    def table_get(table: Annotated[Literal["sigci_grades", "mi_values", "gsi_2000_ranges", "disturbance_factor", "modulus_ratio",
                                           "basic_friction_angle", "soil_field_strength", "uscs_compacted_properties"],
                                   Field(description="Bibliographic table.")],
                  query: Annotated[Optional[str], Field(description="Words that must all appear in a row, e.g. 'granite' or 'tunnel'.")] = None) -> dict[str, Any]:
        """Rows of a sourced table (sigci grades, mi, GSI ranges, D, MR, phi_b, soil grades, USCS properties)."""
        return run("table_get", table=table, query=query)

    @tool("classify_uscs", _EDIT)
    def classify_uscs(fines_pct: Annotated[float, Field(description="% passing No. 200 sieve.")],
                      sand_pct: Annotated[float, Field(description="% sand (No. 4 to No. 200) of the total.")],
                      cu: Annotated[Optional[float], Field(description="Cu = D60/D10.")] = None,
                      cc: Annotated[Optional[float], Field(description="Cc = D30^2/(D10 D60).")] = None,
                      ll: Annotated[Optional[float], Field(description="Liquid limit.")] = None,
                      pi: Annotated[Optional[float], Field(description="Plasticity index.")] = None,
                      organic_ratio: Annotated[Optional[float], Field(description="LL oven dry / LL air dry.")] = None,
                      highly_organic: Annotated[bool, Field(description="Peat-like soil.")] = False,
                      create_material: Annotated[bool, Field(description="Add the Mohr-Coulomb material of the group (UFC 3-220-01N).")] = False,
                      saturated: Annotated[bool, Field(description="Use the saturated cohesion (else as compacted).")] = True,
                      project_id: ProjectId = None) -> dict[str, Any]:
        """USCS classification (ASTM D2487) with typical properties and strength; optionally create the material."""
        return run("classify_uscs", fines_pct=fines_pct, sand_pct=sand_pct, cu=cu, cc=cc, ll=ll, pi=pi,
                   organic_ratio=organic_ratio, highly_organic=highly_organic, create_material=create_material,
                   saturated=saturated, project_id=project_id)

    @tool("barton_estimate", _READ)
    def barton_estimate(jrc0: Annotated[Optional[float], Field(description="JRC at laboratory scale.")] = None,
                        jcs0_kpa: Annotated[Optional[float], Field(description="JCS at laboratory scale (kPa).")] = None,
                        block_length_m: Annotated[Optional[float], Field(description="In-situ block size (m).")] = None,
                        lab_length_m: Annotated[float, Field(description="Laboratory scale (m), 0.1 by default.")] = 0.1,
                        phi_b_deg: Annotated[Optional[float], Field(description="Basic friction angle (deg).")] = None,
                        schmidt_r: Annotated[Optional[float], Field(description="Schmidt rebound on wet weathered joint walls (r).")] = None,
                        schmidt_big_r: Annotated[Optional[float], Field(description="Schmidt rebound on dry unweathered sawn surfaces (R).")] = None) -> dict[str, Any]:
        """Barton-Bandis inputs: phi_r from Schmidt rebounds, JRC/JCS corrected to the block size."""
        return run("barton_estimate", jrc0=jrc0, jcs0_kpa=jcs0_kpa, block_length_m=block_length_m, lab_length_m=lab_length_m,
                   phi_b_deg=phi_b_deg, schmidt_r=schmidt_r, schmidt_big_r=schmidt_big_r)

    # ------------------------------------------------------------ database
    @tool("database_search", _READ)
    def database_search(query: Annotated[str, Field(description="Words (all must match), gran* wildcards, \"exact phrase\"; empty = all.")] = "",
                        page: Annotated[int, Field(description="Page (14 records each).")] = 1) -> dict[str, Any]:
        """Search the materials database (Hoek tables, CANMET 1995, MnDOT 2018 and the user's records)."""
        return run("database_search", query=query, page=page)

    @tool("database_get", _READ)
    def database_get(record_id: Annotated[int, Field(description="Record id from database_search.")]) -> dict[str, Any]:
        """One database record with its reference and test blocks."""
        return run("database_get", record_id=record_id)

    @tool("database_use", _EDIT)
    def database_use(record_id: Annotated[int, Field(description="Record id.")],
                     use: Annotated[Literal["material", "failure_state"], Field(description="'material': new GHB material (sigci, mi); 'failure_state': its specimens into a material.")] = "material",
                     project_id: ProjectId = None, material: MaterialRef = None) -> dict[str, Any]:
        """Use a database record in the project."""
        return run("database_use", record_id=record_id, use=use, project_id=project_id, material=material)

    # ------------------------------------------------------------ outputs
    @tool("render_envelope", _READ)
    def render_envelope(project_id: ProjectId = None,
                        materials: Annotated[Optional[list[str]], Field(description="Materials to draw; default the visible ones.")] = None,
                        plot: Annotated[Literal["principal", "shear"], Field(description="sigma1-sigma3 or shear-normal stress.")] = "principal",
                        unit: Annotated[Optional[str], Field(description="Axis unit: 'kPa', 'MPa'...; default the project's display unit.")] = None,
                        show_data: Annotated[bool, Field(description="Draw the failure-state points.")] = True,
                        show_mc: Annotated[bool, Field(description="Draw the equivalent / best-fit Mohr-Coulomb line.")] = False,
                        save_path: Annotated[Optional[str], Field(description="Also write the PNG here.")] = None,
                        overwrite: Overwrite = False) -> list:
        """A picture (PNG) of the strength envelopes of materials with their test points."""
        out = run("render_envelope", project_id=project_id, materials=materials, plot=plot, unit=unit, show_data=show_data,
                  show_mc=show_mc, save_path=save_path, overwrite=overwrite)
        note = {k: v for k, v in out.items() if k != "png"}
        return [Image(data=out["png"], format="png"), json.dumps(note)]

    @tool("report_generate", _EDIT)
    def report_generate(path: Annotated[str, Field(description="Where to write the .html report.")], project_id: ProjectId = None,
                        title: Annotated[Optional[str], Field(description="Report title; default the project title.")] = None,
                        sections: Annotated[Optional[list[str]], Field(description="Sections to include (catalog('report_sections')); default all non-empty.")] = None,
                        views: Annotated[Optional[list[str]], Field(description="Materials added as graph views (both envelopes + parameters + computed).")] = None,
                        unit: Annotated[Optional[str], Field(description="Stress unit of the report; default the project's display unit.")] = None,
                        overwrite: Overwrite = False) -> dict[str, Any]:
        """Write the self-contained HTML report of the project."""
        return run("report_generate", path=path, project_id=project_id, title=title, sections=sections, views=views,
                   unit=unit, overwrite=overwrite)

    # ------------------------------------------------------------ resources
    @srv.resource("ogr-data://guide", name="guide", mime_type="text/markdown", description="How to use OGR Data from an agent.")
    def guide() -> str:
        return GUIDE

    srv._ogr_tools = tuple(registered)  # for tests and server_info
    return srv
