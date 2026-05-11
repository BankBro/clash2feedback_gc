# Clash2Feedback-GC: 阶段 2 人工局部碰撞注入最终实验报告

> 日期: 2026-05-11  
> 关联阶段: 阶段 0 processed clean complexes, 阶段 1 clash detector / attribution / verifier, 阶段 2 artificial clash benchmark construction  
> 核心产物: `ClashRepairBench-RG-artificial`, `phase2_v0_1`  
> 结论状态: `closed_for_controlled_phase3_preflight_with_minor_visual_qc_caveats`

## 1. 摘要

阶段 2 可以正式关闭.

阶段 2 已完成 `ClashRepairBench-RG-artificial` controlled synthetic failed pose benchmark 构建. 当前 benchmark 从 51 个 clean base samples 和 2610 次 perturbation attempts 中得到 357 个 `supported_single_rgroup` 主负样本. 主集通过 ligand-only validity, target severe clash, non-target/scaffold no-severe, split inheritance 和 sampled visual QC 检查, 足够作为阶段 3 rule locator / verifier preflight 的 controlled benchmark 输入.

阶段 2 的关闭口径必须保持克制: 它验证的是 controlled artificial single-Rgroup clash 子任务的数据构造完成, 不验证真实生成模型 failed poses 的分布覆盖, 不验证 repair 方法有效, 也不声称 synthetic failed pose 是真实稳定结合构象.

核心状态:

- `phase2_acceptance_status`: `complete`.
- `visual_qc_status`: `sampled_visual_qc_passed_with_minor_caveats`.
- `energy_delta_threshold_mode`: `record_only`.
- `energy_delta_filter_interpretation`: `record_only_not_hard_filter`.
- 阶段 3 主评估分母: `oracle_split == supported_single_rgroup`.
- 阶段 2.5 external validity audit: 后续单独处理, 不回改 `phase2_v0_1` benchmark.

## 2. 阶段目标与边界

阶段 2 的目标是从阶段 0/1 验收过的 clean protein-ligand poses 出发, 选择一个合法 target R-group, 对该 R-group 进行 controlled perturbation, 构造 ligand 自身合理但 target R-group 与 protein 发生 severe clash 的 artificial failed pose. 阶段 2 的主产物是带人工真值 target R-group 标签的 controlled benchmark, 用于后续定位器和验证器的受控预飞行评估.

阶段 2 做以下工作:

- 筛选 clean base poses.
- 选择 single-anchor target R-group.
- 执行 `easy_rotation`, `torsion_perturb`, `directed_clash` 三类人工扰动.
- 检查 ligand-only 合理性和 protein-ligand clash.
- 依据 target, non-target, scaffold 的 severe clash 情况分配 oracle split.
- 保存 benchmark manifest, sample files, ligand SDFs 和 reports.

阶段 2 不做以下工作:

- 不接真实生成器, 不调用 DiffSBDD / Pocket2Mol / TargetDiff 等 generator.
- 不训练模型, 不训练 learned critic, ranker 或 feedback adapter.
- 不做 repair, 不做 repair yield 或 repair success 结论.
- 不做 whole-complex minimization.
- 不声称 synthetic failed pose 是真实稳定结合构象.
- 不证明真实生成模型 failures 的分布已覆盖.
- 不回改 `phase2_v0_1` benchmark 定义.

## 3. 实验配置与执行

本次报告依据仓库内已提交的配置, 脚本, reports 和复盘材料归档. 核心入口如下:

| 类型 | 路径 |
|---|---|
| config | `configs/phase2_injection.yaml` |
| injection script | `scripts/phase2_inject_artificial_clashes.py` |
| visual QC script | `scripts/phase2_render_visual_qc_images.py` |
| phase1 report root | `reports/phase1_clash_detector` |
| benchmark root | `data/benchmarks/clashrepairbench_rg_artificial/v0_1` |
| phase2 report root | `reports/phase2_injection` |
| visual QC report root | `reports/phase2_visual_qc` |
| visual QC render root | `runs/phase2_visual_qc` |

配置中的关键参数:

- `schema_version`: `phase2_v0_1`.
- `seed`: `20260510`.
- injection modes: `easy_rotation`, `torsion_perturb`, `directed_clash`.
- default detector delta: `0.4 Å`.
- delta sensitivity: `0.3 Å`, `0.4 Å`, `0.5 Å`.
- severe depth threshold: `0.4 Å`.
- single-region dominant ratio: `0.7`.
- max supported clash depth: `1.5 Å`.
- split policy: derived samples inherit base split by `split_group`.
- energy delta threshold mode: `record_only`.

审计记录中的实际复现命令如下. 报告中保留相对路径版本, 便于从仓库根目录复现:

```bash
python -m compileall src scripts
python -m pytest
python scripts/phase2_inject_artificial_clashes.py \
  --config configs/phase2_injection.yaml \
  --manifest data/processed/v0_1/manifest.parquet \
  --phase1-report-root reports/phase1_clash_detector \
  --output-root data/benchmarks/clashrepairbench_rg_artificial/v0_1 \
  --report-root reports/phase2_injection
```

## 4. 核心结果统计

阶段 2 主统计来自 `reports/phase2_injection/summary.json`, `reports/phase2_injection/phase2_completion_audit.md` 和 benchmark manifest.

| 指标 | 数值 |
|---|---:|
| `num_base_clean_samples` | 51 |
| `num_base_total_samples` | 51 |
| `num_attempts` | 2610 |
| `num_accepted_supported` | 357 |
| manifest shape | 2610 rows x 70 columns |
| `phase2_acceptance_status` | `complete` |
| `default_delta_angstrom` | 0.4 |
| sampled visual QC cases | 32 |
| rendered single-view images | 1536 |
| contact sheets | 128 |

Oracle split 分布:

| oracle split | count | 解释 |
|---|---:|---|
| `supported_single_rgroup` | 357 | 阶段 3 主 Top-1 / Top-3 评估集 |
| `near_miss_contact` | 778 | 接近 contact, 但没有 severe clash |
| `duplicate_removed` | 739 | 重复或高度相似样本, 已去重 |
| `invalid_conformer` | 601 | ligand 自身构象不合理, 不进主集 |
| `unsupported` | 85 | 当前 chemistry / mask / torsion 不支持 |
| `global_pose_failure` | 48 | clash 过深或更像整体失败 |
| `ambiguous_region` | 2 | 归因边界不够单一区域 |

所有 attempts 的 injection mode 分布:

| injection mode | attempts |
|---|---:|
| `directed_clash` | 1160 |
| `easy_rotation` | 725 |
| `torsion_perturb` | 725 |

`supported_single_rgroup` 主集的 injection mode 分布:

| injection mode | supported count |
|---|---:|
| `easy_rotation` | 117 |
| `torsion_perturb` | 118 |
| `directed_clash` | 122 |

`supported_single_rgroup` 主集继承 base split 后的分布:

| derived split | count |
|---|---:|
| `train` | 260 |
| `val` | 18 |
| `test` | 79 |

`supported_single_rgroup` 主集 target R-group 分布:

| target R-group | count |
|---|---:|
| `R1` | 10 |
| `R2` | 64 |
| `R3` | 66 |
| `R4` | 116 |
| `R5` | 53 |
| `R6` | 11 |
| `R7` | 12 |
| `R8` | 25 |

## 5. supported_single_rgroup 主集质量

`supported_single_rgroup` 是阶段 2 最重要的主集, 后续阶段 3 的 Top-1 / Top-3 主指标应只以该 split 为分母. 当前主集质量由自动 gates 和 visual QC 共同支撑.

自动 gates 结果:

| gate | 结果 |
|---|---|
| `ligand_valid` | 357 / 357 为 true |
| `ligand_internal_severe_clash_count` | min = 0, max = 0 |
| `target_num_severe_pairs` | min = 1, max = 12, mean = 1.91 |
| `non_target_num_severe_pairs` | min = 0, max = 0 |
| `scaffold_num_severe_pairs` | min = 0, max = 0 |
| `target_score_ratio_valid` | min = 0.706, mean = 0.997, max = 1.000 |
| `max_clash_depth` | min = 0.402 Å, mean = 0.790 Å, max = 1.496 Å |
| split inheritance | all `base_split == derived_split` |
| unknown derived split | 0 |

这些 gates 说明主集满足阶段 2 对 artificial single-Rgroup failed pose 的关键定义: ligand 本身不过度坏掉, target R-group 至少存在一个 severe protein-ligand clash, non-target R-groups 与 scaffold 不发生 severe clash, 派生样本不跨 split 泄漏.

需要注意的是, `predicted_dominant_valid_rgroup` 只作为记录字段, 不作为 acceptance gate. 主集标签来自人工 target R-group 和 oracle split 规则, 避免把阶段 3 locator 的预测结果反向用于筛样本.

## 6. 三种注入方式的解释

阶段 2 使用三类 controlled perturbation. 它们服务于 benchmark construction 和 diagnostic stress testing, 不代表生成模型真实采样分布.

| mode | 作用 | 边界 |
|---|---|---|
| `easy_rotation` | 围绕 scaffold-R-group anchor bond 旋转 target R-group, 最可控, 适合 debug 和基础定位 | 人工性强 |
| `torsion_perturb` | 扰动 target R-group 内部 torsion, 更接近局部构象错误 | 仍是人工扰动, 不代表真实失败分布 |
| `directed_clash` | 朝 protein hotspot 富集局部 steric conflict, 提高 severe clash 构造效率 | 不能解释为 model-induced generation distribution |

