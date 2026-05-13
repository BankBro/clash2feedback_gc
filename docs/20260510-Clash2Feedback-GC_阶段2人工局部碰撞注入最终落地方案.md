# Clash2Feedback-GC 阶段 2：人工局部碰撞注入最终落地方案

> 日期：2026-05-10  
> 建议仓库路径：`docs/20260510-Clash2Feedback-GC_阶段2人工局部碰撞注入最终落地方案.md`  
> 关联阶段：阶段 0 processed clean complexes、阶段 1 clash detector / attribution / verifier  
> 目标：构建 `ClashRepairBench-RG-artificial`，即带人工 target R-group 标签的 controlled synthetic failed pose benchmark 和 clean local repair substrate。
> 重要边界：阶段 2 不训练模型、不调用生成器、不做 repair、不做 whole protein-ligand complex minimization。

---

## 0. 一句话定位

阶段 2 的目标是：

> 从阶段 1 验收过的 clean protein-ligand pose 出发，选择一个合法 target R-group，进行受控局部扰动，构造 **ligand 自身合理、但 target R-group 与 protein 发生 severe clash** 的 synthetic failed pose benchmark。

阶段 2 的产物是：

```text
ClashRepairBench-RG-artificial
```

阶段 2 是 **造数据**，不是修复；是 **controlled failed pose benchmark construction**，不是生成模型实验。

---

## 1. 阶段 2 做什么 / 不做什么

### 1.1 做什么

阶段 2 做：

```text
1. 从阶段 1 clean base pose 中筛选可用样本；
2. 选择一个合法 target R-group；
3. 检查 target R-group 的 anchor bond 是否可合法扰动；
4. 对 target R-group 做 controlled perturbation；
5. 检查 ligand 自身是否仍然合理；
6. 用阶段 1 detector 检查是否产生 protein-ligand severe clash；
7. 根据 target / non-target / scaffold clash 情况分 split；
8. 保存 benchmark samples、manifest 和 reports。
```

### 1.2 不做什么

阶段 2 不做：

```text
不训练 learned critic；
不训练 ranker；
不训练 feedback adapter；
不调用 DiffSBDD / Pocket2Mol / TargetDiff 等生成器；
不做 repair；
不做 reliable repair yield；
不做阶段 3 Top-1 / Top-3 最终结论；
不做 whole protein-ligand complex strong minimization；
不声称 synthetic failed pose 是真实稳定结合构象；
不把 full receptor 作为 hard gate。
```

---

## 2. 核心概念

### 2.1 target R-group

本次人工扰动的 R-group。

例如：

```text
target_rgroup = R2
```

阶段 2 中它是人工扰动标签 / 参考修复区域标签：

```text
target_rgroup = R2
```

该字段可作为阶段 4 oracle 掩码来源, 但不应表述为无偏定位真值。

但后续文档必须区分:

```text
target_rgroup = 人工扰动标签
supported_single_rgroup = 经过 detector / attribution / target-dominance gates 过滤后的 clean local repair substrate
```

### 2.2 non-target R-groups

除 target R-group 以外的其他 R-groups。

例如：

```text
target_rgroup = R2
non_target_rgroups = R1, R3, R4
```

阶段 2 构造时：

```text
只允许 target R-group 动；
scaffold 不动；
non-target R-groups 不动。
```

### 2.3 anchor

这里的 anchor 不是 ligand 和 protein 的结合点，而是 **ligand 内部 scaffold 与 R-group 的连接位置**。

```text
scaffold_anchor_atom —— rgroup_anchor_atom
```

第一版只处理：

```text
single-anchor R-group
```

如果是 multi-anchor linker、macrocycle、covalent ligand、metal coordination 等情况，第一版标记为 `unsupported`。

---

## 3. 输入数据要求

阶段 2 输入来自阶段 0/1 已验收的数据：

```text
data/processed/v0_1/complexes/*.pkl
data/processed/v0_1/manifest.parquet
data/splits/v0_1/*.txt
reports/phase1_clash_detector/
```

每个 base sample 必须包含：

```text
protein atoms
ligand atoms
ligand coords
ligand bonds
scaffold atom indices
R-group atom indices
anchor info
masks
phase0_pocket8
pocket10_all_atoms
phase1 clash detector outputs
```

---

## 4. Base clean pose 过滤条件

阶段 2 只从 clean base pose 出发。

每个 base sample 必须满足：

