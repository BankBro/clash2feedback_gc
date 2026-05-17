# external 协作规范

## 1. 目录职责

- 本目录存放外部 baseline 仓库和公开 checkpoint 的本地副本.
- 外部源码, checkpoint 和生成缓存默认不提交 Git.
- 长期可复现信息统一记录在 `docs/external_baselines.md`.

## 2. 实现规则

- 不要把第三方仓库当作本项目源码直接重构.
- 如需调整外部 baseline, 优先在本项目 wrapper 中适配, 非必要不修改 `external/` 下的外部源码.
- 只有在万不得已时, 例如修补阻塞运行的 bug 或最小兼容性问题, 才允许修改外部源码; 修改不得改变外部方法的原有算法原理, 采样/去噪语义或实验口径.
- 所有外部源码补丁统一在对应外部仓库的 `clash2feedback_gc` 分支上提交; 不在临时分支, 默认分支或 detached HEAD 上继续堆叠项目补丁.
- 外部源码补丁必须记录 patch 原因, upstream commit, 补丁 commit, 影响范围, 以及是否修改原始生成/采样/denoising 语义.
- 新增外部 baseline 时, 同步更新 `docs/external_baselines.md` 和 `external/README.md`.
- 不要假设远端读者或网页版 ChatGPT 能看到本地 `external/` 内容; 引用外部源码时提供 source repo, pinned commit 和关键文件路径.
