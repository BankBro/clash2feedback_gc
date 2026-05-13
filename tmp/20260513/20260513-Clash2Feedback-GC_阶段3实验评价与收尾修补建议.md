# Clash2Feedback-GC 阶段 3 实验评价与收尾修补建议

> 建议放置路径：`tmp/20260513/20260513-Clash2Feedback-GC_阶段3实验评价与收尾修补建议.md`  
> 面向对象：本地 Codex  
> 文档定位：对阶段 3 结果的外部评价、结论边界说明和进入阶段 4 前的收尾修补建议。  
> 注意：本文不是新的实验方案，也不是最终实验报告正文。若本文与本地仓库真实文件冲突，以本地仓库事实为准。

---

## 1. 总体评价

阶段 3 整体评价为：**通过，可以进入阶段 4.0**。

本次阶段 3 已经完成它在新口径下应承担的职责：

```text
标签溯源审计
+ 循环验证风险审计
+ 构造一致性检查
+ 阶段 4 掩码种子生成
```

阶段 3 不训练模型、不调用生成器、不修复分子，这一点当前结果和 completion audit 中的描述一致。阶段 3 的核心交付物 `reports/phase3_label_provenance_audit/phase4_mask_seed.csv` 已生成，并且可以作为阶段 4.0 / 阶段 4.1 的输入基础。

因此，阶段 3 不需要再做大规模返工，也不建议继续围绕“定位器准确率”方向补实验。后续重点应转向阶段 4：先验证给定正确修复区域时后端能不能修，再验证 Random / Predicted / Oracle 三组掩码下的修复效果。

---

## 2. 当前阶段 3 结果摘要

请 Codex 以真实仓库文件为准复核以下结果。

当前根据远端提交中已读文件，阶段 3 结果大致为：

| 项目 | 当前结果 |
|---|---:|
| phase2 manifest rows | 2610 |
| S0_all_valid_injection_attempts | 1185 |
| S1_oracle_target_local_clash_set | 467 |
| S2_phase2_supported_single_rgroup | 357 |
| phase4_mask_seed rows | 357 |
| phase4_0_backend_feasibility_candidate | 357 |
| phase4_1_formal_loop_candidate | 357 |
| predicted_equals_oracle | 357 / 357 |
| random_equals_oracle | 0 / 357 |
| random_equals_predicted | 0 / 357 |
| construction consistency Top-1 | 357 / 357 = 1.0 |
| construction consistency Top-3 | 357 / 357 = 1.0 |
| phase2.5 rows included in denominator | false |

这些数字说明：

```text
1. 阶段 4 所需的三类掩码输入已经具备；
2. S2 主集上 predicted mask 与 oracle mask 完全一致；
3. random mask 没有退化成 oracle 或 predicted；
4. phase2.5 model-induced samples 没有混入阶段 3 构造一致性分母。
```

---

## 3. 可以支持的结论

阶段 3 当前结果可以支持以下结论：

### 3.1 阶段 3 已经完成阶段 4 输入准备

`phase4_mask_seed.csv` 已覆盖 357 个 S2 主集 case，并且包含 oracle / predicted / random 三类掩码、保留掩码、anchor、旧碰撞证据和阶段 4 候选标记。

可以写：

```text
阶段 3 已完成 phase2 supported_single_rgroup 主集的标签溯源、循环风险审计和阶段 4 掩码种子生成。
```

### 3.2 S2 主集具有高度构造一致性

S2 上 predicted 与 oracle 完全一致，Top-1 / Top-3 均为 1.0。这说明 phase2 supported 主集、attribution 记录和阶段 4 掩码构造逻辑内部一致。

可以写：

```text
在 attribution-aware clean local repair substrate 上，predicted mask policy 与人工扰动目标具有完全构造一致性。
```

### 3.3 random mask baseline 没有明显退化

当前 random mask 没有与 oracle / predicted 重合，说明 Random 组可以作为阶段 4.1 的负对照基础。

可以写：

