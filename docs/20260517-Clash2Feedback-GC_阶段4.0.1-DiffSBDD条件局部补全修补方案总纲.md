# Clash2Feedback-GC 阶段 4.0.1：DiffSBDD 条件局部补全修补方案总纲

> 建议放置路径：`docs/20260517-Clash2Feedback-GC_阶段4.0.1-DiffSBDD条件局部补全修补方案总纲.md`  
> 文档定位：阶段 4.0.1 的方案总纲 / 上位约束  
> 阶段短名：`phase4-0-1-diffsbdd-conditional-repair`  
> 重要说明：网页 ChatGPT 仅负责生成方案和交接材料，未在本地执行命令、未跑实验、未修改仓库。凡涉及真实路径、字段、结果、样本数、候选数、检查点、环境状态、测试结果和最终结论，均以后续本地 Codex 在真实仓库中的核查结果为准。若本文件与仓库事实冲突，必须先生成冲突报告，不得继续执行冲突部分。

---

## 0. 一句话定位

阶段 4.0.1 是：

> 在阶段 4.0 已经完成并关闭的基础上，专门修补 `diffsbdd_conditional_inpainting` 这个生成式局部补全后端，分析它为什么在参考掩码条件下只有有限可靠成功，并尝试通过输入适配、连接点感知筛选、局部接回检查、候选预算曲线和失败漏斗，让它变得更稳定、更可解释。

本阶段只做 **DiffSBDD 条件局部补全修补**。

本阶段不做：

```text
不做 DiffDec adapter 修补；
不修 DiffSBDD joint；
不做新生成基座调研；
不做规则型掩码 sanity check；
不做 Random / Predicted / Oracle 正式掩码对照；
不训练或微调 DiffSBDD；
不修改 DiffSBDD 原始去噪过程；
不声称 H_clash 已进入 DiffSBDD 生成过程。
```

---

## 1. 动机

### 1.1 阶段 4.0 已经回答了什么

阶段 4.0 已完成“参考掩码条件下的多后端修复可行性审计”。其核心口径是：

```text
给定正确参考修复区域后，审计不同 repair backend 是否能生成可读取、可验证、局部可靠的修复候选。
```

阶段 4.0 最终报告显示：

```text
rule_fixed_topology：38/40 case 可靠成功，但它是构象型强基线，不是生成式主方法；
diffsbdd_conditional_inpainting：9/40 case 可靠成功，是当前唯一有非零可靠成功的生成式局部补全后端；
diffdec_single_rgroup：环境、checkpoint、GPU formal run 已跑通，但 0 reliable success，后续拆到阶段 4.0.2；
diffsbdd_full_resampling：只能作为全配体重采样对照，不是局部修复后端；
diffsbdd_joint_inpainting：blocked，不影响阶段 4.0 关闭。
```

阶段 4.0 的结论说明：

```text
当前生成式局部修复主线还没有成熟；
DiffSBDD conditional 已有非零可行性，但 anchor / reconnect / old clash resolution 不稳定；
如果想继续生成式修复路线，最优先应该修补 DiffSBDD conditional，而不是继续扩大规则型方法。
```

### 1.2 为什么阶段 4.0.1 只修 DiffSBDD conditional

选择 `diffsbdd_conditional_inpainting` 作为阶段 4.0.1 的唯一对象，原因是：

```text
1. 它已经有 9/40 case 可靠成功，是当前最接近可用的生成式后端；
2. 它已经能调用 DiffSBDD 条件模型、生成候选、进入统一 verifier；
3. 它的问题更像“连接点、候选后处理、预算和适配稳定性不足”，有短期修补价值；
4. 它比 DiffDec 更接近可用，DiffDec 0 success 的 adapter 问题应拆成阶段 4.0.2；
5. DiffSBDD joint 当前 blocked，不应阻塞 conditional 修补；
6. 规则型方法已经证明构象可逆性，但不能作为生成式主线。
```

### 1.3 本阶段要避免的问题

