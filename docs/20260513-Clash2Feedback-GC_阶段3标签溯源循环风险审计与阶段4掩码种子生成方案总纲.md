# Clash2Feedback-GC 阶段 3：标签溯源、循环验证风险审计与阶段 4 掩码种子生成方案总纲

> 建议放置路径：`docs/20260513-Clash2Feedback-GC_阶段3标签溯源循环风险审计与阶段4掩码种子生成方案总纲.md`  
> 文档定位：阶段 3 的方案总纲 / 上位约束  
> 重要说明：本文件只负责定方向、定目标、定边界、定原理、定做法，不替代本地 Codex 后续生成的具体执行计划。  
> 网页 ChatGPT 未在本地执行、未跑实验、未修改仓库。所有字段、路径、数字、结果和结论以后续本地 Codex 在真实仓库中的核查结果为准。

---

## 0. 一句话定位

阶段 3 仍然叫 **阶段 3**，但它不再承担“独立证明定位器准确率”的职责。

阶段 3 的新定位是：

```text
标签溯源审计
+ 循环验证风险审计
+ 构造一致性检查
+ 阶段 4 掩码种子生成
```

阶段 3 的核心产物不是“定位器准确率主结论”，而是：

```text
reports/phase3_label_provenance_audit/phase4_mask_seed.csv
```

这张表为阶段 4 准备每个 case 的：

```text
参考掩码
自动预测掩码
随机掩码
保留掩码
anchor 信息
旧碰撞证据
阶段 4.0 / 阶段 4.1 候选标记
循环验证风险标记
```

---

## 1. 动机

### 1.1 为什么阶段 3 需要改口径

阶段 2 的人工失败样本里，`target_rgroup` 是人工选择并扰动的 R 基。它可以作为“人工扰动标签”和阶段 4 的参考掩码来源。

但阶段 2 的 `supported_single_rgroup` 主集不是纯人工标签集合。一个样本能否进入 `supported_single_rgroup`，不仅取决于人工扰动了哪个 R 基，还经过了检测器、R 基归因和目标主导门控。

根据此前讨论，本地 Codex 需要核查阶段 2 实现中是否存在以下逻辑：

```text
人工扰动 target_rgroup
→ 检测 protein-ligand clash
→ 将 clash evidence 归因到 scaffold / R-groups
→ 计算 target_score_ratio_valid
→ 检查 target severe clash
→ 检查 scaffold / non-target no-severe
→ 检查 max clash depth
→ 进入 supported_single_rgroup 或其他 split
```

如果 `target_score_ratio_valid` 来自 attribution-derived valid R-group scores，并且参与 `supported_single_rgroup` 相关 gate，那么在 `supported_single_rgroup` 上复用同一套 attribution 规则计算 Top-1 / Top-3，就不能被解释为无偏定位准确率。

因此阶段 3 必须改为：

```text
讲清楚标签如何来；
讲清楚 supported 主集的循环验证风险；
把 Top-1 / Top-3 降级为 construction consistency check；
为阶段 4 准备可执行的掩码种子。
```

### 1.2 阶段 3 和阶段 4 的关系

阶段 3 只负责准备：

```text
修哪里
不该动哪里
连接点在哪里
旧碰撞证据在哪里
这个 mask 来源是什么
这个 case 的循环风险是什么
```

阶段 4 才负责真正修复，并评估：

```text
自动预测掩码修复是否比随机掩码修复更有 downstream repair utility
参考掩码修复是否构成上限
后端在给定正确区域时能否稳定修复
```

---

## 2. 最终目标

阶段 3 的最终目标是生成一套可追溯、可审计、可供阶段 4 直接读取的掩码种子和审计报告。

核心输出目录建议为：

```text
reports/phase3_label_provenance_audit/
```

核心输出文件建议为：

```text
summary.json
phase2_label_provenance_audit.md
circularity_risk_audit.md
field_dependency_table.csv
set_definition_report.csv
construction_consistency_report.csv
locator_stress_report_s0.csv
locator_stress_report_s1.csv
phase4_mask_seed.csv
phase3_completion_audit.md
```

其中最重要的是：

```text
phase4_mask_seed.csv
```

阶段 3 完成后，阶段 4 应直接读取该文件，而不是临时重新决定掩码来源。

---

## 3. 阶段边界

### 3.1 阶段 3 做什么

阶段 3 做：

