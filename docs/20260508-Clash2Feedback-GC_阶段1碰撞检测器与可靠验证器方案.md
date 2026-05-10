# Clash2Feedback-GC：阶段 1 碰撞检测器与可靠验证器方案

> 版本：2026-05-08  
> 建议存放位置：`docs/20260508-Clash2Feedback-GC_阶段1碰撞检测器与可靠验证器方案.md`  
> 阶段定位：正式实现 protein-ligand clash detector、R-group attribution 和 reliable repair verifier skeleton。  
> 阶段边界：不训练模型，不调用生成器，不做人为 clash 注入，不把 full receptor 作为硬依赖。

---

## 0. 一句话总结

阶段 1 要做的是：

> **给 Clash2Feedback-GC 建立正式“裁判系统”：判断哪里发生碰撞、哪个 R-group 主要负责、修复后旧碰撞是否消失、是否产生新问题。**

阶段 0 已经完成数据读入、pocket 提取、scaffold / R-groups / anchors / masks 保存。阶段 1 不再使用阶段 0 的 `basic_clash_screen` 作为正式判断，而是实现基于 vdW 半径、clash depth、R-group attribution 和 repair verifier gates 的正式检测与验证流程。

---

## 1. 阶段 1 目标和边界

### 1.1 阶段 1 要做什么

阶段 1 做五件事：

1. 实现正式 protein-ligand vdW clash detector；
2. 输出 atom-level / pair-level / residue-level clash 信息；
3. 将 clash 归因到 scaffold 和各个 R-group；
4. 给出 `failure_type`，区分 single-region、multi-region、scaffold clash、global pose failure、unsupported chemistry；
5. 实现 repair verifier skeleton，用于后续判断 old clash 是否被修掉、new clash 是否出现、keep region 是否保持。

### 1.2 阶段 1 不做什么

阶段 1 不做：

- 不训练 learned critic；
- 不训练 ranker；
- 不训练 feedback adapter；
- 不调用 DiffSBDD / Pocket2Mol / TargetDiff 等生成器；
- 不构造人工 clash injection benchmark；
- 不处理完整多区域修复策略；
- 不把 full receptor 作为阶段 1 hard gate；
- 不声称无碰撞等于结合成功。

### 1.3 阶段 1 关闭条件

阶段 1 可以关闭，当且仅当：

- `phase0_clean_pool_v0_1` 的 clean samples 可跑正式 detector；
- `phase0_balanced_30_v0_1` 可跑正式 detector；
- detector 支持至少 `phase0_pocket8` 和 `pocket10_all_atoms` 两种 receptor scope；
- detector 输出 clash pairs、clash depth、total clash score、severe clash count；
- R-group attribution 输出 region score、dominant region、dominant ratio 和 failure type；
- verifier skeleton 可完成 clean-vs-clean smoke test；
- 输出 `reports/phase1_clash_detector/` 下的阶段 1 报告；
- `python -m compileall src scripts` 和 `pytest` 通过。

---

## 2. 术语和 receptor scope

### 2.1 protein、receptor、pocket

本项目中建议统一使用如下口径：

| 术语 | 含义 |
|---|---|
| `protein` | 当前样本实际读取的蛋白坐标文件，可以是完整蛋白，也可以是预裁剪局部结构 |
| `receptor` | 在 protein-ligand 语境下作为 ligand 结合对象的蛋白结构；工程中常与 `protein.pdb` 指向同一坐标文件 |
| `full receptor` | 完整蛋白结构，不只包含 ligand 周围局部口袋 |
| `pocket10` | 数据源预先围绕 ligand 裁出的约 10 Å 局部 receptor |
| `phase0 pocket8` | 阶段 0 从当前 `protein.pdb` 中再按 ligand heavy atoms 周围 8 Å 提取的局部 pocket |
| `ligand` | 当前样本中的小分子配体 |
| `scaffold` | ligand 的核心骨架，第一版固定使用 Murcko scaffold |
| `R-group` | scaffold 外接的局部取代基集合 |
| `anchor` | R-group 接回 scaffold 的连接位置 |

