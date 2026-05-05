# Clash2Feedback-GC：阶段 0 工程方案

> 版本：2026-05-05 一致性修订版  
> 目标：环境与数据格式打通，不训练模型，不调用生成器修复。


## 统一实现约定

四个文档统一采用下面的工程口径，后续实现时以此为准。

| 项 | 统一口径 |
|---|---|
| 项目根目录 | `clash2feedback_gc/` |
| Python 包名 | `src/clash2feedback/` |
| 静态说明文档 | `docs/`，本文件和另外三个 Markdown 都放这里 |
| 实验报告 | `reports/`，只放运行后生成的表格、图、摘要，不放方案文档 |
| 运行产物 | `runs/`，放日志、模型 checkpoint、生成候选原始输出等较重产物 |
| 数据产物 | `data/`，放 raw、processed、splits、benchmarks、candidate pools |
| 命令行入口 | `scripts/phaseN_*.py` |
| 阶段 0 processed 版本 | `data/processed/v0_1/` |
| 阶段 0 split 版本 | `data/splits/v0_1/` |
| 人工失败基准 | `data/benchmarks/clashrepairbench_rg_artificial/v0_1/` |
| 候选池 | `data/candidate_pools/v0_1/` |

特别注意：`reports/` 不是文档目录；`docs/` 才是存放这四个 Markdown 方案文件的地方。



## 1. 阶段 0 的目标和边界

阶段 0 的核心目标是：

> **把蛋白质—配体复合物稳定读入，并整理成后续所有阶段都能复用的标准 processed sample。**

它要服务后续阶段：

| 后续阶段 | 阶段 0 提供什么 |
|---|---|
| 阶段 1 碰撞检测器 | protein atoms、ligand atoms、pocket atoms、原子坐标 |
| 阶段 2 人工局部碰撞注入 | scaffold、R-groups、anchors |
| 阶段 3 规则定位 | R-group masks、pocket、基础合法性检查 |
| 阶段 4 局部修复闭环 | editable mask、fixed mask、anchor 信息 |

---

## 2. 阶段 0 做什么

阶段 0 做这些事：

1. 读取 `protein.pdb` / `protein.cif`；
2. 读取 `ligand.sdf`；
3. 用 RDKit 检查配体合法性；
4. 检查蛋白和配体是否在同一坐标系；
5. 根据配体周围 6–8 Å 裁剪 pocket；
6. 用固定规则提取 scaffold；
7. 拆分 R-groups；
8. 找到每个 R-group 的 anchor；
9. 保存统一 processed sample；
10. 生成 manifest、split 和 sanity report。

---

## 3. 阶段 0 不做什么

阶段 0 不做：

- 不训练纠错器；
- 不训练排序器；
- 不训练反馈适配器；
- 不调用 DiffSBDD 或其他生成器进行修复；
- 不做人为局部碰撞注入；
- 不实现完整 reliable repair verifier；
- 不追求大规模数据；
- 不处理所有复杂化学情况。

阶段 0 可以做基础 sanity check，例如：

```text
配体是否合法
pocket 是否非空
原始复合物是否有明显严重碰撞
scaffold / R-groups 是否能拆出来
```

但正式 clash detector 放到阶段 1。

---

## 4. 推荐输入数据

### 4.1 数据来源

当前建议路线：

```text
DiffSBDD example 数据
→ CrossDocked 小子集
→ 可选 PDBBind / RCSB PDB 少量外部检查
```

| 数据 | 用途 |
|---|---|
| DiffSBDD example | 测试脚本和接口，不作为正式数据集 |
| CrossDocked 小子集 | 阶段 0 主数据源 |
| PDBBind / RCSB PDB | 可选，用于补充真实共晶结构检查 |

### 4.2 第一批数据规模

不要一开始处理全量 CrossDocked。

| 类型 | 数量 |
|---|---:|
| 原始候选 complex | 40–50 个 |
| 最终 clean complex | 20–30 个 |
| 每个 complex 可拆 R-groups | 至少 2 个 |

### 4.3 clean complex 条件

第一批 clean complex 建议满足：

| 条件 | 推荐 |
|---|---|
| protein 和 ligand 成对 | 必须来自同一个 complex |
| 坐标系一致 | ligand 周围 8 Å 内有 pocket atoms |
| ligand 格式 | SDF，带三维坐标 |
| ligand 合法性 | RDKit sanitize 通过 |
| ligand 重原子数 | 15–60 |
| ligand 片段数 | 单主片段 |
| 原始严重碰撞 | 无明显 severe clash |
| scaffold | Murcko scaffold 可提取 |
| R-groups | 至少 2 个 |
| anchor | 第一版优先单锚点 |
| 特殊情况 | 共价配体、金属配合物、macrocycle、多片段盐先排除 |

---

