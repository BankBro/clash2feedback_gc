# runs

## 1. 目录说明

本目录存放较重运行产物, 例如日志, checkpoint, 生成候选和可视化辅助资产. 这些文件默认不提交 Git.

## 2. 阶段 0 产物

- `phase0_visual_check/`: 阶段 0 人工可视化抽查辅助资产, 包括 `protein.pdb`, `ligand.sdf`, projection PNG, PyMOL 脚本和 ChimeraX 脚本.

每个样本目录都是可下载的便携检查包. 将单个 `complex_xxx/` 目录下载到本地后, 在该目录运行 `chimerax view.cxc` 即可用相对路径打开对应结构.

轻量结论写入 `tmp/YYYYMMDD/*.md`; 运行生成的大图, raw 结构副本和脚本留在本目录本地使用, 默认不提交 Git.
