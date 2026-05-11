# 发给网页版 ChatGPT 的阶段 2 分析 Prompt

## 1. 仓库定位

- GitHub 仓库: `BankBro/clash2feedback_gc`
- 仓库 URL: `https://github.com/BankBro/clash2feedback_gc`
- 分支: `20260510-102739-phase2-implementation`
- 阶段 2 实验内容提交: `391dfd4157412aa8d0bacf8aaf0ce95c68d78abd`
- 本 prompt 的用途: 让网页版 ChatGPT 基于 GitHub 仓库内可见代码和轻量 reports, 分析阶段 2 实验结果并给出下一步建议。

注意: 批量 PNG, pkl 和 SDF 运行产物未提交到 GitHub。请不要假设能直接看到本地三维图片或 raw benchmark 样本; 需要基于报告表格, summary 和 visual QC 记录进行分析。

## 2. 建议网页版 ChatGPT 先阅读的文件

请按以下顺序阅读:

1. 阶段 2 方案与入口:
   - `docs/20260510-Clash2Feedback-GC_阶段2人工局部碰撞注入最终落地方案.md`
   - `configs/phase2_injection.yaml`
   - `scripts/phase2_inject_artificial_clashes.py`
   - `scripts/phase2_render_visual_qc_images.py`
2. 阶段 2 核心结果:
   - `reports/phase2_injection/summary.json`
   - `reports/phase2_injection/phase2_completion_audit.md`
   - `reports/phase2_injection/supported_single_rgroup_cases.csv`
   - `reports/phase2_injection/injection_attempts.csv`
   - `reports/phase2_injection/delta_sensitivity.csv`
   - `reports/phase2_injection/energy_delta_stats.csv`
   - `reports/phase2_injection/energy_delta_outliers.csv`
3. Visual QC 结果:
   - `reports/phase2_injection/visual_qc_cases.csv`
   - `reports/phase2_injection/visual_qc_notes.md`
   - `reports/phase2_visual_qc/asset_manifest.csv`
   - `reports/phase2_visual_qc/render_manifest.csv`
   - `reports/phase2_visual_qc/contact_sheets.csv`
   - `reports/phase2_visual_qc/by_category_index.csv`
   - `reports/phase2_visual_qc/manual_review_template.csv`
   - `reports/phase2_visual_qc/phase2_visual_qc_render_summary.md`
4. 本次实验说明:
   - `tmp/20260511/20260511-phase2-experiment-summary-for-web-chatgpt.md`
   - `tmp/20260510/20260510-phase2-closure-summary.md`
5. 相关测试:
   - `tests/test_phase2_reports.py`
   - `tests/test_phase2_report_integrity.py`
   - `tests/test_phase2_visual_qc.py`
   - `tests/test_render_visual_check.py`

## 3. 可直接发送给网页版 ChatGPT 的完整 Prompt

