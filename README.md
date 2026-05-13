# Clash2Feedback-GC

## 1. 项目简介

Clash2Feedback-GC 是一个面向生成式分子设计的工程与实验项目. 项目目标是把 protein-ligand complex 中的局部几何冲突转化为结构化反馈, 再用于后续的局部修复, 候选排序和验证评估.

当前仓库已完成阶段 0 的最小工程底座, 用于把 raw protein-ligand complex 转换为 clean processed sample.

阶段 0 收尾采用两层数据口径: `phase0_clean_pool_v0_1` 保留全部 clean samples; `phase0_balanced_30_v0_1` 是从 clean pool 派生的 target-balanced subset, up to 30 samples, 当前 actual n = 28.

阶段 1 方案详见 `docs/20260508-Clash2Feedback-GC_阶段1碰撞检测器与可靠验证器方案.md`. 阶段 1 默认使用 pocket-level receptor scope: `phase0_pocket8` 用于 old clash diagnosis 和 R-group attribution, `pocket10_all_atoms` 用于 local new clash check; full receptor check 为后续阶段可选扩展.

阶段 2 方案详见 `docs/20260510-Clash2Feedback-GC_阶段2人工局部碰撞注入最终落地方案.md`. 阶段 2 构建 controlled synthetic failed pose benchmark, 不调用生成器, 不做 repair, 不做 whole protein-ligand complex minimization; `target_rgroup` 是人工扰动标签, `supported_single_rgroup` 是经过 detector / attribution / target-dominance gates 过滤后的 clean local repair substrate.

阶段 2.5 方案详见 `docs/20260511-Clash2Feedback-GC_阶段2.5模型诱导失败外部有效性审计落地方案.md`. 阶段 2.5 是 model-induced failure external validity audit: 使用 frozen generation baseline 生成 candidates, 审计 all generated samples 的 ligand validity, protein-ligand clash, R-group attribution, failure taxonomy 和 repairability proxy. 阶段 2.5 不训练模型, 不做 repair, 不做 baseline ranking, 不回改 `phase2_v0_1`, 也不把 model-induced samples 混入阶段 3 construction consistency denominator.

后续阶段 3 仍叫阶段 3, 但新口径是 label provenance audit, circularity risk audit, construction consistency check 和 phase4 mask seed generation. `supported_single_rgroup` 上的 Top-1 / Top-3 只能作为 construction consistency check, 不能作为 independent localization benchmark.

后续阶段 4 将先做 backend feasibility audit, 再做 Random / Predicted / Oracle formal repair loop. 阶段 4 的 predicted mask 是 operational mask policy, 不是 ground truth; DiffDec / DiffSBDD plain backend 只能视为 local constrained resampling, 只有实现 clash penalty / hot region guidance 并改采样过程后, 才能声称 `H_clash` 进入生成过程.

`reports/phase2_injection/phase2_final_report.md` 是历史阶段 2 关闭报告, 其中保留的阶段 3 Top-1 / Top-3 建议属于旧口径. 当前后续执行以 `docs/` 中更新后的阶段 3 新口径为准, 不回写历史实验报告.

外部 frozen baseline 的长期可复现入口见 `docs/external_baselines.md`, 当前记录 DiffSBDD 的 source repo, pinned commit, checkpoint, 关键源码路径和输出口径.

## 2. 目录结构

| 目录 | 说明 |
|---|---|
| `docs/` | 方案文档和实验路线说明 |
| `configs/` | 每个阶段的配置文件 |
| `data/` | 原始数据, 处理数据, 数据划分, benchmark 和 candidate pool |
| `external/` | 外部 baseline 仓库和公开 checkpoint 的本地副本 |
| `reports/` | 各阶段生成的统计表, 图, summary 和检查报告 |
| `runs/` | 日志, checkpoint, 生成候选等较重运行产物 |
| `src/clash2feedback/` | 可复用 Python 包源码 |
| `scripts/` | 阶段命令行入口 |
| `tests/` | 自动化测试 |
| `tmp/` | 按日期归档的临时文件, 中间脚本和一次性输出 |

## 3. 统一约定

- Python 包名使用 `clash2feedback`, 路径为 `src/clash2feedback/`.
- 阶段脚本放在 `scripts/`, 命名格式为 `phaseN_*.py`.
- 静态方案文档放在 `docs/`.
- 实验报告放在 `reports/`.
- 较重运行产物放在 `runs/`.
- 外部 baseline 仓库和 checkpoint 放在 `external/`, 默认不提交 Git.
- 外部 baseline 的 repo, commit, checkpoint 和关键代码路径统一登记在 `docs/external_baselines.md`.
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
conda run -n c2f_cpu python -m compileall src scripts
conda run -n c2f_cpu python -m pytest
```

当前本地 Python 如未安装 RDKit 或 Biopython, 对应化学和结构读取测试会自动跳过.

## 6. 阶段 1 用法

运行正式 vdW clash detector, R-group attribution 和 verifier smoke:

```bash
conda run -n c2f_cpu python scripts/phase1_check_clashes.py \
  --config configs/phase1_clash_detector.yaml \
  --manifest data/processed/v0_1/manifest.parquet \
  --balanced-subset data/splits/v0_1/phase0_balanced_30.txt \
  --output-root reports/phase1_clash_detector
