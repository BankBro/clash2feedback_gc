# Clash2Feedback-GC 阶段 1 收尾报告生成说明

> 日期：2026-05-10
> 建议仓库路径：`tmp/20260510/20260510-Clash2Feedback-GC_阶段1收尾报告生成说明.md`
> 目标产物：`tmp/20260510/20260510-Clash2Feedback-GC_阶段1收尾报告.md`
> 适用对象：Codex / 后续自动化写作代理
> 目的：说明阶段 1 收尾报告应包含哪些内容、读取哪些文件、如何解释结果、哪些结论可以写、哪些结论不能写。

---

## 0. 报告定位

请生成一份 **Clash2Feedback-GC 阶段 1 收尾报告**。

这份报告不是代码实现说明，也不是阶段 2 实验报告，而是对阶段 1 的正式收尾总结：

```text
阶段 1 是否验收完成
为什么可以进入阶段 2
当前 detector / attribution / verifier 的结果如何解释
当前结果有哪些边界和风险
阶段 2 controlled synthetic failed pose benchmark 应如何设计
阶段 3 rule locator 应如何评价
```

报告应保持审慎口径：

```text
阶段 1 已完成几何裁判系统和 clean calibration。
阶段 1 尚未验证生成器修复、人工失败样本上的 locator Top-1 / Top-3、真实 repair candidate 或 full-receptor checked repair。
```

---

## 1. 必须读取的文件

请优先读取以下文件，并只基于仓库中已提交的代码、文档和 reports 分析。

### 1.1 项目与方案文件

```text
README.md
docs/20260508-Clash2Feedback-GC_阶段1碰撞检测器与可靠验证器方案.md
tmp/20260510/20260510-Clash2Feedback-GC_阶段1结果复盘与阶段2准备清单.md
tmp/20260510/20260510-Clash2Feedback-GC_阶段1修补清单与文档更新建议.md
configs/phase1_clash_detector.yaml
```

### 1.2 阶段 1 代码文件

```text
scripts/phase1_check_clashes.py
src/clash2feedback/geometry/vdw.py
src/clash2feedback/geometry/clash.py
src/clash2feedback/geometry/clash_types.py
src/clash2feedback/geometry/rgroup_attribution.py
src/clash2feedback/verifier/repair_verifier.py
```

### 1.3 阶段 1 测试文件

```text
tests/test_vdw.py
tests/test_clash_detector.py
tests/test_rgroup_attribution.py
tests/test_repair_verifier.py
tests/test_phase1_report_extensions.py
```

### 1.4 阶段 1 结果文件

```text
reports/phase1_clash_detector/summary.json
reports/phase1_clash_detector/clean_clash_report.csv
reports/phase1_clash_detector/balanced_clash_report.csv
reports/phase1_clash_detector/threshold_sensitivity.csv
reports/phase1_clash_detector/failure_type_counts.csv
reports/phase1_clash_detector/rgroup_attribution_report.csv
reports/phase1_clash_detector/verifier_smoke_report.csv
reports/phase1_clash_detector/strict_delta_false_positive_cases.csv
reports/phase1_clash_detector/nonsevere_contact_stats.csv
reports/phase1_clash_detector/scope_comparison.csv
reports/phase1_clash_detector/unsupported_cases.csv
reports/phase1_clash_detector/vdw_radius_table.json
```

不要依赖 raw PDB/SDF、processed pkl、cache、runs 图片或未提交数据。

---

## 2. 报告应使用的核心数据

请从实际文件读取数据，不要凭记忆硬写。若文件内容与下面示例不一致，以实际文件为准。

阶段 1 当前应重点报告：

```text
num_clean_pool_samples
num_balanced_subset_samples
default_delta_angstrom
delta_sensitivity
receptor_scopes
default_old_scope
default_new_scope
full_receptor_enabled
clean_pool_default_scope_severe_false_positive_count
balanced_subset_default_scope_severe_false_positive_count
per_scope_default_delta
verifier_smoke_total_count
verifier_smoke_pass_count
num_load_errors
phase1_acceptance_status
```

