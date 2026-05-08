# Codex Prompt：实现 Clash2Feedback-GC 阶段 1 碰撞检测器与可靠验证器

> 建议存放位置：`tmp/20260508-Clash2Feedback-GC_阶段1实施CodexPrompt.md`  
> 使用方式：把本文交给 Codex，让 Codex 在服务器上的 `BankBro/clash2feedback_gc` 仓库中直接实现阶段 1。  
> 重要：请先阅读 `docs/20260508-Clash2Feedback-GC_阶段1碰撞检测器与可靠验证器方案.md`，阶段 1 实施以该文档为准。

---

## 0. 你的任务

你是 Codex，需要在当前仓库中实现 Clash2Feedback-GC 阶段 1：

> **正式 protein-ligand vdW clash detector + R-group attribution + repair verifier skeleton + 批量报告脚本 + 测试。**

阶段 1 不训练模型、不调用生成器、不做人为 clash 注入、不强制 full receptor。

---

## 1. 开始前必须阅读

请先阅读：

```text
AGENTS.md
README.md
docs/20260508-Clash2Feedback-GC_阶段1碰撞检测器与可靠验证器方案.md
docs/20260505-Clash2Feedback-GC_阶段0工程方案.md
docs/20260504-03-Clash2Feedback-GC_总体实验递进路线.md
configs/phase0.yaml
src/clash2feedback/data/schema.py
src/clash2feedback/data/build_processed_dataset.py
src/clash2feedback/data/check_dataset.py
src/clash2feedback/chemistry/rgroup.py
src/clash2feedback/geometry/basic_clash_screen.py
```

如存在下面文件，也阅读：

```text
tmp/20260508-Clash2Feedback-GC_docs文档调整建议.md
```

但本 prompt 的主任务是实现阶段 1 代码、配置、脚本和测试。docs 修改可以按用户另行要求执行。

---

## 2. 阶段 1 边界

必须遵守：

```text
不训练模型
不调用生成器
不做人为 clash 注入
不实现阶段 2 benchmark
不实现阶段 4 repair loop
不强制 full receptor
不把 basic_clash_screen 当正式 detector
```

阶段 1 只实现：

```text
formal vdW clash detector
R-group attribution
failure_type classification
repair verifier skeleton
clean pool calibration reports
tests
```

---

## 3. 需要新增或修改的文件

### 3.1 新增配置

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

### 3.2 新增代码

新增：

```text
src/clash2feedback/geometry/vdw.py
src/clash2feedback/geometry/clash.py
src/clash2feedback/geometry/rgroup_attribution.py
src/clash2feedback/geometry/clash_types.py
src/clash2feedback/verifier/repair_verifier.py
scripts/phase1_check_clashes.py
```

如果 `src/clash2feedback/verifier/` 不存在，请创建并加入 `__init__.py`。

### 3.3 新增测试

新增：

```text
tests/test_vdw.py
tests/test_clash_detector.py
tests/test_rgroup_attribution.py
tests/test_repair_verifier.py
```

测试必须不依赖服务器上的真实 phase0 数据。真实数据只在脚本运行时使用。

---

## 4. 实现要求

### 4.1 `src/clash2feedback/geometry/vdw.py`

实现：

```python
VDW_RADII: dict[str, float]

def normalize_element(element: str) -> str:
    ...

def get_vdw_radius(element: str) -> float:
    ...

def get_vdw_radius_table() -> dict[str, float]:
    ...
```

要求：

- 支持 H, C, N, O, F, P, S, Cl, Br, I；
- 大小写和 `CL` / `Cl` 要能归一化；
- unknown element 不要静默给错，建议抛出 `ValueError` 或在 detector 中记录 unsupported；
- 半径表后续要写入 `reports/phase1_clash_detector/vdw_radius_table.json`。

推荐半径：

```python
{
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
```

---

### 4.2 `src/clash2feedback/geometry/clash_types.py`

可以用 dataclass，也可以返回普通 dict。若使用 dataclass，仍需提供易于写 CSV/JSON 的 `to_dict()`。

建议定义：