```text
1. 审计 phase2 标签来源；
2. 审计 target_rgroup、target_score_ratio_valid、predicted_dominant_valid_rgroup、oracle_split / supported_single_rgroup 的依赖关系；
3. 标记 supported_single_rgroup 的循环验证风险；
4. 定义 S0 / S1 / S2 三套分析集合；
5. 报告 construction consistency，而不是 independent localization accuracy；
6. 生成参考掩码、自动预测掩码、随机掩码；
7. 生成每类掩码对应的保留掩码；
8. 单独记录 anchor 信息；
9. 单独记录旧碰撞证据和蛋白侧碰撞热区；
10. 标记阶段 4.0 / 阶段 4.1 可用候选；
11. 生成 phase4_mask_seed.csv。
```

### 3.2 阶段 3 不做什么

阶段 3 不做：

```text
不训练模型；
不训练 ranker；
不训练 learned critic；
不训练 learned adapter；
不调用 DiffSBDD；
不调用 DiffDec；
不调用任何生成模型做修复；
不生成 repaired ligand；
不计算 Reliable Repair Yield；
不修改阶段 2 benchmark；
不修改阶段 2 / 阶段 2.5 的历史结果；
不把阶段 2.5 model-induced samples 放入 construction consistency denominator；
不把 predicted mask 写成 ground truth；
不把 supported_single_rgroup 写成无偏 locator benchmark。
```

---

## 4. 核心实验假设

阶段 3 的实验假设必须保守表达。

### 4.1 可采用的假设

阶段 3 可以采用以下假设：

```text
1. target_rgroup 可以作为人工扰动标签和阶段 4 参考掩码来源；
2. 当前 detect_clashes() + attribute_clashes_to_rgroups() 的输出可以作为阶段 4 的自动预测掩码策略；
3. supported_single_rgroup 可以作为阶段 4 clean local repair substrate；
4. supported_single_rgroup 上 predicted 与 target 的一致性可以作为 construction consistency check；
5. 阶段 4 才真正检验 predicted mask 是否比 random mask 有下游修复价值。
```

### 4.2 不允许采用的假设

阶段 3 不允许采用以下假设：

```text
1. supported_single_rgroup 是无偏 locator benchmark；
2. supported_single_rgroup 上 Top-1 / Top-3 可以证明定位器独立准确；
3. predicted_dominant_valid_rgroup 是 ground truth；
4. target_score_ratio_valid 与 attribution 无关；
5. 阶段 3 已证明修复有效；
6. 阶段 2.5 model-induced dominant R-group 可以当 oracle target_rgroup；
7. DiffSBDD / DiffDec plain backend 已经接收完整 H_clash 反馈。
```

---

## 5. 事实依据与结果来源

本方案的事实基础来自此前阶段 2、阶段 2.5 和 docs 口径讨论。但网页 ChatGPT 未读取本地仓库当前工作区，也未执行命令。因此所有事实需要本地 Codex 重新核查。

### 5.1 本地 Codex 必须核查的代码和配置

本地 Codex 需要核查：

```text
scripts/phase2_inject_artificial_clashes.py
src/clash2feedback/perturb/labels.py
src/clash2feedback/geometry/rgroup_attribution.py
configs/phase2_injection.yaml
```

核查问题包括：

```text
1. phase2 脚本是否记录 target_rgroup；
2. phase2 脚本是否记录 target_atom_indices；
3. phase2 脚本是否记录 anchor_scaffold_atom_idx、anchor_rgroup_atom_idx、anchor_bond_idx；
4. phase2 脚本是否记录 predicted_dominant_valid_rgroup；
5. predicted_dominant_valid_rgroup 是否来自 attribute_clashes_to_rgroups()；
6. predicted_dominant_valid_rgroup 是否只是记录字段，不直接作为 acceptance gate；
7. target_score_ratio_valid 是否来自 attribution-derived valid R-group scores；
8. target_score_ratio_valid 是否参与 supported_single_rgroup 相关 gate；
9. min_target_score_ratio_valid、max_scaffold_severe_pairs、max_non_target_severe_pairs、max_clash_depth_angstrom 等 gate 是否存在；
10. assign_oracle_split 或等价函数如何划分 supported_single_rgroup / ambiguous / reject split。
```

### 5.2 本地 Codex 必须核查的数据和报告

本地 Codex 需要核查：

