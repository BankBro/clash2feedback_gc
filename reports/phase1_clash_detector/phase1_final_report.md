# Clash2Feedback-GC 阶段 1 收尾报告：几何裁判系统验收与阶段 2/3 实验建议

## 1. 摘要结论

阶段 1 可以验收完成, 并进入阶段 2 controlled synthetic failed pose benchmark.

本结论的依据是: 阶段 1 已完成 protein-ligand vdW clash detector, R-group attribution, failure type 分类, repair verifier skeleton, clean calibration 和 verifier clean-vs-clean smoke test. `reports/phase1_clash_detector/summary.json` 显示 `phase1_acceptance_status = complete`, clean pool 为 51 个样本, balanced subset 为 28 个样本, 默认 `delta = 0.4 Å`, `phase0_pocket8` 与 `pocket10_all_atoms` 两种 receptor scope 在默认阈值下 severe false positive 均为 0, verifier smoke 为 28 / 28 pass.

阶段 1 的边界也必须明确: 它不表示生成器修复已经完成, 不表示人工失败样本上的 rule locator Top-1 / Top-3 已验证, 不表示真实 repair candidate 已验证, 也不表示 full-receptor checked repair 已完成.

## 2. 阶段 1 目标与验收标准对照

| 验收项 | 是否完成 | 依据文件 | 简要说明 |
|---|---:|---|---|
| clean pool 可检测 | 是 | `summary.json` | `num_clean_pool_samples = 51`, load error 为 0 |
| balanced subset 可检测 | 是 | `summary.json` | `num_balanced_subset_samples = 28`, load error 为 0 |
| 支持 `phase0_pocket8` | 是 | `configs/phase1_clash_detector.yaml`, `summary.json` | receptor scopes 包含 `phase0_pocket8` |
| 支持 `pocket10_all_atoms` | 是 | `configs/phase1_clash_detector.yaml`, `summary.json` | receptor scopes 包含 `pocket10_all_atoms` |
| 输出 pair-level clash report | 是 | `clean_clash_report.csv`, `balanced_clash_report.csv` | 输出 clash pair count, severe count, score, depth 和 attribution 字段 |
| 输出 R-group attribution | 是 | `rgroup_attribution_report.csv` | 输出 all-region 和 valid-R-group dominant ratio |
| 输出 failure type counts | 是 | `failure_type_counts.csv` | 默认 `delta = 0.4` 下全部为 `no_clash` |
| verifier clean-vs-clean smoke | 是 | `verifier_smoke_report.csv` | 28 / 28 pass |
| delta sensitivity | 是 | `threshold_sensitivity.csv` | 覆盖 `delta = 0.3, 0.4, 0.5` |
| strict false-positive report | 是 | `strict_delta_false_positive_cases.csv` | `delta = 0.3` 下记录 1 个边界样本 |
| non-severe contact stats | 是 | `nonsevere_contact_stats.csv` | 默认阈值下仍存在 mild close contacts |
| scope comparison | 是 | `scope_comparison.csv` | 237 行对比全部一致 |
| unsupported cases report | 是 | `unsupported_cases.csv` | 当前为空表, 仅表头 |

## 3. 阈值定义与 delta sensitivity

阶段 1 使用 raw vdW overlap:

\[
o_{ij}=r_i^{vdW}+r_j^{vdW}-d_{ij}
\]

再计算 clash depth:

\[
c_{ij}=\max(0,o_{ij}-\delta)
\]

默认配置为:

```text
delta = 0.4 Å
severe_depth_threshold = 0.4 Å
```

因此默认下:

```text
clash pair: raw vdW overlap > 0.4 Å
severe clash: raw vdW overlap >= 0.8 Å
```

`threshold_sensitivity.csv` 的结果如下:

