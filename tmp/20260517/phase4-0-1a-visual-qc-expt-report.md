# Phase 4.0.1a Visual QC 临时实验汇报

## 1. 目标和边界

- 本次 visual QC 是阶段 4.0.1a local reconnect calibration 的收尾补充, 只检查 25 个样本的三维结构观察是否支持 reconnect 三分类.
- 不重跑 DiffSBDD, 不重新生成候选, 不训练或微调模型, 不修改 reliable repair 10 项标准, 不生成 final report.
- `ligand_valid` 表示 RDKit sanitize 层面的合法性; `candidate_single_fragment` / `candidate_total_fragment_count` 才表示候选是否为单个连通配体.

## 2. Docs 更新状态

- 已在方案文档中说明 `ligand_valid` 与单分子候选完整性不是同一概念.
- 已同步规则更新: `candidate_total_fragment_count > 1` 或 `candidate_single_fragment=false` 在 multi-attachment 之前归入 `invalid_reconnect`.
- 已同步规则更新: `num_anchor_neighbors > 1` 在 floating/not-connected 之后归入 `multi_attachment_out_of_scope`.

## 3. 实际抽样分布

- sample_count: 25.
- sampling_group_counts: `{'diffsbdd_reliable_strict_shadow_fail': 7, 'diffsbdd_invalid_non_reliable': 6, 'diffsbdd_multi_non_reliable': 6, 'clean_positive': 3, 'rule_positive': 3}`.
- reconnect_category_counts: `{'multi_attachment_out_of_scope': 8, 'invalid_reconnect': 11, 'single_anchor_reconnect_pass': 6}`.
- K 覆盖: `{'8': 14, '16': 5, '32': 3, '0': 3}`.
- 实际采用 25 个 unique candidate; 为满足总数 25, reliable strict shadow fail 组实际为 7 个.

## 4. 渲染概况

- render_status_counts: `{'rendered': 900}`.
- contact_sheet_status_counts: `{'written': 75}`.
- PNG 总量: 900 张 clear views + 75 张 contact sheets + 25 张 Codex review panels, 合计 1000 张.
- 本地运行资产位于 `runs/phase4_0_1a_visual_qc/`, 目录大小约 126M, 不建议提交 Git.
- 在 reconnect 规则更新后, 已 panel-only 重建全部 25 张 `review_panel.png`, 使 panel 标题与当前 `visual_qc_reconnect_cases.csv` 中的 `reconnect_category` / `reconnect_category_reason` 保持一致.
- 已同步重建 `runs/phase4_0_1a_visual_qc/classified_by_visual_error/` 下的 panel-only 分类链接. 该目录只用于本地人工查看, 不作为远端 GitHub 交接产物.

## 5. 相机质量和重渲染

- camera_quality_counts: `{'camera_quality_good': 64, 'camera_quality_usable': 9, 'camera_quality_poor': 2}`.
- camera_retry_count_total: 0.
- `vqc_018` 与 `vqc_019` 的 clash view 自动质量为 `camera_quality_poor`, 但用户复核 topology/overlay 后已分别确认 multi-attachment 和 disconnected 结论.

## 6. Codex / 用户图片检视结论

- Codex 已实际查看 25 个 review panels, 每个 panel 包含三类 contact sheet; 用户随后重点复核了 `vqc_009`, `vqc_018`, `vqc_019`.
- clean_positive: 3/3 视觉上支持 single-anchor reconnect.
- rule_positive: 3/3 视觉上支持 single-anchor reconnect, 未见 reconnect 诊断误伤.
- invalid_reconnect: floating_fragment, not_connected_to_anchor 和 candidate_not_single_fragment 样本视觉/RDKit 证据基本一致; `vqc_019` 已从 multi 改为 invalid, reason 为 `candidate_fragment_count=2`.
- multi_attachment_out_of_scope: 大多数样本显示 extra attachment, bridge, linker-like 拓扑或同 anchor 多邻接; `vqc_018` 确认存在多个连接点.

## 7. 人工复核项

- needs_user_review_count: 0.
- needs_user_review_cases: `[]`.
- `vqc_018`: 用户复核确认多个连接点, 不再列为待复核.
- `vqc_019`: 用户复核确认配体分成两部分, RDKit 也确认两个连通分量, 不再列为待复核.

## 8. 临时关闭建议

- 临时结论: visual QC 支持阶段 4.0.1a local reconnect 三分类和 shadow analysis 的主要方向.
- 从 visual QC 角度, 当前已无强制待复核 case; final report 仍暂不生成, 等用户和网页 ChatGPT 讨论后决定最终报告措辞.
- 面向网页 ChatGPT 的远端交接以轻量 CSV / JSON / Markdown 报告和规则代码为准; `runs/` 下 PNG, SDF, BILD 和 ChimeraX 脚本等运行资产不提交 Git.

## 9. Case Table

