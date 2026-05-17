# Clash2Feedback-GC 阶段 4.0.1a：局部接回诊断规则校准方案总纲

> 建议放置路径：`docs/20260517-Clash2Feedback-GC_阶段4.0.1a局部接回诊断规则校准方案总纲.md`  
> 阶段短名：`phase4-0-1a-local-reconnect-calibration`  
> 文档定位：阶段 4.0.1a 的方案总纲 / 上位约束  
> 重要说明：网页 ChatGPT 只负责生成方案文档和本地 Codex 交接材料，未在本地执行命令、未跑实验、未修改仓库。凡涉及真实路径、字段、样本数、候选数、提交号、测试结果和实验结论，均以后续本地 Codex 在真实仓库中的核查结果为准。若本文档与仓库事实冲突，必须先生成冲突报告，不得继续执行冲突部分。

---

## 0. 一句话定位

阶段 4.0.1a 是一个 **report-only / audit-only 的局部接回诊断规则校准阶段**。

本阶段不继续优化 DiffSBDD，不重跑 DiffSBDD，不重新生成候选，也不修改阶段 4.0.1 的 reliable repair 结论。它只回答一个问题：

```text
local_reconnect_check 这套“局部片段是否正确接回 scaffold anchor”的诊断规则，是否适合当前 single-anchor R-group repair 任务？
```

本阶段的核心产出不是新的生成候选，而是把阶段 4.0.1 中的 `local_reconnect_pass = 0` 进一步拆解成更合理、更可解释的三类结果：

```text
single_anchor_reconnect_pass
multi_attachment_out_of_scope
invalid_reconnect
```

其中：

- `single_anchor_reconnect_pass`：符合当前 single-anchor R-group 局部修复任务。
- `multi_attachment_out_of_scope`：可能化学上合理，但超出当前 single-anchor R-group repair 任务范围。
- `invalid_reconnect`：明显连接失败或候选失败，例如未接回 anchor、游离片段、候选不可读、分子基础合法性失败、固定结构映射失败等。

---

## 1. 动机

### 1.1 阶段 4.0.1 已经回答了什么

阶段 4.0.1 已完成 DiffSBDD conditional 在 reference mask、`center=pocket`、`K=8/16/32` 条件下的预算曲线与失败漏斗分析。

阶段 4.0.1 的 closeout audit 进一步核查了 `diffsbdd_anchor_reconnect_audit.csv` 的完整性，并确认 `local_reconnect_pass_count=0` 可以追溯到候选级诊断字段。该结论以后续本地 Codex 对当前仓库文件的核查为准。

阶段 4.0.1 的核心边界是：

```text
local_reconnect_pass=0 是新增候选级诊断结果；
它不替代阶段 4.0 reliable repair 10 项标准；
它不能反向推翻已经按 10 项标准判定的 reliable candidates。
```

### 1.2 为什么还需要阶段 4.0.1a

虽然阶段 4.0.1 已经确认 `local_reconnect_pass=0` 可追溯，但仍需要回答一个更细的问题：

```text
local_reconnect_check 这把“尺子”本身是否合理？
```

如果这套检查规则过严，它可能会把正常的 single-anchor 候选误判为失败。反过来，如果它能正确放行正常 single-anchor 样本、拦住明显断开或游离片段，并把 multi-attachment 单独标为 out-of-scope，那么后续才能更有把握地说：

```text
DiffSBDD conditional 的局部接回问题是真实瓶颈，
而不是连接检查器本身造成的误判。
```

### 1.3 为什么不能把 multi-attachment 简单写成 invalid

当前第一版任务处理的是 `single-anchor R-group repair`。也就是：

```text
scaffold — R-group
```

理想修复后仍应是：

```text
scaffold — new R-group
```

如果新片段接到了多个 keep atoms 或 scaffold 其他位置，它可能形成 linker、桥接结构、环化结构或多锚点片段。这些结构在药物化学上不一定错误，但它们已经超出当前 single-anchor R-group repair 的任务范围。

