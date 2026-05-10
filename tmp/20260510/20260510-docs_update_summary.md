# 20260510 docs update summary

## 1. 修改文件

- `README.md`: 新增阶段 2 用法, 输出清单, anti-leakage 口径和测试命令.
- `configs/README.md`: 增补 `phase1_clash_detector.yaml` 和 `phase2_injection.yaml`.
- `scripts/README.md`: 增补 `phase2_inject_artificial_clashes.py` 命令和边界说明.
- `src/README.md`: 增补 `perturb/` 和 `verifier/` 模块职责.
- `data/README.md`: 增补阶段 2 benchmark 目录说明.
- `reports/README.md`: 增补阶段 2 reports 文件清单.
- `docs/20260504-03-Clash2Feedback-GC_总体实验递进路线.md`: 对齐阶段 2 目标, 注入方式, acceptance gates, split 和输出口径.
- `docs/20260504-02-Clash2Feedback-GC_第一篇论文实验方案.md`: 对齐 ligand-only gates, MMFF/UFF 边界, artificial split 和 anti-leakage.
- `docs/20260504-01-Clash2Feedback-GC_完整方案与升级路线.md`: 增补 artificial benchmark split 表和阶段 2 边界.
- `docs/20260508-Clash2Feedback-GC_阶段1碰撞检测器与可靠验证器方案.md`: 增补阶段 1 detector/attribution 与阶段 2 的接口说明.
- `docs/20260505-Clash2Feedback-GC_阶段0工程方案.md`: 将目录示例中的阶段 2 配置名更新为 `phase2_injection.yaml`.

## 2. 统一口径

- 阶段 2 是 controlled synthetic failed pose benchmark construction, 不是生成模型, 不是 repair, 不是稳定结合构象证明.
- 阶段 2 只把 `supported_single_rgroup` 作为阶段 3 Top-1 / Top-3 主评估来源.
- `invalid_conformer`, `near_miss_contact`, `unsupported`, `duplicate_removed` 和 reject split 必须单独报告.
- `predicted_dominant_*` 只记录, 不作为主集唯一保留条件.
- 所有 injected variants 必须继承 base complex split.

## 3. 未完全自动完成项

- visual QC 已生成抽样清单和 notes, 但人工可视化判读需要后续人工打开 SDF/sample 复核.
