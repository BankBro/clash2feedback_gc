# 阶段 0 target 分布复盘

## 1. clean pool 分布

`phase0_clean_pool_v0_1` 保留 51 个 clean samples. 其中 CrossDocked / IF3 pocket10 样本 50 个, DiffSBDD example clean 样本 1 个.

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

前两个 target 合计 33 / 51, 占比约 64.7%. 这不是阶段 0 工程错误, 但如果后续直接使用全部 clean pool, 结果可能主要反映少数 target.

## 2. balanced subset 分布

`phase0_balanced_30_v0_1` 是 target-balanced subset with up to 30 samples, actual n = 28.

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

requested_max_samples = 30, actual_samples = 28, max_per_target = 5. 未满 30 的原因是当前只有 8 个 target, 且严格执行 target cap 后无法满 30. 选择 28 是为了优先保证 target diversity, 而不是最大化样本数.

## 3. 后续使用建议

- 阶段 0 的 51 个 clean samples 保留为 `phase0_clean_pool_v0_1`, 不删除.
- 阶段 1-3 mini-loop 优先使用 `phase0_balanced_30_v0_1`, 避免 SMYD2 / CDGT2 过度主导结果.
- 当前 balanced subset 仍然保留了少数 target 样本量差异, 但不再存在单 target 过度集中到 16-17 个样本的问题.
- 后续重新采样建议使用 target-aware streaming selection, 不再只按 archive 顺序凑够 clean 样本后停止.