当前阶段 0 主数据中，CrossDocked / IF3 路线的 `protein.pdb` 来自 `*_pocket10.pdb`。因此：

```text
真实完整蛋白 / full receptor
  → 数据源预裁剪：pocket10.pdb
      → 阶段 0 再裁剪：phase0 pocket8
```

### 2.2 阶段 1 支持的 receptor scope

阶段 1 detector 必须显式记录 `receptor_scope`。

建议支持三种 scope：

| scope | 来源 | 阶段 1 是否硬要求 | 用途 |
|---|---|---:|---|
| `phase0_pocket8` | processed sample 的 `pocket.protein_atom_indices` | 是 | old clash diagnosis、R-group attribution |
| `pocket10_all_atoms` | processed sample 的 `protein` 全部原子；当前通常是 pocket10 | 是 | local new clash check、clean calibration |
| `full_receptor_dynamic_shell` | 后续补充 full receptor 后，围绕 repaired ligand 动态裁 10–12 Å shell | 否 | 阶段 4/5/8 的 shadow 或 final check |

阶段 1 默认：

```yaml
default_old_scope: "phase0_pocket8"
default_new_scope: "pocket10_all_atoms"
```

解释：

- old pose 本来位于阶段 0 pocket 内，用 pocket8 / pocket10 足够定位局部 clash；
- repair candidate 可能轻微移出原 8 Å 邻域，因此 new clash check 用 `pocket10_all_atoms` 更稳；
- 当前 IF3 archive 主路线只支持 pocket10，不要求阶段 1 强制 full receptor；
- full receptor 预留接口，后续阶段 4/5/8 再逐步引入。

---

## 3. 正式 clash detector 定义

### 3.1 原子级 clash depth

对 ligand 原子 \(a_i\) 和 protein 原子 \(p_j\)，定义：

\[
c_{ij}=\max(0,\ r_i^{vdW}+r_j^{vdW}-\delta-d_{ij})
\]

其中：

| 符号 | 含义 |
|---|---|
| \(c_{ij}\) | clash depth，两个原子挤入彼此 vdW 安全距离的深度 |
| \(r_i^{vdW}\) | ligand 原子 \(a_i\) 的 vdW 半径 |
| \(r_j^{vdW}\) | protein 原子 \(p_j\) 的 vdW 半径 |
| \(d_{ij}\) | 两个原子中心之间的实际距离 |
| \(\delta\) | 容忍余量，第一版统一使用 0.4 Å |
| \(\max(0,\cdot)\) | 未碰撞时 depth 记为 0 |

建议第一版：

```text
δ = 0.4 Å
severe_depth_threshold = 0.4 Å
```

也可以先写成 raw vdW overlap:

\[
o_{ij}=r_i^{vdW}+r_j^{vdW}-d_{ij}
\]

\[
c_{ij}=\max(0,\ o_{ij}-\delta)
\]

因此默认设置下:

```text
clash pair: raw vdW overlap > 0.4 Å
severe clash: raw vdW overlap >= 0.8 Å
```

这避免把 `δ = 0.4 Å` 误读成“0.4 Å raw overlap 就是 severe clash”. `δ` 是容忍余量, severe threshold 是在扣除容忍余量后的 clash depth 阈值.

同时必须输出敏感性分析：

```text
δ ∈ {0.3, 0.4, 0.5}
```

### 3.2 统一 δ 还是不同 δ

阶段 1 第一版使用统一 \(\delta\)：

\[
c_{ij}=\max(0,\ r_i^{vdW}+r_j^{vdW}-\delta-d_{ij})
\]

理由：

- 不同元素的大小差异已经由 \(r_i^{vdW}+r_j^{vdW}\) 体现；
- \(\delta\) 主要控制整体宽松程度；
- 第一版过早引入 pair-specific \(\delta_{ij}\) 会增加大量人为参数；
- 后续如果氢键、离子接触等产生系统性误判，再升级为 \(\delta_{ij}\)。

阶段 1 可以预留扩展接口：

\[
c_{ij}=\max(0,\ r_i^{vdW}+r_j^{vdW}-\delta_{ij}-d_{ij})
\]

