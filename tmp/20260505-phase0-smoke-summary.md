# 阶段 0 工程实现与 smoke 验证记录

## 1. 目的

本文件用于给只能阅读 GitHub 仓库内容的网页版 ChatGPT 提供本次阶段 0 工程实现和 smoke 验证背景.

当前阶段 0 的目标是把 raw protein-ligand complex 转换为后续阶段可复用的 clean processed sample, 不训练模型, 不调用生成器, 不做人工 clash 注入.

## 2. 本次提交的数据选择

本次建议提交到 GitHub 的实验相关数据只有本文档:

- `tmp/20260505-phase0-smoke-summary.md`

本次不提交以下数据:

- DiffSBDD example 的 `protein.pdb` 和 `ligand.sdf`, 因为它们来自公开仓库, 可按链接复现下载.
- `data/raw_complexes/` 下的原始结构数据, 因为当前本地没有正式数据集.
- `data/processed/v0_1/complexes/*.pkl`, 因为它们是生成产物, 且不适合作为代码审查输入.
- `manifest.parquet`, `split_report.csv`, `reports/phase0/*.csv` 和 `reports/phase0/*.json`, 因为本次 smoke 输出规模很小, 关键结果已经在本文档中用文本表格保留.

如果后续需要给网页版 ChatGPT 分析真实数据筛选质量, 再单独提交轻量 CSV 摘要, 例如 `failed_cases.csv`, `dataset_check.csv`, `split_report.csv`, 不提交 raw PDB/SDF 或 pickle.

## 3. 代码和配置入口

建议按以下顺序阅读:

- `docs/20260505-Clash2Feedback-GC_阶段0工程方案.md`
- `README.md`
- `configs/phase0.yaml`
- `scripts/phase0_build_processed.py`
- `scripts/phase0_make_splits.py`
- `scripts/phase0_check_dataset.py`
- `src/clash2feedback/data/build_processed_dataset.py`
- `src/clash2feedback/data/split_dataset.py`
- `src/clash2feedback/data/check_dataset.py`
- `src/clash2feedback/chemistry/sanitize.py`
- `src/clash2feedback/chemistry/scaffold.py`
- `src/clash2feedback/chemistry/rgroup.py`
- `src/clash2feedback/pocket/extract_pocket.py`
- `src/clash2feedback/geometry/basic_clash_screen.py`
- `tests/`

当前分支:

```text
20260505-180108-phase0-implementation
```

## 4. 环境

当前 conda 环境名:

```text
c2f_cpu
```

已确认的关键包版本:

| 组件 | 版本 |
|---|---|
| `clash2feedback` | `0.1.0` |
| `rdkit` | `2026.03.2` |
| `biopython` | `1.87` |
| `pandas` | `3.0.2` |

阶段 0 不需要 PyTorch, CUDA, DiffSBDD 工程, DiffSBDD 权重, TargetDiff, Pocket2Mol 或 AutoDock Vina.

## 5. 自动化验证结果

已运行:

```bash
conda run -n c2f_cpu pytest
```

结果:

```text
14 passed
```

覆盖内容包括:

- 配置读取和 raw complex 目录识别.
- RDKit ligand sanitize, Murcko scaffold 和 R-group 拆分基础逻辑.
- pocket 提取和 basic clash screen.
- processed sample 检查报告.
- manifest split 逻辑, 包括空 manifest 和 grouped split.

## 6. CLI 空数据 smoke

使用空 raw root 在 `/tmp` 下验证过三条阶段 0 CLI:

```bash
conda run -n c2f_cpu python scripts/phase0_build_processed.py --raw-root <empty_raw> --processed-root <tmp_processed> --report-root <tmp_reports>
conda run -n c2f_cpu python scripts/phase0_check_dataset.py --processed-root <tmp_processed> --manifest <tmp_processed>/manifest.parquet --report-root <tmp_reports>
conda run -n c2f_cpu python scripts/phase0_make_splits.py --manifest <tmp_processed>/manifest.parquet --split-root <tmp_splits>
```

结果:

| 命令 | 结果 |
|---|---|
| `phase0_build_processed.py` | `processed=0`, `failed=0` |
| `phase0_check_dataset.py` | `checked=0`, `usable=0` |
| `phase0_make_splits.py` | `samples=0` |

该 smoke 说明空数据情况下仍可生成 `manifest.parquet`, `schema.json`, report CSV/JSON 和 split 文件, 不会崩溃.

## 7. DiffSBDD official example smoke

本次用 DiffSBDD 官方 example 在 `/tmp` 临时下载并运行, 运行后已删除临时目录, 没有把 raw 或 processed 数据提交到仓库.

公开来源:

- `https://github.com/arneschneuing/DiffSBDD/tree/main/example`
- `https://raw.githubusercontent.com/arneschneuing/DiffSBDD/main/example/3rfm.pdb`
- `https://raw.githubusercontent.com/arneschneuing/DiffSBDD/main/example/3rfm_B_CFF.sdf`
- `https://raw.githubusercontent.com/arneschneuing/DiffSBDD/main/example/5ndu.pdb`
- `https://raw.githubusercontent.com/arneschneuing/DiffSBDD/main/example/5ndu_C_8V2.sdf`

临时 raw 结构:

```text
raw/complex_diffsbdd_3rfm/protein.pdb
raw/complex_diffsbdd_3rfm/ligand.sdf
raw/complex_diffsbdd_5ndu/protein.pdb
raw/complex_diffsbdd_5ndu/ligand.sdf
```

运行命令:

```bash
conda run -n c2f_cpu python scripts/phase0_build_processed.py --raw-root <tmp_raw> --processed-root <tmp_processed> --report-root <tmp_reports>
conda run -n c2f_cpu python scripts/phase0_check_dataset.py --processed-root <tmp_processed> --manifest <tmp_processed>/manifest.parquet --report-root <tmp_reports>
conda run -n c2f_cpu python scripts/phase0_make_splits.py --manifest <tmp_processed>/manifest.parquet --split-root <tmp_splits>
```

构建结果:

```text
processed=1
failed=1
```

通过样本:

| 字段 | 值 |
|---|---|
| `sample_id` | `complex_diffsbdd_5ndu` |
| `ligand_heavy_atoms` | `49` |
| `num_pocket_atoms` | `530` |
| `num_valid_rgroups` | `2` |
| `phase0_usable` | `True` |
| `split` | `train` |
| `split_strategy` | `complex_level_smoke` |
| `split_group_source` | `complex_id` |

失败样本:

| 字段 | 值 |
|---|---|
| `complex_id` | `complex_diffsbdd_3rfm` |
| `failure_reason` | `ligand_heavy_atoms_out_of_range` |
| `stage` | `ligand` |

解释:

- `5ndu` 能通过 strict phase0, 说明 raw PDB/SDF 读取, ligand validity, pocket 提取, scaffold/R-group 拆分, sample 保存, check 和 split 主流程已经打通.
- `3rfm` 被跳过是预期内严格过滤行为, 不是程序崩溃. 当前配置要求 ligand 重原子数为 15-60.
- 只有一个通过样本时 split 只能是 `complex_level_smoke`, 不能视为正式 target-level split.

## 8. 当前结论

阶段 0 最小工程底座已经具备真实文件 smoke 能力:

- 可以读入 raw complex 目录.
- 可以严格过滤不 clean 的 complex.
- 可以输出 pkl sample, manifest parquet 和 schema.
- 可以生成 split 文件和检查报告.
- 可以在没有正式数据集时用 DiffSBDD official example 验证接口.

当前不能得出的结论:

- 不能证明 CrossDocked 小子集能达到 20-30 个 clean processed complexes, 因为本地还没有 CrossDocked 数据.
- 不能证明 target-level split 有效, 因为 smoke 样本缺少足够 target group.
- 不能评估正式 clash detector 质量, 因为阶段 0 只做 obvious severe clash 过滤.

## 9. 下一步建议

建议下一轮做三件事:

- 新增一个轻量数据准备脚本, 先支持下载并整理 DiffSBDD official example 到 `data/raw_complexes/complex_xxxxxx/`.
- 新增 CrossDocked downsampled adapter, 从 40-50 个候选中整理 raw complex, 再通过当前 strict filter 筛出 20-30 个 clean processed complexes.
- 在真实小子集上提交轻量文本报告或 CSV 摘要, 包括 `failed_cases.csv`, `dataset_check.csv`, `split_report.csv` 和人工抽查记录, 仍不提交 raw PDB/SDF 和 pkl.

## 10. 需要重点审查的问题

网页版 ChatGPT 分析时建议重点看:

- `configs/phase0.yaml` 中 strict 过滤阈值是否适合第一批 CrossDocked 小子集.
- `src/clash2feedback/io/read_protein.py` 对 PDB/mmCIF, hetero atoms, waters, altloc 的处理是否满足阶段 0.
- `src/clash2feedback/chemistry/rgroup.py` 的 R-group 和 anchor 定义是否符合后续局部修复任务.
- `src/clash2feedback/geometry/basic_clash_screen.py` 的 obvious severe clash 过滤是否过宽或过严.
- `src/clash2feedback/data/split_dataset.py` 的 target-level split fallback 逻辑是否清楚.
- 是否应该为 DiffSBDD example 单独保留一个 `configs/phase0_smoke.yaml`, 还是继续使用正式 strict `configs/phase0.yaml`.