因此，本阶段明确采用以下口径：

```text
multi-attachment 不等于 ligand invalid；
multi-attachment 表示 out of current single-anchor R-group repair scope；
它不计入当前 reliable local repair 成功，但应作为后续 multi-anchor / linker repair 的潜在扩展方向单独统计。
```

---

## 2. 本阶段最终目标

阶段 4.0.1a 的最终目标是：

> 校准并解释 `local_reconnect_check` 在当前 single-anchor R-group 局部修复任务中的适用性，明确它能否作为后续候选筛选或加严诊断依据。

具体目标包括：

```text
1. 读取阶段 4.0.1 已有候选级诊断表，不重跑 DiffSBDD；
2. 核查 local_reconnect_pass=0 的候选级来源；
3. 将原有二分类 local_reconnect_pass 拆成三分类；
4. 用正样本和负样本校准连接诊断规则；
5. 单独统计 multi-attachment，并标为 out_of_scope，而不是 invalid；
6. 同步记录候选基础合法性、旧碰撞消除、新碰撞、scaffold/keep 稳定性等已有 verifier 字段；
7. 判断 local_reconnect_check 是否适合后续作为硬筛选项、软筛选项，还是仅作为诊断项；
8. 输出阶段 4.0.1a 临时实验汇报文档，为后续 4.0.2 DiffDec adapter 和 4.1-mini 设计提供依据。
```

---

## 3. 明确成功标准

### 3.1 最低成功标准

满足以下条件，即可认为阶段 4.0.1a 有价值：

```text
1. 不重跑 DiffSBDD；
2. 不重新生成候选；
3. 不修改阶段 4.0.1 原始候选表、验证表和预算曲线；
4. 成功读取阶段 4.0.1 的 anchor reconnect audit、verifier outcome 和 candidate manifest；
5. 输出三分类 reconnect 结果；
6. 能解释原 local_reconnect_pass=false 记录中有多少属于 multi_attachment_out_of_scope，有多少属于 invalid_reconnect；
7. 对 clean / rule 正样本与 synthetic negative 进行最小校准；
8. 输出 calibration summary 和 expt-report；
9. compileall 和相关测试通过，或如实说明无法运行原因。
```

### 3.2 推荐成功标准

推荐目标是：

```text
1. clean original ligand 或等价正样本中，single-anchor reconnect 大部分通过；
2. rule_fixed_topology reliable candidates 中，single-anchor reconnect 大部分通过；
3. synthetic disconnected / floating / extra-attachment negative cases 能被正确识别；
4. DiffSBDD 候选能被分成 single-anchor pass、multi-attachment out-of-scope、invalid reconnect 三类；
5. 对 DiffSBDD reliable candidates 给出 reconnect 分层解释，而不是只报告 local_reconnect_pass=0；
6. 明确 local_reconnect_check 后续是否可作为硬筛选、软筛选或诊断字段。
```

### 3.3 强成功标准

若达到以下结果，可以认为连接诊断规则已经较可信：

```text
1. clean / rule 正样本通过率高；
2. synthetic negative 失败原因与预期一致；
3. 失败原因分布与人工或结构审计一致；
4. multi-attachment 能被单独分离，不再混入 invalid；
5. 结果能直接指导后续 DiffSBDD filtering、DiffDec adapter 预检和 4.1-mini 的 verifier 设计。
```

### 3.4 失败判据

如果出现以下情况，则阶段 4.0.1a 应关闭为“诊断规则待修”结果：

```text
1. clean original ligand 大量不能通过 single-anchor reconnect；
2. rule_fixed_topology reliable candidates 大量不能通过 single-anchor reconnect；
3. synthetic disconnected / floating / extra-attachment negative cases 不能被稳定识别；
4. 候选级 mapping 不稳定，导致三分类不可解释；
5. local reconnect 结果与人工结构审计明显冲突。
```

失败时的结论应写成：