但不作为第一版默认实现。

### 3.3 vdW 半径表

第一版使用固定、版本化半径表：

| 元素 | vdW 半径 Å |
|---|---:|
| H | 1.20 |
| C | 1.70 |
| N | 1.55 |
| O | 1.52 |
| F | 1.47 |
| P | 1.80 |
| S | 1.80 |
| Cl | 1.75 |
| Br | 1.85 |
| I | 1.98 |

建议保存：

```text
src/clash2feedback/geometry/vdw.py
reports/phase1_clash_detector/vdw_radius_table.json
```

### 3.4 pair filtering

第一版 detector 只处理普通非共价 protein-ligand 重原子对。

建议规则：

| 对象 | 处理 |
|---|---|
| ligand hydrogen | 默认排除 |
| protein hydrogen | 默认排除 |
| water | 默认排除 |
| protein hetero atoms | 默认排除或标记 unsupported |
| metal | 默认 unsupported |
| covalent ligand | 默认 unsupported，不进入普通 nonbonded clash detector |
| ligand internal clash | 不在 protein-ligand detector 中处理，放 verifier geometry gate |
| protein-protein clash | 不处理 |
| ligand-ligand intermolecular clash | 不处理 |

共价配体不要靠调大 \(\delta\) 解决，应通过 metadata 或连接信息做 covalent exclusion 或直接标记 `unsupported_covalent_ligand`。

### 3.5 clash score

总 clash score：

\[
S_{clash}=\sum_{(i,j)}c_{ij}^2
\]

其中只对 \(c_{ij}>0\) 的 clash pairs 求和。

同时输出：

```text
num_clash_pairs
num_severe_clash_pairs
total_clash_score
max_clash_depth
mean_clash_depth
```

建议 severe 判断：

```text
is_severe = clash_depth >= severe_depth_threshold
```

第一版：

```text
severe_depth_threshold = 0.4 Å
```

---

## 4. R-group attribution

### 4.1 ligand region 标注

阶段 1 需要将每个 ligand heavy atom 标注到区域：

```text
scaffold
R1
R2
R3
unsupported_rgroup
unknown
```

来源：

```text
sample["masks"]["ligand_scaffold_mask"]
sample["masks"]["ligand_rgroup_id"]
sample["rgroups"]
```

### 4.2 R-group score

对每个 R-group：

\[
Score(R_k)=\sum_{a_i\in R_k}\sum_{p_j}c_{ij}^2
\]

尺寸归一化：

\[
Score_\alpha(R_k)=\frac{Score(R_k)}{|R_k|^\alpha}
\]

第一版：

\[
\alpha=0.5
\]

其中 \(|R_k|\) 建议使用 R-group heavy atom count。

### 4.3 dominant region

定义：

```text
dominant_region = 校正后 score 最高的 ligand region
dominant_ratio = dominant_region_score / total_editable_region_score
```

如果 total score 为 0，则：

```text
dominant_region = null
dominant_ratio = 0
failure_type = no_clash
```

### 4.4 failure type 分类

阶段 1 必须输出 `failure_type`。

建议规则：

| 条件 | failure_type | recommended_action |
|---|---|---|
| severe clash 数量为 0 | `no_clash` | `no_repair_needed` |
| scaffold score 最高且 severe | `scaffold_clash` | `reject` |
| dominant valid R-group ratio ≥ 0.7 | `single_rgroup_clash` | `local_rgroup_repair` |
| 0.5 ≤ dominant ratio < 0.7 | `ambiguous_region_clash` | `reject_or_expand_mask` |
| dominant ratio < 0.5 且多个 R-groups 有明显 score | `multi_region_clash` | `reject` |
| 大量区域都有 clash 或 ligand 整体偏移 | `global_pose_failure` | `full_resampling_or_reject` |
| covalent / metal / unsupported chemistry | `unsupported_chemistry` | `reject` |

第一版主任务只处理：

```text
single_rgroup_clash
```

其他类型必须识别、记录、统计，但不进入 single-R-group repair 主指标。

---

## 5. Repair verifier skeleton

### 5.1 Verifier 的输入

