# Clash2Feedback-GC 阶段 2.5：模型诱导失败外部有效性审计落地方案

> 日期：2026-05-11
> 建议仓库路径：`docs/20260511-Clash2Feedback-GC_阶段2.5模型诱导失败外部有效性审计落地方案.md`
> 关联阶段：阶段 0 processed clean complexes、阶段 1 clash detector / attribution、阶段 2 artificial benchmark
> 阶段定位：**External Validity Audit**，即审计真实 frozen generation baseline 的 model-induced failure 分布。
> 重要边界：阶段 2.5 不训练模型、不做 repair、不调参、不做 baseline 排名、不回改 `phase2_v0_1` benchmark。

---

## 0. 一句话定位

阶段 2.5 的目标是：

> 使用一个最容易复现的 frozen SBDD generation baseline，在经过训练集重叠审计的 clean pockets 上生成 candidates；然后对 **all generated samples** 做 ligand validity、protein-ligand clash、R-group attribution、failure taxonomy、repairability proxy 和 artificial-vs-model-induced distribution gap 分析。

阶段 2.5 要回答的问题是：

```text
阶段 2 构造的 controlled artificial single-Rgroup clash benchmark，
是否覆盖了真实生成模型失败中的一个重要子分布？
```

阶段 2.5 不回答：

```text
修复方法是否有效；
生成模型谁更强；
所有 SBDD 模型的失败分布是否相同；
阶段 2 artificial benchmark 是否覆盖所有真实失败。
```

---

## 1. 阶段边界

### 1.1 阶段 2.5 做什么

阶段 2.5 做：

```text
1. 对 phase0/phase1 clean pockets 做 DiffSBDD / CrossDocked training-overlap audit；
2. 按 overlap tier 选择可解释的 base pockets；
3. 使用 frozen DiffSBDD baseline 做 inference；
4. 保存 all generated samples，而不是只保存 failed samples；
5. 对 generated ligands 做 raw / standardized 两层审计；
6. 对 ligand-valid candidates 做阶段 1 detector clash audit；
7. 对可拆分 generated ligands 做 R-group attribution audit；
8. 输出 failure taxonomy 和 repairability proxy；
9. 和 phase2 supported artificial cases 做 distribution gap analysis；
10. 输出 reports 和 audit 文档。
```

### 1.2 阶段 2.5 不做什么

阶段 2.5 不做：

```text
不训练 DiffSBDD；
不训练任何 learned critic / adapter / ranker；
不做 repair；
不调用 local repair backend；
不做 reliable repair yield；
不做 generator ranking；
不调参以提高生成质量；
不默认做 relax / redock / whole-complex minimization；
不把 predicted dominant R-group 当真值；
不把 model-induced samples 混进阶段 3 Top-1 / Top-3 主评估；
不回改 phase2_v0_1 artificial benchmark。
```

---

## 2. 为什么阶段 2.5 必要

阶段 2 已经构建了 controlled artificial single-Rgroup clash benchmark，但它来自人为局部扰动 clean ligand：

```text
clean pose
→ 人工扰动 target R-group
→ controlled local protein-ligand severe clash
```

真实生成模型输出可能失败在很多不同地方：

```text
ligand 自身非法；
SDF / bond reconstruction 失败；
ligand internal clash；
protein-ligand local single-Rgroup clash；
multi-region clash；
scaffold clash；
global pose failure；
pocket mismatch；
无法 scaffold/R-group attribution。
```

因此，阶段 2 的成功只能说明：

```text
controlled artificial single-Rgroup clash 子任务可构造、可检测、可评估。
```

不能直接说明：

```text
真实 generated failures 大多也是 single-Rgroup local repairable。
```

阶段 2.5 的作用就是补这条外部有效性证据链。

---

## 3. 最合适的 baseline 选择

### 3.1 主 baseline

第一版建议：

```text
Model: DiffSBDD
Checkpoint: crossdocked_fullatom_cond.ckpt
Mode: frozen inference only
```

选择原因：