```text
local_reconnect_check 当前不适合作为硬筛选项，只能作为待校准诊断字段；
后续应先修 reconnect/mapping 诊断逻辑，再讨论是否加严 reliable repair 标准。
```

---

## 4. 阶段边界

### 4.1 本阶段做什么

阶段 4.0.1a 做：

```text
1. 读取阶段 4.0.1 的候选级诊断表；
2. 读取阶段 4.0.1 的 verifier outcome 和 candidate manifest；
3. 读取阶段 4.0.1 closeout audit 和 completion audit；
4. 读取阶段 4.0 中 rule_fixed_topology 的候选和 verifier 结果，用作正样本来源；
5. 读取必要的原始 clean/failed ligand，用于正样本或 synthetic negative 构造；
6. 将 local reconnect 结果从二分类升级为三分类审计；
7. 统计 single_anchor_reconnect_pass、multi_attachment_out_of_scope、invalid_reconnect；
8. 记录并汇总 candidate_readable、ligand_valid、fixed_structure_match_success、anchor_integrity、old_clash_resolved、no_new_severe_clash、scaffold_stable、keep_region_stable、edit_compliance、pocket_retention、reliable_repair_success 等已有字段；
9. 输出 calibration 表、summary 和临时实验报告。
```

### 4.2 本阶段不做什么

阶段 4.0.1a 不做：

```text
不重跑 DiffSBDD；
不重新生成候选；
不修改 DiffSBDD 外部源码；
不修改 DiffSBDD 原始 denoising loop；
不训练或微调任何模型；
不修改 reliable repair 10 项标准；
不把 local reconnect 加入 reliable repair 10 项标准；
不把 multi-attachment 写成 ligand invalid；
不覆盖阶段 4.0 或 4.0.1 历史结果；
不修改 phase4_mask_seed.csv；
不做 DiffDec adapter 修补；
不做 Random / Predicted / Oracle 正式对照；
不进入阶段 4.1；
不声称 H_clash 进入生成过程；
不新增 PoseBusters 等完整几何检查作为硬门槛。
```

---

## 5. 核心假设

### 5.1 可采用假设

阶段 4.0.1a 可以采用以下假设：

```text
1. 当前第一版主任务是 single-anchor R-group 局部修复；
2. 当前阶段只需要判断单锚点局部接回是否符合任务语义；
3. multi-attachment 可能化学上合理，但属于当前任务范围外；
4. local reconnect 应首先作为诊断和筛选字段，而不是直接替代 reliable repair 标准；
5. clean original ligand 和 rule_fixed_topology reliable candidates 可以作为校准正样本；
6. 人工构造 disconnected / floating / extra-attachment 样本可以作为校准负样本；
7. 4.0.1a 的目标是校准诊断规则，不是提高生成成功率。
```

### 5.2 不允许采用假设

阶段 4.0.1a 不允许采用以下假设：

```text
1. multi-attachment 一定化学非法；
2. local_reconnect_pass=0 直接推翻所有 reliable candidates；
3. local reconnect 已经可以直接加入 reliable repair 10 项标准；
4. DiffSBDD 候选 reconnect 失败就说明整个生成式路线失败；
5. clean / rule 未校准前，local reconnect 可以作为硬筛选标准；
6. 本阶段能证明 predicted mask 有下游修复价值；
7. 本阶段能替代阶段 4.1；
8. 本阶段可以修改历史实验结果来适配新口径。
```

---

## 6. 事实依据与结果来源

### 6.1 已有事实来源

本阶段依赖以下已有项目口径，但所有事实必须由本地 Codex 核查：

```text
1. 阶段 2 和阶段 3 文档明确当前第一版任务聚焦 single-anchor R-group；
2. 阶段 4.0 使用 reference mask 做后端可行性审计，不证明 predicted mask 下游价值；
3. 阶段 4.0 reliable repair 使用 10 项标准；
4. 阶段 4.0.1 closeout audit 已检查 anchor reconnect 诊断表完整性；
5. 阶段 4.0.1 completion audit 已记录 local reconnect 是新增诊断/筛选项，不替代 reliable repair 标准；
6. 阶段 4.0.1 的候选、verifier、anchor reconnect audit 表可作为本阶段主要输入。
```

