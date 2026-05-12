import numpy as np

from clash2feedback.generation_audit.ligand_validity import evaluate_generated_ligand


def _mol(smiles: str):
    from rdkit import Chem
    from rdkit.Chem import AllChem

    mol = Chem.AddHs(Chem.MolFromSmiles(smiles))
    AllChem.EmbedMolecule(mol, randomSeed=1)
    return mol


def test_generated_sdf_readable_validity_row() -> None:
    row = evaluate_generated_ligand("c1", _mol("CCO"), postprocess_stage="raw_generated", config={"min_heavy_atoms": 1})
    assert row["rdkit_readable"]
    assert row["rdkit_sanitize_ok"]
    assert row["has_3d_conformer"]


def test_unreadable_ligand_only_invalid() -> None:
    row = evaluate_generated_ligand("c1", None, postprocess_stage="raw_generated", readable=False)
    assert not row["rdkit_readable"]
    assert row["ligand_validity_status"] == "invalid"
    assert row["ligand_validity_reason"] == "rdkit_unreadable"


def test_multifragment_status_recorded() -> None:
    row = evaluate_generated_ligand("c1", _mol("CC.O"), postprocess_stage="raw_generated", config={"min_heavy_atoms": 1})
    assert row["num_fragments"] == 2
    assert row["ligand_validity_status"] == "invalid"
    assert "multiple_fragments" in row["ligand_validity_reason"]


def test_coords_not_finite_rejected() -> None:
    mol = _mol("CCO")
    conf = mol.GetConformer()
    conf.SetAtomPosition(0, (float("nan"), 0.0, 0.0))
    row = evaluate_generated_ligand("c1", mol, postprocess_stage="raw_generated", config={"min_heavy_atoms": 1})
    assert not row["coords_finite"]
    assert "coords_not_finite" in row["ligand_validity_reason"]


def test_internal_clash_count_recorded() -> None:
    mol = _mol("CCCC")
    conf = mol.GetConformer()
    for idx in range(mol.GetNumAtoms()):
        conf.SetAtomPosition(idx, (0.0, 0.0, 0.0))
    row = evaluate_generated_ligand("c1", mol, postprocess_stage="raw_generated", config={"min_heavy_atoms": 1})
    assert row["ligand_internal_severe_clash_count"] >= 1
    assert np.isfinite(row["ligand_internal_max_depth"])
