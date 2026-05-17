# Phase 4.0.1a Visual QC 人工可视化抽查执行计划

> 任务短名: `phase4-0-1a-visual-qc`  
> 计划日期: 2026-05-17  
> 文档定位: `/goal` 执行前的本地执行计划.  
> 本计划只规划执行路径, 不代表已完成 visual QC 渲染或人工检视.

## 1. 仓库事实核查

- 本地仓库: `/home/lyj/mnt/project/clash2feedback_gc`.
- 当前分支: `20260517-161211-phase4-0-1a`.
- 当前 HEAD commit: `6f5a882e4cf6ce114c233184adcc2ee622dbd940`.
- `git status --short --untracked-files=all`: 主仓库无输出, 当前工作区 clean.
- 方案文档存在: `docs/20260517-Clash2Feedback-GC_阶段4.0.1a局部接回诊断规则校准方案总纲.md`.
- 阶段 4.0.1a 已有结果目录存在: `reports/phase4_0_1a_local_reconnect_calibration/`.
- 已确认存在阶段 4.0.1a 关键结果文件:
  - `local_reconnect_calibration_summary.json`.
  - `local_reconnect_category_counts.csv`.
  - `reconnect_shadow_reliable_analysis.csv`.
  - `diffsbdd_reconnect_reclassified.csv`.
  - `clean_positive_reconnect_check.csv`.
  - `rule_positive_reconnect_check.csv`.
  - `synthetic_negative_reconnect_check.csv`.
  - `phase4_0_1a_completion_audit.md`.
- 当前 visual QC 环境能力:
  - `/usr/bin/chimerax` 存在.
  - `chimerax --version`: UCSF ChimeraX `1.11.1`.
  - `chimerax --nogui --offscreen --exit` 成功.
  - `conda run -n c2f_cpu python -c "from PIL import Image"` 成功, Pillow 可用.
- 外部仓状态仅作背景:
  - `external/DiffSBDD` 当前分支为 `clash2feedback_gc`, 有 untracked pycache/checkpoint.
  - `external/DiffDec` 当前分支为 `master`, 有 tracked pycache 修改.
  - 本任务禁止修改 `external/`, 只读取主仓库阶段结果和本地候选文件.

## 2. 字段 / 实现映射

### 2.1. 直接读取字段

从 `reports/phase4_0_1a_local_reconnect_calibration/diffsbdd_reconnect_reclassified.csv`, `clean_positive_reconnect_check.csv`, `rule_positive_reconnect_check.csv` 直接读取:

- 样本和候选标识: `case_id`, `base_sample_id`, `candidate_id`, `candidate_index`, `candidate_path`, `candidate_budget_k`, `source_group`.
- reconnect 三分类: `reconnect_category`, `reconnect_category_reason`, `strict_single_anchor_shadow_reliable`.
- reconnect 原始诊断: `local_reconnect_pass`, `local_reconnect_failure_reason`, `anchor_reconnect_status`, `anchor_reconnect_reason`, `anchor_match_success`, `generated_fragment_connected_to_anchor`, `generated_fragment_attachment_count`, `num_anchor_neighbors`, `num_extra_attachments`, `floating_fragment_detected`.
- reliable repair 相关字段: `candidate_readable`, `ligand_valid`, `fixed_structure_match_success`, `anchor_integrity`, `old_clash_resolved`, `no_new_severe_clash`, `scaffold_stable`, `keep_region_stable`, `edit_compliance`, `pocket_retention`, `reliable_repair_success`.
- fragment 映射字段: `fixed_structure_mapping_success_for_diagnostics`, `fixed_structure_mapping_reason`, `generated_atom_indices_json`, `target_mask_heavy_atom_count`, `generated_fragment_heavy_atom_count`, `candidate_total_fragment_count`, `candidate_single_fragment`, `candidate_extra_fragment_count`, `anchor_candidate_idx`.

### 2.2. 可无歧义恢复字段