```text
data/benchmarks/clashrepairbench_rg_artificial/v0_1/manifest.parquet
data/benchmarks/clashrepairbench_rg_artificial/v0_1/samples/*.pkl
reports/phase2_injection/injection_attempts.csv
reports/phase2_injection/supported_single_rgroup_cases.csv
reports/phase2_injection/summary.json
reports/phase2_injection/phase2_final_report.md
reports/phase2_5_model_induced_audit/phase2_5_final_experiment_report.md
```

核查问题包括：

```text
1. phase2 manifest / csv / pkl 是否有足够字段生成三类掩码；
2. R 基原子集合是否能从 target_atom_indices、sample masks、rgroup definitions 或 pkl 中恢复；
3. predicted_dominant_valid_rgroup 是否能映射回原子集合；
4. old_clash_pairs、protein_clash_hot_atoms、protein_clash_hot_residues 是否已有字段；
5. 若旧碰撞热区字段缺失，是否能从 clash_report 或 attribution_report 重建；
6. sample pkl 中是否能恢复 all ligand atoms；
7. sample pkl 中是否能恢复 scaffold atoms、R-group atoms、anchor 信息；
8. 阶段 2 final report 是否是历史阶段 2 关闭报告；
9. 其中旧阶段 3 Top-1 / Top-3 建议是否应按历史口径处理，不回写历史报告；
10. 阶段 2.5 model-induced samples 是否没有人工 target_rgroup；
11. 阶段 2.5 samples 是否不得进入阶段 3 construction consistency denominator。
```

---

## 6. 三套集合设计

阶段 3 不应只看 `supported_single_rgroup`。建议同时生成 S0 / S1 / S2 三套集合，用于不同目的。

### 6.1 S0：宽松人工注入集合

建议名称：

```text
S0_all_valid_injection_attempts
```

用途：

```text
压力分析；
观察 attribution-derived mask policy 在更宽松、更杂人工扰动样本上的表现；
不作为阶段 4 主修复输入。
```

候选条件由本地 Codex 按真实字段核查后定义。建议方向：

```text
ligand_valid == true
ligand_internal_severe_clash_count == 0
oracle_split not in ["unsupported", "invalid_conformer", "duplicate_removed"]
```

### 6.2 S1：弱化循环风险集合

建议名称：

```text
S1_oracle_target_local_clash_set
```

用途：

```text
辅助分析；
尽量不使用 target_score_ratio_valid >= 0.7 作为筛选条件；
弱化 attribution-dominance gate 带来的循环风险。
```

候选条件由本地 Codex 按真实字段核查后定义。建议方向：

```text
ligand_valid == true
ligand_internal_severe_clash_count == 0
target_num_severe_pairs >= 1
scaffold_num_severe_pairs == 0
non_target_num_severe_pairs == 0
max_clash_depth <= 配置阈值
do_not_use_target_score_ratio_valid_gate == true
```

注意：S1 仍然依赖 detector 的 region-level pair 统计，因此只是弱化循环风险，不是完全无循环验证。

### 6.3 S2：阶段 2 supported 主集

建议名称：

```text
S2_phase2_supported_single_rgroup
```

条件：

```text
oracle_split == "supported_single_rgroup"
```

用途：

```text
阶段 4 clean local repair 主输入；
阶段 3 construction consistency check；
phase4_mask_seed.csv 的主候选来源。
```

必须标记：

```text
circularity_risk_level = high
```

原因：

```text
S2 已经过 detector / attribution / target-dominance gates 过滤。
```

---

## 7. 掩码生成原理

### 7.1 掩码是什么

阶段 3 的掩码本质上是配体原子索引集合。

设配体原子集合为：

\[
A_L
\]

某个 R 基 \(R_k\) 的原子集合为：

\[
A_{R_k} \subseteq A_L
\]

那么编辑掩码为：

\[
M_{\text{edit}} = A_{R_k}
\]

保留掩码为：

\[
M_{\text{keep}} = A_L \setminus M_{\text{edit}}
\]

人话：

```text
编辑掩码 = 允许阶段 4 修改的 R 基原子；
保留掩码 = 配体中除编辑掩码之外的所有原子。
```

### 7.2 为什么编辑掩码使用整个 R 基

第一版阶段 3 固定：

```text
编辑掩码 = 整个目标 R 基
```

不使用：

