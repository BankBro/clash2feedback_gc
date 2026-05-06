# 阶段 0 网页版 ChatGPT 分析上下文

## 1. 阅读入口

- GitHub 仓库: `BankBro/clash2feedback_gc`.
- 分支: `20260505-180108-phase0-implementation`.
- 当前阶段 0 完成提交: `33c3ffc Complete phase 0 data preparation and calibration workflow`.
- 建议优先阅读:
  - `README.md`
  - `tmp/20260506-phase0-final-summary.md`
  - `configs/phase0.yaml`
  - `scripts/phase0_prepare_diffsbdd_examples.py`
  - `scripts/phase0_prepare_crossdocked_subset.py`
  - `scripts/phase0_build_processed.py`
  - `scripts/phase0_check_dataset.py`
  - `scripts/phase0_make_splits.py`
  - `src/clash2feedback/data/prepare_raw_complexes.py`
  - `src/clash2feedback/data/build_processed_dataset.py`
  - `src/clash2feedback/data/check_dataset.py`
  - `src/clash2feedback/data/split_dataset.py`
  - `src/clash2feedback/chemistry/rgroup.py`
  - `src/clash2feedback/geometry/basic_clash_screen.py`

## 2. 提交数据选择

本次不提交 raw PDB/SDF/CIF, 不提交 processed pkl, 不提交 `manifest.parquet`, 不提交运行生成的 CSV/JSON 报告, 不提交 HF cache. 原因:

- raw complex 和 HF cache 来自公开数据源, 属于可再下载或可再抽取数据, 不应进 Git.
- processed pkl 和 manifest 是运行产物, 可由脚本复现.
- `reports/phase0/*.csv` 和 `reports/phase0/*.json` 是运行生成报告, 已被 `.gitignore` 忽略.
- 网页版 ChatGPT 分析所需的关键实验事实已压缩写入本文件和 `tmp/20260506-phase0-final-summary.md`.

如后续需要让网页端看更细粒度实验表, 建议只提交人工压缩后的 `tmp/*.md` 或极小 `tmp/*.csv` 摘要, 不提交原始结构文件和 pkl.

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

## 4. 最终阶段 0 结果

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
| pytest | 17 passed |

failed case:

| complex_id | source | failure_reason |
|---|---|---|
| `complex_diffsbdd_3rfm` | `diffsbdd_example` | `ligand_heavy_atoms_out_of_range` |

## 5. 阈值与分布

| 指标 | min | p25 | median | p75 | max |
|---|---:|---:|---:|---:|---:|
| ligand heavy atoms | 23 | 23 | 34 | 34.5 | 49 |
| 8A pocket atoms | 119 | 179 | 369 | 421 | 540 |
| min ligand-protein distance | 2.424 | 2.703 | 2.730 | 2.761 | 2.995 |
| obvious severe clash pairs | 0 | 0 | 0 | 0 | 0 |
| valid R-groups | 2 | 2 | 3 | 3 | 6 |

当前判断:

- strict 阈值暂不建议放宽.
- `basic_clash_screen` 只用于阶段 0 obvious severe clash 过滤, 不等价于正式 vdW clash detector.
- clean 数为 51, 超过原先目标区间 20-30, 但满足“至少 20 个 clean processed complexes”的阶段 0 结束标准.
- 如果后续希望保持 benchmark 更轻, 可以在准备阶段把 `--max-candidates` 调到 29-30, 或新增显式 downsample manifest 的轻量派生步骤.

## 6. Split 与抽查

- split 策略: `target_level`.
- CrossDocked 样本 split group source: `target_id`.
- DiffSBDD smoke split group source: `complex_id`.
- split 计数:
  - train: 27
  - val: 3
  - test: 21

target group 计数:

| split_group | count |
|---|---:|
| `SMYD2_HUMAN_2_433_0` | 17 |
| `CDGT2_BACCI_28_713_0` | 16 |
| `IPPK_MOUSE_1_468_0` | 5 |
| `RARA_HUMAN_173_420_0` | 4 |
| `RIP1_MOMCH_24_270_0` | 3 |
| `HEPB_PEDHD_25_772_0` | 3 |
| `ODP1_ECOLI_2_887_0` | 2 |
| `5ndu` | 1 |

visual check list 已生成, 推荐人工抽查至少 5 个 high priority 样本. 前 5 个为:

| complex_id | num_pocket_atoms_8A | num_valid_rgroups | priority |
|---|---:|---:|---|
| `complex_crossdocked_000001` | 119 | 2 | high |
| `complex_crossdocked_000002` | 157 | 2 | high |
| `complex_crossdocked_000003` | 165 | 2 | high |
| `complex_crossdocked_000004` | 179 | 2 | high |
| `complex_crossdocked_000005` | 151 | 2 | high |

## 7. 需要网页端重点分析的问题

- 阶段 0 是否可以正式视为完成, 或是否应把 clean 数从 51 下采样到 20-30 以更贴合最初目标.
- IF3 archive 中当前 clean 样本 target 分布不均, 例如 `SMYD2` 和 `CDGT2` 占比较高, 是否需要增加 target diversity 约束.
- ligand-only scaffold/R-group 预筛是否会引入选择偏差, 是否应在后续报告中显式标注.
- 当前 `basic_clash_screen` 阈值只过滤 obvious severe clash, 是否足够作为阶段 0 sanity gate.
- 阶段 1 前是否应该先补人工可视化抽查结果, 或补一个更小的 20-30 clean benchmark manifest.