阶段 4.0.1 不应重新变成一个“大杂烩”阶段。

本阶段只回答：

```text
DiffSBDD conditional 这个生成式局部补全后端，能否通过更清楚的输入适配、连接点筛选、局部接回检查和候选预算扩展，提升或至少解释其参考掩码下的可靠修复能力？
```

不回答：

```text
DiffDec 是否可用；
joint checkpoint 是否能接通；
新生成基座是否更好；
自动掩码是否比随机掩码更有价值；
规则型修复是否仍然更强；
H_clash 是否能进入扩散去噪过程。
```

---

## 2. 本阶段最终目标

阶段 4.0.1 的最终目标是：

> 在不训练模型、不微调模型、不修改 DiffSBDD 原始去噪过程的前提下，使 DiffSBDD 条件局部补全后端在参考掩码条件下形成更清楚、更稳定、更可解释的局部修复链路。

具体目标包括：

```text
1. 复用阶段 4.0 的 40 个 selected cases，与阶段 4.0 DiffSBDD conditional 原结果公平对比；
2. 优先使用 center=pocket 作为主设置；
3. 先做 5 case preflight，确认新增字段、adapter、filter、verifier 和报告 schema 能跑通；
4. 做 K=8 / 16 / 32 单轮候选预算曲线；
5. 增加 anchor-aware filtering；
6. 增加 local reconnect check；
7. 增加 generated fragment 诊断；
8. 输出 DiffSBDD conditional 失败漏斗；
9. 判断 DiffSBDD conditional 是否值得进入后续生成式主线；
10. 若无提升，也要明确失败瓶颈，决定是否转入阶段 4.0.2 DiffDec adapter 或阶段 4.0.4 新基座调研。
```

---

## 3. 明确成功标准

### 3.1 最低成功标准

满足以下条件，即可认为阶段 4.0.1 有价值：

```text
1. 不覆盖阶段 4.0 的任何历史结果；
2. 成功复用阶段 4.0 的 40 个 selected cases；
3. 完成 5 case preflight；
4. 完成 center=pocket 主设置；
5. 完成 K=8 / 16 / 32 预算曲线；
6. 输出完整 DiffSBDD conditional failure funnel；
7. 能区分 anchor failure、reconnect failure、old clash not resolved、new severe clash、mapping failure 等主要失败环节；
8. 输出 case-level failure summary；
9. 输出 phase4_0 vs phase4_0_1 对比表；
10. 所有新增报告字段有定义；
11. compileall 和阶段 4.0.1 相关测试通过，或如实说明无法运行原因。
```

注意：最低成功标准不要求可靠成功率一定提升。即使成功率没有提升，只要失败原因被拆清楚，也能判断 DiffSBDD conditional 是否值得继续投入。

### 3.2 推荐成功标准

推荐目标是：

```text
1. K=8 下结果不低于阶段 4.0 原始 DiffSBDD conditional；
2. K=16 或 K=32 下 sample reliable success 明显高于阶段 4.0 的 9/40；
3. 建议阶段性目标：达到至少 12/40 case 可靠成功；
4. reliable candidate 数量明显增加；
5. anchor / reconnect 相关失败比例下降；
6. old_clash_resolved 候选数量增加；
7. 没有通过放宽 reliable repair 标准制造提升。
```

其中 `12/40` 是推荐目标，不是硬性关闭条件。若未达到，但失败原因清楚，本阶段仍可关闭为负结果或限制性结果。

### 3.3 强成功标准

若达到以下结果，可以考虑让 DiffSBDD conditional 进入后续生成式主线：

```text
1. K=16 或 K=32 下达到约 15/40 case 可靠成功；
2. anchor-aware filtering 后 reliable candidate 质量明显提高；
3. old_clash_resolved 和 no_new_severe_clash 同时改善；
4. 失败原因不再主要来自 adapter / reconnect；
5. 结果可复现，且不依赖人工挑选成功 case。
```

### 3.4 失败判据

如果出现以下情况，则阶段 4.0.1 应关闭为负结果：

