# Clash2Feedback-GC 阶段 1 修补清单与 docs 更新建议

> 日期：2026-05-10  
> 建议仓库路径：`tmp/20260510/20260510-Clash2Feedback-GC_阶段1修补清单与文档更新建议.md`  
> 关联分支：`20260505-180108-phase0-implementation`  
> 目的：在阶段 1 已可验收的前提下，列出进入阶段 2 前建议补齐的代码、报告与文档更新项。

---

## 0. 总结判断

阶段 1 不需要推翻重做。当前阶段 1 已经完成如下核心验收：

- protein-ligand vdW clash detector 已实现；
- R-group attribution 和 failure type 分类已实现；
- repair verifier skeleton 已实现；
- clean pool 与 balanced subset 已完成 clean calibration；
- `delta = 0.4 Å` 下 clean pool 与 balanced subset severe false positive 均为 0；
- clean-vs-clean verifier smoke 为 28 / 28 pass；
- full receptor 当前只是预留接口，不作为阶段 1–3 阻塞条件。

因此，阶段 1 可以关闭，并进入阶段 2 controlled synthetic failed pose benchmark。

但阶段 1 仍有若干需要修补的地方，主要集中在：

```text
1. verifier 仍是 skeleton，缺少 old/new pair tracking；
2. geometry_valid 的文档定义强于当前代码实现；
3. dominant_ratio 定义需要拆分，避免阶段 3 指标混淆；
4. unsupported chemistry / unsupported mask 处理需要更硬；
5. reports 缺少 case-level 诊断表；
6. docs 中阶段 3 Top-1 / Top-3 / reject / unsupported 指标需要更新；
7. BIBM 版论文文档需要收敛成“protein-ligand steric clash 定位与局部修复”的小闭环。
```

---

## 1. 修补优先级

| 优先级 | 类型 | 是否阻塞阶段 2 | 说明 |
|---|---|---:|---|
| P0 | verifier old/new pair tracking | 是，建议阶段 2 前补 | 阶段 2 需要区分旧 clash 残留和新 clash 产生 |
| P0 | `geometry_valid` 口径修正 | 是，至少要改 docs 或字段名 | 当前实现主要是 coordinate-level check |
| P0 | dominant ratio 拆分 | 是，避免阶段 3 评价混乱 | 需要区分 all-region ratio 与 valid-R-group ratio |
| P0 | unsupported handling 补强 | 是 | 避免 unsupported case 被当作 `no_clash` |
| P1 | per-scope summary | 否，但建议补 | 当前 summary 字段容易被误读为 all-scope |
| P1 | strict delta false positive case report | 否，但建议补 | 解释 `delta=0.3` 唯一 ambiguous case |
| P1 | non-severe contact stats | 否，但建议补 | 防止“zero severe FP = zero contact”的误解 |
| P1 | config-driven detector 说明 | 否 | YAML 中部分配置项当前更像 policy，不是 runtime switch |
| P2 | integration tests | 否 | 提高阶段 2/3 稳定性 |

---

## 2. P0 代码修补项

### 2.1 repair verifier 增加 old/new pair tracking

#### 当前问题

当前 `repair_verifier.py` 主要使用 aggregate score 判断：

```text
old_clash_score_before
old_clash_score_after
new_severe_clash_count
```

这足够支持 clean-vs-clean smoke，但阶段 2 会出现 synthetic failed pose。此时必须区分：

```text
旧 clash 没修掉
vs
旧 clash 修掉了但产生新 clash
```

#### 建议新增字段

在 verifier 输出中新增：

```python
{
  "old_pair_count_before": int,
  "old_pair_count_after": int,
  "old_pair_remaining_count": int,
  "old_pair_resolved_fraction": float,
  "new_pair_created_count": int,
  "new_pair_created_regions": list[str],
  "old_severe_pair_remaining_count": int,
  "new_severe_pair_created_count": int,
}
```

#### 建议 pair key

第一版使用：

```python
pair_key = (ligand_atom_idx, protein_atom_idx)
```