```text
analysis_status = ok
unsupported = false
phase0_pocket8 severe clash count = 0
pocket10_all_atoms severe clash count = 0
ligand sanitize pass
scaffold success = true
num_valid_rgroups >= 1
num_single_anchor_rgroups >= 1
atom index mapping valid
```

同时记录 base pose 的 mild contacts：

```text
base_num_clash_pairs
base_num_nonsevere_clash_pairs
base_max_depth
base_total_clash_score
base_contact_level
```

原因：

> zero severe clash 不等于 zero close contact。阶段 2 可以从有 mild contact 的 base pose 出发，但必须记录 base contact 状态，避免后续解释混乱。

---

## 5. 注入方式设计

阶段 2 第一版按优先级实现三种 mode。

### 5.1 `easy_rotation`

围绕 scaffold-R-group anchor bond 旋转 target R-group。

建议角度：

```text
60°, 120°, 180°, 240°, 300°
```

要求：

```text
scaffold 不动
anchor bond 不断
target R-group 内部几何基本保持
non-target R-groups 不动
```

这是第一版最稳的 debug / 主构造方式。

### 5.2 `torsion_perturb`

扰动 target R-group 内部可旋转键，固定 scaffold 和 anchor。

用途：

```text
更接近真实局部构象错误
```

### 5.3 `directed_clash`

把 target R-group 朝 protein hotspot 方向定向扰动，用于构造 mild / medium / severe 难度。

用途：

```text
控制注入成功率和难度分布
```

### 5.4 暂缓模式

暂缓到 phase2b：

```text
fragment_replace
hard_multi_region
bulky replacement
```

这些工程风险更高，第一版不作为阻塞项。

---

## 6. 合法扰动检查

不是所有 R-group 都能随便旋转。

第一版只允许：

```text
single-anchor R-group
anchor bond 是合法 rotatable single bond
target R-group heavy atoms 数量在合理范围内，例如 2–15
```

必须排除或标记 unsupported：

```text
ring bond
double bond
aromatic bond
amide-like bond
强共轭受限 bond
multi-anchor linker
macrocycle
covalent ligand
metal coordination case
unsupported chemistry
```

---

## 7. Ligand-only 合理性检查

阶段 2 的核心目标不是构造真实稳定结合构象，但必须保证 ligand 自身没有坏掉。

### 7.1 必须检查

```text
RDKit sanitize pass
bond length sanity pass
anchor integrity pass
ligand internal severe clash = 0
chirality preserved
coords finite
heavy atom index mapping preserved
```

### 7.2 可选检查

```text
RDKit MMFF / UFF ligand-only energy delta
```

注意：

```text
只做 ligand-only energy check；
不做 whole protein-ligand complex minimization；
不允许把人为制造的 protein-ligand clash 优化没。
```

### 7.3 energy 字段

记录：

```text
forcefield_type: MMFF / UFF / unavailable
energy_original
energy_failed
energy_delta
energy_delta_pass
energy_check_status
```

`energy_delta` 阈值不建议一开始拍死。建议先根据 validation attempts 的分布定，例如 p95 / p99，再结合人工可视化抽查。

---

## 8. Protein-ligand failure 接受条件

人工扰动后，用阶段 1 detector / attribution 重新检测。

主阈值：

```text
delta = 0.4 Å
severe_depth_threshold = 0.4 Å
```

同时记录：

```text
delta = 0.3 / 0.4 / 0.5 sensitivity
```

### 8.1 supported 主集接受条件

一个样本进入 `supported_single_rgroup`，必须满足：

```text
analysis_status = ok
ligand_valid = true
ligand_internal_severe_clash = 0
anchor_integrity_pass = true
scaffold_rmsd < 0.3 Å
non_target_rgroup_rmsd < 0.5 Å
target_num_severe_pairs >= 1
target_score_ratio_valid >= 0.7
scaffold_severe_pair_count = 0
non_target_severe_pair_count = 0
max_clash_depth 不极端，第一版建议 <= 1.5 Å
```

这里的 `target_score_ratio_valid` 来自 `attribute_clashes_to_rgroups()` 产生的 `valid_rgroup_scores`, 不是独立人工标签. 因此 `supported_single_rgroup` 是 attribution-aware filtered clean local repair subset, 后续不应用作 independent locator benchmark.

### 8.2 near-miss 不进入主集

如果只是接近 protein，但未达到 severe：

```text
target_num_severe_pairs = 0
```

则进入：

```text
near_miss_contact
```

