# external 协作规范

## 1. 目录职责

- 本目录存放外部 baseline 仓库和公开 checkpoint 的本地副本.
- 外部源码, checkpoint 和生成缓存默认不提交 Git.
- 长期可复现信息统一记录在 `docs/external_baselines.md`.

## 2. 实现规则

- 不要把第三方仓库当作本项目源码直接重构.
- 如需修改外部源码, 优先在本项目 wrapper 中适配; 必须修改时, 先记录 patch 原因和对应 upstream commit.
- 新增外部 baseline 时, 同步更新 `docs/external_baselines.md` 和 `external/README.md`.
- 不要假设远端读者或网页版 ChatGPT 能看到本地 `external/` 内容; 引用外部源码时提供 source repo, pinned commit 和关键文件路径.
