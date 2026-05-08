# 阶段 0 网页版 ChatGPT 分析说明

## 1. 阅读入口

- GitHub 仓库: `BankBro/clash2feedback_gc`.
- 分支: `20260505-180108-phase0-implementation`.
- 当前阶段: 阶段 0 已完成, 可进入阶段 1 设计.
- 本文档用途: 给只能读取 GitHub 仓库的网页版 ChatGPT 提供阶段 0 实验背景, 结果摘要, 数据边界和下一步分析问题.

建议网页版 ChatGPT 优先阅读:

- `README.md`
- `docs/20260505-Clash2Feedback-GC_阶段0工程方案.md`
- `tmp/20260506/phase0-final-summary.md`
- `tmp/20260506/phase0-closeout-summary.md`
- `tmp/20260506/phase0-balanced30-summary.md`
- `tmp/20260506/phase0-target-distribution-summary.md`
- `tmp/20260506/phase0-prefilter-bias-notes.md`
- `tmp/20260507/phase0-visual-check-notes.md`
- `tmp/20260507/phase0-visual-render-summary.md`
- `configs/phase0.yaml`
- `reports/phase0/summary.json`
- `reports/phase0/dataset_check.csv`
- `reports/phase0/failed_cases.csv`
- `reports/phase0/failure_reason_counts.csv`
- `reports/phase0/threshold_calibration.csv`
- `reports/phase0/visual_check_list.csv`
- `data/processed/v0_1/schema.json`
- `data/splits/v0_1/split_report.csv`
- `data/splits/v0_1/phase0_balanced_30.txt`

代码重点阅读:

- `scripts/phase0_prepare_crossdocked_subset.py`
- `scripts/phase0_build_processed.py`
- `scripts/phase0_check_dataset.py`
- `scripts/phase0_make_splits.py`
- `scripts/phase0_make_balanced_manifest.py`
- `scripts/phase0_generate_visual_check_assets.py`
- `scripts/phase0_render_visual_check_images.py`
- `src/clash2feedback/data/prepare_raw_complexes.py`
- `src/clash2feedback/data/build_processed_dataset.py`
- `src/clash2feedback/data/check_dataset.py`
- `src/clash2feedback/data/split_dataset.py`
- `src/clash2feedback/data/balanced_manifest.py`
- `src/clash2feedback/data/visual_check_assets.py`
- `src/clash2feedback/data/render_visual_check.py`
- `src/clash2feedback/chemistry/rgroup.py`
- `src/clash2feedback/geometry/basic_clash_screen.py`

## 2. 提交数据选择

为了让网页版 ChatGPT 能复核实验结果, 本次选择提交以下轻量结果文件:

- `reports/phase0/summary.json`: 阶段 0 汇总指标和 acceptance status.
- `reports/phase0/dataset_check.csv`: 51 个 usable samples 的 per-sample 检查结果.
- `reports/phase0/failed_cases.csv`: 失败样本和失败原因.
- `reports/phase0/failure_reason_counts.csv`: 失败原因计数.
- `reports/phase0/threshold_calibration.csv`: 阈值分布表.
- `reports/phase0/visual_check_list.csv`: 可视化抽查候选列表.
- `reports/phase0/manual_check_template.csv`: 后续人工检查字段模板.
- `data/processed/v0_1/schema.json`: processed sample schema.
- `data/splits/v0_1/train.txt`, `val.txt`, `test.txt`, `split_report.csv`: 固定 split.
- `data/splits/v0_1/phase0_balanced_30.txt`: 阶段 1-3 mini-loop 建议优先使用的 target-balanced subset.

不提交以下文件:

- raw PDB / SDF / CIF.
- processed `.pkl`.
- `data/processed/v0_1/manifest.parquet`.
- Hugging Face cache 和下载 archive.
- `runs/phase0_visual_check/` 下的 raw structure 副本, ChimeraX 图片, PNG contact sheet 和运行脚本.
- `tmp/20260507/chimerax_downloads/` 和本地 ChimeraX 安装包.

原因:

- raw 和 processed 文件可以通过脚本复现, 且不适合直接进入 Git.
- `runs/phase0_visual_check/` 含结构副本和大量图片, 只作为本地人工检查资产.
- 网页版 ChatGPT 做阶段 0 结果分析主要需要轻量统计, schema, split 和代码逻辑.

## 3. 阶段 0 结果

阶段 0 的目标是把 raw protein-ligand complex 转换为 clean processed sample, 并固定后续阶段可复现的数据口径.

