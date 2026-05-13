# Clash2Feedback-GC docs 文档调整建议：阶段 3 与阶段 4 新口径

> 日期：2026-05-12  
> 建议本地放置路径：`tmp/20260512/20260512-Clash2Feedback-GC_docs文档调整建议_阶段3与阶段4新口径.md`  
> 使用方式：交给本地 Codex 阅读，并让 Codex 在真实仓库中核查后更新 `docs/` 下相关 Markdown 文档。  
> 重要声明：本文件是网页 ChatGPT 基于当前讨论和已查看仓库内容整理的文档调整建议；网页 ChatGPT 未访问本地运行环境，未执行代码，未修改仓库。所有路径、字段、数字、commit、报告状态、测试结果必须由本地 Codex 在真实仓库中核查。若本文件与仓库事实冲突，以仓库事实为准，并先列出冲突，不得自行猜测或编造。

---

## 0. 本次 docs 调整的核心结论

当前阶段 3 的旧口径已经不适合继续使用。

旧口径大致是：

```text
阶段 3 = 规则 locator 独立定位评估
目标 = 验证规则 locator 能否找对失败 R-group
主指标 = R-group Top-1 / Top-3
```

新的口径应改成：

```text
阶段 3 = Phase2 标签溯源 + 循环验证风险审计 + 阶段 4 mask seed 生成
```

原因是：

```text
阶段 2 的 target_rgroup 是人工注入时被扰动的 R-group；
但 supported_single_rgroup 主集不是纯人工标签集合；
它是经过 detector / attribution / target-dominance gates 筛选后的 clean local repair substrate。
```

因此，在 `supported_single_rgroup` 上用同一套 `detect_clashes()` + `attribute_clashes_to_rgroups()` 再计算 Top-1 / Top-3，只能作为：

```text
construction consistency check
```

不能作为：

```text
independent localization benchmark
```

后续论文和 docs 应把真正的方法价值放到阶段 4：

```text
Predicted mask 作为 operational mask policy，
在同一 repair backend 和同一 candidate budget 下，
是否比 size-matched random mask 更能产生 reliable repaired candidates。
```

---

## 1. 已确认的关键事实口径

以下事实应由本地 Codex 再次核查源码和报告，但当前讨论中已形成明确判断。

### 1.1 `target_rgroup` 与 `supported_single_rgroup` 不是一回事

`target_rgroup`：

```text
人工注入时实际被扰动的 R-group。
```

`target_rgroup` 可以理解为干预标签，因为它来自人工选择和扰动操作。

但 `supported_single_rgroup`：

```text
不是纯人工标签；
它经过了 ligand quality gate、protein-ligand clash detector、R-group attribution、
target score ratio、non-target/scaffold no-severe 等自动 gates。
```

因此，docs 必须区分：

```text
target_rgroup = 人工注入目标；
supported_single_rgroup = attribution-aware filtered clean local repair subset。
```

### 1.2 阶段 2 的 supported 主集存在循环验证风险

阶段 2 构造 supported 主集时，使用了类似以下流程：

```text
人工扰动 target R-group
→ detect_clashes()
→ attribute_clashes_to_rgroups()
→ assign_oracle_split()
→ 根据 target_score_ratio_valid 等条件决定 oracle_split
```

其中：

```text
target_score_ratio_valid
```

本身来自 attribution-derived scores。

因此，如果阶段 3 继续在 `supported_single_rgroup` 上用同一个 attribution 方法证明 Top-1 / Top-3，很容易形成：

```text
先用这套规则筛出适合这套规则的样本；
再用这套规则证明自己在这些样本上表现好。
```

这个结论不能作为无偏定位能力证明。

### 1.3 阶段 3 仍保留，但任务必须调整

不要删除阶段 3，也不要改成阶段 3A / 3B 的正式阶段名。项目路线中仍叫：

```text
阶段 3
```

但阶段 3 的任务应改为：

```text
1. Phase2 label provenance audit；
2. circularity risk audit；
3. construction consistency check；
4. phase4 mask seed generation。
```

### 1.4 阶段 4 的 predicted mask 仍使用已有 locator 代码

阶段 4 中：

```text
系统自己判断修哪个 R-group
```

仍然沿用现有代码库里的方法：

