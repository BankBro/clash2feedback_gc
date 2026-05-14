from pathlib import Path

import numpy as np
import pandas as pd

from clash2feedback.repair.case_selection import load_mask_seed, select_formal_cases, select_preflight_cases
from clash2feedback.repair.diffdec_adapter import write_diffdec_scaffold_inputs
from clash2feedback.repair.diffsbdd_adapter import build_full_resampling_command, build_inpaint_command
from clash2feedback.repair.phase4_inputs import load_phase4_case_inputs, write_keep_submol_sdf
from clash2feedback.repair.rule_backend import run_rule_backend
from clash2feedback.utils.config import load_yaml_config
from clash2feedback.verifier.phase4_adapter import RELIABLE_REPAIR_FIELDS, evaluate_candidate_for_phase4


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "configs/phase4_0_backend_feasibility.yaml"


def _config() -> dict:
    return load_yaml_config(CONFIG_PATH)


def _phase1_config() -> dict:
    return load_yaml_config(REPO_ROOT / "configs/phase1_clash_detector.yaml")


def _selected_inputs() -> tuple[pd.DataFrame, list]:
    config = _config()
    selected = select_preflight_cases(load_mask_seed(REPO_ROOT / config["inputs"]["phase4_mask_seed"]), config)
    inputs = load_phase4_case_inputs(
        selected.head(1),
        phase2_manifest_path=REPO_ROOT / config["inputs"]["phase2_manifest"],
        phase2_benchmark_root=REPO_ROOT / config["inputs"]["phase2_benchmark_root"],
        processed_root=REPO_ROOT / config["inputs"]["processed_root"],
    )
    return selected, inputs


def test_phase4_preflight_selection_freezes_five_s2_cases() -> None:
    config = _config()
    selected = select_preflight_cases(load_mask_seed(REPO_ROOT / config["inputs"]["phase4_mask_seed"]), config)

    assert selected["case_id"].tolist() == ["case_001001", "case_001243", "case_000982", "case_001238", "case_000703"]
    assert selected.shape[0] == 5
    assert set(selected["injection_mode"]) == {"directed_clash", "easy_rotation", "torsion_perturb"}
    assert "medium" in set(selected["difficulty_bin"])
    assert selected["oracle_mask_size"].between(1, 20).all()


def test_phase4_formal_selection_matches_stratified_quotas() -> None:
    config = _config()
    selected = select_formal_cases(load_mask_seed(REPO_ROOT / config["inputs"]["phase4_mask_seed"]), config)

    assert selected.shape[0] == 40
    assert selected["injection_mode"].value_counts().to_dict() == {
        "directed_clash": 14,
        "easy_rotation": 13,
        "torsion_perturb": 13,
    }
    assert selected["difficulty_bin"].value_counts().to_dict() == {"easy": 27, "medium": 13}
    assert selected["base_split"].value_counts().to_dict() == {"train": 29, "test": 9, "val": 2}
    assert selected["base_sample_id"].value_counts().max() <= 3


def test_rule_backend_outputs_at_most_k_candidates(tmp_path: Path) -> None:
    config = _config()
    _, inputs = _selected_inputs()
    _, rows = run_rule_backend(
        inputs[0],
        backend_cfg=config["backends"]["rule_fixed_topology"],
        verifier_config=_phase1_config(),
        run_root=tmp_path,
        k=8,
    )

    assert rows
    assert max(int(row["candidate_count"]) for row in rows) <= 8
    assert all("proposal_count" in row and "runtime_sec" in row and "failure_reason" in row for row in rows)
    for row in rows:
        if row["candidate_path"]:
            assert Path(row["candidate_path"]).exists()
            assert row["uses_h_clash_in_generation"] is False


