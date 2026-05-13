# docs_update_summary_phase3_phase4_residual_fix

## 1. 基线记录

- `git status --short`: 起始工作区干净.
- `git branch --show-current`: `main`.
- `git rev-parse HEAD`: `54458882e3036bd8b36a344b15a914d58a0013b7`.

## 2. 修改文件

- `README.md`
- `docs/README.md`
- `docs/20260504-02-Clash2Feedback-GC_第一篇论文实验方案.md`
- `docs/20260504-01-Clash2Feedback-GC_完整方案与升级路线.md`
- `docs/20260504-03-Clash2Feedback-GC_总体实验递进路线.md`
- `tmp/20260512/docs_update_summary_phase3_phase4_residual_fix.md`

## 3. 每个文件修正内容

- `README.md`
  - 补充 `reports/phase2_injection/phase2_final_report.md` 是历史阶段 2 关闭报告.
  - 明确其中阶段 3 Top-1 / Top-3 建议属于旧口径, 当前后续执行以 `docs/` 更新后的阶段 3 新口径为准.
  - 明确不回写历史实验报告.

- `docs/README.md`
  - 同步补充历史 `phase2_final_report.md` 的旧口径边界.

- `docs/20260504-02-Clash2Feedback-GC_第一篇论文实验方案.md`
  - 将长期推荐版本改为 `operational mask policy + 规则适配器 + 可靠验证器`, 并说明 ranker / learned critic / learned adapter 属于阶段 5/6/7.
  - 将实验流程中的 `C_phi^{diag}` / `C_phi^{rank}` 改为当前阶段 3 provenance audit / mask seed 和 verifier / optional selector, 并标注 learned diagnostic head 与 ranker 是后续阶段.
  - 修正旧 ground truth 表述: 删除 `M^* = argmax_k Score_alpha(R_k)` 作为真实失败区域的定义.
  - 新增 `M_injected = target_rgroup` 和 `M_pred = argmax_k Score_alpha(R_k)` 的区分.
  - 明确 `Score_alpha` 不能定义 independent ground truth.
  - 明确 `M_pred` 与 `target_rgroup` 的一致性只能作为 construction consistency check.
  - 将 learned critic / learned adapter / ranker 相关表述改成阶段 4.1 稳定后再推进.
  - 将最小可发表实验包中的 ranker / learned diagnostic / learned adapter 调整为阶段 4.1 稳定后的推进项.

- `docs/20260504-01-Clash2Feedback-GC_完整方案与升级路线.md`
  - 新增“当前短期执行优先级”.
  - 明确短期顺序为阶段 3 label provenance audit / circularity risk audit / phase4 mask seed, 阶段 4.0 backend feasibility audit, 阶段 4.1 Random / Predicted / Oracle formal repair loop.
  - 明确阶段 5/6/7 的 ranker, learned critic, learned adapter 只有在阶段 4.1 得到稳定 repair outcomes 后再推进.
  - 将纠错器和学习型反馈适配器小节改成长期模块, 不作为当前阶段 3 / 4.0 必做项.
  - 将 Oracle protocol 的说明改为人工 `target_rgroup` 对应区域和最优控制上限.
  - 将最后建议从“先证明结构化反馈比 mask 更有效, 再训练...”改为先阶段 3/4.0/4.1, 再训练阶段 5/6/7 模块.

- `docs/20260504-03-Clash2Feedback-GC_总体实验递进路线.md`
  - 将阶段 6 损失中的 `M^*` 改为 `M_label`.
  - 增加 `M_label` 必须来自阶段 3 审计后的标签口径.
  - 明确 `Score_alpha` 不能作为 independent ground truth.
  - 将阶段 6 Top-1 / Top-3 通过标准改为仅在无泄漏或 construction-consistency 标注设置下报告.

## 4. 是否已修正 “真实失败区域 = argmax Score_alpha”

已修正.

- `docs/20260504-02-Clash2Feedback-GC_第一篇论文实验方案.md` 中原来的 `真实失败区域: M^* = argmax_k Score_alpha(R_k)` 已改为:
  - `M_injected = target_rgroup`, 表示人工注入时被扰动的 R-group.
  - `M_pred = argmax_k Score_alpha(R_k)`, 表示 attribution-derived operational mask policy.
  - `Score_alpha` 不能定义 independent ground truth.

## 5. 是否已补充历史 phase2_final_report.md 旧口径边界

已补充.

- `README.md` 和 `docs/README.md` 均明确 `reports/phase2_injection/phase2_final_report.md` 是历史阶段 2 关闭报告, 其中阶段 3 Top-1 / Top-3 建议属于旧口径, 当前后续执行以 docs 新口径为准.

## 6. 是否仍存在 residual old wording

仍存在少量旧词, 但都在正确上下文中:

- `R-group Top-1 > 70%` / `R-group Top-3 > 90%` 仅在 `docs/20260504-03-Clash2Feedback-GC_总体实验递进路线.md` 中作为“旧的通过标准需要降级”的示例保留.
- `independent locator benchmark` / `无偏 locator benchmark` 只出现在否定或边界说明中.
- `完整 feedback-guided denoising` 只出现在 “不得写成 / 不得声称” 的限制语境中.
- `H_clash 进入生成过程` 只出现在 “只有实现 guided sampling 后才能声称” 的限制语境中.

未发现仍把 predicted mask 写成 ground truth, 或把真实 DiffSBDD de novo failures 写成主要是 single-Rgroup clash 的残留表述.

## 7. 是否修改禁止修改的历史实验结果文件

未修改.

检查的禁止路径无 diff:

```text
reports/phase2_injection
reports/phase2_5_model_induced_audit
data/benchmarks/clashrepairbench_rg_artificial/v0_1
```

本次未跑新实验, 未改代码逻辑, 未重写历史实验报告.

## 8. git diff --check 结果

`git diff --check` 已通过, 无输出.