```text
detect_clashes()
→ attribute_clashes_to_rgroups()
→ dominant_valid_rgroup / top_valid_rgroups
→ predicted repair mask
```

但它的角色必须明确为：

```text
operational mask policy
```

而不是 ground truth，也不是最终裁判。

### 1.5 Verifier 与 locator 必须区分

Locator 回答：

```text
修哪里？
```

Verifier 回答：

```text
修完后是否可靠？
```

Verifier 可以用 clash detector 做 old clash / new clash regression test，因为任务本身是 protein-ligand steric clash repair。但 verifier 不能用：

```text
predicted_dominant == target_rgroup
```

作为修复成功标准。

阶段 4 的成功标准应包括：

```text
old clash resolved
no new severe clash
ligand validity
scaffold RMSD
non-mask RMSD
anchor consistency
fixed-region preservation
```

---

## 2. docs 必须统一的新阶段定义

### 2.1 阶段 3 新定义

推荐统一表述：

```text
阶段 3：标签溯源、循环验证风险审计与阶段 4 mask seed 生成。
```

阶段 3 的目标是：

```text
1. 审计 phase2 supported_single_rgroup 的标签来源和筛选依赖；
2. 明确 detector / attribution / target-dominance gates 对主集的影响；
3. 冻结现有 attribution 规则作为阶段 4 的 predicted mask policy；
4. 生成阶段 4 所需的 oracle / predicted / random masks；
5. 报告 supported set 上的 Top-1 / Top-3 作为 construction consistency check，而非 independent localization accuracy。
```

阶段 3 不应再被定义成：

```text
独立证明规则 locator 能找对失败 R-group。
```

### 2.2 阶段 4 新定义

阶段 4 不应直接进入大规模完整 repair loop。建议分成：

```text
阶段 4.0：local repair backend feasibility audit
阶段 4.1：Random / Predicted / Oracle formal repair loop
阶段 4.2：可选 clash-guided denoising prototype
```

#### 阶段 4.0

目标：

```text
优先用 Oracle mask 测试局部生成 / 修复后端是否可用。
```

待核查后端：

```text
DiffDec plain local R-group generation
DiffSBDD inpainting
rule-only torsion / conformer repair
DiffSBDD full resampling baseline
```

核心问题：

```text
给正确 mask，后端能不能稳定生成、接回 anchor、保持 scaffold / keep region，并通过 verifier？
```

#### 阶段 4.1

目标：

```text
在后端可用后，比较 Random / Predicted / Oracle mask 的下游修复效果。
```

核心比较：

```text
Random mask + same backend
Predicted mask + same backend
Oracle mask + same backend
```

核心 claim：

```text
Predicted mask policy 是否比 random mask 有 downstream repair utility。
```

#### 阶段 4.2 可选

如果想证明 `H_clash` / hot region feedback 真的进入生成过程，需要改或封装 sampling / denoising loop，加入：

```text
clash penalty / hot region guidance
```

如果没有实现 guided sampling，不得声称：

```text
clash heatmap 直接指导了扩散模型去噪过程。
```

---

## 3. 需要优先调整的 docs 文件

本节列出需要更新的文档范围和建议修改点。实际是否存在这些文件、文件名是否完全一致、文件内容是否已被更新，必须由本地 Codex 核查。

---

### P0-1. `docs/20260504-03-Clash2Feedback-GC_总体实验递进路线.md`

优先级：最高。

#### 当前风险

该文档旧版本把阶段 3 写成：

```text
规则版定位与反馈；
验证规则 locator 能否找对失败 R-group；
R-group Top-1 > 70%；
R-group Top-3 > 90%；
dominant ratio 平均值 > 0.75。
```

这会误导后续实验，把阶段 3 当成独立 locator benchmark。

#### 建议修改

将阶段 3 从：

```text
规则版定位与反馈
```

改为：

```text
阶段 3：标签溯源、循环验证风险审计与阶段 4 mask seed 生成
```

将阶段 3 主要产出改为：

```text
reports/phase3_label_provenance_audit/
  phase2_label_provenance_audit.md
  circularity_risk_audit.md
  construction_consistency_report.csv
  phase4_mask_seed.csv
  summary.json
```

删除或降级如下通过标准：

```text
R-group Top-1 > 70%
R-group Top-3 > 90%
dominant ratio mean > 0.75
```