阶段 1 的 verifier skeleton 输入：

```text
sample
failed_ligand_coords
repaired_ligand_coords
edit_region
old_clash_report
config
```

阶段 1 不调用生成器，因此主要做 smoke test：

```text
failed_ligand_coords = clean ligand coords
repaired_ligand_coords = clean ligand coords
```

后续阶段 2/4 会传入真实 failed / repaired candidate。

### 5.2 Verifier 的输出

建议输出：

```python
{
  "sample_id": str,
  "old_clash_score_before": float,
  "old_clash_score_after": float,
  "old_clash_resolved": bool,
  "new_severe_clash_count": int,
  "no_new_severe_clash": bool,
  "scaffold_rmsd": float,
  "scaffold_stable": bool,
  "non_edit_rmsd": float,
  "non_edit_stable": bool,
  "coordinate_valid": bool,
  "geometry_valid": bool,
  "edit_compliance": bool,
  "pocket_retention": bool,
  "old_pair_count_before": int,
  "old_pair_count_after": int,
  "old_pair_remaining_count": int,
  "old_pair_resolved_fraction": float,
  "new_pair_created_count": int,
  "new_pair_created_regions": list[str],
  "old_severe_pair_remaining_count": int,
  "new_severe_pair_created_count": int,
  "repair_pass": bool,
  "failure_reasons": list[str],
  "receptor_scope_old": str,
  "receptor_scope_new": str
}
```

### 5.3 Verifier gates

第一版 gates：

| Gate | 建议初始阈值 |
|---|---:|
| old clash resolved | old clash score after ≤ old clash score before × 0.1 |
| no new severe clash | repaired severe clash count = 0 |
| scaffold stable | scaffold RMSD < 0.5 Å |
| non-edit stable | non-edit RMSD < 0.8 Å |
| coordinate valid | 坐标 shape 一致且为有限数 |
| geometry valid | 阶段 1 先等同于 coordinate valid; RDKit sanitize, 键长, 价态和 ligand internal clash 是阶段 2/4 升级 |
| edit compliance | edit region 外修改比例 < 20% |
| pocket retention | ligand 仍在 pocket 附近；第一版可先做 min distance / contact count smoke |
| unsupported case | covalent / metal / scaffold clash / multi-region 可标记 fail 或 unsupported |

阶段 1 当前实现提供 coordinate-level geometry validity, 用于 clean-vs-clean smoke test. 除非显式实现更完整的 geometry checks, 不应把阶段 1 的 `geometry_valid` 解读为完整分子化学合法性.

### 5.4 old clash 和 new clash 的区别

old clash：

```text
修复前已经存在的 clash。
```

new clash：

```text
修复后新增或仍然存在的 severe clash。
```

第一版实现可以保守处理：

- old clash score before：在 failed coords 上计算；
- old clash score after：在 repaired coords 上按同一 receptor scope 重新计算；
- no new severe clash：在 repaired coords 上用 `default_new_scope = pocket10_all_atoms` 计算 severe clash 数量。

后续若需要更精确，可追踪旧 clash pair 集合 \(E^{old}\)，并区分：

```text
old_pair_remaining
new_pair_created
```

阶段 1 先保留扩展字段即可。

---

## 6. Full receptor 的阶段 1 处理

### 6.1 阶段 1 不强制 full receptor

当前 IF3 / CrossDocked pocket10 主路线下，`protein.pdb` 通常是 `*_pocket10.pdb`，并不保证 full receptor 可用。

阶段 1 不要求 full receptor，否则会阻塞 detector 和 verifier 的基础实现。

### 6.2 阶段 1 预留 full receptor 接口

建议配置：

```yaml
full_receptor:
  enabled: false
  mode: "optional_shadow_check"
  dynamic_shell_cutoff_angstrom: 12.0
```

后续若样本 metadata 中出现：

```text
full_receptor_path
full_receptor_alignment_status
```

则 detector 可支持：

```text
full_receptor_dynamic_shell
```

即围绕 repaired ligand 当前坐标，在 full receptor 中动态提取 10–12 Å shell 再做 clash check。