当前验收结论:

- `reports/phase0/summary.json` 中 `phase0_acceptance_status = complete`.
- clean usable samples: 51.
- failed cases: 1, 即 DiffSBDD `3rfm` 因 `ligand_heavy_atoms_out_of_range` 跳过.
- train / val / test split 已固定.
- `phase0_balanced_30_v0_1` 已生成, actual n = 28.
- ChimeraX 批量渲染图已生成, `render_manifest.csv` 中 864 个任务全部 `rendered`.
- 用户已查看 `runs/phase0_visual_check` 下可视化结果, 15 个样本逐项记录为 pass, 未发现明显问题.
- `conda run -n c2f_cpu pytest` 结果: 32 passed.

关键分布:

| 指标 | min | p25 | median | p75 | max |
|---|---:|---:|---:|---:|---:|
| ligand heavy atoms | 23 | 23 | 34 | 34.5 | 49 |
| 8A pocket atoms | 119 | 179 | 369 | 421 | 540 |
| min ligand-protein distance | 2.424 | 2.703 | 2.730 | 2.761 | 2.995 |
| obvious severe clash pairs | 0 | 0 | 0 | 0 | 0 |
| valid R-groups | 2 | 2 | 3 | 3 | 6 |

## 4. 数据口径

阶段 0 收尾采用两层数据口径:

- `phase0_clean_pool_v0_1`: 保留全部 51 个 phase0 usable clean samples.
- `phase0_balanced_30_v0_1`: 从 clean pool 派生的 target-balanced subset, up to 30 samples, actual n = 28.

clean pool target 分布:

| target / split_group | clean pool count |
|---|---:|
| `SMYD2_HUMAN_2_433_0` | 17 |
| `CDGT2_BACCI_28_713_0` | 16 |
| `IPPK_MOUSE_1_468_0` | 5 |
| `RARA_HUMAN_173_420_0` | 4 |
| `RIP1_MOMCH_24_270_0` | 3 |
| `HEPB_PEDHD_25_772_0` | 3 |
| `ODP1_ECOLI_2_887_0` | 2 |
| `complex_diffsbdd_5ndu` | 1 |

balanced subset 分布:

| target / split_group | balanced count |
|---|---:|
| `CDGT2_BACCI_28_713_0` | 5 |
| `IPPK_MOUSE_1_468_0` | 5 |
| `SMYD2_HUMAN_2_433_0` | 5 |
| `RARA_HUMAN_173_420_0` | 4 |
| `HEPB_PEDHD_25_772_0` | 3 |
| `RIP1_MOMCH_24_270_0` | 3 |
| `ODP1_ECOLI_2_887_0` | 2 |
| `complex_diffsbdd_5ndu` | 1 |

未满 30 的原因是当前只有 8 个 target, 且严格执行 `max_per_target = 5`; 不为了凑满 30 放宽 target cap.

## 5. 重要边界

- 当前 CrossDocked clean set 是 `task-specific clean subset for R-group local clash repair`, 不是 unbiased CrossDocked subset.
- ligand-only scaffold/R-group 预筛对本项目合理, 但会偏向可 Murcko scaffold 拆分, 至少有 2 个 valid R-groups, single-anchor 结构清楚的 ligand.
- `basic_clash_screen` 只用于阶段 0 的 obvious severe clash sanity gate, 不使用正式元素相关 vdW 半径, 不等价于阶段 1 的 clash detector.
- IF3 archive 当前使用 `*_pocket10.pdb`, 是 pocket-level protein structure, 不是 full receptor.
- 阶段 0 可视化图片只用于人工初筛, 不替代阶段 1 的正式 clash detector 和 repair verifier.

## 6. 建议网页端重点分析的问题

- 阶段 0 是否可以关闭, 有哪些残余风险需要在阶段 1 文档中声明.
- `phase0_balanced_30_v0_1` actual n = 28 是否足够支撑阶段 1-3 mini-loop.
- 阶段 1 clash detector 应采用哪些定义: 元素 vdW 半径, covalent exclusion, protein-ligand pair filtering, clash depth, R-group attribution.
- 阶段 1 repair verifier 应如何和 clash detector 解耦, 避免只优化一个过窄指标.
- 是否需要在进入阶段 2 前扩展更多 target-balanced clean samples.
- ligand-only prefilter 和 pocket10 数据边界在论文方法部分应如何表述.
- 后续是否需要单独构造 synthetic clash injection benchmark, 以及如何从 `phase0_balanced_30_v0_1` 派生.