改为：

```text
Top-1 / Top-3 仅作为 construction consistency check；
不作为 independent localization benchmark。
```

Mini-Loop 0 也应同步修改：

旧：

```text
规则 locator Top-1 > 70%
规则 locator Top-3 > 90%
```

新：

```text
phase2 label provenance audit 完成；
circularity risk level 明确；
phase4_mask_seed.csv 生成；
supported set 上的 Top-1 / Top-3 仅作为 construction consistency check。
```

阶段 4 小节改为：

```text
阶段 4.0：backend feasibility audit
阶段 4.1：formal repair loop
阶段 4.2：optional clash-guided denoising prototype
```

---

### P0-2. `docs/20260504-02-Clash2Feedback-GC_第一篇论文实验方案.md`

优先级：最高。

#### 当前风险

该文档容易把 BIBM 版论文继续写成：

```text
locator 独立定位准确率 + local repair
```

或者把：

```text
R-group Top-1 Accuracy
```

当成核心主贡献。

#### 建议修改

将第一篇论文 RQ 重写为：

```text
RQ1：Phase2 supported set 的标签依赖和循环验证风险是什么？
RQ2：Predicted mask policy 是否在 downstream repair 中比 random mask 更有用？
RQ3：Local repair 是否比 full resampling / full-ligand repair 更能保持 scaffold 和 non-mask region？
RQ4：若实现 guided sampling，clash heatmap 是否能提高候选生成效率？
```

注意：

```text
RQ4 只有在实现 clash-guided denoising 后才能作为主实验；
否则只能作为 future work 或 exploratory prototype。
```

修改 BIBM 版贡献：

旧贡献若包含：

```text
证明 locator 能准确定位失败 R-group。
```

应改成：

```text
审计 controlled repair substrate 的标签依赖；
冻结 attribution-based mask policy；
通过 downstream repair utility 评估 mask policy 的实际价值。
```

修改主结果：

```text
Random mask repair < Predicted mask repair < Oracle mask repair
```

这个趋势应解释为：

```text
Predicted mask policy 的下游修复价值
```

而不是：

```text
无偏 locator accuracy。
```

---

### P0-3. `docs/20260510-Clash2Feedback-GC_阶段2人工局部碰撞注入最终落地方案.md`

优先级：最高。

#### 当前风险

阶段 2 方案可能仍把 `supported_single_rgroup` 描述成：

```text
带真实失败区域标签的数据
```

但没有足够强调它经过 attribution-derived target dominance gate。

#### 建议新增小节

建议新增：

```text
阶段 2 标签来源与后续使用边界
```

写清楚：

```text
target_rgroup 是人工注入时被扰动的 R-group；
supported_single_rgroup 是 ligand quality、target severe clash、scaffold/non-target no-severe、
target_score_ratio_valid、max_depth 等 gates 后的 clean local repair subset；
target_score_ratio_valid 来自 attribution-derived valid R-group scores；
因此 supported_single_rgroup 不应用作 independent locator benchmark；
它适合作为阶段 4 clean local repair substrate。
```

建议把阶段 3 后续使用改为：

```text
阶段 3 使用 phase2 结果做 label provenance audit、circularity risk audit 和 phase4 mask seed generation。
```

---

## 4. 需要同步调整的 docs 文件

### P1-1. `docs/20260504-01-Clash2Feedback-GC_完整方案与升级路线.md`

优先级：中高。

#### 建议修改点

保留总框架：

```text
失败诊断 → 结构化修复协议 → 生成器可执行控制 → 局部再生成 → 旧错误感知验证
```

但需要改以下内容：

1. 阶段 3 描述改为 label provenance / mask seed；
2. `R-group Top-1 Accuracy` 不再作为 phase2 supported set 上的强独立定位指标；
3. 增加 “operational mask policy” 概念；
4. 增加 “downstream repair utility claim” 概念；
5. 增加 “DiffDec / DiffSBDD plain backend 不是完整 feedback-guided denoising” 的说明；
6. 若提到 `H_clash` 被生成器使用，必须区分：
   - 后处理 verifier 使用；
   - adapter 参数使用；
   - guided denoising 中直接使用。

建议新增说明：