### 6.3 后续引入时机

建议：

| 阶段 | full receptor 角色 |
|---|---|
| 阶段 1–3 | 不强制，只预留接口 |
| 阶段 4 | shadow check |
| 阶段 5 | candidate label / repair utility |
| 阶段 8 | final full-receptor checked metric |

---

## 7. 阶段 1 配置文件建议

新增：

```text
configs/phase1_clash_detector.yaml
```

建议内容：

```yaml
schema_version: "phase1_v0_1"
seed: 20260504

inputs:
  processed_root: "data/processed/v0_1"
  manifest: "data/processed/v0_1/manifest.parquet"
  balanced_subset: "data/splits/v0_1/phase0_balanced_30.txt"

outputs:
  report_root: "reports/phase1_clash_detector"

detector:
  receptor_scopes:
    - phase0_pocket8
    - pocket10_all_atoms
  default_old_scope: "phase0_pocket8"
  default_new_scope: "pocket10_all_atoms"

  ligand_heavy_only: true
  protein_heavy_only: true
  ignore_waters: true
  ignore_hetero: true
  unsupported_metals: true
  unsupported_covalent_ligand: true

  delta_angstrom: 0.4
  delta_sensitivity: [0.3, 0.4, 0.5]
  severe_depth_threshold_angstrom: 0.4

  rgroup_score_alpha: 0.5
  single_region_dominant_ratio: 0.7
  ambiguous_region_dominant_ratio: 0.5

verifier:
  old_clash_resolved_ratio: 0.1
  no_new_severe_clash: true
  scaffold_rmsd_threshold: 0.5
  non_edit_rmsd_threshold: 0.8
  edit_region_outside_change_fraction: 0.2
  pocket_retention_min_contacts: null

full_receptor:
  enabled: false
  mode: "optional_shadow_check"
  dynamic_shell_cutoff_angstrom: 12.0
```

---

## 8. 代码文件清单

阶段 1 建议新增：

```text
src/clash2feedback/geometry/vdw.py
src/clash2feedback/geometry/clash.py
src/clash2feedback/geometry/rgroup_attribution.py
src/clash2feedback/geometry/clash_types.py
src/clash2feedback/verifier/repair_verifier.py
scripts/phase1_check_clashes.py
configs/phase1_clash_detector.yaml
```

建议测试：

```text
tests/test_vdw.py
tests/test_clash_detector.py
tests/test_rgroup_attribution.py
tests/test_repair_verifier.py
```

可选新增：

```text
src/clash2feedback/geometry/contact_shell.py
src/clash2feedback/verifier/geometry_checks.py
```

---

## 9. 关键接口设计

### 9.1 `vdw.py`

职责：

```text
维护 vdW 半径表；
根据元素名返回半径；
导出半径表用于 reports。
```

建议接口：

```python
VDW_RADII = {
    "H": 1.20,
    "C": 1.70,
    "N": 1.55,
    "O": 1.52,
    "F": 1.47,
    "P": 1.80,
    "S": 1.80,
    "Cl": 1.75,
    "Br": 1.85,
    "I": 1.98,
}

def normalize_element(element: str) -> str:
    ...

def get_vdw_radius(element: str) -> float:
    ...

def get_vdw_radius_table() -> dict[str, float]:
    ...
```

### 9.2 `clash.py`

职责：

```text
根据 sample 和 receptor_scope 取 protein atoms；
根据 ligand coords 取 ligand atoms；
计算 pair-level clash depth；
输出 summary 和 clash pairs。
```

建议接口：

```python
def detect_clashes(
    sample: dict,
    ligand_coords: np.ndarray | None = None,
    receptor_scope: str = "phase0_pocket8",
    delta_angstrom: float = 0.4,
    severe_depth_threshold_angstrom: float = 0.4,
    chunk_size: int = 256,
) -> dict:
    ...
```

输出：

```python
{
    "sample_id": "...",
    "receptor_scope": "phase0_pocket8",
    "delta_angstrom": 0.4,
    "severe_depth_threshold_angstrom": 0.4,
    "num_clash_pairs": 0,
    "num_severe_clash_pairs": 0,
    "total_clash_score": 0.0,
    "max_clash_depth": 0.0,
    "clash_pairs": [...],
}
```

