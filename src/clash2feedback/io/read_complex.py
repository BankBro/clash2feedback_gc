from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from clash2feedback.data.schema import RawComplex


PROTEIN_FILENAMES = ("protein.pdb", "protein.cif", "protein.mmcif")
LIGAND_FILENAMES = ("ligand.sdf",)


def read_metadata(metadata_path: Path) -> dict[str, Any]:
    if not metadata_path.exists():
        return {}
    with metadata_path.open("r", encoding="utf-8") as f:
        metadata = json.load(f)
    if not isinstance(metadata, dict):
        raise ValueError(f"metadata.json must be a JSON object: {metadata_path}")
    return metadata


def find_raw_complexes(raw_root: str | Path) -> list[RawComplex]:
    root = Path(raw_root)
    if not root.exists():
        raise FileNotFoundError(f"Raw root does not exist: {root}")

    complexes: list[RawComplex] = []
    for complex_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        raw = read_raw_complex_dir(complex_dir)
        if raw is not None:
            complexes.append(raw)
    return complexes


def read_raw_complex_dir(complex_dir: str | Path) -> RawComplex | None:
    directory = Path(complex_dir)
    protein_path = _first_existing(directory, PROTEIN_FILENAMES)
    ligand_path = _first_existing(directory, LIGAND_FILENAMES)
    if protein_path is None and ligand_path is None:
        return None
    if protein_path is None:
        raise FileNotFoundError(f"Missing protein file in {directory}")
    if ligand_path is None:
        raise FileNotFoundError(f"Missing ligand.sdf in {directory}")

    metadata = read_metadata(directory / "metadata.json")
    complex_id = str(metadata.get("complex_id") or directory.name)
    metadata.setdefault("complex_id", complex_id)
    metadata.setdefault("source", metadata.get("dataset_name") or "unknown")
    metadata.setdefault("split_group", complex_id)
    return RawComplex(
        complex_id=complex_id,
        protein_path=protein_path,
        ligand_path=ligand_path,
        metadata=metadata,
    )


def _first_existing(directory: Path, filenames: tuple[str, ...]) -> Path | None:
    for filename in filenames:
        path = directory / filename
        if path.exists():
            return path
    return None