```text
1. K=32 仍基本不超过阶段 4.0 的 9/40；
2. old_clash_resolved 仍然很低；
3. anchor / reconnect 大量失败；
4. 成功主要集中在阶段 4.0 已成功的少量 case；
5. 候选预算扩大只增加无效候选；
6. 后处理无法修补模型局部生成本身的问题。
```

负结果的结论应写成：

> DiffSBDD conditional 可作为生成式局部补全辅助后端，但不适合作为阶段 4.1 的生成式主后端。

---

## 4. 阶段边界

### 4.1 本阶段做什么

阶段 4.0.1 做：

```text
1. 读取阶段 4.0 最终报告、候选表、验证器结果和收尾诊断；
2. 核查 DiffSBDD conditional 在阶段 4.0 的真实字段、候选、center、失败原因和结果；
3. 复用阶段 4.0 的 40 个 selected cases；
4. 只测试 diffsbdd_conditional_inpainting；
5. 主设置使用 center=pocket；
6. 做 K=8 / 16 / 32 单轮候选预算曲线；
7. 增加 anchor-aware filtering；
8. 增加 local reconnect check；
9. 增加 generated fragment 连接诊断；
10. 输出 DiffSBDD conditional failure funnel；
11. 输出与阶段 4.0 原始 DiffSBDD conditional 的对比；
12. 输出阶段 4.0.1 临时实验汇报文档；
13. 判断是否可以进入后续生成式主线。
```

### 4.2 本阶段不做什么

阶段 4.0.1 不做：

```text
不重跑 rule_fixed_topology；
不修 DiffDec；
不修 DiffSBDD joint；
不做新生成基座调研；
不做 Random / Predicted / Oracle 正式对照；
不训练 DiffSBDD；
不微调 DiffSBDD；
不修改 DiffSBDD 原始源码和去噪过程；
不实现 clash-guided denoising；
不声称 H_clash 进入生成过程；
不把 Vina / docking score 作为主指标；
不覆盖阶段 4.0 原始结果；
不修改 phase4_mask_seed.csv；
不修改阶段 2 / 2.5 / 3 / 4.0 历史结果；
不生成阶段 4.1 正式方案。
```

---

## 5. 核心假设

### 5.1 可采用假设

阶段 4.0.1 可以采用以下假设：

```text
1. DiffSBDD conditional 已具备基础局部补全能力，因为阶段 4.0 中已有非零可靠成功；
2. center=pocket 当前比 center=ligand 更值得优先修补；
3. 一部分失败可能来自后处理、连接点筛选、局部接回检查和候选预算不足；
4. 扩大候选预算可能提高可靠修复覆盖率；
5. anchor-aware filtering 可以提高最终候选质量，但不能改变模型本身生成分布；
6. 若 K 扩大仍无提升，说明瓶颈可能在模型生成分布、连接约束或适配接口，而不是候选数量。
```

### 5.2 不允许采用假设

阶段 4.0.1 不允许采用以下假设：

```text
1. DiffSBDD conditional 已经是成熟主后端；
2. 只要候选无碰撞就算修复成功；
3. 只要 K 变大，成功率一定提升；
4. H_clash 已经进入 DiffSBDD 生成过程；
5. 阶段 4.0.1 能证明 predicted mask 有下游价值；
6. 阶段 4.0.1 能替代阶段 4.1；
7. anchor-aware filtering 可以被解释为模型主动理解了 anchor；
8. 后处理筛选带来的提升可以写成生成过程被反馈引导。
```

---

## 6. 事实依据与结果来源

### 6.1 已有事实来源

本阶段依赖以下阶段 4.0 事实和报告，但所有数字需由本地 Codex 重新核查：