```text
1. DiffSBDD 是 structure-based drug design 的 pocket-conditioned 3D diffusion baseline；
2. 官方代码和 pretrained checkpoint 公开；
3. 可对给定 pocket 生成 3D ligand candidates；
4. 输出可被 RDKit / clash detector pipeline 审计；
5. crossdocked_fullatom_cond.ckpt 与当前 pocket10_all_atoms / full-atom clash detector 口径更接近；
6. checkpoint 小，适合两张 RTX 2080 Ti 做 frozen inference audit。
```

### 3.2 checkpoint 下载

建议下载到本项目或 DiffSBDD 子目录，例如：

```bash
mkdir -p external/DiffSBDD/checkpoints
wget -P external/DiffSBDD/checkpoints/ \
  https://zenodo.org/record/8183747/files/crossdocked_fullatom_cond.ckpt
```

下载后记录：

```bash
ls -lh external/DiffSBDD/checkpoints/crossdocked_fullatom_cond.ckpt
md5sum external/DiffSBDD/checkpoints/crossdocked_fullatom_cond.ckpt
sha256sum external/DiffSBDD/checkpoints/crossdocked_fullatom_cond.ckpt
```

`summary.json` 和 `generation_manifest.parquet` 必须保存：

```text
checkpoint_name
checkpoint_path
checkpoint_md5
checkpoint_sha256
checkpoint_file_size
```

### 3.3 不研究参数量

阶段 2.5 不研究参数量大小对错误分布的影响。

如果后续资源允许，可在 v1 sensitivity 加一个额外 checkpoint，例如：

```text
crossdocked_ca_cond.ckpt
moad_fullatom_cond.ckpt
```

但第一版只做一个主 baseline，避免变成模型比较论文。

---

## 4. 最关键前置：training-overlap audit

### 4.1 为什么必须做

当前 phase0/phase1 clean samples 很可能来自 CrossDocked / IF3 CrossDocked pocket10 archive；DiffSBDD `crossdocked_fullatom_cond.ckpt` 也基于 CrossDocked 训练。因此：

```text
本项目 val/test clean pockets
≠ DiffSBDD unseen pockets
```

如果不做 overlap audit，阶段 2.5 结果只能叫：

```text
same-source diagnostic smoke audit
```

不能叫：

```text
external validity audit on unseen pockets
```

### 4.2 overlap tier 定义

每个 candidate base pocket 必须标记一个 `overlap_tier`：

| tier | 含义 | 用途 |
|---|---|---|
| `T0_exact_pair_seen` | 同一个 protein-ligand pair 明确在 DiffSBDD train | 只做 smoke，不进 external 主结论 |
| `T1_same_pocket_or_target_seen` | 同 pocket / same target / same target_dir 明确在训练中见过 | 只做 debug 或 same-source analysis |
| `T2_ligand_or_scaffold_similar_seen` | ligand / scaffold 与训练集高度相似 | 谨慎分析 |
| `T3_official_diffsbdd_test` | 可映射到 DiffSBDD / Pocket2Mol 官方 test split | 主审计优先 |
| `T4_external_unseen` | 外部数据，未发现训练重叠 | 主审计最优 |
| `T_unknown` | 暂无法判断 | 可跑，但结论必须保守 |

### 4.3 overlap audit 数据来源

Codex 应优先检查或下载以下数据：

```text
DiffSBDD / Pocket2Mol CrossDocked split files
crossdocked_pocket10 pair names
split_by_name.pt
```

若官方 split 文件不可得，至少使用当前 processed sample metadata 里的信息做弱匹配：

```text
source_repo
archive_source_url
original_protein_path
original_pocket10_path
original_ligand_path
target_id
split_group
pdb_id
ligand_id
protein_sha256
ligand_sha256
canonical_smiles
inchi_key
```

### 4.4 overlap audit 输出

新增：

```text
reports/phase2_5_model_induced_audit/training_overlap_audit.csv
reports/phase2_5_model_induced_audit/training_overlap_summary.json
```

`training_overlap_audit.csv` 建议字段：

```text
base_sample_id
base_complex_id
base_split
target_id
split_group
source_dataset
raw_protein_path
raw_ligand_path
original_protein_path
original_pocket10_path
original_ligand_path
protein_sha256
ligand_sha256
canonical_smiles
inchi_key
crossdocked_pair_name
diffsbdd_split_status
exact_pair_overlap
protein_file_overlap
ligand_file_overlap
same_target_overlap
same_pocket_overlap
ligand_exact_overlap
ligand_similarity_max
sequence_identity_to_train_max
overlap_tier
external_validity_eligible
audit_decision
audit_notes
```

