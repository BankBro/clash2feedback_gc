# docs_update_summary_phase3_phase4_new_position

## 1. 基线记录

- `git status --short`: 初始状态只有未跟踪建议文档 `tmp/20260512/20260512-Clash2Feedback-GC_docs文档调整建议_阶段3与阶段4新口径.md`.
- `git branch --show-current`: `main`.
- `git rev-parse HEAD`: `15af462a7332ecadbcbdf0cb7b71f26ffa6f3f39`.

## 2. 核查到的仓库事实

- `scripts/phase2_inject_artificial_clashes.py` 中人工扰动由 `rotate_target_rgroup`, `torsion_perturb_target_rgroup`, `directed_rotation_attempts` 生成, `target_rgroup` 来自被扰动的 R-group.
- `src/clash2feedback/perturb/labels.py` 中 `assign_oracle_split()` 会调用 `target_score_ratio_valid(attribution, target_rgroup)`, 并用 `min_target_score_ratio_valid` gate 影响 `supported_single_rgroup`.
- `src/clash2feedback/geometry/rgroup_attribution.py` 中 `valid_rgroup_scores`, `dominant_valid_rgroup`, `top_valid_rgroups` 来自 attribution-derived normalized region scores.
- `configs/phase2_injection.yaml` 中 `acceptance.min_target_score_ratio_valid = 0.7`, `max_non_target_severe_pairs = 0`, `max_scaffold_severe_pairs = 0`, `max_clash_depth_angstrom = 1.5`.
- `predicted_dominant_valid_rgroup` 在阶段 2脚本中是记录字段, 没有直接作为 acceptance gate.
- `reports/phase2_injection/phase2_final_report.md` 是历史实验报告, 仍含阶段 3 Top-1 / Top-3 旧建议; 本次未修改该历史结果.
- `reports/phase2_5_model_induced_audit/phase2_5_final_experiment_report.md` 已存在, 其结论是 DiffSBDD de novo audit 中 `single_rgroup_clash = 1 / 200` unique candidates, `local_rgroup_repair_possible = 0`.
- `docs/*阶段4*` 当前不存在.

## 3. 修改文件与内容

- `README.md`
  - 增加阶段 3 新口径: label provenance audit, circularity risk audit, construction consistency check, phase4 mask seed generation.
  - 增加阶段 4 新口径: 先 backend feasibility audit, 再 Random / Predicted / Oracle formal repair loop.
  - 明确 `target_rgroup` 与 `supported_single_rgroup` 区别, 并说明 `target_score_ratio_valid` 的 attribution-derived 属性.

- `docs/README.md`
  - 增加阶段 3 / 4 当前口径索引, 方便 docs 目录内统一入口.

- `docs/20260504-03-Clash2Feedback-GC_总体实验递进路线.md`
  - 将阶段 3 从规则 locator 独立评估改为 label provenance audit + circularity risk audit + phase4 mask seed generation.
  - 将阶段 3 产物改为 `reports/phase3_label_provenance_audit/` 和 `phase4_mask_seed.csv`.
  - 将 Top-1 / Top-3 降级为 construction consistency check, 删除其作为阶段关闭线的口径.
  - 将阶段 4 改为 4.0 backend feasibility audit, 4.1 Random / Predicted / Oracle formal repair loop, 4.2 optional clash-guided denoising prototype.
  - 更新 Mini-Loop 0 / 1, 目录结构和决策点.

- `docs/20260504-02-Clash2Feedback-GC_第一篇论文实验方案.md`
  - 重写核心 RQ: 标签依赖和循环验证风险, downstream repair utility, local repair vs full resampling, optional guided sampling.
  - 将论文主张从 locator accuracy 改为 operational mask policy 的 downstream repair utility.
  - 更新数据集用途, 对照方法, 指标表, 实验表格和最小可发表实验包.
  - 引用阶段 2.5 最终报告事实, 收窄 model-induced claim.

- `docs/20260510-Clash2Feedback-GC_阶段2人工局部碰撞注入最终落地方案.md`
  - 增加 `target_rgroup` 与 `supported_single_rgroup` 的边界说明.
  - 明确 `target_score_ratio_valid` 来自 attribution-derived valid R-group scores.
  - 将 `supported_single_rgroup_cases.csv` 用途改为 label provenance audit, construction consistency check 和 phase4 mask seed 输入.
  - 更新阶段 3 preflight 和最终落地结论.

