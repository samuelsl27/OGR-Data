# SPDX-License-Identifier: AGPL-3.0-or-later
"""Spec 029: a readable sidebar that follows its splitter.

UX review of 2026-11-28 (no external reference: these are layout
invariants measured on the real widgets).

- RF-1: every number of the sidebar is shown whole; the arrows never cover
  a character (EN/ES, both themes, several criteria, any allowed width).
- RF-2: the spin-box arrows are drawn by each theme's sheet: visible, at
  least 18 px wide, beside the text and not over it.
- RF-3: dragging the splitter gives the sidebar that width (no fixed cap)
  and the fields grow with it.
- RF-4: when a row does not fit, the label goes above its field instead of
  being cut; the sidebar never shows a horizontal scroll bar.
- RF-5: the sidebar cannot shrink below the width its content needs, nor
  collapse; it opens wide enough for everything.

Run under both the test style (Fusion) and, where present, the style the
application has on Windows 11.
"""

from __future__ import annotations

from contextlib import contextmanager

CRITERIA = ("mohr_coulomb", "generalized_hoek_brown", "softening_hardening")


def _app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _styles() -> list[str]:
    from PySide6.QtWidgets import QStyleFactory

    keys = {k.lower(): k for k in QStyleFactory.keys()}
    return [keys[k] for k in ("fusion", "windows11") if k in keys]


@contextmanager
def _window(language: str, style: str):
    """A main window in ``language`` under ``style``; everything restored after."""

    from ogr_data.gui import i18n
    from ogr_data.gui.main_window import MainWindow

    app = _app()
    old_style = app.style().name()
    old_language = i18n.current_language()
    app.setStyle(style)
    i18n.set_language(language)
    w = MainWindow()
    try:
        w.resize(1366, 768)
        w.show()
        app.processEvents()
        yield w
    finally:
        w._set_theme("light")
        w.ask_unsaved = lambda: "discard"
        w.close()
        w.deleteLater()
        app.processEvents()
        i18n.set_language(old_language)
        app.setStyle(old_style)


def _sidebar(w):
    from PySide6.QtWidgets import QScrollArea

    return w.findChild(QScrollArea, "sidebar")


def _set_width(w, width: int) -> None:
    splitter = w.centralWidget()
    total = sum(splitter.sizes())
    splitter.setSizes([width, total - width])
    _app().processEvents()


def _visible(sidebar, cls) -> list:
    inner = sidebar.widget()
    return [x for x in inner.findChildren(cls) if x.isVisibleTo(inner)]


def _spin_buttons(spin):
    from PySide6.QtWidgets import QStyle, QStyleOptionSpinBox

    option = QStyleOptionSpinBox()
    spin.initStyleOption(option)
    style = spin.style()
    up = style.subControlRect(QStyle.ComplexControl.CC_SpinBox, option, QStyle.SubControl.SC_SpinBoxUp, spin)
    down = style.subControlRect(QStyle.ComplexControl.CC_SpinBox, option, QStyle.SubControl.SC_SpinBoxDown, spin)
    return up, down


def _check_numbers(w, where: str) -> None:
    """RF-1: the whole text fits in the edit field, and the field ends before the arrows."""

    from ogr_data.gui.number_spin import NumberSpinBox

    for spin in _visible(_sidebar(w), NumberSpinBox):
        edit = spin.lineEdit()
        text = edit.text()
        needed = edit.fontMetrics().horizontalAdvance(text) + 4  # QLineEdit's own side margins
        assert edit.width() >= needed, f"{where}: {text!r} needs {needed} px, has {edit.width()}"
        up, down = _spin_buttons(spin)
        for button in (up, down):
            if button.isValid():
                # the button's left border may share the edit's last pixel: that
                # pixel is the edit's own margin (the +4 above), never text
                assert edit.geometry().right() <= button.left(), f"{where}: arrows over {text!r}"


def test_numbers_are_whole_and_arrows_beside_them() -> None:
    """RF-1 and RF-3: at the opening width, the minimum and 600 px."""

    for style in _styles():
        for language in ("en", "es"):
            with _window(language, style) as w:
                for theme in ("light", "dark"):
                    w._set_theme(theme)
                    for criterion in CRITERIA:
                        w._criterion_combo.setCurrentIndex(w._criterion_combo.findData(criterion))
                        _app().processEvents()
                        tag = f"{style}/{language}/{theme}/{criterion}"
                        _set_width(w, 380)
                        _check_numbers(w, f"{tag}/380")
                        _set_width(w, 50)  # the splitter stops at the minimum (RF-5)
                        _check_numbers(w, f"{tag}/min")
                        _set_width(w, 600)
                        _check_numbers(w, f"{tag}/600")


