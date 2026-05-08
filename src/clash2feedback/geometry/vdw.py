from __future__ import annotations


VDW_RADII: dict[str, float] = {
    "H": 1.20,
    "C": 1.70,
    "N": 1.55,
    "O": 1.52,
    "F": 1.47,
    "P": 1.80,
    "S": 1.80,
    "Cl": 1.75,
    "Br": 1.85,
    "I": 1.98,
}


def normalize_element(element: str) -> str:
    value = str(element or "").strip()
    if not value:
        raise ValueError("Element is empty.")
    if len(value) == 1:
        normalized = value.upper()
    else:
        normalized = value[0].upper() + value[1:].lower()
    if normalized not in VDW_RADII:
        raise ValueError(f"Unsupported element for vdW radius: {element!r}")
    return normalized


def get_vdw_radius(element: str) -> float:
    return float(VDW_RADII[normalize_element(element)])


def get_vdw_radius_table() -> dict[str, float]:
    return dict(VDW_RADII)
