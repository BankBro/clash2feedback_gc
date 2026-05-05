from pathlib import Path

from clash2feedback.io.read_complex import find_raw_complexes, read_raw_complex_dir
from clash2feedback.utils.config import load_yaml_config


def test_phase0_config_loads() -> None:
    config = load_yaml_config("configs/phase0.yaml")
    assert config["processed_version"] == "v0_1"
    assert config["paths"]["raw_root"] == "data/raw_complexes"
    assert config["split"]["seed"] == 20260504


def test_read_raw_complex_dir_with_metadata(tmp_path: Path) -> None:
    complex_dir = tmp_path / "complex_000001"
    complex_dir.mkdir()
    (complex_dir / "protein.pdb").write_text("HEADER test\n", encoding="utf-8")
    (complex_dir / "ligand.sdf").write_text("", encoding="utf-8")
    (complex_dir / "metadata.json").write_text(
        '{"complex_id":"complex_000001","source":"unit","uniprot_id":"P00001"}',
        encoding="utf-8",
    )

    raw = read_raw_complex_dir(complex_dir)

    assert raw is not None
    assert raw.complex_id == "complex_000001"
    assert raw.protein_path.name == "protein.pdb"
    assert raw.metadata["split_group"] == "complex_000001"


def test_find_raw_complexes_skips_empty_dirs(tmp_path: Path) -> None:
    (tmp_path / "empty").mkdir()
    complex_dir = tmp_path / "complex_000002"
    complex_dir.mkdir()
    (complex_dir / "protein.cif").write_text("data_test\n", encoding="utf-8")
    (complex_dir / "ligand.sdf").write_text("", encoding="utf-8")

    complexes = find_raw_complexes(tmp_path)

    assert [item.complex_id for item in complexes] == ["complex_000002"]
