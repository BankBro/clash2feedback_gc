# 阶段 4.0 多后端参考掩码修复可行性审计最终实验报告

## 1. 摘要

阶段 4.0 已完成. 本阶段完成的是“参考掩码条件下的多后端修复可行性审计”, 不是 Random / Predicted / Oracle 正式掩码对照, 也不代表生成式局部修复主线已经完成.

本阶段的核心问题是:

```text
在已经给定正确参考修复区域时, 不同修复后端能否生成可读取、可验证、局部可靠的修复候选?
```

正式审计使用 `reports/phase3_label_provenance_audit/phase4_mask_seed.csv` 中冻结的参考掩码, 从 S2 case 中选择 40 个 case. 纳入比较的后端包括:

- `rule_fixed_topology`: 固定拓扑局部构象搜索.
- `diffsbdd_conditional_inpainting`: DiffSBDD CrossDocked full-atom conditional 局部补全.
- `diffdec_single_rgroup`: DiffDec 单取代基重采样.
- `diffsbdd_full_resampling`: DiffSBDD 全配体重采样对照.
- `diffsbdd_joint_inpainting`: DiffSBDD joint 局部补全候选后端, 当前 blocked.

主结果如下:

- `rule_fixed_topology`: 38/40 case 成功, 227/320 candidates 达到 reliable repair.
- `diffsbdd_conditional_inpainting`: 9/40 case 成功, 17/624 candidates 达到 reliable repair.
- `diffdec_single_rgroup`: 0/40 case 成功, 312 个 generated/readable candidates 中 0 个达到 reliable repair.
- `diffsbdd_full_resampling`: 0/40 case 成功, 只能作为全配体重采样对照.
- `diffsbdd_joint_inpainting`: checkpoint 和环境进入 inventory, 但官方 inpaint 入口与 joint checkpoint 接口不兼容, 当前 blocked.

最终结论是: 阶段 4.0 可以关闭. `rule_fixed_topology` 证明当前人工受控局部碰撞样本存在大量构象可逆失败, 但它只能作为构象型强基线和 sanity check, 不能写成生成式主方法. `diffsbdd_conditional_inpainting` 取得非零生成式局部补全可靠修复结果, 但 anchor / reconnect / old clash resolution 仍不稳定. `diffdec_single_rgroup` 已跑通环境, checkpoint 和 GPU formal run, 但输入适配和映射链路尚未通过可靠修复标准. 后续应优先修补生成式后端, 而不是直接把 rule 后端写成生成式主线.

## 2. 实验目标与边界

阶段 4.0 的目标是先排除“修复区域找错”这一干扰项, 在参考掩码已知的条件下审计后端和适配链路是否可用. 因此本阶段只回答:

- 后端能否读取阶段 4.0 输入并构造候选生成请求.
- 后端能否生成候选或明确给出 blocked / failure.
- 候选能否进入统一 verifier adapter.
- 候选是否同时满足旧碰撞消除, 无新严重碰撞, 固定结构保持, anchor integrity 和 pocket retention 等可靠修复标准.

本阶段明确不做:

- 不做 Random / Predicted / Oracle 正式掩码对照.
- 不训练模型.
- 不微调 DiffSBDD / DiffDec.
- 不修改 DiffSBDD / DiffDec 原始去噪过程.
- 不声称 `H_clash` 进入 DiffSBDD / DiffDec 生成过程.
- 不把 Vina / docking score 作为主指标.
- 不做多轮迭代修复.
- 不修改阶段 2 / 2.5 / 3 历史结果.
- 不覆盖 `reports/phase3_label_provenance_audit/phase4_mask_seed.csv`.
- 不提交 `external/DiffSBDD`, `external/DiffDec`, checkpoint, 大量候选 SDF 或日志缓存.

阶段 4.0 的主指标是样本级可靠修复率, 而不是结合成功率、对接分数提升或生成模型综合排名.

## 3. 输入数据与样本选择

主输入文件是:

```text
reports/phase3_label_provenance_audit/phase4_mask_seed.csv
```

正式实验使用 40 个 S2 case. 该集合用于 backend feasibility audit, 不是 held-out 泛化测试集. 它用于回答“给定正确修复区域时, 后端是否能修”的前置问题.

本次阶段 4.0 summary 记录:

- `mode = formal_40_case`.
- `selected_case_count = 40`.
- `expected_case_count = 40`.
- `formal_40_case_results_generated = true`.
- `training_or_finetuning_performed = false`.
- `h_clash_used_in_diffsbdd_generation = false`.
- `phase4_mask_seed_sha256_before = 18cea12cc4f92a8f21f6f9de83c2ba551556e35a19e9d781d3a98f79b99097cc`.
- `phase4_mask_seed_sha256_after = 18cea12cc4f92a8f21f6f9de83c2ba551556e35a19e9d781d3a98f79b99097cc`.
- `phase4_mask_seed_unchanged = true`.

样本选择和 case list 由 `reports/phase4_0_backend_feasibility/selected_cases.csv` 固化. 本报告只读取既有结果, 未重新选择 case, 未重跑任何 repair backend, 未生成新候选.

## 4. 可靠修复候选定义

阶段 4.0 使用 `src/clash2feedback/verifier/phase4_adapter.py` 中的 `RELIABLE_REPAIR_FIELDS` 作为 reliable repair candidate 定义. 单个候选必须同时满足以下 10 项标准:

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

- 不是“生成出来”就算成功.
- 不是“没有新碰撞”就算成功.
- 必须旧碰撞消除, 无新严重碰撞, 局部结构保持, 连接点合理, 候选合法, 且仍在口袋中.
- 对 DiffSBDD / DiffDec 等可能改变拓扑或原子顺序的后端, `fixed_structure_match_success=true` 是可靠成功的必要条件.
- 后端失败, 候选不可读, adapter 失败, fixed structure match 失败, anchor integrity 失败, 候选全部非法, 候选全部未修掉旧碰撞, 候选全部产生新严重碰撞, 都保留在 selected case 分母中.

## 5. 后端矩阵

| backend_name | 后端类型 | 阶段 4.0 定位 | 当前状态 |
|---|---|---|---|
| `rule_fixed_topology` | 固定拓扑局部构象搜索 | 构象型强基线和可逆性 sanity check | ready |
| `diffsbdd_conditional_inpainting` | DiffSBDD 条件局部补全 | 生成式局部补全后端 | ready |
| `diffdec_single_rgroup` | DiffDec 单取代基重采样 | 生成式 R-group 后端 | ready, 但 reliable success 为 0 |
| `diffsbdd_full_resampling` | DiffSBDD 全配体重采样 | 全局生成对照, 不是局部修复后端 | ready |
| `diffsbdd_joint_inpainting` | DiffSBDD joint 模型局部补全候选 | joint 模型可行性调研项 | blocked |

`model_inventory.csv` 显示 DiffSBDD conditional, DiffSBDD full resampling 和 DiffDec 的外部仓库、checkpoint 和环境记录均已纳入 inventory. 所有 DiffSBDD / DiffDec 后端均记录 `uses_h_clash_in_generation = False`.

## 6. 主结果表

主结果来自 `backend_comparison.csv`, `backend_comparison_rates.csv` 和 `phase4_0_small_scale_summary.json`.

| backend_name | selected_case_denominator | candidate_count_sum | proposal_count_sum | failure_attempt_rate | reliable_candidate_rate | sample_reliable_repair_yield | candidate_readable_rate | fixed_structure_match_rate | anchor_integrity_rate | cost_per_reliable_case |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `rule_fixed_topology` | 40 | 320 | 1200 | 0.000000 | 0.709375 | 0.950000 | 1.000000 | 1.000000 | 1.000000 | 31.578947 |
| `diffsbdd_conditional_inpainting` | 40 | 624 | 640 | 0.025000 | 0.027244 | 0.225000 | 1.000000 | 1.000000 | 0.403846 | 71.111111 |
| `diffdec_single_rgroup` | 40 | 312 | 320 | 0.025000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.990385 | NA |
| `diffsbdd_full_resampling` | 40 | 320 | 320 | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 0.000000 | 0.000000 | NA |
| `diffsbdd_joint_inpainting` | 40 | 0 | 0 | 1.000000 | NA | 0.000000 | NA | NA | NA | NA |

解读要点:

- `rule_fixed_topology` 的 `sample_reliable_repair_yield = 0.950000`, `reliable_candidate_rate = 0.709375`, `proposal_per_case_mean = 30.000000`, `cost_per_reliable_case = 31.578947`. 它成功率最高, 但内部 proposal 成本不能被最终 K=8 候选上限掩盖.
- `diffsbdd_conditional_inpainting` 的 `sample_reliable_repair_yield = 0.225000`, `reliable_candidate_rate = 0.027244`, `anchor_integrity_rate = 0.403846`, `cost_per_reliable_case = 71.111111`. 它证明生成式局部补全有非零可行性, 但稳定性不足.
- `diffdec_single_rgroup` 的 `candidate_readable_rate = 1.000000`, `fixed_structure_match_rate = 1.000000`, `anchor_integrity_rate = 0.990385`, 但 `old_clash_resolved = 0`, 因而 `reliable_candidate_rate = 0` 且 `sample_reliable_repair_yield = 0`.
- `diffsbdd_full_resampling` 能生成可读全配体候选, 但不固定 keep region, 不保证 scaffold / anchor / 原 atom order 保留, 因而不能视为局部修复成功.
- `diffsbdd_joint_inpainting` 是 blocked backend, 不应按“修复失败”解释.

## 7. 分后端分析

### 7.1 `rule_fixed_topology`

`rule_fixed_topology` 在 38/40 case 上至少产生 1 个 reliable repair candidate, 320 个最终候选中 227 个达到 reliable repair. 它的 `proposal_count_sum = 1200`, `candidate_count_sum = 320`, 即每个 case 最多保留 K=8 个候选, 但内部搜索总 proposal 数明显高于最终候选数.

该后端是固定拓扑局部构象搜索. 它保留原分子拓扑和原 atom order, 通过 anchor axis rotation 和内部 torsion proposal 在参考掩码区域内搜索构象. 这与阶段 2 人工失败样本中的 `easy_rotation`, `torsion_perturb`, `directed_clash` 构造方式高度相关.

分层成功结果如下:

| group | selected_cases | reliable_cases | sample_success_rate |
|---|---:|---:|---:|
| directed_clash | 14 | 14 | 1.000000 |
| easy_rotation | 13 | 11 | 0.846154 |
| torsion_perturb | 13 | 13 | 1.000000 |
| easy | 27 | 26 | 0.962963 |
| medium | 13 | 12 | 0.923077 |

因此, 38/40 成功的合理解释是: 当前人工受控局部碰撞样本中存在大量构象可逆失败. `rule_fixed_topology` 是一个非常强的构象型基线, 也是阶段 4.0 的 sanity check. 它不能被写成生成式局部修复主方法, 也不能被写成生成式主线已经完成. 后续不建议直接把它作为阶段 4.1 的生成式主方法.

### 7.2 `diffsbdd_conditional_inpainting`

`diffsbdd_conditional_inpainting` 总体在 9/40 case 上成功, 624 个候选中 17 个达到 reliable repair. 这说明 DiffSBDD conditional local completion 在参考掩码条件下有非零生成式局部补全可行性.

但当前可靠修复率仍低. 主要瓶颈不是候选读取, 而是 anchor / reconnect / old clash resolution 的联合稳定性. 总体 `anchor_integrity_rate = 0.403846`, `reliable_candidate_rate = 0.027244`, `sample_reliable_repair_yield = 0.225000`.

按 center 拆分:

| center | attempt_rows | candidate_count | execution_failure_count | reliable_candidate_success_count | sample_reliable_success_count |
|---|---:|---:|---:|---:|---:|
| ligand | 40 | 312 | 1 | 5 | 4 |
| pocket | 40 | 312 | 1 | 12 | 7 |

`center=pocket` 当前表现好于 `center=ligand`, 但两个 center 的 sample success 可能重叠, 不能直接相加为总体 9/40. 两个 center 均能产生可读候选, 但 reliable repair 数仍低.

重要口径是: `H_clash` 未进入 DiffSBDD 生成过程, 碰撞信息只在后验 verifier 中使用. 后续应优先做 anchor-aware filtering, local reconnect check 和 adapter schema 修补, 再讨论是否进入更大规模掩码策略对照.

### 7.3 `diffdec_single_rgroup`

`diffdec_single_rgroup` 的环境, checkpoint 和 GPU formal run 已经跑通. 本次有 40 attempts, 1 个 execution failure, 312 个 generated/readable candidates, 0 个 reliable success.

DiffDec 失败漏斗如下:

| metric | count | denominator | rate |
|---|---:|---:|---:|
| attempts | 40 | 40 | 1.000000 |
| execution_failures | 1 | 40 | 0.025000 |
| generated_candidates | 312 | 312 | 1.000000 |
| readable_candidates | 312 | 312 | 1.000000 |
| ligand_valid | 311 | 312 | 0.996795 |
| fixed_structure_match_success | 312 | 312 | 1.000000 |
| anchor_integrity_success | 309 | 312 | 0.990385 |
| generated_atom_count_mismatch | 194 | 312 | 0.621795 |
| generated_atom_element_mismatch | 112 | 312 | 0.358974 |
| old_clash_resolved | 0 | 312 | 0.000000 |
| no_new_severe_clash | 6 | 312 | 0.019231 |
| reliable_success | 0 | 312 | 0.000000 |

`CL` protein atom vocabulary 问题确实存在, 日志中对应 `case_002599` 的 `KeyError: 'CL'`, 但它只解释 1 个 execution failure. 其余 39 个 attempt 已生成候选并进入 verifier, 因此不能把 0 reliable success 简单归因于 `CL`.

当前更主要的问题是 input adapter, `fixed_context.sdf`, 带星号出口 scaffold smiles, anchor/scaffold mapping, candidate mapping, generated R-group size 控制和 old clash resolution 尚未解决. 当前结果不应直接解释为 DiffDec 模型本身无效, 而应解释为该后端在 Clash2Feedback-GC 阶段 4.0 输入适配和验证映射口径下尚未跑通可靠修复.

### 7.4 `diffsbdd_full_resampling`

`diffsbdd_full_resampling` 是全配体重采样对照, 不是局部修复后端. 它不使用局部 reference mask, 不固定 keep region, 不保证 scaffold / anchor / 原 atom order 保留.

全局对照指标如下:

| metric | value |
|---|---:|
| candidate_denominator | 320 |
| candidate_readable_rate | 1.000000 |
| ligand_valid_rate | 0.978125 |
| fixed_structure_match_rate | 0.000000 |
| anchor_integrity_rate | 0.000000 |
| reliable_local_repair_success_count | 0 |

因此, 在阶段 4.0 的 reliable local repair 标准下, 0 reliable local repair success 是合理结果. 它可以作为“直接重新生成完整配体”的全局对照, 但不应进入阶段 4.1 的 Random / Predicted / Oracle 局部掩码组, 也不应被写成局部修复后端.

### 7.5 `diffsbdd_joint_inpainting`

`diffsbdd_joint_inpainting` 的 checkpoint 已纳入 `model_inventory.csv`, checkpoint 存在且环境为 ready. 但当前官方 `inpaint.py` 入口与 joint checkpoint 不兼容, 阻塞原因是:

```text
official_inpaint_entrypoint_incompatible_with_joint_checkpoint:center_argument
```

因此它是 blocked backend, 不是局部修复失败结果. 该 blocked 状态是阶段 4.0 backend feasibility audit 的真实结论之一. 不需要先修 joint 再出阶段 4.0 最终报告, 也不影响阶段 4.0 关闭.

## 8. 关键风险和局限

- 阶段 4.0 只用参考掩码, 不能证明 predicted mask 的下游价值.
- S2 是人工受控局部碰撞集合, 不是完全真实生成失败分布.
- `rule_fixed_topology` 和阶段 2 人工扰动构造方式高度相关, 高成功率不能外推为生成式修复成功.
- DiffSBDD / DiffDec 原版没有使用 `H_clash` 进入生成过程, 碰撞信息只在后验 verifier 和报告分析中使用.
- `diffsbdd_conditional_inpainting` 虽有非零成功, 但 anchor / reconnect / old clash resolution 仍不稳定.
- `diffdec_single_rgroup` 当前主要是 adapter 和映射问题, 不能直接判定模型本身无效.
- `diffsbdd_full_resampling` 不是局部修复.
- `diffsbdd_joint_inpainting` 当前 blocked 是后端审计结论, 不是可靠修复率意义上的模型失败.
- 阶段 4.1 的 Random / Predicted / Oracle 正式掩码对照需要另行制定方案.

## 9. 最终结论

阶段 4.0 可以关闭. 它完成了“参考掩码条件下的多后端修复可行性审计”.

核心结论如下:

1. 当前人工受控局部碰撞样本在参考掩码条件下具有可修复性.
2. `rule_fixed_topology` 表现最强, 但只能作为构象型强基线和可逆性 sanity check.
3. `diffsbdd_conditional_inpainting` 取得非零可靠修复结果, 是当前最值得继续修补的生成式局部补全后端.
4. `diffdec_single_rgroup` 已经跑通环境和 GPU, 但 0 reliable success. 下一步应修 input adapter, anchor/scaffold mapping, candidate mapping 和 generated R-group size.
5. `diffsbdd_full_resampling` 只能作为全配体重采样对照.
6. `diffsbdd_joint_inpainting` 当前 blocked, 不影响阶段 4.0 最终报告.
7. 阶段 4.0 不建议直接转入以 `rule_fixed_topology` 为生成式主线的阶段 4.1.
8. 后续建议新增阶段 4.0.1 / 4.0.5, 优先修补 DiffSBDD conditional 和 DiffDec adapter, 必要时调研更合适的生成式局部修复基座.
9. 如果要做 `phase4.1-rule-mini`, 只能作为规则型 sanity check, 不作为生成式主结果.
10. Random / Predicted / Oracle 正式掩码对照需要另行制定阶段 4.1 方案.

## 10. 附录

### 10.1 主要输出文件

阶段 4.0 主结果:

- `reports/phase4_0_backend_feasibility/phase4_0_small_scale_summary.json`.
- `reports/phase4_0_backend_feasibility/backend_comparison.csv`.
- `reports/phase4_0_backend_feasibility/verifier_outcome.csv`.
- `reports/phase4_0_backend_feasibility/candidate_manifest.csv`.
- `reports/phase4_0_backend_feasibility/model_inventory.csv`.
- `reports/phase4_0_backend_feasibility/blocked_backends.md`.
- `reports/phase4_0_backend_feasibility/phase4_0_completion_audit.md`.

收尾诊断补丁:

- `reports/phase4_0_backend_feasibility/backend_comparison_rates.csv`.
- `reports/phase4_0_backend_feasibility/diffsbdd_center_sensitivity.csv`.
- `reports/phase4_0_backend_feasibility/diffsbdd_center_sensitivity.md`.
- `reports/phase4_0_backend_feasibility/diffdec_failure_funnel.csv`.
- `reports/phase4_0_backend_feasibility/diffdec_failure_analysis.md`.
- `reports/phase4_0_backend_feasibility/rule_backend_diagnostic.md`.
- `reports/phase4_0_backend_feasibility/full_resampling_control_analysis.md`.
- `reports/phase4_0_backend_feasibility/full_resampling_global_control_metrics.csv`.
- `reports/phase4_0_backend_feasibility/phase4_0_closeout_patch_audit.md`.

本最终报告:

- `reports/phase4_0_backend_feasibility/phase4_0_final_experiment_report.md`.

### 10.2 仓库状态记录

生成本报告前的核查记录:

- `git status --short`: clean.
- `git branch --show-current`: `20260514-043614-phase4-0`.
- `git rev-parse HEAD`: `4f931feda5cbba7dcb6b4fc6cde8e5cd7b23e2c6`.

### 10.3 测试记录

最近一次收尾诊断补丁已记录:

- `conda run -n c2f_cpu python -m compileall src scripts`: passed.
- `conda run -n c2f_cpu python -m pytest tests/test_phase4_backend_feasibility.py -q`: 8 passed.
- `conda run -n c2f_cpu python -m pytest -q`: 128 passed.

本最终报告提交前重新运行:

- `conda run -n c2f_cpu python -m compileall src scripts`: passed.
- `conda run -n c2f_cpu python -m pytest tests/test_phase4_backend_feasibility.py -q`: 8 passed.
- `conda run -n c2f_cpu python -m pytest -q`: 128 passed.

### 10.4 不变性和提交边界

- `phase4_mask_seed.csv` 未被修改, SHA256 前后均为 `18cea12cc4f92a8f21f6f9de83c2ba551556e35a19e9d781d3a98f79b99097cc`.
- 未修改阶段 2 / 2.5 / 3 历史结果.
- 未提交 `external/DiffSBDD`, `external/DiffDec`, checkpoint, 大量候选 SDF 或日志缓存.
- 本报告不生成阶段 4.1 方案, 只说明阶段 4.1 需要另行设计.
