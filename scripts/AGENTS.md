# scripts 协作规范

## 1. 目录职责

- 本目录存放每个阶段的命令行入口.
- 脚本命名统一使用 `phaseN_*.py`, 例如 `phase0_build_processed.py`.
- 复杂业务逻辑放入 `src/clash2feedback/`, 脚本只负责参数解析, 配置加载和流程编排.

## 2. 实现规则

- 命令行参数和日志信息优先使用英文.
- 新增脚本时同步检查 `configs/` 中是否需要阶段配置.
- 脚本应从仓库根目录可运行, 路径参数优先通过配置或 CLI 传入.
- 失败时返回非零退出码, 并输出可定位的错误信息.
- 阶段 0 入口以 `phase0_build_processed.py`, `phase0_check_dataset.py`, `phase0_make_splits.py` 为优先.
