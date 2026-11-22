"""Spec 004: USCS classifier (NRCS figure 3-17 criteria)."""

from __future__ import annotations

from ogr_data.core import uscs


def test_a_line_matches_nrcs_text():
    # NRCS NEH 650 ch.4: A-line PI = 0.73 (LL - 20); U-line PI = 0.9 (LL - 8)
    assert uscs.a_line_pi(50.0) == 0.73 * 30.0
    assert uscs.u_line_pi(50.0) == 0.9 * 42.0


def test_clean_gravels_and_sands():
    # GW: <5% fines, gravel dominant, Cu>4 and 1<Cc<3
    r = uscs.classify(uscs.UsCSInput(fines_pct=2.0, sand_pct=30.0, cu=8.0, cc=2.0))
    assert r.symbol == "GW"
    # GP: fails gradation
    r = uscs.classify(uscs.UsCSInput(fines_pct=2.0, sand_pct=30.0, cu=2.0, cc=2.0))
    assert r.symbol == "GP"
    # SW: sand dominant (sand = 80% of total, fines 3%)
    r = uscs.classify(uscs.UsCSInput(fines_pct=3.0, sand_pct=80.0, cu=10.0, cc=1.5))
    assert r.symbol == "SW"
    # SP
    r = uscs.classify(uscs.UsCSInput(fines_pct=3.0, sand_pct=80.0, cu=2.0, cc=1.5))
    assert r.symbol == "SP"


def test_coarse_with_fines():
    # GM: >12% fines, below A-line and PI<4 (LL=25, PI=3: A=3.65 -> below)
    r = uscs.classify(uscs.UsCSInput(fines_pct=15.0, sand_pct=30.0, ll=25.0, pi=3.0))
    assert r.symbol == "GM"
    # GC: above A-line (LL=30, PI=10: A=7.3)
    r = uscs.classify(uscs.UsCSInput(fines_pct=20.0, sand_pct=30.0, ll=30.0, pi=10.0))
    assert r.symbol == "GC"
    # SM / SC
    r = uscs.classify(uscs.UsCSInput(fines_pct=18.0, sand_pct=70.0, ll=25.0, pi=3.0))
    assert r.symbol == "SM"
    r = uscs.classify(uscs.UsCSInput(fines_pct=18.0, sand_pct=70.0, ll=30.0, pi=10.0))
    assert r.symbol == "SC"


def test_dual_symbols_5_to_12_percent_fines():
    # GW-GM: 8% fines, well graded, fines below A-line PI<4
    r = uscs.classify(uscs.UsCSInput(fines_pct=8.0, sand_pct=30.0, cu=8.0, cc=2.0, ll=25.0, pi=3.0))
    assert r.symbol == "GW-GM"
    # SP-SC
    r = uscs.classify(uscs.UsCSInput(fines_pct=10.0, sand_pct=80.0, cu=2.0, cc=1.5, ll=30.0, pi=10.0))
    assert r.symbol == "SP-SC"
    # borderline PI 4-7 with 5-12% fines -> two dual symbols
    r = uscs.classify(uscs.UsCSInput(fines_pct=8.0, sand_pct=30.0, cu=8.0, cc=2.0, ll=28.0, pi=6.0))
    assert r.symbol == "GW-GM/GW-GC"
    assert r.notes


def test_fine_grained_soils():
    # ML: LL<50, below A-line (LL=30, PI=5: A=7.3)
    assert uscs.classify(uscs.UsCSInput(fines_pct=70.0, sand_pct=20.0, ll=30.0, pi=5.0)).symbol == "ML"
    # CL: LL<50, above A-line, PI>7
    assert uscs.classify(uscs.UsCSInput(fines_pct=70.0, sand_pct=20.0, ll=35.0, pi=15.0)).symbol == "CL"
    # CL-ML: borderline PI 4-7 above A-line (LL=28, PI=6: A=5.84)
    assert uscs.classify(uscs.UsCSInput(fines_pct=70.0, sand_pct=20.0, ll=28.0, pi=6.0)).symbol == "CL-ML"
    # MH / CH
    assert uscs.classify(uscs.UsCSInput(fines_pct=70.0, sand_pct=20.0, ll=70.0, pi=20.0)).symbol == "MH"
    assert uscs.classify(uscs.UsCSInput(fines_pct=70.0, sand_pct=20.0, ll=60.0, pi=30.0)).symbol == "CH"


def test_organic_soils():
    # OL: LL<50, below A-line, PI<4 and ratio < 0.7
    r = uscs.classify(uscs.UsCSInput(fines_pct=70.0, sand_pct=20.0, ll=30.0, pi=3.0, organic_ratio=0.6))
    assert r.symbol == "OL"
    # OH: LL>=50, below A-line, ratio < 0.7
    r = uscs.classify(uscs.UsCSInput(fines_pct=70.0, sand_pct=20.0, ll=70.0, pi=3.0, organic_ratio=0.6))
    assert r.symbol == "OH"
    # PT: highly organic
    r = uscs.classify(uscs.UsCSInput(fines_pct=70.0, sand_pct=20.0, ll=80.0, pi=30.0, highly_organic=True))
    assert r.symbol == "PT"


def test_properties_card_covers_all_classes():
    classes = ["GW", "GP", "GM", "GC", "SW", "SP", "SM", "SC", "ML", "CL", "OL", "MH", "CH", "OH", "PT"]
    for symbol in classes:
        card = uscs.uscs_properties(symbol)
        assert card["typical_names"]
        assert card["shear_strength"]
        assert card["permeability"]
    # dual symbols resolve to the primary class card
    card = uscs.uscs_properties("GW-GM")
    assert "gravels" in card["typical_names"]


def test_validation():
    try:
        uscs.UsCSInput(fines_pct=60.0, sand_pct=50.0)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for fines + sand > 100")
    # clean coarse soil without Cu/Cc must ask for them
    try:
        uscs.classify(uscs.UsCSInput(fines_pct=2.0, sand_pct=30.0))
    except ValueError as exc:
        assert "Cu" in str(exc)
    else:
        raise AssertionError("expected ValueError for missing Cu/Cc")


def test_classifier_dialog_offscreen():
    from PySide6.QtWidgets import QApplication

    from ogr_data.gui.soil_classifier import SoilClassifierDialog

    app = QApplication.instance() or QApplication([])
    dlg = SoilClassifierDialog()
    # default inputs: 30% fines (5-12% band needs LL/PI, which are 0 -> None)
    # -> classification incomplete
    assert dlg._symbol.text() == "—"
    dlg._fields["fines_pct"].setValue(2.0)
    dlg._fields["sand_pct"].setValue(30.0)
    dlg._fields["cu"].setValue(8.0)
    dlg._fields["cc"].setValue(2.0)
    assert dlg._symbol.text() == "GW"
    # fine-grained path
    dlg._fields["fines_pct"].setValue(70.0)
    dlg._fields["ll"].setValue(35.0)
    dlg._fields["pi"].setValue(15.0)
    assert dlg._symbol.text() == "CL"
    dlg.reject()