## 5. 推荐项目目录结构

以下目录结构是本项目唯一推荐结构。四个 Markdown 文件放在 `docs/`；`reports/` 只放运行报告。


```text
clash2feedback_gc/
  README.md
  pyproject.toml
  environment.yml

  docs/
    20260504-01-Clash2Feedback-GC_完整方案与升级路线.md
    20260504-02-Clash2Feedback-GC_第一篇论文实验方案.md
    20260504-03-Clash2Feedback-GC_总体实验递进路线.md
    20260505-Clash2Feedback-GC_阶段0工程方案.md

  configs/
    phase0.yaml
    phase1.yaml
    phase2.yaml
    phase3.yaml
    phase4.yaml
    phase5.yaml
    phase6.yaml
    phase7.yaml
    phase8.yaml

  data/
    raw_complexes/
      complex_000001/
        protein.pdb
        ligand.sdf
        metadata.json
    processed/
      v0_1/
        complexes/
          complex_000001.pkl
        manifest.parquet
        schema.json
    splits/
      v0_1/
        train.txt
        val.txt
        test.txt
        split_report.csv
    benchmarks/
      clashrepairbench_rg_artificial/
        v0_1/
          samples/
          manifest.parquet
      model_induced/
        v0_1/
          samples/
          manifest.parquet
    candidate_pools/
      v0_1/
        train.parquet
        val.parquet
        test.parquet
    cache/

  reports/
    phase0/
    phase1_clash_detector/
    phase2_injection/
    phase3_rule_locator/
    phase4_rule_repair/
    phase5_ranker/
    phase6_critic/
    phase7_adapter/
    phase8_model_induced/

  runs/
    phase4_rule_repair/
    phase5_ranker/
    phase6_critic/
    phase7_adapter/
    phase8_model_induced/

  src/
    clash2feedback/
      __init__.py
      data/
      io/
      chemistry/
      pocket/
      geometry/
      perturb/
      feedback/
      generation/
      verifier/
      models/
      utils/

  scripts/
    phase0_build_processed.py
    phase0_check_dataset.py
    phase0_make_splits.py
    phase1_check_clashes.py
    phase2_inject_artificial_clashes.py
    phase3_rule_locator.py
    phase4_rule_repair.py
    phase5_build_candidate_pool.py
    phase5_train_ranker.py
    phase6_train_critic.py
    phase7_train_adapter.py
    phase8_model_induced_eval.py
```


### 5.1 目录职责

| 目录 | 职责 |
|---|---|
| `docs/` | 静态方案文档，包含当前四个 Markdown 文件 |
| `configs/` | 每个阶段的配置文件 |
| `data/raw_complexes/` | 原始 protein / ligand / metadata，不随意修改 |
| `data/processed/` | 阶段 0 处理后的 clean complexes |
| `data/splits/` | train / val / test 划分 |
| `data/benchmarks/` | 阶段 2 和阶段 8 构造出的失败样本基准 |
| `data/candidate_pools/` | 阶段 5 排序器和适配器训练用候选池 |
| `data/cache/` | 可删除缓存，如 RDKit molblock、pocket 临时结果 |
| `reports/` | 各阶段生成的统计表、图、summary，不放方案文档 |
| `runs/` | 日志、checkpoint、生成候选原始输出等较重运行产物 |
| `src/clash2feedback/` | 可复用 Python 包代码 |
| `scripts/` | 各阶段命令行入口 |

### 5.2 为什么需要同时有 `docs/`、`reports/` 和 `runs/`

| 目录 | 是否人工维护 | 是否随实验反复生成 | 例子 |
|---|---:|---:|---|
| `docs/` | 是 | 否 | 方案文档、实验路线、阶段 0 工程方案 |
| `reports/` | 否 | 是 | `summary.json`、`dataset_check.csv`、结果表、图 |
| `runs/` | 否 | 是 | 模型 checkpoint、日志、生成候选、临时 SDF |

这样做可以避免把“方案文档”和“实验结果”混在一起。

---

## 6. 原始 complex 目录规范

每个 complex 一个目录：

```text
data/raw_complexes/complex_000001/
  protein.pdb
  ligand.sdf
  metadata.json
```

`metadata.json` 建议：

```json
{
  "complex_id": "complex_000001",
  "source": "crossdocked_small",
  "pdb_id": null,
  "uniprot_id": null,
  "target_id": null,
  "ligand_id": null,
  "split_group": "complex_000001",
  "notes": ""
}
```

说明：

- `split_group` 用于后续 train / val / test 分组；
- 如果没有 UniProt ID，就用 complex_id 或 target_id；
- 不要随机把 protein 和 ligand 拼起来，必须按 complex 配对读取；
- 不要用 SMILES 重新生成配体三维坐标，必须使用已经在蛋白口袋中的 `ligand.sdf`。