```text
reports/phase4_0_backend_feasibility/phase4_0_final_experiment_report.md
reports/phase4_0_backend_feasibility/phase4_0_small_scale_summary.json
reports/phase4_0_backend_feasibility/backend_comparison.csv
reports/phase4_0_backend_feasibility/backend_comparison_rates.csv
reports/phase4_0_backend_feasibility/verifier_outcome.csv
reports/phase4_0_backend_feasibility/candidate_manifest.csv
reports/phase4_0_backend_feasibility/adapter_input_manifest.csv
reports/phase4_0_backend_feasibility/selected_cases.csv
reports/phase4_0_backend_feasibility/diffsbdd_center_sensitivity.csv
reports/phase4_0_backend_feasibility/diffsbdd_center_sensitivity.md
```

### 6.2 本地 Codex 必须核查的阶段 4.0 结果

本地 Codex 必须核查：

```text
1. 阶段 4.0 final report 是否存在；
2. 阶段 4.0 selected_cases.csv 是否存在且为 40 个 case；
3. diffsbdd_conditional_inpainting 在阶段 4.0 中的真实 candidate_count、reliable_candidate_count、sample_success_count；
4. center=ligand / center=pocket 的字段是否能从 candidate_manifest 或 generation metadata 中可靠恢复；
5. phase4_0 中 center=pocket 的 sample success 是否确实优于 center=ligand；
6. 阶段 4.0 可靠修复 10 项标准是否仍由 phase4_adapter.py 定义；
7. `H_clash` 是否确实没有进入 DiffSBDD 生成过程；
8. DiffSBDD 条件模型 checkpoint、外部仓库、环境记录是否可用；
9. 阶段 4.0 原始结果是否可以作为对照，而不被覆盖。
```

### 6.3 本地 Codex 必须核查的代码与配置

```text
configs/phase4_0_backend_feasibility.yaml
scripts/phase4_0_backend_feasibility.py
scripts/phase4_0_closeout_diagnostics.py
src/clash2feedback/repair/diffsbdd_adapter.py
src/clash2feedback/verifier/phase4_adapter.py
tests/test_phase4_backend_feasibility.py
```

可能需要新增或扩展：

```text
configs/phase4_0_1_diffsbdd_conditional_repair.yaml
scripts/phase4_0_1_diffsbdd_conditional_repair.py
src/clash2feedback/repair/diffsbdd_anchor_filter.py
src/clash2feedback/repair/reconnect_check.py
src/clash2feedback/repair/fragment_diagnostics.py
tests/test_phase4_0_1_diffsbdd_conditional.py
```

以上新增路径只是方案建议，需由 Codex 根据仓库实际结构映射。

---

## 7. 具体原理和做法

### 7.1 主体思路

阶段 4.0.1 的完整流程为：

```text
读取阶段 4.0 selected_cases
→ 读取 reference / oracle mask
→ 使用 DiffSBDD conditional inpainting
→ 主设置 center=pocket
→ 单轮生成 K=8 / 16 / 32 候选
→ 对候选做 anchor-aware filtering
→ 做 local reconnect check
→ 做 generated fragment 诊断
→ 调用统一 phase4 verifier
→ 输出 failure funnel 和预算曲线
→ 与阶段 4.0 原始 DiffSBDD conditional 结果对比
```

### 7.2 样本设计

主实验复用阶段 4.0 的正式 40 个样本：

```text
reports/phase4_0_backend_feasibility/selected_cases.csv
```

复用原因：

```text
1. 可以和阶段 4.0 DiffSBDD conditional 原始结果公平对比；
2. 不引入新的样本选择偏差；
3. 不把样本变化误写成方法提升；
4. 不需要重新定义阶段 4.0 的 denominator；
5. 有利于分析每个 case 的失败类型变化。
```

本阶段不直接扩大到 S2 全量 357 case。

### 7.3 5 case preflight

正式 40 case 前，先做 5 case preflight。

建议选择：

```text
1. 一个阶段 4.0 DiffSBDD conditional 成功 case；
2. 一个 center=pocket 成功但 center=ligand 失败 case；
3. 一个 anchor_integrity 失败 case；
4. 一个 old_clash_resolved 失败 case；
5. 一个 no_new_severe_clash 失败 case。
```

