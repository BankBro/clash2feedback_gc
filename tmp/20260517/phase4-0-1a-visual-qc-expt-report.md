# Phase 4.0.1a Visual QC 临时实验汇报

> 本文件是临时实验汇报, 不是 final report.

## 1. 目标和边界

- 本次 visual QC 用于检查阶段 4.0.1a reconnect 三分类与三维结构观察是否一致.
- 未重跑 DiffSBDD, 未重新生成候选, 未训练或微调模型.
- 未修改 reliable repair 10 项标准, 未把 local reconnect 加入 reliable repair 标准.
- 未回写阶段 4.0 或阶段 4.0.1 历史结果.
- `multi_attachment_out_of_scope` 不等于 ligand invalid, 只表示超出当前 single-anchor R-group repair 任务范围.

## 2. Docs 更新状态

- 已在 `docs/20260517-Clash2Feedback-GC_阶段4.0.1a局部接回诊断规则校准方案总纲.md` 补充 visual QC 收尾方案.
- 方案明确 visual QC 不是新生成实验, 不生成 final report, 只作为阶段 4.0.1a 关闭前的人工/Codex 可视化抽查材料.

## 3. 实际抽样分布

- sample_count: 25.
- sampling_group_counts: `{'diffsbdd_reliable_strict_shadow_fail': 7, 'diffsbdd_invalid_non_reliable': 6, 'diffsbdd_multi_non_reliable': 6, 'clean_positive': 3, 'rule_positive': 3}`.
- reconnect_category_counts: `{'multi_attachment_out_of_scope': 11, 'invalid_reconnect': 8, 'single_anchor_reconnect_pass': 6}`.
- K 覆盖: `{'8': 14, '16': 5, '32': 3, '0': 3}`.
- 实际采用 25 个 unique candidate; 为满足总数 25, reliable strict shadow fail 组实际为 7 个, 而不是原草案中 8 个.

## 4. 渲染概况

- 三类视图均已生成: `reconnect_clash`, `reconnect_anchor_topology`, `reconnect_before_after_overlay`.
- render_task_count: 900.
- render_status_counts: `{'rendered': 900}`.
- contact_sheet_count: 75.
- contact_sheet_status_counts: `{'written': 75}`.
- PNG 总量: 900 张 clear views + 75 张 contact sheets + 25 张 Codex review panels, 合计 1000 张.
- 本地运行资产位于 `runs/phase4_0_1a_visual_qc/`, 目录大小约 126M, 不建议提交 Git.
- `reconnect_clash_contact_sheet` 基本复用阶段 0 clash view 的白底, soft lighting, candidate orange stick, pocket gray transparent 和 contact marker 扫图风格.

## 5. 相机质量和重渲染

- camera_quality_counts: `{'camera_quality_good': 64, 'camera_quality_usable': 9, 'camera_quality_poor': 2}`.
- camera_retry_count_total: 0.
- 最终成功运行前, 曾因 full pocket + 1024 candidate directions 的相机筛选过慢而停止, 后改为 nearby pocket camera proxy + 256 candidate directions. 该调整只影响相机筛选效率, 不改候选结构和历史结果.
- 最终成功运行后没有逐 case 重渲染. `vqc_018` 和 `vqc_019` 的 clash view 自动质量为 `camera_quality_poor`; topology/overlay 仍支持 multi-attachment 趋势, 但按任务约束保留为 `needs_further_review`, 不写强视觉结论.

## 6. Codex 图片检视结论

- Codex 已实际查看 25 个 review panels, 每个 panel 包含三类 contact sheet.
- clean_positive: 3/3 视觉上支持 single-anchor reconnect.
- rule_positive: 3/3 视觉上支持 single-anchor reconnect, 未见 reconnect 诊断误伤.
- invalid_reconnect: floating_fragment 与 not_connected_to_anchor 样本视觉上基本一致; `vqc_009` 的 `ligand_valid=false` 不能仅凭图片确认, 需结合 RDKit/verifier 复核.
- multi_attachment_out_of_scope: 大多数样本显示 extra attachment, bridge 或 linker-like 拓扑, 符合超出 single-anchor R-group repair 范围的解释.
- 原 reliable 但 strict shadow 失败候选的主要视觉原因: multi-attachment/extra attachment, bridge/ring-closure-like 拓扑, floating fragment, 以及 anchor 邻域 mapping 边界问题.

## 7. 人工复核项

- needs_user_review_count: 4.
- needs_user_review_cases: `['vqc_003', 'vqc_009', 'vqc_018', 'vqc_019']`.
- `vqc_003`: 图像支持 strict single-anchor 失败, 但 invalid vs multi 边界依赖 `anchor_neighbor_count=2`, 建议人工复核分类边界.
- `vqc_009`: `ligand_valid=false` 是 verifier/RDKit 结论, 图片不能单独强判化学有效性.
- `vqc_018`, `vqc_019`: topology/overlay 支持 multi 趋势, 但 clash view 自动质量为 poor, 保留人工复核.

## 8. 临时关闭建议

- 临时结论: visual QC 基本支持阶段 4.0.1a local reconnect 三分类和 shadow analysis 的主要方向.
- 不建议现在生成 final report. 建议用户和网页 ChatGPT 先复核 `vqc_003`, `vqc_009`, `vqc_018`, `vqc_019`, 再决定最终报告措辞.
- 若复核确认这些边界样本不构成系统性反例, 阶段 4.0.1a 可正式关闭.
- 若复核发现大量不一致, 应先修 reconnect/mapping 诊断, 不得强行关闭为正结果.

