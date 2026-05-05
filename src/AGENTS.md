# src 协作规范

## 1. 目录职责

- Python 包统一为 `src/clash2feedback/`.
- 不使用 `clash2feedback_gc` 作为包名.
- 不在 `src/` 下新增 `experiments/` 作为命令入口; 阶段入口放入 `scripts/`.

## 2. 模块边界

- `data/`: 数据 schema, dataset 构建, 检查和划分.
- `io/`: protein, ligand 和 complex 读取.
- `chemistry/`: sanitize, scaffold, R-group 等化学处理.
- `pocket/`: 口袋提取.
- `geometry/`: 几何计算和基础碰撞筛查.
- `perturb/`, `feedback/`, `generation/`, `verifier/`, `models/`: 后续阶段模块.
- `utils/`: 通用小工具, 避免放业务主流程.

## 3. 实现规则

- 阶段 0 优先实现数据读取, 清洗, pocket, scaffold, R-group, sanity check 和 split.
- 公共行为优先写成可测试函数, CLI 只调用这些函数.
- 类型标注和错误信息保持清晰, 不用隐式全局状态承载配置.
- 新增依赖前确认是否已有标准库或现有依赖可以覆盖.