```text
编辑掩码 = 仅发生碰撞的几个原子
```

原因：

```text
碰撞原子是证据；
R 基是化学上更合理的修复单位；
只修几个碰撞原子容易破坏键长、键角、片段几何和 anchor 连接。
```

### 7.3 anchor 如何处理

anchor 是 R 基接回 scaffold 的连接点。第一版阶段 3 固定：

```text
anchor 单独记录；
anchor 不默认加入自由编辑掩码；
anchor 用于阶段 4 后端连接约束或上下文。
```

因此阶段 3 应区分：

```text
edit_mask_atoms
keep_mask_atoms
anchor_scaffold_atom_idx
anchor_rgroup_atom_idx
anchor_bond_idx
```

不要把 anchor scaffold atom 简单混入自由编辑区域。

---

## 8. 三类掩码生成规则

### 8.1 参考掩码

参考掩码来源：

```text
target_rgroup
```

定义：

```text
oracle_mask_rgroup = target_rgroup
oracle_mask_atom_indices = target_rgroup 对应的完整 R 基原子集合
oracle_keep_atom_indices = all_ligand_atoms - oracle_mask_atom_indices
```

含义：

```text
人工扰动标签；
阶段 4 oracle 掩码来源；
阶段 4.0 后端可行性审计优先使用；
不是自动方法；
不应写成无偏定位 ground truth。
```

### 8.2 自动预测掩码

自动预测掩码来源：

```text
predicted_dominant_valid_rgroup
```

定义：

```text
predicted_mask_rgroup = predicted_dominant_valid_rgroup
predicted_mask_atom_indices = predicted_mask_rgroup 对应的完整 R 基原子集合
predicted_keep_atom_indices = all_ligand_atoms - predicted_mask_atom_indices
```

含义：

```text
attribution-derived operational mask policy；
阶段 4 自动方法；
不是 ground truth；
不是独立标签。
```

如果：

```text
predicted_dominant_valid_rgroup 不存在
predicted_dominant_valid_rgroup 不是有效 R 基
predicted R 基无法映射回原子集合
```

则必须记录：

```text
predicted_mask_available = false
predicted_mask_reason = 具体原因
phase4_1_formal_loop_candidate = false 或需要降级处理
```

不能强行编造 predicted mask。

### 8.3 随机掩码

随机掩码来源：

```text
同一配体中大小相近的随机合法 R 基
```

目的：

```text
负对照；
检验是否随便修一个 R 基也能成功；
用于阶段 4 Random / Predicted / Oracle 正式对照。
```

推荐规则：

```text
1. 从同一配体的合法 R 基候选中选；
2. 优先选择 single-anchor R 基；
3. 优先排除 target_rgroup；
4. 优先排除 predicted_dominant_valid_rgroup；
5. 优先选择重原子数接近参考 R 基或自动预测 R 基的候选；
6. 若多个候选同等匹配，使用固定 seed 随机；
7. 若没有其他合法候选，允许 fallback，但必须记录 fallback_reason。
```

必须记录：

```text
random_mask_policy
random_mask_fallback_reason
random_equals_oracle
random_equals_predicted
```

---

## 9. predicted 与 oracle 相同时如何解释

如果：

```text
predicted_mask_rgroup == oracle_mask_rgroup
```

那么核心编辑掩码自然相同：

```text
predicted_mask_atom_indices == oracle_mask_atom_indices
```

这是正常现象，不需要人为制造不同掩码。

阶段 3 必须记录：

```text
predicted_equals_oracle = true / false
```

阶段 4 分析时应分层解释：

```text
predicted == oracle 的样本；
predicted != oracle 的样本；
random == oracle 的样本；
random == predicted 的样本。
```

不能把 predicted 与 oracle 相同直接解释为“定位器已被无偏证明准确”。更准确的表述是：

```text
该 clean substrate 中，自动掩码策略与人工扰动参考区域一致。
```

---

## 10. 待验证问题

本地 Codex 需要在执行计划中回答以下问题：

