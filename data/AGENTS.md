# data 协作规范

## 1. 目录职责

- `raw_complexes/`: 原始 protein, ligand 和 metadata, 默认不改写.
- `processed/`: 阶段 0 生成的 clean complexes.
- `splits/`: train, val, test 划分和划分报告.
- `benchmarks/`: 阶段 2 和阶段 8 的失败样本基准.
- `candidate_pools/`: 阶段 5 排序器和适配器训练用候选池.
- `cache/`: 可删除缓存.

## 2. 数据规则

- 不提交大型数据文件, checkpoint, 运行日志或本地缓存.
- `.gitkeep` 只用于保留空目录, 有真实文件后可按需要删除.
- 修改原始数据前必须确认任务明确要求, 并记录来源和处理方式.
- 生成数据时优先写入版本化子目录, 例如 `v0_1/`.
- 数据格式, manifest 字段和验收标准应在相关实现或报告中保持可追溯.