---

## 7. processed sample 数据格式

每个 clean complex 保存为：

```text
data/processed/v0_1/complexes/complex_000001.pkl
```

同时写入：

```text
data/processed/v0_1/manifest.parquet
```

### 7.1 顶层结构

```python
ProcessedComplexSample = {
    "schema_version": "0.1",
    "sample_id": str,
    "complex_id": str,
    "source": str,
    "created_at": str,

    "paths": {...},
    "metadata": {...},
    "protein": {...},
    "ligand": {...},
    "pocket": {...},
    "scaffold": {...},
    "rgroups": [...],
    "masks": {...},
    "sanity": {...},
    "software_versions": {...}
}
```

---

## 8. 字段设计

### 8.1 paths

```python
"paths": {
    "raw_protein_path": str,
    "raw_ligand_path": str,
    "processed_path": str,
    "protein_sha256": str,
    "ligand_sha256": str
}
```

### 8.2 metadata

```python
"metadata": {
    "pdb_id": str | None,
    "uniprot_id": str | None,
    "target_id": str | None,
    "chain_ids": list[str],
    "ligand_id": str | None,
    "dataset_name": str,
    "split_group": str
}
```

### 8.3 protein

```python
"protein": {
    "num_atoms": int,
    "atom_names": list[str],
    "elements": list[str],
    "atomic_numbers": list[int],
    "coords": np.ndarray,        # shape: [N_protein, 3], float32
    "chain_ids": list[str],
    "residue_ids": list[int],
    "insertion_codes": list[str],
    "residue_names": list[str],
    "is_backbone": np.ndarray,   # shape: [N_protein], bool
    "is_hetero": np.ndarray,     # shape: [N_protein], bool
    "occupancy": np.ndarray | None,
    "b_factor": np.ndarray | None
}
```

### 8.4 ligand

```python
"ligand": {
    "num_atoms": int,
    "num_heavy_atoms": int,
    "elements": list[str],
    "atomic_numbers": list[int],
    "coords": np.ndarray,          # shape: [N_ligand, 3], float32
    "formal_charges": list[int],
    "is_aromatic": list[bool],
    "hybridization": list[str],
    "chiral_tags": list[str],
    "bonds": {
        "edge_index": np.ndarray,  # shape: [2, N_bonds * 2]
        "bond_order": list[float],
        "bond_type": list[str],
        "is_aromatic": list[bool],
        "is_rotatable": list[bool]
    },
    "canonical_smiles": str,
    "isomeric_smiles": str,
    "inchi_key": str | None,
    "molblock": str,
    "rdkit_sanitize_ok": bool,
    "num_fragments": int,
    "has_3d_conformer": bool
}
```

### 8.5 pocket

```python
"pocket": {
    "method": "distance_to_ligand",
    "cutoff_angstrom": 8.0,
    "by_residue": True,
    "protein_atom_indices": np.ndarray,
    "protein_residue_keys": list[tuple],
    "coords": np.ndarray,          # shape: [N_pocket, 3]
    "elements": list[str],
    "atomic_numbers": list[int],
    "center": np.ndarray,
    "num_pocket_atoms": int,
    "num_pocket_residues": int,
    "num_atoms_6A": int,
    "num_atoms_8A": int
}
```

默认 pocket 定义：

```text
所有距离任一 ligand heavy atom 小于等于 8 Å 的蛋白残基
```

也就是先按原子距离找近邻，再扩展到完整残基。

### 8.6 scaffold

```python
"scaffold": {
    "method": "murcko",
    "scaffold_smiles": str,
    "atom_indices": list[int],
    "num_atoms": int,
    "num_heavy_atoms": int,
    "success": bool,
    "failure_reason": str | None
}
```

注意：scaffold 不是天然唯一的。阶段 0 固定使用 Murcko scaffold，避免标签混乱。

### 8.7 rgroups

```python
"rgroups": [
    {
        "rgroup_id": "R1",
        "atom_indices": list[int],
        "heavy_atom_indices": list[int],
        "num_atoms": int,
        "num_heavy_atoms": int,

        "anchor_ligand_atom_idx": int | None,
        "anchor_scaffold_atom_idx": int | None,
        "anchor_rgroup_atom_idx": int | None,
        "anchor_bond_idx": int | None,
        "anchor_bond_order": float | None,

        "num_anchors": int,
        "is_single_anchor": bool,
        "rotatable_bond_indices": list[int],
        "is_valid_for_phase0": bool,
        "failure_reason": str | None
    }
]
```

第一版只把单锚点、2–15 个重原子的 R-group 标记为 valid。

### 8.8 masks