```python
@dataclass
class ClashPair:
    ligand_atom_idx: int
    protein_atom_idx: int
    protein_atom_position: int | None
    ligand_element: str
    protein_element: str
    distance: float
    vdw_sum: float
    clash_depth: float
    is_severe: bool
    ligand_region: str
    protein_residue_key: str | None

@dataclass
class ClashReport:
    sample_id: str
    receptor_scope: str
    delta_angstrom: float
    severe_depth_threshold_angstrom: float
    num_clash_pairs: int
    num_severe_clash_pairs: int
    total_clash_score: float
    max_clash_depth: float
    clash_pairs: list[ClashPair]
```

也可以直接返回 dict，但字段必须一致。

---

### 4.3 `src/clash2feedback/geometry/clash.py`

实现：

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

要求：

1. `ligand_coords=None` 时使用 `sample["ligand"]["coords"]`；
2. `receptor_scope="phase0_pocket8"` 时使用 `sample["pocket"]["protein_atom_indices"]`；
3. `receptor_scope="pocket10_all_atoms"` 时使用 `sample["protein"]` 的全部 protein atoms；
4. `full_receptor_dynamic_shell` 可以先抛出 `NotImplementedError` 或返回 unsupported，但接口预留；
5. 默认只计算 ligand heavy atoms 和 protein heavy atoms；
6. 使用元素 vdW 半径和统一 `delta_angstrom`；
7. severe 判断为 `clash_depth >= severe_depth_threshold_angstrom`；
8. 输出 pair-level list；
9. 输出 summary fields；
10. 对 unknown element 记录 unsupported cases 或清晰报错；
11. 使用 chunking 避免内存暴涨。

pair 输出至少包含：

```text
ligand_atom_idx
protein_atom_idx
protein_atom_position
ligand_element
protein_element
distance
vdw_sum
clash_depth
is_severe
ligand_region
protein_residue_key
```

注意：

- `protein_atom_idx` 应尽量保存原 protein atom index；
- 如果 scope 是 pocket8，`protein_atom_position` 可记录在当前 scope array 中的位置；
- `protein_residue_key` 可用 chain/residue_id/insertion/residue_name 拼成字符串；
- `ligand_region` 由 masks 推断：scaffold、R1、R2、unknown 等。

---

### 4.4 `src/clash2feedback/geometry/rgroup_attribution.py`

实现：

```python
def ligand_atom_regions(sample: dict) -> list[str]:
    ...

def attribute_clashes_to_rgroups(
    sample: dict,
    clash_report: dict,
    alpha: float = 0.5,
    single_region_threshold: float = 0.7,
    ambiguous_threshold: float = 0.5,
) -> dict:
    ...
```

输出字段：

```text
sample_id
region_scores
normalized_region_scores
dominant_region
dominant_ratio
failure_type
recommended_action
top_regions
```

failure type 规则：

| 条件 | failure_type | recommended_action |
|---|---|---|
| no severe clash | `no_clash` | `no_repair_needed` |
| scaffold score 最高且 severe | `scaffold_clash` | `reject` |
| valid R-group dominant ratio ≥ 0.7 | `single_rgroup_clash` | `local_rgroup_repair` |
| 0.5 ≤ dominant ratio < 0.7 | `ambiguous_region_clash` | `reject_or_expand_mask` |
| dominant ratio < 0.5 且多个 R-groups 有 score | `multi_region_clash` | `reject` |
| 其他无法判断 | `unknown_or_unsupported` | `reject` |

如果 total editable score 为 0，输出：

```text
failure_type = no_clash
dominant_region = ""
dominant_ratio = 0.0
```

---

### 4.5 `src/clash2feedback/verifier/repair_verifier.py`

实现：

```python
def verify_repair(
    sample: dict,
    failed_ligand_coords: np.ndarray,
    repaired_ligand_coords: np.ndarray,
    edit_region: str | list[str] | None = None,
    config: dict | None = None,
    old_clash_report: dict | None = None,
) -> dict:
    ...
```

阶段 1 skeleton 要完成：

1. failed coords 上计算 old clash score；
2. repaired coords 上计算 clash score；
3. 判断 old clash resolved；
4. 判断 no new severe clash；
5. 计算 scaffold RMSD；
6. 计算 non-edit RMSD；
7. 做基础 geometry_valid smoke；
8. 做 edit_compliance smoke；
9. 输出 repair_pass 和 failure_reasons。

默认 old scope：

```text
phase0_pocket8
```

默认 new scope：

```text
pocket10_all_atoms
```