```text
1. phase2 manifest / csv / pkl 中是否有足够字段生成 oracle / predicted / random 三类掩码；
2. target_atom_indices 是否就是 target_rgroup 完整原子集合；
3. 若 target_atom_indices 不完整，如何从 sample pkl 中恢复 target_rgroup 原子集合；
4. predicted_dominant_valid_rgroup 是否能映射回原子集合；
5. top_valid_rgroups_json 是否可解析；
6. random mask 候选池是否足够；
7. 单锚点 R 基如何识别；
8. random size-matched 规则按 heavy atom count 还是 atom count 实现；
9. anchor 字段是否对 oracle / predicted / random 三类掩码都可恢复；
10. old_clash_pairs 是否已有；
11. protein_clash_hot_atoms / protein_clash_hot_residues 是否已有；
12. 若旧碰撞热区缺失，是否可从 clash pairs 重建；
13. phase4_0_backend_feasibility_candidate 如何定义；
14. phase4_1_formal_loop_candidate 如何定义；
15. S0 / S1 / S2 集合真实可用样本量是多少；
16. supported 主集是否需要全部进入 phase4_mask_seed.csv；
17. 是否存在字段缺失、文件缺失、路径变更或 schema 变更。
```

---

## 11. 输入

阶段 3 建议读取但不修改以下输入。

### 11.1 阶段 2 benchmark 输入

```text
data/benchmarks/clashrepairbench_rg_artificial/v0_1/manifest.parquet
data/benchmarks/clashrepairbench_rg_artificial/v0_1/samples/*.pkl
```

### 11.2 阶段 2 report 输入

```text
reports/phase2_injection/injection_attempts.csv
reports/phase2_injection/supported_single_rgroup_cases.csv
reports/phase2_injection/summary.json
reports/phase2_injection/phase2_final_report.md
```

### 11.3 阶段 2.5 参考输入

```text
reports/phase2_5_model_induced_audit/phase2_5_final_experiment_report.md
```

阶段 2.5 只作为边界讨论和口径约束，不进入阶段 3 construction consistency denominator。

### 11.4 代码和配置输入

```text
scripts/phase2_inject_artificial_clashes.py
src/clash2feedback/perturb/labels.py
src/clash2feedback/geometry/rgroup_attribution.py
configs/phase2_injection.yaml
```

---

## 12. 输出

阶段 3 建议输出：

```text
reports/phase3_label_provenance_audit/
  summary.json
  phase2_label_provenance_audit.md
  circularity_risk_audit.md
  field_dependency_table.csv
  set_definition_report.csv
  construction_consistency_report.csv
  locator_stress_report_s0.csv
  locator_stress_report_s1.csv
  phase4_mask_seed.csv
  phase3_completion_audit.md
```

本方案不声称这些文件已经存在。本地 Codex 需要在 `/plan` 中确认最终输出路径和 schema。

---

## 13. 建议输出文件说明

### 13.1 `field_dependency_table.csv`

用于说明字段来源和能否作为标签使用。

建议字段：

```text
field_name
source_file
source_function
field_type
depends_on_manual_injection
depends_on_detector
depends_on_attribution
depends_on_target_rgroup
can_be_ground_truth
can_be_oracle_mask_source
can_be_predicted_mask_source
can_be_phase4_mask_seed_source
notes
```

典型解释：

```text
target_rgroup:
  人工扰动标签，可作为参考掩码来源。

target_score_ratio_valid:
  attribution-derived gate，不能作为独立真值。

predicted_dominant_valid_rgroup:
  attribution-derived operational mask policy 输出，可作为自动预测掩码来源，不是 ground truth。

oracle_split / supported_single_rgroup:
  detector + attribution + target gates 共同生成，不是无偏定位 benchmark。
```

### 13.2 `circularity_risk_audit.md`

必须明确：

```text
supported_single_rgroup 依赖 target_score_ratio_valid；
target_score_ratio_valid 来自 attribution-derived valid R-group scores；
因此 supported_single_rgroup 上复用同一 attribution policy 的 Top-1 / Top-3，只能作为 construction consistency check。
```

### 13.3 `construction_consistency_report.csv`

可以计算：

```text
predicted_equals_oracle
target_rank_in_top_valid_rgroups
top1_consistent
top3_consistent
```

但必须命名为：

```text
construction consistency
```

不要命名为：

```text
independent localization accuracy
```

### 13.4 `phase4_mask_seed.csv`

这是阶段 3 最重要的产物，建议字段见下一节。

---

## 14. `phase4_mask_seed.csv` 建议 schema

最终字段以本地 Codex 核查后的真实仓库实现为准。建议 schema 如下。

### 14.1 基础字段

