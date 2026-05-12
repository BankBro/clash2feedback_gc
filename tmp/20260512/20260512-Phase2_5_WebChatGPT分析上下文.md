# Phase 2.5 Web ChatGPT 分析上下文

## 1. 目的

本文档用于给只能阅读 GitHub 仓库的网页版 ChatGPT 提供阶段 2.5 实验上下文。阶段 2.5 的定位是 model-induced failure external validity audit, 使用 frozen DiffSBDD baseline 生成候选分子, 审计真实生成失败类型, 并与阶段 2 artificial single-Rgroup clash benchmark 做分布差距分析。

本文档不替代正式报告。正式报告位于:

```text
reports/phase2_5_model_induced_audit/phase2_5_completion_audit.md
reports/phase2_5_model_induced_audit/summary.json
```

## 2. 建议提交给 GitHub 的轻量文件

建议提交以下文件, 供网页版 ChatGPT 后续阅读:

```text
README.md
AGENTS.md
.gitignore
docs/external_baselines.md
docs/20260511-Clash2Feedback-GC_阶段2.5模型诱导失败外部有效性审计落地方案.md
configs/phase2_5_model_induced_audit.yaml
scripts/phase2_5_prepare_diffsbdd.py
scripts/phase2_5_training_overlap_audit.py
scripts/phase2_5_model_induced_audit.py
src/clash2feedback/generation_audit/
tests/test_phase2_5_*.py
external/AGENTS.md
external/README.md
reports/phase2_5_model_induced_audit/
tmp/20260512/20260512-Phase2_5_WebChatGPT分析上下文.md
```

不建议提交:

```text
external/DiffSBDD/
external/DiffSBDD/checkpoints/crossdocked_fullatom_cond.ckpt
runs/phase2_5_model_induced_audit/
data/raw_complexes/
data/processed/*/complexes/
大型 cache, checkpoint, raw PDB/SDF 和运行中间产物
```

原因: 网页版 ChatGPT 需要的是可解释代码, 配置, 轻量报告和 provenance。DiffSBDD 源码可以通过 `docs/external_baselines.md` 中记录的 source repo 和 pinned commit 访问, 不需要提交本地外部仓库副本。

## 3. DiffSBDD 外部模型信息

长期入口:

```text
docs/external_baselines.md
```

本轮使用:

```text
Source repo: https://github.com/arneschneuing/DiffSBDD.git
Pinned commit: 5d0d38d16c8932a0339fd2ce3f67ade98bbdff27
Local path: external/DiffSBDD/
Entrypoint: external/DiffSBDD/generate_ligands.py
Checkpoint: crossdocked_fullatom_cond.ckpt
Checkpoint URL: https://zenodo.org/records/8183747/files/crossdocked_fullatom_cond.ckpt?download=1
Checkpoint sha256: 07f86764bf569aafbc40a9c15fc02de8e2550437dd0f17f657eab3abe66c372c
```

DiffSBDD core model 内部生成 ligand atom types 和 3D coordinates。DiffSBDD 后处理再根据 atom types 和 coordinates 推断 bonds, 构建 RDKit molecule, 写出 SDF。本项目 Phase 2.5 消费的是 DiffSBDD `generate_ligands.py` 写出的 SDF, 不是裸 point-cloud tensor。

## 4. 实验执行边界

本轮严格遵守:

- 不训练模型.
- 不做 repair.
- 不调参.
- 不做 baseline ranking.
- 不回改 `phase2_v0_1`.
- 不把 model-induced samples 混入阶段 3 主评估.
- 不把 predicted dominant R-group 当 oracle ground truth.
- 先做 training-overlap audit, 再做 generation.
- 记录 all generated samples.

主控环境为 `c2f_cpu`, DiffSBDD frozen inference 使用独立 `diffsbdd` conda 环境。GPU 检查显示两张 RTX 2080 Ti 可用。DiffSBDD smoke test 通过。

## 5. Training-overlap Audit 结果

输入来自本地 `data/processed/v0_1/manifest.parquet` 和 `data/splits/v0_1/val.txt`, `test.txt`。

本轮审计:

```text
num_pockets_audited: 51
external_validity_subset_size: 51
official_split_available: false
tier_counts:
  T_unknown: 51
```

解释:

- 本项目 `val/test` 不等于 DiffSBDD unseen split.
- 当前没有拿到 DiffSBDD/Pocket2Mol 官方 train/test split 文件。
- 因此所有 candidate base pockets 只能标为 `T_unknown`。
- `T_unknown` 不表示已见过或未见过, 只表示无法证明训练重叠关系。
- 因此本轮不能宣称严格 official external-unseen, 结论必须保守。

选中的 10 个 base pockets 来自本地 `v0_1` processed dataset:

```text
complex_crossdocked_000026, val,  RIP1_MOMCH_24_270_0
complex_crossdocked_000027, val,  RIP1_MOMCH_24_270_0
complex_crossdocked_000028, val,  RIP1_MOMCH_24_270_0
complex_crossdocked_000001, test, CDGT2_BACCI_28_713_0
complex_crossdocked_000002, test, CDGT2_BACCI_28_713_0
complex_crossdocked_000003, test, CDGT2_BACCI_28_713_0
complex_crossdocked_000004, test, CDGT2_BACCI_28_713_0
complex_crossdocked_000005, test, CDGT2_BACCI_28_713_0
complex_crossdocked_000006, test, CDGT2_BACCI_28_713_0
complex_crossdocked_000007, test, CDGT2_BACCI_28_713_0
```

## 6. Generation 和 Failure Taxonomy 结果

DiffSBDD 对 10 个 base pockets 各生成 20 个 candidates, 共 200 个 unique generated candidates。

报告中 `generation_manifest.parquet` 有 400 行, 是因为每个 candidate 记录两阶段:

```text
raw_generated: DiffSBDD 原始 SDF 输出.
standardized_generated: 本项目审计层复制 RDKit mol, 若有多个 fragments 则保留最大 heavy-atom fragment.
```

注意: 400 行不是 400 个独立分子, 而是 200 个 unique candidates x 2 stages。

本轮 raw vs standardized 对比:

```text
taxonomy_changed: 0 / 200
validity_changed: 0 / 200
raw num_fragments: 全部为 1
standardized num_fragments: 全部为 1
```

结论: 本轮 `standardized_generated` 没有改变任何 candidate 的 ligand validity 或 failure taxonomy。后续分析真实生成分布时, 应按 200 个 unique candidates 计数, 不应把 raw + standardized 两阶段的 400 行当作 400 个独立分子。

Unique candidate 口径的主要结果:

```text
generated unique candidates: 200
valid ligand: 120
invalid ligand: 80

failure taxonomy:
  ligand_only_invalid: 80
  valid_no_severe_clash: 73
  near_miss_contact: 31
  global_pose_failure: 8
  scaffold_clash: 6
  rgroup_unattributable: 1
  single_rgroup_clash: 1
```

阶段 2.5 正式报告里的部分 summary 数字是 raw + standardized 两阶段行数口径, 例如 `num_ligand_valid=240`, `num_ligand_invalid=160`, `num_single_rgroup_clash=2`。这些适合检查审计表完整性, 不适合直接解释为独立分子数量。解释真实生成分布时应使用上面的 unique candidate 口径。

## 7. 当前结论边界

可以说:

- DiffSBDD frozen inference 已在本地 10 个 val/test base pockets 上跑通。
- 200 个 unique generated candidates 已全部记录并完成 validity/taxonomy 审计。
- 本轮真实生成失败中 `single_rgroup_clash` 只占很小比例, 更多失败来自 ligand invalid, near miss, global pose 和 scaffold-level 问题。
- Phase 2 artificial single-Rgroup clash benchmark 覆盖了可控局部碰撞子任务, 但不能代表全部 model-induced failure 分布。

不能说:

- 这些 pockets 是严格 DiffSBDD external unseen。
- 200 个 generated candidates 可以混入阶段 3 主评估。
- 本轮结果证明 repair 方法有效。
- 本轮结果可用于 DiffSBDD 与其他 generator ranking。

唯一 blocked 项:

```text
official_diffsbdd_or_pocket2mol_split_unavailable
```

## 8. 建议网页版 ChatGPT 优先阅读文件

优先阅读:

```text
README.md
docs/external_baselines.md
docs/20260511-Clash2Feedback-GC_阶段2.5模型诱导失败外部有效性审计落地方案.md
configs/phase2_5_model_induced_audit.yaml
reports/phase2_5_model_induced_audit/phase2_5_completion_audit.md
reports/phase2_5_model_induced_audit/summary.json
reports/phase2_5_model_induced_audit/training_overlap_summary.json
reports/phase2_5_model_induced_audit/base_pocket_selection.csv
reports/phase2_5_model_induced_audit/failure_taxonomy.csv
reports/phase2_5_model_induced_audit/ligand_validity.csv
reports/phase2_5_model_induced_audit/model_induced_clash_report.csv
reports/phase2_5_model_induced_audit/artificial_vs_model_induced_gap.csv
src/clash2feedback/generation_audit/
scripts/phase2_5_model_induced_audit.py
tests/test_phase2_5_*.py
```

必要时再参考 DiffSBDD upstream:

```text
https://github.com/arneschneuing/DiffSBDD.git
commit: 5d0d38d16c8932a0339fd2ce3f67ade98bbdff27
```