| dataset | scope | delta | severe FP count | severe FP rate | median score | max score |
|---|---|---:|---:|---:|---:|---:|
| `phase0_balanced_30_v0_1` | `phase0_pocket8` | 0.3 | 1 | 0.035714 | 0.000376 | 0.652460 |
| `phase0_balanced_30_v0_1` | `phase0_pocket8` | 0.4 | 0 | 0.000000 | 0.000000 | 0.291943 |
| `phase0_balanced_30_v0_1` | `phase0_pocket8` | 0.5 | 0 | 0.000000 | 0.000000 | 0.117748 |
| `phase0_balanced_30_v0_1` | `pocket10_all_atoms` | 0.3 | 1 | 0.035714 | 0.000376 | 0.652460 |
| `phase0_balanced_30_v0_1` | `pocket10_all_atoms` | 0.4 | 0 | 0.000000 | 0.000000 | 0.291943 |
| `phase0_balanced_30_v0_1` | `pocket10_all_atoms` | 0.5 | 0 | 0.000000 | 0.000000 | 0.117748 |
| `phase0_clean_pool_v0_1` | `phase0_pocket8` | 0.3 | 1 | 0.019608 | 0.000116 | 0.652460 |
| `phase0_clean_pool_v0_1` | `phase0_pocket8` | 0.4 | 0 | 0.000000 | 0.000000 | 0.291943 |
| `phase0_clean_pool_v0_1` | `phase0_pocket8` | 0.5 | 0 | 0.000000 | 0.000000 | 0.117748 |
| `phase0_clean_pool_v0_1` | `pocket10_all_atoms` | 0.3 | 1 | 0.019608 | 0.000116 | 0.652460 |
| `phase0_clean_pool_v0_1` | `pocket10_all_atoms` | 0.4 | 0 | 0.000000 | 0.000000 | 0.291943 |
| `phase0_clean_pool_v0_1` | `pocket10_all_atoms` | 0.5 | 0 | 0.000000 | 0.000000 | 0.117748 |

解释: `delta = 0.3` 更严格, 会触发 strict false positive. `delta = 0.4` 是当前主阈值, clean calibration 下 severe false positive 为 0. `delta = 0.5` 更宽松, 也无 severe false positive, 但后续可能降低 failed pose recall, 因此适合作为 sensitivity 而非默认主阈值.

## 4. Strict Delta False Positive Case 解读

`strict_delta_false_positive_cases.csv` 中只有一个实际样本触发 strict severe false positive: `complex_crossdocked_000019`. 由于它同时出现在 clean pool 与 balanced subset, 且两个 receptor scope 结果一致, 表中有 4 行记录.

| sample | dataset | scope | delta | severe pairs | max depth | total score | dominant | valid ratio | failure type |
|---|---|---|---:|---:|---:|---:|---|---:|---|
| `complex_crossdocked_000019` | `phase0_balanced_30_v0_1` | `phase0_pocket8` | 0.3 | 1 | 0.496010 | 0.652460 | `R3` | 0.940381 | `ambiguous_region_clash` |
| `complex_crossdocked_000019` | `phase0_balanced_30_v0_1` | `pocket10_all_atoms` | 0.3 | 1 | 0.496010 | 0.652460 | `R3` | 0.940381 | `ambiguous_region_clash` |
| `complex_crossdocked_000019` | `phase0_clean_pool_v0_1` | `phase0_pocket8` | 0.3 | 1 | 0.496010 | 0.652460 | `R3` | 0.940381 | `ambiguous_region_clash` |
| `complex_crossdocked_000019` | `phase0_clean_pool_v0_1` | `pocket10_all_atoms` | 0.3 | 1 | 0.496010 | 0.652460 | `R3` | 0.940381 | `ambiguous_region_clash` |

top severe pair 为 ligand atom 32 与 protein atom 209, ligand region 为 `R3`, residue key 为 `A:410::ILE`, distance 为 2.423990 Å, vdW sum 为 3.220000 Å, clash depth 为 0.496010 Å.

这个 case 是 strict sensitivity 暴露的边界 clean case. 它不推翻阶段 1 验收, 但说明 `delta = 0.3` 不适合作为默认主阈值. `delta = 0.4` 下该样本不再产生 severe false positive, 因此当前选择 `delta = 0.4` 作为阶段 2/3 主阈值更稳妥.

## 5. Clean Pool 与 Balanced Subset Severe False Positive 为 0 的意义与局限

默认 `delta = 0.4` 下, clean pool 与 balanced subset severe false positive 都为 0. 这说明当前 detector 在阶段 0 clean calibration 上没有 severe 级误报, 支持把 phase0 clean pool 作为阶段 2 synthetic injection 的 base pool.

但该结果有明确局限:

- zero severe false positive 不等于 zero close contact.
- zero severe false positive 不等于真实 false-positive rate 在统计意义上等于 0.
- balanced subset 不一定是 clean pool 的独立外部验证集.
- 当前数据只验证 pocket-level local receptor, 不验证 full receptor.

