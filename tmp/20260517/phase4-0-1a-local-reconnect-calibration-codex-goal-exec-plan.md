# phase4-0-1a-local-reconnect-calibration 本地执行计划

## 1. 仓库事实核查

- 当前分支: `20260517-161211-phase4-0-1a`.
- 当前 HEAD commit: `93f1e221cc7e959248a418382e0800250bf6d5f4`.
- `git status --short --branch`: 当前有未提交修改, 仅见未跟踪方案文档 `docs/20260517-Clash2Feedback-GC_阶段4.0.1a局部接回诊断规则校准方案总纲.md`.
- 方案文档存在, 但当前未跟踪.
- 阶段 4.0.1 主要输入均存在:
  - `phase4_0_1_summary.json`
  - `diffsbdd_anchor_reconnect_audit.csv`
  - `diffsbdd_verifier_outcome.csv`
  - `diffsbdd_candidate_manifest.csv`
  - `diffsbdd_budget_curve.csv`
  - `phase4_0_1_closeout_audit.md`
  - `phase4_0_1_completion_audit.md`
- 阶段 4.0 主要正样本来源均存在:
  - `verifier_outcome.csv`
  - `candidate_manifest.csv`
  - `backend_comparison.csv`
  - `phase4_0_final_experiment_report.md`
- 阶段 4.0 `rule_fixed_topology` 有 320 条候选, 227 条 reliable candidate, 候选 SDF 路径均存在, 可作为 rule positive 来源.
- 阶段 4.0.1 有 2,187 条 DiffSBDD candidate 记录, `local_reconnect_pass=False` 为 2,187/2,187, `reliable_repair_success=True` 为 48 条.
- 40 个 selected cases 的 `original_ligand_sdf`, `failed_ligand_sdf`, phase2 sample 和 processed sample 均可从 `manifest.parquet` 与 selected cases 恢复.

## 2. 字段和实现映射

- DiffSBDD 候选级主表采用 `reports/phase4_0_1_diffsbdd_conditional_repair/diffsbdd_verifier_outcome.csv`, 因其同时包含 verifier 10 项字段和 reconnect 诊断字段.
- `diffsbdd_anchor_reconnect_audit.csv` 作为 reconnect 交叉核查表; 该表缺少 verifier 10 项字段, 可用 `case_id + candidate_budget_k + candidate_id + candidate_index` 从 verifier outcome 无歧义补齐.
- `diffsbdd_candidate_manifest.csv` 作为 candidate path, attempt, proposal 和 generation metadata 来源.
- 以下方案字段在阶段 4.0.1 verifier 主表中已存在:
  - `candidate_readable`, `ligand_valid`, `fixed_structure_match_success`, `anchor_integrity`
  - `local_reconnect_pass`, `local_reconnect_failure_reason`
  - `anchor_reconnect_status`, `anchor_reconnect_reason`
  - `anchor_match_success`, `generated_fragment_connected_to_anchor`, `generated_fragment_attachment_count`
  - `num_anchor_neighbors`, `num_extra_attachments`, `floating_fragment_detected`
  - `candidate_single_fragment`, `candidate_total_fragment_count`
  - `target_mask_heavy_atom_count`, `generated_fragment_heavy_atom_count`, `generated_fragment_size_diff`, `generated_element_mismatch_count`
  - `old_clash_resolved`, `no_new_severe_clash`, `scaffold_stable`, `keep_region_stable`, `edit_compliance`, `pocket_retention`, `reliable_repair_success`
- 阶段 4.0 rule positive 缺少 reconnect 字段, 执行时用 `Phase4CaseInput` + `analyze_candidate_fragment()` 对已有 `candidate_path` 重新计算.
- clean positive 缺少 verifier 10 项完整输出, 只用于 reconnect 规则校准; `candidate_readable`, `ligand_valid`, mapping 和 reconnect 字段可由原始 SDF 与 `analyze_candidate_fragment()` 恢复.
- 当前未发现不可恢复字段或高风险冲突.

## 3. 三分类 reconnect 规则

- `single_anchor_reconnect_pass`: 候选可读, ligand valid, fixed structure mapping 成功, anchor 可映射, generated fragment 连接到 anchor, `num_anchor_neighbors == 1`, `num_extra_attachments == 0`, 无 floating fragment.
- `multi_attachment_out_of_scope`: 候选可读且 mapping / anchor / anchor connection 成功, 但 `num_extra_attachments > 0` 或 `generated_fragment_attachment_count > 1`.
- `invalid_reconnect`: 候选不可读, ligand invalid, fixed structure mapping 失败, anchor 不可映射, generated fragment 为空, 未连接 anchor, floating fragment, 或其他无法解释为 multi-attachment out-of-scope 的失败.
- `multi_attachment_out_of_scope` 不等于 ligand invalid, 只表示超出当前 single-anchor R-group repair 任务范围.
- local reconnect 仍是新增诊断字段, 不加入 reliable repair 10 项标准, 不回写 `reliable_repair_success`.

