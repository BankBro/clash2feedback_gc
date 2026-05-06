import pytest

pytest.importorskip("rdkit")

from rdkit import Chem
from rdkit.Chem import AllChem

from clash2feedback.chemistry.rgroup import decompose_rgroups
from clash2feedback.chemistry.sanitize import check_ligand_validity
from clash2feedback.chemistry.scaffold import get_murcko_scaffold_atom_indices
from clash2feedback.io.read_ligand import read_ligand_sdf


def _embedded_mol(smiles: str):
    mol = Chem.AddHs(Chem.MolFromSmiles(smiles))
    status = AllChem.EmbedMolecule(mol, randomSeed=20260504)
    assert status == 0
    Chem.SanitizeMol(mol)
    return mol


def test_ligand_validity_allows_h_when_allowed_elements_are_heavy_only() -> None:
    mol = _embedded_mol("CCO")
    result = check_ligand_validity(
        mol,
        min_heavy_atoms=1,
        max_heavy_atoms=10,
        allowed_elements={"C", "O"},
    )
    assert result["ok"] is True


def test_scaffold_and_rgroup_decomposition_marks_valid_single_anchor() -> None:
    mol = _embedded_mol("CCc1ccccc1")
    scaffold = get_murcko_scaffold_atom_indices(mol)
    rgroups = decompose_rgroups(mol, scaffold, min_heavy_atoms=2, max_heavy_atoms=15)
    assert scaffold.success is True
    assert any(rgroup.is_valid_for_phase0 for rgroup in rgroups)


def test_read_ligand_sdf_rejects_multiple_molecules_by_default(tmp_path) -> None:
    sdf_path = tmp_path / "multi.sdf"
    writer = Chem.SDWriter(str(sdf_path))
    writer.write(_embedded_mol("CCO"))
    writer.write(_embedded_mol("CCN"))
    writer.close()

    with pytest.raises(ValueError, match="Multiple molecules"):
        read_ligand_sdf(sdf_path)