```text
case_id
base_sample_id
base_complex_id
base_split
derived_split
oracle_split
injection_mode
difficulty_bin
set_membership_s0
set_membership_s1
set_membership_s2
circularity_risk_level
```

### 14.2 标签与归因字段

```text
target_rgroup
target_atom_indices
predicted_dominant_valid_rgroup
top_valid_rgroups_json
target_score_ratio_valid
dominant_ratio_valid_rgroups
failure_type
recommended_action
predicted_equals_oracle
```

### 14.3 参考掩码字段

```text
oracle_mask_rgroup
oracle_mask_atom_indices
oracle_keep_atom_indices
oracle_anchor_scaffold_atom_idx
oracle_anchor_rgroup_atom_idx
oracle_anchor_bond_idx
oracle_mask_available
oracle_mask_reason
```

### 14.4 自动预测掩码字段

```text
predicted_mask_rgroup
predicted_mask_atom_indices
predicted_keep_atom_indices
predicted_anchor_scaffold_atom_idx
predicted_anchor_rgroup_atom_idx
predicted_anchor_bond_idx
predicted_mask_available
predicted_mask_reason
```

### 14.5 随机掩码字段

```text
random_mask_rgroup
random_mask_atom_indices
random_keep_atom_indices
random_anchor_scaffold_atom_idx
random_anchor_rgroup_atom_idx
random_anchor_bond_idx
random_mask_available
random_mask_policy
random_mask_fallback_reason
random_equals_oracle
random_equals_predicted
```

### 14.6 旧碰撞证据字段

```text
old_clash_pairs_json
protein_clash_hot_atoms_json
protein_clash_hot_residues_json
target_num_severe_pairs
non_target_num_severe_pairs
scaffold_num_severe_pairs
num_total_severe_pairs
max_clash_depth
total_clash_score
```

### 14.7 阶段 4 使用字段

```text
phase4_0_backend_feasibility_candidate
phase4_1_formal_loop_candidate
phase4_candidate_reason
phase4_exclusion_reason
```

---

## 15. 阶段 4 接口

阶段 3 结束后，阶段 4 不应重新临时决定掩码来源。

阶段 4.0：

```text
优先使用 oracle_mask
目标：给正确修复区域时，repair backend 是否能修。
```

阶段 4.1：

```text
比较 random_mask / predicted_mask / oracle_mask
目标：检验 predicted mask 是否比 random mask 具有 downstream repair utility。
```

---

## 16. 执行硬约束

阶段 3 必须遵守：

```text
1. 不训练模型；
2. 不调用生成器；
3. 不修复分子；
4. 不生成 repaired ligand；
5. 不修改 phase2 benchmark；
6. 不修改 phase2 / phase2.5 历史结果；
7. 不把 model-induced samples 放入 construction consistency denominator；
8. 不把 predicted mask 写成 ground truth；
9. 不把 supported_single_rgroup 写成无偏定位 benchmark；
10. Top-1 / Top-3 只能叫 construction consistency check；
11. 所有字段、路径、数字、结论以后续本地仓库真实文件为准。
```

---

## 17. 禁止修改范围

本地 Codex 执行阶段 3 时，禁止修改以下历史结果和数据：

```text
reports/phase2_injection/*.csv
reports/phase2_injection/*.json
reports/phase2_injection/*.parquet
reports/phase2_injection/*.jsonl
reports/phase2_injection/*trace*

reports/phase2_5_model_induced_audit/*.csv
reports/phase2_5_model_induced_audit/*.json
reports/phase2_5_model_induced_audit/*.parquet
reports/phase2_5_model_induced_audit/*.jsonl
reports/phase2_5_model_induced_audit/*trace*

data/benchmarks/clashrepairbench_rg_artificial/v0_1/

runs/phase2_5_model_induced_audit/raw_candidates/
runs/phase2_5_model_induced_audit/standardized_candidates/
```

允许读取上述文件，但不得回写、重命名、覆盖或重生成。

如需生成新报告，应写入：

```text
reports/phase3_label_provenance_audit/
```

如需生成本次任务计划或冲突报告，应写入：

```text
tmp/20260513/
```

---

## 18. 冲突处理规则

如果方案文档与仓库事实不一致，以仓库事实为准。

本地 Codex 不得自行猜测，也不得强行把仓库改成符合方案。必须先生成冲突报告：

```text
tmp/20260513/phase3-label-provenance-mask-seed-conflict-report.md
```

