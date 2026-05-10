import pytest

Chem = pytest.importorskip("rdkit.Chem")

from clash2feedback.perturb.quality import check_rotatable_anchor_bond


def test_invalid_nonrotatable_double_bond_rejected() -> None:
    mol = Chem.MolFromSmiles("C=C")
    result = check_rotatable_anchor_bond(mol, {"anchor_bond_idx": 0})
    assert result["rotatable_bond_valid"] is False
    assert result["rotatable_bond_reason"] == "anchor_bond_not_single"


def test_aromatic_bond_rejected() -> None:
    mol = Chem.MolFromSmiles("c1ccccc1")
    result = check_rotatable_anchor_bond(mol, {"anchor_bond_idx": 0})
    assert result["rotatable_bond_valid"] is False
    assert result["rotatable_bond_reason"] in {"anchor_bond_aromatic", "anchor_bond_not_single"}


def test_amide_like_bond_rejected() -> None:
    mol = Chem.MolFromSmiles("CC(=O)NC")
    amide_bond_idx = None
    for bond in mol.GetBonds():
        atoms = {bond.GetBeginAtom().GetAtomicNum(), bond.GetEndAtom().GetAtomicNum()}
        if atoms == {6, 7} and bond.GetBeginAtom().GetDegree() > 1 and bond.GetEndAtom().GetDegree() > 1:
            amide_bond_idx = bond.GetIdx()
            break
    assert amide_bond_idx is not None
    result = check_rotatable_anchor_bond(mol, {"anchor_bond_idx": amide_bond_idx})
    assert result["rotatable_bond_valid"] is False
    assert result["rotatable_bond_reason"] in {"anchor_bond_amide_like", "anchor_bond_conjugated"}