从 `threshold_sensitivity.csv` 报告：

```text
每个 dataset_name + receptor_scope + delta_angstrom 下的:
- num_samples
- num_samples_with_severe_clash
- severe_false_positive_rate
- median_total_clash_score
- max_total_clash_score
```

从 `strict_delta_false_positive_cases.csv` 报告：

```text
strict delta 下触发 severe false positive 的 sample_id
dataset_name
receptor_scope
delta_angstrom
num_severe_clash_pairs
max_clash_depth
total_clash_score
dominant_region
dominant_ratio_all_regions
dominant_valid_rgroup
dominant_ratio_valid_rgroups
failure_type
top clash pair 简述
```

从 `nonsevere_contact_stats.csv` 报告：

```text
默认 delta 下是否存在 non-severe close contacts
num_samples_with_any_clash_pair
num_samples_with_nonsevere_clash_pair
max_num_clash_pairs
max_depth
```

从 `scope_comparison.csv` 报告：

```text
phase0_pocket8 与 pocket10_all_atoms 是否一致
score_diff 与 max_depth_diff 是否为 0
scope_result_same 的总体情况
```

从 `verifier_smoke_report.csv` 报告：

```text
repair_pass 总数
coordinate_valid / geometry_valid
old_pair_count_before / after
old_pair_remaining_count
old_pair_resolved_fraction
new_pair_created_count
old_severe_pair_remaining_count
new_severe_pair_created_count
```

从 `unsupported_cases.csv` 报告：

```text
是否为空
若非空, 逐类统计 unsupported_reason
```

---

## 3. 报告建议结构

最终收尾报告建议使用以下章节。

---

### 3.1 摘要结论

必须回答：

```text
阶段 1 是否可以验收完成？
是否可以进入阶段 2？
阶段 1 结果的边界是什么？
```

建议结论口径：

```text
阶段 1 可以验收完成，并进入阶段 2 controlled synthetic failed pose benchmark。
本结论只表示 detector、R-group attribution、failure type、verifier skeleton 和 clean calibration 已完成。
它不表示生成器修复、人工失败样本定位准确率、真实 repair candidate 验证或 full-receptor checked repair 已完成。
```

---

### 3.2 阶段 1 目标与验收标准对照

请列一个表：

| 验收项 | 是否完成 | 依据文件 | 简要说明 |
|---|---:|---|---|
| clean pool 可检测 | 是/否 | `summary.json` |  |
| balanced subset 可检测 | 是/否 | `summary.json` |  |
| 支持 `phase0_pocket8` | 是/否 | config / summary |  |
| 支持 `pocket10_all_atoms` | 是/否 | config / summary |  |
| 输出 pair-level clash report | 是/否 | `clean_clash_report.csv` |  |
| 输出 R-group attribution | 是/否 | `rgroup_attribution_report.csv` |  |
| 输出 failure type counts | 是/否 | `failure_type_counts.csv` |  |
| verifier clean-vs-clean smoke | 是/否 | `verifier_smoke_report.csv` |  |
| delta sensitivity | 是/否 | `threshold_sensitivity.csv` |  |
| strict false-positive report | 是/否 | `strict_delta_false_positive_cases.csv` |  |
| non-severe contact stats | 是/否 | `nonsevere_contact_stats.csv` |  |
| scope comparison | 是/否 | `scope_comparison.csv` |  |
| unsupported cases report | 是/否 | `unsupported_cases.csv` |  |

---

### 3.3 阈值定义与 delta sensitivity

必须解释：

\[
o_{ij}=r_i^{vdW}+r_j^{vdW}-d_{ij}
\]

\[
c_{ij}=\max(0,o_{ij}-\delta)
\]

默认：

```text
delta = 0.4 Å
severe_depth_threshold = 0.4 Å
```

因此默认下：

```text
clash pair: raw vdW overlap > 0.4 Å
severe clash: raw vdW overlap >= 0.8 Å
```

请用 `threshold_sensitivity.csv` 做一个表：