---

## 5. Base pocket 选择

### 5.1 输入来源

候选 base pockets 来自阶段 0/1 clean processed samples：

```text
data/processed/v0_1/manifest.parquet
data/processed/v0_1/complexes/*.pkl
data/splits/v0_1/val.txt
data/splits/v0_1/test.txt
reports/phase1_clash_detector/summary.json
reports/phase1_clash_detector/clean_clash_report.csv
```

不要从阶段 2 artificial failed samples 里选：

```text
data/benchmarks/clashrepairbench_rg_artificial/v0_1/samples/*.pkl
```

阶段 2 artificial benchmark 只作为 distribution gap 对照，不作为 DiffSBDD generation 输入。

### 5.2 选择条件

优先选择：

```text
phase1 analysis_status = ok
phase0_pocket8 severe clash = 0
pocket10_all_atoms severe clash = 0
base_split in {val, test}
ligand sanitize pass
pocket10_all_atoms 可用
scaffold / R-group 可拆
overlap_tier in {T3_official_diffsbdd_test, T4_external_unseen, T_unknown}
```

T0/T1 只允许用于 smoke，不进入 external-validity 主结论。

### 5.3 规模

v0：

```text
10 pockets × 20 candidates = 200 generated samples
```

v1：

```text
20 pockets × 50 candidates = 1000 generated samples
```

输出：

```text
reports/phase2_5_model_induced_audit/base_pocket_selection.csv
```

字段：

```text
base_sample_id
base_complex_id
base_split
target_id
split_group
num_valid_rgroups
num_single_anchor_rgroups
protein_scope
overlap_tier
external_validity_eligible
selected_for_generation
selection_reason
```

---

## 6. DiffSBDD frozen generation

### 6.1 配置文件

新增：

```text
configs/phase2_5_model_induced_audit.yaml
```

建议内容：

```yaml
schema_version: "phase2_5_v0_1"
seed: 20260511

inputs:
  processed_root: "data/processed/v0_1"
  manifest: "data/processed/v0_1/manifest.parquet"
  splits_root: "data/splits/v0_1"
  phase1_report_root: "reports/phase1_clash_detector"
  phase2_benchmark_root: "data/benchmarks/clashrepairbench_rg_artificial/v0_1"

outputs:
  run_root: "runs/phase2_5_model_induced_audit"
  report_root: "reports/phase2_5_model_induced_audit"

baseline:
  model_name: "DiffSBDD"
  checkpoint_name: "crossdocked_fullatom_cond.ckpt"
  checkpoint_path: "external/DiffSBDD/checkpoints/crossdocked_fullatom_cond.ckpt"
  mode: "frozen_inference_only"
  n_samples_per_pocket: 20
  sanitize: false
  relax: false
  num_gpus: 2

selection:
  preferred_base_splits: ["val", "test"]
  max_pockets_v0: 10
  preferred_overlap_tiers:
    - "T3_official_diffsbdd_test"
    - "T4_external_unseen"
    - "T_unknown"
  exclude_from_external_main:
    - "T0_exact_pair_seen"
    - "T1_same_pocket_or_target_seen"

postprocess:
  stages:
    - "raw_generated"
    - "standardized_generated"
  do_not_default_relax: true
  do_not_default_redock: true
  do_not_default_complex_minimize: true

detector:
  receptor_scope: "pocket10_all_atoms"
  default_delta_angstrom: 0.4
  delta_sensitivity: [0.3, 0.4, 0.5]
  severe_depth_threshold_angstrom: 0.4
  rgroup_score_alpha: 0.5
  single_region_dominant_ratio: 0.7
  ambiguous_region_dominant_ratio: 0.5

constraints:
  do_not_train: true
  do_not_repair: true
  do_not_tune: true
  do_not_rank_baselines: true
  do_not_modify_phase2_v0_1: true
```

### 6.2 运行方式

新增：

```text
scripts/phase2_5_model_induced_audit.py
```

