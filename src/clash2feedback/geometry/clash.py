from __future__ import annotations

from typing import Any

import numpy as np

from clash2feedback.geometry.clash_types import ClashPair, ClashReport
from clash2feedback.geometry.rgroup_attribution import ligand_atom_regions, ligand_region_warnings
from clash2feedback.geometry.vdw import get_vdw_radius, normalize_element


SUPPORTED_ATOMIC_NUMBERS = {1, 6, 7, 8, 9, 15, 16, 17, 35, 53}
ATOMIC_NUMBER_TO_ELEMENT = {
    1: "H",
    6: "C",
    7: "N",
    8: "O",
    9: "F",
    15: "P",
    16: "S",
    17: "Cl",
    35: "Br",
    53: "I",
}
WATER_NAMES = {"HOH", "WAT", "H2O"}
METAL_OR_COFACTOR_ATOMIC_NUMBERS = {
    3,
    4,
    11,
    12,
    13,
    19,
    20,
    21,
    22,
    23,
    24,
    25,
    26,
    27,
    28,
    29,
    30,
    47,
    48,
    50,
    56,
    78,
    79,
    80,
}


def detect_clashes(
    sample: dict[str, Any],
    ligand_coords: np.ndarray | None = None,
    receptor_scope: str = "phase0_pocket8",
    delta_angstrom: float = 0.4,
    severe_depth_threshold_angstrom: float = 0.4,
    chunk_size: int = 256,
) -> dict[str, Any]:
    sample_id = str(sample.get("sample_id") or sample.get("complex_id") or "")
    if receptor_scope == "full_receptor_dynamic_shell":
        return _empty_report(
            sample_id,
            receptor_scope,
            delta_angstrom,
            severe_depth_threshold_angstrom,
            ["full_receptor_dynamic_shell_not_available"],
            analysis_status="unsupported_scope",
        )

    unsupported_reasons = _metadata_unsupported_reasons(sample)
    if "unsupported_covalent_ligand" in unsupported_reasons:
        return _empty_report(
            sample_id,
            receptor_scope,
            delta_angstrom,
            severe_depth_threshold_angstrom,
            unsupported_reasons,
            analysis_status=_analysis_status(unsupported_reasons),
        )

    ligand = sample.get("ligand", {})
    protein = sample.get("protein", {})
    ligand_coord_array = _ligand_coords(sample, ligand_coords)
    protein_coord_array = np.asarray(protein.get("coords"), dtype=np.float32)
    if protein_coord_array.ndim != 2 or protein_coord_array.shape[1] != 3:
        raise ValueError(f"Invalid protein coords for sample {sample_id!r}.")

    receptor_indices = _receptor_atom_indices(sample, receptor_scope)
    receptor_positions = np.arange(receptor_indices.shape[0], dtype=np.int64)
    unsupported_reasons.extend(ligand_region_warnings(sample))
    ligand_indices, ligand_elements, ligand_radii, ligand_reasons = _selected_ligand_atoms(ligand)
    protein_indices, protein_positions, protein_elements, protein_radii, protein_reasons = _selected_protein_atoms(
        protein,
        receptor_indices,
        receptor_positions,
    )
    unsupported_reasons.extend(ligand_reasons)
    unsupported_reasons.extend(protein_reasons)

    if ligand_indices.size == 0 or protein_indices.size == 0:
        return _empty_report(
            sample_id,
            receptor_scope,
            delta_angstrom,
            severe_depth_threshold_angstrom,
            sorted(set(unsupported_reasons)),
            analysis_status=_analysis_status(unsupported_reasons),
        )

    ligand_regions = ligand_atom_regions(sample)
    ligand_selected_coords = ligand_coord_array[ligand_indices]
    protein_selected_coords = protein_coord_array[protein_indices]
    clash_pairs: list[ClashPair] = []
    total_score = 0.0
    max_depth = 0.0
    depth_sum = 0.0
    severe_count = 0

    chunk = max(int(chunk_size), 1)
    for start in range(0, protein_selected_coords.shape[0], chunk):
        stop = min(start + chunk, protein_selected_coords.shape[0])
        protein_chunk = protein_selected_coords[start:stop]
        diff = ligand_selected_coords[:, None, :] - protein_chunk[None, :, :]
        distances = np.sqrt(np.sum(diff * diff, axis=2))
        vdw_sums = ligand_radii[:, None] + protein_radii[start:stop][None, :]
        depths = np.maximum(0.0, vdw_sums - float(delta_angstrom) - distances)
        ligand_pos, protein_pos = np.nonzero(depths > 0.0)
        for local_ligand_pos, local_protein_pos in zip(ligand_pos.tolist(), protein_pos.tolist(), strict=False):
            depth = float(depths[local_ligand_pos, local_protein_pos])
            distance = float(distances[local_ligand_pos, local_protein_pos])
            protein_selected_pos = start + local_protein_pos
            ligand_atom_idx = int(ligand_indices[local_ligand_pos])
            protein_atom_idx = int(protein_indices[protein_selected_pos])
            is_severe = depth >= float(severe_depth_threshold_angstrom)
            if is_severe:
                severe_count += 1
            total_score += depth * depth
            depth_sum += depth
            max_depth = max(max_depth, depth)
            clash_pairs.append(
                ClashPair(
                    ligand_atom_idx=ligand_atom_idx,
                    protein_atom_idx=protein_atom_idx,
                    protein_atom_position=int(protein_positions[protein_selected_pos]),
                    ligand_element=str(ligand_elements[local_ligand_pos]),
                    protein_element=str(protein_elements[protein_selected_pos]),
                    distance=distance,
                    vdw_sum=float(vdw_sums[local_ligand_pos, local_protein_pos]),
                    clash_depth=depth,
                    is_severe=bool(is_severe),
                    ligand_region=ligand_regions[ligand_atom_idx] if ligand_atom_idx < len(ligand_regions) else "unknown",
                    protein_residue_key=_protein_residue_key(protein, protein_atom_idx),
                )
            )

    report = ClashReport(
        sample_id=sample_id,
        receptor_scope=receptor_scope,
        delta_angstrom=float(delta_angstrom),
        severe_depth_threshold_angstrom=float(severe_depth_threshold_angstrom),
        num_clash_pairs=len(clash_pairs),
        num_severe_clash_pairs=int(severe_count),
        total_clash_score=float(total_score),
        max_clash_depth=float(max_depth),
        mean_clash_depth=float(depth_sum / len(clash_pairs)) if clash_pairs else 0.0,
        clash_pairs=clash_pairs,
        unsupported_reasons=sorted(set(unsupported_reasons)),
        analysis_status=_analysis_status(unsupported_reasons),
    )
    return report.to_dict()