- `original_ligand_sdf`, `failed_ligand_sdf`, `phase2_sample_path`: 通过 `reports/phase4_0_1_diffsbdd_conditional_repair/selected_cases.csv` 结合 `data/benchmarks/clashrepairbench_rg_artificial/v0_1/manifest.parquet` 恢复.
- `protein_pocket.pdb`: 从 `data/processed/v0_1/complexes/{base_sample_id}.pkl` 的 pocket atom indices 和 protein 坐标写出到 `runs/phase4_0_1a_visual_qc/...`.
- `scaffold_atoms.pdb`, `keep_atoms.pdb`: 从 `oracle_keep_atom_indices`, processed sample scaffold 信息和 failed/candidate 坐标恢复.
- `generated_fragment_atoms.pdb`: 从 `generated_atom_indices_json` 和 candidate SDF 坐标恢复.
- `anchor_atoms.pdb` / `expected_anchor.bild`: 从 `oracle_anchor_scaffold_atom_idx`, `oracle_anchor_rgroup_atom_idx`, `anchor_candidate_idx` 和 failed/candidate 坐标恢复.
- `actual_attachment_bonds.bild` 和 `extra_attachment_bonds.bild`: 读取 candidate SDF RDKit graph, 结合 generated atom set 与 keep atom set 计算 actual anchor attachment 和 extra attachment.
- `close_contacts.bild`, `protein_pocket_vdw_atoms.pdb`, `ligand_vdw_atoms.pdb`: 对 candidate 坐标运行现有 clash/close-contact 几何逻辑或阶段 0 visual asset 辅助逻辑生成.

### 2.3. 低风险适配点

- 阶段 4.0.1a 现有 summary/audit 中记录的是生成当时的旧 HEAD 和当时 dirty 状态; 当前仓库 HEAD 已推进到 `6f5a882e...`. visual QC 汇报应同时记录“输入文件 provenance 中的旧 HEAD”和“本次 visual QC 执行时 HEAD”, 不视作实验口径冲突.
- DiffSBDD invalid reconnect 中没有 `anchor_not_mapped` / `anchor_match_success=false` 样本. 抽样时覆盖 `not_connected_to_anchor`, `floating_fragment`, `ligand_valid=false` 等当前真实 failure reason; 在 `fallback_reason` 中记录 `anchor_not_mapped_not_available_in_diffsbdd_candidates`.
- 用户已确认 25 个样本总数优先, 因原始配额 `3+3+6+6+8=26`, 执行时将 reliable strict shadow fail 类取 7 个.

## 3. docs 总纲补充方案

修改文件:

- `docs/20260517-Clash2Feedback-GC_阶段4.0.1a局部接回诊断规则校准方案总纲.md`.

建议补充位置:

- 在“阶段边界 / 做与不做”附近新增 visual QC 边界.
- 在“三分类定义”或其后新增 visual QC 与 reconnect 三分类的关系.
- 在“完成条件 / 关闭口径”附近新增 visual QC 收尾判据.

必须写清楚:

- visual QC 是阶段 4.0.1a 的收尾补充, 不是新生成实验.
- 不重跑 DiffSBDD, 不重新生成候选, 不训练或微调模型.
- 不修改 reliable repair 10 项标准.
- 不把 local reconnect 加入 reliable repair 标准.
- 不回写阶段 4.0 或 4.0.1 历史结果.
- visual QC 目标是检查 reconnect 三分类和真实三维结构观察是否一致.
- `multi_attachment_out_of_scope` 不等于 ligand invalid, 只表示超出当前 single-anchor R-group repair 范围.
- 若人工 / Codex 图像检视基本支持自动分类, 阶段 4.0.1a 可正式关闭.
- 若发现大量不一致, 应先修 reconnect / mapping 诊断, 不得强行关闭为正结果.
- 如果 Codex 环境无法查看图片, 不编造视觉结论, 只生成图片, 索引和人工 review 模板.

## 4. 25 个 visual QC 样本抽样规则

总数固定为 25, 配额如下:

- `clean_positive`: 3 个.
- `rule_positive`: 3 个.
- `diffsbdd_invalid_non_reliable`: 6 个.
- `diffsbdd_multi_non_reliable`: 6 个.
- `diffsbdd_reliable_strict_shadow_fail`: 7 个.

可用样本数核查:

- clean positive: 40 条.
- rule positive: 227 条.
- DiffSBDD invalid reconnect 非 reliable: 1620 条.
- DiffSBDD multi attachment 非 reliable: 519 条.
- DiffSBDD 原 reliable 且 strict shadow fail: 48 条.

抽样优先级:

1. 先选 `diffsbdd_reliable_strict_shadow_fail`, 因为若同一候选满足多个类别, 优先归入该类.
2. 再选 `diffsbdd_invalid_non_reliable`.
3. 再选 `diffsbdd_multi_non_reliable`.
4. 最后选 clean / rule positive.

多样性要求:

- 尽量覆盖 `candidate_budget_k` = 8, 16, 32.
- invalid 类尽量覆盖 `not_connected_to_anchor`, `floating_fragment`, `ligand_valid=false`.
- multi 类尽量覆盖不同 `num_extra_attachments`, 包括 1, 2, 3, 4, 5+.
- reliable strict shadow fail 类尽量覆盖 K=8/16/32 和 `extra_attachments=1/2/3+`, 以及少量 floating 或 anchor_neighbor_count 异常.
- 尽量保证 25 个 `candidate_id` 唯一.
- 若不足或重复, 在 `visual_qc_reconnect_cases.csv` 写入 `duplicate_of`, `fallback_reason`, `sampling_reason`.

## 5. 三类视图实现方案

每个候选生成 3 类 contact sheet, 每类默认 3 x 4, 共 12 个 clear views:

- `reconnect_clash_contact_sheet.png`.
- `reconnect_anchor_topology_contact_sheet.png`.
- `reconnect_before_after_overlay_contact_sheet.png`.

运行资产目录:

- `runs/phase4_0_1a_visual_qc/<case_id>/<safe_candidate_id>/images/`.
- 同级目录写入 `scripts/`, `assets/`, `case_metadata.json`.

### 5.1. reconnect_clash

用途: 只回答 candidate 在 protein pocket 中是否仍有明显 close contact / clash / 空间异常.

风格要求:

- 尽量复用阶段 0 `clash_contact_sheet.png` 的白底, soft lighting, 3 x 4 contact sheet, 12 clear views.
- candidate ligand 用橙色 stick.
- protein / pocket 用灰色, 半透明或阶段 0 clash view 近似风格.
- protein close-contact atoms 和 ligand close-contact atoms 用 sphere.
- 使用 `close_contacts.bild` 或等价 BILD 标记.
- 不塞入 anchor / scaffold / generated fragment 的大量标记.

### 5.2. reconnect_anchor_topology

用途: 检查 generated fragment 是否接回 anchor, 是否 floating, 是否 multi-attachment, extra attachment 是否真实.

显示建议:

- keep / scaffold atoms: 灰色或蓝色 stick.
- generated fragment: 橙色或黄色高亮.
- anchor scaffold atom: 紫色大球.
- expected anchor region: 紫色标记.
- actual attachment bonds: 绿色高亮.
- extra attachment bonds: 红色高亮.
- floating fragment: 红色或黄色醒目标记.
- protein 默认隐藏或极淡化.

### 5.3. reconnect_before_after_overlay

用途: 检查 candidate 相对 failed / original 的局部变化和 strict shadow fail 的原因.

显示建议:

- failed ligand: 半透明红色或粉色 stick.
- candidate ligand: 橙色 stick.
- original clean ligand: 可选淡蓝色或灰色透明 stick.
- scaffold / keep atoms: 蓝色或灰色高亮.
- generated fragment: 黄色或橙色高亮.
- anchor: 紫色球.
- protein 可隐藏或只保留淡化 pocket surface.

## 6. 视角 / 相机复用方案

复用现有能力:

- `src/clash2feedback/data/render_visual_check.py` 中的 `select_clear_camera_views`, `CameraView`, clear-view scoring, contact sheet 拼图.
- `src/clash2feedback/data/phase2_visual_qc.py` 中的 grouped ChimeraX 脚本, legend/contact sheet 样式, overlay 思路.

适配方式:

- `reconnect_clash`: 使用 `view_proxy="clash"` 选择相机; interest coords 为 close-contact coords + candidate ligand coords. close contacts 不存在时退回 candidate ligand-centered.
- `reconnect_anchor_topology`: 使用 `view_proxy="rgroup"` 选择相机; interest coords 为 anchor + generated fragment + actual/extra attachment atoms.
- `reconnect_before_after_overlay`: 使用 ligand/union proxy, focus 为 candidate ligand + failed ligand + generated fragment 的共同中心; multi-attachment case 优先选择能同时看到多个 attachment 的角度.
- 新模块中可写最小 retarget 逻辑, 不修改阶段 0/2 原有语义.

## 7. 相机质量评估和迭代重渲染策略

第一轮:

- 自动生成 12 个 clear views.
- 写入 `visual_qc_render_manifest.csv`, 包含 camera score, selection tier, occlusion metrics, render status.

质量标记:

- `camera_quality_good`: 关键结构清楚, 多数 clear views 可判断.
- `camera_quality_usable`: 个别遮挡, 但足够判断.
- `camera_quality_poor`: 关键结构部分遮挡, 需要谨慎或重渲染.
- `camera_quality_failed`: 渲染失败或无法判断.

重渲染策略:

- clash 视图: 调整 interest coords 为 close_contacts + candidate ligand; 必要时降低 protein opacity.
- anchor_topology 视图: 调整 interest coords 为 anchor + generated fragment + attachment atoms; 必要时隐藏 protein.
- before_after_overlay 视图: 调整 interest coords 为 candidate + failed + generated fragment; 必要时只显示 ligand overlay.
- 如果 anchor / extra attachment 仍看不清, 允许生成额外 zoom-in clear views.
- 每次重渲染记录 `retry_count`, `camera_adjustment_reason`, `final_camera_selection_status`.
- 对 `camera_quality_poor` 或 `camera_quality_failed` 样本, `manual_visual_label` 必须标记 `needs_further_review` 或 `manual_visual_confidence=low`.

## 8. 预计新增和修改文件

允许新增 / 修改:

- `docs/20260517-Clash2Feedback-GC_阶段4.0.1a局部接回诊断规则校准方案总纲.md`.
- `configs/phase4_0_1a_visual_qc.yaml`.
- `scripts/phase4_0_1a_visual_qc.py`.
- `src/clash2feedback/repair/reconnect_visual_qc.py`.
- `tests/test_phase4_0_1a_visual_qc.py`.
- `reports/phase4_0_1a_local_reconnect_calibration/visual_qc_reconnect_cases.csv`.
- `reports/phase4_0_1a_local_reconnect_calibration/visual_qc_reconnect_notes.md`.
- `reports/phase4_0_1a_local_reconnect_calibration/phase4_0_1a_visual_qc_summary.json`.
- `reports/phase4_0_1a_local_reconnect_calibration/visual_qc_render_manifest.csv`.
- `reports/phase4_0_1a_local_reconnect_calibration/visual_qc_contact_sheets.csv`.
- `reports/phase4_0_1a_local_reconnect_calibration/manual_review_template.csv`.
- `tmp/20260517/phase4-0-1a-visual-qc-expt-report.md`.
- `tmp/20260517/phase4-0-1a-visual-qc-codex-goal-exec-plan.md`.
- 相关 `README.md`, 若目录结构或使用方式变化.

允许生成但默认不提交:

- `runs/phase4_0_1a_visual_qc/` 下 PNG, SDF, PDB, BILD, CXC, metadata.

禁止修改:

- 用户列出的 phase2/phase2.5/phase3/phase4.0/phase4.0.1 历史主结果.
- `reports/phase3_label_provenance_audit/phase4_mask_seed.csv`.
- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/`.
- `external/DiffSBDD/`.
- `external/DiffDec/`.

## 9. 测试计划

计划运行:

```bash
conda run -n c2f_cpu python -m compileall src scripts
conda run -n c2f_cpu python -m pytest tests/test_phase4_0_1a_local_reconnect_calibration.py -q
conda run -n c2f_cpu python -m pytest tests/test_phase4_0_1a_visual_qc.py -q
conda run -n c2f_cpu python -m pytest tests/test_render_visual_check.py -q
conda run -n c2f_cpu python -m pytest -q
```

新增测试点:

- 25 样本抽样配额正确, 总数为 25.
- `diffsbdd_reliable_strict_shadow_fail` 优先级高于其他 DiffSBDD 类.
- `multi_attachment_out_of_scope` 不被写成 ligand invalid.
- 缺失 `anchor_not_mapped` DiffSBDD 样本时写入 fallback reason.
- contact sheet 路径字段和 manifest schema 完整.
- camera quality 枚举合法.
- summary 不修改 reliable repair 10 项标准.

若 ChimeraX, 图形环境或依赖不可用导致部分渲染/测试无法运行, 必须在临时汇报中如实记录原因.

## 10. 禁止修改范围核查方式

执行前记录:

```bash
git status --short --untracked-files=all
git rev-parse HEAD
git branch --show-current
```

执行后核查:

```bash
git diff --name-only
git status --short --untracked-files=all
```

必须确认 diff 不包含:

- `reports/phase2_injection/`.
- `reports/phase2_5_model_induced_audit/`.
- `reports/phase3_label_provenance_audit/phase4_mask_seed.csv`.
- `reports/phase3_label_provenance_audit/summary.json`.
- `reports/phase3_label_provenance_audit/phase3_final_experiment_report.md`.
- `reports/phase4_0_backend_feasibility/phase4_0_final_experiment_report.md`.
- `reports/phase4_0_backend_feasibility/backend_comparison.csv`.
- `reports/phase4_0_backend_feasibility/backend_comparison_rates.csv`.
- `reports/phase4_0_backend_feasibility/candidate_manifest.csv`.
- `reports/phase4_0_backend_feasibility/verifier_outcome.csv`.
- `reports/phase4_0_backend_feasibility/phase4_0_small_scale_summary.json`.
- `reports/phase4_0_1_diffsbdd_conditional_repair/phase4_0_1_summary.json`.
- `reports/phase4_0_1_diffsbdd_conditional_repair/diffsbdd_budget_curve.csv`.
- `reports/phase4_0_1_diffsbdd_conditional_repair/diffsbdd_failure_funnel.csv`.
- `reports/phase4_0_1_diffsbdd_conditional_repair/diffsbdd_verifier_outcome.csv`.
- `reports/phase4_0_1_diffsbdd_conditional_repair/diffsbdd_candidate_manifest.csv`.
- `reports/phase4_0_1_diffsbdd_conditional_repair/diffsbdd_anchor_reconnect_audit.csv`.
- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/`.
- `external/DiffSBDD/`.
- `external/DiffDec/`.

