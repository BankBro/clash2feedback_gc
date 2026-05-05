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
        "paths": {"processed_path": str(processed_path)},
        "metadata": {},
        "protein": {
            "num_atoms": 2,
            "coords": np.asarray([[0, 0, 0], [1, 0, 0]], dtype=np.float32),
        },
        "ligand": {
            "num_atoms": 2,
            "coords": np.asarray([[0, 1, 0], [1, 1, 0]], dtype=np.float32),
        },
        "pocket": {"coords": np.asarray([[0, 0, 0]], dtype=np.float32)},
        "scaffold": {"success": True},
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
