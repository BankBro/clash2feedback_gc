# Phase 3 Circularity Risk Audit

## 1. Risk Statement

- S2 使用 detector / attribution / target-dominance gates 过滤, circularity risk level 为 high.
- S2 上的 Top-1 / Top-3 只解释为 construction consistency check.
- S0 / S1 只做辅助审计和压力分析, 不作为阶段 4 主输入.

## 2. Construction Consistency

- denominator set: S2_phase2_supported_single_rgroup
- denominator: 357
- top1 predicted equals oracle: 357 / 357
- top3 target in top valid R-groups: 357 / 357

## 3. Phase 4 Mask Policy

- Oracle mask: target R-group entire atom set.
- Predicted mask: predicted dominant valid R-group entire atom set.
- Random mask: same-ligand size-matched valid single-anchor R-group.
- Anchor is recorded separately and is not added to the free edit mask by default.
