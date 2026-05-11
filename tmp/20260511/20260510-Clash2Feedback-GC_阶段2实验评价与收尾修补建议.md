# Clash2Feedback-GC 阶段 2 实验评价与收尾修补建议

> 日期：2026-05-10  
> 目标仓库：`BankBro/clash2feedback_gc`  
> 目标分支：`20260510-102739-phase2-implementation`  
> 参考 commit：`94dc1df087a5084a5cfd99b08ff50b467c42e927`  
> 本文用途：给 Codex 阅读，用于阶段 2 收尾检查、必要小修补和最终关闭阶段 2。  
> 重要边界：本文只处理阶段 2 收尾。阶段 2.5 baseline generation failure audit 后续单独处理，本次不要实现阶段 2.5。

---

## 0. 给 Codex 的任务摘要

请基于当前仓库阶段 2 实验结果，完成阶段 2 收尾，不要扩展到阶段 2.5。

阶段 2 当前已经完成核心目标：

```text
构建 ClashRepairBench-RG-artificial controlled synthetic failed pose benchmark。
```

当前结论是：

```text
阶段 2 可以认为已经达成目标，足够支撑阶段 3 rule locator / verifier 初步实验。
```

但收尾前仍建议修补几个小问题：

```text
1. 完成人工 visual QC，并更新 visual_qc_cases.csv / visual_qc_notes.md。
2. 修复 delta_sensitivity.csv 的空表头问题。
3. 增加 energy_delta 分布和 outlier 报告，明确 energy 目前是 record_only，不是 hard filter。
4. 更新 phase2_completion_audit.md，把仍 pending / blocked 的项收口。
5. 重新运行 compileall / pytest，必要时重新运行 phase2 脚本生成报告。
```

不要做：

```text
不要实现 phase2.5。
不要调用生成器。
不要做 repair。
不要训练模型。
不要做 whole protein-ligand complex minimization。
不要回改 phase2 v0_1 的核心 benchmark 策略。
```

---

## 1. 阶段 2 当前评价

### 1.1 总体判断

阶段 2 当前结果是可靠的，前提是只在它自己的定义范围内解释：

> 从阶段 0/1 clean pose 出发，通过受控局部扰动构造 ligand 自身合理、target R-group 与 protein 发生 severe clash 的 artificial failed pose benchmark。

它可以支撑：

```text
阶段 3 controlled rule locator / verifier preflight。
```

它不能支撑：

```text
真实生成模型失败分布已经被覆盖；
生成器修复已经有效；
真实 model-induced failures 上也能定位和修复；
full receptor 下也一定安全。
```

### 1.2 当前主要结果

阶段 2 当前核心结果如下：

```text
base clean samples: 51 / 51
total injection attempts: 2610
manifest: 2610 rows x 70 columns
supported_single_rgroup: 357
compileall: pass
pytest: 74 passed
phase2_acceptance_status: complete
```

oracle split 分布：

| split | count | 解释 |
|---|---:|---|
| `supported_single_rgroup` | 357 | 阶段 3 Top-1 / Top-3 主评估集 |
| `near_miss_contact` | 778 | 接近 protein，但未达到 severe clash |
| `duplicate_removed` | 739 | 重复或高度相似样本，已去重 |
| `invalid_conformer` | 601 | ligand 自身构象不合理，未进入主集 |
| `unsupported` | 85 | chemistry / mask / torsion 当前不支持 |
| `global_pose_failure` | 48 | clash 过深或更像整体失败 |
| `ambiguous_region` | 2 | target attribution 不够单一区域 |

supported 主集按 injection mode 分布：

| injection mode | count |
|---|---:|
| `easy_rotation` | 117 |
| `torsion_perturb` | 118 |
| `directed_clash` | 122 |

supported 主集按 base split 分布：

| split | count |
|---|---:|
| train | 260 |
| val | 18 |
| test | 79 |

### 1.3 当前结果为什么可以支撑阶段 3

阶段 3 的目标是验证 rule locator 能否从人工失败样本中找对 target R-group。阶段 2 已经提供了 357 个 `supported_single_rgroup` oracle-labeled cases，且这些样本满足：

```text
ligand_valid = true
ligand_internal_severe_clash_count = 0
target_num_severe_pairs >= 1
non_target_num_severe_pairs = 0
scaffold_num_severe_pairs = 0
target_score_ratio_valid >= 0.7
max_clash_depth <= 1.5 Å
base_split == derived_split
unknown split = 0
```

因此它们适合用于阶段 3 的主定位指标：

```text
Coverage
Top-1
Top-1 covered
Top-3 rank
Top-3 operational
dominant_ratio_valid distribution
delta sensitivity
mode-wise / difficulty-wise performance
```