| dataset | scope | delta | severe FP count | severe FP rate | median score | max score |
|---|---|---:|---:|---:|---:|---:|

然后解释：

```text
delta = 0.3 更严格, 会触发 strict false positive。
delta = 0.4 当前是主阈值, clean calibration 下 severe false positive 为 0。
delta = 0.5 更宽松, 也无 severe false positive, 但可能降低后续 failed pose recall。
```

---

### 3.4 strict delta false positive case 解读

请从 `strict_delta_false_positive_cases.csv` 抽取 strict false positive case，写清楚：

```text
是哪一个 sample？
在哪些 dataset/scope 下出现？
max clash depth 是多少？
dominant region 是什么？
dominant_ratio_all_regions 是多少？
dominant_ratio_valid_rgroups 是多少？
failure_type 是什么？
为什么这支持 delta = 0.4 而不是 delta = 0.3 作为默认值？
```

必须强调：

```text
strict false positive 是 strict sensitivity 暴露的边界 clean case。
它不推翻阶段 1 验收。
它说明 delta = 0.3 不适合作为默认主阈值。
```

---

### 3.5 clean pool 与 balanced subset severe false positive 为 0 的意义与局限

请解释意义：

```text
默认 delta = 0.4 下 clean pool 与 balanced subset severe FP 为 0，说明当前 detector 在阶段 0 clean calibration 上没有 severe 级误报。
这支持把 phase0 clean pool 作为阶段 2 synthetic injection 的 base pool。
```

也必须解释局限：

```text
zero severe FP 不等于 zero close contact。
zero severe FP 不等于真实 false-positive rate = 0。
balanced subset 不一定是 clean pool 的独立外部验证集。
当前数据只验证 pocket-level local receptor，不验证 full receptor。
```

请引用 `nonsevere_contact_stats.csv` 说明默认 delta 下是否仍有 mild non-severe contacts。

---

### 3.6 receptor scope comparison

请基于 `scope_comparison.csv` 写：

```text
phase0_pocket8 与 pocket10_all_atoms 在当前 clean calibration 中是否一致？
哪些字段显示一致？例如 clash pair count、severe count、score_diff、max_depth_diff。
```

解释它能说明：

```text
当前 clean pose 的 clash-relevant protein atoms 已被 phase0_pocket8 覆盖。
phase0_pocket8 可用于 old clash diagnosis 和 R-group attribution。
```

解释它不能说明：

```text
不能说明 repair candidate 移出原 8 Å pocket 后仍安全。
不能说明 pocket10_all_atoms 没有必要。
不能说明 full receptor checked repair 已完成。
不能说明 pocket-level no clash 等于 full receptor no clash。
```

---

### 3.7 clash detector 实现与风险

请简述 detector 已实现内容：

```text
protein-ligand heavy atom vdW clash
phase0_pocket8 / pocket10_all_atoms scope
clash pairs, clash depth, severe count, score
analysis_status
unsupported chemistry / unsupported atoms / covalent / metal handling
```

请列出风险：

```text
不处理 ligand internal clash。
不处理 protein-protein / ligand-ligand clash。
full receptor 只是预留。
部分 YAML flags 可能是 policy 而非完整 runtime switch。
metal / covalent 目前是 reject/unsupported, 不是专门化学模块。
```

---

### 3.8 R-group attribution 实现与风险

请说明当前 attribution 已实现：

```text
region score
normalized region score
all-region dominant ratio
valid-Rgroup dominant ratio
dominant_valid_rgroup
failure_type
recommended_action
top_regions / top_valid_rgroups
```

必须解释：

```text
阶段 3 Top-1 / Top-3 应主要使用 valid R-group ranking。
failure type / reject / unsupported 判断需要 all-region 信息。
```

请列出风险：

```text
failure_type 仍是启发式规则。
global_pose_failure 识别仍较粗。
unsupported / unknown / scaffold 与 valid R-group 的分流需要在阶段 2/3 继续验证。
阶段 2 构造 benchmark 时不能只用 predicted dominant_region 作为保留条件。
```

---

