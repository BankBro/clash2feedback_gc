# 阶段 2 实验说明与网页版 ChatGPT 分析材料

## 1. 目的

本文档用于让只能阅读 GitHub 代码仓的网页版 ChatGPT 理解本次 Clash2Feedback-GC 阶段 2 实验结果, 并据此分析阶段 2 是否可关闭, 以及阶段 3 或阶段 2.5 的下一步建议。

阶段 2 的目标是构造一个 controlled artificial single-Rgroup clash benchmark。它从阶段 0/1 的 clean complex 出发, 对单个 target R-group 注入局部几何扰动, 生成用于后续 locator/verifier/repair 研究的人工失败样本。

阶段 2 不做以下事情:

- 不接入真实生成模型。
- 不训练 repair 模型。
- 不做 whole-complex minimization。
- 不把 ligand-only energy delta 作为硬过滤条件。
- 不声称人工负样本覆盖真实生成模型失败分布。

## 2. 本次应提交到 GitHub 的材料选择

建议提交并推送以下轻量材料:

- 代码与入口:
  - `scripts/phase2_inject_artificial_clashes.py`
  - `scripts/phase2_render_visual_qc_images.py`
  - `src/clash2feedback/data/phase2_visual_qc.py`
  - `src/clash2feedback/data/render_visual_check.py`
- 配置与文档:
  - `configs/phase2_injection.yaml`
  - `docs/20260510-Clash2Feedback-GC_阶段2人工局部碰撞注入最终落地方案.md`
  - `scripts/README.md`
  - `reports/README.md`
- 阶段 2 结果报告:
  - `reports/phase2_injection/summary.json`
  - `reports/phase2_injection/phase2_completion_audit.md`
  - `reports/phase2_injection/supported_single_rgroup_cases.csv`
  - `reports/phase2_injection/injection_attempts.csv`
  - `reports/phase2_injection/delta_sensitivity.csv`
  - `reports/phase2_injection/energy_delta_stats.csv`
  - `reports/phase2_injection/energy_delta_outliers.csv`
  - `reports/phase2_injection/visual_qc_cases.csv`
  - `reports/phase2_injection/visual_qc_notes.md`
- 阶段 2 visual QC 轻量索引:
  - `reports/phase2_visual_qc/asset_manifest.csv`
  - `reports/phase2_visual_qc/render_manifest.csv`
  - `reports/phase2_visual_qc/contact_sheets.csv`
  - `reports/phase2_visual_qc/by_category_index.csv`
  - `reports/phase2_visual_qc/manual_review_template.csv`
  - `reports/phase2_visual_qc/phase2_visual_qc_render_summary.md`
- 测试:
  - `tests/test_phase2_reports.py`
  - `tests/test_phase2_report_integrity.py`
  - `tests/test_phase2_visual_qc.py`
  - `tests/test_render_visual_check.py`

不建议提交以下重运行产物:

- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/samples/*.pkl`
- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/ligands/*.sdf`
- `runs/phase2_visual_qc/**/*.png`

原因是这些文件体量大, 更适合本地复核或按需抽样发布。当前 GitHub 分析可依赖 reports 中的表格, summary 和 visual QC 结论。

## 3. 核心实验结果

阶段 2 共生成 2610 个 perturbation attempts, 对应 51 个 clean base samples。

主要 oracle split 分布:

| oracle_split | count |
|---|---:|
| supported_single_rgroup | 357 |
| near_miss_contact | 778 |
| duplicate_removed | 739 |
| invalid_conformer | 601 |
| unsupported | 85 |
| global_pose_failure | 48 |
| ambiguous_region | 2 |

supported 主负样本的三种注入方式均有产出:

| injection_mode | supported count |
|---|---:|
| easy_rotation | 117 |
| torsion_perturb | 118 |
| directed_clash | 122 |

supported 主集 gate 结论:

- `ligand_valid = true`: 全部通过。
- ligand internal severe clash: max 0。
- target severe pairs: min 1。
- non-target severe pairs: max 0。
- scaffold severe pairs: max 0。
- target score ratio valid >= 0.7: 全部通过。
- max clash depth <= 1.5 Å: 全部通过。
- split inheritance: 全部 `base_split == derived_split`, 且无 unknown split。

## 4. Visual QC 结论

本次 visual QC 从原 25 个抽样 case 扩展为 32 个 case, 并补充了 7 个 `supported_single_rgroup + torsion_perturb` case, 使 supported visual QC 覆盖三种 injection mode。

视觉复核范围:

- 32 个 case。
- 128 张 contact sheets。
- 1536 张单视角图片。
- 4 类主视图: `ligand_delta`, `overlay_sticks`, `overlay_surface`, `clash_pair_vdw`。

最终状态:

```text
sampled_visual_qc_passed_with_minor_caveats
```

结论:

- supported 主集视觉上符合单一 target R-group 局部 ligand-protein clash。
- scaffold 和 non-target R-groups 在 supported 样本中稳定。
- `easy_rotation`, `torsion_perturb`, `directed_clash` 三种 supported 样本均未发现阻断问题。
- `global_pose_failure` 符合 clash 过深或过强的 hard failure 语义。
- `ambiguous_region` 符合 target 附近但边界归因不够干净的语义。
- `near_miss_contact` 符合 close contact 但无 severe VDW pair 的语义。
- `invalid_conformer` 不像合格 protein clash, 但当前没有 ligand internal self-clash 专用高亮视图。

保留 minor caveats:

- `invalid_conformer` 当前没有 ligand internal self-clash 专用高亮视图。
- invalid visual QC 有两组视觉重复样本: `case_000019`/`case_000029`, `case_000057`/`case_000070`。
- `ambiguous_region` 中 `case_000717` 和 `case_000718` 的 `overlay_surface` 信息量有限。
- `near_miss_contact` 没有 severe VDW pair, 因此 `clash_pair_vdw` 为 background-only。

这些 caveat 不影响 supported 主集质量判断。

## 5. 当前关闭判断

阶段 2 可以关闭为:

```text
closed_for_controlled_phase3_preflight_with_minor_visual_qc_caveats
```

更准确地说, 阶段 2 完成的是一个受控的人工单 R-group 局部碰撞 benchmark。它适合用于阶段 3 的 locator/verifier preflight, 但不应直接推断真实生成模型失败分布。

## 6. 给网页版 ChatGPT 的关键分析问题

建议网页版 ChatGPT 重点回答:

- 阶段 2 的 supported 主集是否足以作为阶段 3 locator/verifier 的 controlled benchmark。
- `easy_rotation`, `torsion_perturb`, `directed_clash` 三种注入方式是否互补, 是否存在明显偏差。
- `near_miss_contact`, `invalid_conformer`, `global_pose_failure`, `ambiguous_region` 应如何用于阶段 3 或阶段 2.5。
- 当前 visual QC 的 minor caveats 是否需要在阶段 3 前修复。
- 是否需要阶段 2.5 来比较真实生成模型失败和人工注入失败之间的分布差距。
- 阶段 3 最小启动集应该如何定义, 例如 Top-1/Top-3 target R-group locator 评估。

## 7. 读者注意

如果网页版 ChatGPT 无法访问本地 PNG, 不应重新判断 visual QC 图像本身, 而应基于 `reports/phase2_visual_qc/*.csv`, `phase2_visual_qc_render_summary.md`, `visual_qc_notes.md` 和 `phase2_completion_audit.md` 中的记录进行二次分析。