### 6.2 本地 Codex 必须核查的文件

Codex 必须核查以下文件是否存在、字段是否齐全、内容是否可读取：

```text
reports/phase4_0_1_diffsbdd_conditional_repair/phase4_0_1_summary.json
reports/phase4_0_1_diffsbdd_conditional_repair/diffsbdd_anchor_reconnect_audit.csv
reports/phase4_0_1_diffsbdd_conditional_repair/diffsbdd_verifier_outcome.csv
reports/phase4_0_1_diffsbdd_conditional_repair/diffsbdd_candidate_manifest.csv
reports/phase4_0_1_diffsbdd_conditional_repair/diffsbdd_budget_curve.csv
reports/phase4_0_1_diffsbdd_conditional_repair/phase4_0_1_closeout_audit.md
reports/phase4_0_1_diffsbdd_conditional_repair/phase4_0_1_completion_audit.md

reports/phase4_0_backend_feasibility/verifier_outcome.csv
reports/phase4_0_backend_feasibility/candidate_manifest.csv
reports/phase4_0_backend_feasibility/backend_comparison.csv
reports/phase4_0_backend_feasibility/phase4_0_final_experiment_report.md

src/clash2feedback/repair/fragment_diagnostics.py
src/clash2feedback/repair/diffsbdd_anchor_filter.py
src/clash2feedback/repair/reconnect_check.py
src/clash2feedback/verifier/phase4_adapter.py
src/clash2feedback/verifier/repair_verifier.py
configs/phase4_0_1_diffsbdd_conditional_repair.yaml
```

如果真实路径或文件名与方案不同，Codex 必须在 `/plan` 中提出字段和路径映射，不得自行编造。

### 6.3 本地 Codex 必须核查的字段

至少核查以下字段是否存在或可从等价字段恢复：

```text
case_id
base_sample_id
candidate_id
candidate_path
candidate_budget_k
backend_name
candidate_readable
ligand_valid
fixed_structure_match_success
anchor_integrity
local_reconnect_pass
local_reconnect_failure_reason
anchor_reconnect_status
anchor_reconnect_reason
anchor_match_success
generated_fragment_connected_to_anchor
generated_fragment_attachment_count
num_anchor_neighbors
num_extra_attachments
floating_fragment_detected
candidate_single_fragment
candidate_total_fragment_count
target_mask_heavy_atom_count
generated_fragment_heavy_atom_count
generated_fragment_size_diff
generated_element_mismatch_count
old_clash_resolved
no_new_severe_clash
scaffold_stable
keep_region_stable
edit_compliance
pocket_retention
reliable_repair_success
```

若字段缺失，但可由现有字段无歧义计算，Codex 应在计划中说明计算方式。若字段缺失且不可恢复，应生成 conflict report 或 blocked 项。

---

## 7. 具体原理和做法

### 7.1 原有 local reconnect 的含义

当前 local reconnect 诊断本质上是在检查：

```text
DiffSBDD 生成的新局部片段是否按当前任务语义接回原 scaffold anchor。
```

原有二分类大致为：

```text
local_reconnect_pass = true / false
```

它容易把不同类型的失败混在一起：

```text
未接回 anchor；
游离片段；
额外连接；
候选不可读；
固定结构映射失败；
多连接但可能化学合理、只是超出当前任务。
```

因此本阶段将其拆成三分类。

### 7.2 三分类定义

#### 7.2.1 `single_anchor_reconnect_pass`

候选满足当前 single-anchor R-group repair 任务语义：

```text
anchor_candidate_idx 存在；
generated fragment 非空；
generated fragment 连接到指定 anchor；
anchor 附近只有 1 个 generated neighbor；
没有额外连接到其他 keep atoms；
没有 floating fragment；
候选基础可读；
固定结构映射成功。
```

#### 7.2.2 `multi_attachment_out_of_scope`

