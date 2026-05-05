# scripts

## 1. 目录说明

本目录存放阶段命令行入口. 复杂逻辑放在 `src/clash2feedback/`, 脚本只负责参数解析, 配置读取和流程编排.

## 2. 阶段 0 命令

```bash
python scripts/phase0_build_processed.py --config configs/phase0.yaml
python scripts/phase0_make_splits.py --config configs/phase0.yaml
python scripts/phase0_check_dataset.py --config configs/phase0.yaml
```