注意：阶段 3 主指标只应使用 `oracle_split == supported_single_rgroup`。其他 split 只用于 reject / unsupported / near-miss 分流分析，不能混进 Top-1 / Top-3 主指标。

---

## 2. 当前阶段 2 仍需收尾的点

## P0：建议阶段 2 关闭前完成

### 2.1 完成人工 visual QC

当前 `visual_qc_cases.csv` 中抽样样本仍是：

```text
pending_manual_review
```

这说明自动抽样已经完成，但人工视觉判读还没收口。

#### 为什么需要补

三维结构任务中，自动 gate 通过不等于空间解释一定正确。尤其需要人工确认：

```text
target R-group 是否真的动了；
scaffold 是否没有漂移；
non-target R-groups 是否没有漂移；
protein-ligand clash 是否位于预期 target 区域；
invalid_conformer 是否确实是 ligand 自身不合理；
global_pose_failure 是否确实过深或过重。
```

#### 建议操作

至少抽查：

```text
10 个 supported_single_rgroup
5 个 invalid_conformer
3 个 global_pose_failure
2 个 ambiguous_region
5 个 near_miss_contact 或 duplicate_removed
```

更新文件：

```text
reports/phase2_injection/visual_qc_cases.csv
reports/phase2_injection/visual_qc_notes.md
reports/phase2_injection/phase2_completion_audit.md
```

建议 `visual_qc_status` 使用：

```text
pass
minor_issue
fail
pending_manual_review
```

如果全部抽查通过或只有 minor issue，可将 summary/audit 中的状态更新为：

```text
visual_qc_status = sampled_manual_review_passed
```

如果发现 fail，需要记录 case_id、原因和处理建议；不要静默移除样本。

---

### 2.2 修复 `delta_sensitivity.csv` 空表头问题

当前 `delta_sensitivity.csv` 表头存在空列，例如：

```text
delta_angstrom,no_target_severe,target_severe,
```

但数据行有第四列，例如：

```text
0.3,1543,982,85
0.4,1649,876,85
0.5,1750,775,85
```

这说明报告生成逻辑里有一个状态列未命名，可能是 `unsupported`、`unavailable`、空字符串或其他未归类状态。

#### 建议修复

在 `scripts/phase2_inject_artificial_clashes.py` 的 delta sensitivity report 生成逻辑里，确保所有状态都有明确列名。

建议列名：

```text
delta_angstrom
no_target_severe
target_severe
unsupported_or_unavailable
```

或者更严格地输出：

```text
delta_angstrom
target_severe
no_target_severe
unsupported
unavailable
missing_status
```

#### 修复后要求

重新生成：

```text
reports/phase2_injection/delta_sensitivity.csv
```

并补充测试，确保 CSV 不出现空表头：

```text
test_phase2_delta_sensitivity_has_no_empty_columns
```

---

### 2.3 增加 energy_delta 分布和 outlier 报告

当前配置里：

```yaml
energy_delta_threshold_mode: "record_only"
```

这意味着 MMFF / UFF energy delta 当前只是记录，不是 hard filter。这个设计可以接受，但报告中必须说清楚，否则容易被误解成 energy 已严格过滤。

#### 建议新增报告

新增：

```text
reports/phase2_injection/energy_delta_stats.csv
reports/phase2_injection/energy_delta_outliers.csv
```

`energy_delta_stats.csv` 建议按 `oracle_split` 和 `injection_mode` 分组统计：

```text
oracle_split
injection_mode
forcefield_type
count
num_available
mean_energy_delta
median_energy_delta
p90_energy_delta
p95_energy_delta
p99_energy_delta
max_energy_delta
num_large_positive_delta
num_large_negative_delta
```

`energy_delta_outliers.csv` 建议列出：

```text
case_id
oracle_split
injection_mode
target_rgroup
forcefield_type
energy_original
energy_failed
energy_delta
ligand_valid
ligand_internal_severe_clash_count
target_num_severe_pairs
max_clash_depth
visual_qc_recommended
sample_path
failed_ligand_sdf
```

#### 重要口径

不要因为 energy outlier 就自动回改 phase2 v0_1 主集。建议只新增辅助字段：

```text
energy_delta_strict_pass
energy_delta_percentile
energy_delta_outlier_flag
```

然后在 report / audit 里解释：

```text
Phase2 v0_1 uses energy_delta as record-only ligand-only diagnostic. Supported cases pass sanitize, bond, anchor, chirality, internal-clash, and protein-ligand gates, but not a strict energy-delta filter.
```

---