后续若 repair candidate 出现 atom reindex，可升级为：

```python
pair_key = (ligand_region, protein_residue_key, protein_atom_idx)
```

#### 建议判定

```python
old_pairs = set(pair_key(p) for p in failed_report["clash_pairs"])
after_pairs = set(pair_key(p) for p in repaired_report["clash_pairs"])

old_pair_remaining = old_pairs & after_pairs
new_pair_created = after_pairs - old_pairs
```

#### 阶段 2 必测 case

| case | failed coords | repaired coords | 期望 |
|---|---|---|---|
| no-repair negative | synthetic failed | synthetic failed | `old_pair_remaining_count > 0`, fail |
| oracle repair | synthetic failed | original clean | `old_pair_remaining_count = 0`, pass |
| wrong-region repair | synthetic failed | wrong region moved | fail |
| new-clash repair | synthetic failed | repaired but new clash | `new_pair_created_count > 0`, fail |

---

### 2.2 `geometry_valid` 口径修正

#### 当前问题

阶段 1 文档中 `geometry_valid` 写成：

```text
RDKit sanitize + 基础键长/坐标检查通过
```

但当前代码实现主要检查：

```text
coords shape 正确
coords finite
failed / repaired shape 一致
```

这在 clean-vs-clean smoke 中可以接受，但不等同于真正的 molecular geometry validity。

#### 修补方案 A：最小修补，推荐阶段 2 前先做

将当前字段改名或增加解释：

```python
"coordinate_valid": bool
"geometry_valid": bool  # phase1 currently aliases coordinate_valid unless full geometry checks are enabled
```

docs 中写清楚：

```text
Phase 1 implementation provides coordinate-level geometry validity for smoke testing.
RDKit sanitize, bond-length sanity checks, valence checks and ligand-internal clash checks are phase2/4 upgrades.
```

#### 修补方案 B：完整修补，建议阶段 4 前做

新增 `src/clash2feedback/verifier/geometry_checks.py`：

```text
RDKit sanitize
bond length sanity
valence check
ligand internal heavy-atom severe clash
fragment connectivity
finite coordinate check
```

---

### 2.3 dominant ratio 定义拆分

#### 当前问题

当前 attribution 输出 `dominant_ratio`，但阶段 2/3 会需要区分：

```text
dominant 是否被 scaffold / unknown / unsupported 稀释
valid R-group 内的 target 是否主导
reject / unsupported 是否应该单独分流
```

如果只保留一个 `dominant_ratio`，阶段 3 评价容易混淆。

#### 建议新增字段

在 `attribute_clashes_to_rgroups()` 输出中增加：

```python
{
  "dominant_region_all": str,
  "dominant_ratio_all_regions": float,

  "dominant_valid_rgroup": str,
  "dominant_ratio_valid_rgroups": float,
  "num_nonzero_valid_rgroups": int,

  "scaffold_score": float,
  "unsupported_region_score": float,
  "unknown_region_score": float,

  "valid_rgroup_scores": dict[str, float],
  "all_region_scores": dict[str, float],
}
```

#### 推荐定义

设所有 region 归一化分数为：

\[
s_r \ge 0
\]

则：

\[
\mathrm{dominant\_ratio\_all}
=\frac{\max_{r\in\mathcal A}s_r}{\sum_{r\in\mathcal A}s_r+\epsilon}
\]

其中 \(\mathcal A\) 包括 scaffold、valid R-groups、unsupported、unknown。

valid R-group ratio：

\[
\mathrm{dominant\_ratio\_valid}
=\frac{\max_{r\in\mathcal R_{valid}}s_r}{\sum_{r\in\mathcal R_{valid}}s_r+\epsilon}
\]

阶段 3 rule locator 的 Top-1 / Top-3 应主要使用 valid R-group ranking，而 failure type / reject / unsupported 判断应使用 all-region 信息。

---

### 2.4 unsupported chemistry 和 unsupported mask 处理补强

#### 当前问题

当前 `unsupported_cases.csv` 为空，说明本批 clean pool 没有触发 unsupported case。但这不代表 unsupported 逻辑已充分覆盖。