该脚本可以调用外部 DiffSBDD 仓库命令，也可以先生成可执行 shell scripts。建议实现为 wrapper，保存实际命令到 logs。

两张 RTX 2080 Ti 的用法：

```text
GPU 0 跑一部分 pockets
GPU 1 跑另一部分 pockets
```

不要做模型并行；阶段 2.5 不需要。

---

## 7. all generated samples manifest

必须输出：

```text
reports/phase2_5_model_induced_audit/generation_manifest.parquet
```

关键原则：

```text
记录 all generated samples，不只记录 failed samples。
```

字段建议：

```text
candidate_id
base_sample_id
base_complex_id
base_split
target_id
split_group
overlap_tier
external_validity_eligible
model_name
checkpoint_name
checkpoint_path
checkpoint_md5
checkpoint_sha256
checkpoint_file_size
seed
n_samples
cuda_device
generation_command
inference_config_json
raw_output_path
standardized_output_path
generation_status
postprocess_stage
postprocess_status
sanitize_flag
relax_flag
readable
ligand_valid
failure_taxonomy
repairability_proxy
```

---

## 8. raw / standardized 分层审计

第一版只做两层：

```text
raw_generated
standardized_generated
```

不要默认：

```text
relaxed
redocked
whole-complex-minimized
```

原因：relax / redock / minimization 可能制造或消除 protein-ligand clash，会污染 audit 对真实 raw generation failure 的判断。

如果后续加 relaxed，要单独报告：

```text
raw_failure_taxonomy
standardized_failure_taxonomy
relaxed_failure_taxonomy
```

---

## 9. Ligand-only validity audit

新增模块：

```text
src/clash2feedback/generation_audit/read_generated.py
src/clash2feedback/generation_audit/ligand_validity.py
```

输出：

```text
reports/phase2_5_model_induced_audit/ligand_validity.csv
```

字段：

```text
candidate_id
postprocess_stage
rdkit_readable
rdkit_sanitize_ok
sanitize_error
num_fragments
largest_fragment_selected
allowed_elements_ok
heavy_atom_count
heavy_atom_count_in_range
coords_finite
has_3d_conformer
ligand_internal_severe_clash_count
ligand_internal_max_depth
forcefield_type
energy
energy_check_status
ligand_validity_status
ligand_validity_reason
```

注意：阶段 2.5 的 generated ligand 不一定来自 processed sample 的 original ligand molblock，因此不能直接照搬阶段 2 的 `evaluate_ligand_only_quality()`。可以复用其中的 sanitize、internal clash、energy 检查思想，但需要为 generated SDF 独立实现输入接口。

---

## 10. Protein-ligand clash audit

对 `ligand_valid = true` 的 generated candidates 调用阶段 1 detector：

```text
receptor_scope = pocket10_all_atoms
δ = 0.4 Å
delta_sensitivity = 0.3 / 0.4 / 0.5
```

输出：

```text
reports/phase2_5_model_induced_audit/model_induced_clash_report.csv
```

字段：

```text
candidate_id
base_sample_id
postprocess_stage
receptor_scope
delta_angstrom
num_clash_pairs
num_severe_clash_pairs
total_clash_score
max_clash_depth
mean_clash_depth
delta03_status
delta04_status
delta05_status
```

---

## 11. R-group attribution audit

阶段 2.5 不能直接使用阶段 2 的 `target_rgroup` 逻辑。

原因：

```text
phase2 generated failed pose = 原 ligand 拓扑不变，有人工 target_rgroup；
phase2.5 model-induced generated ligand = 新分子，没有 oracle target_rgroup。
```

阶段 2.5 先判断：

```text
rgroup_attributable = true / false
```

如果 generated ligand 能成功 scaffold / R-group decomposition，再调用 attribution：

```text
dominant_valid_rgroup
dominant_ratio_valid
failure_type
recommended_action
```

如果不能拆，标记：

```text
rgroup_unattributable
```

禁止：

```text
把 predicted_dominant_rgroup 当作 ground-truth target_rgroup。
```

---

## 12. Failure taxonomy

新增模块：

```text
src/clash2feedback/generation_audit/taxonomy.py
```

输出：

```text
reports/phase2_5_model_induced_audit/failure_taxonomy.csv
```

taxonomy：