def _metadata_unsupported_reasons(sample: dict[str, Any]) -> list[str]:
    metadata = sample.get("metadata", {})
    protein = sample.get("protein", {})
    if metadata.get("is_covalent_ligand") or metadata.get("covalent"):
        return ["unsupported_covalent_ligand"]
    atomic_numbers = [int(value) for value in protein.get("atomic_numbers", [])]
    if any(number in METAL_OR_COFACTOR_ATOMIC_NUMBERS for number in atomic_numbers):
        return ["unsupported_metal_or_cofactor"]
    return []


def _ligand_coords(sample: dict[str, Any], ligand_coords: np.ndarray | None) -> np.ndarray:
    coords = np.asarray(ligand_coords if ligand_coords is not None else sample.get("ligand", {}).get("coords"), dtype=np.float32)
    if coords.ndim != 2 or coords.shape[1] != 3:
        raise ValueError(f"Invalid ligand coords for sample {sample.get('sample_id', '')!r}.")
    if not np.isfinite(coords).all():
        raise ValueError(f"Ligand coords contain non-finite values for sample {sample.get('sample_id', '')!r}.")
    return coords


def _receptor_atom_indices(sample: dict[str, Any], receptor_scope: str) -> np.ndarray:
    protein = sample.get("protein", {})
    num_protein_atoms = int(protein.get("num_atoms") or np.asarray(protein.get("coords")).shape[0])
    if receptor_scope == "phase0_pocket8":
        indices = np.asarray(sample.get("pocket", {}).get("protein_atom_indices", []), dtype=np.int64)
    elif receptor_scope == "pocket10_all_atoms":
        indices = np.arange(num_protein_atoms, dtype=np.int64)
    else:
        raise ValueError(f"Unsupported receptor_scope: {receptor_scope}")
    if indices.size == 0:
        return indices
    return indices[(indices >= 0) & (indices < num_protein_atoms)]