```python
"masks": {
    "ligand_scaffold_mask": np.ndarray,   # shape: [N_ligand], bool
    "ligand_rgroup_id": list[str | None],
    "ligand_is_rgroup": np.ndarray,       # shape: [N_ligand], bool
    "pocket_atom_mask": np.ndarray,       # shape: [N_protein], bool
    "heavy_atom_mask": np.ndarray         # shape: [N_ligand], bool
}
```

这些 mask 是后面阶段最重要的接口。

### 8.9 sanity

```python
"sanity": {
    "valid_ligand": bool,
    "has_3d_coords": bool,
    "single_ligand_fragment": bool,
    "protein_has_coords": bool,
    "pocket_nonempty": bool,
    "scaffold_success": bool,
    "num_valid_rgroups": int,
    "num_single_anchor_rgroups": int,

    "ligand_heavy_atoms_in_range": bool,
    "pocket_atoms_in_range": bool,
    "all_coords_finite": bool,

    "min_ligand_protein_distance": float,
    "num_obvious_clash_pairs": int,
    "basic_clash_screen_pass": bool,

    "fatal_errors": list[str],
    "warnings": list[str]
}
```

这里的 `basic_clash_screen_pass` 只是阶段 0 过滤用，不是正式 repair verifier。

### 8.10 software_versions

```python
"software_versions": {
    "python": str,
    "rdkit": str,
    "biopython": str,
    "mdanalysis": str,
    "numpy": str,
    "scipy": str,
    "pandas": str
}
```

---

## 9. manifest 字段

`manifest.parquet` 建议字段：

| 字段 | 含义 |
|---|---|
| sample_id | 样本 ID |
| complex_id | 复合物 ID |
| source | 数据来源 |
| protein_path | 原始蛋白路径 |
| ligand_path | 原始配体路径 |
| processed_path | processed 文件路径 |
| ligand_heavy_atoms | 配体重原子数 |
| num_pocket_atoms | pocket 原子数 |
| num_rgroups | R-group 数 |
| num_valid_rgroups | 可用 R-group 数 |
| num_single_anchor_rgroups | 单锚点 R-group 数 |
| scaffold_success | scaffold 是否成功 |
| valid_ligand | ligand 是否合法 |
| basic_clash_screen_pass | 原始样本是否通过基础碰撞筛查 |
| phase0_usable | 是否可进入后续阶段 |
| failure_reason | 失败原因 |
| split_group | 数据划分分组键 |

---

## 10. 阶段 0 执行步骤

### Step 0：建立环境

建议使用独立环境：

```yaml
name: c2f_phase0
channels:
  - conda-forge
dependencies:
  - python=3.11
  - rdkit
  - biopython
  - mdanalysis
  - numpy
  - scipy
  - pandas
  - pyarrow
  - pyyaml
  - tqdm
  - pytest
  - matplotlib
  - pip
  - pip:
      - posebusters
```

PoseBusters 在阶段 0 只作为可选 smoke check，不作为正式验证器。

### Step 1：整理 raw complex

目录：

```text
data/raw_complexes/complex_000001/
  protein.pdb
  ligand.sdf
  metadata.json
```

必须保证：

```text
protein.pdb 和 ligand.sdf 来自同一个 complex
ligand.sdf 的坐标已经位于 protein pocket 中
```

不要用 SMILES 重新生成 3D ligand 坐标。

### Step 2：读取 protein

处理规则：

1. 支持 PDB 和 mmCIF；
2. 默认去掉水；
3. 默认去掉非蛋白小分子和金属；
4. 记录 chain、residue、atom name、element、coords；
5. altloc 先取 occupancy 最大的构象；
6. element 缺失时可从 atom name 推断，但要写 warning。

### Step 3：读取 ligand

处理规则：

1. 用 RDKit 读取 SDF；
2. 要求有三维 conformer；
3. 运行 sanitize；
4. 记录原子、键、坐标、formal charge、aromaticity；
5. 生成 canonical SMILES 和 isomeric SMILES；
6. 保存 molblock；
7. 读取后立刻给每个 atom 写入 `orig_atom_idx`。

### Step 4：配体合法性检查

| 检查 | 标准 |
|---|---|
| RDKit sanitize | 通过 |
| conformer | 至少 1 个三维构象 |
| 坐标 | 无 NaN / inf |
| fragment | 单主片段 |
| 重原子数 | 15–60 |
| 元素 | C、N、O、S、P、F、Cl、Br、I 优先 |
| 金属 | 第一版排除 |
| 共价配体 | 第一版排除 |

### Step 5：检查 protein 和 ligand 是否同坐标系

做三个基础检查：

| 检查 | 目的 |
|---|---|
| ligand 周围 8 Å 内 protein atom 数 | 判断 pocket 是否非空 |
| ligand 到最近 protein atom 距离 | 判断是否明显错位 |
| protein / ligand 坐标范围 | 判断坐标是否异常 |

建议阈值：