clean-vs-clean 时应通过：

```python
failed_ligand_coords = sample["ligand"]["coords"]
repaired_ligand_coords = sample["ligand"]["coords"]
```

RMSD 要求：

- 不需要 Kabsch 对齐，直接按坐标计算即可；
- 若 mask 为空，返回 NaN 并不要误判；
- scaffold atoms 来自 `sample["scaffold"]["atom_indices"]`；
- non-edit atoms = heavy atoms 中不属于 edit region 的原子。

`geometry_valid` 第一版可以做：

```text
coords finite
same shape
bond length 不做严格判断或只做基础 smoke
```

不要在阶段 1 过度实现 PoseBusters。

---

### 4.6 `scripts/phase1_check_clashes.py`

实现命令行：

```bash
python scripts/phase1_check_clashes.py \
  --config configs/phase1_clash_detector.yaml \
  --manifest data/processed/v0_1/manifest.parquet \
  --balanced-subset data/splits/v0_1/phase0_balanced_30.txt \
  --output-root reports/phase1_clash_detector
```

参数：

```text
--config
--manifest
--processed-root
--balanced-subset
--output-root
--delta
--scopes
--max-samples
```

功能：

1. 读取 config；
2. 读取 manifest parquet；
3. 读取 balanced subset txt；
4. 对 clean pool 跑 detector；
5. 对 balanced subset 跑 detector；
6. 对 delta sensitivity 跑 detector；
7. 对 clean-vs-clean 跑 verifier smoke；
8. 写 reports。

输出：

```text
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

如果服务器上没有 phase0 processed data，脚本应给出清晰错误，不影响 pytest。

---

## 5. 报告字段要求

### 5.1 `clean_clash_report.csv`

每行 sample + scope + delta：

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
dominant_region
dominant_ratio
failure_type
recommended_action
```

### 5.2 `balanced_clash_report.csv`

同 clean report，但只包含 `phase0_balanced_30_v0_1` 的样本。

### 5.3 `threshold_sensitivity.csv`

字段：

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

### 5.4 `rgroup_attribution_report.csv`

字段：

```text
sample_id
receptor_scope
delta_angstrom
dominant_region
dominant_ratio
failure_type
recommended_action
region_scores_json
normalized_region_scores_json
top_regions_json
```

### 5.5 `failure_type_counts.csv`

字段：

```text
dataset_name
receptor_scope
delta_angstrom
failure_type
count
```

### 5.6 `verifier_smoke_report.csv`

字段：

```text
sample_id
old_clash_score_before
old_clash_score_after
old_clash_resolved
new_severe_clash_count
no_new_severe_clash
scaffold_rmsd
non_edit_rmsd
geometry_valid
edit_compliance
repair_pass
failure_reasons
```

### 5.7 `summary.json`

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
  "clean_pool_severe_false_positive_count": 0,
  "balanced_subset_severe_false_positive_count": 0,
  "verifier_smoke_pass_count": 28,
  "phase1_acceptance_status": "complete"
}
```

实际数值按运行结果填写。

---

## 6. 测试要求

### 6.1 `tests/test_vdw.py`

测试：

```text
C 返回 1.70
CL / Cl / cl 均返回 1.75
unknown element 抛出错误或被标记 unsupported
半径表包含 C/N/O/S/P/F/Cl/Br/I
```

### 6.2 `tests/test_clash_detector.py`

用小型 mock sample，不依赖 RDKit。

测试：

1. 两个原子距离远，`num_clash_pairs = 0`；
2. 两个原子距离近，`clash_depth > 0`；
3. `phase0_pocket8` scope 使用 pocket indices；
4. `pocket10_all_atoms` scope 使用 protein 全部原子；
5. severe threshold 生效；
6. ligand region 标记正确。

### 6.3 `tests/test_rgroup_attribution.py`

构造 mock clash report：

1. R2 score 最高且 ratio ≥ 0.7 → `single_rgroup_clash`；
2. scaffold score 最高 → `scaffold_clash`；
3. 多个 R-group 接近 → `multi_region_clash` 或 `ambiguous_region_clash`；
4. 无 clash → `no_clash`。

### 6.4 `tests/test_repair_verifier.py`

构造 mock sample：

1. clean-vs-clean → repair_pass true；
2. repaired coords 产生 severe clash → repair_pass false；
3. scaffold drift 超阈值 → repair_pass false；
4. non-edit drift 超阈值 → repair_pass false。

---

## 7. 运行命令

实现后执行：

```bash
python -m compileall src scripts
pytest
```

如果服务器上有 conda 环境：

```bash
conda run -n c2f_cpu python -m compileall src scripts
conda run -n c2f_cpu pytest
```

然后在有 phase0 data 的服务器上执行：

```bash
conda run -n c2f_cpu python scripts/phase1_check_clashes.py \
  --config configs/phase1_clash_detector.yaml \
  --manifest data/processed/v0_1/manifest.parquet \
  --balanced-subset data/splits/v0_1/phase0_balanced_30.txt \
  --output-root reports/phase1_clash_detector