### 9.3 `rgroup_attribution.py`

职责：

```text
将 clash pairs 映射到 scaffold / R-group；
计算 region scores；
判断 dominant region 和 failure_type。
```

建议接口：

```python
def attribute_clashes_to_rgroups(
    sample: dict,
    clash_report: dict,
    alpha: float = 0.5,
    single_region_threshold: float = 0.7,
    ambiguous_threshold: float = 0.5,
) -> dict:
    ...
```

### 9.4 `repair_verifier.py`

职责：

```text
比较 failed ligand 和 repaired ligand；
用 detector 判断 old resolved / no new clash；
用 masks 判断 scaffold / non-edit 是否稳定；
输出 repair pass/fail。
```

建议接口：

```python
def verify_repair(
    sample: dict,
    failed_ligand_coords: np.ndarray,
    repaired_ligand_coords: np.ndarray,
    edit_region: str | list[str] | None,
    config: dict | None = None,
    old_clash_report: dict | None = None,
) -> dict:
    ...
```

### 9.5 `phase1_check_clashes.py`

职责：

```text
批量读取 manifest；
跑 clean pool；
跑 balanced subset；
跑 delta sensitivity；
跑 verifier smoke；
写 reports。
```

建议命令：

```bash
conda run -n c2f_cpu python scripts/phase1_check_clashes.py \
  --config configs/phase1_clash_detector.yaml \
  --manifest data/processed/v0_1/manifest.parquet \
  --balanced-subset data/splits/v0_1/phase0_balanced_30.txt \
  --output-root reports/phase1_clash_detector
```

---

## 10. 报告文件

阶段 1 输出目录：

```text
reports/phase1_clash_detector/
```

建议文件：

```text
summary.json
clean_clash_report.csv
balanced_clash_report.csv
threshold_sensitivity.csv
rgroup_attribution_report.csv
failure_type_counts.csv
verifier_smoke_report.csv
unsupported_cases.csv
vdw_radius_table.json
strict_delta_false_positive_cases.csv
nonsevere_contact_stats.csv
scope_comparison.csv
```

### 10.1 `clean_clash_report.csv`

每行一个 sample + scope + delta：

```text
sample_id
complex_id
source
receptor_scope
delta_angstrom
num_clash_pairs
num_severe_clash_pairs
total_clash_score
max_clash_depth
mean_clash_depth
analysis_status
dominant_region
dominant_ratio
dominant_valid_rgroup
dominant_ratio_valid_rgroups
failure_type
recommended_action
```

### 10.2 `threshold_sensitivity.csv`

统计不同 delta 下 clean pool / balanced subset 的 severe false positive 情况：

```text
dataset_name
receptor_scope
delta_angstrom
num_samples
num_samples_with_severe_clash
severe_false_positive_rate
median_total_clash_score
max_total_clash_score
```

Zero severe false positives on phase-1 clean calibration does not imply zero close contacts or statistically zero false-positive rate. Mild non-severe close contacts may exist and are intentionally tolerated.

### 10.3 `strict_delta_false_positive_cases.csv`

记录严格阈值, 例如 `δ = 0.3`, 下触发 severe clash 的 clean calibration case:

```text
sample_id
dataset_name
receptor_scope
delta_angstrom
num_severe_clash_pairs
max_clash_depth
total_clash_score
dominant_region
dominant_ratio_all_regions
dominant_valid_rgroup
dominant_ratio_valid_rgroups
failure_type
top_regions_json
top_clash_pairs_json
```

### 10.4 `nonsevere_contact_stats.csv`

记录 non-severe close contact 统计, 防止把 zero severe false positive 误写成 zero close contact:

```text
dataset_name
receptor_scope
delta_angstrom
num_samples
num_samples_with_any_clash_pair
num_samples_with_nonsevere_clash_pair
median_num_clash_pairs
p95_num_clash_pairs
max_num_clash_pairs
median_max_depth
p95_max_depth
max_depth
```