```text
请阅读 GitHub 仓库 `BankBro/clash2feedback_gc`, 分支 `20260510-102739-phase2-implementation`, 阶段 2 实验内容提交 `391dfd4157412aa8d0bacf8aaf0ce95c68d78abd`。

请重点阅读以下文件:

- `tmp/20260511/20260511-phase2-experiment-summary-for-web-chatgpt.md`
- `reports/phase2_injection/summary.json`
- `reports/phase2_injection/phase2_completion_audit.md`
- `reports/phase2_injection/supported_single_rgroup_cases.csv`
- `reports/phase2_injection/injection_attempts.csv`
- `reports/phase2_injection/delta_sensitivity.csv`
- `reports/phase2_injection/energy_delta_stats.csv`
- `reports/phase2_injection/energy_delta_outliers.csv`
- `reports/phase2_injection/visual_qc_cases.csv`
- `reports/phase2_injection/visual_qc_notes.md`
- `reports/phase2_visual_qc/asset_manifest.csv`
- `reports/phase2_visual_qc/render_manifest.csv`
- `reports/phase2_visual_qc/contact_sheets.csv`
- `reports/phase2_visual_qc/by_category_index.csv`
- `reports/phase2_visual_qc/manual_review_template.csv`
- `reports/phase2_visual_qc/phase2_visual_qc_render_summary.md`
- `scripts/phase2_inject_artificial_clashes.py`
- `scripts/phase2_render_visual_qc_images.py`
- `src/clash2feedback/data/phase2_visual_qc.py`
- `tests/test_phase2_visual_qc.py`

背景:

本项目阶段 2 构造 controlled artificial single-Rgroup clash benchmark。它从 clean complex 出发, 对单个 target R-group 注入局部扰动, 生成人工失败样本。阶段 2 不接真实生成模型, 不训练 repair, 不做 whole-complex minimization, 不把 ligand-only energy delta 作为硬过滤条件。

核心结果:

- total attempts: 2610。
- supported_single_rgroup: 357。
- supported injection modes: `easy_rotation` 117, `torsion_perturb` 118, `directed_clash` 122。
- supported gate: ligand valid, ligand internal severe clash 0, target severe >= 1, non-target severe 0, scaffold severe 0, target score ratio valid >= 0.7, max clash depth <= 1.5 Å, split inheritance pass。
- sampled visual QC: 32 cases, 128 contact sheets, status `sampled_visual_qc_passed_with_minor_caveats`。

请完成以下分析:

1. 判断阶段 2 是否可以作为 controlled benchmark 正式关闭, 并说明证据和限制。
2. 分析 `easy_rotation`, `torsion_perturb`, `directed_clash` 三种人工注入方式是否互补, 是否存在偏差。
3. 分析 supported 主集, near_miss_contact, invalid_conformer, global_pose_failure, ambiguous_region 各自应如何用于阶段 3 或阶段 2.5。
4. 评估 visual QC 的 minor caveats 是否需要在阶段 3 前修复:
   - invalid_conformer 没有 ligand internal self-clash 专用高亮视图。
   - invalid 抽样有两组视觉重复。
   - ambiguous_region 部分 surface 视图信息量有限。
   - near_miss_contact 没有 severe VDW pair, `clash_pair_vdw` 为 background-only。
5. 给出阶段 3 locator/verifier preflight 的最小实验设计:
   - 数据 split。
   - Top-1/Top-3 target R-group 指标。
   - reject/near_miss/invalid/global/ambiguous 的使用方式。
   - 必要的 sanity checks。
6. 给出阶段 2.5 external validity audit 的建议, 重点比较真实生成模型失败样本与人工注入失败样本的分布差距。
7. 明确指出哪些结论不能从阶段 2 推出, 避免过度解释。

请输出结构化中文分析, 包含:

- 总体结论。
- 关键证据。
- 主要风险和 caveats。
- 阶段 3 最小启动方案。
- 阶段 2.5 建议。
- 需要补充的数据或实验。
```

## 4. 简要 Prompt

```text
请阅读 GitHub 仓库 `BankBro/clash2feedback_gc`, 分支 `20260510-102739-phase2-implementation`, 阶段 2 实验提交 `391dfd4157412aa8d0bacf8aaf0ce95c68d78abd`。重点看 `tmp/20260511/20260511-phase2-experiment-summary-for-web-chatgpt.md`, `reports/phase2_injection/summary.json`, `reports/phase2_injection/phase2_completion_audit.md`, `reports/phase2_injection/visual_qc_notes.md`, `reports/phase2_visual_qc/*.csv`, `scripts/phase2_inject_artificial_clashes.py`, `scripts/phase2_render_visual_qc_images.py`。请分析阶段 2 controlled artificial single-Rgroup clash benchmark 是否可以关闭, visual QC caveats 是否阻断阶段 3, 并给出阶段 3 locator/verifier preflight 和阶段 2.5 external validity audit 的下一步实验建议。
```
