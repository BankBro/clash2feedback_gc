from __future__ import annotations

from pathlib import Path

import pandas as pd

from clash2feedback.data.visual_check_assets import (
    generate_visual_check_assets,
    select_visual_check_samples,
    visual_check_notes_markdown,
)


def test_select_visual_check_samples_prefers_high_priority() -> None:
    visual = pd.DataFrame(
        {
            "sample_id": ["sample_low", "sample_high", "sample_medium"],
            "complex_id": ["sample_low", "sample_high", "sample_medium"],
            "processed_path": ["a.pkl", "b.pkl", "c.pkl"],
            "recommended_check_priority": ["low", "high", "medium"],
            "manual_check_status": ["unchecked", "unchecked", "unchecked"],
        }
    )
    manifest = pd.DataFrame(
        {
            "sample_id": ["sample_low", "sample_high", "sample_medium"],
            "target_id": ["target_l", "target_h", "target_m"],
            "phase0_usable": [True, True, True],
        }
    )

    selected = select_visual_check_samples(visual, manifest, num_samples=2)

    assert selected["sample_id"].tolist() == ["sample_high", "sample_medium"]
    assert selected.loc[0, "target_id"] == "target_h"


def test_visual_check_notes_are_conservative() -> None:
    assets = pd.DataFrame(
        {
            "complex_id": ["complex_1"],
            "target_id": ["target_1"],
            "asset_dir": ["runs/phase0_visual_check/complex_1"],
            "projection_status": ["projection_png_generated"],
        }
    )

    markdown = visual_check_notes_markdown(assets)

    assert "requires_human_review: 1" in markdown
    assert "pass: 0" in markdown
    assert "complex_1" in markdown


def test_generate_visual_check_assets_copies_structures_and_uses_relative_paths(tmp_path: Path) -> None:
    protein = tmp_path / "source_protein.pdb"
    ligand = tmp_path / "source_ligand.sdf"
    protein.write_text("HEADER test\n", encoding="utf-8")
    ligand.write_text("ligand\n$$$$\n", encoding="utf-8")
    visual = pd.DataFrame(
        {
            "sample_id": ["complex_1"],
            "complex_id": ["complex_1"],
            "protein_path": [str(protein)],
            "ligand_path": [str(ligand)],
            "processed_path": [str(tmp_path / "missing.pkl")],
            "recommended_check_priority": ["high"],
            "manual_check_status": ["unchecked"],
        }
    )
    manifest = pd.DataFrame({"sample_id": ["complex_1"], "target_id": ["target_1"]})

    generate_visual_check_assets(
        visual,
        manifest,
        output_root=tmp_path / "assets",
        notes_path=tmp_path / "notes.md",
        num_samples=1,
    )

    sample_dir = tmp_path / "assets" / "complex_1"
    assert (sample_dir / "protein.pdb").exists()
    assert (sample_dir / "ligand.sdf").exists()
    cxc = (sample_dir / "view.cxc").read_text(encoding="utf-8")
    assert "open protein.pdb" in cxc
    assert "open ligand.sdf" in cxc
    assert str(protein) not in cxc
