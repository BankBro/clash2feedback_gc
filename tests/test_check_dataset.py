import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from clash2feedback.data.check_dataset import check_processed_dataset, check_processed_sample


def _sample(processed_path: Path) -> dict:
    return {
        "schema_version": "0.1",
        "sample_id": "complex_000001",
        "complex_id": "complex_000001",
        "source": "unit",
        "paths": {
            "processed_path": str(processed_path),
            "raw_protein_path": "protein.pdb",
            "raw_ligand_path": "ligand.sdf",
        },
        "metadata": {"split_group": "target_a", "split_group_source": "target_id"},
        "protein": {
            "num_atoms": 2,
            "coords": np.asarray([[0, 0, 0], [1, 0, 0]], dtype=np.float32),
        },
        "ligand": {
            "num_atoms": 2,
            "coords": np.asarray([[0, 1, 0], [1, 1, 0]], dtype=np.float32),
        },
        "pocket": {
            "coords": np.asarray([[0, 0, 0]], dtype=np.float32),
            "num_atoms_6A": 1,
            "num_atoms_8A": 1,
        },
        "scaffold": {"success": True, "num_atoms": 1},
        "rgroups": [{"rgroup_id": "R1"}, {"rgroup_id": "R2"}],
        "masks": {
            "ligand_scaffold_mask": np.asarray([True, False]),
            "ligand_is_rgroup": np.asarray([False, True]),
            "heavy_atom_mask": np.asarray([True, True]),
            "pocket_atom_mask": np.asarray([True, False]),
        },
        "sanity": {
            "valid_ligand": True,
            "pocket_nonempty": True,
            "scaffold_success": True,
            "num_valid_rgroups": 2,
            "num_single_anchor_rgroups": 2,
            "min_ligand_protein_distance": 1.7,
            "num_obvious_clash_pairs": 0,
            "num_pairs_below_1_0": 0,
            "num_pairs_below_1_2": 0,
            "num_pairs_below_1_5": 0,
            "basic_clash_screen_pass": True,
        },
        "software_versions": {},
    }


def test_check_processed_sample_accepts_minimal_valid_sample(tmp_path: Path) -> None:
    sample_path = tmp_path / "complex_000001.pkl"
    with sample_path.open("wb") as f:
        pickle.dump(_sample(sample_path), f)

    row = check_processed_sample(sample_path)

    assert row["load_ok"] is True
    assert row["phase0_usable"] is True
    assert row["num_pocket_atoms_8A"] == 1
    assert row["errors"] == ""


def test_check_processed_dataset_writes_reports(tmp_path: Path) -> None:
    processed_root = tmp_path / "processed" / "v0_1"
    complexes_dir = processed_root / "complexes"
    complexes_dir.mkdir(parents=True)
    sample_path = complexes_dir / "complex_000001.pkl"
    with sample_path.open("wb") as f:
        pickle.dump(_sample(sample_path), f)
    manifest = pd.DataFrame(
        {
            "sample_id": ["complex_000001"],
            "complex_id": ["complex_000001"],
            "processed_path": [str(sample_path)],
            "protein_path": ["protein.pdb"],
            "ligand_path": ["ligand.sdf"],
        }
    )
    manifest_path = processed_root / "manifest.parquet"
    manifest.to_parquet(manifest_path, index=False)

    result = check_processed_dataset(processed_root, manifest_path, tmp_path / "reports")

    assert len(result["dataset_check"]) == 1
    assert (tmp_path / "reports" / "summary.json").exists()
    assert (tmp_path / "reports" / "visual_check_list.csv").exists()
    assert (tmp_path / "reports" / "threshold_calibration.csv").exists()
    assert (tmp_path / "reports" / "failure_reason_counts.csv").exists()
    assert result["threshold_calibration"].loc[0, "split_group_source"] == "target_id"