不进入阶段 3 construction consistency check 分母。

---

## 9. Split 设计

阶段 2 不只保留成功构造的主集，还要保留失败和 reject 统计。

最终 split：

| split | 含义 | 阶段 3 用途 |
|---|---|---|
| `supported_single_rgroup` | target R-group 单区域主导, clean local repair substrate | label provenance audit, construction consistency check, phase4 mask seed |
| `ambiguous_region` | target 有 clash，但区域不够单一 | reject / hard split |
| `multi_region` | 多个 R-groups 同时 severe | reject |
| `scaffold_clash` | scaffold 也发生 severe clash | reject |
| `global_pose_failure` | 多区域整体失败 | reject |
| `near_miss_contact` | 接近但未 severe | 不进主集 |
| `invalid_conformer` | ligand 自身构象不合理 | 丢弃但统计 |
| `unsupported` | 化学或 mask 不支持 | unsupported |
| `duplicate_removed` | 重复样本 | 不进主集 |

---

## 10. 防泄漏规则

这是阶段 2 必须严格执行的部分。

### 10.1 不用预测结果筛样本

不能用：

```text
predicted_dominant_rgroup == target_rgroup
```

作为唯一保留条件。

否则阶段 3 locator 评估会泄漏。

正确做法：

```text
target_rgroup 是人工扰动标签 / 参考修复区域标签；
predicted_dominant_rgroup 只记录，不用于主过滤；
oracle_split 根据 ligand quality, target / non-target / scaffold clash 质量, target_score_ratio_valid 和 max_depth gates 决定。
```

需要注意: `target_score_ratio_valid` 是 attribution-derived gate. 它不等同于 `predicted_dominant_rgroup == target_rgroup`, 但会使 supported 主集带有 attribution 选择偏差. 因此阶段 3 必须把 Top-1 / Top-3 降级为 construction consistency check, 并报告 circularity risk.

### 10.2 派生样本继承 base split

```text
base complex in train
→ all injected variants in train
```

不能把同一个 base complex 派生的不同角度拆到不同 split。

### 10.3 保存 split 字段

每个样本必须保存：

```text
base_sample_id
base_complex_id
target_id
split_group
base_split
derived_split
```

---

## 11. 去重策略

同一 R-group 不同角度可能产生几乎一样的 clash pattern，需要去重。

建议 duplicate 判定依据：

```text
same base_sample_id
same target_rgroup
failed_coords_rmsd 很小
top_clash_pairs 高度重合
top_clash_residue 相同
failure_type 相同
max_depth / total_score 接近
```

报告：

```text
num_attempts
num_unique_failed_poses
num_duplicates_removed
duplicate_rate
```

---

## 12. Difficulty bins

阶段 2 需要给样本标难度，方便阶段 3 解释结果。

| 难度 | 定义建议 |
|---|---|
| `easy` | target ratio 高，single-region 非常明显 |
| `medium` | target 主导，但存在少量 non-severe contact |
| `hard` | ambiguous / near-scaffold / multi-region tendency |
| `invalid` | ligand 自身不合理 |
| `unsupported` | 当前系统不支持 |

报告时保留：

```text
difficulty_bin
difficulty_reason
```

---

## 13. Manifest 字段设计

`data/benchmarks/clashrepairbench_rg_artificial/v0_1/manifest.parquet` 建议至少包含：

```text
case_id
base_sample_id
base_complex_id
base_split
derived_split
target_id
source_dataset

injection_mode
attempt_id
seed
rotation_angle_deg
rotation_axis_atom_pair
transform_matrix
target_rgroup
target_atom_indices
anchor_scaffold_atom_idx
anchor_rgroup_atom_idx
anchor_bond_idx

oracle_split
difficulty_bin
acceptance_status
reject_reason
unsupported_reason
invalid_reason
duplicate_of

ligand_valid
rdkit_sanitize_ok
rotatable_bond_valid
anchor_integrity_pass
bond_length_valid
chirality_preserved
ligand_internal_severe_clash_count
forcefield_type
energy_original
energy_failed
energy_delta
energy_delta_pass
energy_check_status

scaffold_rmsd
non_target_rgroup_rmsd
target_rgroup_rmsd

delta_angstrom
severe_depth_threshold_angstrom
target_num_clash_pairs
target_num_severe_pairs
target_total_score
target_max_depth
target_score_ratio_valid
target_score_ratio_all

non_target_num_severe_pairs
scaffold_num_severe_pairs
num_total_severe_pairs
total_clash_score
max_clash_depth

predicted_dominant_region_all
predicted_dominant_valid_rgroup
dominant_ratio_all_regions
dominant_ratio_valid_rgroups
failure_type
recommended_action

delta03_status
delta04_status
delta05_status
```

