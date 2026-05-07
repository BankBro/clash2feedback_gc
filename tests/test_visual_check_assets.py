from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
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
    assert (sample_dir / "scaffold_atoms.pdb").exists()
    assert (sample_dir / "valid_rgroup_atoms.pdb").exists()
    assert (sample_dir / "valid_anchors.bild").exists()
    assert (sample_dir / "protein_pocket_vdw_atoms.pdb").exists()
    assert (sample_dir / "ligand_vdw_atoms.pdb").exists()
    assert (sample_dir / "close_contacts.bild").exists()
    assert (sample_dir / "view_overview.cxc").exists()
    assert (sample_dir / "view_clash.cxc").exists()
    assert (sample_dir / "view_rgroup.cxc").exists()
    assert (sample_dir / "view_ligand.cxc").exists()
    assert (sample_dir / "README.md").exists()
    cxc = (sample_dir / "view.cxc").read_text(encoding="utf-8")
    assert "open protein.pdb" in cxc
    assert "open ligand.sdf" in cxc
    assert str(protein) not in cxc
    rgroup_cxc = (sample_dir / "view_rgroup.cxc").read_text(encoding="utf-8")
    assert "open scaffold_atoms.pdb" in rgroup_cxc
    assert "open valid_rgroup_atoms.pdb" in rgroup_cxc
    assert "open valid_anchors.bild" in rgroup_cxc
    assert "transparency #1 97 target s" in rgroup_cxc
    assert "size #3 atomRadius 0.35" in rgroup_cxc
    clash_cxc = (sample_dir / "view_clash.cxc").read_text(encoding="utf-8")
    assert "camera ortho" in clash_cxc
    assert "camera orthographic" not in clash_cxc
    assert 'ui tool show "Side View"' in clash_cxc
    assert "\nview\n" in clash_cxc
    assert "view #2" not in clash_cxc
    assert "open protein_pocket_vdw_atoms.pdb" in clash_cxc
    assert "open ligand_vdw_atoms.pdb" in clash_cxc
    assert "open close_contacts.bild" in clash_cxc
    assert "style #3 sphere" in clash_cxc
    assert "graphics silhouettes true width 1.5 depthJump 0.01" in clash_cxc
    assert "transparency #1 70 target a" in clash_cxc
    assert "transparency #3 45 target a" in clash_cxc
    assert "color #4 royalblue" in clash_cxc
    assert "transparency #4 25 target a" in clash_cxc
    ligand_cxc = (sample_dir / "view_ligand.cxc").read_text(encoding="utf-8")
    assert "open ligand.sdf" in ligand_cxc
    assert "open scaffold_atoms.pdb" in ligand_cxc


def test_generate_visual_check_assets_writes_vdw_and_contact_markers(tmp_path: Path) -> None:
    protein = tmp_path / "source_protein.pdb"
    ligand = tmp_path / "source_ligand.sdf"
    processed = tmp_path / "sample.pkl"
    protein.write_text("HEADER test\n", encoding="utf-8")
    ligand.write_text("ligand\n$$$$\n", encoding="utf-8")
    sample = {
        "sample_id": "complex_contact",
        "ligand": {
            "coords": np.asarray([[0.0, 0.0, 0.0], [1.5, 0.0, 0.0], [5.0, 0.0, 0.0]]),
            "elements": ["C", "O", "H"],
        },
        "pocket": {
            "coords": np.asarray([[0.9, 0.0, 0.0], [4.5, 0.0, 0.0]]),
            "elements": ["N", "C"],
        },
        "scaffold": {"atom_indices": [0]},
        "rgroups": [
            {
                "is_valid_for_phase0": True,
                "heavy_atom_indices": [1],
                "anchor_scaffold_atom_idx": 0,
                "anchor_rgroup_atom_idx": 1,
            }
        ],
    }
    with processed.open("wb") as f:
        pickle.dump(sample, f)
    visual = pd.DataFrame(
        {
            "sample_id": ["complex_contact"],
            "complex_id": ["complex_contact"],
            "protein_path": [str(protein)],
            "ligand_path": [str(ligand)],
            "processed_path": [str(processed)],
            "recommended_check_priority": ["high"],
            "manual_check_status": ["unchecked"],
        }
    )
    manifest = pd.DataFrame({"sample_id": ["complex_contact"], "target_id": ["target_1"]})

    assets = generate_visual_check_assets(
        visual,
        manifest,
        output_root=tmp_path / "assets",
        notes_path=tmp_path / "notes.md",
        num_samples=1,
    )

    sample_dir = tmp_path / "assets" / "complex_contact"
    assert "visual_close_contacts=2" in str(assets.loc[0, "marker_status"])
    assert " H" not in (sample_dir / "ligand_vdw_atoms.pdb").read_text(encoding="utf-8")
    assert ".cylinder" in (sample_dir / "close_contacts.bild").read_text(encoding="utf-8")