候选可能化学上不一定错误，但超出当前任务范围：

```text
候选基础可读；
固定结构可映射；
generated fragment 与 keep region 存在多个 attachment；
或出现接到非指定 keep atom 的额外连接；
该现象更接近 linker / bridge / ring closure / multi-anchor fragment；
不计入当前 single-anchor reliable local repair 成功；
不标记为 ligand invalid。
```

#### 7.2.3 `invalid_reconnect`

候选明确不满足接回要求或候选失败：

```text
候选不可读；
基础分子合法性失败；
固定结构映射失败；
anchor 不可映射；
generated fragment 为空；
未连接到 anchor；
出现 floating fragment；
其他无法解释为 multi-attachment out-of-scope 的连接失败。
```

### 7.3 推荐分类优先级

分类时建议采用如下优先级，避免同一候选被重复归类：

```text
1. 如果 candidate_readable=false 或候选路径缺失：invalid_reconnect；
2. 如果 ligand_valid=false：invalid_reconnect，但需保留 ligand_valid=false 作为原因；
3. 如果 fixed_structure_mapping_success_for_diagnostics=false 或 fixed_structure_match_success=false：invalid_reconnect；
4. 如果 anchor_match_success=false：invalid_reconnect；
5. 如果 floating_fragment_detected=true：invalid_reconnect；
6. 如果 generated_fragment_connected_to_anchor=false：invalid_reconnect；
7. 如果 num_extra_attachments > 0 或 generated_fragment_attachment_count > 1：multi_attachment_out_of_scope；
8. 如果 num_anchor_neighbors == 1 且 num_extra_attachments == 0 且 no floating fragment：single_anchor_reconnect_pass；
9. 其他情况：invalid_reconnect，并记录 reconnect_category_reason。
```

上述优先级需由本地 Codex 根据真实字段校准。如果真实字段语义不同，应在 `/plan` 中提出调整。

### 7.4 正样本校准

正样本用于确认检查器不会误伤正常单锚点结构。

建议来源：

```text
1. original clean ligand 或 failed ligand 中未被改变的原始 single-anchor R-group 结构；
2. phase4_0_backend_feasibility 中 rule_fixed_topology 的 reliable candidates；
3. 若字段允许，可选择阶段 4.0.1 中 fixed_structure_match_success=true 且 anchor_integrity=true 的候选作为观察组，但不作为规则正确性的唯一正样本。
```

正样本预期：

```text
clean / rule 正样本大多数应为 single_anchor_reconnect_pass。
```

如果 clean / rule 大量不通过，应优先怀疑 reconnect 检查或 mapping 口径。

### 7.5 负样本校准

负样本用于确认检查器能拦住明显错误结构。

建议最小构造：

```text
1. disconnected negative：删除 anchor bond 或构造未接回 anchor 的片段；
2. floating negative：添加或保留一个不连接 scaffold 的游离片段；
3. extra-attachment negative：构造一个额外连接到其他 keep atom 的片段；
4. missing-anchor negative：让 anchor 映射失败或移除 anchor 关联信息；
5. unreadable / invalid negative：如本地已有候选读入失败记录，可直接复用，不必人为构造。
```

负样本预期：

```text
disconnected / floating / missing-anchor 应进入 invalid_reconnect；
extra-attachment 应进入 multi_attachment_out_of_scope；
不可读或 ligand invalid 应进入 invalid_reconnect。
```

### 7.6 DiffSBDD 候选重分类

对阶段 4.0.1 中所有 DiffSBDD candidates 做三分类：

```text
single_anchor_reconnect_pass
multi_attachment_out_of_scope
invalid_reconnect
```

并按以下维度汇总：

```text
candidate_budget_k
case_id
reliable_repair_success
old_clash_resolved
no_new_severe_clash
anchor_integrity
ligand_valid
failure_reason / reconnect_category_reason
```

重点分析：