### 2.4 更新 `phase2_completion_audit.md`

当前 audit 中仍有：

```text
visual_qc_manual_review: blocked
```

在完成 visual QC 后，需更新为：

```text
visual_qc_manual_review: done
```

如果 visual QC 仍无法完成，也应明确保留为 blocked，并说明：

```text
blocked reason
需要人工用什么工具查看
抽样文件路径
对阶段 3 的影响
```

建议 audit 新增一节：

```text
Phase2 Closure Decision
```

内容：

```text
Phase2 is accepted for controlled phase3 locator / verifier preflight.
Phase2 does not validate model-induced generation failures.
Phase2.5 external validity audit will be handled separately.
```

---

## P1：不阻塞阶段 3，但建议尽快补

### 2.5 补 report integrity 测试

现有测试已经覆盖 phase2 rotation、ligand validity、anchor integrity、labels、no leakage 和 reports。但建议再补一个轻量报告完整性测试：

```text
tests/test_phase2_report_integrity.py
```

检查：

```text
summary.json 中 phase2_acceptance_status = complete
summary.json 中 num_accepted_supported > 0
delta_sensitivity.csv 无空列名
supported_single_rgroup_cases.csv 不包含 non-target severe > 0
supported_single_rgroup_cases.csv 不包含 scaffold severe > 0
supported_single_rgroup_cases.csv 全部 base_split == derived_split
visual_qc_cases.csv 存在且至少包含 supported / reject / invalid 抽样
```

如果 CI 中没有真实 reports，可用临时 mock CSV 测试 schema 函数；如果本地有 reports，则可做可选 local integrity test。

---

### 2.6 更新 README 或 tmp 实验报告的阶段 2 收尾说明

建议新增或更新一个收尾总结文件：

```text
tmp/20260510/20260510-phase2-closure-summary.md
```

内容包括：

```text
1. 阶段 2 当前验收结论；
2. 357 supported 主集用途；
3. 当前仍有限制：artificial benchmark only；
4. visual QC 状态；
5. energy_delta 是 record_only；
6. 阶段 3 可启动；
7. 阶段 2.5 后续单独处理。
```

这个文件可以作为阶段 3 / 2.5 之间的工程交接说明。

---

### 2.7 明确 `directed_clash` 的解释边界

`directed_clash` 是 protein-guided 合法旋转角度选择，用于稳定构造 clash，不是模拟生成模型真实采样分布。

建议在实验报告或 docs 中写清楚：

```text
Directed clash enriches controlled local steric conflicts for diagnostic stress testing. It should not be interpreted as a model-induced generation distribution.
```

---

## P2：暂不处理，放到阶段 2.5 / 3 / 4

以下内容本次不要做：

```text
1. 不要实现 phase2_5_model_induced_audit。
2. 不要引入生成模型 baseline。
3. 不要接 DiffSBDD / Pocket2Mol / TargetDiff。
4. 不要做 repair。
5. 不要训练 learned critic / ranker / adapter。
6. 不要做 full receptor hard gate。
7. 不要做 whole complex minimization。
8. 不要为了阶段 2.5 结果反向修改 phase2 v0_1 benchmark。
```

这些内容后续单独进入阶段 2.5、阶段 3 或阶段 4。

---

## 3. 阶段 2 关闭后的推荐结论写法

Codex 更新文档或 audit 时，推荐使用下面这段口径。

### 3.1 可以写

```text
Phase 2 completed the construction of ClashRepairBench-RG-artificial, a controlled synthetic failed pose benchmark for local R-group protein-ligand steric clashes. The benchmark contains 357 supported single-Rgroup cases from 51 clean base samples and 2610 injection attempts. Supported cases pass ligand-only validity gates, target severe clash gates, non-target/scaffold no-severe gates, and split-inheritance checks. Phase 2 is sufficient for Phase 3 rule locator and verifier preflight on controlled artificial failures.
```

中文：

```text
阶段 2 已完成 ClashRepairBench-RG-artificial controlled synthetic failed pose benchmark 构建。当前从 51 个 clean base samples 和 2610 次 injection attempts 中得到 357 个 supported single-Rgroup 主负样本。主集通过 ligand-only validity、target severe clash、non-target/scaffold no-severe 和 split inheritance 检查，足够支撑阶段 3 在受控人工失败样本上的 rule locator / verifier 初步实验。
```

### 3.2 不能写

不要写：

```text
阶段 2 证明了真实生成模型 failures 也能被定位。
阶段 2 证明了 repair 方法有效。
阶段 2 证明了 model-induced failures 可以被可靠修复。
阶段 2 证明了 full receptor 下也无问题。
阶段 2 的 synthetic failed poses 是真实稳定结合构象。
阶段 2 的 energy gate 已经严格过滤所有高能构象。
```

