# 阶段 0 ligand-only 预筛偏差说明

## 1. 执行事实

- IF3 archive 流式扫描 paired candidates 数: 1132.
- ligand-only scaffold/R-group 预筛跳过数: 1082.
- 整理为 raw complex 的 IF3 CrossDocked 候选: 50.
- strict build 后 CrossDocked clean: 50.
- DiffSBDD official example strict clean: 1.

## 2. 预筛标准

ligand-only 预筛只读取 ligand SDF, 不使用 protein 坐标做正式判断. 当前预筛检查:

- RDKit 可读取并 sanitize.
- Murcko scaffold 可提取并通过基础 scaffold 合法性检查.
- R-group decomposition 可完成.
- phase0-valid R-group 数至少为 2.

这里的 phase0-valid R-group 指 single-anchor 且 heavy atoms 数在阶段 0 配置范围内的 R-group.

## 3. 为什么对本项目合理

Clash2Feedback-GC 第一版聚焦 R-group 局部碰撞修复. 如果配体没有清晰 scaffold/R-group/anchor 结构, 后续阶段很难定义“失败取代基”, 也难以构造局部修复 mask. 因此, 在阶段 0 小规模 clean subset 中先过滤掉不适合 R-group 任务的配体是合理的工程取舍.

## 4. 选择偏差

当前 CrossDocked clean set 经过 ligand-only scaffold/R-group 预筛, 因此是面向 R-group 局部碰撞修复任务的 task-specific clean subset, 不代表完整 CrossDocked 分布.

该预筛会偏向:

- 可 Murcko scaffold 拆分的配体.
- 至少有 2 个 valid R-groups 的配体.
- 单锚点 R-group 较清楚的配体.
- 对糖类、对称结构或 scaffold 定义特殊的分子可能有额外选择偏差.

## 5. 报告表述建议

后续报告和论文中应表述为:

> Current CrossDocked clean set is a task-specific clean subset for R-group local clash repair, selected with ligand-only scaffold/R-group prefiltering. It should not be interpreted as an unbiased CrossDocked subset.

后续如果扩展数据, 建议记录 `prefilter_reason_counts_by_target`, 用于判断某些 target 或 ligand family 是否被预筛系统性排除.
