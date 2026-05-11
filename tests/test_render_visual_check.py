from __future__ import annotations

from pathlib import Path

import numpy as np

from clash2feedback.data.render_visual_check import (
    DEFAULT_CONTACT_SHEET_COLUMNS,
    DEFAULT_CONTACT_SHEET_ROWS,
    DEFAULT_NUM_CLEAR_VIEWS,
    DEFAULT_VIEWS,
    RenderResult,
    _dedupe_directions,
    build_render_tasks,
    render_visual_check_images,
    select_clear_camera_views,
    write_batch_review_markdown,
    write_render_contact_sheets,
    write_render_manifest,
)


def _make_visual_package(root: Path, sample_id: str = "complex_1") -> Path:
    sample_dir = root / sample_id
    sample_dir.mkdir(parents=True)
    ligand_sdf = """ligand
  test

  4  3  0  0  0  0            999 V2000
    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    1.4000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    0.0000    1.2000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
    1.4000    1.2000    0.1000 N   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  1  0
  1  3  1  0
  2  4  1  0
M  END
$$$$
"""
    protein_pdb = "\n".join(
        [
            "ATOM      1  CA  ALA A   1      -5.000   0.000   0.000  1.00 20.00           C",
            "ATOM      2  CB  ALA A   1      -4.000   1.000   0.000  1.00 20.00           C",
            "ATOM      3  O   ALA A   1      -3.500  -1.000   0.000  1.00 20.00           O",
            "END",
            "",
        ]
    )
    ligand_pdb = "\n".join(
        [
            "HETATM    1  C1  LIG A   1       0.000   0.000   0.000  1.00 20.00           C",
            "HETATM    2  C2  LIG A   1       1.400   0.000   0.000  1.00 20.00           C",
            "END",
            "",
        ]
    )
    (sample_dir / "ligand.sdf").write_text(ligand_sdf, encoding="utf-8")
    (sample_dir / "protein.pdb").write_text(protein_pdb, encoding="utf-8")
    (sample_dir / "protein_pocket_vdw_atoms.pdb").write_text(protein_pdb, encoding="utf-8")
    (sample_dir / "ligand_vdw_atoms.pdb").write_text(ligand_pdb, encoding="utf-8")
    (sample_dir / "close_contacts.bild").write_text(".color red\n", encoding="utf-8")
    (sample_dir / "scaffold_atoms.pdb").write_text(ligand_pdb, encoding="utf-8")
    (sample_dir / "valid_rgroup_atoms.pdb").write_text(ligand_pdb, encoding="utf-8")
    (sample_dir / "valid_anchors.bild").write_text(".sphere 1.4 0.0 0.0 0.3\n", encoding="utf-8")
    return sample_dir


def test_build_render_tasks_uses_default_clear_views(tmp_path: Path) -> None:
    _make_visual_package(tmp_path)

    tasks = build_render_tasks(tmp_path)

    assert len(tasks) == len(DEFAULT_VIEWS) * DEFAULT_NUM_CLEAR_VIEWS
    assert {task.view for task in tasks} == set(DEFAULT_VIEWS)
    assert {task.angle for task in tasks} == {f"clear_{idx:02d}" for idx in range(1, DEFAULT_NUM_CLEAR_VIEWS + 1)}
    assert all(task.camera_view is not None for task in tasks)
    assert all(task.script_path.parent.name == "headless_scripts" for task in tasks)
    assert all(task.image_path.parent.name == "images" for task in tasks)


def test_clear_views_are_selected_per_view_type(tmp_path: Path) -> None:
    _make_visual_package(tmp_path)

    tasks = build_render_tasks(tmp_path, views=["clash", "rgroup"], num_clear_views=1, candidate_directions=64)

    by_view = {task.view: task for task in tasks}
    clash_camera = by_view["clash"].camera_view
    rgroup_camera = by_view["rgroup"].camera_view
    assert clash_camera is not None
    assert rgroup_camera is not None
    assert clash_camera.focus != rgroup_camera.focus


def test_antipodal_camera_directions_are_not_deduped() -> None:
    directions = _dedupe_directions(
        [
            np.asarray([1.0, 0.0, 0.0]),
            np.asarray([-1.0, 0.0, 0.0]),
            np.asarray([1.0, 0.001, 0.0]),
        ]
    )

    assert len(directions) == 2
    assert any(float(np.dot(direction, np.asarray([-1.0, 0.0, 0.0]))) > 0.99 for direction in directions)


def test_clear_view_selection_prefers_unblocked_pocket_side(tmp_path: Path) -> None:
    sample_dir = _make_visual_package(tmp_path)
    blocking_protein = "\n".join(
        [
            "ATOM      1  CA  ALA A   1       2.200   0.600   0.025  1.00 20.00           C",
            "END",
            "",
        ]
    )
    (sample_dir / "protein.pdb").write_text(blocking_protein, encoding="utf-8")
    (sample_dir / "protein_pocket_vdw_atoms.pdb").write_text(blocking_protein, encoding="utf-8")

    camera = select_clear_camera_views(sample_dir, view="overview", num_views=1, num_candidates=128)[0]

    assert camera.center_line_blocked is False
    assert camera.selection_tier in {"strict", "relaxed"}
    assert float(np.dot(np.asarray(camera.direction), np.asarray([1.0, 0.0, 0.0]))) < 0.4


def test_clear_view_selection_applies_candidate_filter_before_diverse_pick(tmp_path: Path) -> None:
    sample_dir = _make_visual_package(tmp_path)

    cameras = select_clear_camera_views(
        sample_dir,
        view="overview",
        num_views=3,
        num_candidates=128,
        camera_filter=lambda camera: camera.direction[0] < -0.2,
    )

    assert len(cameras) == 3
    assert all(camera.direction[0] < -0.2 for camera in cameras)


