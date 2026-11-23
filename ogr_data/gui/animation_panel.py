"""Animation of a simulated test (spec 013c), after RSData's Animation tab.

RSData 1.009 (help "Animation", "Stress Path Graphs"; NorSand tutorial
capture): a Material - Test selector, a sketch of the specimen being loaded
(arrow on top, dashed initial outline), a step slider and Play / Pause; the
Stress Path Graphs mark the current point of the test and the q-p graph
shows the current yield (bounding) surface.

Here the specimen sketch exaggerates the strains so the largest one of the
test reads as 30 % of the specimen size; simple shear is drawn as a sheared
parallelogram.
"""

from __future__ import annotations

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.patches import FancyArrow, Polygon, Rectangle
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QComboBox, QGroupBox, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout

from ..core import simulation as sm
from .i18n import tr


class SpecimenSketch(FigureCanvasQTAgg):
    def __init__(self) -> None:
        self.figure = Figure(figsize=(1.8, 1.8), tight_layout=True)
        super().__init__(self.figure)
        self.axes = self.figure.add_subplot(111)
        self.setMinimumSize(150, 150)

    def draw_state(self, result: sm.SimulationResult | None, step: int, color: str) -> None:
        ax = self.axes
        ax.clear()
        ax.set_xlim(-1.6, 1.6)
        ax.set_ylim(-0.4, 2.9)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.add_patch(Rectangle((-1.2, -0.25), 2.4, 0.2, color="#555555"))
        if result is None:
            self.draw_idle()
            return
        strains = result.strain
        peak = float(np.max(np.abs(strains))) or 1.0
        amp = 0.3 / peak
        ea, ex, gamma = strains[step, 0], strains[step, 1], strains[step, 3]
        height = 2.0 * (1.0 - amp * ea)
        half = 0.6 * (1.0 - amp * ex)
        shift = amp * gamma * height / 2.0
        ax.add_patch(Rectangle((-0.6, 0.0), 1.2, 2.0, fill=False, linestyle="--", edgecolor="#777777"))
        corners = [(-half, 0.0), (half, 0.0), (half + shift, height), (-half + shift, height)]
        ax.add_patch(Polygon(corners, closed=True, facecolor=color, edgecolor="#222222", alpha=0.85))
        down = result.test.loading == "Compression"
        top = height + 0.05
        if result.test.test_type == "simple_shear":
            sign = 1.0 if down else -1.0
            ax.add_patch(FancyArrow(shift - 0.4 * sign, top + 0.25, 0.8 * sign, 0.0, width=0.03, head_width=0.15, color="#111111"))
        else:
            start, length = (top + 0.55, -0.45) if down else (top + 0.05, 0.45)
            ax.add_patch(FancyArrow(shift, start, 0.0, length, width=0.03, head_width=0.15, length_includes_head=True, color="#111111"))
        self.draw_idle()


class AnimationPanel(QGroupBox):
    """Animation controls; `window` provides animation_targets() and show_animation_step()."""

    def __init__(self, window) -> None:
        super().__init__(tr("Animation"))
        self.window_ = window
        self.material = QComboBox()
        self.material.currentIndexChanged.connect(lambda _i: self.set_step(0))
        self.play = QPushButton(tr("▶ Play"))
        self.pause = QPushButton(tr("⏸ Pause"))
        self.play.clicked.connect(self.start)
        self.pause.clicked.connect(self.stop)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.valueChanged.connect(self.set_step)
        self.step_label = QLabel("0")
        self.sketch = SpecimenSketch()
        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self._tick)
        controls = QVBoxLayout()
        top = QHBoxLayout()
        top.addWidget(QLabel("Material:"))  # i18n: ignore (same in Spanish)
        top.addWidget(self.material, stretch=1)
        controls.addLayout(top)
        row = QHBoxLayout()
        row.addWidget(self.step_label)
        row.addWidget(self.slider, stretch=1)
        controls.addLayout(row)
        buttons = QHBoxLayout()
        buttons.addWidget(self.play)
        buttons.addWidget(self.pause)
        buttons.addStretch(1)
        controls.addLayout(buttons)
        layout = QHBoxLayout(self)
        layout.addLayout(controls, stretch=1)
        layout.addWidget(self.sketch)
        self._targets: list = []
        self.refresh_items()

    # ---------------------------------------------------------------- items

    def refresh_items(self) -> None:
        """Rebuild the Material - Test list (visible simulated tests)."""

        current = self.material.currentText()
        self._targets = list(self.window_.animation_targets())
        self.material.blockSignals(True)
        self.material.clear()
        for label, _result, _color in self._targets:
            self.material.addItem(label)
        index = self.material.findText(current)
        self.material.setCurrentIndex(index if index >= 0 else (0 if self._targets else -1))
        self.material.blockSignals(False)
        enabled = bool(self._targets)
        for w in (self.play, self.pause, self.slider):
            w.setEnabled(enabled)
        if not enabled:
            self.stop()
        self.set_step(min(self.slider.value(), self._steps() - 1) if enabled else 0)

    def _current(self):
        i = self.material.currentIndex()
        return self._targets[i] if 0 <= i < len(self._targets) else None

    def _steps(self) -> int:
        target = self._current()
        return len(target[1].q) if target else 1

    # ------------------------------------------------------------- stepping

    def set_step(self, step: int) -> None:
        target = self._current()
        n = self._steps()
        self.slider.blockSignals(True)
        self.slider.setRange(0, max(0, n - 1))
        self.slider.setValue(max(0, min(step, n - 1)))
        self.slider.blockSignals(False)
        step = self.slider.value()
        self.step_label.setText(f"{step}")
        if target is None:
            self.sketch.draw_state(None, 0, "#888888")
            self.window_.show_animation_step(None, 0)
            return
        _label, result, color = target
        self.sketch.draw_state(result, step, color)
        self.window_.show_animation_step(result, step)

    def start(self) -> None:
        if self._targets:
            if self.slider.value() >= self._steps() - 1:
                self.set_step(0)
            self.timer.start()

    def stop(self) -> None:
        self.timer.stop()

    def _tick(self) -> None:
        step = self.slider.value() + max(1, self._steps() // 150)
        if step >= self._steps() - 1:
            self.set_step(self._steps() - 1)
            self.stop()
        else:
            self.set_step(step)