```text
1. 原 local_reconnect_pass=false 的候选中，有多少是 multi_attachment_out_of_scope；
2. 原 reliable candidates 中，有多少属于 multi_attachment_out_of_scope 或 invalid_reconnect；
3. old_clash_resolved=true 的候选中，reconnect category 如何分布；
4. no_new_severe_clash=true 的候选中，reconnect category 如何分布；
5. K=8/16/32 是否改变 reconnect category 分布。
```

### 7.7 不改变 reliable repair 10 项标准

本阶段必须明确：

```text
三分类结果是新增诊断；
不修改 reliable_repair_success；
不重算阶段 4.0.1 budget curve；
不反向删除阶段 4.0.1 的 reliable candidates；
只在报告中给出“若将 strict single-anchor reconnect 作为后续硬门槛，会产生什么影响”的 shadow analysis。
```

### 7.8 可选 shadow analysis

可以额外输出 shadow 分析，但不得修改历史结果：

```text
strict_single_anchor_reliable = reliable_repair_success AND reconnect_category == single_anchor_reconnect_pass
```

该字段只用于观察，不作为阶段 4.0.1 正式指标。

---

## 8. 输入与输出

### 8.1 输入目录

主要输入目录：

```text
reports/phase4_0_1_diffsbdd_conditional_repair/
reports/phase4_0_backend_feasibility/
```

必要时读取运行目录，但不提交重资产文件：

```text
runs/phase4_0_1_diffsbdd_conditional_repair/
runs/phase4_0_backend_feasibility/
```

是否需要读取 `runs/` 由本地 Codex 根据现有 report 是否足够决定，并在 `/plan` 中说明。

### 8.2 输出目录

本阶段新增结果建议写入：

```text
reports/phase4_0_1a_local_reconnect_calibration/
```

不得覆盖阶段 4.0 或 4.0.1 历史目录中的主结果表。

### 8.3 建议输出文件

```text
reports/phase4_0_1a_local_reconnect_calibration/
  local_reconnect_calibration_summary.json
  local_reconnect_calibration_cases.csv
  local_reconnect_category_counts.csv
  diffsbdd_reconnect_reclassified.csv
  rule_positive_reconnect_check.csv
  clean_positive_reconnect_check.csv
  synthetic_negative_reconnect_check.csv
  reconnect_shadow_reliable_analysis.csv
  phase4_0_1a_completion_audit.md
```

临时实验汇报文档：

```text
tmp/20260517/phase4-0-1a-local-reconnect-calibration-expt-report.md
```

### 8.4 建议 summary 字段

```json
{
  "schema_version": "phase4_0_1a_local_reconnect_calibration_v0_1",
  "mode": "report_only_audit_only",
  "rerun_diffsbdd": false,
  "regenerate_candidates": false,
  "modify_reliable_repair_fields": false,
  "classification_labels": [
    "single_anchor_reconnect_pass",
    "multi_attachment_out_of_scope",
    "invalid_reconnect"
  ],
  "num_diffsbdd_candidates_reclassified": null,
  "num_clean_positive_cases": null,
  "num_rule_positive_cases": null,
  "num_synthetic_negative_cases": null,
  "single_anchor_pass_count": null,
  "multi_attachment_out_of_scope_count": null,
  "invalid_reconnect_count": null,
  "strict_single_anchor_shadow_reliable_count": null,
  "recommended_use_of_local_reconnect": "diagnostic_only|soft_filter|hard_filter_candidate|blocked_pending_calibration"
}
```

---

## 9. 预期产物

阶段 4.0.1a 完成后，应能给出以下判断：

```text
1. local_reconnect_check 是否误伤 clean / rule 正样本；
2. multi-attachment 在 DiffSBDD 候选中占比多少；
3. multi-attachment 是否应作为 out-of-scope 单独统计；
4. DiffSBDD reliable candidates 在 reconnect category 上如何分布；
5. local reconnect 后续应作为诊断、软筛选，还是有条件加严的硬筛选候选；
6. 是否需要修 reconnect/mapping 代码；
7. 是否需要为 multi-anchor / linker repair 单独开后续方向。
```