冲突报告必须包含：

```text
冲突项
方案文档表述
仓库实际情况
涉及文件
影响范围
建议处理方式
是否需要人工确认
```

### 18.1 低风险冲突

低风险冲突包括：

```text
字段名不同但语义一致；
路径名不同但文件存在；
已有函数名与方案名称不同；
schema 多了无害字段；
报告文件名不同但内容可映射。
```

处理方式：

```text
在执行计划中提出字段 / 路径映射；
按仓库事实适配；
无需修改历史结果。
```

### 18.2 高风险冲突

高风险冲突包括：

```text
实验口径不同；
标签定义不同；
target_score_ratio_valid 实际不参与 gate；
predicted_dominant_valid_rgroup 实际参与 acceptance gate；
阶段 2 历史报告与方案事实冲突；
需要修改 summary.json / csv / parquet / jsonl / trace 才能推进；
需要修改 benchmark 数据才符合方案；
phase2 sample 中无法恢复 R 基原子集合；
phase2 sample 中无法恢复 anchor；
phase2 sample 中无法恢复旧碰撞证据。
```

处理方式：

```text
停止执行冲突部分；
生成 conflict report；
等待人工确认。
```

---

## 19. 风险与局限

阶段 3 必须承认以下风险和局限：

```text
1. supported_single_rgroup 存在 attribution-derived circularity risk；
2. S2 上的 Top-1 / Top-3 不能作为无偏定位准确率；
3. S1 只是弱化循环风险，不是完全无循环验证；
4. predicted mask 与 oracle mask 在很多样本上可能相同；
5. predicted == oracle 只能说明 mask policy 与人工扰动参考区域一致，不能证明无偏定位能力；
6. random mask 可能没有合适候选，需要 fallback；
7. phase2 pkl / manifest 字段可能不足，需要本地 Codex 核查和重建；
8. old_clash_hot_atoms / residues 可能需要从 clash pairs 重建；
9. 阶段 3 不证明 repair backend 可用；
10. 阶段 3 不证明修复有效；
11. 阶段 4 才能检验 predicted mask 的 downstream repair utility。
```

---

## 20. 完成标准

阶段 3 方案执行完成后，应满足以下 checklist。

```text
[ ] 已生成 phase2 标签溯源审计；
[ ] 已生成循环验证风险审计；
[ ] 已生成字段依赖表；
[ ] 已定义并统计 S0 / S1 / S2；
[ ] 已生成 construction consistency report；
[ ] 已明确 Top-1 / Top-3 只作为 construction consistency check；
[ ] 已生成 phase4_mask_seed.csv；
[ ] 参考掩码来源明确；
[ ] 自动预测掩码来源明确；
[ ] 随机掩码来源明确；
[ ] 三类掩码均有编辑掩码和保留掩码；
[ ] anchor 单独记录，不默认加入自由编辑掩码；
[ ] old clash evidence 已记录或说明重建方式；
[ ] predicted_equals_oracle 已记录；
[ ] random_equals_oracle 已记录；
[ ] random_equals_predicted 已记录；
[ ] S2 标记为 high circularity risk；
[ ] 阶段 4.0 candidate flag 已定义；
[ ] 阶段 4.1 candidate flag 已定义；
[ ] 未修改禁止修改的历史结果文件；
[ ] 未修改阶段 2 benchmark 数据；
[ ] compileall / pytest 通过，或说明无法运行原因。
```

---

## 21. 本地 Codex 后续计划要求

本文件不替代本地 Codex 执行计划。本地 Codex 必须先进入 `/plan` 模式，只规划不执行。

执行计划建议文件：

```text
tmp/20260513/phase3-label-provenance-mask-seed-codex-goal-exec-plan.md
```

如果发现冲突，先生成：

```text
tmp/20260513/phase3-label-provenance-mask-seed-conflict-report.md
```

人工确认执行计划后，再使用 `/goal` 严格按计划执行。

---

## 22. 最终总结

阶段 3 的核心不是证明“定位器找得准”，而是：

```text
讲清楚标签怎么来的；
讲清楚循环风险在哪里；
把每个 case 转成阶段 4 可用的三套掩码；
为阶段 4 的修复闭环准备干净、可追溯、可解释的输入。
```

一句话：

> 阶段 3 准备“修哪里”的施工图；阶段 4 才真正“去修并验证修没修好”。
