"""Series data export for spreadsheets (spec 016).

Honest equivalent of the RocData / RSData "Export to Excel": a CSV with
one column pair per series, ready to open in Excel, without requiring
Excel installed. Series may have different lengths; shorter series are
padded with empty cells.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np


def write_series_csv(path: str | Path, columns: list[tuple[str, str, np.ndarray, np.ndarray]], unit: str = "MPa") -> None:
    """Write series as CSV: (x_label, y_label, x_values, y_values) columns.

    Values must already be in the display unit (the caller converts).
    """

    if not columns:
        raise ValueError("no series to export")
    table: list[list] = []
    headers: list[str] = []
    for x_label, y_label, x_values, y_values in columns:
        x = np.asarray(x_values, dtype=float).ravel()
        y = np.asarray(y_values, dtype=float).ravel()
        if x.shape != y.shape:
            raise ValueError(f"series {x_label!r}/{y_label!r}: x and y lengths differ")
        headers.append(f"{x_label} ({unit})")
        headers.append(f"{y_label} ({unit})")
        table.append((x, y))
    rows = max(pair[0].shape[0] for pair in table)
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        for i in range(rows):
            row: list = []
            for x, y in table:
                row.append(f"{x[i]:.6g}" if i < x.shape[0] else "")
                row.append(f"{y[i]:.6g}" if i < y.shape[0] else "")
            writer.writerow(row)