```text
在冻结原版生成后端设定下，H_clash 和 severity 多数情况下不会直接进入模型去噪过程；
只有实现 clash penalty / hot region guidance 后，才能声称旧碰撞热区参与生成过程。
```

---

### P1-2. `docs/20260511-Clash2Feedback-GC_阶段2.5模型诱导失败外部有效性审计落地方案.md`

优先级：中。

#### 建议修改点

该文档整体边界是正确的：阶段 2.5 不训练、不 repair、不 baseline ranking、不回改 phase2。

建议补充：

```text
阶段 2.5 的 model-induced samples 不进入阶段 3 Top-1 / Top-3；
阶段 2.5 的 single_rgroup_clash 只是 taxonomy，不是 oracle target R-group；
阶段 2.5 结果提示：DiffSBDD de novo generation 中 single-Rgroup clash 很少，因此论文主张应收窄为 controlled local repair substrate，而不是声称真实 de novo failures 主要是 R-group clash。
```

如果已有：

```text
reports/phase2_5_model_induced_audit/phase2_5_final_experiment_report.md
```

则 docs 应引用该最终报告，并避免继续使用阶段 2.5 旧口径。

---

### P1-3. `docs/external_baselines.md`

优先级：中。

#### 建议新增小节

```text
Candidate local repair backends
```

建议记录：

```text
DiffSBDD:
  role:
    - de novo audit baseline
    - full resampling baseline
    - candidate inpainting backend
  limitation:
    - 原生不直接接收完整 clash feedback
    - H_clash / old-clash-resolved / no-new-clash 主要由 verifier / selector 使用
    - 若要生成过程中避开 old clash heatmap，需要 guided sampling patch

DiffDec:
  role:
    - scaffold decoration / R-group generation candidate backend
    - 阶段 4.0 backend feasibility audit 第一优先核查对象
  limitation:
    - 原版 DiffDec 是 anchor-aware R-group resampling
    - 不保证避开旧 clash
    - 不原生接收 H_clash / severity / no-new-clash 约束
```

如果本地还没有验证 DiffDec 环境和 checkpoint，必须写：

```text
status: to_be_verified_locally
```

不能写：

```text
ready
```

---

## 5. 可能需要调整的文档

### P2-1. `README.md`

优先级：低到中。

如果 README 当前只写到阶段 2.5 用法，可以暂时不加阶段 3 / 4 命令。

但建议增加一条路线说明：

```text
后续阶段 3 将按新口径执行：label provenance audit、circularity risk audit、phase4 mask seed generation；
后续阶段 4 将先做 backend feasibility audit，再做 Random / Predicted / Oracle formal repair loop。
```

不要提前写具体命令，除非本地已经实现阶段 3 / 4 脚本。

---

### P2-2. 阶段 4 方案文档

如果本地已有：

```text
docs/20260512-Clash2Feedback-GC_阶段4局部碰撞最小修复闭环方案总纲.md
```

必须重点修。

#### 应改内容

旧：

```text
阶段 4 直接做最小修复闭环
```

新：

```text
阶段 4.0 先做 oracle-mask backend feasibility audit；
阶段 4.1 再做 formal repair loop。
```

旧：

```text
DiffDec / DiffSBDD 接收完整错误反馈
```

新：

```text
DiffDec / DiffSBDD plain 后端只能接收部分结构化几何条件；
完整 H_clash feedback 需要 verifier / selector 或 guided sampling patch。
```

旧：

```text
rule-only torsion / conformer repair 作为主方法
```

新：

```text
rule-only repair 只能作为 baseline / sanity check，不是主方法。
```

旧：

```text
clash heatmap 指导生成
```

新：

```text
除非实现 clash-guided denoising，否则 clash heatmap 只参与后处理 verifier / selector。
```

---

## 6. docs 中必须避免的旧表述

以下表达应删除、改写或加限定：

```text
阶段 3 证明规则 locator 能独立找对失败 R-group。
supported_single_rgroup 是无偏 locator benchmark。
R-group Top-1 > 70% 是阶段 3 的主要关闭条件。
target_rgroup ground truth 完全不受 detector / attribution 流程影响。
supported_single_rgroup 上的 Top-1 / Top-3 能代表真实失败定位能力。
DiffDec 能直接接收完整 Clash2Feedback 错误反馈。
DiffSBDD / DiffDec 能直接理解 H_clash、severity、old clash resolved 目标。
plain local resampling 就等于 feedback-guided repair。
我们不是采样方法。
阶段 4 可直接证明 Clash2Feedback 比采样挑选型模型更强。
阶段 2.5 证明真实 de novo failures 主要是 single-Rgroup clash。
global_pose_failure 一定代表整体 pose 放错。
```

