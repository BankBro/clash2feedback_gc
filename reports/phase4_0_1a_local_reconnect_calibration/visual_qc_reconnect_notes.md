# Phase 4.0.1a Visual QC Reconnect Notes

## 1. Scope

- visual QC 是阶段 4.0.1a 收尾补充, 不重跑 DiffSBDD, 不重新生成候选.
- `multi_attachment_out_of_scope` 不等于 ligand invalid, 只表示超出当前 single-anchor R-group repair 范围.
- `ligand_valid` 是历史字段名, 在本阶段表示 RDKit sanitize 层面的化学可解析性, 不等价于候选是单个完整 ligand.
- `candidate_single_fragment=false` 或 `candidate_total_fragment_count > 1` 表示候选不是单个连通配体, 在 reconnect 三分类中优先归入 `invalid_reconnect`.
- 本次没有修改 reliable repair 10 项标准, 没有把 local reconnect 加入 reliable repair 标准, 没有回写阶段 4.0 或 4.0.1 历史主结果.

## 2. Summary

- sample_count: 25.
- sampling_group_counts: `{'diffsbdd_reliable_strict_shadow_fail': 7, 'diffsbdd_invalid_non_reliable': 6, 'diffsbdd_multi_non_reliable': 6, 'clean_positive': 3, 'rule_positive': 3}`.
- reconnect_category_counts: `{'multi_attachment_out_of_scope': 8, 'invalid_reconnect': 11, 'single_anchor_reconnect_pass': 6}`.
- render_status_counts: `{'rendered': 900}`.
- contact_sheet_status_counts: `{'written': 75}`.
- review_panel_count: 25.
- local_png_count: 1000, 包含 900 张 clear views, 75 张 contact sheets 和 25 张 Codex review panels.
- camera_quality_counts: `{'camera_quality_good': 64, 'camera_quality_usable': 9, 'camera_quality_poor': 2}`.
- manual_visual_label_counts: `{'looks_single_anchor_connected': 6, 'looks_multi_attachment': 7, 'looks_floating_fragment': 5, 'looks_possible_linker_or_bridge': 4, 'looks_disconnected': 3}`.
- manual_visual_confidence_counts: `{'high': 21, 'medium': 4}`.
- needs_user_review_cases: `[]`.

## 3. Codex Visual Review Conclusion

- clean_positive: 3/3 图像支持 `looks_single_anchor_connected`.
- rule_positive: 3/3 图像支持 `looks_single_anchor_connected`, 未见 reconnect 检查误伤.
- DiffSBDD invalid_reconnect: floating_fragment, not_connected_to_anchor 和 candidate_not_single_fragment 样本基本被图像/RDKit 复核支持; `vqc_009` 与 `vqc_019` 均确认不是渲染拆分错误.
- DiffSBDD multi_attachment_out_of_scope: 单连通候选中的多数样本在 topology/overlay 中呈现 extra attachment, bridge, linker-like 拓扑或同 anchor 多邻接; `vqc_018` 经用户图像复核确认确实存在多个连接点.
- 对同时呈现多连接视觉特征和多片段 RDKit 证据的候选, reconnect 分类以多片段 invalid 优先, 手工视觉标签仍保留可观察到的 multi/linker/floating 特征.
- 原 reliable_repair_success=True 但 strict_single_anchor_shadow_reliable=False 的样本主要原因是 extra attachment/multi-attachment, bridge/ring-closure-like 拓扑, floating fragment, 同 anchor 多邻接或候选多片段, 不是阶段 4.0/4.0.1 十项 reliable 标准本身被修改.

## 4. Case Index