def test_arrows_are_drawn_by_the_theme() -> None:
    """RF-2: buttons at least 18 px wide with a visible arrow, in both themes."""

    from ogr_data.gui.number_spin import NumberSpinBox

    for style in _styles():
        with _window("en", style) as w:
            for theme in ("light", "dark"):
                w._set_theme(theme)
                _app().processEvents()
                spin = w._sig3max
                up, down = _spin_buttons(spin)
                image = spin.grab().toImage()
                for name, rect in (("up", up), ("down", down)):
                    assert rect.width() >= 18, f"{style}/{theme}: {name} button {rect.width()} px"
                    # the arrow: some pixel of the button contrasts with its corner
                    corner = image.pixelColor(rect.right() - 1, rect.center().y()).lightness()
                    contrast = max(
                        abs(image.pixelColor(x, y).lightness() - corner)
                        for x in range(rect.left() + 3, rect.right() - 2)
                        for y in range(rect.top() + 1, rect.bottom())
                    )
                    assert contrast > 80, f"{style}/{theme}: {name} arrow not visible ({contrast})"
                assert isinstance(spin, NumberSpinBox)


def test_sidebar_follows_the_splitter() -> None:
    """RF-3: no fixed cap; 150 px more panel than its one-line width makes the fields 150 px wider."""

    for style in _styles():
        with _window("en", style) as w:
            w.resize(2600, 900)  # room for the graphs whatever the fonts measure
            _app().processEvents()
            scroll = _sidebar(w)
            one_line = scroll.sizeHint().width()  # below it the rows wrap (RF-4)
            _set_width(w, one_line)
            narrow = w._sig3max.width()
            _set_width(w, one_line + 150)
            assert scroll.width() == one_line + 150, (style, one_line, w.centralWidget().sizes())
            assert w._sig3max.width() >= narrow + 140, (style, narrow, w._sig3max.width())


def test_narrow_sidebar_wraps_rows_instead_of_cutting() -> None:
    """RF-4 and RF-5: at the minimum nothing is cut and there is no horizontal bar."""

    from PySide6.QtWidgets import QComboBox, QLabel, QPushButton

    for style in _styles():
        for language in ("en", "es"):
            with _window(language, style) as w:
                scroll = _sidebar(w)
                for criterion in CRITERIA:
                    w._criterion_combo.setCurrentIndex(w._criterion_combo.findData(criterion))
                    _app().processEvents()
                    _set_width(w, 50)
                    tag = f"{style}/{language}/{criterion}"
                    assert scroll.width() >= 200, f"{tag}: collapsed to {scroll.width()}"
                    assert not w.centralWidget().isCollapsible(0)
                    assert not scroll.horizontalScrollBar().isVisible(), tag
                    inner = scroll.widget()
                    assert inner.width() <= scroll.viewport().width(), f"{tag}: content wider than the panel"
                    for cls in (QLabel, QPushButton, QComboBox):
                        for widget in _visible(scroll, cls):
                            if cls is QLabel and (widget.wordWrap() or not widget.text()):
                                continue
                            # 1 px: QFormLayout's integer rounding when it decides
                            # not to wrap a row (seen on a combo: 107 for 108)
                            assert widget.width() >= widget.minimumSizeHint().width() - 1, (
                                f"{tag}: {type(widget).__name__} {getattr(widget, 'text', lambda: '')()!r} "
                                f"{widget.width()} < {widget.minimumSizeHint().width()}"
                            )
                # the long Spanish labels go above their field rather than being cut
                if language == "es":
                    w._criterion_combo.setCurrentIndex(w._criterion_combo.findData("mohr_coulomb"))
                    _app().processEvents()
                    _set_width(w, 50)
                    spin = w._widgets["peak_friction"]
                    label = next(lab for lab in _visible(scroll, QLabel) if lab.buddy() is spin)
                    assert label.width() >= label.sizeHint().width(), label.text()
                    y_label = label.mapTo(scroll.widget(), label.rect().center()).y()
                    y_spin = spin.mapTo(scroll.widget(), spin.rect().center()).y()
                    assert y_label < y_spin - spin.height() // 2, "label not above its field"


def test_sidebar_opens_wide_enough() -> None:
    """RF-5: at 1366x768 the sidebar opens as wide as its rows need, up to 40 % of the splitter.

    Within that cap every row is on one line; past it (fonts wider than the
    usual ones) the rows wrap, which RF-4 covers.
    """

    from PySide6.QtWidgets import QLabel

    from ogr_data.gui.number_spin import NumberSpinBox

    for style in _styles():
        for language in ("en", "es"):
            with _window(language, style) as w:
                scroll = _sidebar(w)
                wanted = scroll.sizeHint().width()
                splitter = w.centralWidget()
                total = sum(splitter.sizes())
                # the graphs keep at least their own minimum (only binding when
                # the fonts are wider than usual, as offscreen without a font folder)
                cap = min(int(total * 0.4), total - splitter.widget(1).minimumSizeHint().width())
                expected = max(scroll.minimumSizeHint().width(), min(wanted, cap))
                assert scroll.width() >= expected - 1, (scroll.width(), wanted, cap)
                if scroll.width() < wanted:
                    continue
                # one line per row: each label at the height of its field
                for spin in _visible(scroll, NumberSpinBox):
                    label = next(
                        (lab for lab in _visible(scroll, QLabel) if lab.buddy() is spin), None
                    )
                    if label is None:
                        continue
                    y_label = label.mapTo(scroll.widget(), label.rect().center()).y()
                    y_spin = spin.mapTo(scroll.widget(), spin.rect().center()).y()
                    assert abs(y_label - y_spin) < spin.height(), f"{style}/{language}: {label.text()!r} wrapped"
