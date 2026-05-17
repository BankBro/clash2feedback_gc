# scripts

## 1. 目录说明

本目录存放阶段命令行入口. 复杂逻辑放在 `src/clash2feedback/`, 脚本只负责参数解析, 配置读取和流程编排.

## 2. 阶段 0 命令

```bash
python scripts/phase0_prepare_diffsbdd_examples.py --output-root data/raw_complexes --force
python scripts/phase0_prepare_crossdocked_subset.py --auto-download --download-root data/cache/crossdocked_downloads --output-root data/raw_complexes --max-candidates 50
python scripts/phase0_prepare_crossdocked_subset.py --auto-download --source if3_archive --download-root data/cache/crossdocked_downloads --output-root data/raw_complexes --max-candidates 50 --force
python scripts/phase0_build_processed.py --config configs/phase0.yaml
python scripts/phase0_check_dataset.py --config configs/phase0.yaml
python scripts/phase0_make_splits.py --config configs/phase0.yaml
python scripts/phase0_make_balanced_manifest.py --manifest data/processed/v0_1/manifest.parquet --visual-check reports/phase0/visual_check_list.csv --output data/splits/v0_1/phase0_balanced_30.txt --summary tmp/20260506/phase0-balanced30-summary.md --max-samples 30 --min-samples 20 --max-per-target 5 --seed 20260504
python scripts/phase0_generate_visual_check_assets.py --visual-check reports/phase0/visual_check_list.csv --manifest data/processed/v0_1/manifest.parquet --num-samples 15 --output-root runs/phase0_visual_check --notes tmp/20260507/phase0-visual-check-notes.md
python scripts/phase0_render_visual_check_images.py --assets-root runs/phase0_visual_check --manifest runs/phase0_visual_check/render_manifest.csv --summary tmp/20260507/phase0-visual-render-summary.md
```

`phase0_prepare_crossdocked_subset.py` 优先通过 HF 镜像读取 `THU-ATOM/crossdocked`; 若该小测试源 clean 数不足, 可用 `--source if3_archive` 从 `Yukk1Zz/if3-crossdocked2020` 的 pocket10 archive 流式抽取候选. 下载缓存写入项目内 `data/cache/`.

`phase0_make_balanced_manifest.py` 只生成派生样本清单, 不删除或替换 51 个 clean pool. `phase0_generate_visual_check_assets.py` 只生成可视化辅助资产和人工检查 notes, 不把自动图片解释为人工 pass. `phase0_render_visual_check_images.py` 调用服务器端 ChimeraX 批量生成 PNG 初筛图, 默认每个样本输出 4 类视图 x 12 个 `clear_*` 少遮挡视角, 并为每个 `sample_id + view` 生成 `3 x 4` contact sheet. 批量图会以 ligand 为中心, 默认从 1024 个候选方向及额外结构方向中选择; 选择时先按 `strict`, `relaxed`, `fallback`, `score_only` 做分层硬过滤, 优先剔除 ligand center line 被 protein 阻挡, ligand 或关键坐标遮挡严重, 投影过小的视角, 再按视图用途评分: `overview` 看 pocket, `clash` 看接触界面, `rgroup` 看 scaffold/R-group/anchor, `ligand` 看配体拆分. 回退层级会写入 manifest 的 `camera_selection_tier`; 同一 `sample_id + view` 的 clear 视角会分组放入同一个 ChimeraX 进程连续保存; `rgroup` 和 `ligand` 会缩小 marker 以减少遮挡; 非 ligand-only 图片会做 PNG 方向校正, 尽量让 protein pocket 位于 ligand 下方. 旧的 `front/back/left/right/top/bottom/iso` 视角可通过 `--camera-mode fixed-angles` 使用.

## 3. 阶段 1 命令

```bash
python scripts/phase1_check_clashes.py \
  --config configs/phase1_clash_detector.yaml \
  --manifest data/processed/v0_1/manifest.parquet \
  --balanced-subset data/splits/v0_1/phase0_balanced_30.txt \
  --output-root reports/phase1_clash_detector
```

`phase1_check_clashes.py` 读取阶段 0 clean pool 和 balanced subset, 生成正式 vdW clash detector, R-group attribution, delta sensitivity, per-scope summary, strict-delta case report, non-severe contact stats, scope comparison 和 verifier clean-vs-clean smoke 报告. 阶段 1 不做人为注入, 不接生成器, 不强制 full receptor.

## 4. 阶段 2 命令

