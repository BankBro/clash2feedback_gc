from clash2feedback.repair.reconnect_calibration import (
    RECONNECT_LABELS,
    build_shadow_reliable_analysis,
    build_synthetic_negative_checks,
    classify_reconnect_row,
)
from clash2feedback.verifier.phase4_adapter import RELIABLE_REPAIR_FIELDS


def _base_row() -> dict:
    return {
        "candidate_readable": True,
        "candidate_path": "/tmp/mock.sdf",
        "ligand_valid": True,
        "fixed_structure_mapping_success_for_diagnostics": True,
        "fixed_structure_match_success": True,
        "anchor_match_success": True,
        "generated_fragment_heavy_atom_count": 3,
        "floating_fragment_detected": False,
        "generated_fragment_connected_to_anchor": True,
        "generated_fragment_attachment_count": 1,
        "num_anchor_neighbors": 1,
        "num_extra_attachments": 0,
    }


def test_reconnect_three_way_classification() -> None:
    assert classify_reconnect_row(_base_row())["reconnect_category"] == "single_anchor_reconnect_pass"

    multi = _base_row()
    multi["generated_fragment_attachment_count"] = 3
    multi["num_extra_attachments"] = 2
    result = classify_reconnect_row(multi)
    assert result["reconnect_category"] == "multi_attachment_out_of_scope"
    assert "ligand_valid" not in result["reconnect_category_reason"]

    disconnected = _base_row()
    disconnected["generated_fragment_connected_to_anchor"] = False
    assert classify_reconnect_row(disconnected)["reconnect_category"] == "invalid_reconnect"

    floating = _base_row()
    floating["floating_fragment_detected"] = True
    assert classify_reconnect_row(floating)["reconnect_category"] == "invalid_reconnect"

    missing_anchor = _base_row()
    missing_anchor["anchor_match_success"] = False
    assert classify_reconnect_row(missing_anchor)["reconnect_category"] == "invalid_reconnect"


def test_synthetic_negative_expected_categories() -> None:
    import pandas as pd

    clean = pd.DataFrame([{**_base_row(), "case_id": "case_x", "candidate_id": "clean:case_x", "reconnect_category": "single_anchor_reconnect_pass"}])
    negatives = build_synthetic_negative_checks(clean)

    by_type = dict(zip(negatives["synthetic_negative_type"], negatives["reconnect_category"]))
    assert by_type == {
        "disconnected": "invalid_reconnect",
        "floating": "invalid_reconnect",
        "extra_attachment": "multi_attachment_out_of_scope",
        "missing_anchor": "invalid_reconnect",
    }


def test_shadow_analysis_does_not_modify_reliable_repair_success() -> None:
    import pandas as pd

    df = pd.DataFrame(
        [
            {"candidate_budget_k": 8, "reliable_repair_success": True, "strict_single_anchor_shadow_reliable": True, "reconnect_category": "single_anchor_reconnect_pass"},
            {"candidate_budget_k": 8, "reliable_repair_success": True, "strict_single_anchor_shadow_reliable": False, "reconnect_category": "multi_attachment_out_of_scope"},
            {"candidate_budget_k": 8, "reliable_repair_success": False, "strict_single_anchor_shadow_reliable": False, "reconnect_category": "invalid_reconnect"},
        ]
    )

    shadow = build_shadow_reliable_analysis(df)
    total = shadow[shadow["candidate_budget_k"] == -1].iloc[0]

    assert total["reliable_repair_success_count"] == 2
    assert total["strict_single_anchor_shadow_reliable_count"] == 1
    assert df["reliable_repair_success"].tolist() == [True, True, False]


def test_reliable_repair_standard_stays_ten_fields_without_local_reconnect() -> None:
    assert len(RELIABLE_REPAIR_FIELDS) == 10
    assert "local_reconnect_pass" not in RELIABLE_REPAIR_FIELDS
    assert "reconnect_category" not in RELIABLE_REPAIR_FIELDS
    assert RECONNECT_LABELS == [
        "single_anchor_reconnect_pass",
        "multi_attachment_out_of_scope",
        "invalid_reconnect",
    ]
