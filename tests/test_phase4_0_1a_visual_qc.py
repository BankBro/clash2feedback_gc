from __future__ import annotations

from pathlib import Path

import pandas as pd

from clash2feedback.repair.reconnect_visual_qc import (
    VISUAL_QC_VIEWS,
    _camera_quality_for_group,
    _view_commands,
    select_visual_qc_cases,
)


def _candidate_file(tmp_path: Path, name: str) -> str:
    path = tmp_path / f"{name}.sdf"
    path.write_text("mock\n", encoding="utf-8")
    return str(path)


def _diff_row(tmp_path: Path, idx: int, *, category: str, reason: str, reliable: bool, strict: bool, budget: int, extra: int = 0) -> dict:
    return {
        "case_id": f"case_{idx:06d}",
        "base_sample_id": f"complex_{idx:06d}",
        "candidate_id": f"diff:{idx:03d}",
        "candidate_path": _candidate_file(tmp_path, f"diff_{idx:03d}"),
        "candidate_budget_k": budget,
        "source_group": "diffsbdd_candidates",
        "candidate_readable": True,
        "ligand_valid": True,
        "generated_fragment_heavy_atom_count": 3,
        "reliable_repair_success": reliable,
        "strict_single_anchor_shadow_reliable": strict,
        "reconnect_category": category,
        "reconnect_category_reason": reason,
        "num_extra_attachments": extra,
    }


def _positive_row(tmp_path: Path, idx: int, *, source_group: str) -> dict:
    return {
        "case_id": f"case_{idx:06d}",
        "base_sample_id": f"complex_{idx:06d}",
        "candidate_id": f"{source_group}:{idx:03d}",
        "candidate_path": _candidate_file(tmp_path, f"{source_group}_{idx:03d}"),
        "candidate_budget_k": 0,
        "source_group": source_group,
        "candidate_readable": True,
        "ligand_valid": True,
        "generated_fragment_heavy_atom_count": 3,
        "reliable_repair_success": source_group == "rule_positive",
        "strict_single_anchor_shadow_reliable": True,
        "reconnect_category": "single_anchor_reconnect_pass",
        "reconnect_category_reason": "single_anchor_connected",
        "num_extra_attachments": 0,
    }


def test_visual_qc_sampling_uses_confirmed_25_case_distribution(tmp_path: Path) -> None:
    diffsbdd = pd.DataFrame(
        [
            *[
                _diff_row(
                    tmp_path,
                    idx,
                    category="multi_attachment_out_of_scope",
                    reason=f"extra_attachments={(idx % 5) + 1}",
                    reliable=True,
                    strict=False,
                    budget=[8, 16, 32][idx % 3],
                    extra=(idx % 5) + 1,
                )
                for idx in range(1, 12)
            ],
            *[
                _diff_row(
                    tmp_path,
                    idx,
                    category="invalid_reconnect",
                    reason=["not_connected_to_anchor", "floating_fragment", "ligand_valid=false"][idx % 3],
                    reliable=False,
                    strict=False,
                    budget=[8, 16, 32][idx % 3],
                    extra=idx % 4,
                )
                for idx in range(20, 32)
            ],
            *[
                _diff_row(
                    tmp_path,
                    idx,
                    category="multi_attachment_out_of_scope",
                    reason=f"extra_attachments={(idx % 6) + 1}",
                    reliable=False,
                    strict=False,
                    budget=[8, 16, 32][idx % 3],
                    extra=(idx % 6) + 1,
                )
                for idx in range(40, 52)
            ],
        ]
    )
    clean = pd.DataFrame([_positive_row(tmp_path, idx, source_group="clean_positive") for idx in range(60, 66)])
    rule = pd.DataFrame([_positive_row(tmp_path, idx, source_group="rule_positive") for idx in range(70, 76)])

    cases = select_visual_qc_cases(
        clean=clean,
        rule=rule,
        diffsbdd=diffsbdd,
        quotas={
            "clean_positive": 3,
            "rule_positive": 3,
            "diffsbdd_invalid_non_reliable": 6,
            "diffsbdd_multi_non_reliable": 6,
            "diffsbdd_reliable_strict_shadow_fail": 7,
        },
        seed=20260517,
    )

    assert len(cases) == 25
    assert cases["sampling_group"].value_counts().to_dict() == {
        "diffsbdd_reliable_strict_shadow_fail": 7,
        "diffsbdd_invalid_non_reliable": 6,
        "diffsbdd_multi_non_reliable": 6,
        "clean_positive": 3,
        "rule_positive": 3,
    }
    assert cases["candidate_id"].is_unique
    assert cases.loc[cases["sampling_group"] == "diffsbdd_invalid_non_reliable", "fallback_reason"].str.contains("anchor_not_mapped_not_available").any()


def test_visual_qc_view_commands_keep_three_distinct_view_purposes() -> None:
    assert set(VISUAL_QC_VIEWS) == {
        "reconnect_clash",
        "reconnect_anchor_topology",
        "reconnect_before_after_overlay",
    }
    clash = _view_commands("reconnect_clash")
    topology = _view_commands("reconnect_anchor_topology")
    overlay = _view_commands("reconnect_before_after_overlay")

    assert "open protein_pocket.pdb" in clash
    assert "open close_contacts.bild" in clash
    assert "color #2 orange" in clash
    assert "open actual_attachment_bonds.bild" in topology
    assert "open extra_attachment_bonds.bild" in topology
    assert "color #6 red" in topology
    assert "open failed_ligand.sdf" in overlay
    assert "open candidate_ligand.sdf" in overlay
    assert "open original_ligand.sdf" in overlay


def test_camera_quality_marks_missing_or_occluded_views() -> None:
    good = pd.DataFrame(
        [
            {
                "status": "rendered",
                "ligand_occluded_fraction": 0.05,
                "key_occluded_fraction": 0.10,
                "projection_area_score": 0.5,
                "center_line_blocked": False,
            }
            for _ in range(12)
        ]
    )
    poor = pd.DataFrame(
        [
            {
                "status": "rendered",
                "ligand_occluded_fraction": 0.70,
                "key_occluded_fraction": 0.80,
                "projection_area_score": 0.03,
                "center_line_blocked": True,
            }
            for _ in range(12)
        ]
    )
    failed = pd.DataFrame([{"status": "failed"}])

    assert _camera_quality_for_group(good) == "camera_quality_good"
    assert _camera_quality_for_group(poor) == "camera_quality_poor"
    assert _camera_quality_for_group(failed) == "camera_quality_failed"
