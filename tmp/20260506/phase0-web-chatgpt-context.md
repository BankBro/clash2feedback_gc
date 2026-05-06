# 阶段 0 网页版 ChatGPT 分析上下文

## 1. 阅读入口

- GitHub 仓库: `BankBro/clash2feedback_gc`.
- 分支: `20260505-180108-phase0-implementation`.
- 当前文档对应阶段: phase 0 closeout, visual check pending.
- 建议优先阅读:
  - `README.md`
  - `tmp/README.md`
  - `tmp/20260506/phase0-final-summary.md`
  - `tmp/20260506/phase0-closeout-summary.md`
  - `tmp/20260506/phase0-balanced30-summary.md`
  - `tmp/20260506/phase0-target-distribution-summary.md`
  - `tmp/20260506/phase0-prefilter-bias-notes.md`
  - `tmp/20260506/phase0-visual-check-notes.md`
  - `configs/phase0.yaml`
  - `scripts/phase0_prepare_crossdocked_subset.py`
  - `scripts/phase0_make_balanced_manifest.py`
  - `scripts/phase0_generate_visual_check_assets.py`
  - `src/clash2feedback/data/prepare_raw_complexes.py`
  - `src/clash2feedback/data/build_processed_dataset.py`
  - `src/clash2feedback/data/check_dataset.py`
  - `src/clash2feedback/data/split_dataset.py`
  - `src/clash2feedback/data/balanced_manifest.py`
  - `src/clash2feedback/data/visual_check_assets.py`
  - `src/clash2feedback/chemistry/rgroup.py`
  - `src/clash2feedback/geometry/basic_clash_screen.py`

## 2. 提交数据选择

本次提交给网页版 ChatGPT 的内容只包括代码、配置、文档、测试和轻量 Markdown 复盘. 不提交以下文件:

- raw PDB / SDF / CIF.
- processed `.pkl`.
- `manifest.parquet` 和 `schema.json`.
- `reports/phase0/*.csv` / `reports/phase0/*.json`.
- `data/cache/`.
- `runs/phase0_visual_check/` 下的 portable visual check packages, 因为其中包含 `protein.pdb` 和 `ligand.sdf` 副本.
- PNG 截图或其他大型运行产物.

原因:

- raw complex 和 HF cache 来自公开数据源, 可由脚本复现或重新抽取, 不应进 Git.
- processed pkl, manifest 和 reports 是运行产物, 已由 `.gitignore` 忽略.
- 网页版 ChatGPT 分析阶段 0 设计、风险和下一步建议时, 只需要轻量统计和代码路径.
- 如果需要人工可视化, 用户应在本地从 `runs/phase0_visual_check/complex_xxx/` 下载便携样本包, 但这些包不提交 Git.

## 3. 数据源与获取结果

- DiffSBDD official example:
  - 来源: `arneschneuing/DiffSBDD` GitHub example.
  - 结果: `5ndu` strict 通过, `3rfm` 因 `ligand_heavy_atoms_out_of_range` 跳过.

- `THU-ATOM/crossdocked`:
  - 优先通过 `https://hf-mirror.com/datasets/THU-ATOM/crossdocked` 访问.
  - API 和文件可访问.
  - 初始 50 个候选 strict 后只有 13 个 CrossDocked clean.
  - 加入 ligand-only scaffold/R-group 预筛后, 该小测试源最多整理出 17 个可用候选, 仍低于阶段 0 验收线.
  - 主要不足原因: `not_enough_valid_rgroups`.

- `Yukk1Zz/if3-crossdocked2020`:
  - 通过 HF mirror 访问 `crossdocked_pocket10.tar.gz`.
  - 使用流式读取, 未把 1.6GB tar.gz 写入默认 `~/.cache/huggingface`.
  - 抽取文件缓存显式放在项目内 `data/cache/crossdocked_downloads/`.
  - 最终作为阶段 0 CrossDocked 小子集验收数据源.

## 4. 阶段 0 当前结果

| 指标 | 数值 |
|---|---:|
| IF3 archive 流式扫描 paired candidates | 1132 |
| ligand-only 预筛跳过 | 1082 |
| 整理为 raw complex 的 IF3 CrossDocked 候选 | 50 |
| strict processed 总数 | 51 |
| CrossDocked clean 数 | 50 |
| DiffSBDD clean 数 | 1 |
| failed cases | 1 |
| phase0 usable | 51 |
| pytest | 22 passed |

failed case:

| complex_id | source | failure_reason |
|---|---|---|
| `complex_diffsbdd_3rfm` | `diffsbdd_example` | `ligand_heavy_atoms_out_of_range` |

当前结论:

- 阶段 0 工程验收通过.
- 51 个 clean samples 保留为 `phase0_clean_pool_v0_1`.
- 不删除 51 个 clean samples.
- 进入阶段 1 前, 仍需要人工可视化抽查签字.

## 5. 阈值与分布

| 指标 | min | p25 | median | p75 | max |
|---|---:|---:|---:|---:|---:|
| ligand heavy atoms | 23 | 23 | 34 | 34.5 | 49 |
| 8A pocket atoms | 119 | 179 | 369 | 421 | 540 |
| min ligand-protein distance | 2.424 | 2.703 | 2.730 | 2.761 | 2.995 |
| obvious severe clash pairs | 0 | 0 | 0 | 0 | 0 |
| valid R-groups | 2 | 2 | 3 | 3 | 6 |