`nonsevere_contact_stats.csv` 显示默认 `delta = 0.4` 下仍存在 non-severe close contacts:

| dataset | scope | samples | any clash pair | non-severe samples | max pairs | max depth |
|---|---|---:|---:|---:|---:|---:|
| `phase0_balanced_30_v0_1` | `phase0_pocket8` | 28 | 5 | 5 | 10 | 0.396010 |
| `phase0_balanced_30_v0_1` | `pocket10_all_atoms` | 28 | 5 | 5 | 10 | 0.396010 |
| `phase0_clean_pool_v0_1` | `phase0_pocket8` | 51 | 5 | 5 | 10 | 0.396010 |
| `phase0_clean_pool_v0_1` | `pocket10_all_atoms` | 51 | 5 | 5 | 10 | 0.396010 |

因此, 阶段 1 的 clean calibration 结论应写成“默认阈值下没有 severe 级误报”, 不能写成“没有任何近接触”.

## 6. Receptor Scope Comparison

`scope_comparison.csv` 共 237 行, `scope_result_same = true` 的行数为 237, false 为 0. `score_diff` 的最大绝对值为 0, `max_depth_diff` 的最大绝对值为 0.

这说明在当前 clean calibration 中, `phase0_pocket8` 与 `pocket10_all_atoms` 对 clash pair count, severe count, total score 和 max depth 的结果一致. 对当前 clean pose 来说, clash-relevant protein atoms 已被 `phase0_pocket8` 覆盖, 因此 `phase0_pocket8` 可用于 old clash diagnosis 和 R-group attribution.

但这个结果不能外推为:

- repair candidate 移出原 8 Å pocket 后仍安全.
- `pocket10_all_atoms` 没有必要.
- full receptor checked repair 已完成.
- pocket-level no clash 等于 full receptor no clash.

## 7. Clash Detector 实现与风险

当前 detector 已实现:

- protein-ligand heavy atom vdW clash.
- `phase0_pocket8` 与 `pocket10_all_atoms` receptor scope.
- pair-level clash pairs, clash depth, severe count, total score, max depth 和 mean depth.
- `analysis_status`.
- unsupported atom, covalent, metal 和 mask 问题的 reject / unsupported 处理.
- full receptor dynamic shell 的接口和报告字段预留, 但未作为阶段 1 hard dependency.

主要风险:

| 风险 | 当前状态 | 是否阻塞阶段 2 | 建议处理 |
|---|---|---:|---|
| ligand internal clash 未处理 | 未纳入 detector 主流程 | 否, 但阶段 2 需要过滤 | 阶段 2 injection 接受标准加入 internal clash check |
| protein-protein / ligand-ligand clash 未处理 | 阶段 1 不处理 | 否 | 保持 protein-ligand 几何裁判边界 |
| full receptor 未启用 | 预留接口 | 否 | 阶段 4/5/8 做 shadow 或 final check |
| YAML 部分 flags 更像 policy | 已记录配置, 非全部为完整 runtime switch | 否 | 后续将 policy 与 runtime 行为拆清 |
| metal / covalent 只做 reject | 未实现专门化学模块 | 否 | 继续作为 unsupported split |

## 8. R-group Attribution 实现与风险

当前 attribution 已实现:

- region score.
- normalized region score.
- all-region dominant ratio.
- valid-R-group dominant ratio.
- `dominant_valid_rgroup`.
- `failure_type`.
- `recommended_action`.
- `top_regions` 与 `top_valid_rgroups`.

阶段 3 的 Top-1 / Top-3 应主要使用 valid R-group ranking. failure type, reject 和 unsupported 判断则需要 all-region 信息, 因为 scaffold, unknown, unsupported region 不应被硬塞进 single R-group repair 主指标.

主要风险:

- `failure_type` 仍是启发式规则.
- `global_pose_failure` 识别仍较粗.
- unsupported, unknown, scaffold 与 valid R-group 的分流需要在阶段 2/3 继续验证.
- 阶段 2 构造 benchmark 时不能只用 predicted `dominant_region` 作为保留条件, 否则会污染阶段 3 Top-1 / Top-3 评价.

## 9. Repair Verifier Smoke 与风险

`verifier_smoke_report.csv` 结果:

| 指标 | 数值 |
|---|---:|
| total rows | 28 |
| repair pass | 28 |
| coordinate valid | 28 |
| geometry valid | 28 |
| old pair count before sum | 14 |
| old pair count after sum | 14 |
| old pair remaining count sum | 14 |
| new pair created count sum | 0 |
| old severe pair remaining count sum | 0 |
| new severe pair created count sum | 0 |

clean-vs-clean 28 / 28 pass 说明 verifier skeleton 可稳定运行, 不会误杀 identity repair. 当前 `geometry_valid` 等同 coordinate-level `coordinate_valid`, 主要检查坐标 shape 和 finite.

它不能证明:

- 真实 repair candidate 能被可靠验证.
- old severe clash 能被修掉.
- wrong-region repair 会失败.
- oracle repair 会通过.

RDKit sanitize, 键长, 价态, ligand internal clash 和 fragment connectivity 应作为阶段 2/4 的 verifier 升级项.

## 10. Unsupported Cases

`unsupported_cases.csv` 当前为空, 只有表头:

```text
dataset_name,sample_id,receptor_scope,delta_angstrom,unsupported_reason,error
```

这说明本批 clean calibration 未触发 unsupported case. 这不能写成 unsupported 逻辑已经完整覆盖所有未来样本. 后续阶段 2/3 仍应单独保留 unsupported split, 覆盖 metal, covalent ligand, invalid mask 和 unsupported atom 等边界.

## 11. 阶段 1 总体风险与不足

| 风险 | 当前状态 | 是否阻塞阶段 2 | 建议处理 |
|---|---|---:|---|
| full receptor 未启用 | 预留接口 | 否 | 阶段 4/5/8 做 shadow 或 final check |
| `geometry_valid` 仍弱 | coordinate-level | 否, 但必须说明 | 阶段 2/4 升级 RDKit sanitize, 键长, 价态和 internal clash |
| synthetic failed pose 未验证 | 未做 | 是, 属于阶段 2 | 阶段 2 构造 controlled benchmark |
| locator Top-1 / Top-3 未验证 | 未做 | 是, 属于阶段 3 | 阶段 3 在 supported single-Rgroup failures 上评估 |
| real repair candidate 未验证 | 未做 | 后续阶段 | 阶段 4 进入 repair loop |
| sample size 小 | clean 51 / balanced 28 | 不阻塞 | 后续扩展 clean pool 和外部验证 |

## 12. 阶段 2 Controlled Synthetic Failed Pose Benchmark 建议

### 12.1 Split 设计

| split | 目的 | 是否进主 locator 指标 |
|---|---|---:|
| `directed_clash` | 朝 protein hotspot 定向扰动, 构造明确 single-Rgroup failure | 是 |
| `torsion_perturb` | 扰动 target R-group rotatable bond, 更接近构象错误 | 是 |
| `easy_rotation` | anchor bond rotation baseline, 方便 debug | 是, 但需严格过滤 |
| `fragment_replace` | bulky replacement, 更接近取代基太大 | 增强实验 |
| `hard_multi_region` | multi/scaffold/global stress test | 否, 进 reject 指标 |
| `unsupported` | metal/covalent/invalid mask 等边界 | 否, 进 unsupported 指标 |

优先级建议:

```text
directed_clash -> torsion_perturb -> easy_rotation -> fragment_replace -> hard_multi_region
```

### 12.2 Base Clean Pose 过滤条件

每个 base sample 应满足:

```text
analysis_status = ok
delta = 0.4 下 phase0_pocket8 severe count = 0
delta = 0.4 下 pocket10_all_atoms severe count = 0
至少 1 个 valid R-group
target R-group 是 valid editable R-group
无 covalent / metal / unsupported chemistry
```

### 12.3 Synthetic Failed Pose 接受标准

supported single-Rgroup 主集建议接受条件:

```text
target R-group 至少产生 1 个 severe protein-ligand clash pair
old clash report 可正常计算
analysis_status = ok
scaffold RMSD < 0.3 Å
non-target R-group RMSD < 0.5 Å
ligand internal severe clash = 0
max clash depth 不应极端过大, 可先限制在 1.2-1.5 Å 内
target_region_ratio_valid >= 0.7
```

可以记录 predicted `dominant_region` 和 `dominant_valid_rgroup`, 但不要把 predicted `dominant_region == target_rgroup` 作为唯一保留条件, 否则阶段 3 Top-1 / Top-3 会被构造过程泄漏污染.

### 12.4 每个 Case 建议保存字段