| visual_case_id | sampling_group | case_id | K | reconnect_category | reason | camera_quality | manual_label | confidence | needs_user_review | notes |
|---|---|---:|---:|---|---|---|---|---|---|---|
| vqc_001 | diffsbdd_reliable_strict_shadow_fail | case_000041 | 8 | multi_attachment_out_of_scope | extra_attachments=1 | camera_quality_good/camera_quality_good/camera_quality_good | looks_multi_attachment | high | False | anchor_topology 和 overlay 中可见 generated fragment 在 anchor 附近存在额外连接, 支持 multi_attachment_out_of_scope, 也解释原 reliable 但 strict single-anchor shadow fail. |
| vqc_002 | diffsbdd_reliable_strict_shadow_fail | case_000109 | 16 | multi_attachment_out_of_scope | extra_attachments=2 | camera_quality_good/camera_quality_good/camera_quality_good | looks_multi_attachment | high | False | anchor 附近可见多条 attachment-like 连接, 与 extra_attachments=2 一致, 支持 strict single-anchor shadow fail. |
| vqc_003 | diffsbdd_reliable_strict_shadow_fail | case_000552 | 32 | multi_attachment_out_of_scope | anchor_neighbor_count=2 | camera_quality_good/camera_quality_good/camera_quality_good | looks_multi_attachment | medium | False | anchor_topology 和 overlay 显示 anchor 邻域存在两个 attachment-like 邻接; 按更新后的 reconnect 优先级, num_anchor_neighbors > 1 归为 multi_attachment_out_of_scope, reason 保留 anchor_neighbor_count=2. |
| vqc_004 | diffsbdd_reliable_strict_shadow_fail | case_001704 | 8 | multi_attachment_out_of_scope | extra_attachments=10 | camera_quality_good/camera_quality_good/camera_quality_good | looks_possible_linker_or_bridge | high | False | generated fragment 呈多连接/桥接式拓扑, 与 extra_attachments=10 一致, 明显超出 single-anchor R-group repair 范围. |
| vqc_005 | diffsbdd_reliable_strict_shadow_fail | case_001702 | 8 | invalid_reconnect | candidate_fragment_count=2 | camera_quality_good/camera_quality_good/camera_quality_good | looks_multi_attachment | high | False | anchor_topology 中可见多个 generated attachment 位点, 但 RDKit fragment count 显示 candidate_total_fragment_count=2; 按更新后的优先级, 多片段候选优先归为 invalid_reconnect, 视觉标签保留 multi-attachment 观察特征. |
| vqc_006 | diffsbdd_reliable_strict_shadow_fail | case_001300 | 16 | multi_attachment_out_of_scope | extra_attachments=3 | camera_quality_good/camera_quality_good/camera_quality_good | looks_possible_linker_or_bridge | high | False | overlay 中局部结构呈桥接或 ring-closure 式偏离, 与 extra_attachments=3 一致, 支持 strict shadow fail. |
| vqc_007 | diffsbdd_reliable_strict_shadow_fail | case_002134 | 16 | invalid_reconnect | candidate_fragment_count=2 | camera_quality_good/camera_quality_good/camera_quality_good | looks_floating_fragment | high | False | anchor_topology 和 overlay 中可见与 anchor 主结构分离的 generated/floating 标记, 与 floating_fragment 诊断一致. |
| vqc_008 | diffsbdd_invalid_non_reliable | case_000041 | 8 | invalid_reconnect | candidate_fragment_count=3 | camera_quality_good/camera_quality_good/camera_quality_good | looks_floating_fragment | high | False | 图像中可见游离 generated fragment 或 floating 标记远离 anchor 连接区域, 与 invalid_reconnect/floating_fragment 一致. |
| vqc_009 | diffsbdd_invalid_non_reliable | case_002226 | 16 | invalid_reconnect | ligand_valid=false | camera_quality_good/camera_quality_good/camera_quality_good | looks_disconnected | high | False | 图像中候选配体明显分成两个连通部分; RDKit 直接读取 source/candidate SDF 均显示 2 个连通分量, 且 sanitize 失败为 Explicit valence for atom #5 N, 4, is greater than permitted. 因此该样本支持真实 disconnected/invalid reconnect, 不是渲染拆分错误. |
| vqc_010 | diffsbdd_invalid_non_reliable | case_000109 | 32 | invalid_reconnect | not_connected_to_anchor | camera_quality_good/camera_quality_good/camera_quality_good | looks_disconnected | high | False | generated fragment 与紫色 anchor 区域未形成清楚单锚点接回, 与 not_connected_to_anchor 一致. |
| vqc_011 | diffsbdd_invalid_non_reliable | case_000347 | 8 | invalid_reconnect | candidate_fragment_count=2 | camera_quality_good/camera_quality_good/camera_quality_good | looks_floating_fragment | high | False | anchor_topology/overlay 中可见分离的 generated/floating 标记, 与 floating_fragment 诊断一致. |
| vqc_012 | diffsbdd_invalid_non_reliable | case_000670 | 8 | invalid_reconnect | candidate_fragment_count=2 | camera_quality_usable/camera_quality_usable/camera_quality_good | looks_floating_fragment | medium | False | 虽然 clash 和 topology 质量为 usable, 仍可见 floating/generated 标记与 anchor 主体分离, 支持 floating_fragment 诊断. |
| vqc_013 | diffsbdd_invalid_non_reliable | case_001055 | 8 | invalid_reconnect | candidate_fragment_count=2 | camera_quality_usable/camera_quality_usable/camera_quality_good | looks_floating_fragment | medium | False | usable 质量下仍可判断有游离 generated/floating 标记, 与 floating_fragment 诊断一致. |
| vqc_014 | diffsbdd_multi_non_reliable | case_000552 | 8 | multi_attachment_out_of_scope | extra_attachments=1 | camera_quality_good/camera_quality_good/camera_quality_good | looks_multi_attachment | high | False | anchor_topology 中可见额外 attachment 关系, 与 extra_attachments=1 一致, 支持 multi_attachment_out_of_scope. |
| vqc_015 | diffsbdd_multi_non_reliable | case_001270 | 16 | invalid_reconnect | candidate_fragment_count=4 | camera_quality_usable/camera_quality_good/camera_quality_good | looks_possible_linker_or_bridge | high | False | 拓扑视图显示多连接/桥接式 generated fragment, 同时 RDKit fragment count 显示 candidate_total_fragment_count=4; 按更新后的优先级, 多片段候选优先归为 invalid_reconnect, 而不是 multi_attachment_out_of_scope. |
| vqc_016 | diffsbdd_multi_non_reliable | case_001457 | 32 | invalid_reconnect | candidate_fragment_count=4 | camera_quality_usable/camera_quality_usable/camera_quality_good | looks_possible_linker_or_bridge | medium | False | topology/overlay 可见大范围多连接和片段延伸, 同时 RDKit fragment count 显示 candidate_total_fragment_count=4; 按更新后的优先级, 多片段候选优先归为 invalid_reconnect. |
| vqc_017 | diffsbdd_multi_non_reliable | case_000347 | 8 | multi_attachment_out_of_scope | extra_attachments=2 | camera_quality_good/camera_quality_good/camera_quality_good | looks_multi_attachment | high | False | anchor 附近额外 attachment 在 topology/overlay 中可见, 与 extra_attachments=2 一致. |
| vqc_018 | diffsbdd_multi_non_reliable | case_000670 | 8 | multi_attachment_out_of_scope | extra_attachments=3 | camera_quality_poor/camera_quality_usable/camera_quality_good | looks_multi_attachment | high | False | 用户复核图像后确认该候选确实存在多个连接点; RDKit 读源 SDF 为单一连通分量且 sanitize ok, 因此支持 multi_attachment_out_of_scope, 不是渲染拆分错误. |
| vqc_019 | diffsbdd_multi_non_reliable | case_000707 | 8 | invalid_reconnect | candidate_fragment_count=2 | camera_quality_poor/camera_quality_usable/camera_quality_good | looks_disconnected | high | False | 用户复核图像后确认候选配体分成两个部分; RDKit 直接读取 source/candidate SDF 也显示 candidate_total_fragment_count=2 且 candidate_single_fragment=false. 因此该样本按更新后的优先级归为 invalid_reconnect, 不是渲染错误. |
| vqc_020 | clean_positive | case_000041 | 0 | single_anchor_reconnect_pass | single_anchor_connected | camera_quality_good/camera_quality_good/camera_quality_good | looks_single_anchor_connected | high | False | clean positive 的 anchor_topology 显示 generated/anchor 区域为单锚点连接, 未见游离或额外 attachment. |
| vqc_021 | clean_positive | case_000109 | 0 | single_anchor_reconnect_pass | single_anchor_connected | camera_quality_good/camera_quality_good/camera_quality_good | looks_single_anchor_connected | high | False | clean positive 视觉上支持 single-anchor connected, 未见 floating 或 multi-attachment. |
| vqc_022 | clean_positive | case_000347 | 0 | single_anchor_reconnect_pass | single_anchor_connected | camera_quality_good/camera_quality_good/camera_quality_good | looks_single_anchor_connected | high | False | clean positive 视觉上支持 single-anchor connected, 与自动 single_anchor_reconnect_pass 一致. |
| vqc_023 | rule_positive | case_000041 | 8 | single_anchor_reconnect_pass | single_anchor_connected | camera_quality_good/camera_quality_good/camera_quality_good | looks_single_anchor_connected | high | False | rule_fixed_topology positive 视觉上支持 single-anchor connected, 未见 reconnect 检查误伤. |
| vqc_024 | rule_positive | case_000109 | 8 | single_anchor_reconnect_pass | single_anchor_connected | camera_quality_good/camera_quality_good/camera_quality_good | looks_single_anchor_connected | high | False | rule_fixed_topology positive 视觉上支持 single-anchor connected, 与自动 single_anchor_reconnect_pass 一致. |
| vqc_025 | rule_positive | case_000347 | 8 | single_anchor_reconnect_pass | single_anchor_connected | camera_quality_good/camera_quality_good/camera_quality_good | looks_single_anchor_connected | high | False | rule_fixed_topology positive 视觉上支持 single-anchor connected, 未见游离或额外 attachment. |