```

主要输出:

- `reports/phase1_clash_detector/summary.json`
- `reports/phase1_clash_detector/clean_clash_report.csv`
- `reports/phase1_clash_detector/balanced_clash_report.csv`
- `reports/phase1_clash_detector/threshold_sensitivity.csv`
- `reports/phase1_clash_detector/rgroup_attribution_report.csv`
- `reports/phase1_clash_detector/failure_type_counts.csv`
- `reports/phase1_clash_detector/verifier_smoke_report.csv`
- `reports/phase1_clash_detector/unsupported_cases.csv`
- `reports/phase1_clash_detector/vdw_radius_table.json`
- `reports/phase1_clash_detector/strict_delta_false_positive_cases.csv`
- `reports/phase1_clash_detector/nonsevere_contact_stats.csv`
- `reports/phase1_clash_detector/scope_comparison.csv`

## 7. 阶段 2 用法

运行人工局部碰撞注入 benchmark 构建:

```bash
conda run -n c2f_cpu python scripts/phase2_inject_artificial_clashes.py \
  --config configs/phase2_injection.yaml \
  --manifest data/processed/v0_1/manifest.parquet \
  --phase1-report-root reports/phase1_clash_detector \
  --output-root data/benchmarks/clashrepairbench_rg_artificial/v0_1 \
  --report-root reports/phase2_injection
```

主要输出:

- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/manifest.parquet`
- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/schema.json`
- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/samples/*.pkl`
- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/ligands/*_original.sdf`
- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/ligands/*_failed.sdf`
- `reports/phase2_injection/summary.json`
- `reports/phase2_injection/phase2_completion_audit.md`

`predicted_dominant_*` 字段只记录阶段 1 attribution 结果, 不作为阶段 2 主集保留条件. 但 `target_score_ratio_valid` 来自 attribution-derived valid R-group scores, 因此 supported 主集后续只作为 clean local repair substrate 和 construction consistency check 输入. 所有 injected variants 继承 base complex split.

## 8. 阶段 2.5 用法

先准备 DiffSBDD 外部仓库, checkpoint 和独立 `diffsbdd` 环境:

```bash
conda run -n c2f_cpu python scripts/phase2_5_prepare_diffsbdd.py \
  --config configs/phase2_5_model_induced_audit.yaml \
  --report-root reports/phase2_5_model_induced_audit \
  --run-root runs/phase2_5_model_induced_audit
```

再运行 training-overlap audit:

```bash
conda run -n c2f_cpu python scripts/phase2_5_training_overlap_audit.py \
  --config configs/phase2_5_model_induced_audit.yaml \
  --manifest data/processed/v0_1/manifest.parquet \
  --output-root reports/phase2_5_model_induced_audit
```

再运行 model-induced audit wrapper:

```bash
conda run -n c2f_cpu python scripts/phase2_5_model_induced_audit.py \
  --config configs/phase2_5_model_induced_audit.yaml \
  --manifest data/processed/v0_1/manifest.parquet \
  --phase1-report-root reports/phase1_clash_detector \
  --phase2-benchmark-root data/benchmarks/clashrepairbench_rg_artificial/v0_1 \
  --run-root runs/phase2_5_model_induced_audit \
  --report-root reports/phase2_5_model_induced_audit
```

主要输出:

- `reports/phase2_5_model_induced_audit/summary.json`
- `reports/phase2_5_model_induced_audit/training_overlap_audit.csv`
- `reports/phase2_5_model_induced_audit/base_pocket_selection.csv`
- `reports/phase2_5_model_induced_audit/generation_manifest.parquet`
- `reports/phase2_5_model_induced_audit/failure_taxonomy.csv`
- `reports/phase2_5_model_induced_audit/phase2_5_completion_audit.md`
- `runs/phase2_5_model_induced_audit/`

若 DiffSBDD 仓库, checkpoint, official split, GPU 或生成数据缺失, 脚本会生成 schema-valid 报告并把原因写入 blocked, 不伪造 generation / taxonomy 结果.

## 9. 协作说明

修改仓库前先阅读根目录 `AGENTS.md`. 修改主目录内文件时, 同步阅读该目录下的 `AGENTS.md`.