## 4. 具体执行步骤

- 新增 `configs/phase4_0_1a_local_reconnect_calibration.yaml`, 固定 `mode: report_only_audit_only`.
- 新增 `src/clash2feedback/repair/reconnect_calibration.py`, 实现:
  - 输入表存在性和字段 schema 校验.
  - DiffSBDD candidates 三分类重标注.
  - rule positive reconnect 诊断重算.
  - clean positive reconnect 诊断重算.
  - synthetic negative row-level 最小校准, 覆盖 disconnected, floating, extra-attachment, missing-anchor.
  - shadow analysis, 仅新增 `strict_single_anchor_shadow_reliable`.
  - summary, completion audit 和临时 expt-report 写出.
- 新增 `scripts/phase4_0_1a_local_reconnect_calibration.py`, 只运行 report-only audit, 不调用 DiffSBDD, 不重新生成候选.
- 输出到 `reports/phase4_0_1a_local_reconnect_calibration/`:
  - `local_reconnect_calibration_summary.json`
  - `local_reconnect_calibration_cases.csv`
  - `local_reconnect_category_counts.csv`
  - `diffsbdd_reconnect_reclassified.csv`
  - `rule_positive_reconnect_check.csv`
  - `clean_positive_reconnect_check.csv`
  - `synthetic_negative_reconnect_check.csv`
  - `reconnect_shadow_reliable_analysis.csv`
  - `phase4_0_1a_completion_audit.md`
- 输出临时实验汇报:
  - `tmp/20260517/phase4-0-1a-local-reconnect-calibration-expt-report.md`

## 5. 预计新增和修改文件

- 允许新增或修改:
  - `configs/phase4_0_1a_local_reconnect_calibration.yaml`
  - `scripts/phase4_0_1a_local_reconnect_calibration.py`
  - `src/clash2feedback/repair/reconnect_calibration.py`
  - `tests/test_phase4_0_1a_local_reconnect_calibration.py`
  - `reports/phase4_0_1a_local_reconnect_calibration/`
  - `tmp/20260517/phase4-0-1a-local-reconnect-calibration-expt-report.md`
  - 相关 `README.md` 的阶段入口和产物说明
- 只读输入:
  - 阶段 4.0.1 所有既有报告
  - 阶段 4.0 所有既有报告
  - phase2 benchmark 和 processed sample
  - `runs/` 下已有候选 SDF, 仅作为读取对象
- 禁止修改:
  - 用户列出的阶段 2, 2.5, 3, 4.0, 4.0.1 历史结果文件
  - `data/benchmarks/clashrepairbench_rg_artificial/v0_1/`
  - `external/DiffSBDD/`
  - `external/DiffDec/`
  - `runs/`

## 6. 测试计划

- `conda run -n c2f_cpu python -m compileall src scripts`
- `conda run -n c2f_cpu python -m pytest tests/test_phase4_0_1a_local_reconnect_calibration.py -q`
- `conda run -n c2f_cpu python -m pytest tests/test_phase4_0_1_diffsbdd_conditional.py -q`
- 如时间允许, 运行 `conda run -n c2f_cpu python -m pytest -q`.
- 新增测试覆盖三分类优先级, multi-attachment 口径, shadow analysis 不回写 reliable, synthetic negative 最小负样本, reliable 10 项标准不变.

## 7. 禁止修改范围核查方式

- 执行前后记录 `git status --short --branch`, 当前分支和 HEAD.
- 执行后用 `git diff --name-only` 核查实际改动路径, 对禁止清单逐项确认无 diff.
- 对 `reports/phase3_label_provenance_audit/phase4_mask_seed.csv` 记录执行前后 SHA256, 必须不变.
- 不把 `reports/phase4_0_backend_feasibility/` 和 `reports/phase4_0_1_diffsbdd_conditional_repair/` 作为写入目标.

## 8. 冲突项和阻塞项

- 当前只读核查未发现高风险冲突.
- 若执行时发现字段不可恢复, 输入表行数不一致, clean / rule positive 大量无法映射, 或方案口径与仓库事实冲突, 先生成 `tmp/20260517/phase4-0-1a-local-reconnect-calibration-conflict-report.md`, 停止冲突部分.
- 低风险字段差异仅在 summary 和 completion audit 中记录适配方式.

## 9. 后续 /goal 执行建议

- 先实现 report-only calibration 代码和测试, 再运行 CLI 生成报告.
- 完成后必须生成 `tmp/20260517/phase4-0-1a-local-reconnect-calibration-expt-report.md`.
- 该 expt-report 是临时实验汇报, 不是 final report.