若真实字段无法准确恢复上述分类，Codex 应在 plan 中提出替代选择规则，不得编造 case。

preflight 目标：

```text
1. 新增字段能生成；
2. anchor-aware filtering 能跑；
3. local reconnect check 能跑；
4. 候选能进入 verifier；
5. K 设置能生效；
6. 报告 schema 能写出；
7. 不覆盖阶段 4.0 历史结果。
```

### 7.4 center 设置

主设置：

```text
center = pocket
```

原因：

```text
1. 阶段 4.0 中 center=pocket 表现优于 center=ligand；
2. 阶段 4.0.1 目标是修最接近可用的设置；
3. 本阶段不是重新做 center 大对比；
4. center=ligand 结果可作为阶段 4.0 历史对照，不作为本阶段主线。
```

若 Codex 发现阶段 4.0 的 center 字段无法可靠映射，必须先在 plan 中记录 schema 风险，并给出处理建议。

### 7.5 候选预算曲线

预算设置：

```text
K = 8
K = 16
K = 32
```

解释：

```text
K=8：和阶段 4.0 原始预算公平对比；
K=16 / K=32：判断候选预算增加是否提升 reliable repair yield；
所有 K 均为单轮多候选生成，不是多轮迭代修复。
```

必须记录：

```text
candidate_budget_k
attempt_count
proposal_count
candidate_count
runtime_sec
candidate_readable_count
reliable_candidate_count
sample_reliable_success
cost_per_reliable_case
```

### 7.6 anchor-aware filtering

新增连接点感知筛选。候选至少应检查：

```text
1. 候选是否能读取；
2. 候选是否为单主片段；
3. 固定结构是否能匹配；
4. scaffold anchor atom 是否能在候选中恢复；
5. 新生成局部是否接回 anchor；
6. anchor 附近是否存在合理连接或距离关系；
7. generated fragment 是否漂移到 pocket 外；
8. generated fragment 是否出现孤立小片段；
9. generated fragment 大小是否过大或过小；
10. 候选是否能进入统一 verifier。
```

建议新增字段：

```text
anchor_candidate_idx
anchor_match_success
generated_fragment_connected_to_anchor
generated_fragment_attachment_count
candidate_single_fragment
candidate_extra_fragment_count
anchor_bond_like_distance
anchor_reconnect_status
anchor_reconnect_reason
```

这些字段用于诊断和筛选，不得替代可靠修复 10 项标准。

### 7.7 local reconnect check

local reconnect check 用于判断局部补全片段是否真的接回固定结构。

检查内容：

```text
1. scaffold anchor atom 是否仍在候选中；
2. generated fragment 是否与 scaffold 存在单一主连接；
3. 是否出现多个 attachment；
4. 是否出现未接回 scaffold 的 floating fragment；
5. 新片段与 anchor 的距离是否合理；
6. 候选是否能被统一 verifier 映射回原始任务语义；
7. 是否存在额外孤立小分子片段。
```

建议输出字段：

```text
local_reconnect_pass
local_reconnect_failure_reason
num_generated_components
num_anchor_neighbors
num_extra_attachments
floating_fragment_detected
```

### 7.8 generated fragment 诊断

新增局部生成片段诊断字段：

```text
target_mask_heavy_atom_count
generated_fragment_heavy_atom_count
generated_fragment_size_diff
generated_fragment_elements
target_mask_elements
generated_element_mismatch_count
generated_size_status
```

这些字段用于解释失败原因，不直接定义成功。

### 7.9 失败漏斗

必须输出 DiffSBDD conditional failure funnel：

```text
attempted_cases
execution_success
generated_candidates
candidate_readable
ligand_valid
fixed_structure_match_success
anchor_match_success
local_reconnect_pass
anchor_integrity
old_clash_resolved
no_new_severe_clash
scaffold_stable
keep_region_stable
edit_compliance
pocket_retention
reliable_repair_success
```

失败漏斗用于回答：