| taxonomy | 含义 |
|---|---|
| `valid_no_severe_clash` | ligand valid，且无 severe protein-ligand clash |
| `ligand_only_invalid` | ligand 自身非法或内部严重不合理 |
| `postprocess_failed` | generated output 读入、标准化或后处理失败 |
| `rgroup_unattributable` | 不能可靠拆 scaffold / R-group |
| `unsupported_chemistry` | covalent / metal / macrocycle / unsupported element 等 |
| `near_miss_contact` | 有 close contact，但未达到 severe |
| `single_rgroup_clash` | severe clash 主要集中在一个 valid R-group |
| `multi_region_clash` | 多个 R-groups 同时明显 clash |
| `scaffold_clash` | scaffold 发生 severe clash |
| `global_pose_failure` | clash 过深、过多或整体 pose 明显失败 |
| `pocket_mismatch_or_out_of_scope` | generated ligand 不在合理 pocket 范围内或 receptor scope 不匹配 |

---

## 13. Repairability proxy

输出：

```text
reports/phase2_5_model_induced_audit/repairability_proxy.csv
```

proxy：

| proxy | 含义 |
|---|---|
| `local_rgroup_repair_possible` | 看起来适合后续 local R-group repair |
| `global_repose_needed` | 更像整体 pose placement 错误，需要重新摆 pose 或重新生成 |
| `invalid_unrepairable` | ligand 自身坏掉，局部修 R-group 没意义 |
| `unsupported` | 当前系统无法处理 |
| `reject` | 不进入 local repair 主线 |

`local_rgroup_repair_possible` 建议条件：

```text
ligand_valid = true
rgroup_attributable = true
num_severe_clash_pairs >= 1
dominant_valid_rgroup exists
dominant_ratio_valid >= 0.7
scaffold severe = 0
multi-region severe 不明显
max_clash_depth <= 1.5 Å
```

---

## 14. Artificial vs model-induced gap analysis

新增：

```text
src/clash2feedback/generation_audit/gap_analysis.py
```

输出：

```text
reports/phase2_5_model_induced_audit/artificial_vs_model_induced_gap.csv
```

比较三组：

```text
phase2_supported_single_rgroup
model_induced_single_rgroup_clash
model_induced_all_failures
```

比较指标：

```text
num_severe_pairs
max_clash_depth
total_clash_score
dominant_ratio_valid
dominant_ratio_all
R-group size
ligand_validity
internal_clash_count
failure_taxonomy
repairability_proxy
```

这张表回答：

```text
phase2 artificial supported cases 是否和 model-induced single-Rgroup failures 同量级？
真实 generated failures 中有多少属于 local_rgroup_repair_possible？
phase2 artificial benchmark 是否太干净、太简单或太窄？
```

---

## 15. Visual QC

输出：

```text
reports/phase2_5_model_induced_audit/visual_qc_cases.csv
reports/phase2_5_model_induced_audit/visual_qc_notes.md
```

抽样建议：

```text
5 个 valid_no_severe_clash
5 个 ligand_only_invalid / postprocess_failed
5 个 single_rgroup_clash
5 个 global_pose_failure / scaffold_clash
5 个 rgroup_unattributable
```

人工检查：

```text
generated ligand 是否在 pocket 附近；
clash taxonomy 是否空间上合理；
R-group attribution 是否明显错误；
是否存在坐标系错位；
是否存在 postprocess 误判。
```

---

## 16. 代码落地文件建议

新增：

```text
configs/phase2_5_model_induced_audit.yaml

scripts/phase2_5_training_overlap_audit.py
scripts/phase2_5_model_induced_audit.py

src/clash2feedback/generation_audit/__init__.py
src/clash2feedback/generation_audit/overlap.py
src/clash2feedback/generation_audit/diffsbdd_runner.py
src/clash2feedback/generation_audit/read_generated.py
src/clash2feedback/generation_audit/ligand_validity.py
src/clash2feedback/generation_audit/taxonomy.py
src/clash2feedback/generation_audit/gap_analysis.py
src/clash2feedback/generation_audit/reports.py

测试：
tests/test_phase2_5_overlap.py
tests/test_phase2_5_generated_ligand_validity.py
tests/test_phase2_5_taxonomy.py
tests/test_phase2_5_no_oracle_leakage.py
tests/test_phase2_5_reports.py
```

