# Phase 2 Completion Audit

## 1. Checklist

| item | status |
|---|---|
| configs/phase2_injection.yaml exists | done |
| phase2 script runnable | done |
| manifest.parquet readable | done |
| samples/*.pkl generated | done |
| reports/phase2_injection generated | done |
| supported_single_rgroup cases > 0 | done |
| accepted samples ligand_valid true | done |
| accepted samples ligand internal severe clash = 0 | done |
| supported target severe clash >= 1 | done |
| supported non-target severe = 0 | done |
| supported scaffold severe = 0 | done |
| injected samples inherit base split | done |
| predicted dominant not used as acceptance gate | done |
| invalid/reject/unsupported/duplicate reported | done |
| visual QC cases recorded | done |
| visual QC manual review | done_with_minor_caveats |
| delta_sensitivity.csv has no empty columns | done |
| energy_delta stats/outliers reports | done |

## 2. Commands

```bash
/home/lyj/miniconda3/envs/c2f_cpu/bin/python -m compileall src scripts
/home/lyj/miniconda3/envs/c2f_cpu/bin/python -m pytest
/home/lyj/miniconda3/envs/c2f_cpu/bin/python scripts/phase2_inject_artificial_clashes.py --config configs/phase2_injection.yaml --manifest data/processed/v0_1/manifest.parquet --phase1-report-root reports/phase1_clash_detector --output-root data/benchmarks/clashrepairbench_rg_artificial/v0_1 --report-root reports/phase2_injection
```

## 3. Summary

```json
{
  "schema_version": "phase2_v0_1",
  "num_base_clean_samples": 51,
  "num_base_total_samples": 51,
  "num_attempts": 2610,
  "num_accepted_supported": 357,
  "num_reject": 50,
  "num_invalid_conformer": 601,
  "num_unsupported": 85,
  "num_duplicates_removed": 739,
  "num_near_miss_contact": 778,
  "oracle_split_counts": {
    "near_miss_contact": 778,
    "duplicate_removed": 739,
    "invalid_conformer": 601,
    "supported_single_rgroup": 357,
    "unsupported": 85,
    "global_pose_failure": 48,
    "ambiguous_region": 2
  },
  "default_delta_angstrom": 0.4,
  "delta_sensitivity": [
    0.3,
    0.4,
    0.5
  ],
  "injection_modes": [
    "easy_rotation",
    "torsion_perturb",
    "directed_clash"
  ],
  "phase1_report_root": "/home/lyj/mnt/project/clash2feedback_gc/reports/phase1_clash_detector",
  "phase2_acceptance_status": "complete",
  "visual_qc_status": "sampled_visual_qc_passed_with_minor_caveats",
  "energy_delta_threshold_mode": "record_only",
  "energy_delta_filter_interpretation": "record_only_not_hard_filter"
}
```

## 4. Validation Results

- `compileall`: pass.
- `pytest`: 78 passed in 6.17s.
- phase2 rerun: complete, 2610 attempts, 357 supported.
- manifest readable: pass, shape `(2610, 70)`.
- split inheritance: pass, all `base_split == derived_split`, derived splits are `train`, `val`, `test`.
- `delta_sensitivity.csv`: pass, columns are `delta_angstrom`, `target_severe`, `no_target_severe`, `unsupported_or_unavailable`; no empty header.
- `energy_delta_stats.csv`: generated, 17 grouped rows.
- `energy_delta_outliers.csv`: generated, 746 record-only outlier rows for visual/diagnostic prioritization.
- `visual_qc_cases.csv`: 32 sampled visual QC cases marked `sampled_visual_qc_passed_with_minor_caveats`: 17 supported, 5 invalid_conformer, 3 global_pose_failure, 2 ambiguous_region, 5 near_miss_contact. Supported visual QC covers all three injection modes, including 7 `torsion_perturb` cases.
- `reports/phase2_visual_qc/`: generated, 1536 rendered single-view images and 128 contact sheets; `by_category_index.csv` indexes cases by oracle split, injection mode and their matrix. Automated file checks found 0 missing images, 0 missing sheets and 0 broken category links.

## 5. Visual QC Caveats

- visual_qc_manual_review: done_with_minor_caveats. 用户人工粗看和 4 个只读子 agent 独立复核均未发现阻断问题; supported 主集视觉上符合单一 target R-group 局部 ligand-protein clash, scaffold/non-target 稳定.
- invalid_conformer caveat: 当前视图不专门高亮 ligand internal self-clash, 但 invalid cases 不像合格 ligand-protein clash.
- duplicate rejected-sample caveat: invalid visual QC 中 `case_000019`/`case_000029` 和 `case_000057`/`case_000070` 是视觉重复, 但属于 rejected invalid 样本, 不影响 supported 主集.
- ambiguous/near_miss caveat: `ambiguous_region` 的部分 surface 视图信息量有限; `near_miss_contact` 没有 severe VDW pair, 因此 `clash_pair_vdw` 为背景-only. 这些均符合对应 split 语义.

## 6. Phase2 Closure Decision

- Phase2 is accepted for controlled Phase3 locator / verifier preflight.
- Phase2 v0_1 is a controlled artificial single-Rgroup clash benchmark, not validation of model-induced generation failures.
- Phase2.5 external validity audit will be handled separately and is not implemented here.
- Energy delta is a record-only ligand-only diagnostic in phase2_v0_1; it is not a hard acceptance filter.

## 7. Phase 3 Preflight

- 使用 `supported_single_rgroup` 作为 Top-1 / Top-3 主评估集.
- 使用 reject/unsupported/near_miss/duplicate split 单独统计分流表现.
- 阶段 3 读取 `target_rgroup`, `top_valid_rgroups_json`, `delta03/04/05_status` 做 locator preflight.
