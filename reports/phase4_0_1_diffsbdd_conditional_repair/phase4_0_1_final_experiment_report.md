# 阶段 4.0.1 DiffSBDD Conditional Repair 最终实验报告

## 1. 摘要

阶段 4.0.1 已完成. 本阶段的目标是在阶段 4.0 已冻结的 40 个 selected cases 上, 只针对 `diffsbdd_conditional_inpainting` 做 reference mask 条件局部补全修补, 核查提高 candidate budget 并加入 anchor / reconnect 诊断后, DiffSBDD conditional 是否能成为更稳定的生成式局部修复后端.

本阶段主设置为:

- backend: `diffsbdd_conditional_inpainting`.
- mask: reference / oracle mask, 复用阶段 4.0 的 40 个 selected cases.
- center: `pocket`.
- candidate budget: K=8, K=16, K=32.
- 可靠修复标准: 沿用阶段 4.0 的 10 项 reliable repair candidate 标准.
- 输出目录: `reports/phase4_0_1_diffsbdd_conditional_repair/`.

最终结果:

| candidate_budget_k | selected cases | generated candidates | reliable candidates | reliable cases | sample reliable repair yield |
|---:|---:|---:|---:|---:|---:|
| 8 | 40 | 312 | 10 | 7 | 0.175 |
| 16 | 40 | 624 | 14 | 7 | 0.175 |
| 32 | 40 | 1248 | 24 | 10 | 0.250 |

K=32 相比阶段 4.0 的 `center=pocket` 单设置 7/40 多 3 个 case, 但相比阶段 4.0 `diffsbdd_conditional_inpainting` overall 的 9/40 只多 1 个 case. 因此阶段 4.0.1 是有限正结果, 不是强成功, 也不支持直接把 DiffSBDD conditional 写成阶段 4.1 主生成式后端.

阶段 4.0.1 可以关闭. DiffSBDD conditional 建议保留为生成式辅助后端和后续机制实验对象, 但不建议直接进入完整阶段 4.1 Random / Predicted / Oracle 正式掩码对照.

## 2. 实验边界

本报告基于当前仓库已有结果编写, 没有重跑 DiffSBDD, 没有重建候选, 没有覆盖阶段 4.0 或更早历史结果.

本阶段明确做了:

- 只复测 DiffSBDD conditional local inpainting.
- 只使用 reference / oracle mask.
- 只使用 `center=pocket` 主设置.
- 做 K=8, K=16, K=32 candidate budget 曲线.
- 增加 anchor-aware filtering, local reconnect check 和 generated fragment diagnostics 作为诊断 / 筛选字段.
- 所有阶段 4.0.1 结果写入独立目录.

本阶段明确没有做:

- 没有训练或微调 DiffSBDD.
- 没有修改 DiffSBDD 原始 denoising loop.
- 没有声称 `H_clash` 进入 DiffSBDD 生成过程.
- 没有重跑 `rule_fixed_topology`.
- 没有修补 DiffSBDD joint.
- 没有修补 DiffDec.
- 没有做 Random / Predicted / Oracle 正式掩码对照.
- 没有证明 predicted mask 的下游价值.
- 没有把 K=16 或 K=32 写成多轮修复.
- 没有把后处理筛选提升写成模型理解反馈.
- 没有把阶段 4.0.1 写成阶段 4.1 结论.

DiffSBDD 的 GPU inpainting 使用外部实验分支 `BankBro/DiffSBDD@20260517-080227-phase4-0-1-gpu-inpaint-fix`, patch commit `a3d49bba85d6426120759cd7b1b856d9b84471f2`. 该 patch 只在 molecule-building / SDF 写出前把 `lig_mask` 移到 CPU, 用于修复 GPU 后处理 device mismatch. 它不是模型机制改进, 不修改 denoising, 不引入 clash guidance.

## 3. 数据与可追溯性

阶段 4.0.1 复用阶段 4.0 的 40 个 selected cases, 输入来自:

- `reports/phase4_0_backend_feasibility/selected_cases.csv`.
- `reports/phase3_label_provenance_audit/phase4_mask_seed.csv`.

`phase4_mask_seed.csv` 在阶段 4.0.1 前后 SHA256 保持不变:

```text
18cea12cc4f92a8f21f6f9de83c2ba551556e35a19e9d781d3a98f79b99097cc
```

阶段 4.0.1 summary 记录:

- `selected_case_count = 40`.
- `candidate_budget_ks = [8, 16, 32]`.
- `center = pocket`.
- `backend_name = diffsbdd_conditional_inpainting`.
- `training_or_finetuning_performed = false`.
- `h_clash_used_in_diffsbdd_generation = false`.
- `diffsbdd_original_denoising_modified = false`.

## 4. 可靠修复候选定义

阶段 4.0.1 继续沿用阶段 4.0 的 10 项 reliable repair candidate 标准. 单个候选必须同时满足:

- `candidate_readable`.
- `ligand_valid`.
- `fixed_structure_match_success`.
- `old_clash_resolved`.
- `no_new_severe_clash`.
- `scaffold_stable`.
- `keep_region_stable`.
- `anchor_integrity`.
- `edit_compliance`.
- `pocket_retention`.

这意味着:

- 不是生成出来就算成功.
- 不是没有新碰撞就算成功.
- 不是 old clash resolved 单独成立就算成功.
- 不得放宽可靠修复标准来制造提升.
- anchor-aware filtering 和 local reconnect check 是新增诊断 / 筛选, 不替代 reliable repair 10 项标准.
- `local_reconnect_pass=0` 不能反向推翻已经按 10 项标准判定的 reliable candidates.

## 5. 预算曲线

主预算曲线来自 `diffsbdd_budget_curve.csv`.

| candidate_budget_k | attempt rows | proposal count | generated candidates | execution failures | reliable candidates | reliable cases | reliable case yield | reliable candidate rate | runtime sec sum |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 8 | 40 | 320 | 312 | 1 | 10 | 7 | 0.175 | 0.032051 | 349.898481 |
| 16 | 40 | 640 | 624 | 1 | 14 | 7 | 0.175 | 0.022436 | 462.216100 |
| 32 | 40 | 1280 | 1248 | 1 | 24 | 10 | 0.250 | 0.019231 | 763.258701 |

解读:

- K=8 到 K=16 只增加 reliable candidate 数, 没有增加 reliable case 数.
- K=32 将 reliable case 从 7/40 提高到 10/40.
- reliable candidate rate 随预算升高反而下降, K=32 为 24/1248 = 0.019231.
- execution failure 每档均为 1 个 attempt, 对应 `case_002599`.
- K=32 的正向增量来自更大的候选池覆盖到了少量新增成功 case, 不是模型机制变强.

K=32 相比 K=16 新增可靠 case 为:

- `case_001270`.
- `case_001316`.
- `case_001648`.
- `case_002226`.

同时 K=16 的 `case_002134` 在 K=32 下没有保留为 reliable case. 因此 K=32 增量不是简单的单调 case 级包含关系.

## 6. 与阶段 4.0 对比

阶段 4.0 中 `diffsbdd_conditional_inpainting` overall 是 9/40 reliable cases, 17 reliable candidates. 其中 `center=pocket` 单设置是 7/40 reliable cases, 12 reliable candidates.

| metric | phase4.0 conditional overall | phase4.0 center=pocket | phase4.0.1 K=8 | phase4.0.1 K=16 | phase4.0.1 K=32 |
|---|---:|---:|---:|---:|---:|
| reliable cases | 9 | 7 | 7 | 7 | 10 |
| reliable case yield | 0.225 | 0.175 | 0.175 | 0.175 | 0.250 |
| reliable candidates | 17 | 12 | 10 | 14 | 24 |
| reliable candidate rate | 0.027244 | 0.038462 | 0.032051 | 0.022436 | 0.019231 |
| anchor integrity rate | 0.403846 | 0.451923 | 0.365385 | 0.347756 | 0.369391 |
| old clash resolved rate | 0.083333 | 0.073718 | 0.096154 | 0.097756 | 0.083333 |
| no new severe clash rate | 0.088141 | 0.080128 | 0.096154 | 0.105769 | 0.088141 |

关键结论:

- 相比阶段 4.0 `center=pocket`, K=32 从 7/40 提高到 10/40, 增加 3 个 case.
- 相比阶段 4.0 conditional overall, K=32 从 9/40 提高到 10/40, 只增加 1 个 case.
- K=32 的 reliable candidate 数比阶段 4.0 overall 多 7 个, 但 candidate rate 从 0.027244 降到 0.019231.
- 阶段 4.0.1 的收益主要来自提高候选预算和后验筛选覆盖, 不应解释为 DiffSBDD 已经理解 clash feedback.

## 7. Failure Funnel 分析

候选读取和 fixed structure match 不是主要瓶颈:

| candidate_budget_k | candidate_readable | fixed_structure_match_success | ligand_valid |
|---:|---:|---:|---:|
| 8 | 312/312 | 312/312 | 270/312 |
| 16 | 624/624 | 624/624 | 565/624 |
| 32 | 1248/1248 | 1248/1248 | 1092/1248 |

主要瓶颈集中在 old clash resolution, no new severe clash, anchor integrity 和 local reconnect:

| candidate_budget_k | anchor_integrity | old_clash_resolved | no_new_severe_clash | local_reconnect_pass | reliable_success |
|---:|---:|---:|---:|---:|---:|
| 8 | 114/312 | 30/312 | 30/312 | 0/312 | 10/312 |
| 16 | 217/624 | 61/624 | 66/624 | 0/624 | 14/624 |
| 32 | 461/1248 | 104/1248 | 110/1248 | 0/1248 | 24/1248 |

解读:

- `candidate_readable=1.0` 和 `fixed_structure_match_success=1.0` 说明 SDF 读取和统一 verifier 映射链路不是本阶段主障碍.
- `old_clash_resolved` 在 K=32 仍只有 104/1248 = 0.083333.
- `no_new_severe_clash` 在 K=32 仍只有 110/1248 = 0.088141.
- `anchor_integrity` 在 K=32 为 461/1248 = 0.369391, 连接点和局部拓扑保持仍不稳定.
- `local_reconnect_pass` 三档均为 0, 指向更严格的局部接回质量问题.

因此, DiffSBDD conditional 当前能偶发产生 reliable repair, 但多数候选仍卡在“生成片段是否正确接回原局部结构并同时解决旧碰撞”这一组合问题上.

## 8. Closeout Audit 与 Local Reconnect 诊断

`phase4_0_1_closeout_audit.md` 已核查 `diffsbdd_anchor_reconnect_audit.csv` 的完整性. 结论是:

- `diffsbdd_anchor_reconnect_audit.csv` 不是空表.
- `diffsbdd_candidate_manifest.csv`, `diffsbdd_verifier_outcome.csv`, `diffsbdd_anchor_reconnect_audit.csv` 均有 2,187 条数据记录.
- 这 2,187 条记录中包含 2,184 条候选级记录和 3 条 execution failure 记录.
- `local_reconnect_pass_count=0` 可追溯到候选级 diagnostics / verifier 字段, 不是缺失表导致的聚合占位值.
- 本次 closeout audit 没有重跑 DiffSBDD, 没有重建候选, 没有修改阶段 4.0 或更早历史结果.

主要 local reconnect failure reason 为:

| reason | count |
|---|---:|
| `not_connected_to_anchor` | 1037 |
| `floating_fragment` | 519 |
| `extra_attachments=4` | 102 |
| `extra_attachments=5` | 99 |
| `extra_attachments=3` | 87 |
| `extra_attachments=6` | 72 |
| `extra_attachments=2` | 59 |
| `extra_attachments=7` | 49 |
| `extra_attachments=8` | 43 |
| `extra_attachments=1` | 40 |

这些诊断说明 DiffSBDD conditional 在 reference mask 下生成的局部片段经常出现未接回 anchor, 漂浮片段, 或 attachment 数异常. 这不是读取失败, 而是局部接回质量和化学拓扑一致性问题.

需要强调的是, local reconnect check 是阶段 4.0.1 新增诊断, 不属于阶段 4.0 的 10 项 reliable repair 标准. 因此 `local_reconnect_pass=0` 应用于解释失败漏斗和设计后续筛选 / calibration, 不能用于回头否定已经按 10 项标准判定的 reliable candidates.

## 9. 外部 DiffSBDD Patch 解释

阶段 4.0.1 使用的外部 DiffSBDD patch 信息记录在 `docs/external_baselines.md` 和 `phase4_0_1_summary.json`.

```text
External repo: BankBro/DiffSBDD
Branch: 20260517-080227-phase4-0-1-gpu-inpaint-fix
Patch commit: a3d49bba85d6426120759cd7b1b856d9b84471f2
Patch scope: move lig_mask to CPU before batch_to_list in molecule-building post-processing
Denoising change: no
```

该 patch 的作用是让 GPU inpainting 能完成 molecule-building / SDF 写出, 避免 CPU tensor 使用 CUDA mask 的后处理错误. 它没有改变 DiffSBDD 的原始采样分布, 没有引入 feedback guidance, 也没有让 `H_clash` 进入生成过程.

