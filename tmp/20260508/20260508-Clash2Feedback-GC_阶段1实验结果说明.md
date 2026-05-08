# Clash2Feedback-GC 阶段 1 实验结果说明

## 1. 本次实验目的

本次阶段 1 的目标是把 Clash2Feedback-GC 从阶段 0 的基础数据 sanity check 推进到正式几何裁判系统:

- 实现 protein-ligand vdW clash detector.
- 实现 R-group attribution 和 failure type 分类.
- 实现 reliable repair verifier skeleton.
- 对阶段 0 clean pool 和 balanced subset 做 clean calibration, threshold sensitivity 和 verifier smoke test.

阶段 1 明确不做:

- 不做人为 clash injection.
- 不接生成器.
- 不训练模型.
- 不把 full receptor 作为 hard dependency.

## 2. 提交给 GitHub 分析的数据选择

为了让网页版 ChatGPT 只依赖 GitHub 代码仓即可分析结果, 本次建议提交以下轻量结果文件:

- `reports/phase1_clash_detector/summary.json`
- `reports/phase1_clash_detector/clean_clash_report.csv`
- `reports/phase1_clash_detector/balanced_clash_report.csv`
- `reports/phase1_clash_detector/threshold_sensitivity.csv`
- `reports/phase1_clash_detector/rgroup_attribution_report.csv`
- `reports/phase1_clash_detector/failure_type_counts.csv`
- `reports/phase1_clash_detector/verifier_smoke_report.csv`
- `reports/phase1_clash_detector/unsupported_cases.csv`
- `reports/phase1_clash_detector/vdw_radius_table.json`

不建议提交:

- `data/raw_complexes/` 下的原始 PDB / SDF.
- `data/processed/v0_1/complexes/*.pkl`.
- `data/cache/`.
- `runs/` 下的大图, checkpoint 或运行产物.

理由: 阶段 1 分析主要需要 detector 参数, clean calibration 统计, failure type 分布和 verifier smoke 结果. 上述 reports 已能支持结果分析, 不需要暴露 raw structure 或 processed pickle.

## 3. 关键实现文件

- `configs/phase1_clash_detector.yaml`: 阶段 1 配置.
- `src/clash2feedback/geometry/vdw.py`: 固定 vdW 半径表.
- `src/clash2feedback/geometry/clash.py`: 正式 protein-ligand heavy atom nonbonded clash detector.
- `src/clash2feedback/geometry/rgroup_attribution.py`: ligand region 标注, R-group score 和 failure type 分类.
- `src/clash2feedback/verifier/repair_verifier.py`: reliable repair verifier skeleton.
- `scripts/phase1_check_clashes.py`: 批量报告脚本.
- `tests/test_vdw.py`, `tests/test_clash_detector.py`, `tests/test_rgroup_attribution.py`, `tests/test_repair_verifier.py`: 阶段 1 单元测试.

## 4. 运行命令

语法和单元测试:

```bash
python -m compileall src scripts
pytest
```

阶段 1 报告生成:

```bash
python scripts/phase1_check_clashes.py \
  --config configs/phase1_clash_detector.yaml \
  --manifest data/processed/v0_1/manifest.parquet \
  --balanced-subset data/splits/v0_1/phase0_balanced_30.txt \
  --output-root reports/phase1_clash_detector
```

## 5. 本次结果摘要

本次使用本地已有阶段 0 数据:

- `phase0_clean_pool_v0_1`: 51 samples.
- `phase0_balanced_30_v0_1`: 28 samples.

`reports/phase1_clash_detector/summary.json` 结果:

```json
{
  "num_clean_pool_samples": 51,
  "num_balanced_subset_samples": 28,
  "default_delta_angstrom": 0.4,
  "delta_sensitivity": [0.3, 0.4, 0.5],
  "receptor_scopes": ["phase0_pocket8", "pocket10_all_atoms"],
  "clean_pool_severe_false_positive_count": 0,
  "balanced_subset_severe_false_positive_count": 0,
  "verifier_smoke_total_count": 28,
  "verifier_smoke_pass_count": 28,
  "phase1_acceptance_status": "complete"
}
```

Threshold sensitivity 关键现象:

- `delta=0.4` 时, clean pool 和 balanced subset 在两个 receptor scope 下 severe false positive 均为 0.
- `delta=0.5` 更宽松, severe false positive 仍为 0.
- `delta=0.3` 更严格, clean pool 和 balanced subset 各有 1 个样本出现 severe clash, failure type 为 `ambiguous_region_clash`.

Verifier smoke:

- clean-vs-clean smoke test 在 balanced subset 上 28 / 28 pass.

Unsupported cases:

- 当前阶段 1 报告中 `unsupported_cases.csv` 为空, 表示本次 clean pool / balanced subset 没有触发 unsupported 或脚本错误.

## 6. 解释边界

本次结果只能说明阶段 1 detector / attribution / verifier skeleton 已能在阶段 0 clean pool 上稳定运行, 并完成 clean calibration.

不能说明:

- 规则 locator 已能找对人工失败 R-group.
- repair verifier 已能评估真实修复候选.
- 生成器修复闭环有效.
- full receptor checked repair 已完成.

这些属于后续阶段:

- 阶段 2: controlled synthetic failed pose benchmark.
- 阶段 3: 规则 locator Top-1 / Top-3 验证.
- 阶段 4: 冻结生成器最小修复闭环.
- 阶段 5/8: candidate ranking 和 full-receptor checked / model-induced failure 测试.

## 7. 建议网页版 ChatGPT 重点分析的问题

- `delta=0.4` 是否适合作为阶段 2 / 3 的默认阈值.
- `delta=0.3` 下唯一 ambiguous case 是否值得人工查看.
- `phase0_pocket8` 和 `pocket10_all_atoms` 在当前数据上结果完全一致是否符合 pocket10 数据预期.
- R-group attribution 报告中大量 `unsupported_rgroup` 零分项是否需要在报告中压缩展示.
- Verifier skeleton 的 old clash resolved gate 是否需要在阶段 2 failed pose 后升级为 old pair tracking.
- 阶段 2 synthetic failed pose 应优先实现 easy_rotation, torsion_perturb, directed_clash 还是 fragment_replace.
