# 阶段 0 balanced subset 复盘

## 1. 选择结论

- clean pool 总数: 51.
- requested_max_samples: 30.
- actual_samples: 28.
- min_samples: 20.
- max_per_target: 5.
- 输出清单: `data/splits/v0_1/phase0_balanced_30.txt`.
- 选择原因: 当前只有 8 个 target, 且严格执行 max_per_target=5 后无法满 30; 选择 28 是为了优先保证 target diversity.
- `phase0_balanced_30_v0_1` 表示 target-balanced subset with up to 30 samples, actual n = 28.

## 2. Target 分布

| target | count |
|---|---|
| CDGT2_BACCI_28_713_0 | 5 |
| IPPK_MOUSE_1_468_0 | 5 |
| SMYD2_HUMAN_2_433_0 | 5 |
| RARA_HUMAN_173_420_0 | 4 |
| HEPB_PEDHD_25_772_0 | 3 |
| RIP1_MOMCH_24_270_0 | 3 |
| ODP1_ECOLI_2_887_0 | 2 |
| complex_diffsbdd_5ndu | 1 |

## 3. 数值分布

- ligand heavy atoms: count=28, min=23, median=34, max=49.
- 8A pocket atoms: count=28, min=119, median=368, max=540.
- valid R-groups: count=28, min=2, median=3, max=6.

## 4. 人工检查使用情况

| manual_check_status | count |
|---|---|
| unchecked | 28 |

## 5. 判断

- 是否覆盖至少 6 个 target: 是.
- 是否满足每个 target 最多 5 个: 是.
- 未满 30 不是失败; 本轮优先保证 target diversity, 不为凑满 30 放宽 target cap.