```text
DiffSBDD conditional 到底卡在生成、读取、连接点、旧碰撞、新碰撞、结构保持还是口袋保持？
```

### 7.10 可靠修复成功标准

阶段 4.0.1 继续沿用阶段 4.0 的 10 项可靠修复标准：

```text
candidate_readable
ligand_valid
fixed_structure_match_success
old_clash_resolved
no_new_severe_clash
scaffold_stable
keep_region_stable
anchor_integrity
edit_compliance
pocket_retention
```

必须明确：

```text
不是生成出来就算成功；
不是没有新碰撞就算成功；
不是 old clash resolved 单独成立就算成功；
必须 10 项全部通过，才是 reliable repair candidate。
```

本阶段不得放宽可靠修复标准来制造提升。

---

## 8. 输入与输出

### 8.1 输入

阶段 4.0.1 输入包括：

```text
docs/20260517-Clash2Feedback-GC_阶段4.0.1-DiffSBDD条件局部补全修补方案总纲.md

reports/phase4_0_backend_feasibility/phase4_0_final_experiment_report.md
reports/phase4_0_backend_feasibility/selected_cases.csv
reports/phase4_0_backend_feasibility/candidate_manifest.csv
reports/phase4_0_backend_feasibility/verifier_outcome.csv
reports/phase4_0_backend_feasibility/backend_comparison.csv
reports/phase4_0_backend_feasibility/backend_comparison_rates.csv
reports/phase4_0_backend_feasibility/diffsbdd_center_sensitivity.csv
reports/phase4_0_backend_feasibility/diffsbdd_center_sensitivity.md

reports/phase3_label_provenance_audit/phase4_mask_seed.csv

configs/phase4_0_backend_feasibility.yaml
scripts/phase4_0_backend_feasibility.py
src/clash2feedback/repair/diffsbdd_adapter.py
src/clash2feedback/verifier/phase4_adapter.py
```

### 8.2 输出目录

本阶段必须使用新目录，不得覆盖阶段 4.0：

```text
reports/phase4_0_1_diffsbdd_conditional_repair/
runs/phase4_0_1_diffsbdd_conditional_repair/
```

### 8.3 建议输出文件

报告目录建议：

```text
reports/phase4_0_1_diffsbdd_conditional_repair/
  selected_cases.csv
  preflight_cases.csv
  phase4_0_1_summary.json
  diffsbdd_budget_curve.csv
  diffsbdd_failure_funnel.csv
  diffsbdd_anchor_reconnect_audit.csv
  diffsbdd_candidate_manifest.csv
  diffsbdd_verifier_outcome.csv
  diffsbdd_failure_cases.csv
  diffsbdd_case_level_summary.csv
  phase4_0_vs_4_0_1_comparison.csv
  phase4_0_1_completion_audit.md
```

根据用户当前要求，实验完成后只生成临时实验汇报文档：

```text
tmp/20260517/phase4-0-1-diffsbdd-conditional-repair-expt-report.md
```

注意：

```text
本阶段不生成正式 final report；
本阶段只生成临时 expt-report，用于网页 ChatGPT 后续分析；
若后续确认收尾，再另行生成正式报告。
```

运行目录建议：

```text
runs/phase4_0_1_diffsbdd_conditional_repair/
  preflight/
  k8/
  k16/
  k32/
  logs/
  raw_candidates/
  standardized_candidates/
```

重资产候选 SDF、日志和 raw candidates 不建议提交 Git。

---

## 9. 对阶段 4.0 的对比方式

阶段 4.0.1 不能覆盖阶段 4.0 结果。

应新增对比表：

```text
reports/phase4_0_1_diffsbdd_conditional_repair/phase4_0_vs_4_0_1_comparison.csv
```

建议字段：

```text
metric
phase4_0_diffsbdd_conditional
phase4_0_1_k8
phase4_0_1_k16
phase4_0_1_k32
delta_k8
delta_k16
delta_k32
notes
```

重点比较：