潜在风险：

```text
unsupported element 被跳过
→ clash_pairs 为空
→ severe_count = 0
→ failure_type = no_clash
```

这会把部分不可分析样本误报为 clean。

#### 建议新增 `analysis_status`

在 detector / attribution report 中新增：

```python
analysis_status in {
  "ok",
  "partial_due_to_unsupported_atoms",
  "unsupported_chemistry",
  "unsupported_mask",
  "detector_failed"
}
```

若存在 unsupported atom、metal、covalent ligand、invalid R-group mask，即使没有 severe clash，也不应简单标为普通 `no_clash`。

#### 建议测试

新增测试：

```text
test_unsupported_ligand_element_reported
test_unsupported_protein_element_reported
test_covalent_ligand_metadata_unsupported
test_metal_marked_unsupported
test_unsupported_rgroup_dominant_not_local_repair
test_unknown_region_dominant_not_no_clash
```

---

## 3. P1 报告修补项

### 3.1 per-scope summary

#### 当前问题

当前 `summary.json` 的 severe FP 字段容易被理解为所有 receptor scopes 的统计，但实际应明确 default scope 与 per-scope 统计。

#### 建议新增字段

```json
{
  "clean_pool_default_scope_severe_false_positive_count": 0,
  "balanced_subset_default_scope_severe_false_positive_count": 0,
  "per_scope_default_delta": {
    "phase0_pocket8": {
      "clean_pool_severe_fp": 0,
      "balanced_subset_severe_fp": 0
    },
    "pocket10_all_atoms": {
      "clean_pool_severe_fp": 0,
      "balanced_subset_severe_fp": 0
    }
  }
}
```

---

### 3.2 strict delta false positive case-level report

#### 背景

`delta=0.3` 下 clean pool 和 balanced subset 各出现 1 个 severe false positive，failure type 为 `ambiguous_region_clash`。阶段 1 可以接受，但应记录 case-level 诊断，便于判断这是合理近接触、数据问题还是 attribution 问题。

#### 建议新增文件

```text
reports/phase1_clash_detector/strict_delta_false_positive_cases.csv
```

字段：

```text
sample_id
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
top_regions_json
top_clash_pairs_json
```

---

### 3.3 non-severe contact stats

#### 背景

默认 `delta=0.4` 下 severe false positive 为 0，但部分样本仍有 mild non-severe close contacts。需要显式报告，避免误写成“clean pool 没有任何 close contact”。

#### 建议新增文件

```text
reports/phase1_clash_detector/nonsevere_contact_stats.csv
```

字段：

```text
dataset_name
receptor_scope
delta_angstrom
num_samples
num_samples_with_any_clash_pair
num_samples_with_nonsevere_clash_pair
median_num_clash_pairs
p95_num_clash_pairs
max_num_clash_pairs
median_max_depth
p95_max_depth
max_depth
```

---

### 3.4 scope comparison report

#### 背景

当前 `phase0_pocket8` 与 `pocket10_all_atoms` 在 clean calibration 中结果完全一致。这支持阶段 1，但不能证明 repair 后移动到 pocket8 边界外的候选也能被 pocket8 捕捉。

#### 建议新增文件

```text
reports/phase1_clash_detector/scope_comparison.csv
```

字段：

```text
sample_id
dataset_name
delta_angstrom
pocket8_num_clash_pairs
pocket10_num_clash_pairs
pocket8_num_severe
pocket10_num_severe
score_diff
max_depth_diff
scope_result_same
```

---

## 4. P2 测试补强项

建议新增 mock-based tests，不依赖 raw PDB/SDF 或 processed pickle。

```text
tests/test_phase1_summary_counts.py
tests/test_verifier_old_new_pair_tracking.py
tests/test_unsupported_handling.py
tests/test_rgroup_ratio_definitions.py
tests/test_nonsevere_contact_stats.py
tests/test_scope_comparison_report.py
```

关键测试点：

