from __future__ import annotations

import numpy as np
import pytest

from clash2feedback.data.phase2_visual_qc import (
    DISPLACEMENT_AXIS_MAX_ANGLE_DEGREES,
    DISPLACEMENT_AXIS_MIN_ANGLE_DEGREES,
    TargetDisplacementCameraGeometry,
    _displacement_axis_angle_degrees,
    _phase2_camera_filter,
    _prepare_phase2_camera_views,
    _task_images_exist,
    _view_frame_spec,
    _view_legend_items,
    _view_commands,
    _write_severe_clashes_bild,
    write_phase2_visual_qc_category_index,
)
from clash2feedback.data.render_visual_check import CameraView


def _camera(label: str, direction: tuple[float, float, float]) -> CameraView:
    return CameraView(
        label=label,
        focus=(0.0, 0.0, 0.0),
        direction=direction,
        score=1.0,
        ligand_occluded_fraction=0.0,
        center_line_blocked=False,
        projection_area_score=1.0,
    )


def test_displacement_axis_angle_uses_undirected_line_angle() -> None:
    axis = np.asarray([1.0, 0.0, 0.0])

    assert _displacement_axis_angle_degrees((0.0, 1.0, 0.0), axis) == pytest.approx(90.0)
    assert _displacement_axis_angle_degrees((1.0, 0.0, 0.0), axis) == pytest.approx(0.0)
    assert _displacement_axis_angle_degrees((-1.0, 0.0, 0.0), axis) == pytest.approx(0.0)


def test_phase2_camera_preparation_filters_and_retargets_to_displacement_midpoint() -> None:
    geometry = TargetDisplacementCameraGeometry(
        focus=np.asarray([1.0, 2.0, 3.0]),
        axis=np.asarray([1.0, 0.0, 0.0]),
    )
    cameras = [
        _camera("candidate_1", (1.0, 0.0, 0.0)),
        _camera("candidate_2", (0.5, 0.8660254, 0.0)),
        _camera("candidate_3", (0.0, 1.0, 0.0)),
    ]

    prepared = _prepare_phase2_camera_views(cameras, geometry, num_views=2)

    assert [camera.label for camera in prepared] == ["clear_01", "clear_02"]
    assert [camera.focus for camera in prepared] == [(1.0, 2.0, 3.0), (1.0, 2.0, 3.0)]
    assert all(
        DISPLACEMENT_AXIS_MIN_ANGLE_DEGREES
        <= _displacement_axis_angle_degrees(camera.direction, geometry.axis)
        <= DISPLACEMENT_AXIS_MAX_ANGLE_DEGREES
        for camera in prepared
    )


def test_phase2_camera_filter_enforces_displacement_axis_angle_gate_before_selection() -> None:
    geometry = TargetDisplacementCameraGeometry(
        focus=np.asarray([0.0, 0.0, 0.0]),
        axis=np.asarray([1.0, 0.0, 0.0]),
    )
    camera_filter = _phase2_camera_filter(geometry)

    assert camera_filter is not None
    assert camera_filter(_camera("perpendicular", (0.0, 1.0, 0.0))) is True
    assert camera_filter(_camera("thirty_degrees", (0.8660254, 0.5, 0.0))) is True
    assert camera_filter(_camera("too_axis_aligned", (1.0, 0.0, 0.0))) is False


def test_overlay_surface_adds_original_and_failed_target_atom_markers() -> None:
    commands = _view_commands("overlay_surface")

    assert "open target_original_atoms.pdb" in commands
    assert "open target_failed_atoms.pdb" in commands
    assert "open surface_clash_spots.bild" in commands
    assert "style #4 sphere" in commands
    assert "style #5 sphere" in commands
    assert "size #4 atomRadius 0.24" in commands
    assert "size #5 atomRadius 0.28" in commands
    assert "color #4 purple" in commands
    assert "color #5 cyan" in commands


def test_view_commands_use_consistent_target_failed_and_clash_colors() -> None:
    assert "color #5 cyan" in _view_commands("ligand_delta")
    assert "color #6 cyan" in _view_commands("overlay_sticks")
    assert "color #5 cyan" in _view_commands("overlay_surface")

    clash_pair_commands = _view_commands("clash_pair_vdw")
    assert "color #3 royalblue" in clash_pair_commands
    assert "color #4 red" in clash_pair_commands
    assert "color #5 black" in clash_pair_commands