注意:

- strict 阈值暂不建议放宽.
- `basic_clash_screen` 只用于阶段 0 obvious severe clash sanity gate, 不等价于正式 vdW clash detector.
- `pocket10` 是 ligand 周围约 10 Å 的 pocket-level protein structure, 不是 full receptor.

## 6. Target 分布与 balanced subset

clean pool target group 计数:

| split_group | clean pool count |
|---|---:|
| `SMYD2_HUMAN_2_433_0` | 17 |
| `CDGT2_BACCI_28_713_0` | 16 |
| `IPPK_MOUSE_1_468_0` | 5 |
| `RARA_HUMAN_173_420_0` | 4 |
| `RIP1_MOMCH_24_270_0` | 3 |
| `HEPB_PEDHD_25_772_0` | 3 |
| `ODP1_ECOLI_2_887_0` | 2 |
| `complex_diffsbdd_5ndu` | 1 |

前两个 target 合计 33 / 51, 约 64.7%. 这不是阶段 0 工程错误, 但会影响后续 mini-loop 的代表性.

已派生:

```text
phase0_balanced_30_v0_1
```

balanced subset 是 up to 30 samples, actual n = 28:

| split_group | balanced count |
|---|---:|
| `CDGT2_BACCI_28_713_0` | 5 |
| `IPPK_MOUSE_1_468_0` | 5 |
| `SMYD2_HUMAN_2_433_0` | 5 |
| `RARA_HUMAN_173_420_0` | 4 |
| `HEPB_PEDHD_25_772_0` | 3 |
| `RIP1_MOMCH_24_270_0` | 3 |
| `ODP1_ECOLI_2_887_0` | 2 |
| `complex_diffsbdd_5ndu` | 1 |

requested_max_samples = 30, actual_samples = 28, max_per_target = 5. 未满 30 是因为严格执行 target cap, 当前只有 8 个 target, 不为了凑满 30 放宽到每 target 6 个.

## 7. ligand-only prefilter 偏差

当前 CrossDocked clean set 经过 ligand-only scaffold/R-group 预筛, 因此应表述为:

```text
task-specific clean subset for R-group local clash repair
```

不应表述为:

```text
unbiased CrossDocked subset
```

该预筛对当前任务合理, 因为第一版只聚焦 single-anchor R-group 局部修复. 但它会偏向可 Murcko scaffold 拆分、至少有 2 个 valid R-groups、single-anchor 清楚的 ligand.

后续建议统计 `prefilter_reason_counts_by_target`.

## 8. 可视化检查状态

人工可视化检查尚未完成, 当前状态应写为:

```text
visual_check_status = pending
manual_check_status = to_be_filled
```

已生成便携式 ChimeraX / PyMOL 检查包到本地运行目录:

```text
runs/phase0_visual_check/complex_xxx/
```

每个本地样本包包含:

```text
protein.pdb
ligand.sdf
view.cxc
view.pml
projection.png
```

`view.cxc` 和 `view.pml` 已改为相对路径. 用户下载单个 `complex_xxx/` 目录到本地后, 可以在该目录运行:

```bash
chimerax view.cxc
```

由于 `runs/phase0_visual_check/` 包含 raw structure 副本和 PNG, 默认不提交 Git. Web 端 ChatGPT 只能看到本文件中的状态摘要, 看不到实际结构图.

当前建议至少人工看 5 个 high-priority 样本:

| complex_id | target_id | status |
|---|---|---|
| `complex_crossdocked_000001` | `CDGT2_BACCI_28_713_0` | pending |
| `complex_crossdocked_000002` | `CDGT2_BACCI_28_713_0` | pending |
| `complex_crossdocked_000003` | `CDGT2_BACCI_28_713_0` | pending |
| `complex_crossdocked_000004` | `CDGT2_BACCI_28_713_0` | pending |
| `complex_crossdocked_000005` | `CDGT2_BACCI_28_713_0` | pending |

检查项:

- ligand 是否在 pocket 中.
- pocket 是否围绕 ligand.
- scaffold / R-group / anchor 是否明显合理.
- 是否有肉眼可见的严重重叠.

## 9. 需要网页端重点分析的问题

- 阶段 0 工程是否可以关闭, 在 visual check pending 的前提下是否应阻止进入阶段 1.
- `phase0_clean_pool_v0_1` 保留 51 个样本, `phase0_balanced_30_v0_1` 使用 actual n = 28 是否合理.
- target 分布不均是否还需要进一步处理, 是否需要 target-aware streaming reselection.
- ligand-only scaffold/R-group 预筛偏差是否可以接受, 在论文或报告中如何准确表述.
- `basic_clash_screen` 作为阶段 0 sanity gate 是否足够, 以及阶段 1 正式 clash detector 应避免复用哪些阶段 0 简化假设.
- pocket10 不是 full receptor 这一边界, 对后续生成器接入和验证会有什么影响.
- 人工 visual check 的最小样本数和判定模板是否足够.