---

## 10. 执行硬约束

阶段 4.0.1a 必须遵守：

```text
1. 不重跑 DiffSBDD；
2. 不重新生成候选；
3. 不训练或微调模型；
4. 不修改 DiffSBDD 外部源码；
5. 不修改 DiffSBDD 原始 denoising loop；
6. 不修改 reliable repair 10 项标准；
7. 不把 local reconnect 加入 reliable repair 10 项标准；
8. 不把 multi-attachment 写成 ligand invalid；
9. 不覆盖阶段 4.0 或阶段 4.0.1 历史主结果；
10. 不修改 phase4_mask_seed.csv；
11. 不做 DiffDec adapter 修补；
12. 不做 Random / Predicted / Oracle 正式对照；
13. 不声称 H_clash 进入生成过程；
14. 不提交 runs 下重资产候选 SDF 或日志；
15. 如发现方案与仓库事实冲突，先生成 conflict report，不继续执行冲突部分。
```

---

## 11. 禁止修改范围

本地 Codex 执行时，禁止修改以下历史结果和数据：

```text
reports/phase2_injection/
reports/phase2_5_model_induced_audit/
reports/phase3_label_provenance_audit/phase4_mask_seed.csv
reports/phase3_label_provenance_audit/summary.json
reports/phase3_label_provenance_audit/phase3_final_experiment_report.md

reports/phase4_0_backend_feasibility/phase4_0_final_experiment_report.md
reports/phase4_0_backend_feasibility/backend_comparison.csv
reports/phase4_0_backend_feasibility/backend_comparison_rates.csv
reports/phase4_0_backend_feasibility/candidate_manifest.csv
reports/phase4_0_backend_feasibility/verifier_outcome.csv
reports/phase4_0_backend_feasibility/phase4_0_small_scale_summary.json

reports/phase4_0_1_diffsbdd_conditional_repair/phase4_0_1_summary.json
reports/phase4_0_1_diffsbdd_conditional_repair/diffsbdd_budget_curve.csv
reports/phase4_0_1_diffsbdd_conditional_repair/diffsbdd_failure_funnel.csv
reports/phase4_0_1_diffsbdd_conditional_repair/diffsbdd_verifier_outcome.csv
reports/phase4_0_1_diffsbdd_conditional_repair/diffsbdd_candidate_manifest.csv
reports/phase4_0_1_diffsbdd_conditional_repair/diffsbdd_anchor_reconnect_audit.csv

data/benchmarks/clashrepairbench_rg_artificial/v0_1/
external/DiffSBDD/
external/DiffDec/
runs/
```

允许读取上述文件；不得回写、重命名、覆盖或重生成。

允许新增范围建议为：

```text
docs/20260517-Clash2Feedback-GC_阶段4.0.1a局部接回诊断规则校准方案总纲.md
configs/phase4_0_1a_local_reconnect_calibration.yaml
scripts/phase4_0_1a_local_reconnect_calibration.py
src/clash2feedback/repair/reconnect_calibration.py
tests/test_phase4_0_1a_local_reconnect_calibration.py
reports/phase4_0_1a_local_reconnect_calibration/
tmp/20260517/
```

实际新增和修改文件以本地 Codex `/plan` 结合仓库事实提出为准。

---

## 12. 风险与局限

| 风险 | 说明 | 处理 |
|---|---|---|
| 正样本也大量失败 | 说明 reconnect check 或 mapping 过严 | 不把 local reconnect 作为硬筛选，先修诊断逻辑 |
| multi-attachment 占比很高 | 说明 DiffSBDD 候选常超出 single-anchor 任务范围 | 单独报告 out-of-scope，不写成 invalid |
| synthetic negative 构造不真实 | 可能导致校准结论过强 | 只作为最小单元测试，不作为论文主证据 |
| 缺少 clean / rule 正样本路径 | 无法直接运行候选结构检查 | Codex 在 plan 中提出替代字段或阻塞项 |
| 结果与原 reliable candidates 冲突 | reconnect 诊断比原标准更严 | 保持原 reliable 标准不变，只做 shadow analysis |
| 用户误读为“多连接都错” | multi-attachment 口径不清 | 明确写为 out-of-scope，而非 invalid |
| 过度扩展到 multi-anchor repair | 任务变大 | 保持本阶段只校准 single-anchor，multi-anchor 作为后续方向 |

