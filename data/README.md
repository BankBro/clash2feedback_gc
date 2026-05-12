# data

## 1. 目录说明

本目录存放数据输入和阶段产物. 大型原始数据, processed pickle, checkpoint 和缓存默认不提交.

## 2. 阶段 0 约定

- `raw_complexes/complex_xxxxxx/`: 原始 `protein.pdb` 或 `protein.cif`, `ligand.sdf`, 可选 `metadata.json`.
- `processed/v0_1/`: 阶段 0 clean sample, manifest 和 schema.
- `splits/v0_1/`: train, val, test 划分, `split_report.csv` 和派生 benchmark 清单, 例如 `phase0_balanced_30.txt`.
- `benchmarks/clashrepairbench_rg_artificial/v0_1/`: 阶段 2 controlled synthetic failed pose benchmark, 包含 manifest, schema, samples 和 original/failed ligand SDF.
- `benchmarks/model_induced/v0_1/`: 后续阶段 8 model-induced repair evaluation benchmark 预留位置. 阶段 2.5 只生成 reports/runs 审计产物, 不把 generated samples 混入阶段 3 主评估, 也不回改 `phase2_v0_1`.
- `candidate_pools/`: 后续候选池.
- `cache/`: 可删除缓存, 包括 HF 镜像下载的 CrossDocked 小子集文件.

`phase0_balanced_30.txt` 是从 clean pool 派生的 target-balanced 清单, 不是 raw/processed 数据副本, 默认作为运行产物不提交.