```text
num_pocket_atoms_8A >= 50
num_pocket_atoms_8A <= 3000
min_ligand_protein_distance <= 6 Å
```

阈值只是阶段 0 防呆，不是物理结论。

### Step 6：提取 pocket

默认配置：

```text
cutoff = 8.0 Å
by_residue = true
ligand_heavy_only = true
ignore_waters = true
```

流程：

1. 取 ligand heavy atom 坐标；
2. 找所有距离 ligand heavy atoms 小于等于 8 Å 的 protein atoms；
3. 扩展到完整残基；
4. 保存 pocket atom indices；
5. 保存 pocket residue keys；
6. 保存 pocket 坐标和元素。

建议同时记录 6 Å 和 8 Å 数量。

### Step 7：提取 scaffold

流程：

1. 调用 RDKit Murcko scaffold；
2. 把 scaffold mol 映射回原 ligand atom indices；
3. 保存 scaffold atom indices；
4. 生成 ligand_scaffold_mask。

失败处理：

| 情况 | 处理 |
|---|---|
| scaffold 为空 | 标记不可用 |
| scaffold 等于整个 ligand | 没有 R-group，标记不可用 |
| 映射失败 | 标记不可用 |
| scaffold 太小 | warning |

### Step 8：拆分 R-groups

定义：

```text
R-group = ligand graph 中去掉 scaffold atoms 后的连通片段
```

流程：

1. 从 ligand bond graph 删除 scaffold atoms；
2. 找剩余原子的连通分量；
3. 每个连通分量作为候选 R-group；
4. 找它和 scaffold 的连接键；
5. 记录 anchor；
6. 单锚点、2–15 个重原子的 R-group 标记为 valid。

### Step 9：基础原始碰撞筛查

阶段 0 不实现完整 clash detector，但要排除明显坏样本。

建议做：

```text
计算 ligand heavy atoms 与 pocket protein atoms 的最小距离
计算明显过近的原子对数量
如果明显 severe clash 太多，标记 basic_clash_screen_pass = false
```

正式碰撞深度、R-group clash score、old/new clash verifier 放到阶段 1。

### Step 10：保存 processed sample

保存：

```text
data/processed/v0_1/complexes/complex_000001.pkl
```

同时更新：

```text
data/processed/v0_1/manifest.parquet
```

### Step 11：生成 split

第一批可以粗略划分：

```text
train : val : test = 70 : 10 : 20
```

但必须按 `split_group` 分组，不要按派生样本随机划分。

原则：

1. 同一个 complex 的所有派生样本必须在同一个 split；
2. 如果有 target_id / uniprot_id，优先按 target 分组；
3. 后续人工注入样本继承原 complex split；
4. 保存 split_seed 和 split_version。

### Step 12：运行 dataset check

输出：

```text
reports/phase0/dataset_check.csv
reports/phase0/failed_cases.csv
reports/phase0/summary.json
```

检查：

| 检查 | 要求 |
|---|---:|
| processed 文件可读取 | 100% |
| 必要字段存在 | 100% |
| 坐标 shape 正确 | 100% |
| RDKit sanitize | phase0 usable 样本 100% |
| pocket 非空 | phase0 usable 样本 100% |
| scaffold 成功 | phase0 usable 样本 100% |
| 至少 2 个 R-groups | phase0 usable 样本 100% |
| 至少 1 个单锚点 R-group | phase0 usable 样本 100% |
| split 无重复 | 100% |

### Step 13：人工可视化抽查

至少抽查 5 个 complex：

1. ligand 是否在 pocket 中；
2. pocket 是否围绕 ligand；
3. scaffold 是否合理；
4. R-groups 是否真是取代基；
5. anchors 是否在 scaffold 和 R-group 连接处。

---

## 11. 关键脚本和函数设计

### 11.1 `src/clash2feedback/data/schema.py`

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass
class RawComplex:
    complex_id: str
    protein_path: Path
    ligand_path: Path
    metadata: dict[str, Any]

@dataclass
class ProteinAtoms:
    atom_names: list[str]
    elements: list[str]
    atomic_numbers: list[int]
    coords: Any
    chain_ids: list[str]
    residue_ids: list[int]
    insertion_codes: list[str]
    residue_names: list[str]
    is_backbone: Any
    is_hetero: Any

@dataclass
class LigandData:
    molblock: str
    canonical_smiles: str
    isomeric_smiles: str
    elements: list[str]
    atomic_numbers: list[int]
    coords: Any
    formal_charges: list[int]
    bonds: dict[str, Any]
    rdkit_sanitize_ok: bool
    has_3d_conformer: bool

@dataclass
class PocketData:
    cutoff_angstrom: float
    by_residue: bool
    protein_atom_indices: Any
    protein_residue_keys: list[tuple]
    coords: Any
    center: Any