- `docs/20260504-01-Clash2Feedback-GC_完整方案与升级路线.md`
  - 增加 operational mask policy, downstream repair utility 和阶段 4 新口径.
  - 明确 DiffDec / DiffSBDD plain backend 是 local constrained resampling / candidate backend, 不是完整 feedback-guided denoising.
  - 更新数据集用途, 对照方法, 指标和目录结构.

- `docs/20260511-Clash2Feedback-GC_阶段2.5模型诱导失败外部有效性审计落地方案.md`
  - 引用阶段 2.5 最终报告.
  - 明确 model-induced samples 不进入阶段 3 construction consistency denominator.
  - 明确 `single_rgroup_clash` 是 taxonomy, 不是 oracle target R-group.
  - 更新与阶段 3 / 4 的关系.

- `docs/external_baselines.md`
  - 新增 Candidate Local Repair Backends 小节.
  - 记录 DiffSBDD 在阶段 2.5 中已验证 frozen de novo audit, 但作为 phase4 backend 仍需 feasibility audit.
  - 记录 DiffDec `status: to_be_verified_locally`, 并标明原版不直接接收完整 `H_clash` feedback.

- `docs/20260508-Clash2Feedback-GC_阶段1碰撞检测器与可靠验证器方案.md`
  - 将阶段 1 到阶段 3 的接口改为 label provenance audit / phase4 mask seed.
  - 明确 Top-1 / Top-3 只作为 construction consistency check.
  - 增加阶段 4 predicted mask 和 `protein_clash_heatmap` 使用边界.

- `docs/20260505-Clash2Feedback-GC_阶段0工程方案.md`
  - 同步目录结构中的 phase3 / phase4 新产物目录.
  - 将阶段 3 说明改为标签溯源与 mask seed.

## 4. 删除或降级的旧表述

- 删除阶段 3 作为 independent locator benchmark 的路线口径.
- 删除 `R-group Top-1 > 70%`, `R-group Top-3 > 90%`, `dominant ratio mean > 0.75` 作为阶段 3 关闭条件的口径; 仅保留为旧阈值示例或 construction consistency observation.
- 删除 `supported_single_rgroup` 是阶段 3 主 Top-1 / Top-3 主评估集的口径.
- 删除 DiffDec / DiffSBDD plain backend 可被写成完整 feedback-guided denoising 的口径.
- 删除 model-induced failures 主要是 single-Rgroup clash 的论文口径.

## 5. 新加入的统一口径

- 阶段 3 仍叫阶段 3.
- 阶段 3 = label provenance audit + circularity risk audit + construction consistency check + phase4 mask seed generation.
- `target_rgroup` 是人工扰动标签.
- `supported_single_rgroup` 是经过 detector / attribution / target-dominance gates 过滤后的 clean local repair substrate.
- `supported_single_rgroup` 上的 Top-1 / Top-3 只能作为 construction consistency check.
- 阶段 4 predicted mask 是 operational mask policy, 不是 ground truth.
- 阶段 4 先做 backend feasibility audit, 再做 Random / Predicted / Oracle formal repair loop.
- DiffDec / DiffSBDD plain backend 是 local constrained resampling / candidate backend.
- 只有实现 clash penalty / hot region guidance 并改采样过程后, 才能声称 `H_clash` 进入生成过程.

## 6. 未修改项与冲突

- 未修改任何 `reports/phase2_injection/*.csv`, `reports/phase2_injection/*.json`, `reports/phase2_5_model_induced_audit/*.csv`, `*.json`, `*.parquet`, 或 `data/benchmarks/clashrepairbench_rg_artificial/v0_1/` 文件.
- 未运行新实验, 未重写历史实验结果.
- 建议文档中若暗示 `predicted_dominant_valid_rgroup` 直接参与 acceptance, 与仓库事实不完全一致; 代码事实是 `predicted_dominant_valid_rgroup` 只记录, `target_score_ratio_valid` 才是 attribution-derived acceptance gate.
- 历史报告 `reports/phase2_injection/phase2_final_report.md` 仍保留旧阶段 3 Top-1 / Top-3 建议, 本次按“不改历史实验结果”要求未修改.
- 当前没有 `docs/*阶段4*` 独立方案文档可更新.
