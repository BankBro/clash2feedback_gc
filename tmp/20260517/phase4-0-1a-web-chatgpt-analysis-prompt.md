# Phase 4.0.1a 网页 ChatGPT 分析 Prompt 草稿

> 使用时请把 `<COMMIT_ID>` 替换为本地提交并推送后的实际 commit id.

请阅读 GitHub 仓库 `BankBro/clash2feedback_gc`, 分支 `20260517-161211-phase4-0-1a`, commit `<COMMIT_ID>`, 对阶段 4.0.1a local reconnect calibration 和 visual QC 收尾结果进行独立分析, 并给出下一步实验建议.

请优先阅读这些文件:

- `docs/20260517-Clash2Feedback-GC_阶段4.0.1a局部接回诊断规则校准方案总纲.md`
- `tmp/20260517/phase4-0-1a-local-reconnect-calibration-expt-report.md`
- `tmp/20260517/phase4-0-1a-visual-qc-expt-report.md`
- `reports/phase4_0_1a_local_reconnect_calibration/phase4_0_1a_completion_audit.md`
- `reports/phase4_0_1a_local_reconnect_calibration/local_reconnect_calibration_summary.json`
- `reports/phase4_0_1a_local_reconnect_calibration/local_reconnect_category_counts.csv`
- `reports/phase4_0_1a_local_reconnect_calibration/diffsbdd_reconnect_reclassified.csv`
- `reports/phase4_0_1a_local_reconnect_calibration/reconnect_shadow_reliable_analysis.csv`
- `reports/phase4_0_1a_local_reconnect_calibration/visual_qc_reconnect_cases.csv`
- `reports/phase4_0_1a_local_reconnect_calibration/visual_qc_reconnect_notes.md`
- `reports/phase4_0_1a_local_reconnect_calibration/phase4_0_1a_visual_qc_summary.json`
- `reports/phase4_0_1a_local_reconnect_calibration/manual_review_template.csv`
- `reports/phase4_0_1a_local_reconnect_calibration/reconnect_rule_field_consistency_audit.md`
- `src/clash2feedback/repair/reconnect_calibration.py`
- `tests/test_phase4_0_1a_local_reconnect_calibration.py`

分析时请注意以下边界:

- 4.0.1a 是 report-only / audit-only 的 reconnect 诊断规则校准, 不是新的生成实验.
- 不重跑 DiffSBDD, 不重新生成候选, 不训练或微调模型.
- 不修改 reliable repair 10 项标准, 不把 local reconnect 加入 reliable repair 标准.
- `multi_attachment_out_of_scope` 不等于 ligand invalid, 只表示超出当前 single-anchor R-group repair 任务范围.
- `ligand_valid` 是 RDKit sanitize 层面的合法性, 不等于候选一定是单个完整连通 ligand.
- `candidate_single_fragment=false` 或 `candidate_total_fragment_count > 1` 现在在 reconnect 三分类中优先归入 `invalid_reconnect`.
- `runs/phase4_0_1a_visual_qc/` 下有本地图片和中间资产, 但不提交 Git; 请以已提交的轻量 CSV / JSON / Markdown 和代码为主要依据.

请回答:

1. 当前 reconnect 三分类规则顺序是否合理? 特别是 candidate 可读性, RDKit sanitize, 单连通分量, floating, not connected, extra attachment, generated attachment count, anchor neighbor count 的优先级.
2. 如何解释 `reliable_repair_success=True` 但 `strict_single_anchor_shadow_reliable=False` 的候选? 这是否说明阶段 4.0 / 4.0.1 的 10 项标准不足以覆盖 local reconnect 拓扑约束?
3. visual QC 的 25 个样本是否足以支持阶段 4.0.1a 作为诊断规则校准收尾? 哪些证据还不足?
4. 是否建议关闭阶段 4.0.1a? 如果建议关闭, 请说明关闭口径应是 soft-filter / audit closeout, 不是 final generation improvement claim.
5. 下一步实验建议是什么? 请区分低风险审计增强, 规则/映射修补, 以及真正需要重新生成候选或新 baseline 的实验.
6. 最终报告应该如何表述, 以避免声称 DiffSBDD 改善了生成质量, 或声称 H_clash 进入生成过程?