```bash
python scripts/phase2_inject_artificial_clashes.py \
  --config configs/phase2_injection.yaml \
  --manifest data/processed/v0_1/manifest.parquet \
  --phase1-report-root reports/phase1_clash_detector \
  --output-root data/benchmarks/clashrepairbench_rg_artificial/v0_1 \
  --report-root reports/phase2_injection

python scripts/phase2_render_visual_qc_images.py \
  --case-id case_000041 \
  --num-clear-views 12 \
  --candidate-directions 1024 \
  --output-root runs/phase2_visual_qc \
  --report-root reports/phase2_visual_qc
```

`phase2_inject_artificial_clashes.py` 从阶段 0/1 clean base pose 出发, 枚举合法 single-anchor target R-group, 执行 `easy_rotation`, `torsion_perturb`, `directed_clash`, 复用阶段 1 detector / attribution 分配 oracle split, 并输出 benchmark, reports 和 completion audit. `delta_sensitivity.csv` 使用显式状态列, `energy_delta_*` 只作为 record-only ligand-only 诊断报告. 阶段 2 不调用生成器, 不做 repair, 不做 whole complex minimization.

`phase2_render_visual_qc_images.py` 读取阶段 2 `visual_qc_cases.csv` 和 benchmark manifest, 复用阶段 0 clear-view 视角选择算法, 默认先采样 1024 个候选方向, 再为每类主视图选出 12 个去遮挡视角. 阶段 2 会以 target R-group 位移线中点为 camera target, 并在最终选择前加入 target 位移轴角度约束: 相机视线与 R 基位移线的无方向夹角必须在 30 到 90 度之间. 渲染脚本会在每张图保存前把 camera 光轴平移到该中点, 避免只对齐方向但画面中心偏离 target. 默认 contact sheets 缩为 `ligand_delta`, `overlay_sticks`, `overlay_surface`, `clash_pair_vdw` 四类; `overlay_surface` 会为原始和失败 target R-group 原子叠加小球 marker, `overlay_sticks` 会用不同颜色区分配体侧碰撞点, 蛋白侧碰撞点和中心连线. 渲染使用统一颜色词典: target failed 为青色, target displacement 为绿色, 配体碰撞为红色, 蛋白碰撞为蓝色, 碰撞连线为深灰色. 传入 `--skip-existing` 时, 已完整存在的 case/view 图组会复用, 只渲染缺失图组, 但报告和 contact sheets 仍会全量重写以保持索引一致. 脚本还会在 `runs/phase2_visual_qc/` 下生成 `by_oracle_split/`, `by_injection_mode/`, `by_oracle_split_and_mode/` 三套软链接索引, 并把对应关系写入 `reports/phase2_visual_qc/by_category_index.csv`. `clash` 和 `rgroup` 仍可通过 `--views` 显式渲染作为调试视图. 这些图只作为人工 visual QC 辅助, 不把自动渲染解释为人工 pass.

## 5. 阶段 2.5 命令

```bash
python scripts/phase2_5_prepare_diffsbdd.py \
  --config configs/phase2_5_model_induced_audit.yaml \
  --report-root reports/phase2_5_model_induced_audit \
  --run-root runs/phase2_5_model_induced_audit

python scripts/phase2_5_training_overlap_audit.py \
  --config configs/phase2_5_model_induced_audit.yaml \
  --manifest data/processed/v0_1/manifest.parquet \
  --output-root reports/phase2_5_model_induced_audit

python scripts/phase2_5_model_induced_audit.py \
  --config configs/phase2_5_model_induced_audit.yaml \
  --manifest data/processed/v0_1/manifest.parquet \
  --phase1-report-root reports/phase1_clash_detector \
  --phase2-benchmark-root data/benchmarks/clashrepairbench_rg_artificial/v0_1 \
  --run-root runs/phase2_5_model_induced_audit \
  --report-root reports/phase2_5_model_induced_audit
```

阶段 2.5 使用 `c2f_cpu` 作为主控环境. `phase2_5_prepare_diffsbdd.py` 负责准备外部 DiffSBDD 仓库, checkpoint 和独立 `diffsbdd` conda 环境, 并把环境, GPU, checkpoint hash 和 smoke test 写入 `external_setup.json`. wrapper 先做 training-overlap audit, 再选择 clean base pockets, 然后在 DiffSBDD 仓库, checkpoint 和 `diffsbdd` 环境可用时执行 frozen inference. 如果 DiffSBDD, checkpoint, official split, GPU 或生成数据缺失, 脚本只生成 blocked audit 和 schema-valid 空报告, 不训练, 不 repair, 不调参, 不做 baseline ranking.

## 6. 阶段 3 命令