```text
size-matched random mask 没有复用 oracle / predicted R 基，具备作为阶段 4 对照组的基本条件。
```

### 3.4 phase2.5 没有污染阶段 3 分母

phase2.5 model-induced samples 没有人工 `target_rgroup`，当前阶段 3 已排除它们，不进入 construction consistency denominator。

可以写：

```text
model-induced audit rows 仅用于外部有效性和分布差距讨论，不参与阶段 3 构造一致性分母。
```

---

## 4. 不能支持的结论

阶段 3 当前结果**不能**支持以下结论，后续报告、论文和文档中必须避免。

### 4.1 不能写成 independent locator accuracy

不能写：

```text
规则定位器在 357 个样本上取得 100% 独立定位准确率。
```

应该写：

```text
S2 主集上 Top-1 / Top-3 为 1.0，但该结果只能解释为 construction consistency check。
```

原因：S2 是经过 detector / attribution / target-dominance gates 过滤后的 clean local repair substrate，不是无偏定位 benchmark。

### 4.2 不能把 target_rgroup 写成无偏定位真值

不能写：

```text
target_rgroup 是无偏 locator ground truth。
```

应该写：

```text
target_rgroup 是人工扰动标签和阶段 4 oracle mask 来源。
```

### 4.3 不能把 predicted mask 写成 ground truth

不能写：

```text
predicted mask 是真实失败区域。
```

应该写：

```text
predicted mask 是 attribution-derived operational mask policy。
```

### 4.4 不能说阶段 3 已经证明修复有效

不能写：

```text
阶段 3 证明 Clash2Feedback-GC 能修复失败分子。
```

应该写：

```text
阶段 3 只准备阶段 4 的掩码种子和审计报告，修复能力需要阶段 4 验证。
```

---

## 5. 是否还有必须继续修补的点？

我的判断：**没有阻断阶段 4 的必须修补点。**

阶段 3 已达到进入阶段 4.0 的最低要求：

```text
1. S2 主输入已明确；
2. oracle / predicted / random 三类掩码均可用；
3. keep mask 和 anchor 均已记录；
4. old clash evidence 和 protein hot region 均已记录；
5. construction consistency 已生成；
6. circularity risk 已明确；
7. phase2.5 未混入分母；
8. 测试通过。
```

因此，不建议为了阶段 3 再继续追加复杂实验。

---

## 6. 建议做的轻量收尾修补

虽然没有阻断问题，但建议 Codex 在进入阶段 4 前做以下轻量核查或文档补充。

### 6.1 补充 random mask 公平性统计

当前只知道：

```text
random_equals_oracle = 0 / 357
random_equals_predicted = 0 / 357
```

但阶段 4 之前最好再补一个轻量统计，确认 random mask 大小是否公平。

建议新增或在后续阶段 4 preflight 中生成：

```text
reports/phase3_label_provenance_audit/random_mask_balance_summary.csv
```

建议字段：

```text
case_id
oracle_mask_size
predicted_mask_size
random_mask_size
abs_size_diff_random_vs_oracle
abs_size_diff_random_vs_predicted
random_mask_fallback_reason
injection_mode
difficulty_bin
base_split
```

如果不想新增阶段 3 输出，也可以把这项放到阶段 4.0 preflight 中做。

### 6.2 在阶段 3 completion audit 或后续最终报告中强调 predicted = oracle 的解释边界

当前 S2 上：

```text
predicted_equals_oracle = 357 / 357
```

这会导致阶段 4.1 中：

```text
Predicted mask repair 和 Oracle mask repair 的核心编辑掩码完全相同。
```

这不是错误，但必须在阶段 4 报告中提前解释：

```text
在 S2 clean substrate 上，Predicted 与 Oracle 组主要不是用来区分定位误差；阶段 4.1 的核心比较应是 Random vs Predicted/Oracle。
```

### 6.3 不建议为了更新 summary.json 的 git 字段而重跑阶段 3

