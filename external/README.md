# external

本目录用于放置外部 baseline 仓库和公开 checkpoint 的本地副本.

阶段 2.5 使用 `external/DiffSBDD/` 作为 frozen DiffSBDD inference 仓库, checkpoint 放在 `external/DiffSBDD/checkpoints/`. 阶段 4.0 使用 `external/DiffSBDD/` 的 conditional/full-resampling 入口和 `external/DiffDec/` 的 DiffDec scaffold decoration 入口做 frozen inference 审计, DiffDec checkpoint 放在 `external/DiffDec/ckpt/`. 这些外部源码, checkpoint 和生成缓存默认不提交 Git.

长期可复现入口见 `docs/external_baselines.md`, 其中记录 DiffSBDD / DiffDec source repo, pinned commit, checkpoint, 关键源码路径和输出口径. 单次运行的实际环境, GPU, smoke test 和命令记录写入对应阶段的 `reports/` 目录.
