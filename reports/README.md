# reports

## 1. 目录说明

本目录只放运行生成的报告, 不放人工维护的方案文档.

## 2. 阶段 0 报告

`reports/phase0/` 由阶段 0 CLI 生成:

- `dataset_check.csv`
- `failed_cases.csv`
- `summary.json`
- `threshold_calibration.csv`
- `failure_reason_counts.csv`
- `visual_check_list.csv`
- `manual_check_template.csv`

阶段 0 可视化抽查的大图和软件脚本默认放入 `runs/phase0_visual_check/`. 轻量人工检查结论写入 `tmp/YYYYMMDD/phase0-visual-check-notes.md`.

## 3. 阶段 1 报告

`reports/phase1_clash_detector/` 由阶段 1 CLI 生成:

- `summary.json`
- `clean_clash_report.csv`
- `balanced_clash_report.csv`
- `threshold_sensitivity.csv`
- `rgroup_attribution_report.csv`
- `failure_type_counts.csv`
- `verifier_smoke_report.csv`
- `unsupported_cases.csv`
- `vdw_radius_table.json`
- `strict_delta_false_positive_cases.csv`
- `nonsevere_contact_stats.csv`
- `scope_comparison.csv`
- `phase1_final_report.md`

这些文件是 detector calibration, threshold sensitivity 和 verifier smoke 的运行报告, 不替代 `docs/` 中的方案文档.

## 4. 阶段 2 报告

`reports/phase2_injection/` 由阶段 2 CLI 生成:

- `summary.json`
- `injection_attempts.csv`
- `base_clean_filter_report.csv`
- `supported_single_rgroup_cases.csv`
- `reject_cases.csv`
- `invalid_conformer_cases.csv`
- `unsupported_cases.csv`
- `duplicate_cases.csv`
- `near_miss_cases.csv`
- `delta_sensitivity.csv`
- `energy_delta_stats.csv`
- `energy_delta_outliers.csv`
- `difficulty_bins.csv`
- `visual_qc_cases.csv`
- `visual_qc_notes.md`
- `phase2_completion_audit.md`

这些报告记录 artificial R-group clash benchmark 的构造尝试, split 统计, 数据质量 gates, energy_delta record-only 诊断, visual QC 待人工检查清单和最终审计结果.

`reports/phase2_visual_qc/` 由 `scripts/phase2_render_visual_qc_images.py` 生成:

- `asset_manifest.csv`
- `render_manifest.csv`
- `contact_sheets.csv`
- `by_category_index.csv`
- `manual_review_template.csv`
- `phase2_visual_qc_render_summary.md`

这些文件索引 `runs/phase2_visual_qc/` 下的 ChimeraX PNG/contact sheet 运行产物, 用于人工 visual QC 判读. 默认 contact sheets 覆盖四类主视图: `ligand_delta`, `overlay_sticks`, `overlay_surface`, `clash_pair_vdw`; `overlay_surface` 会为原始和失败 target R-group 原子叠加小球 marker, `overlay_sticks` 会用不同颜色区分配体侧碰撞点, 蛋白侧碰撞点和中心连线. 颜色词典在所有视图间保持一致: target failed 为青色, target displacement 为绿色, 配体碰撞为红色, 蛋白碰撞为蓝色, 碰撞连线为深灰色. `by_category_index.csv` 对应 `runs/phase2_visual_qc/by_oracle_split/`, `by_injection_mode/`, `by_oracle_split_and_mode/` 三套软链接索引, 用来按 oracle split 和 injection mode 快速浏览 case. `clash` 和 `rgroup` 可作为可选调试视图. 默认每类先采样 1024 个候选方向, 再选 12 个 clear-view; 候选数记录在 `asset_manifest.csv` 和 `render_manifest.csv` 的 `candidate_directions` 列. R 基位移线中点记录在 `render_manifest.csv` 的 `camera_target` 列, 相机视线与位移线的无方向夹角记录在 `displacement_axis_angle_degrees` 和 `displacement_axis_angle_gate_pass` 列, 合格范围为 30 到 90 度. 自动渲染不替代人工 pass/fail 结论.

## 5. 阶段 2.5 报告

`reports/phase2_5_model_induced_audit/` 由阶段 2.5 CLI 生成:

- `summary.json`
- `external_setup.json`
- `training_overlap_audit.csv`
- `training_overlap_summary.json`
- `base_pocket_selection.csv`
- `generation_manifest.parquet`
- `ligand_validity.csv`
- `model_induced_clash_report.csv`
- `failure_taxonomy.csv`
- `repairability_proxy.csv`
- `artificial_vs_model_induced_gap.csv`
- `visual_qc_cases.csv`
- `visual_qc_notes.md`
- `phase2_5_audit.md`
- `phase2_5_completion_audit.md`

这些报告记录 frozen generation baseline 的 external validity audit. `external_setup.json` 记录 DiffSBDD 仓库 commit, checkpoint hash, `diffsbdd` 环境检查, GPU 和 smoke test. 若 DiffSBDD 仓库, checkpoint, official split, GPU 或生成数据缺失, 报告必须明确 blocked 原因, 且不得把 predicted dominant R-group 当 oracle ground truth.
