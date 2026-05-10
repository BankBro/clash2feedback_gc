import numpy as np
import pytest

Chem = pytest.importorskip("rdkit.Chem")

from clash2feedback.perturb.quality import (
    evaluate_ligand_only_quality,
    ligand_energy_delta,
    ligand_internal_severe_clash_count,
)


def _mol() -> object:
    mol = Chem.MolFromSmiles("CCCC")
    mol = Chem.AddHs(mol)
    conf = Chem.Conformer(mol.GetNumAtoms())
    coords = np.zeros((mol.GetNumAtoms(), 3), dtype=float)
    coords[:4] = np.asarray([[0.0, 0.0, 0.0], [1.54, 0.0, 0.0], [3.08, 0.0, 0.0], [4.62, 0.0, 0.0]])
    for idx, xyz in enumerate(coords):
        conf.SetAtomPosition(idx, tuple(float(v) for v in xyz))
    mol.AddConformer(conf)
    return mol


def _sample(mol: object) -> dict:
    return {
        "sample_id": "mock",
        "ligand": {
            "molblock": Chem.MolToMolBlock(mol),
            "coords": np.asarray(mol.GetConformer().GetPositions(), dtype=np.float32),
            "atomic_numbers": [atom.GetAtomicNum() for atom in mol.GetAtoms()],
        },
    }


def _config() -> dict:
    return {
        "chemistry": {
            "require_rdkit_sanitize": True,
            "require_rotatable_anchor_bond": True,
            "require_chirality_preserved": True,
            "use_energy_delta_filter": True,
            "forcefield_preference": ["UFF"],
            "energy_delta_threshold_mode": "record_only",
        },
        "geometry": {
            "anchor_bond_length_delta_threshold": 0.05,
            "bond_length_delta_threshold": 0.05,
            "ligand_internal_delta_angstrom": 0.4,
            "ligand_internal_severe_depth_threshold_angstrom": 0.4,
            "ligand_internal_severe_clash_allowed": 0,
        },
    }


def test_ligand_validity_records_energy_delta() -> None:
    mol = _mol()
    coords = np.asarray(mol.GetConformer().GetPositions(), dtype=np.float32)
    result = evaluate_ligand_only_quality(
        _sample(mol),
        mol,
        {"anchor_bond_idx": 0, "anchor_scaffold_atom_idx": 0, "anchor_rgroup_atom_idx": 1},
        coords,
        coords.copy(),
        _config(),
    )
    assert result["ligand_valid"] is True
    assert result["rdkit_sanitize_ok"] is True
    assert result["ligand_internal_severe_clash_count"] == 0
    assert result["forcefield_type"] in {"UFF", "unavailable"}


def test_ligand_internal_clash_gate_counts_nonbonded_overlap() -> None:
    mol = _mol()
    coords = np.asarray(mol.GetConformer().GetPositions(), dtype=np.float32)
    coords[3] = coords[0] + np.asarray([0.1, 0.0, 0.0], dtype=np.float32)
    count, max_depth = ligand_internal_severe_clash_count(mol, coords)
    assert count >= 1
    assert max_depth > 0.4


def test_energy_unavailable_recorded_not_crash() -> None:
    mol = _mol()
    coords = np.asarray(mol.GetConformer().GetPositions(), dtype=np.float32)
    result = ligand_energy_delta(mol, coords, coords, forcefield_preference=["BAD"], threshold_mode="record_only")
    assert result["forcefield_type"] == "unavailable"
    assert result["energy_delta_pass"] is True
