from __future__ import annotations

import json
import pickle
import platform
from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from clash2feedback.chemistry.rgroup import build_ligand_masks, decompose_rgroups
from clash2feedback.chemistry.sanitize import check_ligand_validity
from clash2feedback.chemistry.scaffold import get_murcko_scaffold_atom_indices, validate_scaffold
from clash2feedback.data.schema import RawComplex
from clash2feedback.geometry.basic_clash_screen import basic_original_clash_screen
from clash2feedback.io.read_complex import find_raw_complexes
from clash2feedback.io.read_ligand import mol_to_ligand_data, read_ligand_sdf
from clash2feedback.io.read_protein import read_protein_structure
from clash2feedback.pocket.extract_pocket import extract_pocket_atoms
from clash2feedback.utils.files import ensure_dir, sha256_file


class SampleBuildError(RuntimeError):
    def __init__(self, reason: str, message: str | None = None, *, stage: str = "build") -> None:
        super().__init__(message or reason)
        self.reason = reason
        self.stage = stage


def build_processed_sample(raw_complex: RawComplex, config: dict[str, Any]) -> dict[str, Any]:
    ligand_cfg = config.get("ligand", {})
    protein_cfg = config.get("protein", {})
    pocket_cfg = config.get("pocket", {})
    scaffold_cfg = config.get("scaffold", {})
    rgroup_cfg = config.get("rgroup", {})
    clash_cfg = config.get("basic_clash_screen", {})

    covalent_flag = raw_complex.metadata.get("is_covalent_ligand") or raw_complex.metadata.get("covalent")
    if ligand_cfg.get("reject_covalent", True) and covalent_flag:
        raise SampleBuildError("ligand_covalent", stage="metadata")

    try:
        mol = read_ligand_sdf(
            raw_complex.ligand_path,
            sanitize=False,
            remove_hs=bool(ligand_cfg.get("remove_hs", False)),
        )
    except Exception as exc:
        raise SampleBuildError("ligand_read_failed", str(exc), stage="ligand") from exc

    validity = check_ligand_validity(
        mol,
        min_heavy_atoms=int(ligand_cfg.get("min_heavy_atoms", 15)),
        max_heavy_atoms=int(ligand_cfg.get("max_heavy_atoms", 60)),
        allowed_elements=set(ligand_cfg.get("allowed_elements", [])) or None,
        require_single_fragment=bool(ligand_cfg.get("require_single_fragment", True)),
        require_3d=bool(ligand_cfg.get("require_3d", True)),
        reject_metals=bool(ligand_cfg.get("reject_metals", True)),
        reject_macrocycles=bool(ligand_cfg.get("reject_macrocycles", True)),
        macrocycle_min_ring_size=int(ligand_cfg.get("macrocycle_min_ring_size", 12)),
    )
    if not validity["ok"]:
        raise SampleBuildError(validity["fatal_errors"][0], stage="ligand")

    _sanitize_mol_in_place(mol)
    ligand = mol_to_ligand_data(mol)
    if not np.isfinite(ligand.coords).all():
        raise SampleBuildError("ligand_coords_not_finite", stage="ligand")

    try:
        protein = read_protein_structure(
            raw_complex.protein_path,
            keep_waters=bool(protein_cfg.get("keep_waters", False)),
            keep_hetero=bool(protein_cfg.get("keep_hetero", False)),
            prefer_mmcif=bool(protein_cfg.get("prefer_mmcif", True)),
        )
    except Exception as exc:
        raise SampleBuildError("protein_read_failed", str(exc), stage="protein") from exc

    pocket = extract_pocket_atoms(
        protein,
        ligand,
        cutoff_angstrom=float(pocket_cfg.get("cutoff_angstrom", 8.0)),
        by_residue=bool(pocket_cfg.get("by_residue", True)),
        ligand_heavy_only=bool(pocket_cfg.get("ligand_heavy_only", True)),
    )
    if pocket.num_pocket_atoms == 0:
        raise SampleBuildError("pocket_empty", stage="pocket")

    clash_result = basic_original_clash_screen(
        protein,
        ligand,
        pocket,
        min_distance_threshold=float(clash_cfg.get("min_distance_threshold_angstrom", 1.2)),
        max_obvious_clash_pairs=int(clash_cfg.get("max_obvious_clash_pairs", 0)),
    )
    min_allowed_pocket = int(pocket_cfg.get("min_atoms_8A", 50))
    max_allowed_pocket = int(pocket_cfg.get("max_atoms_8A", 3000))
    max_min_distance = float(pocket_cfg.get("max_min_ligand_protein_distance_angstrom", 6.0))
    if pocket.num_atoms_8A < min_allowed_pocket:
        raise SampleBuildError("pocket_too_small", stage="pocket")
    if pocket.num_atoms_8A > max_allowed_pocket:
        raise SampleBuildError("pocket_too_large", stage="pocket")
    if float(clash_result["min_ligand_protein_distance"]) > max_min_distance:
        raise SampleBuildError("protein_ligand_coordinate_mismatch", stage="pocket")
    if bool(clash_cfg.get("enabled", True)) and not bool(clash_result["basic_clash_screen_pass"]):
        raise SampleBuildError("basic_clash_screen_failed", stage="geometry")

    scaffold = get_murcko_scaffold_atom_indices(mol)
    scaffold_check = validate_scaffold(
        mol,
        scaffold,
        min_scaffold_atoms=int(scaffold_cfg.get("min_scaffold_atoms", 3)),
    )
    if not scaffold_check["ok"]:
        raise SampleBuildError(scaffold_check["fatal_errors"][0], stage="scaffold")

    rgroups = decompose_rgroups(
        mol,
        scaffold,
        min_heavy_atoms=int(rgroup_cfg.get("min_heavy_atoms", 2)),
        max_heavy_atoms=int(rgroup_cfg.get("max_heavy_atoms", 15)),
        single_anchor_only=bool(rgroup_cfg.get("single_anchor_only", True)),
    )
    num_valid_rgroups = sum(1 for rgroup in rgroups if rgroup.is_valid_for_phase0)
    if num_valid_rgroups < int(rgroup_cfg.get("min_valid_rgroups_per_complex", 2)):
        raise SampleBuildError("not_enough_valid_rgroups", stage="rgroup")

    masks = build_ligand_masks(mol, scaffold, rgroups)
    pocket_atom_mask = np.zeros(protein.num_atoms, dtype=bool)
    pocket_atom_mask[pocket.protein_atom_indices] = True
    masks["pocket_atom_mask"] = pocket_atom_mask

    metadata = _normalized_metadata(raw_complex)
    sanity = {
        "valid_ligand": bool(validity["ok"]),
        "has_3d_coords": bool(ligand.has_3d_conformer),
        "single_ligand_fragment": ligand.num_fragments == 1,
        "protein_has_coords": protein.num_atoms > 0,
        "pocket_nonempty": pocket.num_pocket_atoms > 0,
        "scaffold_success": bool(scaffold.success),
        "num_valid_rgroups": int(num_valid_rgroups),
        "num_single_anchor_rgroups": int(sum(1 for rgroup in rgroups if rgroup.is_single_anchor)),
        "ligand_heavy_atoms_in_range": bool(validity["heavy_atoms_in_range"]),
        "pocket_atoms_in_range": min_allowed_pocket <= pocket.num_atoms_8A <= max_allowed_pocket,
        "all_coords_finite": _all_coords_finite(protein.coords, ligand.coords, pocket.coords),
        "min_ligand_protein_distance": float(clash_result["min_ligand_protein_distance"]),
        "num_obvious_clash_pairs": int(clash_result["num_obvious_clash_pairs"]),
        "num_pairs_below_1_0": int(clash_result["num_pairs_below_1_0"]),
        "num_pairs_below_1_2": int(clash_result["num_pairs_below_1_2"]),
        "num_pairs_below_1_5": int(clash_result["num_pairs_below_1_5"]),
        "basic_clash_screen_pass": bool(clash_result["basic_clash_screen_pass"]),
        "fatal_errors": [],
        "warnings": list(validity.get("warnings", []))
        + list(scaffold_check.get("warnings", []))
        + list(protein.warnings or []),
    }

    return {
        "schema_version": str(config.get("schema_version", "0.1")),
        "sample_id": raw_complex.complex_id,
        "complex_id": raw_complex.complex_id,
        "source": str(raw_complex.metadata.get("source") or raw_complex.metadata.get("dataset_name") or "unknown"),
        "created_at": datetime.now(UTC).isoformat(),
        "paths": {
            "raw_protein_path": str(raw_complex.protein_path),
            "raw_ligand_path": str(raw_complex.ligand_path),
            "processed_path": "",
            "protein_sha256": sha256_file(raw_complex.protein_path),
            "ligand_sha256": sha256_file(raw_complex.ligand_path),
        },
        "metadata": metadata,
        "protein": protein.to_dict(),
        "ligand": ligand.to_dict(),
        "pocket": pocket.to_dict(),
        "scaffold": scaffold.to_dict(),
        "rgroups": [rgroup.to_dict() for rgroup in rgroups],
        "masks": masks,
        "sanity": sanity,
        "software_versions": collect_software_versions(),
    }


