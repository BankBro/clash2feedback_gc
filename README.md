# Clash2Feedback-GC

## 1. 项目简介

Clash2Feedback-GC 是一个面向生成式分子设计的工程与实验项目. 项目目标是把 protein-ligand complex 中的局部几何冲突转化为结构化反馈, 再用于后续的局部修复, 候选排序和验证评估.

当前仓库已完成阶段 0 的最小工程底座, 用于把 raw protein-ligand complex 转换为 clean processed sample.

## 2. 目录结构

| 目录 | 说明 |
|---|---|
| `docs/` | 方案文档和实验路线说明 |
| `configs/` | 每个阶段的配置文件 |
| `data/` | 原始数据, 处理数据, 数据划分, benchmark 和 candidate pool |
| `reports/` | 各阶段生成的统计表, 图, summary 和检查报告 |
| `runs/` | 日志, checkpoint, 生成候选等较重运行产物 |
| `src/clash2feedback/` | 可复用 Python 包源码 |
| `scripts/` | 阶段命令行入口 |
| `tests/` | 阶段 0 自动化测试 |

## 3. 统一约定

- Python 包名使用 `clash2feedback`, 路径为 `src/clash2feedback/`.
- 阶段脚本放在 `scripts/`, 命名格式为 `phaseN_*.py`.
- 静态方案文档放在 `docs/`.
- 实验报告放在 `reports/`.
- 较重运行产物放在 `runs/`.
- 不使用顶层 `outputs/`.
- 大型原始数据, processed sample 和运行生成报告默认不提交到 Git.

## 4. 阶段 0 用法

创建或更新环境:

```bash
conda env create -f environment.yml
conda env update -f environment.yml
conda run -n c2f_cpu python -m pip install --no-build-isolation -e .
```

最后一行会以 editable 方式安装本仓库, 便于脚本和交互式 Python 直接导入 `clash2feedback`.

准备 raw complex:

```text
data/raw_complexes/complex_000001/
  protein.pdb
  ligand.sdf
  metadata.json
```

运行阶段 0:

```bash
conda run -n c2f_cpu python scripts/phase0_build_processed.py
conda run -n c2f_cpu python scripts/phase0_make_splits.py
conda run -n c2f_cpu python scripts/phase0_check_dataset.py
```

主要输出:

- `data/processed/v0_1/complexes/*.pkl`
- `data/processed/v0_1/manifest.parquet`
- `data/processed/v0_1/schema.json`
- `data/splits/v0_1/train.txt`, `val.txt`, `test.txt`, `split_report.csv`
- `reports/phase0/dataset_check.csv`, `failed_cases.csv`, `summary.json`, `visual_check_list.csv`

## 5. 测试

```bash
conda run -n c2f_cpu pytest
```

当前本地 Python 如未安装 RDKit 或 Biopython, 对应化学和结构读取测试会自动跳过.

## 6. 协作说明

修改仓库前先阅读根目录 `AGENTS.md`. 修改主目录内文件时, 同步阅读该目录下的 `AGENTS.md`.