def test_clash_pair_view_falls_back_when_top_pair_is_unavailable(tmp_path) -> None:
    (tmp_path / "top_clash_pair_metadata.json").write_text('{"available": false}\n', encoding="utf-8")

    commands = _view_commands("clash_pair_vdw", tmp_path)

    assert "open protein_pocket.pdb" in commands
    assert "open failed_ligand.sdf" in commands
    assert "open top_clash_protein_vdw_atom.pdb" not in commands
    assert "open top_clash_ligand_vdw_atom.pdb" not in commands
    assert _view_frame_spec("clash_pair_vdw", tmp_path) == "#1-2"
    assert _view_legend_items("clash_pair_vdw", case_dir=tmp_path) == [
        ("蛋白口袋背景", (135, 135, 135)),
        ("失败构象配体背景", (230, 155, 0)),
        ("无可用碰撞原子对, 仅显示背景", (70, 70, 70)),
    ]


def test_severe_clash_bild_distinguishes_ligand_protein_and_center_line(tmp_path) -> None:
    case = {
        "failed_ligand_coords": np.asarray([[1.0, 2.0, 3.0]], dtype=float),
        "clash_report": {
            "clash_pairs": [
                {
                    "is_severe": True,
                    "ligand_atom_idx": 0,
                    "protein_atom_idx": 0,
                    "protein_atom_position": 0,
                }
            ]
        },
    }
    base = {"protein": {"coords": np.asarray([[4.0, 5.0, 6.0]], dtype=float)}}
    output_path = tmp_path / "severe_clashes.bild"

    _write_severe_clashes_bild(case, base, output_path)

    text = output_path.read_text(encoding="utf-8")
    assert ".color red" in text
    assert ".color 0.25 0.45 1.0" in text
    assert ".color 0.28 0.28 0.28" in text
    assert ".sphere 1.000 2.000 3.000 0.36" in text
    assert ".sphere 4.000 5.000 6.000 0.30" in text
    assert ".cylinder 1.000 2.000 3.000 4.000 5.000 6.000 0.055" in text


def test_visual_qc_category_index_uses_symlinks_without_moving_cases(tmp_path) -> None:
    import pandas as pd

    output_root = tmp_path / "runs" / "phase2_visual_qc"
    report_root = tmp_path / "reports" / "phase2_visual_qc"
    (output_root / "case_000001").mkdir(parents=True)
    (output_root / "case_000002").mkdir(parents=True)
    assets = pd.DataFrame(
        [
            {"case_id": "case_000001", "oracle_split": "supported_single_rgroup", "injection_mode": "torsion_perturb"},
            {"case_id": "case_000002", "oracle_split": "near_miss_contact", "injection_mode": "easy_rotation"},
        ]
    )

    index = write_phase2_visual_qc_category_index(
        asset_manifest=assets,
        output_root=output_root,
        report_root=report_root,
    )

    assert (report_root / "by_category_index.csv").exists()
    assert len(index) == 2
    by_split = output_root / "by_oracle_split" / "supported_single_rgroup" / "case_000001"
    by_mode = output_root / "by_injection_mode" / "torsion_perturb" / "case_000001"
    by_matrix = output_root / "by_oracle_split_and_mode" / "supported_single_rgroup" / "torsion_perturb" / "case_000001"
    assert by_split.is_symlink()
    assert by_mode.is_symlink()
    assert by_matrix.is_symlink()
    assert by_split.resolve() == (output_root / "case_000001").resolve()


def test_task_images_exist_requires_all_expected_nonempty_images(tmp_path) -> None:
    from clash2feedback.data.phase2_visual_qc import Phase2RenderTask

    case_dir = tmp_path / "case_000001"
    images_dir = case_dir / "images"
    images_dir.mkdir(parents=True)
    task = Phase2RenderTask(
        case_id="case_000001",
        view="ligand_delta",
        case_dir=case_dir,
        script_path=case_dir / "scripts" / "ligand_delta.cxc",
        cameras=(_camera("clear_01", (0.0, 1.0, 0.0)), _camera("clear_02", (0.0, 0.0, 1.0))),
        candidate_directions=1024,
    )

    (images_dir / "ligand_delta_clear_01.png").write_bytes(b"image")

    assert _task_images_exist(task) is False

    (images_dir / "ligand_delta_clear_02.png").write_bytes(b"image")

    assert _task_images_exist(task) is True