def test_render_visual_check_images_dry_run_writes_clear_view_scripts(tmp_path: Path) -> None:
    sample_dir = _make_visual_package(tmp_path)
    tasks = build_render_tasks(tmp_path, views=["clash"], num_clear_views=2, candidate_directions=64)

    results = render_visual_check_images(tasks, dry_run=True)

    assert [row.status for row in results] == ["script_written", "script_written"]
    clash_script = sample_dir / "headless_scripts" / "clash_clear_01.cxc"
    group_script = sample_dir / "headless_scripts" / "clash_clear_01_clear_02.cxc"
    content = clash_script.read_text(encoding="utf-8")
    assert "open protein.pdb" in content
    assert "open ligand_vdw_atoms.pdb" in content
    assert "graphics silhouettes true width 1.5 depthJump 0.01" in content
    assert "transparency #1 70 target a" in content
    assert "transparency #3 45 target a" in content
    assert "color #4 royalblue" in content
    assert "transparency #4 25 target a" in content
    assert "camera ortho" not in content
    assert "ui tool show" not in content
    assert "define axis fromPoint" in content
    assert "view #2 clip false pad 0.45 zalign #" in content
    assert "save images/clash_clear_01.png" in content
    group_content = group_script.read_text(encoding="utf-8")
    assert "Headless ChimeraX grouped render" in group_content
    assert "save images/clash_clear_01.png" in group_content
    assert "save images/clash_clear_02.png" in group_content
    assert all(row.camera_score is not None for row in results)
    assert all(row.camera_selection_tier for row in results)


def test_rgroup_clear_view_uses_extra_transparent_protein_context(tmp_path: Path) -> None:
    sample_dir = _make_visual_package(tmp_path)
    tasks = build_render_tasks(tmp_path, views=["rgroup"], num_clear_views=1, candidate_directions=64)

    render_visual_check_images(tasks, dry_run=True)

    content = (sample_dir / "headless_scripts" / "rgroup_clear_01.cxc").read_text(encoding="utf-8")
    assert "surface #1" in content
    assert "transparency #1 97 target s" in content
    assert "open valid_anchors.bild" in content
    assert "size #3 atomRadius 0.35" in content
    assert "size #4 atomRadius 0.35" in content


def test_fixed_angle_mode_is_still_available(tmp_path: Path) -> None:
    sample_dir = _make_visual_package(tmp_path)
    tasks = build_render_tasks(tmp_path, views=["clash"], angles=["front", "back"], camera_mode="fixed-angles")

    render_visual_check_images(tasks, dry_run=True)

    assert {task.angle for task in tasks} == {"front", "back"}
    assert all(task.camera_view is None for task in tasks)
    assert "define plane #2 id #90" in (sample_dir / "headless_scripts" / "clash_front.cxc").read_text(encoding="utf-8")
    assert "turn y 180 center #2" in (sample_dir / "headless_scripts" / "clash_back.cxc").read_text(encoding="utf-8")


def test_write_render_manifest_and_summary(tmp_path: Path) -> None:
    _make_visual_package(tmp_path)
    tasks = build_render_tasks(tmp_path, views=["overview"], num_clear_views=1, candidate_directions=32)
    results = render_visual_check_images(tasks, dry_run=True)
    manifest = tmp_path / "render_manifest.csv"
    summary = tmp_path / "summary.md"

    write_render_manifest(results, manifest)
    write_batch_review_markdown(results, summary, assets_root=tmp_path)

    manifest_text = manifest.read_text(encoding="utf-8")
    assert "sample_id,view,angle" in manifest_text
    assert "image_rotation_degrees" in manifest_text
    assert "image_orientation_status" in manifest_text
    assert "camera_selection_tier" in manifest_text
    assert "interest_occluded_fraction" in manifest_text
    text = summary.read_text(encoding="utf-8")
    assert "阶段 0 ChimeraX 批量出图初筛记录" in text
    assert "overview" in text
    assert "clear_01" in text


def test_write_render_contact_sheets_uses_three_by_four_layout(tmp_path: Path) -> None:
    from PIL import Image

    image_dir = tmp_path / "complex_1" / "images"
    image_dir.mkdir(parents=True)
    results: list[RenderResult] = []
    for idx in range(1, DEFAULT_CONTACT_SHEET_ROWS * DEFAULT_CONTACT_SHEET_COLUMNS + 1):
        image_path = image_dir / f"clash_clear_{idx:02d}.png"
        Image.new("RGB", (120, 80), (idx * 10 % 255, 80, 180)).save(image_path)
        results.append(
            RenderResult(
                sample_id="complex_1",
                view="clash",
                angle=f"clear_{idx:02d}",
                script_path=f"headless_scripts/clash_clear_{idx:02d}.cxc",
                image_path=str(image_path),
                status="rendered",
            )
        )

    sheets = write_render_contact_sheets(results)

    assert len(sheets) == 1
    assert sheets[0].status == "written"
    assert sheets[0].num_images == 12
    assert sheets[0].rows == 3
    assert sheets[0].columns == 4
    sheet_path = image_dir / "clash_contact_sheet.png"
    assert sheet_path.exists()
    with Image.open(sheet_path) as sheet:
        assert sheet.width >= DEFAULT_CONTACT_SHEET_COLUMNS * 120
        assert sheet.height >= DEFAULT_CONTACT_SHEET_ROWS * 80
