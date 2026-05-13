# Phase 3 Label Provenance Audit

## 1. Scope

- 阶段 3 = label provenance audit + circularity risk audit + construction consistency check + phase4 mask seed generation.
- 阶段 3 不承担 independent locator benchmark 职责.
- `target_rgroup` 是人工扰动标签和参考掩码来源, 不是无偏定位真值.
- `predicted_dominant_valid_rgroup` 是 operational mask policy, 不是 ground truth.

## 2. Counts

- phase2 manifest rows: 2610
- S0 rows: 1185
- S1 rows: 467
- S2 rows: 357
- phase4 mask seed rows: 357

## 3. Provenance Decisions

- `target_score_ratio_valid` 来自 attribution-derived valid R-group scores, 并参与 supported gate.
- `supported_single_rgroup` 是 clean local repair substrate.
- phase2.5 model-induced rows 没有进入 construction consistency denominator.
