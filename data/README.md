# data

## 1. 目录说明

本目录存放数据输入和阶段产物. 大型原始数据, processed pickle, checkpoint 和缓存默认不提交.

## 2. 阶段 0 约定

- `raw_complexes/complex_xxxxxx/`: 原始 `protein.pdb` 或 `protein.cif`, `ligand.sdf`, 可选 `metadata.json`.
- `processed/v0_1/`: 阶段 0 clean sample, manifest 和 schema.
- `splits/v0_1/`: train, val, test 划分和 `split_report.csv`.
- `benchmarks/`: 后续失败样本基准.
- `candidate_pools/`: 后续候选池.
- `cache/`: 可删除缓存, 包括 HF 镜像下载的 CrossDocked 小子集文件.