阶段 3 `summary.json` 中的 git 信息可能记录的是生成时的本地状态，而非最终提交后的干净状态。这类信息可以在最终报告中说明为 generation-time metadata，不建议为了“让 summary.json 更好看”手动改历史结果文件。

如果确实需要刷新，应由 Codex 明确说明会重新运行阶段 3 脚本，且不得改变核心结果。未经确认，不要只手动 patch `summary.json`。

### 6.4 检查 docs / README 是否已经同步阶段 3 结果入口

如果 README、reports/README、configs/README、scripts/README、src/README 已经同步阶段 3 用法和输出，则不需要再改。若仍缺少阶段 3 运行命令或输出路径，可以做轻量补充。

---

## 7. 阶段 4 前必须牢记的实验口径

进入阶段 4 前，Codex 必须保持以下口径：

```text
阶段 4.0：Oracle mask backend feasibility audit
```

目的：

```text
先验证给正确区域时，repair backend 能不能修。
```

```text
阶段 4.1：Random / Predicted / Oracle formal repair loop
```

目的：

```text
同一后端、同一预算下，比较 random mask 与 predicted/oracle mask 的 downstream repair utility。
```

由于当前 S2 中 predicted 与 oracle 完全一致，所以阶段 4.1 的核心趋势应写成：

```text
Random mask repair < Predicted/Oracle mask repair
```

不要强行写成：

```text
Random < Predicted < Oracle
```

当前数据不支持 predicted 与 oracle 在 S2 上产生差距。

---

## 8. 阶段 4 最小可执行顺序建议

建议后续阶段 4 按以下顺序推进：

```text
1. 读取 phase4_mask_seed.csv，做字段 sanity check；
2. 先抽取 20–50 个 S2 case；
3. 优先运行 Oracle mask backend feasibility audit；
4. 检查 candidate generation success、ligand validity、anchor consistency、old clash resolved、no new severe clash、scaffold RMSD、non-mask RMSD；
5. 如果 Oracle mask 下后端可行，再做 Random / Predicted / Oracle 三组正式对照；
6. 如果 Oracle mask 都修不好，优先修 repair backend，不要责怪 mask policy；
7. 最后再扩展到 357 个 S2 case。
```

第一轮不建议直接上全量 357，也不建议一开始引入训练型 ranker、learned critic 或 learned adapter。

---

## 9. 给 Codex 的具体建议

Codex 下一步可以做两件事：

### 9.1 轻量核查阶段 3 是否需要 patch

核查：

```text
1. phase3 reports 是否齐全；
2. phase4_mask_seed.csv 是否为 357 行；
3. 三类 mask 是否均可用；
4. random mask 是否无 oracle / predicted 复用；
5. README / docs / reports README 是否已同步阶段 3 入口；
6. 是否需要新增 random_mask_balance_summary.csv。
```

若仅是文档说明不足，可以轻量补充文档。若涉及重跑脚本或改 summary，必须先报告风险。

### 9.2 准备阶段 4 方案，但不要在本次任务中直接执行阶段 4

本次文档的目的只是阶段 3 收尾评价和修补建议。阶段 4 应另起方案文档和执行计划。

---

## 10. 最终结论

阶段 3 已经达到预期目标，可以进入阶段 4.0。

建议最终结论写成：

```text
阶段 3 成功完成了 phase2 标签溯源、循环验证风险审计、构造一致性检查和阶段 4 掩码种子生成。S2 主集上 predicted mask 与 oracle mask 完全一致，说明该 clean local repair substrate 与 attribution-derived mask policy 高度一致；但该结果只能作为 construction consistency check，不能解释为 independent locator accuracy。phase4_mask_seed.csv 已为 357 个 S2 case 提供 oracle / predicted / random 三类掩码、keep mask、anchor 和旧碰撞证据，足以支持阶段 4.0 Oracle mask backend feasibility audit 和阶段 4.1 Random / Predicted / Oracle formal repair loop。进入阶段 4 前建议补充 random mask 大小公平性统计，并在后续报告中明确 predicted=oracle 的解释边界。
```

