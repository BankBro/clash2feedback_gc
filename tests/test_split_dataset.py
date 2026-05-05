import pandas as pd

from clash2feedback.data.split_dataset import make_grouped_splits, make_splits_from_manifest, resolve_split_groups


def test_resolve_split_groups_prefers_uniprot() -> None:
    manifest = pd.DataFrame(
        {
            "sample_id": ["c1", "c2"],
            "complex_id": ["c1", "c2"],
            "uniprot_id": ["P1", "P1"],
            "target_id": ["T1", "T2"],
        }
    )
    resolved, strategy = resolve_split_groups(manifest)
    assert strategy == "target_level"
    assert resolved["split_group_resolved"].tolist() == ["P1", "P1"]
    assert resolved["split_group_source"].tolist() == ["uniprot_id", "uniprot_id"]


def test_resolve_split_groups_falls_back_to_complex_smoke() -> None:
    manifest = pd.DataFrame({"sample_id": ["c1"], "complex_id": ["c1"]})
    resolved, strategy = resolve_split_groups(manifest)
    assert strategy == "complex_level_smoke"
    assert resolved.loc[0, "split_group_resolved"] == "c1"


def test_make_grouped_splits_keeps_group_together() -> None:
    manifest = pd.DataFrame(
        {
            "sample_id": ["a1", "a2", "b1", "c1"],
            "split_group_resolved": ["A", "A", "B", "C"],
        }
    )
    splits = make_grouped_splits(manifest, ratios=(0.5, 0.25, 0.25), seed=7)
    sample_to_split = {
        sample_id: split_name
        for split_name, sample_ids in splits.items()
        for sample_id in sample_ids
    }
    assert sample_to_split["a1"] == sample_to_split["a2"]
    assert sorted(sample_to_split) == ["a1", "a2", "b1", "c1"]


def test_make_splits_from_empty_manifest_writes_empty_files(tmp_path) -> None:
    manifest_path = tmp_path / "manifest.parquet"
    pd.DataFrame(columns=["sample_id", "complex_id"]).to_parquet(manifest_path, index=False)

    report = make_splits_from_manifest(manifest_path, tmp_path / "splits", {"split": {"seed": 1}})

    assert report.empty
    assert (tmp_path / "splits" / "train.txt").read_text(encoding="utf-8") == ""
    assert (tmp_path / "splits" / "split_report.csv").exists()