@dataclass
class ScaffoldData:
    method: str
    atom_indices: list[int]
    scaffold_smiles: str
    success: bool
    failure_reason: str | None = None

@dataclass
class RGroupData:
    rgroup_id: str
    atom_indices: list[int]
    heavy_atom_indices: list[int]
    anchor_ligand_atom_idx: int | None
    anchor_scaffold_atom_idx: int | None
    anchor_rgroup_atom_idx: int | None
    anchor_bond_idx: int | None
    num_anchors: int
    is_single_anchor: bool
    is_valid_for_phase0: bool
    failure_reason: str | None = None
```

### 11.2 `src/clash2feedback/io/read_protein.py`

```python
from pathlib import Path
from clash2feedback.data.schema import ProteinAtoms

def read_protein_structure(
    protein_path: Path,
    *,
    keep_waters: bool = False,
    keep_hetero: bool = False,
    prefer_mmcif: bool = True,
) -> ProteinAtoms:
    """读取 PDB/mmCIF，返回统一蛋白原子表。"""
```

### 11.3 `src/clash2feedback/io/read_ligand.py`

```python
from pathlib import Path
from rdkit import Chem
from clash2feedback.data.schema import LigandData

def read_ligand_sdf(
    ligand_path: Path,
    *,
    sanitize: bool = True,
    remove_hs: bool = False,
) -> Chem.Mol:
    """读取 SDF，返回 RDKit Mol。"""

def mol_to_ligand_data(
    mol: Chem.Mol,
    *,
    keep_molblock: bool = True,
) -> LigandData:
    """把 RDKit Mol 转成数组化 LigandData。"""
```

### 11.4 `src/clash2feedback/chemistry/sanitize.py`

```python
from rdkit import Chem

def check_ligand_validity(
    mol: Chem.Mol,
    *,
    min_heavy_atoms: int = 15,
    max_heavy_atoms: int = 60,
    allowed_elements: set[str] | None = None,
    require_single_fragment: bool = True,
    require_3d: bool = True,
) -> dict:
    """返回配体合法性检查结果，不直接抛弃样本。"""
```

### 11.5 `src/clash2feedback/pocket/extract_pocket.py`

```python
from clash2feedback.data.schema import ProteinAtoms, LigandData, PocketData

def extract_pocket_atoms(
    protein: ProteinAtoms,
    ligand: LigandData,
    *,
    cutoff_angstrom: float = 8.0,
    by_residue: bool = True,
    ligand_heavy_only: bool = True,
) -> PocketData:
    """根据配体坐标裁剪蛋白口袋。"""
```

### 11.6 `src/clash2feedback/chemistry/scaffold.py`

```python
from rdkit import Chem
from clash2feedback.data.schema import ScaffoldData

def get_murcko_scaffold_atom_indices(
    mol: Chem.Mol,
) -> ScaffoldData:
    """返回 Murcko scaffold 在原始 ligand atom index 中的位置。"""

def validate_scaffold(
    mol: Chem.Mol,
    scaffold: ScaffoldData,
    *,
    min_scaffold_atoms: int = 3,
) -> dict:
    """检查 scaffold 是否适合阶段 0。"""
```

### 11.7 `src/clash2feedback/chemistry/rgroup.py`

```python
from rdkit import Chem
from clash2feedback.data.schema import ScaffoldData, RGroupData

def decompose_rgroups(
    mol: Chem.Mol,
    scaffold: ScaffoldData,
    *,
    min_heavy_atoms: int = 2,
    max_heavy_atoms: int = 15,
    single_anchor_only: bool = True,
) -> list[RGroupData]:
    """基于 scaffold atom indices 拆分 R-groups。"""

def build_ligand_masks(
    mol: Chem.Mol,
    scaffold: ScaffoldData,
    rgroups: list[RGroupData],
) -> dict:
    """生成 scaffold mask、rgroup id mask 等。"""
```

### 11.8 `src/clash2feedback/geometry/basic_clash_screen.py`

```python
from clash2feedback.data.schema import ProteinAtoms, LigandData, PocketData

def basic_original_clash_screen(
    protein: ProteinAtoms,
    ligand: LigandData,
    pocket: PocketData,
    *,
    min_distance_threshold: float = 1.2,
) -> dict:
    """阶段 0 基础原始碰撞筛查，不替代阶段 1 正式 clash detector。"""
```

### 11.9 `src/clash2feedback/data/build_processed_dataset.py`

```python
from pathlib import Path
from clash2feedback.data.schema import RawComplex

def build_processed_sample(
    raw_complex: RawComplex,
    config: dict,
) -> dict:
    """阶段 0 主处理函数：read -> sanitize -> pocket -> scaffold -> rgroups -> sanity。"""

def save_processed_sample(
    sample: dict,
    output_dir: Path,
) -> Path:
    """保存 processed sample。"""

