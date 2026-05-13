# configs

## 1. 目录说明

本目录存放各阶段配置文件. 当前已实现 `phase0.yaml`, `phase1_clash_detector.yaml`, `phase2_injection.yaml`, `phase2_5_model_induced_audit.yaml` 和 `phase3_label_provenance_audit.yaml`.

## 2. 当前配置

- `phase0.yaml`: raw complex 读取, ligand/protein 过滤, pocket 提取, scaffold/R-group 拆分, basic clash screen, split 和 visual check 参数.
- `phase1_clash_detector.yaml`: vdW clash detector, R-group attribution, receptor scope 和 verifier smoke 参数.
- `phase2_injection.yaml`: artificial R-group clash injection, ligand-only gates, acceptance split, deduplication 和 visual QC 抽样参数.
- `phase2_5_model_induced_audit.yaml`: frozen DiffSBDD generation audit, training-overlap audit, 外部仓库/checkpoint/env 元数据, all generated samples manifest, ligand validity, taxonomy 和 blocked 约束参数.
- `phase3_label_provenance_audit.yaml`: phase2 标签溯源, 循环风险审计, construction consistency check, phase4 mask seed 生成路径, S0/S1/S2 集合约束和 random mask 策略.

配置中不要写本机绝对路径, 密钥或临时实验说明.