def save_processed_sample(sample: dict[str, Any], output_dir: str | Path) -> Path:
    complexes_dir = ensure_dir(Path(output_dir) / "complexes")
    sample_id = sample["sample_id"]
    path = complexes_dir / f"{sample_id}.pkl"
    sample["paths"]["processed_path"] = str(path)
    with path.open("wb") as f:
        pickle.dump(sample, f, protocol=pickle.HIGHEST_PROTOCOL)
    return path


def build_processed_dataset(
    raw_root: str | Path,
    output_root: str | Path,
    config: dict[str, Any],
    *,
    report_dir: str | Path | None = None,
) -> dict[str, pd.DataFrame]:
    raw_complexes = find_raw_complexes(raw_root)
    output_dir = ensure_dir(output_root)
    report_path = ensure_dir(report_dir) if report_dir is not None else None

    manifest_rows: list[dict[str, Any]] = []
    failed_rows: list[dict[str, Any]] = []
    for raw_complex in raw_complexes:
        try:
            sample = build_processed_sample(raw_complex, config)
            processed_path = save_processed_sample(sample, output_dir)
            manifest_rows.append(_manifest_row(sample, processed_path))
        except SampleBuildError as exc:
            failed_rows.append(_failed_row(raw_complex, exc.reason, str(exc), exc.stage))
        except Exception as exc:
            failed_rows.append(_failed_row(raw_complex, "unexpected_error", str(exc), "build"))

    manifest = pd.DataFrame(manifest_rows, columns=MANIFEST_COLUMNS)
    manifest_path = output_dir / "manifest.parquet"
    manifest.to_parquet(manifest_path, index=False)
    write_schema_json(output_dir / "schema.json")

    failed = pd.DataFrame(failed_rows, columns=FAILED_COLUMNS)
    if report_path is not None:
        failed.to_csv(report_path / "failed_cases.csv", index=False)
        summary = {
            "num_raw_complexes": len(raw_complexes),
            "num_processed": int(len(manifest)),
            "num_failed": int(len(failed)),
            "processed_root": str(output_dir),
            "manifest_path": str(manifest_path),
        }
        with (report_path / "summary.json").open("w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

    return {"manifest": manifest, "failed_cases": failed}


def collect_software_versions() -> dict[str, str | None]:
    modules = {
        "rdkit": "rdkit",
        "biopython": "Bio",
        "mdanalysis": "MDAnalysis",
        "numpy": "numpy",
        "scipy": "scipy",
        "pandas": "pandas",
    }
    versions: dict[str, str | None] = {"python": platform.python_version()}
    for key, module_name in modules.items():
        try:
            module = import_module(module_name)
            versions[key] = getattr(module, "__version__", None)
        except Exception:
            versions[key] = None
    return versions


def _sanitize_mol_in_place(mol: Any) -> None:
    try:
        from rdkit import Chem
    except ImportError as exc:
        raise SampleBuildError("rdkit_not_available", str(exc), stage="ligand") from exc
    Chem.SanitizeMol(mol)


def write_schema_json(path: str | Path) -> None:
    schema = {
        "schema_version": "0.1",
        "format": "pickle_sample_plus_manifest_parquet",
        "required_top_level_fields": [
            "schema_version",
            "sample_id",
            "complex_id",
            "source",
            "created_at",
            "paths",
            "metadata",
            "protein",
            "ligand",
            "pocket",
            "scaffold",
            "rgroups",
            "masks",
            "sanity",
            "software_versions",
        ],
        "manifest_columns": MANIFEST_COLUMNS,
    }
    with Path(path).open("w", encoding="utf-8") as f:
        json.dump(schema, f, ensure_ascii=False, indent=2)


def _normalized_metadata(raw_complex: RawComplex) -> dict[str, Any]:
    metadata = dict(raw_complex.metadata)
    complex_id = raw_complex.complex_id
    split_group, split_group_source = _resolve_split_group(metadata, complex_id)
    metadata.update(
        {
            "pdb_id": metadata.get("pdb_id"),
            "uniprot_id": metadata.get("uniprot_id"),
            "target_id": metadata.get("target_id"),
            "target_name": metadata.get("target_name"),
            "protein_family": metadata.get("protein_family"),
            "cluster": metadata.get("cluster"),
            "chain_ids": metadata.get("chain_ids") or [],
            "ligand_id": metadata.get("ligand_id"),
            "dataset_name": metadata.get("dataset_name") or metadata.get("source") or "unknown",
            "split_group": split_group,
            "split_group_source": split_group_source,
            "complex_id": complex_id,
        }
    )
    return metadata


def _resolve_split_group(metadata: dict[str, Any], complex_id: str) -> tuple[str, str]:
    if metadata.get("split_group_source") and metadata.get("split_group") not in (None, ""):
        return str(metadata["split_group"]), str(metadata["split_group_source"])
    for key in ("uniprot_id", "target_id", "target_name", "protein_family", "cluster", "pdb_id"):
        value = metadata.get(key)
        if value not in (None, ""):
            return str(value), key
    split_group = metadata.get("split_group")
    if split_group not in (None, ""):
        return str(split_group), str(metadata.get("split_group_source") or "split_group")
    return complex_id, "complex_id"


def _first_nonempty(metadata: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = metadata.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _all_coords_finite(*arrays: np.ndarray) -> bool:
    return all(bool(np.isfinite(np.asarray(array)).all()) for array in arrays)


def _manifest_row(sample: dict[str, Any], processed_path: Path) -> dict[str, Any]:
    sanity = sample["sanity"]
    metadata = sample["metadata"]
    return {
        "sample_id": sample["sample_id"],
        "complex_id": sample["complex_id"],
        "source": sample["source"],
        "protein_path": sample["paths"]["raw_protein_path"],
        "ligand_path": sample["paths"]["raw_ligand_path"],
        "processed_path": str(processed_path),
        "ligand_heavy_atoms": int(sample["ligand"]["num_heavy_atoms"]),
        "num_pocket_atoms": int(sample["pocket"]["num_pocket_atoms"]),
        "num_pocket_atoms_6A": int(sample["pocket"]["num_atoms_6A"]),
        "num_pocket_atoms_8A": int(sample["pocket"]["num_atoms_8A"]),
        "min_ligand_protein_distance": float(sanity["min_ligand_protein_distance"]),
        "num_obvious_clash_pairs": int(sanity["num_obvious_clash_pairs"]),
        "num_pairs_below_1_0": int(sanity["num_pairs_below_1_0"]),
        "num_pairs_below_1_2": int(sanity["num_pairs_below_1_2"]),
        "num_pairs_below_1_5": int(sanity["num_pairs_below_1_5"]),
        "num_rgroups": int(len(sample["rgroups"])),
        "num_valid_rgroups": int(sanity["num_valid_rgroups"]),
        "num_single_anchor_rgroups": int(sanity["num_single_anchor_rgroups"]),
        "scaffold_num_atoms": int(sample["scaffold"]["num_atoms"]),
        "scaffold_success": bool(sample["scaffold"]["success"]),
        "valid_ligand": bool(sanity["valid_ligand"]),
        "basic_clash_screen_pass": bool(sanity["basic_clash_screen_pass"]),
        "phase0_usable": len(sanity.get("fatal_errors", [])) == 0,
        "failure_reason": "",
        "split_group": str(metadata.get("split_group") or sample["complex_id"]),
        "split_group_source": str(metadata.get("split_group_source") or "complex_id"),
        "uniprot_id": metadata.get("uniprot_id"),
        "target_id": metadata.get("target_id"),
        "target_name": metadata.get("target_name"),
        "protein_family": metadata.get("protein_family"),
        "cluster": metadata.get("cluster"),
        "pdb_id": metadata.get("pdb_id"),
    }


def _failed_row(raw_complex: RawComplex, reason: str, message: str, stage: str) -> dict[str, Any]:
    return {
        "complex_id": raw_complex.complex_id,
        "source": raw_complex.metadata.get("source") or raw_complex.metadata.get("dataset_name") or "unknown",
        "protein_path": str(raw_complex.protein_path),
        "ligand_path": str(raw_complex.ligand_path),
        "failure_reason": reason,
        "stage": stage,
        "message": message,
    }


MANIFEST_COLUMNS = [
    "sample_id",
    "complex_id",
    "source",
    "protein_path",
    "ligand_path",
    "processed_path",
    "ligand_heavy_atoms",
    "num_pocket_atoms",
    "num_pocket_atoms_6A",
    "num_pocket_atoms_8A",
    "min_ligand_protein_distance",
    "num_obvious_clash_pairs",
    "num_pairs_below_1_0",
    "num_pairs_below_1_2",
    "num_pairs_below_1_5",
    "num_rgroups",
    "num_valid_rgroups",
    "num_single_anchor_rgroups",
    "scaffold_num_atoms",
    "scaffold_success",
    "valid_ligand",
    "basic_clash_screen_pass",
    "phase0_usable",
    "failure_reason",
    "split_group",
    "split_group_source",
    "uniprot_id",
    "target_id",
    "target_name",
    "protein_family",
    "cluster",
    "pdb_id",
]

FAILED_COLUMNS = [
    "complex_id",
    "source",
    "protein_path",
    "ligand_path",
    "failure_reason",
    "stage",
    "message",
]