def test_diffsbdd_input_adapter_uses_keep_atoms_and_failed_ligand(tmp_path: Path) -> None:
    config = _config()
    _, inputs = _selected_inputs()
    case_input = inputs[0]
    fix_atoms = tmp_path / "fix_atoms.sdf"
    fix_meta = write_keep_submol_sdf(case_input, fix_atoms)
    command = build_inpaint_command(
        config["backends"]["diffsbdd_conditional_inpainting"],
        case_input=case_input,
        repo_root=REPO_ROOT,
        fix_atoms_sdf=fix_atoms,
        output_sdf=tmp_path / "out.sdf",
        center="ligand",
    )

    assert fix_atoms.exists()
    assert fix_meta["fixed_atom_count"] == len(case_input.keep_atom_indices)
    assert fix_meta["add_n_nodes"] == len(case_input.mask_atom_indices)
    assert "--ref_ligand" in command
    assert str(case_input.failed_ligand_sdf) in command
    assert "--fix_atoms" in command
    assert str(fix_atoms) in command
    assert "H_clash" not in " ".join(command)


def test_diffsbdd_full_resampling_command_uses_failed_ligand_without_mask(tmp_path: Path) -> None:
    config = _config()
    _, inputs = _selected_inputs()
    case_input = inputs[0]
    command = build_full_resampling_command(
        config["backends"]["diffsbdd_full_resampling"],
        case_input=case_input,
        repo_root=REPO_ROOT,
        output_sdf=tmp_path / "full.sdf",
    )

    assert "generate_ligands.py" in command
    assert "--ref_ligand" in command
    assert str(case_input.failed_ligand_sdf) in command
    assert "--fix_atoms" not in command
    assert "H_clash" not in " ".join(command)


def test_diffdec_scaffold_adapter_writes_dummy_exit(tmp_path: Path) -> None:
    _, inputs = _selected_inputs()
    meta = write_diffdec_scaffold_inputs(
        inputs[0],
        scaffold_file=tmp_path / "fixed_context.sdf",
        scaffold_smiles_file=tmp_path / "fixed_context.smi",
    )

    assert Path(meta["scaffold_file"]).exists()
    assert Path(meta["scaffold_smiles_file"]).exists()
    assert "*" in Path(meta["scaffold_smiles_file"]).read_text(encoding="utf-8")
    assert meta["fixed_atom_count"] == len(inputs[0].keep_atom_indices)


def test_phase4_verifier_adapter_keeps_failure_in_denominator() -> None:
    _, inputs = _selected_inputs()
    outcome = evaluate_candidate_for_phase4(
        {
            "backend_name": "mock_backend",
            "backend_unit": "mock_unit",
            "case_id": inputs[0].case_id,
            "candidate_id": "",
            "candidate_index": 0,
            "candidate_path": "",
            "failure_stage": "generation",
            "failure_reason": "mock_failure",
            "same_topology": False,
        },
        inputs[0],
        verifier_config=_phase1_config(),
    )

    assert len(RELIABLE_REPAIR_FIELDS) == 10
    assert outcome["candidate_readable"] is False
    assert outcome["reliable_repair_success"] is False
    assert outcome["failure_reason"] == "mock_failure"


def test_phase4_verifier_adapter_accepts_same_topology_candidate(tmp_path: Path) -> None:
    from clash2feedback.perturb.quality import copy_mol_with_coords
    from clash2feedback.repair.phase4_inputs import read_first_mol
    from rdkit import Chem

    _, inputs = _selected_inputs()
    case_input = inputs[0]
    mol = read_first_mol(case_input.failed_ligand_sdf, sanitize=False)
    candidate_path = tmp_path / "same_topology.sdf"
    writer = Chem.SDWriter(str(candidate_path))
    writer.write(copy_mol_with_coords(mol, np.asarray(case_input.failed_ligand_coords, dtype=np.float32)))
    writer.close()

    outcome = evaluate_candidate_for_phase4(
        {
            "backend_name": "rule_fixed_topology",
            "backend_unit": "fixed_topology_local_conformer_repair",
            "case_id": case_input.case_id,
            "candidate_id": "candidate",
            "candidate_index": 1,
            "candidate_path": str(candidate_path),
            "failure_stage": "",
            "failure_reason": "",
            "same_topology": True,
        },
        case_input,
        verifier_config=_phase1_config(),
    )

    assert outcome["candidate_readable"] is True
    assert outcome["fixed_structure_match_success"] is True
    assert outcome["anchor_integrity"] is True
    assert outcome["reliable_repair_success"] is False
