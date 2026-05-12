from pathlib import Path

from clash2feedback.generation_audit.overlap import (
    OfficialSplitNames,
    audit_decision,
    classify_overlap_tier,
    diffsbdd_split_status,
    load_project_split_map,
)


def test_overlap_tier_exact_pair_seen() -> None:
    tier = classify_overlap_tier(
        source_dataset="crossdocked_subset",
        diffsbdd_split_status="official_train_exact_pair",
        exact_pair_overlap=True,
        protein_file_overlap=False,
        ligand_file_overlap=False,
        same_target_overlap=False,
        same_pocket_overlap=False,
        official_split_available=True,
    )
    assert tier == "T0_exact_pair_seen"
    assert audit_decision(tier) == "same_source_smoke_only"


def test_overlap_tier_unknown_when_no_split_available() -> None:
    official = OfficialSplitNames(train=set(), val=set(), test=set())
    status = diffsbdd_split_status("target/a.sdf", "target/a.sdf", "target/a_pocket10.pdb", official)
    tier = classify_overlap_tier(
        source_dataset="crossdocked_subset",
        diffsbdd_split_status=status,
        exact_pair_overlap=False,
        protein_file_overlap=False,
        ligand_file_overlap=False,
        same_target_overlap=False,
        same_pocket_overlap=False,
        official_split_available=official.available,
    )
    assert status == "official_split_unavailable"
    assert tier == "T_unknown"


def test_t0_t1_not_external_validity_eligible() -> None:
    assert audit_decision("T0_exact_pair_seen") == "same_source_smoke_only"
    assert audit_decision("T1_same_pocket_or_target_seen") == "same_source_debug_only"


def test_official_test_external_validity_eligible() -> None:
    official = OfficialSplitNames(train=set(), val=set(), test={"target/a.sdf"})
    status = diffsbdd_split_status("target/a.sdf", "target/a.sdf", "target/a_pocket10.pdb", official)
    tier = classify_overlap_tier(
        source_dataset="crossdocked_subset",
        diffsbdd_split_status=status,
        exact_pair_overlap=False,
        protein_file_overlap=False,
        ligand_file_overlap=False,
        same_target_overlap=False,
        same_pocket_overlap=False,
        official_split_available=official.available,
    )
    assert status == "official_test_exact_pair"
    assert tier == "T3_official_diffsbdd_test"


def test_project_split_map_reads_standard_files(tmp_path: Path) -> None:
    (tmp_path / "train.txt").write_text("a\n", encoding="utf-8")
    (tmp_path / "val.txt").write_text("b\n", encoding="utf-8")
    (tmp_path / "test.txt").write_text("c\n", encoding="utf-8")
    assert load_project_split_map(tmp_path) == {"a": "train", "b": "val", "c": "test"}
