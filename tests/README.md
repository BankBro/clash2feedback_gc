# tests

## 1. 目录说明

本目录存放 pytest 测试. 阶段 0 测试优先覆盖公开行为和关键边界, 不依赖真实 CrossDocked 数据.

## 2. 运行

```bash
pytest
```

缺少 RDKit 或 Biopython 时, 对应测试会自动跳过.

阶段 1 测试覆盖 vdW 半径表, protein-ligand clash detector, R-group attribution 和 repair verifier skeleton. 这些测试使用 mock sample, 不依赖真实 CrossDocked 数据.

阶段 4.0 测试覆盖 preflight case 冻结, 规则型候选 K 限制, DiffSBDD input adapter 命令构造, failure denominator 保留和 same-topology verifier adapter. 这些测试读取本仓库已有的 phase2/phase3 小型产物, 但不执行外部 DiffSBDD 生成命令.

阶段 4.0.1 测试覆盖 DiffSBDD conditional `center=pocket` 配置, K 预算映射, preflight case 复用, anchor/reconnect/fragment 诊断字段, 报告 schema helper 和 reliable repair 10 项标准不变. 这些测试不执行外部 DiffSBDD 生成命令.

阶段 4.0.1a 测试覆盖 local reconnect 三分类优先级, synthetic negative 最小负样本, shadow reliable analysis 和 reliable repair 10 项标准不变. 这些测试不执行外部 DiffSBDD 生成命令, 不重新生成候选.
