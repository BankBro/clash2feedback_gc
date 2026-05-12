# Phase 2.5 Model-Induced Audit

## 1. Summary

```json
{
  "schema_version": "phase2_5_v0_1",
  "audit_type": "external_validity_audit",
  "baseline_model": "DiffSBDD",
  "baseline_conda_env": "diffsbdd",
  "diffsbdd_repo_commit": "5d0d38d16c8932a0339fd2ce3f67ade98bbdff27",
  "diffsbdd_expected_repo_commit": "5d0d38d16c8932a0339fd2ce3f67ade98bbdff27",
  "diffsbdd_env_check_status": "ready",
  "diffsbdd_cuda_available": true,
  "checkpoint_name": "crossdocked_fullatom_cond.ckpt",
  "checkpoint_path": "external/DiffSBDD/checkpoints/crossdocked_fullatom_cond.ckpt",
  "checkpoint_md5": "166b0c056b31ffdf31d489a63e91e05b",
  "checkpoint_sha256": "07f86764bf569aafbc40a9c15fc02de8e2550437dd0f17f657eab3abe66c372c",
  "checkpoint_file_size": 17861341,
  "num_base_pockets_selected": 10,
  "num_generated_total": 200,
  "num_readable": 400,
  "num_ligand_valid": 240,
  "num_ligand_invalid": 160,
  "num_rgroup_attributable": 348,
  "num_with_severe_clash": 30,
  "num_single_rgroup_clash": 2,
  "num_multi_region_clash": 0,
  "num_scaffold_clash": 12,
  "num_global_pose_failure": 16,
  "num_near_miss_contact": 62,
  "num_local_rgroup_repair_possible": 0,
  "phase2_coverage_proxy": 0.0,
  "training_overlap_audit_done": true,
  "num_pockets_t0_exact_pair_seen": 0,
  "num_pockets_t1_same_target_seen": 0,
  "num_pockets_t3_official_diffsbdd_test": 0,
  "num_pockets_t4_external_unseen": 0,
  "num_pockets_t_unknown": 51,
  "external_validity_subset_size": 51,
  "same_source_debug_subset_size": 0,
  "does_not_train": true,
  "does_not_repair": true,
  "does_not_rank_baselines": true,
  "does_not_modify_phase2_v0_1": true,
  "blocked_reasons": [
    "official_diffsbdd_or_pocket2mol_split_unavailable"
  ]
}
```

## 2. Boundary

- 本阶段不训练模型, 不做 repair, 不调参, 不做 baseline ranking.
- generated ligand 没有 oracle `target_rgroup`; predicted dominant R-group 只作为 taxonomy / proxy 信号.
- model-induced samples 不进入阶段 3 Top-1 / Top-3 主评估.

## 3. Blocked

- official_diffsbdd_or_pocket2mol_split_unavailable