`directed_clash` 的正确解释是: Directed clash enriches controlled local steric conflicts for diagnostic stress testing. It should not be interpreted as a model-induced generation distribution.

## 7. Delta Sensitivity

`delta_sensitivity.csv` 已修复空表头, 当前列为:

```text
delta_angstrom,target_severe,no_target_severe,unsupported_or_unavailable
```

结果如下:

| delta Å | target severe | no target severe | unsupported or unavailable |
|---:|---:|---:|---:|
| 0.3 | 982 | 1543 | 85 |
| 0.4 | 876 | 1649 | 85 |
| 0.5 | 775 | 1750 | 85 |

随着 delta 从 0.3 Å 增加到 0.5 Å, 判定为 target severe 的 attempts 数下降, 符合更宽松 vdW 容忍余量会减少 clash 判定的预期. 阶段 2 主标签仍使用 delta = 0.4 Å, delta = 0.3 Å / 0.5 Å 作为 sensitivity 信息保留给阶段 3 preflight 和后续论文分析.

## 8. Energy Delta Record-Only 口径

`energy_delta` 在 `phase2_v0_1` 中是 record-only ligand-only diagnostic, 不是 hard acceptance filter.

当前配置里保留 ligand-only forcefield energy 字段, 包括 `forcefield_type`, `energy_original`, `energy_failed`, `energy_delta`, `energy_delta_pass`, `energy_check_status`. 但 `energy_delta_threshold_mode` 为 `record_only`, 因此 supported 主集通过的是 sanitize, bond, anchor, chirality, ligand internal clash 和 protein-ligand clash gates, 没有使用 strict energy-delta gate 筛除.

能量相关报告:

- `reports/phase2_injection/energy_delta_stats.csv`: 17 个 grouped rows.
- `reports/phase2_injection/energy_delta_outliers.csv`: 746 个 record-only outlier rows, 用于 visual / diagnostic prioritization.

阶段 2 不应基于这些 outliers 自动回改 `phase2_v0_1` benchmark. 后续阶段 4 repair 或论文分析中, 可以基于 `energy_delta_strict_pass` / `energy_delta_outlier_flag` 做分层分析, 但这属于后续解释与敏感性分析, 不是阶段 2 closure 的阻塞项.

## 9. Visual QC 结果与 Caveats

Visual QC 状态为 `sampled_visual_qc_passed_with_minor_caveats`. 自动结构 gates 已完成, 32 个抽样 case 的 ChimeraX contact sheets 已完成用户人工粗看和 4 个只读子 agent 独立复核, 未发现阻断问题.

Visual QC 范围:

| 项 | 数值 |
|---|---:|
| reviewed cases | 32 |
| reviewed contact sheets | 128 |
| rendered single-view images | 1536 |
| supported cases in QC | 17 |
| invalid_conformer cases in QC | 5 |
| global_pose_failure cases in QC | 3 |
| ambiguous_region cases in QC | 2 |
| near_miss_contact cases in QC | 5 |

Supported visual QC 覆盖 `easy_rotation`, `directed_clash` 和 `torsion_perturb` 三种 injection modes, 其中补充的 `supported_single_rgroup + torsion_perturb` case 覆盖 target R-group `R1` 到 `R7`. 视觉结论是 supported 主集符合单一 target R-group 局部 ligand-protein clash, scaffold 和 non-target R-groups 在 supported 样本中稳定, 三种 supported injection mode 均未发现阻断问题.

保留 minor caveats:

- `invalid_conformer` 当前没有 ligand internal self-clash 专用高亮视图, 但 invalid cases 不像合格 ligand-protein clash.
- invalid visual QC 中 `case_000019` / `case_000029` 和 `case_000057` / `case_000070` 是视觉重复, 但属于 rejected invalid 样本, 不影响 supported 主集.
- `ambiguous_region` 中 `case_000717` 和 `case_000718` 的 `overlay_surface` 信息量有限, 但其他视图支持 ambiguous-region 标签.
- `near_miss_contact` 没有 severe VDW pair, 因此 `clash_pair_vdw` 为 background-only, 这符合该 split 语义.

这些 caveats 不影响 `supported_single_rgroup` 主集质量判断, 也不阻断阶段 3 locator / verifier preflight.

## 10. 阶段 2 可以支持什么

阶段 2 支持阶段 3 在 controlled artificial `supported_single_rgroup` cases 上评估 rule locator / verifier preflight.

阶段 3 可以使用以下输入启动:

- `reports/phase2_injection/supported_single_rgroup_cases.csv`.
- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/manifest.parquet`.
- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/samples/*.pkl`.
- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/ligands/*_failed.sdf`.

阶段 3 主指标建议:

- Coverage.
- Top-1.
- Top-1 covered.
- Top-3 rank.
- Top-3 operational.
- `dominant_ratio_valid` mean / median / p95.
- delta sensitivity performance.
- mode-wise performance: `easy_rotation`, `torsion_perturb`, `directed_clash`.
- difficulty-wise performance.
- split-wise performance.

Reject / unsupported / near_miss / duplicate / invalid / global / ambiguous 不应混入 Top-1 / Top-3 主分母, 但应单独用于分流能力, reject policy 和 failure taxonomy 分析.

## 11. 阶段 2 不能推出什么

阶段 2 的结果不能推出以下结论:

- 不能证明真实生成模型 failures 已被覆盖.
- 不能证明 model-induced failures 可被定位或修复.
- 不能证明 repair 方法有效.
- 不能证明 full receptor 下也安全.
- 不能证明 synthetic failed poses 是真实稳定结合构象.
- 不能证明 energy gate 已严格过滤所有高能构象.
- 不能证明 `directed_clash` 分布等价于真实 generator sampling distribution.

这些边界对论文表述很重要. 阶段 2 是 benchmark construction 和 preflight substrate, 不是生成模型失败分布验证, 也不是 repair 方法结果.

## 12. 阶段 3 Locator / Verifier Preflight 建议

阶段 3 应以 `supported_single_rgroup` 作为主 Top-1 / Top-3 分母. 每个 supported case 的 `target_rgroup` 是人工真值标签, `top_valid_rgroups_json`, `dominant_ratio_valid_rgroups`, `delta03_status`, `delta04_status`, `delta05_status` 可作为 rule locator / verifier preflight 的辅助输入和诊断字段.

建议阶段 3 最小产物:

```text
configs/phase3_rule_locator.yaml
scripts/phase3_rule_locator.py
reports/phase3_rule_locator/summary.json
reports/phase3_rule_locator/rule_locator_results.csv
reports/phase3_rule_locator/reject_split_report.csv
reports/phase3_rule_locator/delta_sensitivity_report.csv
```

建议阶段 3 执行策略:

- 先冻结阶段 2 主集分母, 只在 `supported_single_rgroup` 上报告主定位指标.
- 对 reject / unsupported / near_miss / duplicate / invalid / global / ambiguous 单独报告分流表现.
- 按 injection mode, difficulty bin, derived split 和 target R-group 做分层统计.
- 报告 delta 0.3 / 0.4 / 0.5 sensitivity, 但主结果沿用 phase2 default delta 0.4.
- 不使用 phase2 visual QC notes 作为模型输入, 只作为数据集验收证据.

## 13. 阶段 2.5 External Validity Audit 后续边界

阶段 2.5 external validity audit 后续单独处理, 本报告不实现阶段 2.5.

阶段 2.5 的合理目标是验证 artificial benchmark 与真实 generator-induced failures 之间的外部有效性差距. 它应使用 frozen DiffSBDD baseline 或其他可复现 SBDD generator, 在经过 training-overlap audit 的 clean pockets 上生成 candidates, 审计 all generated samples 的 ligand validity, protein-ligand clash, R-group attribution, failure taxonomy, repairability proxy, 并与 phase2 artificial supported cases 做 distribution gap analysis.

阶段 2.5 的边界:

- 不回改 `phase2_v0_1` benchmark.
- 不把真实 generator failures 混入阶段 2 主集.
- 不用阶段 2.5 的结果重写阶段 2 closure.
- 不在本轮调用生成器, 不做 repair, 不训练模型.

阶段 2.5 可以回答 external validity 和 distribution gap 问题, 但它不是阶段 2 controlled benchmark closure 的前置阻塞项.

## 14. 当前验证结果

本报告生成后重新运行了仓库级验证:

```bash
python -m compileall src scripts
python -m pytest
```

验证结果:

| 命令 | 结果 |
|---|---|
| `python -m compileall src scripts` | pass |
| `python -m pytest` | 79 passed, 3 skipped in 6.52s |

3 个 skipped tests 均来自当前环境缺少 RDKit:

- `tests/test_chemistry_rdkit.py`.
- `tests/test_phase2_anchor_integrity.py`.
- `tests/test_phase2_ligand_validity.py`.

## 15. 关闭结论

阶段 2 已可关闭, 并可作为阶段 3 controlled locator / verifier preflight 的输入. 它建立的是干净的 artificial single-Rgroup clash benchmark; 真实生成模型失败外部有效性和 repair 效果仍需由阶段 2.5 及后续修复阶段单独验证.

正式关闭结论:

```text
Phase 2 is closed for controlled Phase 3 locator/verifier preflight.
It establishes a clean artificial single-Rgroup clash benchmark.
Model-induced external validity and repair effectiveness remain separate questions for Phase 2.5 and later repair phases.
```