不要把阶段 2.5 逻辑塞进：

```text
src/clash2feedback/perturb/
```

因为 `perturb/` 是阶段 2 artificial injection 模块，而阶段 2.5 是 generation audit。

---

## 17. 执行命令建议

Step 0：training-overlap audit：

```bash
conda run -n c2f_cpu python scripts/phase2_5_training_overlap_audit.py \
  --config configs/phase2_5_model_induced_audit.yaml \
  --manifest data/processed/v0_1/manifest.parquet \
  --output-root reports/phase2_5_model_induced_audit
```

Step 1：model-induced audit：

```bash
conda run -n c2f_cpu python scripts/phase2_5_model_induced_audit.py \
  --config configs/phase2_5_model_induced_audit.yaml \
  --manifest data/processed/v0_1/manifest.parquet \
  --phase1-report-root reports/phase1_clash_detector \
  --phase2-benchmark-root data/benchmarks/clashrepairbench_rg_artificial/v0_1 \
  --run-root runs/phase2_5_model_induced_audit \
  --report-root reports/phase2_5_model_induced_audit
```

验证：

```bash
conda run -n c2f_cpu python -m compileall src scripts
conda run -n c2f_cpu python -m pytest
```

---

## 18. 输出文件清单

报告目录：

```text
reports/phase2_5_model_induced_audit/
  summary.json
  training_overlap_audit.csv
  training_overlap_summary.json
  base_pocket_selection.csv
  generation_manifest.parquet
  ligand_validity.csv
  model_induced_clash_report.csv
  failure_taxonomy.csv
  repairability_proxy.csv
  artificial_vs_model_induced_gap.csv
  visual_qc_cases.csv
  visual_qc_notes.md
  phase2_5_audit.md
```

运行目录：

```text
runs/phase2_5_model_induced_audit/
  raw_candidates/
  standardized_candidates/
  logs/
```

---

## 19. `summary.json` 建议字段

```json
{
  "schema_version": "phase2_5_v0_1",
  "audit_type": "external_validity_audit",
  "baseline_model": "DiffSBDD",
  "checkpoint_name": "crossdocked_fullatom_cond.ckpt",
  "checkpoint_sha256": "",
  "num_base_pockets_selected": 10,
  "num_generated_total": 200,
  "num_readable": 0,
  "num_ligand_valid": 0,
  "num_ligand_invalid": 0,
  "num_rgroup_attributable": 0,
  "num_with_severe_clash": 0,
  "num_single_rgroup_clash": 0,
  "num_multi_region_clash": 0,
  "num_scaffold_clash": 0,
  "num_global_pose_failure": 0,
  "num_near_miss_contact": 0,
  "num_local_rgroup_repair_possible": 0,
  "phase2_coverage_proxy": 0.0,
  "training_overlap_audit_done": true,
  "num_pockets_t0_exact_pair_seen": 0,
  "num_pockets_t1_same_target_seen": 0,
  "num_pockets_t3_official_diffsbdd_test": 0,
  "num_pockets_t4_external_unseen": 0,
  "num_pockets_t_unknown": 0,
  "external_validity_subset_size": 0,
  "same_source_debug_subset_size": 0,
  "does_not_train": true,
  "does_not_repair": true,
  "does_not_rank_baselines": true,
  "does_not_modify_phase2_v0_1": true
}
```

---

## 20. 测试要求

### 20.1 Overlap tests

```text
test_overlap_tier_exact_pair_seen
test_overlap_tier_unknown_when_no_split_available
test_t0_t1_not_external_validity_eligible
test_official_test_external_validity_eligible
```

### 20.2 Generated ligand validity tests

```text
test_generated_sdf_readable
test_sanitize_failed_ligand_only_invalid
test_multifragment_status_recorded
test_coords_not_finite_rejected
test_internal_clash_count_recorded
```

### 20.3 Taxonomy tests

```text
test_valid_no_severe_clash_taxonomy
test_ligand_only_invalid_taxonomy
test_rgroup_unattributable_taxonomy
test_single_rgroup_clash_taxonomy
test_multi_region_clash_taxonomy
test_scaffold_clash_taxonomy
test_global_pose_failure_taxonomy
```