| 测试 | 目的 |
|---|---|
| non-severe contact 仍为 `no_clash` | 确认 severe gate 生效 |
| unsupported element 不应静默变成 clean | 防止误报 |
| old clash remaining 与 new clash created 可区分 | 支撑阶段 2 verifier |
| scaffold-dominant clash 不进入 local repair | 安全性 |
| dominant valid R-group ratio 与 all-region ratio 不同 | 支撑阶段 3 |
| per-scope summary 正确 | 防止 summary 误读 |

---

## 5. docs 更新建议

### 5.1 更新 `docs/20260508-Clash2Feedback-GC_阶段1碰撞检测器与可靠验证器方案.md`

#### A. 增加 raw overlap 解释

当前文档已定义：

\[
c_{ij}=\max(0,r_i+r_j-\delta-d_{ij})
\]

建议补充：

\[
o_{ij}=r_i+r_j-d_{ij}
\]

\[
c_{ij}=\max(0,o_{ij}-\delta)
\]

默认：

```text
δ = 0.4 Å
severe_depth_threshold = 0.4 Å
```

因此：

```text
clash pair: raw vdW overlap > 0.4 Å
severe clash: raw vdW overlap >= 0.8 Å
```

避免读者误解为“0.4 Å overlap 直接等于 severe clash”。

#### B. 修正 `geometry_valid` 口径

建议改成：

```text
Phase 1 implementation provides coordinate-level geometry validity for smoke testing.
RDKit sanitize, bond-length sanity, valence checks and ligand-internal clash checks are phase2/4 upgrades unless implemented explicitly.
```

#### C. 增加 zero severe FP 的边界

建议增加：

```text
Zero severe false positives on phase-1 clean calibration does not imply zero close contacts or a statistically zero false-positive rate. Mild non-severe contacts may exist and are intentionally tolerated.
```

#### D. 增加 pocket8 / pocket10 一致结果解释

建议增加：

```text
Identical phase0_pocket8 and pocket10_all_atoms results indicate that current clean-pose clash-relevant atoms are covered by the 8 Å pocket. It does not validate repair candidates that move outside the phase0_pocket8 region.
```

#### E. 明确当前 detector config flags 的性质

若暂不实现 runtime-switchable detector config，则写：

```text
The detector flags in the phase-1 YAML document the default policy. In v0_1, not all flags are runtime-switchable unless explicitly wired into detect_clashes().
```

---

### 5.2 更新 `docs/20260504-03-Clash2Feedback-GC_总体实验递进路线.md`

阶段 3 rule locator 指标需要从简单的：

```text
R-group Top-1 > 70%
R-group Top-3 > 90%
dominant ratio > 0.75
```

升级为：

```text
Coverage
Top1
Top1_covered
Top3_rank
Top3_op
RejectRecall
UnsupportedRecall
FalseLocalRepair
```

#### 推荐公式

令 \(S\) 为 supported single-R-group synthetic failures。

对每个样本 \(i\in S\)：

| 符号 | 含义 |
|---|---|
| \(y_i\) | 真实 target R-group |
| \(\hat y_i\) | 预测 dominant R-group |
| \(l_i\) | 是否预测为 local repair |
| \(T_i^{(3)}\) | valid R-groups 的 Top-3 ranking |

Coverage：

\[
\mathrm{Coverage}
=
\frac{1}{|S|}
\sum_{i\in S}\mathbf{1}[l_i=1]
\]

Top-1，reject 算 miss：

\[
\mathrm{Top1}
=
\frac{1}{|S|}
\sum_{i\in S}\mathbf{1}[l_i=1\land \hat y_i=y_i]
\]

Top-1 covered：

\[
\mathrm{Top1}_{covered}
=
\frac{
\sum_{i\in S}\mathbf{1}[l_i=1\land \hat y_i=y_i]
}{
\sum_{i\in S}\mathbf{1}[l_i=1]
}
\]

Top-3 rank：

\[
\mathrm{Top3}_{rank}
=
\frac{1}{|S|}
\sum_{i\in S}\mathbf{1}[y_i\in T_i^{(3)}]
\]