`runs/phase4_0_1a_visual_qc/` 可生成, 但默认不纳入提交.

## 11. 冲突项和阻塞项

当前未发现必须阻断执行的高风险冲突.

低风险差异:

- 25 样本数与原始分组配额 26 的差异: 用户已确认采用 25 个样本, reliable strict shadow fail 类取 7 个.
- 现有 4.0.1a summary/audit 记录旧 HEAD: 作为输入 provenance 保留, visual QC 另记本次执行 HEAD.
- DiffSBDD invalid 样本没有 `anchor_not_mapped`: 在抽样表中记录 fallback reason, 不伪造样本.

潜在阻塞:

- 如果候选 SDF 无法读取或缺失, 对应候选不能进入 visual QC, 需按抽样规则替补并记录.
- 如果 ChimeraX headless 渲染失败, 生成 conflict/blocker 说明, 不编造图片结论.
- 如果 Codex 当前无法查看 PNG, 只生成图片, 索引和人工 review 模板, 临时汇报必须标明不能下视觉结论.

若发现高风险实验口径冲突, 先生成:

- `tmp/20260517/phase4-0-1a-visual-qc-conflict-report.md`.

冲突报告需包含: 冲突项, 方案文档表述, 仓库实际情况, 涉及文件, 影响范围, 建议处理方式, 是否需要人工确认.

## 12. 后续 /goal 目标和成功标准

### 12.1. /goal 目标

在不重跑 DiffSBDD, 不重新生成候选, 不修改 reliable repair 10 项标准, 不回写阶段 4.0/4.0.1 历史结果的前提下, 为阶段 4.0.1a 新增并执行 25 个样本的 visual QC 人工可视化抽查收尾流程, 生成可追溯的抽样表, 渲染 manifest, contact sheet 索引, 人工/Codex 检视记录和临时实验汇报, 用于判断 reconnect 三分类是否与真实三维结构观察一致.

### 12.2. 成功标准

- 方案文档已补充 visual QC 收尾方案和边界.
- 生成 `visual_qc_reconnect_cases.csv`, 且 25 个候选抽样分布符合确认口径: 3 clean, 3 rule, 6 invalid non reliable, 6 multi non reliable, 7 reliable strict shadow fail.
- 每个候选都有 3 类视图路径字段: clash, anchor topology, before/after overlay.
- 成功生成或明确记录失败原因的 render manifest 和 contact sheet index.
- 相机质量, retry count, adjustment reason, final status 均有记录.
- 若图片可查看, Codex 完成 25 个候选逐类图片检视, 填写 manual label/confidence/notes; 若不可查看, 明确写明阻塞且不编造视觉结论.
- 生成 `tmp/20260517/phase4-0-1a-visual-qc-expt-report.md`, 且明确它是临时实验汇报, 不是 final report.
- 测试计划中的可运行测试完成并记录结果; 不可运行项记录真实原因.
- 禁止修改范围未被改动.
- 不提交 `runs/` 下重资产图片/SDF/BILD/CXC, 除非用户另行确认.
- 提交并推送当前分支, commit message 使用 `phase4.0.1a visual qc reconnect review`.
