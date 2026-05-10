# 网页 ChatGPT Prompt: 阶段 2 结果分析与阶段 2.5 实验建议

请你阅读 GitHub 仓库并基于当前代码和报告进行分析。

## 1. 仓库信息

```text
Repository: BankBro/clash2feedback_gc
Branch: 20260510-102739-phase2-implementation
Commit: 295e4947aec4cdcf77e3d22fc76fa5d7af4029c6
```

本次分析只讨论阶段 2 和阶段 2.5。阶段 2.5 还没有实施, 请不要假设已有阶段 2.5 实验结果。

## 2. 请重点阅读的文件

阶段 2 方案和实验汇报:

```text
docs/20260510-Clash2Feedback-GC_阶段2人工局部碰撞注入最终落地方案.md
tmp/20260510/20260510-phase2-experiment-report.md
reports/phase2_injection/phase2_completion_audit.md
reports/phase2_injection/summary.json
```

阶段 2 结果数据:

```text
reports/phase2_injection/injection_attempts.csv
reports/phase2_injection/supported_single_rgroup_cases.csv
reports/phase2_injection/reject_cases.csv
reports/phase2_injection/invalid_conformer_cases.csv
reports/phase2_injection/unsupported_cases.csv
reports/phase2_injection/duplicate_cases.csv
reports/phase2_injection/near_miss_cases.csv
reports/phase2_injection/difficulty_bins.csv
reports/phase2_injection/delta_sensitivity.csv
reports/phase2_injection/visual_qc_cases.csv
data/benchmarks/clashrepairbench_rg_artificial/v0_1/manifest.parquet
data/benchmarks/clashrepairbench_rg_artificial/v0_1/schema.json
```

阶段 2 实现:

```text
configs/phase2_injection.yaml
scripts/phase2_inject_artificial_clashes.py
src/clash2feedback/perturb/
tests/test_phase2_rotation.py
tests/test_phase2_ligand_validity.py
tests/test_phase2_anchor_integrity.py
tests/test_phase2_labels.py
tests/test_phase2_no_leakage.py
tests/test_phase2_reports.py
```

阶段 0/1 背景:

```text
docs/20260508-Clash2Feedback-GC_阶段1碰撞检测器与可靠验证器方案.md
reports/phase1_clash_detector/summary.json
README.md
```

## 3. 阶段 2 已知结果摘要

阶段 2 已完成 `ClashRepairBench-RG-artificial` controlled synthetic failed pose benchmark 构造。

核心结果:

```text
base clean samples: 51 / 51
total injection attempts: 2610
manifest: 2610 rows x 70 columns
supported_single_rgroup: 357
compileall: pass
pytest: 74 passed
```

split 分布:

```text
supported_single_rgroup: 357
near_miss_contact: 778
duplicate_removed: 739
invalid_conformer: 601
unsupported: 85
global_pose_failure: 48
ambiguous_region: 2
```

supported 主集按注入方式:

```text
easy_rotation: 117
torsion_perturb: 118
directed_clash: 122
```

supported 主集按 train / val / test:

```text
train: 260
val: 18
test: 79
```

supported 主集全部满足:

```text
ligand_valid = true
ligand_internal_severe_clash_count = 0
target_num_severe_pairs >= 1
non_target_num_severe_pairs = 0
scaffold_num_severe_pairs = 0
target_score_ratio_valid >= 0.7
max_clash_depth <= 1.5 Å
base_split == derived_split
unknown split = 0
```

阶段 2 的边界:

```text
阶段 2 是 controlled synthetic failed pose benchmark construction.
阶段 2 不训练模型.
阶段 2 不调用生成器.
阶段 2 不做 repair.
阶段 2 不做 whole protein-ligand complex minimization.
阶段 2 不能证明方法适用于真实生成模型失败分布.
```

## 4. 当前核心问题

请重点分析这个科学和工程问题:

```text
阶段 2 的人工负样本是人为构造的 controlled local R-group clash.
真实生成模型产生的 model-induced failures 不一定符合这个分布.
因此阶段 2 只能证明方法在受控局部 R-group clash 子任务上可行,
不能直接证明修正器或 locator 适用于真实生成模型输出.
```

请评估:

1. 阶段 2 的 357 个 `supported_single_rgroup` 主负样本是否足够支撑阶段 3 的 locator / verifier 初步实验.
2. `easy_rotation`, `torsion_perturb`, `directed_clash` 三类人工注入是否互补, 是否存在明显偏差.
3. `near_miss_contact`, `duplicate_removed`, `invalid_conformer`, `unsupported`, `global_pose_failure`, `ambiguous_region` 的比例说明了什么.
4. 当前 artificial benchmark 可能低估了哪些真实生成错误.
5. 阶段 2 结果应该如何在论文或技术路线里表述, 避免过度声称.

