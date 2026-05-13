# 阶段 3 标签溯源与阶段 4 掩码种子实验说明

## 1. 背景

本次工作执行的是阶段 3, 不是分子修复实验. 阶段 3 的定义为 label provenance audit, circularity risk audit, construction consistency check 和 phase4 mask seed generation.

阶段 3 不承担 independent locator benchmark 职责, 不训练模型, 不调用生成器, 不修复分子, 也不生成阶段 3 最终实验报告. `supported_single_rgroup` 上的 Top-1 / Top-3 只解释为 construction consistency check.

## 2. Git 参考

- 本地仓库: `/home/lyj/mnt/project/clash2feedback_gc`
- 远端仓库: `git@github.com:BankBro/clash2feedback_gc.git`
- 分支: `20260513-160230-phase3-implementation`
- 阶段 3 执行基线 commit: `d1ad862f62b531e83ee8c866f4f13e54cab52015`
- 推送后请以用户 prompt 指定的最终 commit id 为准.

## 3. 本次应提交给远端的文件选择

网页版 ChatGPT 只能阅读远端 GitHub 仓库. 为便于它分析本次实验, 本次应提交以下轻量文件:

- 阶段 3 方案上下文:
  - `docs/20260513-Clash2Feedback-GC_阶段3标签溯源循环风险审计与阶段4掩码种子生成方案总纲.md`
  - `tmp/20260513/phase3-label-provenance-mask-seed-codex-goal-exec-plan.md`
  - `tmp/20260513/phase3-label-provenance-mask-seed-experiment-summary-for-chatgpt.md`
- 阶段 3 实现:
  - `configs/phase3_label_provenance_audit.yaml`
  - `scripts/phase3_label_provenance_audit.py`
  - `src/clash2feedback/feedback/__init__.py`
  - `src/clash2feedback/feedback/mask_seed.py`
  - `tests/test_phase3_label_provenance.py`
  - `tests/test_phase3_mask_seed.py`
- 阶段 3 输出:
  - `reports/phase3_label_provenance_audit/summary.json`
  - `reports/phase3_label_provenance_audit/phase2_label_provenance_audit.md`
  - `reports/phase3_label_provenance_audit/circularity_risk_audit.md`
  - `reports/phase3_label_provenance_audit/field_dependency_table.csv`
  - `reports/phase3_label_provenance_audit/set_definition_report.csv`
  - `reports/phase3_label_provenance_audit/construction_consistency_report.csv`
  - `reports/phase3_label_provenance_audit/locator_stress_report_s0.csv`
  - `reports/phase3_label_provenance_audit/locator_stress_report_s1.csv`
  - `reports/phase3_label_provenance_audit/phase4_mask_seed.csv`
  - `reports/phase3_label_provenance_audit/phase3_completion_audit.md`
- 文档同步:
  - `README.md`
  - `configs/README.md`
  - `scripts/README.md`
  - `reports/README.md`
  - `src/README.md`

不需要提交或推送 phase2 sample pkl, ligand SDF, raw candidates 或 standardized candidates. 本次分析需要的每个 S2 case 的 R 基掩码, 保留掩码, anchor, 旧碰撞 pairs, protein hot atoms 和 protein hot residues 已经汇总在 `reports/phase3_label_provenance_audit/phase4_mask_seed.csv`.

## 4. 已有远端上下文

以下 phase2 / phase2.5 文件已经在 Git 中跟踪, 网页版 ChatGPT 可直接读取:

- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/manifest.parquet`
- `reports/phase2_injection/summary.json`
- `reports/phase2_injection/supported_single_rgroup_cases.csv`
- `reports/phase2_injection/phase2_final_report.md`
- `reports/phase2_5_model_induced_audit/failure_taxonomy.csv`
- `reports/phase2_5_model_induced_audit/phase2_5_final_experiment_report.md`

注意: phase2 历史报告中可能保留旧口径的阶段 3 Top-1 / Top-3 表述. 本次阶段 3 以新口径为准, 即 Top-1 / Top-3 只能作为 construction consistency check.

## 5. 关键仓库事实

- `target_rgroup` 来自 phase2 人工扰动流程, 是参考掩码来源, 不是无偏定位真值.
- `target_atom_indices`, `anchor_scaffold_atom_idx`, `anchor_rgroup_atom_idx`, `anchor_bond_idx` 可用于生成和核查参考掩码.
- `predicted_dominant_valid_rgroup` 来自 `attribute_clashes_to_rgroups()`, 是 operational predicted mask policy, 不是 ground truth.
- `predicted_dominant_valid_rgroup` 只是记录字段, 不直接作为 phase2 acceptance gate.
- `target_score_ratio_valid` 来自 attribution-derived valid R-group scores, 并参与 `supported_single_rgroup` 相关 gate.
- `supported_single_rgroup` 是 detector / attribution / target-dominance gates 过滤后的 clean local repair substrate, 不是无偏定位 benchmark.
- phase2.5 model-induced samples 没有人工 `target_rgroup`, 不得进入阶段 3 construction consistency denominator.
- phase2 sample pkl 不包含完整 `rgroups` / `masks`; 阶段 3 通过 `base_sample_id` 回连 `data/processed/v0_1/complexes/*.pkl` 恢复 R 基定义.

## 6. S0 / S1 / S2 集合

- S0: `S0_all_valid_injection_attempts`, 当前 1185 行. 用于辅助审计.
- S1: `S1_oracle_target_local_clash_set`, 当前 467 行. 不使用 `target_score_ratio_valid >= 0.7` gate, 用于压力分析.
- S2: `S2_phase2_supported_single_rgroup`, 当前 357 行. 阶段 4 主输入, 也是 construction consistency check denominator.

S2 的 circularity risk level 为 high, 因为它经过 detector / attribution / target-dominance gates 过滤.

## 7. 掩码定义

本次 mask 本质是 ligand 内部的 0-based 原子编号集合.

- 参考掩码: `target_rgroup` 对应的整个 R 基原子集合.
- 自动预测掩码: `predicted_dominant_valid_rgroup` 对应的整个 R 基原子集合.
- 随机掩码: 同一配体中 size-matched 的合法 single-anchor R 基原子集合.
- 编辑掩码: 整个 R 基.
- 保留掩码: 配体中除编辑掩码以外的所有原子.
- anchor: 单独记录, 不默认加入自由编辑掩码.

`phase4_mask_seed.csv` 中必须重点看:

- `oracle_mask_atom_indices`
- `predicted_mask_atom_indices`
- `random_mask_atom_indices`
- `oracle_keep_atom_indices`
- `predicted_keep_atom_indices`
- `random_keep_atom_indices`
- `oracle_anchor_*`
- `predicted_anchor_*`
- `random_anchor_*`
- `old_clash_pairs_json`
- `protein_clash_hot_atoms_json`
- `protein_clash_hot_residues_json`
- `predicted_equals_oracle`
- `random_equals_oracle`
- `random_equals_predicted`

## 8. 本次结果摘要

- phase2 manifest rows: 2610.
- S0: 1185.
- S1: 467.
- S2: 357.
- `phase4_mask_seed.csv` rows: 357.
- `phase4_0_backend_feasibility_candidate`: 357.
- `phase4_1_formal_loop_candidate`: 357.
- `predicted_equals_oracle`: 357 / 357.
- `random_equals_oracle`: 0 / 357.
- `random_equals_predicted`: 0 / 357.
- construction consistency Top-1: 357 / 357 = 1.0.
- construction consistency Top-3: 357 / 357 = 1.0.
- phase2.5 failure taxonomy rows: 400.
- phase2.5 rows included in construction consistency denominator: false.

## 9. 结论边界

可以得出的结论:

- phase2 人工扰动标签, attribution 记录和阶段 4 掩码种子构造在 S2 上一致.
- 阶段 4 的三组输入 Random / Predicted / Oracle 均已具备.
- random mask 没有退化成 oracle 或 predicted 复用.
- 阶段 2.5 model-induced rows 没有混入阶段 3 construction consistency denominator.

不能得出的结论:

- 不能把 357 / 357 写成 independent locator accuracy.
- 不能把 `target_rgroup` 写成无偏定位真值.
- 不能把 predicted mask 写成 ground truth.
- 不能从阶段 3 推断修复后端有效, 因为阶段 3 没有调用修复后端.

## 10. 验证命令

```bash
python scripts/phase3_label_provenance_audit.py --config configs/phase3_label_provenance_audit.yaml
python -m compileall src scripts
python -m pytest tests/test_phase3_*.py
python -m pytest
```

本地验证结果:

- `python -m compileall src scripts`: passed.
- `python -m pytest tests/test_phase3_*.py`: 8 passed.
- `python -m pytest`: 120 passed.

## 11. 建议网页版 ChatGPT 分析的问题

- 本次阶段 3 结果能否充分支持进入阶段 4.0 backend feasibility audit.
- `phase4_mask_seed.csv` schema 是否足够支撑阶段 4.0 Oracle mask backend feasibility 和阶段 4.1 Random / Predicted / Oracle formal loop.
- random size-matched mask 是否还需要额外 stratification, 例如按 R 基大小, injection mode, difficulty bin 或 base split 分层.
- S0 / S1 是否应保留为辅助压力分析, 以及如何避免被误读为 independent locator benchmark.
- 阶段 4 应优先定义哪些成功指标, 例如 old clash clearance, new clash avoidance, scaffold preservation, anchor integrity 和 ligand validity.