| visual_case_id | sampling_group | case_id | K | reconnect_category | reason | manual_label | confidence | needs_user_review |
|---|---|---:|---:|---|---|---|---|---|
| vqc_001 | diffsbdd_reliable_strict_shadow_fail | case_000041 | 8 | multi_attachment_out_of_scope | extra_attachments=1 | looks_multi_attachment | high | False |
| vqc_002 | diffsbdd_reliable_strict_shadow_fail | case_000109 | 16 | multi_attachment_out_of_scope | extra_attachments=2 | looks_multi_attachment | high | False |
| vqc_003 | diffsbdd_reliable_strict_shadow_fail | case_000552 | 32 | multi_attachment_out_of_scope | anchor_neighbor_count=2 | looks_multi_attachment | medium | False |
| vqc_004 | diffsbdd_reliable_strict_shadow_fail | case_001704 | 8 | multi_attachment_out_of_scope | extra_attachments=10 | looks_possible_linker_or_bridge | high | False |
| vqc_005 | diffsbdd_reliable_strict_shadow_fail | case_001702 | 8 | invalid_reconnect | candidate_fragment_count=2 | looks_multi_attachment | high | False |
| vqc_006 | diffsbdd_reliable_strict_shadow_fail | case_001300 | 16 | multi_attachment_out_of_scope | extra_attachments=3 | looks_possible_linker_or_bridge | high | False |
| vqc_007 | diffsbdd_reliable_strict_shadow_fail | case_002134 | 16 | invalid_reconnect | candidate_fragment_count=2 | looks_floating_fragment | high | False |
| vqc_008 | diffsbdd_invalid_non_reliable | case_000041 | 8 | invalid_reconnect | candidate_fragment_count=3 | looks_floating_fragment | high | False |
| vqc_009 | diffsbdd_invalid_non_reliable | case_002226 | 16 | invalid_reconnect | ligand_valid=false | looks_disconnected | high | False |
| vqc_010 | diffsbdd_invalid_non_reliable | case_000109 | 32 | invalid_reconnect | not_connected_to_anchor | looks_disconnected | high | False |
| vqc_011 | diffsbdd_invalid_non_reliable | case_000347 | 8 | invalid_reconnect | candidate_fragment_count=2 | looks_floating_fragment | high | False |
| vqc_012 | diffsbdd_invalid_non_reliable | case_000670 | 8 | invalid_reconnect | candidate_fragment_count=2 | looks_floating_fragment | medium | False |
| vqc_013 | diffsbdd_invalid_non_reliable | case_001055 | 8 | invalid_reconnect | candidate_fragment_count=2 | looks_floating_fragment | medium | False |
| vqc_014 | diffsbdd_multi_non_reliable | case_000552 | 8 | multi_attachment_out_of_scope | extra_attachments=1 | looks_multi_attachment | high | False |
| vqc_015 | diffsbdd_multi_non_reliable | case_001270 | 16 | invalid_reconnect | candidate_fragment_count=4 | looks_possible_linker_or_bridge | high | False |
| vqc_016 | diffsbdd_multi_non_reliable | case_001457 | 32 | invalid_reconnect | candidate_fragment_count=4 | looks_possible_linker_or_bridge | medium | False |
| vqc_017 | diffsbdd_multi_non_reliable | case_000347 | 8 | multi_attachment_out_of_scope | extra_attachments=2 | looks_multi_attachment | high | False |
| vqc_018 | diffsbdd_multi_non_reliable | case_000670 | 8 | multi_attachment_out_of_scope | extra_attachments=3 | looks_multi_attachment | high | False |
| vqc_019 | diffsbdd_multi_non_reliable | case_000707 | 8 | invalid_reconnect | candidate_fragment_count=2 | looks_disconnected | high | False |
| vqc_020 | clean_positive | case_000041 | 0 | single_anchor_reconnect_pass | single_anchor_connected | looks_single_anchor_connected | high | False |
| vqc_021 | clean_positive | case_000109 | 0 | single_anchor_reconnect_pass | single_anchor_connected | looks_single_anchor_connected | high | False |
| vqc_022 | clean_positive | case_000347 | 0 | single_anchor_reconnect_pass | single_anchor_connected | looks_single_anchor_connected | high | False |
| vqc_023 | rule_positive | case_000041 | 8 | single_anchor_reconnect_pass | single_anchor_connected | looks_single_anchor_connected | high | False |
| vqc_024 | rule_positive | case_000109 | 8 | single_anchor_reconnect_pass | single_anchor_connected | looks_single_anchor_connected | high | False |
| vqc_025 | rule_positive | case_000347 | 8 | single_anchor_reconnect_pass | single_anchor_connected | looks_single_anchor_connected | high | False |

## 10. 测试结果

- `conda run -n c2f_cpu python -m compileall src scripts`: passed.
- `conda run -n c2f_cpu python -m pytest tests/test_phase4_0_1a_local_reconnect_calibration.py -q`: 4 passed in 0.42s.
- `conda run -n c2f_cpu python -m pytest tests/test_phase4_0_1a_local_reconnect_calibration.py tests/test_phase4_0_1a_visual_qc.py -q`: 7 passed in 0.55s.
- `conda run -n c2f_cpu python -m pytest -q`: 141 passed in 8.47s.