正确边界：

```text
阶段 2 只证明 controlled artificial single-Rgroup clash 子任务的数据构造已经完成。
真实生成模型失败分布由后续阶段 2.5 单独审计。
repair 效果由后续阶段 4 评估。
```

---

## 4. 阶段 3 启动建议

阶段 2 收尾后，可以启动阶段 3。

阶段 3 首先读取：

```text
reports/phase2_injection/supported_single_rgroup_cases.csv
data/benchmarks/clashrepairbench_rg_artificial/v0_1/manifest.parquet
```

阶段 3 主指标只计算：

```text
oracle_split == supported_single_rgroup
```

阶段 3 初始报告建议包括：

```text
Coverage
Top-1
Top-1 covered
Top-3 rank
Top-3 operational
dominant_ratio_valid mean / median / p95
delta sensitivity
mode-wise performance: easy_rotation / torsion_perturb / directed_clash
difficulty-wise performance: easy / medium
split-wise performance: train / val / test
```

reject / unsupported / near_miss / duplicate 不混入 Top-1 / Top-3 主分母，但可以单独统计：

```text
RejectRecall
UnsupportedRecall
FalseLocalRepair
near_miss classification
```

---

## 5. 建议 Codex 执行顺序

### Step 1：检查当前状态

```bash
python -m compileall src scripts
pytest
```

查看：

```text
reports/phase2_injection/summary.json
reports/phase2_injection/phase2_completion_audit.md
reports/phase2_injection/visual_qc_cases.csv
reports/phase2_injection/delta_sensitivity.csv
reports/phase2_injection/supported_single_rgroup_cases.csv
```

### Step 2：完成 visual QC 收尾

手动打开抽样 SDF / sample：

```text
reports/phase2_injection/visual_qc_cases.csv
```

更新：

```text
visual_qc_status
notes
visual_qc_notes.md
phase2_completion_audit.md
```

### Step 3：修 delta sensitivity report schema

确保：

```text
无空列名
所有 status 均命名
有对应测试
```

### Step 4：新增 energy delta stats / outliers report

新增：

```text
reports/phase2_injection/energy_delta_stats.csv
reports/phase2_injection/energy_delta_outliers.csv
```

并在 audit 中说明：

```text
energy_delta is record-only in phase2_v0_1.
```

### Step 5：更新 audit 和 closure summary

更新或新增：

```text
reports/phase2_injection/phase2_completion_audit.md
tmp/20260510/20260510-phase2-closure-summary.md
```

### Step 6：最终验证

```bash
python -m compileall src scripts
pytest
```

如果改动了 report generation 代码，重新运行：

```bash
python scripts/phase2_inject_artificial_clashes.py \
  --config configs/phase2_injection.yaml \
  --manifest data/processed/v0_1/manifest.parquet \
  --phase1-report-root reports/phase1_clash_detector \
  --output-root data/benchmarks/clashrepairbench_rg_artificial/v0_1 \
  --report-root reports/phase2_injection
```

---

## 6. 阶段 2 最终关闭标准

阶段 2 可以关闭，当且仅当：

```text
[ ] summary.json 仍显示 phase2_acceptance_status = complete；
[ ] supported_single_rgroup cases > 0，当前应为 357 或有解释；
[ ] compileall 通过；
[ ] pytest 通过；
[ ] delta_sensitivity.csv 无空表头；
[ ] visual_qc_cases.csv 已完成 sampled manual review，或 audit 明确 blocked 原因；
[ ] visual_qc_notes.md 已更新；
[ ] energy_delta_stats.csv 已生成；
[ ] energy_delta_outliers.csv 已生成；
[ ] phase2_completion_audit.md 已更新最终状态；
[ ] tmp/20260510/20260510-phase2-closure-summary.md 已生成；
[ ] 文档明确阶段 2 是 artificial benchmark，不是 model-induced validity；
[ ] 未实现 phase2.5；
[ ] 未调用生成器；
[ ] 未做 repair；
[ ] 未训练模型。
```

---

## 7. 最终结论

阶段 2 当前已经达成核心目标，可以作为阶段 3 的输入。

阶段 2 收尾重点不是重做实验，而是把几个解释和报告问题补完整：

```text
visual QC 收口；
delta_sensitivity 表头修正；
energy_delta record-only 透明报告；
phase2 audit 更新；
closure summary 生成。
```

完成这些后，阶段 2 可以正式关闭。阶段 2.5 作为 external validity audit 后续单独设计和实施，不应在本次阶段 2 收尾任务中混入。