### 20.4 No-oracle-leakage tests

```text
test_no_target_rgroup_required_for_model_induced_audit
test_predicted_dominant_not_ground_truth
test_generated_samples_not_mixed_into_phase3_top1
```

### 20.5 Report tests

```text
test_generation_manifest_includes_all_samples
test_summary_json_schema
test_failure_taxonomy_covers_all_samples
test_gap_analysis_has_phase2_and_model_induced_groups
```

---

## 21. 验收标准

阶段 2.5 v0 关闭条件：

```text
[ ] training-overlap audit 完成；
[ ] 选出 10 个 pockets，或写明不足原因；
[ ] 每个 selected pocket 生成 20 个 candidates，或写明 generation failure；
[ ] all generated samples 全部进入 generation_manifest；
[ ] raw / standardized 输出分开记录；
[ ] ligand_validity.csv 覆盖 all generated samples；
[ ] model_induced_clash_report.csv 覆盖 ligand-valid samples；
[ ] rgroup_attributable gate 已实现；
[ ] rgroup_unattributable 不强行归因；
[ ] failure_taxonomy.csv 覆盖 all generated samples；
[ ] repairability_proxy.csv 生成；
[ ] artificial_vs_model_induced_gap.csv 生成；
[ ] visual_qc_cases.csv 和 visual_qc_notes.md 生成；
[ ] 不使用 predicted dominant R-group 作为真值；
[ ] 不回改 phase2_v0_1；
[ ] 不训练、不 repair、不调参、不做模型排名；
[ ] compileall 和 pytest 通过；
[ ] phase2_5_audit.md 明确写出结论边界。
```

---

## 22. 最高等级自检循环要求

Codex 实施时必须启动一个最高等级的新子 agent 或等价自检流程，命名建议：

```text
phase2_5_completion_auditor
```

职责：

```text
1. 逐条读取本 md 文档中的所有落地要求；
2. 对照当前仓库代码、配置、测试、reports、runs 和实际运行结果；
3. 标记每一项为 done / partial / missing / blocked；
4. 对 partial / missing 项生成修复计划；
5. 执行修复；
6. 再次运行检查；
7. 不断重复，直到所有非 blocked 项均为 done；
8. 如果存在 blocked 项，必须写明阻塞原因、需要的数据/依赖/权限，以及临时替代方案。
```

最终审计文件：

```text
reports/phase2_5_model_induced_audit/phase2_5_completion_audit.md
```

必须包含：

```text
- checklist 全量状态；
- 尚未完成项；
- blocked 项及原因；
- 已完成代码文件；
- 已完成测试文件；
- 已生成报告文件；
- 实际运行命令；
- compileall / pytest 结果；
- generation summary；
- training-overlap summary；
- failure taxonomy summary；
- visual QC 状态；
- 结论边界。
```

---

## 23. 与阶段 3 / 4 / 8 的关系

阶段 2.5 不阻塞阶段 3。

```text
阶段 3：在 phase2 supported_single_rgroup 上评估 rule locator Top-1 / Top-3。
阶段 2.5：审计真实 frozen generator 产生的 failure distribution。
```

阶段 2.5 不等于阶段 4。

```text
阶段 4：repair loop。
阶段 2.5：no repair，只审计。
```

阶段 2.5 不等于阶段 8。

```text
阶段 8：model-induced repair evaluation。
阶段 2.5：model-induced failure taxonomy and external validity audit。
```

---

## 24. 最终落地结论

阶段 2.5 最终版冻结为：

> 使用 frozen DiffSBDD `crossdocked_fullatom_cond.ckpt` 作为单一 generation baseline；先对 phase0/phase1 clean pockets 做 DiffSBDD/CrossDocked training-overlap audit，优先选择 official-test / external-unseen / unknown pockets；然后生成 all candidates，并对 raw / standardized generated ligands 做 ligand validity、protein-ligand clash、R-group attribution、failure taxonomy、repairability proxy 和 artificial-vs-model-induced gap analysis。

一句话：

> **阶段 2.5 是“真实生成失败分布审计”，不是“生成模型比赛”，也不是“修复实验”。**