---

## 14. 样本文件结构

建议目录：

```text
data/benchmarks/clashrepairbench_rg_artificial/v0_1/
  manifest.parquet
  schema.json
  samples/
    case_000001.pkl
    case_000002.pkl
  ligands/
    case_000001_original.sdf
    case_000001_failed.sdf
```

每个 `case_*.pkl` 保存：

```python
{
  "schema_version": "phase2_v0_1",
  "case_id": str,
  "base_sample": {... minimal reference ...},
  "original_ligand_coords": np.ndarray,
  "failed_ligand_coords": np.ndarray,
  "target_rgroup": str,
  "injection": {...},
  "ligand_validity": {...},
  "clash_report": {...},
  "attribution_report": {...},
  "oracle_labels": {...},
  "split": str,
  "difficulty": str,
}
```

---

## 15. Reports 设计

输出目录：

```text
reports/phase2_injection/
```

必须输出：

```text
summary.json
injection_attempts.csv
base_clean_filter_report.csv
supported_single_rgroup_cases.csv
reject_cases.csv
invalid_conformer_cases.csv
unsupported_cases.csv
duplicate_cases.csv
near_miss_cases.csv
delta_sensitivity.csv
difficulty_bins.csv
visual_qc_cases.csv
visual_qc_notes.md
```

### 15.1 `summary.json`

建议包含：

```json
{
  "schema_version": "phase2_v0_1",
  "num_base_clean_samples": 51,
  "num_attempts": 0,
  "num_accepted_supported": 0,
  "num_reject": 0,
  "num_invalid_conformer": 0,
  "num_unsupported": 0,
  "num_duplicates_removed": 0,
  "default_delta_angstrom": 0.4,
  "delta_sensitivity": [0.3, 0.4, 0.5],
  "injection_modes": ["easy_rotation", "torsion_perturb", "directed_clash"],
  "phase2_acceptance_status": "pending"
}
```

### 15.2 `injection_attempts.csv`

记录所有尝试，包括失败尝试。

核心字段：

```text
case_id
base_sample_id
target_rgroup
injection_mode
angle
attempt_status
acceptance_status
reject_reason
invalid_reason
unsupported_reason
```

### 15.3 `supported_single_rgroup_cases.csv`

阶段 3 label provenance audit, construction consistency check 和 phase4 mask seed 的主要输入。

### 15.4 `invalid_conformer_cases.csv`

记录 ligand 自身坏掉的样本，避免静默丢弃。

### 15.5 `visual_qc_cases.csv`

记录人工可视化抽查样本。

---

## 16. 代码落地文件

建议新增：

```text
configs/phase2_injection.yaml

src/clash2feedback/perturb/__init__.py
src/clash2feedback/perturb/rotation.py
src/clash2feedback/perturb/torsion.py
src/clash2feedback/perturb/directed_clash.py
src/clash2feedback/perturb/quality.py
src/clash2feedback/perturb/deduplicate.py
src/clash2feedback/perturb/labels.py

scripts/phase2_inject_artificial_clashes.py

tests/test_phase2_rotation.py
tests/test_phase2_ligand_validity.py
tests/test_phase2_anchor_integrity.py
tests/test_phase2_labels.py
tests/test_phase2_no_leakage.py
tests/test_phase2_reports.py
```

如果当前仓库已有部分文件，Codex 应优先复用和扩展现有实现，不应重复造无关代码。

---

## 17. `configs/phase2_injection.yaml` 建议