```text
sample_reliable_success_count
sample_reliable_repair_yield
reliable_candidate_success_count
reliable_candidate_rate
anchor_integrity_rate
local_reconnect_pass_rate
old_clash_resolved_rate
no_new_severe_clash_rate
cost_per_reliable_case
runtime_per_case
```

---

## 10. 硬约束

阶段 4.0.1 必须遵守：

```text
1. 不覆盖阶段 4.0 历史结果；
2. 不修改阶段 4.0 final report；
3. 不修改 reports/phase4_0_backend_feasibility/ 下已有主结果表；
4. 不修改 phase4_mask_seed.csv；
5. 不修改阶段 2 / 2.5 / 3 的历史结果；
6. 不重跑 rule_fixed_topology；
7. 不修 DiffDec；
8. 不修 DiffSBDD joint；
9. 不做新生成基座调研；
10. 不做 Random / Predicted / Oracle 正式对照；
11. 不训练或微调 DiffSBDD；
12. 不修改 DiffSBDD 原始去噪过程；
13. 不声称 H_clash 进入 DiffSBDD 生成过程；
14. 不把 K=16 / K=32 写成多轮修复；
15. 不把后处理筛选提升写成模型本身理解反馈；
16. 不把本阶段结果直接写成阶段 4.1 结论；
17. 不提交 external/DiffSBDD、checkpoint、大量候选 SDF 或日志缓存。
```

---

## 11. 禁止修改范围

本地 Codex 执行时禁止修改：

```text
reports/phase2_injection/
reports/phase2_5_model_induced_audit/
reports/phase3_label_provenance_audit/phase4_mask_seed.csv
reports/phase4_0_backend_feasibility/phase4_0_final_experiment_report.md
reports/phase4_0_backend_feasibility/backend_comparison.csv
reports/phase4_0_backend_feasibility/backend_comparison_rates.csv
reports/phase4_0_backend_feasibility/candidate_manifest.csv
reports/phase4_0_backend_feasibility/verifier_outcome.csv
data/benchmarks/clashrepairbench_rg_artificial/v0_1/
external/DiffSBDD/
```

允许读取上述文件，但不得覆盖、回写、重命名或静默修改。

新增结果必须写入：

```text
reports/phase4_0_1_diffsbdd_conditional_repair/
runs/phase4_0_1_diffsbdd_conditional_repair/
tmp/20260517/
```

---

## 12. 风险与局限

### 12.1 K 增大但成功率不提升

解释：

```text
说明瓶颈不是候选预算，而是模型生成分布、连接点约束或局部补全语义。
```

处理：

```text
记录预算曲线；
不要继续盲目扩大 K；
转入阶段 4.0.2 DiffDec adapter 或阶段 4.0.4 新基座调研。
```

### 12.2 anchor-aware filtering 让成功数下降

解释：

```text
原有候选可能只是表面通过部分检查，连接点并不稳定。
```

处理：

```text
保持严格标准；
不要为了成功率放宽 anchor；
将结果写成连接点瓶颈。
```

### 12.3 local reconnect check 与 phase4 verifier 冲突

解释：

```text
新增局部接回诊断可能与现有 verifier 的 atom mapping / fixed structure 逻辑存在口径差异。
```

处理：

```text
优先不改变 reliable repair 定义；
把 reconnect check 作为诊断字段；
如需改变 verifier adapter，必须在 plan 中明确说明并等待确认。
```

### 12.4 center=pocket 仍不稳定

解释：

```text
center=pocket 虽优于 center=ligand，但 center 选择可能不是主要瓶颈。
```

处理：

```text
保留阶段 4.0 center 对照；
若无提升，说明应转向其他生成后端或模型基座。
```

### 12.5 DiffSBDD 原版不支持强 anchor 约束

解释：

```text
这是模型接口边界，不是本阶段实现错误。
```

处理：

```text
报告中明确 DiffSBDD conditional 只是候选局部补全后端；
不能写成完整结构化 clash feedback 已进入生成过程。
```

---

## 13. 完成标准 checklist

阶段 4.0.1 完成时，应满足：

