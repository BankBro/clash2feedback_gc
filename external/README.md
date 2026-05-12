# external

本目录用于放置外部 baseline 仓库和公开 checkpoint 的本地副本.

阶段 2.5 使用 `external/DiffSBDD/` 作为 frozen DiffSBDD inference 仓库, checkpoint 放在 `external/DiffSBDD/checkpoints/`. 这些外部源码, checkpoint 和生成缓存默认不提交 Git.

长期可复现入口见 `docs/external_baselines.md`, 其中记录 DiffSBDD source repo, pinned commit, checkpoint, 关键源码路径和输出口径. 单次运行的实际环境, GPU, smoke test 和命令记录写入 `reports/phase2_5_model_induced_audit/external_setup.json`.
