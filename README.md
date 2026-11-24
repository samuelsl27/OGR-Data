# OGR Data

Material properties for the OpenGeoRock suite: strength criteria
(Hoek-Brown generalized, Mohr-Coulomb, Barton-Bandis, Power Curve and more),
USCS soil classification, estimation from official bibliography, fitting to
laboratory data, and clipboard transfer to [OGR Slip2D](https://github.com/samuelsl27/OGR-Slip2D)
and OGR FEM2D.

Spiritual heir of the earlier reference program (2004), with the design language of
OGR Slip2D. Part of the OpenGeoRock suite; see the suite registry for how the
programs fit together.

## Scripts and AI agents

Everything the program does is also a named operation of `ogr_data.api`
(no window needed), and an MCP server publishes them for AI agents:

```
pip install -e ".[mcp]"
ogr-data-mcp --workdir C:\path\to\projects     # stdio
```

```python
from ogr_data.api import Workspace, call

ws = Workspace()
call(ws, "project_new", title="Demo")
call(ws, "material_set", criterion="generalized_hoek_brown",
     parameters={"sigci": 30000, "gsi": 50, "mi": 10, "d": 0})
call(ws, "material_compute")["computed"]    # kPa: mb, s, a, sigcm, c, phi, Erm...
```

Units in and out: kPa, kN/m3, m, degrees. `catalog("criteria")` lists the
parameters of every criterion.

## Status

Early development. The SDD constitution lives in `spec/constitution/`
(methodology: [hello-sdd](https://github.com/mouredev/hello-sdd)),
including the UX guidelines (`spec/constitution/ux-guidelines.md`). Rules
for AI agents and contributors: [AGENTS.md](AGENTS.md).

## License

AGPL-3.0-or-later, see [LICENSE](LICENSE).
