# 阶段 2 人工局部碰撞注入实验汇报

## 1. 实验目的

本次阶段 2 的目标是构建 `ClashRepairBench-RG-artificial` controlled synthetic failed pose benchmark。实验从阶段 0/1 已验收的 clean protein-ligand pose 出发, 只扰动一个合法 single-anchor target R-group, 构造 ligand 自身合理但 target R-group 与 protein 发生 severe clash 的负样本。

阶段 2 不训练模型, 不调用生成器, 不做 repair, 不做 whole protein-ligand complex minimization。它的定位是提供带 oracle target R-group 标签的受控失败样本, 用于后续 detector / locator / verifier / repair policy 的机制验证。

## 2. 输入和实现

输入数据:

- `data/processed/v0_1/manifest.parquet`
- `data/processed/v0_1/complexes/*.pkl`
- `data/splits/v0_1/train.txt`, `val.txt`, `test.txt`
- `reports/phase1_clash_detector/`

新增实现:

- `configs/phase2_injection.yaml`
- `scripts/phase2_inject_artificial_clashes.py`
- `src/clash2feedback/perturb/rotation.py`
- `src/clash2feedback/perturb/torsion.py`
- `src/clash2feedback/perturb/directed_clash.py`
- `src/clash2feedback/perturb/quality.py`
- `src/clash2feedback/perturb/labels.py`
- `src/clash2feedback/perturb/deduplicate.py`

三种注入方式:

- `easy_rotation`: 绕 scaffold-R-group anchor bond 旋转 target R-group.
- `torsion_perturb`: 扰动 target R-group 内部合法 rotatable torsion.
- `directed_clash`: 用 protein 位置引导合法旋转角度选择, 提高构造 clash 的概率; 不是直接平移 R-group.

## 3. 质量门控

Base clean pose gate:

- phase1 detector `analysis_status = ok`.
- `phase0_pocket8` severe clash count = 0.
- `pocket10_all_atoms` severe clash count = 0.
- ligand sanitize pass.
- scaffold success.
- 至少 1 个 valid R-group 和 single-anchor R-group.

Ligand-only validity gate:

- RDKit sanitize pass.
- anchor bond 是合法 rotatable single bond.
- 排除 ring, double, aromatic, amide-like, conjugated bond.
- anchor integrity pass.
- bond length sanity pass.
- ligand internal severe clash = 0.
- chirality preserved.
- MMFF/UFF energy delta 只记录或作为 ligand-only filter, 不做 complex minimization.

Protein-ligand failure gate:

- 默认 `delta = 0.4 Å`.
- `delta sensitivity = 0.3 / 0.4 / 0.5`.
- target severe pairs >= 1.
- target score ratio valid >= 0.7.
- scaffold severe pairs = 0.
- non-target severe pairs = 0.
- max clash depth <= 1.5 Å.

Anti-leakage:

- `target_rgroup` 是人工扰动 oracle 标签.
- `predicted_dominant_*` 只记录, 不作为样本保留条件.
- 所有 injected variants 继承 base train / val / test split.
- heavy atom index mapping 保持稳定; AddHs 只用于 ligand-only energy check.

## 4. 运行命令和验证

阶段 2 实验命令:

```bash
/home/lyj/miniconda3/envs/c2f_cpu/bin/python scripts/phase2_inject_artificial_clashes.py \
  --config configs/phase2_injection.yaml \
  --manifest data/processed/v0_1/manifest.parquet \
  --phase1-report-root reports/phase1_clash_detector \
  --output-root data/benchmarks/clashrepairbench_rg_artificial/v0_1 \
  --report-root reports/phase2_injection
```

验证命令:

```bash
/home/lyj/miniconda3/envs/c2f_cpu/bin/python -m compileall src scripts
/home/lyj/miniconda3/envs/c2f_cpu/bin/python -m pytest
```

结果:

- `compileall`: pass.
- `pytest`: 74 passed.
- phase2 run: complete.

## 5. 主要结果

总体:

- base clean samples: 51 / 51.
- total injection attempts: 2610.
- manifest: 2610 rows x 70 columns.
- supported 主负样本: 357.

Split 分布:

| split | count | 含义 |
|---|---:|---|
| `supported_single_rgroup` | 357 | 合格主负样本, 阶段 3 Top-1 / Top-3 主评估使用 |
| `near_miss_contact` | 778 | 接近 protein 但没有达到 severe clash |
| `duplicate_removed` | 739 | 与已有样本太相似, 去重移除 |
| `invalid_conformer` | 601 | ligand 自身构象不合理 |
| `unsupported` | 85 | 当前 chemistry / torsion / mask 不支持 |
| `global_pose_failure` | 48 | clash 太重或更像整体失败 |
| `ambiguous_region` | 2 | 归因不够单一区域 |

Supported 主集按注入方式:

| injection_mode | supported count |
|---|---:|
| `easy_rotation` | 117 |
| `torsion_perturb` | 118 |
| `directed_clash` | 122 |

Supported 主集按 split:

| base_split | supported count |
|---|---:|
| train | 260 |
| val | 18 |
| test | 79 |

## 6. 主集质量检查

`supported_single_rgroup` 主集全部满足:

- `ligand_valid = true`.
- `ligand_internal_severe_clash_count = 0`.
- `target_num_severe_pairs >= 1`.
- `non_target_num_severe_pairs = 0`.
- `scaffold_num_severe_pairs = 0`.
- `target_score_ratio_valid >= 0.7`.
- `max_clash_depth <= 1.5 Å`.
- `base_split == derived_split`.
- 无 `unknown` split.

这说明 357 个主负样本是结构受控, 标签清楚, 且 ligand 自身合理的局部失败样本。

## 7. GitHub 上建议提交的数据范围

适合提交:

- `reports/phase2_injection/*.csv`
- `reports/phase2_injection/summary.json`
- `reports/phase2_injection/phase2_completion_audit.md`
- `reports/phase2_injection/visual_qc_notes.md`
- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/manifest.parquet`
- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/schema.json`

不建议提交:

- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/samples/*.pkl`
- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/ligands/*.sdf`

原因:

- 全量 samples/SDF 文件数超过 7800, 主要用于本地复现实验和可视化, 不适合网页 ChatGPT 阅读.
- 结果分析所需的 split, gate, injection mode, clash score, delta sensitivity 和 summary 已经在 reports 和 manifest 中保留.

## 8. 当前结论

阶段 2 已完成受控人工负样本构造, 且产出 357 个可用于阶段 3 主评估的 high-quality local R-group clash negatives。该结果能支撑 detector / locator / verifier 的 controlled diagnostic benchmark, 但不能直接证明方法适用于真实生成模型的失败分布。

阶段 2 的局限性:

- 人工负样本来自人为扰动 clean pose, 不代表扩散模型或其他生成模型的自然错误分布.
- `directed_clash` 是 protein-guided 合法旋转搜索, 目的是稳定构造 clash, 不是模拟生成模型采样分布.
- 真实生成失败可能包含 scaffold clash, whole-pose drift, invalid chemistry, multi-region clash 或 pocket mismatch.

因此后续需要单独设计阶段 2.5, 复现至少一个生成 baseline 并审计 model-induced failures, 比较人工负样本和真实生成失败的分布差距。

## 9. 供网页 ChatGPT 重点阅读的文件

- `docs/20260510-Clash2Feedback-GC_阶段2人工局部碰撞注入最终落地方案.md`
- `tmp/20260510/20260510-phase2-experiment-report.md`
- `reports/phase2_injection/summary.json`
- `reports/phase2_injection/phase2_completion_audit.md`
- `reports/phase2_injection/supported_single_rgroup_cases.csv`
- `reports/phase2_injection/injection_attempts.csv`
- `reports/phase2_injection/difficulty_bins.csv`
- `reports/phase2_injection/delta_sensitivity.csv`
- `configs/phase2_injection.yaml`
- `scripts/phase2_inject_artificial_clashes.py`
- `src/clash2feedback/perturb/`
