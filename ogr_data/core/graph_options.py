"""Serializable per-plot display options (spec 016).

matplotlib does the rendering; this module is the data layer the graph
editor edits and the project file persists. Style values left empty
(color "" / linewidth 0 / linestyle "") mean "theme default".
"""

from __future__ import annotations

from dataclasses import dataclass, field

SERIES_KEYS = ("envelope", "mc", "tangent", "mogi")

DEFAULT_LINEWIDTHS = {
    "envelope": 1.8,
    "mc": 1.2,
    "tangent": 1.3,
    "mogi": 1.2,
}

DEFAULT_LINESTYLES = {
    "envelope": "-",
    "mc": "--",
    "tangent": "-.",
    "mogi": "-",
}

LINE_STYLES = ("", "-", "--", "-.", ":")


@dataclass
class SeriesStyle:
    visible: bool = True
    color: str = ""  # "" = theme default
    linewidth: float = 0.0  # 0 = default per series
    linestyle: str = ""  # "" = default per series

    def to_dict(self) -> dict:
        return {
            "visible": self.visible,
            "color": self.color,
            "linewidth": self.linewidth,
            "linestyle": self.linestyle,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SeriesStyle":
        return cls(
            visible=bool(data.get("visible", True)),
            color=str(data.get("color", "")),
            linewidth=float(data.get("linewidth", 0.0)),
            linestyle=str(data.get("linestyle", "")) if data.get("linestyle", "") in LINE_STYLES else "",
        )


@dataclass
class PlotOptions:
    title: str = ""  # "" = default plot title
    grid: bool = True
    square_axis: bool = False
    labels_inside: bool = False  # axis label position Inside/Outside
    x_range: tuple[float, float] | None = None  # None = automatic
    y_range: tuple[float, float] | None = None
    styles: dict[str, SeriesStyle] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for key in SERIES_KEYS:
            self.styles.setdefault(key, SeriesStyle())

    def style(self, key: str) -> SeriesStyle:
        return self.styles[key]

    def linewidth(self, key: str) -> float:
        style = self.styles[key]
        return style.linewidth if style.linewidth > 0.0 else DEFAULT_LINEWIDTHS[key]

    def linestyle(self, key: str) -> str:
        style = self.styles[key]
        return style.linestyle if style.linestyle else DEFAULT_LINESTYLES[key]

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "grid": self.grid,
            "square_axis": self.square_axis,
            "labels_inside": self.labels_inside,
            "x_range": list(self.x_range) if self.x_range else None,
            "y_range": list(self.y_range) if self.y_range else None,
            "styles": {key: self.styles[key].to_dict() for key in SERIES_KEYS},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlotOptions":
        def _range(value):
            if not value:
                return None
            pair = (float(value[0]), float(value[1]))
            return pair if pair[0] < pair[1] else None

        styles = {key: SeriesStyle.from_dict(data.get("styles", {}).get(key, {})) for key in SERIES_KEYS}
        return cls(
            title=str(data.get("title", "")),
            grid=bool(data.get("grid", True)),
            square_axis=bool(data.get("square_axis", False)),
            labels_inside=bool(data.get("labels_inside", False)),
            x_range=_range(data.get("x_range")),
            y_range=_range(data.get("y_range")),
            styles=styles,
        )
