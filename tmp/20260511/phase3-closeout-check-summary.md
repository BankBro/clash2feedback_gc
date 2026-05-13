# 阶段 3 收尾核查摘要

## 1. 核查结论

阶段 3 通过, 没有发现阻断阶段 4.0 的问题. 当前结果已经满足阶段 3 新口径: label provenance audit, circularity risk audit, construction consistency check, phase4 mask seed generation.

阶段 3 不应继续补做 independent locator benchmark, 不应训练模型, 不应调用生成器, 不应修复分子. 建议进入阶段 4.0, 先做 Oracle mask backend feasibility audit.

## 2. Git 状态

- 当前分支: `20260513-160230-phase3-implementation`
- 当前 commit: `8f847110a4a6b999af3b2387eb59bc26b7376942`
- 核查开始时工作区不干净: 存在未跟踪输入文档 `tmp/20260513/20260513-Clash2Feedback-GC_阶段3实验评价与收尾修补建议.md`.
- 本次未覆盖该输入文档, 未执行 commit, 未执行 push.

## 3. 阶段 3 结果核查

`reports/phase3_label_provenance_audit/summary.json` 显示:

- `S0_all_valid_injection_attempts`: 1185
- `S1_oracle_target_local_clash_set`: 467
- `S2_phase2_supported_single_rgroup`: 357
- `phase4_mask_seed.rows`: 357
- `phase4_0_backend_feasibility_candidates`: 357
- `phase4_1_formal_loop_candidates`: 357
- `predicted_equals_oracle`: 357 / 357
- `random_equals_oracle`: 0 / 357
- `random_equals_predicted`: 0 / 357
- `phase2_5_model_induced_audit.included_in_construction_consistency_denominator`: false

`construction_consistency_report.csv` 包含 2 条 construction consistency 指标:

- Top-1: 357 / 357 = 1.0
- Top-3: 357 / 357 = 1.0

两项指标均标记 `not_independent_locator_benchmark=True`, 因此只能解释为 clean local repair substrate 上的构造一致性检查.

`phase4_mask_seed.csv` 共有 357 行, oracle / predicted / random 三类 mask 全部可用, anchor, keep mask, old clash evidence 和 protein hot region 字段齐全. 该文件可作为阶段 4.0 和阶段 4.1 的输入基础.

`phase3_completion_audit.md` 已明确阶段 3 未训练模型, 未调用生成器, 未修复分子, 也未生成阶段 3 final experiment report.

## 4. 轻量收尾修补

本次新增非破坏性统计:

- `reports/phase3_label_provenance_audit/random_mask_balance_summary.csv`

该文件由现有 `phase4_mask_seed.csv` 派生, 不回写 `summary.json`, 不修改原始 CSV/JSON/Parquet/trace/JSONL 数据. 统计结果:

- 行数: 357
- `random_mask_fallback_reason=primary_exclude_oracle_and_predicted`: 357
- random vs oracle mask size 差值分布: 0 -> 127, 1 -> 26, 2 -> 118, 3 -> 86
- random vs predicted mask size 差值分布: 0 -> 127, 1 -> 26, 2 -> 118, 3 -> 86

结论: random mask 未复用 oracle/predicted, 但不是所有 case 都能精确等大小. 当前 random mask 应解释为同配体内排除 oracle/predicted 后的 size-matched 或 nearest-size 合法 R 基 baseline. 这不阻断阶段 4.0, 但阶段 4.1 报告应记录该大小差异, 必要时做按 mask size diff 的敏感性分析.

## 5. README 同步核查

- `README.md`: 已包含阶段 3 口径, 运行命令, 输出列表, mask 策略和 phase2.5 不进入 denominator 的说明.
- `configs/README.md`: 已列出 `phase3_label_provenance_audit.yaml`.
- `scripts/README.md`: 已列出 `scripts/phase3_label_provenance_audit.py` 运行入口和阶段 3 不训练/不生成/不修复边界.
- `reports/README.md`: 本次补充 `random_mask_balance_summary.csv` 的说明, 并明确该文件是收尾核查派生统计, 不回写阶段 3 核心结果.

不需要修改 `configs/README.md` 或 `scripts/README.md`, 因为本次没有新增配置或命令入口.

## 6. 禁止范围核查

本次未修改以下历史结果和数据:

- `reports/phase2_injection/`
- `reports/phase2_5_model_induced_audit/`
- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/`
- `runs/phase2_5_model_induced_audit/raw_candidates/`
- `runs/phase2_5_model_induced_audit/standardized_candidates/`

本次也未手动 patch 阶段 3 原始核心结果:

- 未修改 `reports/phase3_label_provenance_audit/summary.json`
- 未修改 `reports/phase3_label_provenance_audit/construction_consistency_report.csv`
- 未修改 `reports/phase3_label_provenance_audit/phase4_mask_seed.csv`
- 未修改 `reports/phase3_label_provenance_audit/phase3_completion_audit.md`

## 7. 后续建议

建议进入阶段 4.0. 最小顺序:

- 读取 `phase4_mask_seed.csv`, 先做字段 sanity check.
- 抽取 20-50 个 S2 case.
- 先运行 Oracle mask backend feasibility audit.
- 若 Oracle mask 下后端可行, 再进入阶段 4.1 Random / Predicted / Oracle formal repair loop.

阶段 4.1 中, 因 S2 上 predicted mask 与 oracle mask 完全一致, 核心比较应写成 Random vs Predicted/Oracle, 不应强行写成 Random < Predicted < Oracle.