def _selected_ligand_atoms(ligand: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    atomic_numbers = [int(value) for value in ligand.get("atomic_numbers", [])]
    elements = list(ligand.get("elements", []))
    num_atoms = int(ligand.get("num_atoms") or len(atomic_numbers) or len(elements))
    if not atomic_numbers:
        atomic_numbers = [0] * num_atoms
    selected_indices: list[int] = []
    selected_elements: list[str] = []
    selected_radii: list[float] = []
    unsupported: list[str] = []
    for atom_idx in range(num_atoms):
        atomic_number = atomic_numbers[atom_idx] if atom_idx < len(atomic_numbers) else 0
        if atomic_number <= 1:
            continue
        if atomic_number not in SUPPORTED_ATOMIC_NUMBERS:
            if atomic_number in METAL_OR_COFACTOR_ATOMIC_NUMBERS:
                unsupported.append(f"unsupported_metal:{_element_value(elements, atomic_numbers, atom_idx)}")
            else:
                unsupported.append(f"unsupported_ligand_element:{_element_value(elements, atomic_numbers, atom_idx)}")
            continue
        try:
            element = _normalized_atom_element(elements, atomic_numbers, atom_idx)
            radius = get_vdw_radius(element)
        except ValueError:
            unsupported.append(f"unsupported_ligand_element:{_element_value(elements, atomic_numbers, atom_idx)}")
            continue
        selected_indices.append(atom_idx)
        selected_elements.append(element)
        selected_radii.append(radius)
    return (
        np.asarray(selected_indices, dtype=np.int64),
        np.asarray(selected_elements, dtype=object),
        np.asarray(selected_radii, dtype=np.float32),
        unsupported,
    )


def _selected_protein_atoms(
    protein: dict[str, Any],
    receptor_indices: np.ndarray,
    receptor_positions: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str]]:
    atomic_numbers = [int(value) for value in protein.get("atomic_numbers", [])]
    elements = list(protein.get("elements", []))
    residue_names = list(protein.get("residue_names", []))
    is_hetero = np.asarray(protein.get("is_hetero", np.zeros(len(atomic_numbers), dtype=bool)), dtype=bool)
    selected_indices: list[int] = []
    selected_positions: list[int] = []
    selected_elements: list[str] = []
    selected_radii: list[float] = []
    unsupported: list[str] = []
    for atom_idx, position in zip(receptor_indices.tolist(), receptor_positions.tolist(), strict=False):
        atomic_number = atomic_numbers[atom_idx] if atom_idx < len(atomic_numbers) else 0
        residue_name = str(residue_names[atom_idx]).upper() if atom_idx < len(residue_names) else ""
        if atomic_number <= 1 or residue_name in WATER_NAMES:
            continue
        if atom_idx < is_hetero.shape[0] and bool(is_hetero[atom_idx]):
            continue
        if atomic_number not in SUPPORTED_ATOMIC_NUMBERS:
            if atomic_number in METAL_OR_COFACTOR_ATOMIC_NUMBERS:
                unsupported.append(f"unsupported_metal:{_element_value(elements, atomic_numbers, atom_idx)}")
            else:
                unsupported.append(f"unsupported_protein_element:{_element_value(elements, atomic_numbers, atom_idx)}")
            continue
        try:
            element = _normalized_atom_element(elements, atomic_numbers, atom_idx)
            radius = get_vdw_radius(element)
        except ValueError:
            unsupported.append(f"unsupported_protein_element:{_element_value(elements, atomic_numbers, atom_idx)}")
            continue
        selected_indices.append(atom_idx)
        selected_positions.append(position)
        selected_elements.append(element)
        selected_radii.append(radius)
    return (
        np.asarray(selected_indices, dtype=np.int64),
        np.asarray(selected_positions, dtype=np.int64),
        np.asarray(selected_elements, dtype=object),
        np.asarray(selected_radii, dtype=np.float32),
        unsupported,
    )


