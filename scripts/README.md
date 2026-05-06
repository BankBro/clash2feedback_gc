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
python scripts/phase0_generate_visual_check_assets.py --visual-check reports/phase0/visual_check_list.csv --manifest data/processed/v0_1/manifest.parquet --num-samples 10 --output-root runs/phase0_visual_check --notes tmp/20260506/phase0-visual-check-notes.md
```

`phase0_prepare_crossdocked_subset.py` 优先通过 HF 镜像读取 `THU-ATOM/crossdocked`; 若该小测试源 clean 数不足, 可用 `--source if3_archive` 从 `Yukk1Zz/if3-crossdocked2020` 的 pocket10 archive 流式抽取候选. 下载缓存写入项目内 `data/cache/`.

`phase0_make_balanced_manifest.py` 只生成派生样本清单, 不删除或替换 51 个 clean pool. `phase0_generate_visual_check_assets.py` 只生成可视化辅助资产和人工检查 notes, 不把自动图片解释为人工 pass.
