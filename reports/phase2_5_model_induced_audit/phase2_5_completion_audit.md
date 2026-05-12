# Phase 2.5 Completion Audit

## 1. Checklist

| item | status | notes |
|---|---|---|
| report exists: summary.json | done |  |
| report exists: training_overlap_audit.csv | done |  |
| report exists: training_overlap_summary.json | done |  |
| report exists: base_pocket_selection.csv | done |  |
| report exists: generation_manifest.parquet | done |  |
| report exists: ligand_validity.csv | done |  |
| report exists: model_induced_clash_report.csv | done |  |
| report exists: failure_taxonomy.csv | done |  |
| report exists: repairability_proxy.csv | done |  |
| report exists: artificial_vs_model_induced_gap.csv | done |  |
| report exists: visual_qc_cases.csv | done |  |
| report exists: visual_qc_notes.md | done |  |
| report exists: phase2_5_audit.md | done |  |
| training-overlap audit first | done | training_overlap_audit.csv is written before generation audit |
| all generated samples recorded | done | generation_manifest is schema-valid and includes raw/standardized stages when generation succeeds |
| DiffSBDD assets | done |  |
| DiffSBDD environment and GPU | done |  |
| DiffSBDD generation | done | unique_candidates=200 |
| official split provenance | blocked | official_diffsbdd_or_pocket2mol_split_unavailable |
| no train/repair/tune/ranking | done | constraints are enforced by config and wrapper scope |
| predicted dominant not oracle | done | taxonomy rows set predicted_dominant_is_oracle_ground_truth=false |
| phase2_v0_1 unchanged | done | phase2 benchmark is read-only input |

## 2. Commands

```bash
conda run -n c2f_cpu python scripts/phase2_5_prepare_diffsbdd.py --config configs/phase2_5_model_induced_audit.yaml --report-root reports/phase2_5_model_induced_audit --run-root runs/phase2_5_model_induced_audit
conda run -n c2f_cpu python scripts/phase2_5_training_overlap_audit.py --config configs/phase2_5_model_induced_audit.yaml --manifest data/processed/v0_1/manifest.parquet --output-root reports/phase2_5_model_induced_audit
conda run -n c2f_cpu python scripts/phase2_5_model_induced_audit.py --config configs/phase2_5_model_induced_audit.yaml --manifest data/processed/v0_1/manifest.parquet --phase1-report-root reports/phase1_clash_detector --phase2-benchmark-root data/benchmarks/clashrepairbench_rg_artificial/v0_1 --run-root runs/phase2_5_model_induced_audit --report-root reports/phase2_5_model_induced_audit
conda run -n c2f_cpu python -m compileall src scripts
conda run -n c2f_cpu python -m pytest
```

## 3. Verification

- compileall: passed: conda run -n c2f_cpu python -m compileall src scripts
- pytest: passed: 112 tests in 6.24s

## 4. Summary

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

## 5. Files

-  M .gitignore
-  M README.md
-  M configs/README.md
-  M data/README.md
-  M "docs/20260504-01-Clash2Feedback-GC_\345\256\214\346\225\264\346\226\271\346\241\210\344\270\216\345\215\207\347\272\247\350\267\257\347\272\277.md"
-  M "docs/20260504-02-Clash2Feedback-GC_\347\254\254\344\270\200\347\257\207\350\256\272\346\226\207\345\256\236\351\252\214\346\226\271\346\241\210.md"
-  M "docs/20260504-03-Clash2Feedback-GC_\346\200\273\344\275\223\345\256\236\351\252\214\351\200\222\350\277\233\350\267\257\347\272\277.md"
-  M "docs/20260508-Clash2Feedback-GC_\351\230\266\346\256\2651\347\242\260\346\222\236\346\243\200\346\265\213\345\231\250\344\270\216\345\217\257\351\235\240\351\252\214\350\257\201\345\231\250\346\226\271\346\241\210.md"
-  M reports/README.md
-  M runs/README.md
-  M scripts/README.md
-  M src/README.md
- ?? configs/phase2_5_model_induced_audit.yaml
- ?? "docs/20260511-Clash2Feedback-GC_\351\230\266\346\256\2652.5\346\250\241\345\236\213\350\257\261\345\257\274\345\244\261\350\264\245\345\244\226\351\203\250\346\234\211\346\225\210\346\200\247\345\256\241\350\256\241\350\220\275\345\234\260\346\226\271\346\241\210.md"
- ?? external/
- ?? reports/phase2_5_model_induced_audit/
- ?? scripts/phase2_5_model_induced_audit.py
- ?? scripts/phase2_5_prepare_diffsbdd.py
- ?? scripts/phase2_5_training_overlap_audit.py
- ?? src/clash2feedback/generation_audit/
- ?? tests/test_phase2_5_generated_ligand_validity.py
- ?? tests/test_phase2_5_no_oracle_leakage.py
- ?? tests/test_phase2_5_overlap.py
- ?? tests/test_phase2_5_reports.py
- ?? tests/test_phase2_5_taxonomy.py
- ?? "tmp/20260511/20260511-Clash2Feedback-GC_docs\346\226\207\346\241\243\350\260\203\346\225\264\345\273\272\350\256\256_\351\230\266\346\256\2652.5.md"
- ?? "tmp/20260511/20260511-Clash2Feedback-GC_\347\273\204\344\274\232\346\261\207\346\212\245\347\250\277_\346\234\200\347\273\210\347\211\210.md"
- ?? "tmp/20260511/20260511-Codex\351\230\266\346\256\2652.5\345\256\236\346\226\275Prompt.md"
- ?? "tmp/20260511/Clash2Feedback_GC_\347\273\204\344\274\232PPT_12\351\241\265\345\244\247\347\272\262_\346\226\271\346\241\210\347\273\223\346\236\234\347\211\210.md"

## 6. Blocked

- official_diffsbdd_or_pocket2mol_split_unavailable

## 7. Conclusion Boundary

- 当前报告只对已生成或已阻塞项给出审计结论.
- DiffSBDD/checkpoint/official split 缺失时, external validity 结论必须保守.
- 阶段 3 继续只使用 phase2 `supported_single_rgroup` 主评估集; 阶段 4 才进入 repair loop.