---

## 7. docs 中推荐统一的新表述

建议统一使用以下表述。

### 7.1 阶段 3

```text
阶段 3 仍叫阶段 3，但新定位是 label provenance audit + circularity risk audit + phase4 mask seed generation。

target_rgroup 是人工扰动标签；
supported_single_rgroup 是经过 detector / attribution / target-dominance gates 过滤后的 clean local repair substrate。

supported_single_rgroup 上的 Top-1 / Top-3 只能作为 construction consistency check；
不能作为 independent localization benchmark。

阶段 3 的核心交付物是 phase4_mask_seed.csv，
其中包含 oracle / predicted / random masks，以及 circularity risk 标记。
```

### 7.2 阶段 4

```text
阶段 4 的 predicted mask 来自现有 detect_clashes + attribute_clashes_to_rgroups，
是 operational mask policy，不是 ground truth。

阶段 4 的核心 claim 是 downstream repair utility：
Predicted mask repair 是否在同一 repair backend 和同一 candidate budget 下优于 random mask repair。

阶段 4 先做 backend feasibility audit：
优先用 oracle mask 测 DiffDec / DiffSBDD inpainting / rule-only / full resampling 后端能否运行和通过 verifier。

DiffDec / DiffSBDD plain backend 是 local constrained resampling，不是完整 feedback-guided denoising。

只有实现 clash penalty / hot region guidance 并改采样过程后，才能声称 H_clash 进入生成过程。
```

### 7.3 论文主张

```text
本文不声称无偏证明 locator accuracy；
本文评估一个 attribution-derived operational mask policy 是否能在下游局部修复中优于 random mask，并接近 oracle mask。

本文不声称不用采样；
本文主张把采样从 blind full-ligand resampling 收窄到 failure-localized constrained resampling，并通过 verifier 判断可靠修复。
```

---

## 8. 建议新的阶段 3 产物

建议 docs 中统一阶段 3 产物为：

```text
reports/phase3_label_provenance_audit/
  phase2_label_provenance_audit.md
  circularity_risk_audit.md
  construction_consistency_report.csv
  locator_stress_report_s0.csv
  locator_stress_report_s1.csv
  phase4_mask_seed.csv
  summary.json
  phase3_completion_audit.md
```

### 8.1 `phase4_mask_seed.csv` 建议字段

```text
case_id
base_sample_id
target_rgroup
predicted_dominant_valid_rgroup
top_valid_rgroups_json
random_rgroup_size_matched
oracle_mask_atoms
predicted_mask_atoms
random_mask_atoms
keep_mask_atoms_oracle
keep_mask_atoms_predicted
anchor_atoms_oracle
anchor_atoms_predicted
target_score_ratio_valid
dominant_ratio_valid_rgroups
dominant_ratio_all_regions
failure_type
recommended_action
circularity_risk_level
phase4_main_candidate
phase4_candidate_reason
```

---

## 9. 建议新的阶段 4 产物

### 9.1 阶段 4.0

```text
reports/phase4_0_backend_feasibility/
  backend_feasibility_summary.json
  backend_feasibility_cases.csv
  backend_candidate_manifest.csv
  verifier_outcome.csv
  blocked_backends.md
  phase4_0_completion_audit.md

runs/phase4_0_backend_feasibility/
  diffdec/
  diffsbdd_inpainting/
  rule_only/
  full_resampling/
  logs/
```

### 9.2 阶段 4.1

```text
reports/phase4_local_repair_loop/
  summary.json
  repair_candidate_manifest.csv
  repair_outcome.csv
  verifier_report.csv
  baseline_comparison.csv
  locality_metrics.csv
  failure_cases.csv
  phase4_completion_audit.md

runs/phase4_local_repair_loop/
  raw_candidates/
  standardized_candidates/
  logs/
```

---

## 10. 给本地 Codex 的修改要求

Codex 应执行以下流程。

### 10.1 先核查仓库状态