因此, 阶段 4.0.1 的提升不能写成模型机制改进. 更准确的表述是: 在修复 GPU 后处理 bug 后, 通过 `center=pocket` 和更大的候选预算观察到有限的候选池覆盖增益.

## 10. 风险与局限

- 本阶段只使用 reference mask, 不能证明 predicted mask 的下游价值.
- 本阶段只评估 DiffSBDD conditional, 没有与 Random / Predicted / Oracle 做正式对照.
- K=32 的 10/40 是有限正结果, 但 reliable candidate rate 仍低.
- `local_reconnect_pass=0` 表明新增的更严格局部接回诊断下, 候选级接回质量仍非常弱.
- local reconnect check 与阶段 4.0 的 reliable repair 标准不是同一套成功定义, 不能混用为主指标.
- K=16 / K=32 是单次生成的候选预算曲线, 不是多轮修复.
- DiffSBDD 原模型未接收 `H_clash`, 当前结果不代表 feedback-guided generation 已跑通.
- 外部 checkpoint, raw candidates 和日志缓存仍属于本地重资产, 不应提交 Git.

## 11. 最终结论

阶段 4.0.1 可以关闭.

本阶段给出的最强正面结论是: 在 reference mask, `center=pocket`, K=32 的设置下, DiffSBDD conditional 可以达到 10/40 reliable cases, 相比阶段 4.0 `center=pocket` 单设置的 7/40 有 3 个 case 增量.

但本阶段同时显示:

- 相比阶段 4.0 conditional overall 的 9/40, K=32 只多 1 个 case.
- K=32 的 reliable candidate rate 只有 0.019231.
- old clash resolution, no new severe clash, anchor integrity 和 local reconnect 仍是主瓶颈.
- local reconnect 诊断显示大量 `not_connected_to_anchor`, `floating_fragment` 和 `extra_attachments`.

因此, DiffSBDD conditional 应保留为生成式辅助后端和后续机制修补对象, 但不建议直接作为阶段 4.1 主生成式后端. 阶段 4.0.1 不应被写成阶段 4.1 已完成, 也不应被写成 predicted mask 有下游价值.

## 12. 后续建议

建议优先做:

1. 进入 phase4.0.2 DiffDec adapter 3-5 case 预检, 重点核查 input adapter, anchor/scaffold mapping, generated R-group size 和 candidate mapping.
2. 为 DiffSBDD conditional 补做 local reconnect calibration, 明确 local reconnect 与阶段 4.0 10 项 reliable repair 标准之间的关系, 避免新增诊断和主指标混用.
3. 单独设计 DiffSBDD sampling / guidance 最小实验, 只在明确修改 sampling 或 guidance 后再讨论 `H_clash` 是否进入生成过程.
4. 暂不直接进入完整阶段 4.1 Random / Predicted / Oracle 正式掩码对照.
5. 暂不把 rule fixed topology 的高成功率作为生成式主线结论, 它仍应作为构象型强基线和 sanity check.

如果后续目标是生成式主线, 更合理的路线是先完成生成式 adapter / reconnect / guidance 的小规模可证伪实验, 再决定是否进入阶段 4.1.

## 13. 主要依据文件

- `tmp/20260517/phase4-0-1-diffsbdd-conditional-repair-expt-report.md`.
- `reports/phase4_0_1_diffsbdd_conditional_repair/phase4_0_1_summary.json`.
- `reports/phase4_0_1_diffsbdd_conditional_repair/diffsbdd_budget_curve.csv`.
- `reports/phase4_0_1_diffsbdd_conditional_repair/diffsbdd_failure_funnel.csv`.
- `reports/phase4_0_1_diffsbdd_conditional_repair/phase4_0_vs_4_0_1_comparison.csv`.
- `reports/phase4_0_1_diffsbdd_conditional_repair/diffsbdd_case_level_summary.csv`.
- `reports/phase4_0_1_diffsbdd_conditional_repair/diffsbdd_anchor_reconnect_audit.csv`.
- `reports/phase4_0_1_diffsbdd_conditional_repair/phase4_0_1_closeout_audit.md`.
- `reports/phase4_0_1_diffsbdd_conditional_repair/phase4_0_1_completion_audit.md`.
- `reports/phase4_0_backend_feasibility/phase4_0_final_experiment_report.md`.
- `reports/phase4_0_backend_feasibility/backend_comparison.csv`.
- `reports/phase4_0_backend_feasibility/diffsbdd_center_sensitivity.csv`.
- `configs/phase4_0_1_diffsbdd_conditional_repair.yaml`.
- `docs/external_baselines.md`.