## 5. 阶段 2.5 拟议定位

我们正在考虑加入:

```text
阶段 2.5: baseline generation failure audit
```

更精确的定位是:

```text
external validity audit
```

阶段 2.5 的目的不是训练模型, 不是 repair, 不是公平比较生成 baseline, 也不是阶段 8 的提前版。

它的目的:

```text
复现或运行一个最容易可控的生成 baseline,
审计真实 model-induced generated poses 的失败分布,
分析它们与阶段 2 artificial failures 的差距,
判断阶段 2 是否覆盖真实生成失败中的一个重要子分布.
```

阶段 2.5 第一版应回答:

1. model-induced samples 中有多少 ligand-only invalid.
2. ligand 合法的 generated poses 中有多少 severe protein-ligand clash.
3. severe clash 中有多少是 `single_rgroup_clash`, `multi_region`, `scaffold_clash`, `global_pose_failure`, `near_miss`, `unsupported`.
4. 有多少 generated samples 能成功 scaffold / R-group mapping, 即 `rgroup_attributable = true`.
5. model-induced single-region failures 与 phase2 supported artificial cases 在 clash severity, dominant ratio, severe pair count, ligand validity, R-group size/type 上是否同量级.
6. model-induced failures 中有多少看起来适合 `local_rgroup_repair_possible`, 有多少更适合 `global_repose_needed`, `invalid_unrepairable`, `reject`.

## 6. 阶段 2.5 需要警惕的漏洞

请逐条分析这些潜在漏洞, 并提出修复方案:

```text
1. baseline 选择偏差: 只选一个生成模型可能不能代表生成模型整体失败分布.
2. baseline 复现不真实: checkpoint, config, seed, pocket input, postprocess 不一致可能导致错误结论.
3. receptor scope 不一致: generation scope 和 evaluation scope 可能不同.
4. model outputs 不一定能做 scaffold/R-group mapping, 不能强行贴 target R-group.
5. ligand generation error 和 pose placement error 可能混在一起.
6. sanitization, protonation, docking, minimization 等 postprocess 可能制造或消除 clash.
7. 只比较 severe clash rate 不够, 需要比较更完整的 distribution.
8. 小样本 audit 容易过度解释.
9. 只看失败样本不看全部 generated samples 会误判覆盖率.
10. 根据阶段 2.5 结果反向改 phase2 v0_1 会污染 benchmark.
11. model-induced failure 可能不可 local repair, 应区分 repairability proxy.
12. 用 predicted dominant region 当真值可能造成评价泄漏.
```

## 7. 请给出阶段 2.5 最小实验设计

请设计一个克制的 v0 实验, 要求:

```text
不训练.
不 repair.
不调参.
不做 baseline 排名.
只做 frozen pretrained / inference.
只做 taxonomy 和 distribution gap 分析.
不回改 phase2 v0_1.
```

建议考虑:

```text
数据规模: 10-20 个 val/test base pockets, 每个 20-50 个 generated candidates.
baseline 数量: 第一版 1 个最容易复现的生成 baseline; 如果成本可控, 增加第 2 个机制不同的 baseline.
报告对象: all generated samples, not only failures.
```

请给出建议输出文件, 例如:

```text
reports/phase2_5_model_induced_audit/summary.json
reports/phase2_5_model_induced_audit/generation_manifest.parquet
reports/phase2_5_model_induced_audit/ligand_validity.csv
reports/phase2_5_model_induced_audit/model_induced_clash_report.csv
reports/phase2_5_model_induced_audit/failure_taxonomy.csv
reports/phase2_5_model_induced_audit/artificial_vs_model_induced_gap.csv
reports/phase2_5_model_induced_audit/visual_qc_cases.csv
reports/phase2_5_model_induced_audit/phase2_5_audit.md
```

## 8. 输出要求

请输出一份结构化分析, 包含:

1. 阶段 2 结果是否达成目标.
2. 阶段 2 的主要证据和局限.
3. 357 个 supported 主负样本是否足够启动阶段 3.
4. 是否应该加入阶段 2.5, 以及它的准确定位.
5. 阶段 2.5 最小可行实验设计.
6. 阶段 2.5 的关键风险和对应修复方案.
7. 哪些结论不能从阶段 2 或阶段 2.5 推出.
8. 对阶段 3 是否可以并行启动的建议.

请保持审慎, 不要把 artificial benchmark 的成功过度解释为真实生成模型失败修复成功。