def build_processed_dataset(
    raw_root: Path,
    output_root: Path,
    config_path: Path,
) -> None:
    """批量处理 raw complexes。"""
```

### 11.10 `src/clash2feedback/data/check_dataset.py`

```python
from pathlib import Path

def check_processed_sample(
    sample_path: Path,
    config: dict,
) -> dict:
    """检查单个 processed sample 是否可用于后续阶段。"""

def check_processed_dataset(
    processed_root: Path,
    manifest_path: Path,
    report_dir: Path,
) -> None:
    """生成 dataset_check.csv、failed_cases.csv、summary.json。"""
```

### 11.11 `src/clash2feedback/data/split_dataset.py`

```python
from pathlib import Path
import pandas as pd

def make_grouped_splits(
    manifest: pd.DataFrame,
    *,
    group_col: str = "split_group",
    ratios: tuple[float, float, float] = (0.7, 0.1, 0.2),
    seed: int = 20260504,
) -> dict[str, list[str]]:
    """按 target / protein / complex 分组划分数据。"""

def write_splits(
    splits: dict[str, list[str]],
    output_dir: Path,
) -> None:
    """写 train.txt、val.txt、test.txt。"""
```

---

## 12. 配置文件建议

`configs/phase0.yaml`：

```yaml
schema_version: "0.1"
processed_version: "v0_1"
seed: 20260504

paths:
  raw_root: "data/raw_complexes"
  processed_root: "data/processed/v0_1"
  split_root: "data/splits/v0_1"
  report_root: "reports/phase0"

ligand:
  min_heavy_atoms: 15
  max_heavy_atoms: 60
  require_single_fragment: true
  require_3d: true
  remove_hs: false
  allowed_elements:
    - C
    - N
    - O
    - S
    - P
    - F
    - Cl
    - Br
    - I

protein:
  keep_waters: false
  keep_hetero: false
  prefer_mmcif: true

pocket:
  cutoff_angstrom: 8.0
  also_record_cutoff_6A: true
  by_residue: true
  ligand_heavy_only: true

scaffold:
  method: "murcko"
  min_scaffold_atoms: 3

rgroup:
  min_heavy_atoms: 2
  max_heavy_atoms: 15
  single_anchor_only: true

basic_clash_screen:
  enabled: true
  min_distance_threshold: 1.2
  max_obvious_clash_pairs: 0

split:
  ratios: [0.7, 0.1, 0.2]
  group_col: "split_group"
  seed: 20260504