## 9. Case Table

| visual_case_id | sampling_group | case_id | K | reconnect_category | reason | manual_label | confidence | needs_user_review |
|---|---|---:|---:|---|---|---|---|---|
| vqc_001 | diffsbdd_reliable_strict_shadow_fail | case_000041 | 8 | multi_attachment_out_of_scope | extra_attachments=1 | looks_multi_attachment | high | False |
| vqc_002 | diffsbdd_reliable_strict_shadow_fail | case_000109 | 16 | multi_attachment_out_of_scope | extra_attachments=2 | looks_multi_attachment | high | False |
| vqc_003 | diffsbdd_reliable_strict_shadow_fail | case_000552 | 32 | invalid_reconnect | anchor_neighbor_count=2 | looks_mapping_uncertain | medium | True |
| vqc_004 | diffsbdd_reliable_strict_shadow_fail | case_001704 | 8 | multi_attachment_out_of_scope | extra_attachments=10 | looks_possible_linker_or_bridge | high | False |
| vqc_005 | diffsbdd_reliable_strict_shadow_fail | case_001702 | 8 | multi_attachment_out_of_scope | extra_attachments=4 | looks_multi_attachment | high | False |
| vqc_006 | diffsbdd_reliable_strict_shadow_fail | case_001300 | 16 | multi_attachment_out_of_scope | extra_attachments=3 | looks_possible_linker_or_bridge | high | False |
| vqc_007 | diffsbdd_reliable_strict_shadow_fail | case_002134 | 16 | invalid_reconnect | floating_fragment | looks_floating_fragment | high | False |
| vqc_008 | diffsbdd_invalid_non_reliable | case_000041 | 8 | invalid_reconnect | floating_fragment | looks_floating_fragment | high | False |
| vqc_009 | diffsbdd_invalid_non_reliable | case_002226 | 16 | invalid_reconnect | ligand_valid=false | needs_further_review | low | True |
| vqc_010 | diffsbdd_invalid_non_reliable | case_000109 | 32 | invalid_reconnect | not_connected_to_anchor | looks_disconnected | high | False |
| vqc_011 | diffsbdd_invalid_non_reliable | case_000347 | 8 | invalid_reconnect | floating_fragment | looks_floating_fragment | high | False |
| vqc_012 | diffsbdd_invalid_non_reliable | case_000670 | 8 | invalid_reconnect | floating_fragment | looks_floating_fragment | medium | False |
| vqc_013 | diffsbdd_invalid_non_reliable | case_001055 | 8 | invalid_reconnect | floating_fragment | looks_floating_fragment | medium | False |
| vqc_014 | diffsbdd_multi_non_reliable | case_000552 | 8 | multi_attachment_out_of_scope | extra_attachments=1 | looks_multi_attachment | high | False |
| vqc_015 | diffsbdd_multi_non_reliable | case_001270 | 16 | multi_attachment_out_of_scope | extra_attachments=10 | looks_possible_linker_or_bridge | high | False |
| vqc_016 | diffsbdd_multi_non_reliable | case_001457 | 32 | multi_attachment_out_of_scope | extra_attachments=11 | looks_possible_linker_or_bridge | medium | False |
| vqc_017 | diffsbdd_multi_non_reliable | case_000347 | 8 | multi_attachment_out_of_scope | extra_attachments=2 | looks_multi_attachment | high | False |
| vqc_018 | diffsbdd_multi_non_reliable | case_000670 | 8 | multi_attachment_out_of_scope | extra_attachments=3 | needs_further_review | low | True |
| vqc_019 | diffsbdd_multi_non_reliable | case_000707 | 8 | multi_attachment_out_of_scope | extra_attachments=4 | needs_further_review | low | True |
| vqc_020 | clean_positive | case_000041 | 0 | single_anchor_reconnect_pass | single_anchor_connected | looks_single_anchor_connected | high | False |
| vqc_021 | clean_positive | case_000109 | 0 | single_anchor_reconnect_pass | single_anchor_connected | looks_single_anchor_connected | high | False |
| vqc_022 | clean_positive | case_000347 | 0 | single_anchor_reconnect_pass | single_anchor_connected | looks_single_anchor_connected | high | False |
| vqc_023 | rule_positive | case_000041 | 8 | single_anchor_reconnect_pass | single_anchor_connected | looks_single_anchor_connected | high | False |
| vqc_024 | rule_positive | case_000109 | 8 | single_anchor_reconnect_pass | single_anchor_connected | looks_single_anchor_connected | high | False |
| vqc_025 | rule_positive | case_000347 | 8 | single_anchor_reconnect_pass | single_anchor_connected | looks_single_anchor_connected | high | False |

## 10. 测试结果

- `conda run -n c2f_cpu python -m compileall src scripts`: passed.
- `conda run -n c2f_cpu python -m pytest tests/test_phase4_0_1a_local_reconnect_calibration.py -q`: 4 passed.
- `conda run -n c2f_cpu python -m pytest tests/test_phase4_0_1a_visual_qc.py -q`: 3 passed.
- `conda run -n c2f_cpu python -m pytest tests/test_render_visual_check.py -q`: 10 passed.
- `conda run -n c2f_cpu python -m pytest -q`: 141 passed in 8.87s.