```yaml
schema_version: "phase2_v0_1"
seed: 20260510

inputs:
  processed_root: "data/processed/v0_1"
  manifest: "data/processed/v0_1/manifest.parquet"
  phase1_report_root: "reports/phase1_clash_detector"

outputs:
  benchmark_root: "data/benchmarks/clashrepairbench_rg_artificial/v0_1"
  report_root: "reports/phase2_injection"

base_filter:
  require_analysis_status_ok: true
  require_no_severe_phase0_pocket8: true
  require_no_severe_pocket10_all_atoms: true
  require_unsupported_false: true
  min_valid_rgroups: 1
  min_single_anchor_rgroups: 1

injection:
  modes:
    - easy_rotation
    - torsion_perturb
    - directed_clash
  easy_rotation_angles_deg: [60, 120, 180, 240, 300]
  max_attempts_per_rgroup: 8
  max_accepted_per_base_sample: 5

chemistry:
  require_rdkit_sanitize: true
  require_rotatable_anchor_bond: true
  reject_ring_bond: true
  reject_double_bond: true
  reject_aromatic_bond: true
  reject_amide_like_bond: true
  require_chirality_preserved: true
  use_energy_delta_filter: true
  forcefield_preference: ["MMFF", "UFF"]
  energy_delta_threshold_mode: "calibrate_from_validation_distribution"

geometry:
  scaffold_rmsd_threshold: 0.3
  non_target_rmsd_threshold: 0.5
  anchor_bond_length_delta_threshold: 0.05
  ligand_internal_severe_clash_allowed: 0

detector:
  default_delta_angstrom: 0.4
  delta_sensitivity: [0.3, 0.4, 0.5]
  severe_depth_threshold_angstrom: 0.4
  old_scope: "phase0_pocket8"
  new_scope: "pocket10_all_atoms"

acceptance:
  min_target_severe_pairs: 1
  min_target_score_ratio_valid: 0.7
  max_scaffold_severe_pairs: 0
  max_non_target_severe_pairs: 0
  max_clash_depth_angstrom: 1.5

splitting:
  inherit_base_split: true
  group_by: "split_group"

deduplicate:
  enabled: true
  coords_rmsd_threshold: 0.1
  require_same_top_residue: true
  require_same_failure_type: true

visual_qc:
  num_supported_cases: 10
  num_reject_cases: 5
  num_invalid_cases: 5
```

---

## 18. 单元测试要求

### 18.1 Rotation tests

```text
test_rotate_only_target_rgroup
test_scaffold_unchanged_after_rotation
test_non_target_rgroups_unchanged
test_anchor_bond_length_preserved
test_invalid_nonrotatable_bond_rejected
```

### 18.2 Ligand validity tests

```text
test_rdkit_sanitize_gate
test_ligand_internal_clash_gate
test_energy_delta_recorded
test_energy_unavailable_recorded_not_crash
test_chirality_preserved
```

### 18.3 Label tests

```text
test_target_rgroup_saved_independent_of_prediction
test_supported_single_rgroup_label
test_multi_region_label
test_scaffold_clash_label
test_near_miss_label
test_invalid_conformer_label
```

### 18.4 Anti-leakage tests

```text
test_injected_samples_inherit_base_split
test_same_base_not_split_across_train_test
test_predicted_dominant_not_used_as_acceptance_gate
test_heavy_atom_index_mapping_preserved
```

### 18.5 Report tests

```text
test_summary_json_schema
test_injection_attempts_csv_has_all_attempts
test_supported_cases_csv_only_supported
test_invalid_cases_not_silent_drop
test_delta_sensitivity_report
```

---

## 19. 阶段 2 执行流程

建议命令：

```bash
python scripts/phase2_inject_artificial_clashes.py \
  --config configs/phase2_injection.yaml \
  --manifest data/processed/v0_1/manifest.parquet \
  --phase1-report-root reports/phase1_clash_detector \
  --output-root data/benchmarks/clashrepairbench_rg_artificial/v0_1 \
  --report-root reports/phase2_injection
```

执行顺序：

```text
1. load manifest
2. apply base clean filter
3. enumerate valid target R-groups
4. enumerate injection modes / angles / attempts
5. run ligand-only validity gates
6. run phase1 detector on failed coords
7. run attribution
8. assign oracle_split
9. deduplicate
10. write samples / manifest / reports
11. run visual QC sampling
```

---

## 20. 阶段 2 验收标准

### 20.1 工程验收

```text
[ ] configs/phase2_injection.yaml 存在；
[ ] phase2 脚本可运行；
[ ] 所有 phase2 unit tests 通过；
[ ] manifest.parquet 可读取；
[ ] samples/*.pkl 可读取；
[ ] reports/phase2_injection/ 全部生成。
```

### 20.2 数据验收

