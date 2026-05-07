# Clash2Feedback-GC

## 1. 项目简介

Clash2Feedback-GC 是一个面向生成式分子设计的工程与实验项目. 项目目标是把 protein-ligand complex 中的局部几何冲突转化为结构化反馈, 再用于后续的局部修复, 候选排序和验证评估.

当前仓库已完成阶段 0 的最小工程底座, 用于把 raw protein-ligand complex 转换为 clean processed sample.

阶段 0 收尾采用两层数据口径: `phase0_clean_pool_v0_1` 保留全部 clean samples; `phase0_balanced_30_v0_1` 是从 clean pool 派生的 target-balanced subset, up to 30 samples, 当前 actual n = 28.

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
| `tmp/` | 按日期归档的临时文件, 中间脚本和一次性输出 |

## 3. 统一约定

- Python 包名使用 `clash2feedback`, 路径为 `src/clash2feedback/`.
- 阶段脚本放在 `scripts/`, 命名格式为 `phaseN_*.py`.
- 静态方案文档放在 `docs/`.
- 实验报告放在 `reports/`.
- 较重运行产物放在 `runs/`.
- 临时文件放在 `tmp/`, 必要的实验复盘 Markdown 按 `tmp/YYYYMMDD/` 日期子目录归档, 可以保留并提交.
- 不使用顶层 `outputs/`.
- 大型原始数据, processed sample 和运行生成报告默认不提交到 Git.
- 使用 Hugging Face 数据源时, 优先检查镜像是否可用; 镜像可用时优先从镜像下载, 并将下载缓存显式放入项目内 `data/cache/`, 避免写入默认 `~/.cache/huggingface`.

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

准备 DiffSBDD official example smoke:

```bash
conda run -n c2f_cpu python scripts/phase0_prepare_diffsbdd_examples.py --output-root data/raw_complexes --force
```

准备 CrossDocked 小子集:

```bash
conda run -n c2f_cpu python scripts/phase0_prepare_crossdocked_subset.py \
  --auto-download \
  --download-root data/cache/crossdocked_downloads \
  --output-root data/raw_complexes \
  --max-candidates 50
```

如果 `THU-ATOM/crossdocked` 小测试源不足以筛出 20 个 clean complex, 可切换到 IF3 CrossDocked pocket10 archive 公开源:

```bash
conda run -n c2f_cpu python scripts/phase0_prepare_crossdocked_subset.py \
  --auto-download \
  --source if3_archive \
  --download-root data/cache/crossdocked_downloads \
  --output-root data/raw_complexes \
  --max-candidates 50 \
  --force
```

运行阶段 0:

```bash
conda run -n c2f_cpu python scripts/phase0_build_processed.py
conda run -n c2f_cpu python scripts/phase0_check_dataset.py
conda run -n c2f_cpu python scripts/phase0_make_splits.py
```

生成阶段 0 收尾 benchmark 和可视化抽查辅助资产:

```bash
conda run -n c2f_cpu python scripts/phase0_make_balanced_manifest.py \
  --manifest data/processed/v0_1/manifest.parquet \
  --visual-check reports/phase0/visual_check_list.csv \
  --output data/splits/v0_1/phase0_balanced_30.txt \
  --summary tmp/20260506/phase0-balanced30-summary.md \
  --max-samples 30 \
  --min-samples 20 \
  --max-per-target 5 \
  --seed 20260504

conda run -n c2f_cpu python scripts/phase0_generate_visual_check_assets.py \
  --visual-check reports/phase0/visual_check_list.csv \
  --manifest data/processed/v0_1/manifest.parquet \
  --num-samples 15 \
  --output-root runs/phase0_visual_check \
  --notes tmp/20260507/phase0-visual-check-notes.md

conda run -n c2f_cpu python scripts/phase0_render_visual_check_images.py \
  --assets-root runs/phase0_visual_check \
  --manifest runs/phase0_visual_check/render_manifest.csv \
  --summary tmp/20260507/phase0-visual-render-summary.md
```

主要输出:

- `data/processed/v0_1/complexes/*.pkl`
- `data/processed/v0_1/manifest.parquet`
- `data/processed/v0_1/schema.json`
- `data/splits/v0_1/train.txt`, `val.txt`, `test.txt`, `split_report.csv`
- `data/splits/v0_1/phase0_balanced_30.txt`
- `reports/phase0/dataset_check.csv`, `failed_cases.csv`, `summary.json`
- `reports/phase0/threshold_calibration.csv`, `failure_reason_counts.csv`, `visual_check_list.csv`
- `runs/phase0_visual_check/`

`runs/phase0_visual_check/complex_xxx/` 是本地可下载的人工抽查包, 包含 `protein.pdb`, `ligand.sdf`, `view_overview.cxc`, `view_clash.cxc`, `view_rgroup.cxc`, `view_ligand.cxc` 和 `view.pml`. 默认抽样 15 个样本. 下载单个样本目录后, 在该目录依次运行 `chimerax view_overview.cxc`, `chimerax view_clash.cxc`, `chimerax view_rgroup.cxc`, `chimerax view_ligand.cxc` 即可查看 pocket-ligand, vdW sphere clash sanity, scaffold/R-group/anchor 高亮和 ligand-only 拆分视图.

`phase0_render_visual_check_images.py` 用服务器端 ChimeraX 批量生成 PNG 初筛图. 默认对每个样本生成 `overview`, `clash`, `rgroup`, `ligand` 四类视图, 每类从 1024 个 ligand-centered 候选方向及额外结构方向中自动选择 `clear_01` 到 `clear_12` 十二个少遮挡视角, 并为每类视图生成一张 `3 x 4` contact sheet, 例如 `clash_contact_sheet.png`. 单图默认保持 `1800 x 1400`, contact sheet 不降采样, 便于放大检查细节. 视角选择先做分层硬过滤, 优先要求 ligand center line 不被 protein 阻挡, ligand 和关键坐标可见, 再按视图用途分别评分: `overview` 偏向口袋入口无遮挡, `clash` 偏向 protein-ligand 接触界面可见, `rgroup` 偏向 scaffold/R-group/anchor 连接可见, `ligand` 偏向配体投影展开. 若严格条件不足 12 张, 会按 `relaxed`, `fallback`, `score_only` 逐级回退, 并在 manifest 的 `camera_selection_tier` 中记录. 同一 `sample_id + view` 的 clear 视角会分组放入同一个 ChimeraX 进程连续保存, 避免每张图重复启动渲染器. `rgroup` 和 `ligand` 视图会缩小 scaffold/R-group marker, 便于看清 ligand 拆分关系; 非 ligand-only 图片会在渲染后做 PNG 方向校正, 尽量让 protein pocket 位于 ligand 下方. 如需回退旧视角, 使用 `--camera-mode fixed-angles`. 这些图片只用于人工初筛, 不替代阶段 1 正式 clash detector.

## 5. 测试

```bash
conda run -n c2f_cpu pytest
```

当前本地 Python 如未安装 RDKit 或 Biopython, 对应化学和结构读取测试会自动跳过.

## 6. 协作说明

修改仓库前先阅读根目录 `AGENTS.md`. 修改主目录内文件时, 同步阅读该目录下的 `AGENTS.md`.