```

如果 `data/processed/v0_1/manifest.parquet` 不存在，请不要伪造结果，清晰报错即可。

---

## 8. 验收标准

阶段 1 实现完成后，至少满足：

```text
[ ] configs/phase1_clash_detector.yaml 存在
[ ] src/clash2feedback/geometry/vdw.py 存在
[ ] src/clash2feedback/geometry/clash.py 存在
[ ] src/clash2feedback/geometry/rgroup_attribution.py 存在
[ ] src/clash2feedback/verifier/repair_verifier.py 存在
[ ] scripts/phase1_check_clashes.py 存在
[ ] tests/test_vdw.py 存在并通过
[ ] tests/test_clash_detector.py 存在并通过
[ ] tests/test_rgroup_attribution.py 存在并通过
[ ] tests/test_repair_verifier.py 存在并通过
[ ] python -m compileall src scripts 通过
[ ] pytest 通过
[ ] 若服务器有 phase0 data，phase1_check_clashes.py 能生成 reports/phase1_clash_detector/
```

`reports/phase1_clash_detector/summary.json` 中：

```text
phase1_acceptance_status
```

如果 clean pool 可用且运行成功，应为：

```text
complete
```

若 clean pool severe false positive 不为 0，不要自动失败；需要在 summary 中记录并在报告中逐例列出。

---

## 9. 重要实现注意事项

### 9.1 不要把 Top-1 / Top-3 写成阶段 1 验收

阶段 1 没有人工失败样本，不应在阶段 1 脚本中要求 R-group Top-1 / Top-3。这些属于阶段 3。

### 9.2 不要强制 full receptor

当前 IF3 pocket10 主路线可能没有 full receptor。阶段 1 只预留接口。

### 9.3 不要过度实现 pair-specific δ

第一版统一：

```text
delta = 0.4 Å
```

并输出：

```text
0.3 / 0.4 / 0.5 sensitivity
```

### 9.4 不要把 multi-region 强行归到一个 R-group

如果 dominant ratio 低，标记：

```text
multi_region_clash
ambiguous_region_clash
```

不要假装是 clean single-R-group case。

### 9.5 不要把 covalent / metal 当普通 clash

第一版：

```text
unsupported_chemistry
reject
```

### 9.6 保持与阶段 0 schema 兼容

不要修改阶段 0 pkl schema。阶段 1 只读取已有 fields：

```text
protein
ligand
pocket
scaffold
rgroups
masks
sanity
metadata
```

如果有字段缺失，脚本应清晰记录 unsupported 或 error，不要 silent fail。

---

## 10. 推荐提交信息

若代码实现完成，commit message 可用：

```text
Implement phase1 clash detector and repair verifier skeleton
```

中文可用：

```text
实现阶段1碰撞检测器与可靠验证器骨架
```

---

## 11. 最终输出给用户的总结格式

完成后请在终端或最终回复中汇报：

```text
完成文件：
- configs/phase1_clash_detector.yaml
- src/clash2feedback/geometry/vdw.py
- src/clash2feedback/geometry/clash.py
- src/clash2feedback/geometry/rgroup_attribution.py
- src/clash2feedback/verifier/repair_verifier.py
- scripts/phase1_check_clashes.py
- tests/...

验证：
- compileall: passed / failed
- pytest: passed / failed
- phase1_check_clashes: passed / failed / skipped because no phase0 data

主要报告：
- reports/phase1_clash_detector/summary.json
- reports/phase1_clash_detector/threshold_sensitivity.csv
```

不要声称没有运行过的命令已经通过。