```text
[ ] supported_single_rgroup cases > 0；
[ ] accepted samples 全部 analysis_status = ok；
[ ] accepted samples 全部 ligand_valid = true；
[ ] accepted samples 全部 ligand_internal_severe_clash = 0；
[ ] accepted samples 全部 scaffold_rmsd < 0.3 Å；
[ ] accepted samples 全部 non_target_rmsd < 0.5 Å；
[ ] supported 主集全部 target severe clash >= 1；
[ ] supported 主集全部 non-target severe = 0；
[ ] supported 主集全部 scaffold severe = 0；
[ ] 所有 samples 继承 base split；
[ ] predicted_dominant 没有作为保留条件；
[ ] duplicate rate 已报告；
[ ] invalid / reject / unsupported 都有原因统计；
[ ] visual QC 抽查无明显错误。
```

### 20.3 阶段 3 preflight

进入阶段 3 前，至少满足：

```text
supported_single_rgroup 样本数量足够做 label provenance audit 和 phase4 mask seed；
difficulty bins 有 easy / medium 分布；
每个 supported case 有 target_rgroup 人工扰动标签；
每个 supported case 有 predicted_dominant_rgroup 记录；
每个 supported case 有 top_valid_rgroups ranking；
delta sensitivity 已保存。
```

阶段 3 后续使用边界:

```text
阶段 3 使用 phase2 结果做 label provenance audit, circularity risk audit, construction consistency check 和 phase4 mask seed generation.
supported_single_rgroup 上的 Top-1 / Top-3 不作为 independent localization benchmark.
阶段 4 使用 supported_single_rgroup 作为 clean local repair substrate.
```

---

## 21. 当前不要做的事

阶段 2 第一版不要做：

```text
不要接生成器；
不要做 repair；
不要做 full receptor hard gate；
不要做 whole complex minimization；
不要做 fragment replacement 作为主线；
不要训练 learned critic；
不要用 predicted dominant 筛样本；
不要把 invalid conformer 静默丢弃；
不要把阶段 2 结果写成真实稳定构象。
```

---

## 22. Codex 实施要求

Codex 实施时必须遵守：

```text
1. 先读取本文件，理解阶段 2 的定义和边界；
2. 再检查当前仓库实际已有代码、测试、配置和报告；
3. 复用已有阶段 1 detector / attribution / verifier；
4. 不重复实现阶段 1 已有逻辑；
5. 先做可测试的最小 phase2 pipeline；
6. 再补报告、manifest、schema 和单元测试；
7. 最后在真实 processed 数据上跑实验验证；
8. 每次修改后运行 compileall 和 pytest；
9. 不允许用 predicted_dominant 作为样本保留条件；
10. 不允许做 whole complex minimization。
```

---

## 23. 最高等级自检循环要求

Codex 必须启动一个最高等级的新子 agent 或等价自检流程，命名建议：

```text
phase2_completion_auditor
```

该子 agent / 自检流程的职责：

```text
1. 逐条读取本 md 文档中的所有落地要求；
2. 对照当前仓库代码、配置、测试、reports 和实际运行结果；
3. 标记每一项为 done / partial / missing / blocked；
4. 对 partial / missing 项生成修复计划；
5. 执行修复；
6. 再次运行检查；
7. 不断重复，直到所有非 blocked 项均为 done；
8. 如果存在 blocked 项，必须写明阻塞原因、需要的数据/依赖/权限，以及临时替代方案。
```

建议生成最终审计文件：

```text
reports/phase2_injection/phase2_completion_audit.md
```

其中包含：

```text
- checklist 全量状态；
- 尚未完成项；
- 已完成的代码文件；
- 已完成的测试文件；
- 已生成的报告文件；
- 实际运行命令；
- compileall / pytest 结果；
- phase2 summary.json 摘要；
- visual QC 抽查状态。
```

---

## 24. 最终落地结论

阶段 2 最终版冻结为：

> 从 phase0/phase1 clean base pose 出发，选择合法 single-anchor target R-group，通过 easy rotation / torsion perturb / directed clash 构造 protein-ligand severe clash；用 RDKit 和几何规则过滤 ligand 自身不合理构象；用阶段 1 detector / attribution 标注 target、non-target、scaffold clash, 并用 `target_score_ratio_valid` 等 gates 形成 attribution-aware clean local repair substrate；严格防止数据泄漏、标签泄漏、atom index 错位和重复样本灌水；最终产出 supported / reject / invalid / unsupported 分层 benchmark。

一句话：

> **阶段 2 是造一个人工 target 标签明确、结构受控、配体自身合理、适合局部修复的 artificial R-group clash substrate, 不是 independent locator benchmark, 不是生成模型, 不是修复, 也不是稳定结合构象证明。**
