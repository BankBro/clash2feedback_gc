# Phase 2 Completion Audit

## 1. Checklist

| item | status | evidence |
|---|---|---|
| `configs/phase2_injection.yaml` exists | done | config 已新增, 包含 processed, splits, phase1 report 和输出路径 |
| phase2 script runnable | done | `scripts/phase2_inject_artificial_clashes.py` 已跑完整 51 个 base samples |
| base clean pose gate | done | 51/51 base clean pass |
| ligand-only validity gate | done | supported 主集全部 `ligand_valid = true`, `ligand_internal_severe_clash_count = 0` |
| rotatable anchor gate | done | ring/double/aromatic/amide/conjugated gate 已实现并测试 |
| protein-ligand failure gate | done | supported 主集全部 target severe >= 1, non-target severe = 0, scaffold severe = 0 |
| delta sensitivity | done | `delta_sensitivity.csv`, manifest `delta03/04/05_status` 已生成 |
| split design | done | supported, reject, invalid, unsupported, duplicate, near_miss 均有报告 |
| anti-leakage | done | `target_rgroup` 为 oracle; `predicted_dominant_*` 只记录, 不参与 acceptance; train/val/test split 继承通过 |
| heavy atom index stability | done | rotation/torsion 不 AddHs; AddHs 只用于 ligand-only energy check |
| deduplication | done | `duplicate_removed = 739` |
| benchmark manifest/schema/samples | done | manifest, schema, samples, original/failed SDF 已生成 |
| reports | done | `reports/phase2_injection/` 必需文件已生成 |
| visual QC sampling | done | `visual_qc_cases.csv`, `visual_qc_notes.md` 已生成 |
| visual QC manual review | blocked | 需要人工打开抽样 SDF/sample 判读 |

## 2. 修改和新增

代码文件:

- `src/clash2feedback/perturb/__init__.py`
- `src/clash2feedback/perturb/rotation.py`
- `src/clash2feedback/perturb/torsion.py`
- `src/clash2feedback/perturb/directed_clash.py`
- `src/clash2feedback/perturb/quality.py`
- `src/clash2feedback/perturb/labels.py`
- `src/clash2feedback/perturb/deduplicate.py`
- `scripts/phase2_inject_artificial_clashes.py`
- `configs/phase2_injection.yaml`

测试文件:

- `tests/test_phase2_rotation.py`
- `tests/test_phase2_ligand_validity.py`
- `tests/test_phase2_anchor_integrity.py`
- `tests/test_phase2_labels.py`
- `tests/test_phase2_no_leakage.py`
- `tests/test_phase2_reports.py`

报告和数据:

- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/manifest.parquet`
- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/schema.json`
- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/samples/*.pkl`
- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/ligands/*_original.sdf`
- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/ligands/*_failed.sdf`
- `reports/phase2_injection/*.csv`
- `reports/phase2_injection/summary.json`
- `reports/phase2_injection/visual_qc_notes.md`
- `reports/phase2_injection/phase2_completion_audit.md`

docs:

- `README.md`, `configs/README.md`, `scripts/README.md`, `src/README.md`, `data/README.md`, `reports/README.md`
- `docs/20260504-01-Clash2Feedback-GC_完整方案与升级路线.md`
- `docs/20260504-02-Clash2Feedback-GC_第一篇论文实验方案.md`
- `docs/20260504-03-Clash2Feedback-GC_总体实验递进路线.md`
- `docs/20260505-Clash2Feedback-GC_阶段0工程方案.md`
- `docs/20260508-Clash2Feedback-GC_阶段1碰撞检测器与可靠验证器方案.md`
- `tmp/20260510/20260510-docs_update_summary.md`

## 3. Actual Commands

```bash
/home/lyj/miniconda3/envs/c2f_cpu/bin/python scripts/phase2_inject_artificial_clashes.py --config configs/phase2_injection.yaml --manifest data/processed/v0_1/manifest.parquet --phase1-report-root reports/phase1_clash_detector --output-root data/benchmarks/clashrepairbench_rg_artificial/v0_1 --report-root reports/phase2_injection
/home/lyj/miniconda3/envs/c2f_cpu/bin/python -m compileall src scripts
/home/lyj/miniconda3/envs/c2f_cpu/bin/python -m pytest
```

## 4. Validation Results

- `compileall`: pass.
- `pytest`: 74 passed in 6.12s.
- phase2 run: complete, 2610 attempts, 357 supported.
- manifest readable: pass, shape `(2610, 70)`.
- samples readable: spot-check pass; generated 2610 `.pkl`, 2610 original SDF, 2610 failed SDF.
- train/val/test split inheritance: pass, all `base_split == derived_split`; counts `train = 1422`, `test = 1080`, `val = 108`; `unknown = 0`.
- split group traceability: pass, `split_group` 保留原始 group key, 例如 `CDGT2_BACCI_28_713_0`.

Supported主集校验:

- `ligand_valid`: all true.
- `ligand_internal_severe_clash_count`: max 0.
- `target_num_severe_pairs`: min 1.
- `non_target_num_severe_pairs`: max 0.
- `scaffold_num_severe_pairs`: max 0.

## 5. Phase2 Summary

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
  "delta_sensitivity": [0.3, 0.4, 0.5],
  "injection_modes": ["easy_rotation", "torsion_perturb", "directed_clash"],
  "phase2_acceptance_status": "complete",
  "visual_qc_status": "pending_manual_review"
}
```

## 6. Blocked Or Unfinished

- `visual_qc_manual_review`: blocked. 已生成 `visual_qc_cases.csv` 和 `visual_qc_notes.md`, 但需要人工打开抽样 `SDF/sample` 做可视化判读.
- 无其他非 blocked 未完成项.

## 7. Phase 3 Preflight

- 阶段 3 Top-1 / Top-3 主指标只读取 `oracle_split == supported_single_rgroup`.
- reject / unsupported / near_miss / duplicate split 单独统计分流表现.
- phase3 locator 可读取 `target_rgroup`, `predicted_dominant_valid_rgroup`, `top_valid_rgroups_json`, `delta03_status`, `delta04_status`, `delta05_status`.
- no-repair negative, oracle repair 和 wrong-region repair 可作为 verifier preflight, 但不等同于阶段 4 真实 repair candidate 验证.