```

---

## 13. sanity check 和验收标准

### 13.1 单样本检查

| 检查 | 通过标准 |
|---|---|
| 原始文件存在 | protein 和 ligand 都存在 |
| protein 可读取 | atom 数 > 0 |
| ligand 可读取 | RDKit Mol 非空 |
| ligand sanitize | 通过 |
| ligand 三维坐标 | conformer 存在 |
| 坐标有限 | 无 NaN / inf |
| 配体重原子数 | 15–60 |
| pocket 非空 | 8 Å pocket atom 数合理 |
| scaffold | 成功且非空 |
| R-groups | 至少 2 个 |
| 单锚点 R-group | 至少 1 个 |
| mask 一致 | mask 长度等于 ligand atom 数 |
| anchor 合法 | anchor atom index 和 bond 存在 |
| 保存可读 | pkl 保存后可重新加载 |
| manifest 对应 | 路径都能找到 |

### 13.2 数据集级检查

| 指标 | 最低要求 |
|---|---:|
| processed 文件可加载 | 100% |
| schema_version 存在 | 100% |
| phase0 usable 样本 | ≥ 20 个 |
| valid ligand | phase0 usable 样本 100% |
| pocket 非空 | phase0 usable 样本 100% |
| scaffold 成功 | phase0 usable 样本 100% |
| num_rgroups ≥ 2 | phase0 usable 样本 100% |
| 至少 1 个单锚点 R-group | phase0 usable 样本 100% |
| split 无重复 complex | 100% |
| 人工可视化抽查 | 至少 5 个合理 |

### 13.3 可以进入阶段 1 的标准

```text
[ ] 至少 20–30 个 clean processed complexes
[ ] 每个样本都有 protein、ligand、pocket、scaffold、R-groups、anchors
[ ] manifest.parquet 可正常筛选
[ ] train / val / test split 已固定
[ ] check_dataset.py 无 fatal error
[ ] failed_cases.csv 记录所有失败原因
[ ] configs/phase0.yaml 记录所有阈值
[ ] environment.yml 和 software_versions 已记录
[ ] 人工看过至少 5 个样本，确认 pocket、scaffold、R-group、anchor 没有明显错
```

---

## 14. 常见风险与排查

### 14.1 protein 和 ligand 不在同一坐标系

表现：

```text
pocket atom 数为 0
ligand 离 protein 很远
最近距离几十 Å
```

排查：

```text
检查 ligand centroid 到最近 protein atom 的距离
检查 8 Å pocket atom 数
可视化 protein + ligand
确认 ligand.sdf 是否来自同一个 complex
```

处理：

```text
阶段 0 直接跳过，不手动平移修复
```

### 14.2 RDKit sanitize 失败

表现：

```text
valence error
aromaticity error
multiple fragments
no conformer
```

处理：

```text
第一版只保留 sanitize 通过样本
失败样本写入 failed_cases.csv
不要在阶段 0 大量手修配体
```

### 14.3 PDB 元素解析错误

表现：

```text
element 为空
atom name 被误判
金属被当作普通原子
```

处理：

```text
优先使用 mmCIF
PDB element 缺失时谨慎推断
推断结果写 warning
```

### 14.4 pocket 太小或太大

表现：

```text
pocket atoms < 50
pocket atoms > 3000
pocket 不包围 ligand
```

排查：

```text
比较 6 Å 和 8 Å pocket atom 数
检查 by_atom 和 by_residue 的差异
可视化 pocket
```

### 14.5 scaffold 不合理

表现：

```text
scaffold 为空
scaffold 等于整个 ligand
scaffold 太小
scaffold 映射失败
```

处理：

```text
标记 not_decomposable
不要强行修
后续可加 BRICS fallback
```

### 14.6 R-group anchor 错误

表现：

```text
anchor 为 None
一个 R-group 有多个 anchor
R-group 原子数异常大
R-group 只有 1 个原子
```

处理：

```text
第一版只保留单锚点 R-group
多锚点标记 unsupported_multi_anchor
```

### 14.7 原子索引错位

表现：

```text
scaffold mask 对不上坐标
R-group atom index 错位
anchor 指向错误原子
```

处理：

```text
读取 ligand 后立刻写 orig_atom_idx
所有中间步骤映射回原始 ligand atom index
保存 molblock 和 coords 做对照
```

### 14.8 数据划分泄漏

表现：

```text
同一个 complex 出现在 train 和 test
同一 target 派生样本跨 split
人工注入样本泄漏
```

处理：

```text
阶段 0 按 split_group 分组划分
后续所有派生样本继承原 complex split
```

---

## 15. 阶段 0 最小代码文件清单

必须先写：

```text
src/clash2feedback/data/schema.py
src/clash2feedback/io/read_complex.py
src/clash2feedback/io/read_ligand.py
src/clash2feedback/io/read_protein.py
src/clash2feedback/pocket/extract_pocket.py
src/clash2feedback/chemistry/sanitize.py
src/clash2feedback/chemistry/scaffold.py
src/clash2feedback/chemistry/rgroup.py
src/clash2feedback/geometry/basic_clash_screen.py
src/clash2feedback/data/build_processed_dataset.py
src/clash2feedback/data/check_dataset.py
src/clash2feedback/data/split_dataset.py
scripts/phase0_build_processed.py
scripts/phase0_check_dataset.py
scripts/phase0_make_splits.py
configs/phase0.yaml
```

暂时可以不写：

```text
src/clash2feedback/models/
src/clash2feedback/generation/
src/clash2feedback/feedback/learned_adapter.py
src/clash2feedback/verifier/repair_verifier.py
src/clash2feedback/perturb/inject_clash.py
```

这些放到后续阶段。

---

## 16. 当前第一步

现在最应该先做：

```text
建立阶段 0 项目骨架
→ 放入 5–10 个 DiffSBDD example / CrossDocked 样本
→ 先写 read_ligand.py
→ 再写 read_protein.py
→ 再写 extract_pocket.py
→ 再写 scaffold.py 和 rgroup.py
→ 跑出第一个 processed sample
```

第一个目标不是处理 100 个样本，而是跑出：

```text
complex_id: complex_000001
ligand_heavy_atoms: 34
num_pocket_atoms_8A: 812
scaffold_atoms: 18
num_rgroups: 4
num_single_anchor_rgroups: 3
valid_ligand: true
phase0_usable: true
```

只要这个样本能稳定生成、保存、重读、检查，阶段 0 就可以开始批量扩展。

---

## 17. 阶段 0 最终交付物

阶段 0 完成时，应该交付：

```text
data/processed/v0_1/complexes/*.pkl
data/processed/v0_1/manifest.parquet
data/processed/v0_1/schema.json
data/splits/v0_1/train.txt
data/splits/v0_1/val.txt
data/splits/v0_1/test.txt
reports/phase0/dataset_check.csv
reports/phase0/failed_cases.csv
reports/phase0/summary.json
configs/phase0.yaml
environment.yml
```

达到这些后，再进入阶段 1：正式实现 clash detector 和 reliable repair verifier。
