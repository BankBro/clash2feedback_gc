# Phase 4.0.1a Local Reconnect Calibration + Visual QC 最终实验报告

## 1. 阶段定位

阶段 4.0.1a 是 report-only / audit-only 的 local reconnect 诊断规则校准与 visual QC 收尾阶段. 本阶段只复核和重标注既有候选级结果, 不产生新的生成候选.

本阶段明确未执行以下操作:

- 未重跑 DiffSBDD.
- 未重新生成候选.
- 未训练或微调模型.
- 未修改 DiffSBDD denoising loop.
- 未修改 reliable repair 10 项标准.
- 未把 local reconnect 加入 reliable repair 标准.
- 未回写阶段 4.0 或阶段 4.0.1 历史主结果.
- 未声称 `H_clash` 进入 DiffSBDD 生成过程.
- 未提交 `runs/` 下 PNG, SDF, BILD, ChimeraX 脚本等重资产.

本报告依据当前仓库真实结果生成. 生成前核查信息如下:

- repository: `BankBro/clash2feedback_gc`.
- branch: `20260517-161211-phase4-0-1a`.
- report base HEAD: `e268b7e36099949d2c2f276420cec6a1434a1465`.
- generation-time `git status --short`: clean.
- 当前 HEAD 已包含阶段 4.0.1a local reconnect calibration, visual QC 和 field consistency audit 最新轻量产物.

## 2. 数据来源

本报告主要读取以下产物:

- `docs/20260517-Clash2Feedback-GC_阶段4.0.1a局部接回诊断规则校准方案总纲.md`.
- `tmp/20260517/phase4-0-1a-local-reconnect-calibration-expt-report.md`.
- `tmp/20260517/phase4-0-1a-visual-qc-expt-report.md`.
- `reports/phase4_0_1a_local_reconnect_calibration/local_reconnect_calibration_summary.json`.
- `reports/phase4_0_1a_local_reconnect_calibration/local_reconnect_category_counts.csv`.
- `reports/phase4_0_1a_local_reconnect_calibration/diffsbdd_reconnect_reclassified.csv`.
- `reports/phase4_0_1a_local_reconnect_calibration/reconnect_shadow_reliable_analysis.csv`.
- `reports/phase4_0_1a_local_reconnect_calibration/visual_qc_reconnect_cases.csv`.
- `reports/phase4_0_1a_local_reconnect_calibration/visual_qc_reconnect_notes.md`.
- `reports/phase4_0_1a_local_reconnect_calibration/phase4_0_1a_visual_qc_summary.json`.
- `reports/phase4_0_1a_local_reconnect_calibration/reconnect_rule_field_consistency_audit.md`.
- `src/clash2feedback/repair/reconnect_calibration.py`.
- `tests/test_phase4_0_1a_local_reconnect_calibration.py`.
- `tests/test_phase4_0_1a_visual_qc.py`.

## 3. Reconnect 三分类规则

阶段 4.0.1a 将原先二分类的 local reconnect 诊断拆成三类:

- `single_anchor_reconnect_pass`: 候选符合当前 single-anchor R-group repair 语义. 候选可读, RDKit sanitize 基础合法, 单连通配体, 生成片段接回 anchor, `num_anchor_neighbors == 1`, `num_extra_attachments == 0`, 且无 floating fragment.
- `multi_attachment_out_of_scope`: 候选基础可读且为单连通配体, 但存在 extra attachment, generated fragment 多 attachment, 或 anchor 多邻接. 这类样本可能在化学上不一定非法, 但超出当前 single-anchor R-group repair 任务范围.
- `invalid_reconnect`: 候选不可读, `ligand_valid=false`, 候选多片段, 固定结构映射失败, anchor 缺失, generated fragment 为空, floating fragment, 未接回 anchor, 或其它不可解释的 reconnect 失败.

当前规则顺序是先排除 invalid, 再判断 multi-attachment, 最后才判定 single-anchor pass. 具体优先级为:

1. `candidate_readable=false` 或候选路径为空 -> `invalid_reconnect`.
2. `ligand_valid=false` -> `invalid_reconnect`.
3. `candidate_total_fragment_count > 1` 或 `candidate_single_fragment=false` -> `invalid_reconnect`.
4. 固定结构映射失败, `fixed_structure_match_success=false`, 或 `anchor_match_success=false` -> `invalid_reconnect`.
5. `generated_fragment_heavy_atom_count <= 0` -> `invalid_reconnect`.
6. `floating_fragment_detected=true` -> `invalid_reconnect`.
7. `generated_fragment_connected_to_anchor=false` -> `invalid_reconnect`.
8. `num_extra_attachments > 0` 或 `generated_fragment_attachment_count > 1` -> `multi_attachment_out_of_scope`.
9. `num_anchor_neighbors > 1` -> `multi_attachment_out_of_scope`.
10. 单连通, 接回 anchor, anchor 邻接数为 1, 无 extra attachment, 无 floating fragment -> `single_anchor_reconnect_pass`.

这里有两个关键口径:

- `multi_attachment_out_of_scope` 不等于 ligand invalid. 它只表示该候选超出当前 single-anchor R-group repair 范围.
- `ligand_valid` 只是 RDKit sanitize 层面的基础合法性, 不等于候选一定是单个完整连通 ligand. 候选整体连通性由 `candidate_single_fragment` 和 `candidate_total_fragment_count` 判断.

## 4. 校准结果

阶段 4.0.1a 的正负样本校准支持当前规则方向:

| source_group | K | reconnect_category | count |
|---|---:|---|---:|
| clean_positive | 0 | single_anchor_reconnect_pass | 40 |
| rule_positive | 8 | single_anchor_reconnect_pass | 227 |
| synthetic_negative | 0 | invalid_reconnect | 3 |
| synthetic_negative | 0 | multi_attachment_out_of_scope | 1 |

结论:

- clean_positive 40/40 均为 `single_anchor_reconnect_pass`.
- rule_positive 227/227 均为 `single_anchor_reconnect_pass`.
- synthetic_negative 中 3 个为 `invalid_reconnect`, 1 个为 `multi_attachment_out_of_scope`.
- 这些结果说明 reconnect 规则没有误伤 clean original 或 rule_fixed_topology reliable 正样本, 并能区分最小负样本中的断开, floating, missing anchor 和 extra attachment 情况.

DiffSBDD 既有候选重标注结果如下:

| K | candidate_count | single_anchor_reconnect_pass | multi_attachment_out_of_scope | invalid_reconnect |
|---:|---:|---:|---:|---:|
| 8 | 313 | 0 | 44 | 269 |
| 16 | 625 | 0 | 94 | 531 |
| 32 | 1249 | 0 | 194 | 1055 |
| total | 2187 | 0 | 332 | 1855 |

DiffSBDD 2187 条候选中没有 `single_anchor_reconnect_pass`; 其中 332 条为 `multi_attachment_out_of_scope`, 1855 条为 `invalid_reconnect`. 该结果不表示 4.0.1a 改善了 DiffSBDD 生成质量, 只说明在当前 single-anchor R-group repair 语义下, 既有 DiffSBDD conditional 候选的 local reconnect 拓扑表现不稳定.

## 5. Shadow Analysis

`reliable_repair_success` 保持阶段 4.0 / 4.0.1 的 10 项标准. 阶段 4.0.1a 只新增 `strict_single_anchor_shadow_reliable`, 用于观察如果未来把 single-anchor reconnect 作为额外约束会产生什么影响.

| K | candidate_count | reliable_repair_success_count | strict_single_anchor_shadow_reliable_count | multi_attachment_out_of_scope | invalid_reconnect |
|---:|---:|---:|---:|---:|---:|
| 8 | 313 | 10 | 0 | 44 | 269 |
| 16 | 625 | 14 | 0 | 94 | 531 |
| 32 | 1249 | 24 | 0 | 194 | 1055 |
| total | 2187 | 48 | 0 | 332 | 1855 |

原 `reliable_repair_success_count=48`, 但 `strict_single_anchor_shadow_reliable_count=0`.

这不是推翻阶段 4.0 / 4.0.1 的 10 项 reliable repair 标准, 也不是回写历史结果. 它只说明如果未来把 strict single-anchor reconnect 加入更严格的 shadow 口径, 当前 DiffSBDD reliable candidates 会全部被过滤. 因此 local reconnect 更适合作为 diagnostic + soft filter, 暂不适合作为立即回写的 hard filter.

## 6. Field Consistency Audit

`reconnect_rule_field_consistency_audit.md` 对当前 CSV 字段和规则输出做了字段一致性审计. 审计范围包括:

| file | rows |
|---|---:|
| `diffsbdd_reconnect_reclassified.csv` | 2187 |
| `clean_positive_reconnect_check.csv` | 40 |
| `rule_positive_reconnect_check.csv` | 227 |
| `synthetic_negative_reconnect_check.csv` | 4 |
| `visual_qc_reconnect_cases.csv` | 25 |

审计结果:

- total_rows_checked: 2483.
- exact_rule_output_mismatches: 0.
- semantic_invariant_violations: 0.
- multi-fragment or non-single-fragment rows checked: 1237.

该审计证明当前 CSV 中的 `reconnect_category` / `reconnect_category_reason` 与实现规则和关键语义不变量一致. 它不提供额外视觉证据, 也不替代 visual QC.

## 7. Visual QC

visual QC 是阶段 4.0.1a 的收尾抽查, 不是新生成实验, 也不是对 2187 条 DiffSBDD 候选的全量人工标注.

抽样与渲染概况:

- 25 个 unique visual QC 样本.
- sampling groups: 7 个 DiffSBDD reliable strict shadow fail, 6 个 DiffSBDD invalid non-reliable, 6 个 DiffSBDD multi non-reliable, 3 个 clean positive, 3 个 rule positive.
- K 覆盖: K=8 为 14 个, K=16 为 5 个, K=32 为 3 个, K=0 为 3 个.
- 900 张 clear views.
- 75 张 contact sheets.
- 25 张 review panels.
- local PNG 总数 1000, 作为本地运行资产保存在 `runs/phase4_0_1a_visual_qc/`, 未提交 Git.
- camera_quality_counts: 64 个 `camera_quality_good`, 9 个 `camera_quality_usable`, 2 个 `camera_quality_poor`.
- needs_user_review_count: 0.

visual QC 的自动分类分布:

| reconnect_category | count |
|---|---:|
| single_anchor_reconnect_pass | 6 |
| multi_attachment_out_of_scope | 8 |
| invalid_reconnect | 11 |

visual QC 结论:

- clean_positive 3/3 视觉上支持 `single_anchor_reconnect_pass`.
- rule_positive 3/3 视觉上支持 `single_anchor_reconnect_pass`, 未见 reconnect 诊断误伤.
- DiffSBDD `invalid_reconnect` 样本总体显示 floating fragment, not connected to anchor, candidate not single fragment, 或 sanitize invalid 等现象, 与自动分类主结论一致.
- DiffSBDD `multi_attachment_out_of_scope` 样本总体显示 extra attachment, bridge, linker-like topology 或 anchor 多邻接, 与当前 out-of-scope 口径一致.
- `vqc_018` 经用户图像复核确认多个连接点, 支持 `multi_attachment_out_of_scope`.
- `vqc_019` 经图像和 RDKit 连通分量复核确认候选分成两个部分, 按多片段优先规则归为 `invalid_reconnect`.

因此, visual QC 对 reconnect 三分类提供了抽查级支持. 但它仍然是 25-case 抽样证据, 不能写成全量人工标注.

## 8. 最终结论

阶段 4.0.1a 可以正式关闭.

本阶段得到的结论是:

- local reconnect 三分类规则得到正样本校准, synthetic negative 校准, 字段一致性审计和 25-case visual QC 的初步支持.
- clean_positive 和 rule_positive 均通过 single-anchor reconnect, 说明当前规则没有明显误伤基础正样本.
- DiffSBDD 2187 条既有候选在 strict single-anchor R-group repair 语义下均未达到 `single_anchor_reconnect_pass`.
- 原 reliable repair 10 项标准下的 48 个 reliable candidates 在 strict single-anchor shadow 口径下为 0, 说明 10 项标准尚未覆盖 local reconnect 拓扑约束.
- 该结果不推翻阶段 4.0 / 4.0.1 的 10 项 reliable repair 标准, 也不回写历史结果.
- local reconnect 后续建议作为 diagnostic + soft filter, 暂不建议作为 hard filter.
- 不应直接把 local reconnect 加入 reliable repair 10 项标准.
- DiffSBDD conditional 当前候选在 strict single-anchor R-group repair 语义下表现不稳定, 不建议直接作为阶段 4.1 主生成式后端.

本阶段不产生阶段 4.1 结论, 也不声称 4.0.1a 改善了 DiffSBDD 生成质量.

## 9. 下一步建议

### 9.1 审计增强

- 保留本 final report, field consistency audit, shadow analysis 和 visual QC notes 作为阶段 4.0.1a 的关闭证据.
- 后续若需要对外展示, 优先使用轻量 CSV / JSON / Markdown 报告, 不提交 `runs/` 重资产.
- 如需补充图片证据, 应先确认只提交少量代表性 panel, 且不要把它们写成全量人工标注.

### 9.2 规则和映射修补

- 后续可细分 `invalid_reconnect` 子原因, 例如 candidate not readable, sanitize invalid, multi-fragment, anchor mapping fail, floating fragment, not connected to anchor.
- 后续可细分 `multi_attachment_out_of_scope` 子原因, 例如 extra attachment, generated fragment attachment count > 1, anchor neighbor count > 1, bridge/linker-like topology.
- 这些细分能提升解释性, 但不阻塞阶段 4.0.1a 关闭.
- 若未来要把 reconnect 变成 hard filter, 应先扩大 visual QC 或加入更系统的结构审计, 再讨论 reliable repair 标准变更.

### 9.3 新生成实验

- 下一步优先进入 phase4.0.2 DiffDec adapter 3-5 case 预检.
- DiffSBDD postfilter 或 guidance 若继续做, 应单独开新阶段, 不回写 4.0.1a.
- Random / Predicted / Oracle 正式对照不属于阶段 4.0.1a 产出, 如需开展应单独设计阶段.

## 10. 验证结果

本轮 final report 生成流程运行了用户指定验证命令:

| command | result |
|---|---|
| `conda run -n c2f_cpu python -m compileall src scripts` | passed |
| `conda run -n c2f_cpu python -m pytest tests/test_phase4_0_1a_local_reconnect_calibration.py -q` | 4 passed in 0.42s |
| `conda run -n c2f_cpu python -m pytest tests/test_phase4_0_1a_visual_qc.py -q` | 3 passed in 0.48s |
| `conda run -n c2f_cpu python -m pytest -q` | 141 passed in 8.58s |
