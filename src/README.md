# src

## 1. 目录说明

Python 包名为 `clash2feedback`, 路径为 `src/clash2feedback/`.

## 2. 阶段 0 模块

- `io/`: raw complex, ligand SDF 和 protein PDB/mmCIF 读取.
- `chemistry/`: ligand validity, Murcko scaffold 和 R-group 拆分.
- `pocket/`: ligand 周围 pocket 提取.
- `geometry/`: basic original clash screen.
- `data/`: processed sample 构建, dataset check, split, visual check assets 和 ChimeraX 初筛图渲染.
- `perturb/`: 阶段 2 controlled target R-group perturbation, ligand-only quality gates, oracle split labeling 和 deduplication.
- `verifier/`: 阶段 1/后续阶段 repair verifier.
- `utils/`: 配置和文件工具.