### 3.9 repair verifier smoke 与风险

请报告 clean-vs-clean smoke：

```text
总样本数
pass 数
coordinate_valid / geometry_valid 情况
new_pair_created_count
old severe pair remaining
```

解释：

```text
clean-vs-clean 28/28 pass 说明 verifier skeleton 可稳定运行，不会误杀 identity repair。
```

也必须解释：

```text
它不能证明真实 repair candidate 能被可靠验证。
它不能证明 old severe clash 能被修掉。
它不能证明 wrong-region repair 会失败。
它不能证明 oracle repair 会通过。
```

请强调：

```text
geometry_valid 当前等同 coordinate_valid，主要是 shape 和 finite check。
RDKit sanitize、键长、价态、ligand internal clash 是阶段 2/4 升级项。
```

---

### 3.10 unsupported cases

请基于 `unsupported_cases.csv` 报告：

```text
当前是否为空？
若为空，说明本批 clean calibration 未触发 unsupported case。
不要写成 unsupported 逻辑已经完整覆盖所有未来样本。
```

如果不为空，请按 `unsupported_reason` 统计。

---

### 3.11 阶段 1 总体风险与不足

请用表格列出：

| 风险 | 当前状态 | 是否阻塞阶段 2 | 建议处理 |
|---|---|---:|---|
| full receptor 未启用 | 预留接口 | 否 | 阶段 4/5/8 shadow/final check |
| geometry_valid 仍弱 | coordinate-level | 否，但需说明 | 阶段 2/4 升级 |
| synthetic failed pose 未验证 | 未做 | 是，属于阶段 2 | 阶段 2 构造 benchmark |
| locator Top-1/Top-3 未验证 | 未做 | 是，属于阶段 3 | 阶段 3 评估 |
| real repair candidate 未验证 | 未做 | 后续阶段 | 阶段 4 进入 repair loop |
| sample size 小 | clean 51 / balanced 28 | 不阻塞 | 后续扩展 |

---

## 4. 阶段 2 实验建议必须包含的内容

最终报告必须给出阶段 2 controlled synthetic failed pose benchmark 的具体建议。

### 4.1 split 设计

建议 split：

| split | 目的 | 是否进主 locator 指标 |
|---|---|---:|
| `directed_clash` | 朝 protein hotspot 定向扰动，构造明确 single-Rgroup failure | 是 |
| `torsion_perturb` | 扰动 target R-group rotatable bond，更接近构象错误 | 是 |
| `easy_rotation` | anchor bond rotation baseline，方便 debug | 是，但需严格过滤 |
| `fragment_replace` | bulky replacement，更接近取代基太大 | 增强实验 |
| `hard_multi_region` | multi/scaffold/global stress test | 否，进 reject 指标 |
| `unsupported` | metal/covalent/invalid mask 等边界 | 否，进 unsupported 指标 |

优先级建议：

```text
directed_clash -> torsion_perturb -> easy_rotation -> fragment_replace -> hard_multi_region
```

---

### 4.2 base clean pose 过滤条件

每个 base sample 应满足：

```text
analysis_status = ok
delta = 0.4 下 phase0_pocket8 severe count = 0
delta = 0.4 下 pocket10_all_atoms severe count = 0
至少 1 个 valid R-group
target R-group 是 valid editable R-group
无 covalent / metal / unsupported chemistry
```

---

### 4.3 synthetic failed pose 接受标准

supported single-Rgroup 主集建议接受条件：

```text
target R-group 至少产生 1 个 severe protein-ligand clash pair
old clash report 可正常计算
analysis_status = ok
scaffold RMSD < 0.3 Å
non-target R-group RMSD < 0.5 Å
ligand internal severe clash = 0
max clash depth 不应极端过大, 可先限制在 1.2–1.5 Å 内
target_region_ratio_valid 达到阈值, 例如 >= 0.7
```

注意：

```text
可以记录 predicted dominant_region / dominant_valid_rgroup。
不要把 predicted dominant_region == target_rgroup 作为唯一保留条件。
否则阶段 3 Top-1 / Top-3 会被构造过程泄漏污染。
```