def _normalized_atom_element(elements: list[Any], atomic_numbers: list[int], atom_idx: int) -> str:
    if atom_idx < len(elements) and elements[atom_idx] not in (None, ""):
        return normalize_element(str(elements[atom_idx]))
    atomic_number = atomic_numbers[atom_idx] if atom_idx < len(atomic_numbers) else 0
    if atomic_number in ATOMIC_NUMBER_TO_ELEMENT:
        return ATOMIC_NUMBER_TO_ELEMENT[atomic_number]
    raise ValueError(f"Unsupported atomic number: {atomic_number}")


def _element_value(elements: list[Any], atomic_numbers: list[int], atom_idx: int) -> str:
    if atom_idx < len(elements) and elements[atom_idx] not in (None, ""):
        return str(elements[atom_idx])
    if atom_idx < len(atomic_numbers):
        return str(atomic_numbers[atom_idx])
    return "unknown"


def _protein_residue_key(protein: dict[str, Any], atom_idx: int) -> str | None:
    chain_ids = list(protein.get("chain_ids", []))
    residue_ids = list(protein.get("residue_ids", []))
    insertion_codes = list(protein.get("insertion_codes", []))
    residue_names = list(protein.get("residue_names", []))
    if atom_idx >= len(residue_ids):
        return None
    chain_id = chain_ids[atom_idx] if atom_idx < len(chain_ids) else ""
    residue_id = residue_ids[atom_idx]
    insertion_code = insertion_codes[atom_idx] if atom_idx < len(insertion_codes) else ""
    residue_name = residue_names[atom_idx] if atom_idx < len(residue_names) else ""
    return f"{chain_id}:{residue_id}:{insertion_code}:{residue_name}"


def _empty_report(
    sample_id: str,
    receptor_scope: str,
    delta_angstrom: float,
    severe_depth_threshold_angstrom: float,
    unsupported_reasons: list[str] | None = None,
    analysis_status: str | None = None,
) -> dict[str, Any]:
    reasons = sorted(set(unsupported_reasons or []))
    return ClashReport(
        sample_id=sample_id,
        receptor_scope=receptor_scope,
        delta_angstrom=float(delta_angstrom),
        severe_depth_threshold_angstrom=float(severe_depth_threshold_angstrom),
        num_clash_pairs=0,
        num_severe_clash_pairs=0,
        total_clash_score=0.0,
        max_clash_depth=0.0,
        mean_clash_depth=0.0,
        clash_pairs=[],
        unsupported_reasons=reasons,
        analysis_status=analysis_status or _analysis_status(reasons),
    ).to_dict()


def _analysis_status(unsupported_reasons: list[str]) -> str:
    if not unsupported_reasons:
        return "ok"
    if any("covalent" in reason or "metal" in reason for reason in unsupported_reasons):
        return "unsupported_chemistry"
    if any(reason.startswith("unsupported_mask") for reason in unsupported_reasons):
        return "unsupported_mask"
    if any("unsupported_ligand_element" in reason or "unsupported_protein_element" in reason for reason in unsupported_reasons):
        return "partial_due_to_unsupported_atoms"
    if any(reason.startswith("full_receptor_dynamic_shell") for reason in unsupported_reasons):
        return "unsupported_scope"
    return "partial_due_to_unsupported_atoms"