```text
[ ] 已读取阶段 4.0 最终报告和必要结果表；
[ ] 已确认阶段 4.0 原始结果未被覆盖；
[ ] 已固定 40 case 复测集合；
[ ] 已完成 5 case preflight；
[ ] 已完成 center=pocket 主设置；
[ ] 已完成 K=8 / 16 / 32 预算曲线；
[ ] 已新增 anchor-aware filtering；
[ ] 已新增 local reconnect check；
[ ] 已输出 generated fragment 诊断；
[ ] 已输出 DiffSBDD failure funnel；
[ ] 已输出 case-level failure summary；
[ ] 已输出 phase4_0_vs_4_0_1 comparison；
[ ] 已生成 phase4_0_1_completion_audit.md；
[ ] 已生成 tmp/20260517/phase4-0-1-diffsbdd-conditional-repair-expt-report.md；
[ ] 已明确 DiffSBDD conditional 是否建议进入后续生成式主线；
[ ] 未修改 phase4_mask_seed.csv；
[ ] 未修改阶段 2 / 2.5 / 3 / 4.0 历史结果；
[ ] 未修改 DiffSBDD 原始去噪过程；
[ ] compileall 通过；
[ ] pytest 通过或说明无法运行原因。
```

---

## 14. 阶段结束后的决策

### 情况 A：DiffSBDD 明显提升

如果：

```text
K=16 / K=32 后可靠成功明显高于 9/40；
anchor / reconnect 失败下降；
旧碰撞消除更多；
```

则下一步可以考虑：

```text
1. 继续做阶段 4.0.2 DiffDec adapter，对比另一个生成式后端；
2. 或设计阶段 4.1 生成式 mini，但仍需谨慎定义 Random / Predicted / Oracle 对照。
```

### 情况 B：DiffSBDD 无明显提升，但失败原因清楚

如果：

```text
失败主要集中在 anchor / reconnect / old clash not resolved；
K 扩大无效；
```

则结论：

```text
DiffSBDD conditional 不适合作为当前生成式主后端；
进入阶段 4.0.2 DiffDec adapter；
并准备阶段 4.0.4 新基座调研。
```

### 情况 C：DiffSBDD 结果混乱

如果：

```text
不同 K / seed 波动很大；
candidate mapping 不稳定；
报告字段不可靠；
```

则下一步：

```text
先修 adapter schema 和候选映射稳定性；
不要进入阶段 4.1。
```

---

## 15. 推荐执行方式

阶段 4.0.1 建议按以下流程推进：

```text
1. 将本方案放入 docs/；
2. 让 Codex 进入 /plan 模式，只规划不执行；
3. Codex 核查阶段 4.0 结果、字段、DiffSBDD adapter 和 checkpoint 状态；
4. 若发现方案与仓库事实冲突，先写 conflict report；
5. plan 通过后再使用 /goal 执行；
6. 先做 5 case preflight；
7. preflight 通过后跑 40 case；
8. 主设置 center=pocket；
9. 做 K=8 / 16 / 32；
10. 输出失败漏斗、预算曲线和临时实验汇报；
11. 再由网页 ChatGPT 分析结果，决定是否进入 4.0.2 或 4.1。
```

---

## 16. 最终总结

阶段 4.0.1 的核心不是证明阶段 4.1，也不是证明 DiffSBDD 已经成熟，而是：

> 对当前最接近可用的生成式局部补全后端 `diffsbdd_conditional_inpainting` 做一次有边界的修补实验：固定 40 个阶段 4.0 case、主用 center=pocket、扩展 K=8/16/32、增加 anchor-aware filtering 和 local reconnect check，最终判断它是否能从阶段 4.0 的非零可行性推进到更稳定、可解释的生成式修复能力。

一句话：

```text
阶段 4.0.1 只修 DiffSBDD conditional；
目标是弄清它能不能成为生成式局部修复主线；
成功则继续生成式路线，失败则转向 DiffDec adapter 或新基座调研。
```