```bash
git status
git branch --show-current
git rev-parse HEAD
```

如果工作区不干净，先记录，不要自行覆盖。

### 10.2 核查 docs 文件

优先检查：

```text
docs/20260504-03-Clash2Feedback-GC_总体实验递进路线.md
docs/20260504-02-Clash2Feedback-GC_第一篇论文实验方案.md
docs/20260510-Clash2Feedback-GC_阶段2人工局部碰撞注入最终落地方案.md
docs/20260504-01-Clash2Feedback-GC_完整方案与升级路线.md
docs/20260511-Clash2Feedback-GC_阶段2.5模型诱导失败外部有效性审计落地方案.md
docs/external_baselines.md
README.md
```

如果存在阶段 4 方案文档，也要检查：

```text
docs/*阶段4*
```

### 10.3 核查阶段 2 代码事实

重点核查：

```text
scripts/phase2_inject_artificial_clashes.py
src/clash2feedback/perturb/labels.py
src/clash2feedback/geometry/rgroup_attribution.py
configs/phase2_injection.yaml
reports/phase2_injection/phase2_final_report.md
```

核查点：

```text
target_rgroup 是否来自人工扰动；
supported_single_rgroup 是否依赖 target_score_ratio_valid；
target_score_ratio_valid 是否来自 attribution；
predicted_dominant_valid_rgroup 是否直接参与 acceptance；
当前 docs 是否把 supported_single_rgroup 误写成 independent locator benchmark。
```

### 10.4 修改 docs

按本文建议修改 docs，不要修改历史实验结果。

禁止修改：

```text
reports/phase2_injection/*.csv
reports/phase2_injection/*.json
reports/phase2_5_model_induced_audit/*.csv
reports/phase2_5_model_induced_audit/*.json
reports/phase2_5_model_induced_audit/*.parquet
data/benchmarks/clashrepairbench_rg_artificial/v0_1/
```

本任务只调整文档口径，不跑新实验。

### 10.5 输出总结

修改后生成：

```text
tmp/20260512/docs_update_summary_phase3_phase4_new_position.md
```

总结：

```text
修改了哪些 docs；
每个文件改了什么；
哪些旧表述被删除；
哪些新口径被加入；
哪些内容因仓库事实不明而保留为待核查项；
是否未修改任何历史实验结果。
```

---

## 11. 完成标准

这次 docs 更新完成后，应满足：

```text
[ ] docs 不再把阶段 3 写成 independent locator benchmark；
[ ] docs 明确 supported_single_rgroup 的循环验证风险；
[ ] docs 明确 target_rgroup 与 supported_single_rgroup 的区别；
[ ] docs 明确阶段 3 的新目标是 label provenance audit + circularity risk audit + phase4 mask seed generation；
[ ] docs 明确阶段 4 predicted mask 是 operational mask policy；
[ ] docs 明确阶段 4 的裁判是 verifier，而不是 locator；
[ ] docs 明确阶段 4 先做 backend feasibility audit；
[ ] docs 明确 DiffDec / DiffSBDD plain backend 不等于 full feedback-guided denoising；
[ ] docs 不再声称我们不是采样方法；
[ ] docs 不再声称 DiffSBDD de novo failures 主要是 single-Rgroup clash；
[ ] 不修改任何历史实验结果；
[ ] 生成 docs_update_summary。
```

---

## 12. 最终建议

本次 docs 修改的核心不是重写整个项目，而是纠正一个非常关键的实验逻辑问题：

```text
阶段 3 不能在由同一套 attribution gate 构造出来的 supported_single_rgroup 主集上，
再用同一套 attribution 方法声称独立 locator accuracy。
```

因此，阶段 3 保留，但功能改成：

```text
讲清阶段 2 标签怎么来；
讲清循环验证风险；
冻结现有 locator 作为 operational mask policy；
生成阶段 4 的 oracle / predicted / random masks。
```

真正证明方法价值的实验，应放到阶段 4：

```text
在同一修复后端、同一候选预算、同一 verifier 下，
Predicted mask repair 是否优于 Random mask repair，
并接近 Oracle mask repair。
```

一句话：

> **阶段 3 负责“把标签和 mask 讲清楚”，阶段 4 负责“证明这个 mask 对修复有没有用”。**
