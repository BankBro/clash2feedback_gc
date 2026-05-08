import pytest

from clash2feedback.geometry.vdw import get_vdw_radius, get_vdw_radius_table, normalize_element


def test_vdw_radius_for_carbon() -> None:
    assert get_vdw_radius("C") == pytest.approx(1.70)


def test_normalize_halogen_case() -> None:
    assert normalize_element("CL") == "Cl"
    assert normalize_element("Cl") == "Cl"
    assert normalize_element("cl") == "Cl"
    assert get_vdw_radius("cl") == pytest.approx(1.75)


def test_unknown_element_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported element"):
        get_vdw_radius("Na")


def test_radius_table_contains_phase1_elements() -> None:
    table = get_vdw_radius_table()
    for element in ["C", "N", "O", "S", "P", "F", "Cl", "Br", "I", "H"]:
        assert element in table
