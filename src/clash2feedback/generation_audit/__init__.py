from __future__ import annotations

TAXONOMY_LABELS = {
    "valid_no_severe_clash",
    "ligand_only_invalid",
    "postprocess_failed",
    "rgroup_unattributable",
    "unsupported_chemistry",
    "near_miss_contact",
    "single_rgroup_clash",
    "multi_region_clash",
    "scaffold_clash",
    "global_pose_failure",
    "pocket_mismatch_or_out_of_scope",
}

REPAIRABILITY_PROXY_LABELS = {
    "local_rgroup_repair_possible",
    "global_repose_needed",
    "invalid_unrepairable",
    "unsupported",
    "reject",
}

EXTERNAL_ELIGIBLE_TIERS = {"T3_official_diffsbdd_test", "T4_external_unseen", "T_unknown"}