---

### 4.4 阶段 2 每个 case 应保存的字段

建议字段：

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

---

### 4.5 阶段 2 报告文件建议

建议输出：

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

---

### 4.6 阶段 2 verifier 必测 case

必须建议做：

| 测试 | failed coords | repaired coords | 期望 |
|---|---|---|---|
| no-repair negative | synthetic failed | synthetic failed | fail，old pair remaining > 0 |
| oracle repair | synthetic failed | original clean | pass |
| wrong-region repair | synthetic failed | wrong region modified | fail |
| new-clash repair | synthetic failed | repaired but new clash | fail，new pair created > 0 |

---

## 5. 阶段 3 实验建议必须包含的内容

阶段 3 才正式评价 rule locator。

请说明主指标只在：

```text
supported_single_rgroup synthetic failures
```

上计算。

不要把以下 case 混入 Top-1 / Top-3 主指标：

```text
unsupported
scaffold_clash
multi_region_clash
global_pose_failure
hard ambiguous reject case
```

必须建议报告：

```text
Coverage
Top-1, reject 算 miss
Top-1 covered
Top-3 rank
Top-3 operational
dominant ratio valid mean / median
Reject recall
Unsupported recall
False local repair
```

推荐解释：

```text
Top-1 是主 operational 指标。
Top-1 covered 用于拆分 coverage 与 locator accuracy。
Top-3 rank 衡量 ranking 本身。
Top-3 operational 衡量后续 Top-3 repair search 的实际可用性。
False local repair 是安全指标，越低越好。
```

---

## 6. 报告中禁止写的结论

最终报告不得写：

```text
阶段 1 已经完成生成器修复。
阶段 1 已经验证真实 repair candidate。
阶段 1 已经验证 rule locator Top-1 / Top-3。
阶段 1 已经证明 full receptor repair 安全。
zero severe false positive 说明 false positive rate 统计上等于 0。
no_clash 等于结合成功。
geometry_valid 等于完整化学合法性。
```

---

## 7. 报告中推荐写的结论

推荐写：

```text
阶段 1 已完成正式 detector、attribution、failure type 和 verifier skeleton。
默认 delta = 0.4 Å 在当前 clean calibration 上没有 severe false positive。
delta = 0.3 暴露了一个 strict boundary case，支持将其保留为 sensitivity 而非默认。
phase0_pocket8 与 pocket10_all_atoms 在 clean calibration 上结果一致，说明当前 clean pose 的 clash-relevant atoms 已被 pocket8 覆盖。
该一致性不能外推到 repair 后移动出 pocket8 的候选或 full receptor。
verifier clean-vs-clean 28/28 pass 支持进入阶段 2，但不证明真实 repair verification。
阶段 2 应构造 controlled synthetic failed pose benchmark，阶段 3 才评估 rule locator。
```

---

## 8. 最终报告建议标题

建议标题：

```text
# Clash2Feedback-GC 阶段 1 收尾报告：几何裁判系统验收与阶段 2/3 实验建议
```

建议输出路径：

```text
tmp/20260510/20260510-Clash2Feedback-GC_阶段1收尾报告.md
```

---

## 9. 最终检查清单

生成报告前请检查：

```text
[ ] 所有数字来自 reports 文件，而不是人工猜测。
[ ] 每个关键结论都能追溯到代码、docs 或 reports。
[ ] 没有把阶段 1 解释成生成器修复完成。
[ ] 没有把 clean-vs-clean smoke 解释成真实 repair candidate 验证完成。
[ ] 已解释 delta raw overlap 与 severe threshold 的关系。
[ ] 已解释 delta = 0.3 strict false positive。
[ ] 已解释 zero severe FP 与 non-severe contact 的区别。
[ ] 已解释 phase0_pocket8 / pocket10_all_atoms 的意义和局限。
[ ] 已给出阶段 2 benchmark split、过滤条件、接受标准和报告字段。
[ ] 已给出阶段 3 locator 指标设计。
```
