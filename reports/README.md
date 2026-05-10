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
- `difficulty_bins.csv`
- `visual_qc_cases.csv`
- `visual_qc_notes.md`
- `phase2_completion_audit.md`

这些报告记录 artificial R-group clash benchmark 的构造尝试, split 统计, 数据质量 gates, visual QC 抽样和最终审计结果.
