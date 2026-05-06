# 阶段 0 最终复盘

## 1. 执行状态

- 分支: `20260505-180108-phase0-implementation`.
- 起始最近提交: `294e843 Document Hugging Face mirror download policy`.
- 阶段边界: 本轮只推进阶段 0, 未进入阶段 1, 未实现正式 clash detector, 未接生成器, 未引入 PyTorch / CUDA.
- 基线验证: `python -m compileall src scripts` 通过, `conda run -n c2f_cpu pytest` 从 14 个测试扩展到 17 个测试并通过.

## 2. 数据源尝试

- DiffSBDD official example: 从 `arneschneuing/DiffSBDD` GitHub raw example 下载 `3rfm` 和 `5ndu`, smoke 可复现. strict 结果为 `5ndu` 通过, `3rfm` 因 `ligand_heavy_atoms_out_of_range` 跳过.
- `THU-ATOM/crossdocked`: 优先通过 `https://hf-mirror.com/datasets/THU-ATOM/crossdocked` 读取. 该公开小测试源可访问, 但 clean 数不足. 初始 50 个候选 strict 后只有 13 个 CrossDocked clean, 主要失败原因为 `not_enough_valid_rgroups`. 加入 ligand-only scaffold/R-group 预筛后, 该源最多只准备出 17 个可用候选, 仍低于阶段 0 验收线.
- `Yukk1Zz/if3-crossdocked2020`: 通过 HF mirror 访问 `crossdocked_pocket10.tar.gz`. 未把 1.6GB tar.gz 写入默认 `~/.cache/huggingface`; 使用流式读取, 将抽取到的 pocket PDB / ligand SDF 缓存在项目 `data/cache/crossdocked_downloads/`.

## 3. 最终数据结果

- IF3 archive 流式扫描 paired candidates: 1132.
- ligand-only 预筛跳过: 1082.
- 整理为 raw complex 的 IF3 CrossDocked 候选: 50.
- strict build processed: 51, 其中 CrossDocked clean 50, DiffSBDD clean 1.
- failed cases: 1, 即 DiffSBDD `3rfm` 的 `ligand_heavy_atoms_out_of_range`.
- phase0 usable: 51.
- split 策略: `target_level`, CrossDocked 样本使用 `target_id`, DiffSBDD smoke 使用 `complex_id`.

## 4. 生成产物

- `data/processed/v0_1/manifest.parquet`.
- `data/processed/v0_1/schema.json`.
- `data/splits/v0_1/train.txt`, `val.txt`, `test.txt`, `split_report.csv`.
- `reports/phase0/dataset_check.csv`.
- `reports/phase0/failed_cases.csv`.
- `reports/phase0/summary.json`.
- `reports/phase0/threshold_calibration.csv`.
- `reports/phase0/failure_reason_counts.csv`.
- `reports/phase0/visual_check_list.csv`.

这些运行产物均按 `.gitignore` 规则不提交到 Git.

## 5. 阈值观察

- clean 样本 ligand heavy atoms 范围: 23-49.
- clean 样本 8A pocket atoms 范围: 119-540.
- min ligand-protein distance 范围: 2.424-2.995 Å.
- obvious severe clash pairs: 全部为 0.
- valid R-groups 范围: 2-6.

当前 strict 阈值不建议放宽. IF3 archive 最终 clean 数超过原先 20-30 的目标区间, 但满足至少 20 个 clean processed complexes 的阶段 0 验收线. 如后续希望 benchmark 更轻, 可在数据准备阶段将 `--max-candidates` 降到 29-30, 或增加一个显式 downsample manifest 的只读派生步骤.

## 6. 当前结论

阶段 0 工程底座, DiffSBDD example smoke, CrossDocked 小子集 adapter, 公开数据获取, strict filtering, dataset check, split, threshold calibration 和 visual check list 均已跑通. 在当前结果下, 阶段 0 已达到可验收状态.