### 10.5 `scope_comparison.csv`

比较 `phase0_pocket8` 与 `pocket10_all_atoms` 的结果:

```text
sample_id
dataset_name
delta_angstrom
pocket8_num_clash_pairs
pocket10_num_clash_pairs
pocket8_num_severe
pocket10_num_severe
score_diff
max_depth_diff
scope_result_same
```

当前 clean calibration 中两种 scope 结果一致, 只说明 clean pose 的 clash-relevant atoms 已被 8 Å pocket 覆盖. 它不验证修复候选移动到原 phase0 pocket8 边界外时的情况.

### 10.6 `verifier_smoke_report.csv`

clean-vs-clean smoke：

```text
sample_id
old_clash_score_before
old_clash_score_after
old_clash_resolved
new_severe_clash_count
scaffold_rmsd
non_edit_rmsd
coordinate_valid
geometry_valid
edit_compliance
repair_pass
failure_reasons
old_pair_count_before
old_pair_count_after
old_pair_remaining_count
old_pair_resolved_fraction
new_pair_created_count
new_pair_created_regions
old_severe_pair_remaining_count
new_severe_pair_created_count
```

### 10.7 `summary.json`

建议字段：

```json
{
  "schema_version": "phase1_v0_1",
  "num_clean_pool_samples": 51,
  "num_balanced_subset_samples": 28,
  "default_delta_angstrom": 0.4,
  "delta_sensitivity": [0.3, 0.4, 0.5],
  "default_old_scope": "phase0_pocket8",
  "default_new_scope": "pocket10_all_atoms",
  "full_receptor_enabled": false,
  "clean_pool_default_scope_severe_false_positive_count": 0,
  "balanced_subset_default_scope_severe_false_positive_count": 0,
  "per_scope_default_delta": {
    "phase0_pocket8": {
      "clean_pool_severe_fp": 0,
      "balanced_subset_severe_fp": 0
    },
    "pocket10_all_atoms": {
      "clean_pool_severe_fp": 0,
      "balanced_subset_severe_fp": 0
    }
  },
  "verifier_smoke_pass_count": 28,
  "phase1_acceptance_status": "complete"
}
```

---

## 11. 阶段 1 验收标准

### 11.1 工程验收

| 项 | 标准 |
|---|---|
| `configs/phase1_clash_detector.yaml` 存在 | 是 |
| `vdw.py` 存在并可导出半径表 | 是 |
| `clash.py` 支持 `phase0_pocket8` 和 `pocket10_all_atoms` | 是 |
| `rgroup_attribution.py` 输出 failure type | 是 |
| `repair_verifier.py` clean-vs-clean smoke 可跑 | 是 |
| `phase1_check_clashes.py` 可批量生成 reports | 是 |
| `python -m compileall src scripts` 通过 | 是 |
| `pytest` 通过 | 是 |

### 11.2 数据验收

| 指标 | 建议标准 |
|---|---:|
| 51 clean pool 可检测 | 100% |
| 28 balanced subset 可检测 | 100% |
| clean pool severe false positive | 尽量接近 0 |
| balanced subset severe false positive | 尽量接近 0 |
| verifier clean-vs-clean pass | 100% 或逐例解释 |
| δ sensitivity 报告 | 必须 |
| failure type counts 报告 | 必须 |

### 11.3 阶段 1 不以 Top-1 / Top-3 为验收

R-group Top-1 / Top-3 需要人工失败样本，因此应作为阶段 3 规则 locator 的验收标准，而不是阶段 1 自身验收标准。

阶段 1 只负责提供：

```text
detector
attribution
failure_type
verifier skeleton
```

阶段 2 生成人工失败样本后，阶段 3 再评估：

```text
R-group Top-1 > 70%
R-group Top-3 > 90%
dominant ratio 平均值 > 0.75
```

---

## 12. 与阶段 2–4 的接口

### 12.1 给阶段 2 的接口

阶段 2 人工注入需要调用阶段 1 detector 判断：

```text
是否产生 protein-ligand severe clash；
是否目标 R-group 主导；
dominant_ratio 是否 > 0.7；
是否 scaffold / multi-region / global pose failure。
```

