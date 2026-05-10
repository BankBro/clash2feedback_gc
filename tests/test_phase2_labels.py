from clash2feedback.perturb.labels import assign_oracle_split


def _pair(region: str, depth: float = 0.8) -> dict:
    return {
        "ligand_atom_idx": 1,
        "protein_atom_idx": 2,
        "ligand_region": region,
        "clash_depth": depth,
        "is_severe": depth >= 0.4,
        "protein_residue_key": "A:1::ALA",
    }


def _report(pairs: list[dict]) -> dict:
    return {
        "analysis_status": "ok",
        "unsupported_reasons": [],
        "clash_pairs": pairs,
        "max_clash_depth": max([pair["clash_depth"] for pair in pairs] or [0.0]),
    }


def _quality(ok: bool = True) -> dict:
    return {"ligand_valid": ok, "fatal_errors": [] if ok else ["ligand_internal_severe_clash"]}


def _acceptance() -> dict:
    return {
        "min_target_severe_pairs": 1,
        "min_target_score_ratio_valid": 0.7,
        "max_scaffold_severe_pairs": 0,
        "max_non_target_severe_pairs": 0,
        "max_clash_depth_angstrom": 1.5,
    }


def test_supported_single_rgroup_label_independent_of_prediction_field() -> None:
    attr = {
        "dominant_valid_rgroup": "R2",
        "valid_rgroup_scores": {"R1": 10.0, "R2": 0.0},
    }
    result = assign_oracle_split(
        ligand_quality=_quality(),
        clash_report=_report([_pair("R1")]),
        attribution=attr,
        target_rgroup="R1",
        acceptance_cfg=_acceptance(),
    )
    assert result["oracle_split"] == "supported_single_rgroup"


def test_multi_region_label() -> None:
    result = assign_oracle_split(
        ligand_quality=_quality(),
        clash_report=_report([_pair("R1"), _pair("R2")]),
        attribution={"valid_rgroup_scores": {"R1": 10.0, "R2": 2.0}},
        target_rgroup="R1",
        acceptance_cfg=_acceptance(),
    )
    assert result["oracle_split"] == "multi_region"


def test_scaffold_clash_label() -> None:
    result = assign_oracle_split(
        ligand_quality=_quality(),
        clash_report=_report([_pair("R1"), _pair("scaffold")]),
        attribution={"valid_rgroup_scores": {"R1": 10.0}},
        target_rgroup="R1",
        acceptance_cfg=_acceptance(),
    )
    assert result["oracle_split"] == "scaffold_clash"


def test_near_miss_and_invalid_labels() -> None:
    near = assign_oracle_split(
        ligand_quality=_quality(),
        clash_report=_report([]),
        attribution={"valid_rgroup_scores": {}},
        target_rgroup="R1",
        acceptance_cfg=_acceptance(),
    )
    invalid = assign_oracle_split(
        ligand_quality=_quality(False),
        clash_report=_report([_pair("R1")]),
        attribution={"valid_rgroup_scores": {"R1": 10.0}},
        target_rgroup="R1",
        acceptance_cfg=_acceptance(),
    )
    assert near["oracle_split"] == "near_miss_contact"
    assert invalid["oracle_split"] == "invalid_conformer"
