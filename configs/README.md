# configs

## 1. 目录说明

本目录存放各阶段配置文件. 当前已实现 `phase0.yaml`, `phase1_clash_detector.yaml` 和 `phase2_injection.yaml`.

## 2. 当前配置

- `phase0.yaml`: raw complex 读取, ligand/protein 过滤, pocket 提取, scaffold/R-group 拆分, basic clash screen, split 和 visual check 参数.
- `phase1_clash_detector.yaml`: vdW clash detector, R-group attribution, receptor scope 和 verifier smoke 参数.
- `phase2_injection.yaml`: artificial R-group clash injection, ligand-only gates, acceptance split, deduplication 和 visual QC 抽样参数.

配置中不要写本机绝对路径, 密钥或临时实验说明.