Top-3 operational：

\[
\mathrm{Top3}_{op}
=
\frac{1}{|S|}
\sum_{i\in S}\mathbf{1}[l_i=1\land y_i\in T_i^{(3)}]
\]

Reject recall：

\[
\mathrm{RejectRecall}
=
\frac{1}{|R|}
\sum_{i\in R}\mathbf{1}[\hat a_i\in\{reject,expand,full\_resampling\}]
\]

Unsupported recall：

\[
\mathrm{UnsupportedRecall}
=
\frac{1}{|U|}
\sum_{i\in U}\mathbf{1}[\hat a_i=unsupported]
\]

False local repair：

\[
\mathrm{FalseLocalRepair}
=
\frac{1}{|R|+|U|}
\sum_{i\in R\cup U}\mathbf{1}[\hat a_i=local\_repair]
\]

解释：

```text
Top1 是主 operational 指标，reject 算 miss。
Top1_covered 只看系统愿意进入 local repair 的样本，用来判断 locator 本身准不准。
Top3_rank 衡量 ranking 质量。
Top3_op 衡量真实可用于 Top-3 repair search 的比例。
RejectRecall 和 UnsupportedRecall 评价安全分流。
FalseLocalRepair 是避免危险误修的关键安全指标。
```

---

### 5.3 更新 `docs/20260504-02-Clash2Feedback-GC_第一篇论文实验方案.md`

该文档目前偏完整第一篇路线，包含学习型纠错器、排序器、适配器等较大范围。若目标是 BIBM full paper，建议新增或改写一个 BIBM 收敛版小节：

```text
BIBM 版不做完整 Clash2Feedback-GC 大框架。
BIBM 版聚焦 protein-ligand steric clash 的 failure-localized repair。
主线是 Clash2Mask + mask-guided local repair + regression verifier。
```

推荐 BIBM 版主问题：

```text
给定一个在 pocket 中发生局部 protein-ligand steric clash 的 failed ligand candidate，
定位主要失败 R-group，
只修该局部区域，
并验证 old clash resolved、no new clash、scaffold preserved、non-edit region preserved。
```

推荐 BIBM 版最小实验：

| 模块 | 最低要求 |
|---|---|
| benchmark | injected split + small natural/model-induced split |
| locator | rule locator / Clash2Mask |
| repair | local torsion / conformer repair，R-group resampling 可作为增强 |
| verifier | resolved old clash + no new clash + scaffold/non-edit RMSD |
| baselines | hard filter, resampling, full-ligand repair, random mask, reference mask |
| main metric | Reliable Repair Yield |

推荐主趋势：

\[
\text{Random Mask Repair}
<
\text{Predicted Mask Repair}
<
\text{Reference Mask Repair}
\]

以及：

\[
\text{Local Repair}
>
\text{Re-sampling / Full-ligand Repair}
\]

但这里的“大于”指：

```text
reliable repair yield
scaffold preservation
non-edit preservation
no-new-clash rate
cost per success
```

不要把 docking score 作为主指标。

---

### 5.4 更新 `docs/20260504-01-Clash2Feedback-GC_完整方案与升级路线.md`

建议新增阶段 1 实际结果摘要：

```text
Phase 1 completed on 51 clean pool samples and 28 balanced subset samples.
Default delta = 0.4 Å yielded zero severe false positives on the current clean calibration.
Verifier clean-vs-clean smoke passed 28 / 28.
These results support moving to controlled synthetic failed pose construction, but do not validate generator repair or rule locator Top-1 / Top-3 on failed samples.
```

并新增重要警告：

```text
During phase 2 benchmark construction, predicted dominant_region should be recorded but should not be used as the only acceptance criterion. Otherwise phase 3 Top-1 / Top-3 evaluation will be biased by construction.
```

---

### 5.5 新增阶段复盘文档到 tmp

建议新增：

```text
tmp/20260510/20260510-Clash2Feedback-GC_阶段1结果复盘与阶段2准备清单.md
```

内容可以包括：