```text
case_id
base_sample_id
split
injection_type
target_rgroup
target_atom_indices
target_anchor_atom
original_ligand_coords
failed_ligand_coords
transform_parameters
old_scope
new_scope
delta_angstrom
severe_depth_threshold
num_old_clash_pairs
num_old_severe_pairs
max_old_clash_depth
total_old_clash_score
target_rgroup_score
target_rgroup_normalized_score
target_region_ratio_valid
target_region_ratio_all
predicted_dominant_region_all
predicted_dominant_valid_rgroup
dominant_ratio_all_regions
dominant_ratio_valid_rgroups
num_nonzero_valid_rgroups
scaffold_score
non_target_rgroup_score
unsupported_region_score
failure_type
recommended_action
scaffold_rmsd
non_target_rgroup_rmsd
ligand_internal_clash_count
analysis_status
reject_reason
unsupported_reason
top_regions_json
top_valid_rgroups_json
top_clash_pairs_json
```

### 12.5 阶段 2 报告文件建议

```text
reports/phase2_injection/summary.json
reports/phase2_injection/base_clean_filter_report.csv
reports/phase2_injection/injection_attempts.csv
reports/phase2_injection/supported_single_rgroup_cases.csv
reports/phase2_injection/reject_cases.csv
reports/phase2_injection/unsupported_cases.csv
reports/phase2_injection/delta_sensitivity.csv
reports/phase2_injection/oracle_verifier_report.csv
reports/phase2_injection/no_repair_negative_report.csv
reports/phase2_injection/wrong_region_negative_report.csv
```

### 12.6 阶段 2 Verifier 必测 Case

| 测试 | failed coords | repaired coords | 期望 |
|---|---|---|---|
| no-repair negative | synthetic failed | synthetic failed | fail, old pair remaining > 0 |
| oracle repair | synthetic failed | original clean | pass |
| wrong-region repair | synthetic failed | wrong region modified | fail |
| new-clash repair | synthetic failed | repaired but new clash | fail, new pair created > 0 |

## 13. 阶段 3 Rule Locator 评价建议

阶段 3 才正式评价 rule locator. 主指标只应在:

```text
supported_single_rgroup synthetic failures
```

上计算.

不要把以下 case 混入 Top-1 / Top-3 主指标:

```text
unsupported
scaffold_clash
multi_region_clash
global_pose_failure
hard ambiguous reject case
```

建议报告:

| 指标 | 解释 |
|---|---|
| Coverage | locator 能给出可操作建议的比例 |
| Top-1, reject 算 miss | 主 operational 指标 |
| Top-1 covered | 拆分 coverage 与 locator accuracy |
| Top-3 rank | 衡量 ranking 本身 |
| Top-3 operational | 衡量后续 Top-3 repair search 的可用性 |
| dominant ratio valid mean / median | 衡量单 R-group 归因集中度 |
| Reject recall | 对 multi/scaffold/global 等应拒绝 case 的识别 |
| Unsupported recall | 对 metal/covalent/invalid mask 等 unsupported case 的识别 |
| False local repair | 安全指标, 越低越好 |

## 14. 不应写出的结论

本阶段报告不支持以下结论:

- 阶段 1 已经完成生成器修复.
- 阶段 1 已经验证真实 repair candidate.
- 阶段 1 已经验证 rule locator Top-1 / Top-3.
- 阶段 1 已经证明 full receptor repair 安全.
- zero severe false positive 说明 false positive rate 统计上等于 0.
- no_clash 等于结合成功.
- `geometry_valid` 等于完整化学合法性.

## 15. 最终判断

阶段 1 的几何裁判系统可以关闭: detector, attribution, failure type, verifier skeleton 和 clean calibration 已达到当前阶段目标. 默认 `delta = 0.4 Å` 在 clean pool 和 balanced subset 上没有 severe false positive; `delta = 0.3 Å` 暴露了一个 strict boundary case, 支持把它保留为 sensitivity 而非默认主阈值; `phase0_pocket8` 与 `pocket10_all_atoms` 在当前 clean calibration 中结果一致, 但不能替代 full receptor repair 安全检查.

下一步应进入阶段 2 controlled synthetic failed pose benchmark, 构造可控的 single-Rgroup failed poses, 同时保留 reject / unsupported / hard case split. 阶段 3 再基于 supported single-Rgroup synthetic failures 正式评价 rule locator 的 Top-1, Top-3, coverage 和安全指标.
