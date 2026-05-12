from clash2feedback.generation_audit.taxonomy import classify_failure_taxonomy, classify_repairability_proxy


def test_valid_no_severe_clash_taxonomy() -> None:
    row = classify_failure_taxonomy(candidate_id="c1", postprocess_stage="raw_generated")
    assert row["failure_taxonomy"] == "valid_no_severe_clash"


def test_ligand_only_invalid_taxonomy() -> None:
    row = classify_failure_taxonomy(
        candidate_id="c1",
        postprocess_stage="raw_generated",
        ligand_valid=False,
        ligand_validity_reason="rdkit_sanitize_failed",
    )
    assert row["failure_taxonomy"] == "ligand_only_invalid"


def test_rgroup_unattributable_taxonomy() -> None:
    row = classify_failure_taxonomy(
        candidate_id="c1",
        postprocess_stage="raw_generated",
        num_severe_clash_pairs=1,
        rgroup_attributable=False,
    )
    assert row["failure_taxonomy"] == "rgroup_unattributable"


def test_single_rgroup_clash_taxonomy_and_proxy() -> None:
    row = classify_failure_taxonomy(
        candidate_id="c1",
        postprocess_stage="raw_generated",
        num_severe_clash_pairs=1,
        max_clash_depth=0.8,
        rgroup_attributable=True,
        attribution_failure_type="single_rgroup_clash",
        dominant_valid_rgroup="R1",
        dominant_ratio_valid=0.8,
    )
    proxy = classify_repairability_proxy(row, max_clash_depth=0.8)
    assert row["failure_taxonomy"] == "single_rgroup_clash"
    assert proxy["repairability_proxy"] == "local_rgroup_repair_possible"


def test_multi_region_clash_taxonomy() -> None:
    row = classify_failure_taxonomy(
        candidate_id="c1",
        postprocess_stage="raw_generated",
        num_severe_clash_pairs=2,
        attribution_failure_type="multi_region_clash",
    )
    assert row["failure_taxonomy"] == "multi_region_clash"


def test_scaffold_clash_taxonomy() -> None:
    row = classify_failure_taxonomy(
        candidate_id="c1",
        postprocess_stage="raw_generated",
        num_severe_clash_pairs=1,
        attribution_failure_type="scaffold_clash",
    )
    assert row["failure_taxonomy"] == "scaffold_clash"


def test_global_pose_failure_taxonomy() -> None:
    row = classify_failure_taxonomy(
        candidate_id="c1",
        postprocess_stage="raw_generated",
        num_severe_clash_pairs=1,
        max_clash_depth=2.0,
    )
    assert row["failure_taxonomy"] == "global_pose_failure"