```text
1. 阶段 1 是否验收：yes
2. delta=0.4 为什么作为默认值
3. clean pool / balanced subset severe false positive 为 0 的意义与局限
4. verifier smoke 28/28 的意义与局限
5. 阶段 2 controlled synthetic failed pose benchmark 准备清单
6. 阶段 3 Top-1 / Top-3 / reject / unsupported 指标定义
7. 当前不应声称的内容：生成器修复、人工失败验证、full receptor checked repair
```

---

## 6. 阶段 2 前 preflight checklist

进入阶段 2 前，建议确认：

```text
[ ] summary.json 增加 per-scope default-delta 统计
[ ] strict_delta_false_positive_cases.csv 已输出
[ ] nonsevere_contact_stats.csv 已输出
[ ] scope_comparison.csv 已输出
[ ] verifier 支持 old_pair_remaining / new_pair_created
[ ] geometry_valid 已改名或文档降级为 coordinate-level
[ ] attribution 输出 dominant_ratio_all_regions 与 dominant_ratio_valid_rgroups
[ ] unsupported case 不会静默变成普通 no_clash
[ ] docs 已更新 Top1 / Top3 / reject / unsupported 指标
[ ] 阶段 2 benchmark construction 不使用 predicted dominant_region 作为唯一保留条件
```

---

## 7. 当前不要做的事情

以下内容不建议作为阶段 1 修补项，否则会拖慢阶段 2：

```text
1. 不要把 full receptor 作为阶段 1–3 阻塞项；
2. 不要把阶段 1 改成 Top-1 / Top-3 验收；
3. 不要现在接生成器修复；
4. 不要声称 clean calibration 证明真实 false positive rate = 0；
5. 不要声称 verifier smoke 证明真实 repair candidate 可验证；
6. 不要把 docking score 作为 BIBM 版主指标。
```

---

## 8. 建议落地顺序

### 第一步：最小代码修补

```text
1. verifier old/new pair tracking
2. dominant ratio 拆分
3. unsupported handling 补强
4. per-scope summary
```

### 第二步：补 reports

```text
1. strict_delta_false_positive_cases.csv
2. nonsevere_contact_stats.csv
3. scope_comparison.csv
4. enhanced verifier_gate_report.csv
```

### 第三步：补测试

```text
1. test_verifier_old_new_pair_tracking.py
2. test_rgroup_ratio_definitions.py
3. test_unsupported_handling.py
4. test_phase1_report_extensions.py
```

### 第四步：更新 docs

```text
1. 阶段 1 文档：delta raw overlap、geometry_valid skeleton、zero severe FP 边界
2. 总体路线：阶段 3 指标改成 Coverage / Top1 / Top3 / reject / unsupported split
3. 第一篇论文方案：收敛成 BIBM 小闭环版本
4. 完整方案：加入阶段 1 实际结果和 benchmark construction 防泄漏提醒
```

---

## 9. 建议提交信息

```bash
git add tmp/20260510/20260510-Clash2Feedback-GC_阶段1修补清单与文档更新建议.md
git commit -m "docs: summarize phase1 patch plan and docs updates"
```

如果后续直接实现代码修补，可以分成独立 commit：

```bash
git commit -m "feat(verifier): track old and new clash pairs"
git commit -m "feat(attribution): split dominant ratio definitions"
git commit -m "feat(reports): add phase1 diagnostic extension reports"
git commit -m "docs: update phase1 and phase3 metric definitions"
```

---

## 10. 最终结论

阶段 1 当前没有硬伤，可以进入阶段 2。  
但为了让阶段 2/3 的 benchmark、locator evaluation 和 BIBM 版论文叙事更稳，建议优先修补：

```text
old/new clash pair tracking
geometry_valid 口径
R-group dominant ratio 拆分
unsupported handling
strict delta false-positive case report
non-severe contact stats
per-scope summary
阶段 3 指标文档
BIBM 小闭环文档
```

这些修补完成后，阶段 2 的 controlled synthetic failed pose benchmark 会更容易形成可复现、可解释、可投稿的实验闭环。
