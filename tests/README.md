# tests

## 1. 目录说明

本目录存放 pytest 测试. 阶段 0 测试优先覆盖公开行为和关键边界, 不依赖真实 CrossDocked 数据.

## 2. 运行

```bash
pytest
```

缺少 RDKit 或 Biopython 时, 对应测试会自动跳过.