---

## 13. 完成标准 checklist

阶段 4.0.1a 完成时，应满足：

```text
[ ] 已核查 git status、当前分支和 HEAD；
[ ] 已读取本方案文档；
[ ] 已核查阶段 4.0.1 主要报告和候选级表；
[ ] 已核查阶段 4.0 rule_fixed_topology 可作为正样本来源的文件；
[ ] 已确认不重跑 DiffSBDD；
[ ] 已确认不重新生成候选；
[ ] 已定义 reconnect 三分类规则；
[ ] 已输出 DiffSBDD 候选三分类结果；
[ ] 已输出 clean / rule 正样本校准结果，或清楚说明阻塞原因；
[ ] 已输出 synthetic negative 校准结果，或清楚说明阻塞原因；
[ ] 已输出 multi_attachment_out_of_scope 单独统计；
[ ] 已输出 shadow reliable analysis；
[ ] 已明确 local reconnect 后续使用建议；
[ ] 未修改禁止修改范围内的历史结果；
[ ] 已生成 phase4_0_1a_completion_audit.md；
[ ] 已生成 tmp/20260517/phase4-0-1a-local-reconnect-calibration-expt-report.md；
[ ] compileall 通过；
[ ] pytest 通过或说明无法运行原因。
```

---

## 14. 阶段结束后的决策

### 情况 A：连接规则通过校准

如果 clean / rule 正样本大多通过，synthetic negative 能被正确识别，则：

```text
local_reconnect_check 可作为后续软筛选或加严候选标准；
DiffSBDD conditional 的 reconnect 瓶颈更可信；
后续 4.0.2 DiffDec adapter 应重点关注是否能产生 single-anchor reconnect pass 候选。
```

### 情况 B：连接规则过严或 mapping 不稳定

如果 clean / rule 正样本大量失败，则：

```text
local_reconnect_check 暂不应作为硬筛选；
需要优先修 reconnect/mapping 诊断逻辑；
阶段 4.0.1 中 local_reconnect_pass=0 只能作为未完全校准的诊断观察。
```

### 情况 C：multi-attachment 占比很高

如果多连接候选占比很高，则：

```text
当前 DiffSBDD conditional 常生成超出 single-anchor repair 范围的候选；
这些候选不能计入当前 reliable local repair 成功；
但可以作为后续 multi-anchor / linker repair 方向的现象证据。
```

---

## 15. 本地 Codex 后续计划要求

本文件不替代本地 Codex 执行计划。本地 Codex 必须先进入 `/plan` 模式，只规划不执行。

计划文件必须生成到：

```text
tmp/20260517/phase4-0-1a-local-reconnect-calibration-codex-goal-exec-plan.md
```

执行计划必须包含：

```text
1. 仓库事实核查；
2. 字段 / 实现映射；
3. 具体执行步骤；
4. 预计新增和修改文件；
5. 测试计划；
6. 禁止修改范围核查方式；
7. 冲突项；
8. 阻塞项；
9. 后续 /goal 执行建议；
10. 若有拿不准的实验口径或用户决策点，必须列出并询问用户。
```

如发现方案文档与仓库事实冲突，必须先生成：

```text
tmp/20260517/phase4-0-1a-local-reconnect-calibration-conflict-report.md
```

冲突报告必须包含：

```text
冲突项；
方案文档表述；
仓库实际情况；
涉及文件；
影响范围；
建议处理方式；
是否需要人工确认。
```

低风险字段 / 路径差异可在 plan 中提出适配；高风险实验口径或历史结果差异必须等待人工确认。