```bash
python scripts/phase3_label_provenance_audit.py \
  --config configs/phase3_label_provenance_audit.yaml
```

`phase3_label_provenance_audit.py` 只读 phase2 benchmark, phase2 reports, processed base samples 和 phase2.5 reports, 生成 label provenance audit, circularity risk audit, construction consistency report 和 `phase4_mask_seed.csv`. 阶段 3 不训练模型, 不调用生成器, 不修复分子, 不把 phase2.5 model-induced rows 混入 construction consistency denominator.

## 7. 阶段 4.0 backend feasibility 命令

```bash
python scripts/phase4_0_backend_feasibility.py \
  --config configs/phase4_0_backend_feasibility.yaml \
  --mode preflight
```

```bash
python scripts/phase4_0_backend_feasibility.py \
  --config configs/phase4_0_backend_feasibility.yaml \
  --mode formal
```

`phase4_0_backend_feasibility.py` 实现阶段 4.0 后端可行性审计闭环: `preflight` 冻结 5 个 S2 case, `formal` 选择 40 个 S2 case. 脚本运行规则型固定拓扑局部构象修复, DiffSBDD CrossDocked full-atom conditional local completion, DiffSBDD full-ligand resampling 和 DiffDec single R-group scaffold decoration, 并把所有候选或失败尝试送入统一 verifier adapter. DiffSBDD joint checkpoint 可被 inventory 记录, 但官方 inpaint 入口不兼容时写入 blocked. 该脚本不训练/微调模型, 不修改 DiffSBDD/DiffDec 原始源码, 不回写阶段 2/2.5/3 历史结果.

## 8. 阶段 4.0.1 DiffSBDD conditional repair 命令

```bash
python scripts/phase4_0_1_diffsbdd_conditional_repair.py \
  --config configs/phase4_0_1_diffsbdd_conditional_repair.yaml \
  --mode preflight
```

```bash
python scripts/phase4_0_1_diffsbdd_conditional_repair.py \
  --config configs/phase4_0_1_diffsbdd_conditional_repair.yaml \
  --mode formal
```

`phase4_0_1_diffsbdd_conditional_repair.py` 只修补 DiffSBDD conditional inpainting 链路: 复用阶段 4.0 的 40 个 selected cases, 主设置固定 `center=pocket`, formal 模式运行 K=8/16/32 单轮候选预算曲线, 并输出 anchor-aware filtering, local reconnect check 和 generated fragment diagnostics. 该脚本不重跑 rule backend, 不修 DiffDec 或 DiffSBDD joint, 不训练/微调 DiffSBDD, 不修改 DiffSBDD 原始去噪过程, 不覆盖阶段 4.0 历史结果.

GPU 运行使用 `external/DiffSBDD` 的本地实验分支 `20260517-080227-phase4-0-1-gpu-inpaint-fix`, 仅修复 `inpaint.py` 在 SDF 写出前的 `lig_mask` CPU/CUDA 设备不一致问题, 不改 DiffSBDD denoising 过程.

## 9. 阶段 4.0.1a local reconnect calibration 命令

```bash
python scripts/phase4_0_1a_local_reconnect_calibration.py \
  --config configs/phase4_0_1a_local_reconnect_calibration.yaml
```

`phase4_0_1a_local_reconnect_calibration.py` 只读取阶段 4.0 和 4.0.1 既有报告与候选 SDF, 对 local reconnect 诊断做 `single_anchor_reconnect_pass`, `multi_attachment_out_of_scope`, `invalid_reconnect` 三分类校准. 该脚本不重跑 DiffSBDD, 不重新生成候选, 不训练或微调模型, 不修改 reliable repair 10 项标准, 不覆盖阶段 4.0 或 4.0.1 历史结果.

```bash
python scripts/phase4_0_1a_visual_qc.py \
  --config configs/phase4_0_1a_visual_qc.yaml
```

`phase4_0_1a_visual_qc.py` 是阶段 4.0.1a 的 visual QC 收尾入口: 从既有 reconnect 校准表中抽 25 个候选, 为每个候选生成 `reconnect_clash`, `reconnect_anchor_topology`, `reconnect_before_after_overlay` 三类 `3 x 4` contact sheet, 并输出轻量索引和人工/Codex review 模板. 运行图片和 ChimeraX 资产写入 `runs/phase4_0_1a_visual_qc/`, 默认不提交; reports 下只提交 CSV/JSON/Markdown 索引和临时汇报. 该脚本不重跑 DiffSBDD, 不重新生成候选, 不修改 reliable repair 10 项标准, 不生成 final report.