### 12.2 给阶段 3 的接口

阶段 3 rule locator 直接使用：

```text
rgroup_score
normalized_rgroup_score
dominant_region
failure_type
```

### 12.3 给阶段 4 的接口

阶段 4 generator repair 需要使用：

```text
edit_region = dominant_rgroup
keep_region = scaffold + non-dominant R-groups
old_clash_pairs
protein_clash_heatmap
repair_verifier
```

---

## 13. docs 中需要同步强调的内容

阶段 1 完成后，docs 中应保持如下口径：

1. 阶段 1 是正式 detector / verifier，不做人为注入和生成器修复；
2. 阶段 1 自身验收基于 clean pool calibration 和 verifier smoke，不基于人工注入 Top-1；
3. 当前主数据是 pocket10-level receptor，不是 full receptor；
4. `phase0_pocket8` 和 `pocket10_all_atoms` 都应记录为 receptor scope；
5. full receptor 从阶段 4 shadow check、阶段 5 candidate label、阶段 8 final metric 逐步引入；
6. 第一版 \(\delta=0.4\) 使用统一容忍余量，pair-specific \(\delta_{ij}\) 后续再做；
7. multi-region / scaffold / global pose failure 第一版识别并 reject，不进入 single-R-group repair 主指标；
8. 人工 rotation injection 构造的是 controlled synthetic failed pose，不应表述为真实稳定结合构象。
9. 阶段 2 调用阶段 1 detector / attribution 的用途是判断人工扰动后是否产生 protein-ligand severe clash, 记录 target / non-target / scaffold clash scores, 并记录 predicted dominant region; predicted dominant == target 不能作为唯一保留条件。
10. 阶段 2 不做 whole protein-ligand complex minimization。RDKit MMFF / UFF 可作为 ligand-only energy delta filter, 用于排除 ligand 自身极端不合理构象, 但不用于消除人工注入的 protein-ligand clash。
11. 阶段 2 可准备 verifier preflight: no-repair negative 应 fail, oracle repair synthetic failed -> original clean 应 pass, wrong-region repair 应 fail; 这不等同于阶段 4 真实 repair candidate 验证。

---

## 14. 最终建议执行顺序

推荐 Codex 或人工实现顺序：

1. 新建 `configs/phase1_clash_detector.yaml`；
2. 实现 `src/clash2feedback/geometry/vdw.py`；
3. 实现 `src/clash2feedback/geometry/clash.py`；
4. 实现 `src/clash2feedback/geometry/rgroup_attribution.py`；
5. 实现 `src/clash2feedback/verifier/repair_verifier.py`；
6. 实现 `scripts/phase1_check_clashes.py`；
7. 新增 pytest；
8. 跑 `python -m compileall src scripts`；
9. 跑 `pytest`；
10. 在服务器阶段 0 数据上跑 `scripts/phase1_check_clashes.py`；
11. 检查 `reports/phase1_clash_detector/summary.json`；
12. 若 clean pool severe false positive 异常，先排查 detector / scope / radii / delta，不要进入阶段 2。

---

## 15. 阶段 1 最终交付物

阶段 1 交付物：

```text
configs/phase1_clash_detector.yaml

src/clash2feedback/geometry/vdw.py
src/clash2feedback/geometry/clash.py
src/clash2feedback/geometry/rgroup_attribution.py
src/clash2feedback/geometry/clash_types.py
src/clash2feedback/verifier/repair_verifier.py

scripts/phase1_check_clashes.py

tests/test_vdw.py
tests/test_clash_detector.py
tests/test_rgroup_attribution.py
tests/test_repair_verifier.py

reports/phase1_clash_detector/
  summary.json
  clean_clash_report.csv
  balanced_clash_report.csv
  threshold_sensitivity.csv
  rgroup_attribution_report.csv
  failure_type_counts.csv
  verifier_smoke_report.csv
  unsupported_cases.csv
  vdw_radius_table.json
```

其中 `reports/phase1_clash_detector/` 是运行产物，默认不一定提交 Git；代码、配置和测试应提交。
