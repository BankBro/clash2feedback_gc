# 阶段 3 标签溯源与阶段 4 掩码种子执行计划

## 1. 当前 git 状态

- 记录时间: 2026-05-13.
- 当前分支: `20260513-160230-phase3-implementation`.
- 当前 commit: `d1ad862f62b531e83ee8c866f4f13e54cab52015`.
- `git status --short` 显示工作区不干净:

```text
?? docs/20260513-Clash2Feedback-GC_阶段3标签溯源循环风险审计与阶段4掩码种子生成方案总纲.md
```

- 风险判断:
  - 该未跟踪文件是本次阶段 3 新口径的方案依据, 后续执行不得误删, 覆盖或假设其已提交.
  - 未发现已跟踪文件修改.
  - 本计划文件自身会作为新增临时计划文件写入 `tmp/20260513/`.

## 2. 仓库事实核查结果

- `target_rgroup` 来自人工扰动流程. `scripts/phase2_inject_artificial_clashes.py` 先枚举合法 single-anchor R 基, 再对目标 R 基执行 `easy_rotation`, `torsion_perturb`, `directed_clash`, 最后在 `_common_row()` 写入 `target_rgroup`.
- `target_atom_indices`, `anchor_scaffold_atom_idx`, `anchor_rgroup_atom_idx`, `anchor_bond_idx` 来自同一个 phase2 target R 基定义, 可用于生成参考掩码和记录 anchor.
- `predicted_dominant_valid_rgroup` 来自 `attribute_clashes_to_rgroups()` 的 `dominant_valid_rgroup`, 在 phase2 中只写入记录字段, 不直接进入 `assign_oracle_split()` acceptance gate.
- `target_score_ratio_valid` 由 `src/clash2feedback/perturb/labels.py` 使用 attribution 的 `valid_rgroup_scores` 计算, 并参与 `supported_single_rgroup` 相关 gate.
- `supported_single_rgroup` 经过 ligand validity, detector, attribution-derived target dominance, target severe, scaffold/non-target no-severe, max-depth, deduplication 等过滤, 应定义为 clean local repair substrate, 不是无偏定位 benchmark.
- phase2.5 `failure_taxonomy.csv` 没有人工 `target_rgroup`, 只有 `dominant_valid_rgroup` 和 `predicted_dominant_is_oracle_ground_truth=false`; 阶段 2.5 model-induced samples 不得进入阶段 3 construction consistency denominator.
- phase2 sample pkl 可恢复 ligand atom count, old clash evidence 和 attribution report, 但不含完整 `rgroups` / `masks`; 阶段 3 需通过 `base_sample_id` 回连 `data/processed/v0_1/complexes/*.pkl` 恢复 R 基定义和 anchor.
- 已抽查验证 S2 `supported_single_rgroup` 的 357 个 case 均可从 processed base sample 映射 oracle / predicted R 基和 anchor.
- 当前数据快照:
  - phase2 manifest: 2610 rows x 70 columns.
  - `supported_single_rgroup`: 357 cases.
  - S2 中 `predicted_dominant_valid_rgroup == target_rgroup`: 357 / 357.

## 3. 字段 / 实现映射

- `target_rgroup`: 人工扰动标签, 来源于 phase2 注入脚本的目标 R 基.
- `target_atom_indices`: phase2 target R 基的完整原子集合记录; 执行时仍用 processed base sample 复核.
- `anchor_scaffold_atom_idx`, `anchor_rgroup_atom_idx`, `anchor_bond_idx`: phase2 target R 基 anchor 记录; 对 predicted/random R 基 anchor 需从 processed base sample 的 `rgroups` 中恢复.
- `predicted_dominant_valid_rgroup`: attribution-derived operational mask policy 输出, 来源于 `attribute_clashes_to_rgroups()`.
- `top_valid_rgroups_json`: attribution 中 `top_valid_rgroups` 的 JSON 记录, 用于 construction consistency rank 检查.
- `target_score_ratio_valid`: attribution-derived valid R-group scores 中 target 占比, 不是独立真值.
- `oracle_split == supported_single_rgroup`: detector + attribution + target gates 共同生成的 clean local repair substrate.
- `old_clash_pairs_json`: phase2 sample pkl 的 `clash_report.clash_pairs`.
- `protein_clash_hot_atoms_json`: 从 old clash pairs 的 `protein_atom_idx` 聚合.
- `protein_clash_hot_residues_json`: 从 old clash pairs 的 `protein_residue_key` 聚合.

## 4. S0 / S1 / S2 集合定义

- S0: `S0_all_valid_injection_attempts`.
  - 条件: `ligand_valid == true`, `ligand_internal_severe_clash_count == 0`, `oracle_split` 不在 `unsupported`, `invalid_conformer`, `duplicate_removed`.
  - 用途: 压力分析, 不作为阶段 4 主输入.
  - 当前估计样本量: 1185.
- S1: `S1_oracle_target_local_clash_set`.
  - 条件: `ligand_valid == true`, `ligand_internal_severe_clash_count == 0`, `target_num_severe_pairs >= 1`, `scaffold_num_severe_pairs == 0`, `non_target_num_severe_pairs == 0`, `max_clash_depth <= 1.5`.
  - 不使用 `target_score_ratio_valid >= 0.7` 作为筛选条件.
  - 用途: 弱化循环风险辅助审计; 仍依赖 detector region-level pair 统计, 不是无循环 benchmark.
  - 当前估计样本量: 467, 包含 357 个 S2, 108 个 `duplicate_removed`, 2 个 `ambiguous_region`.
- S2: `S2_phase2_supported_single_rgroup`.
  - 条件: `oracle_split == "supported_single_rgroup"`.
  - 用途: 阶段 4 clean local repair 主输入, 阶段 3 construction consistency check 分母.
  - 当前样本量: 357.
  - `circularity_risk_level = high`.

## 5. 掩码生成逻辑

- 配体全集:
  - 从 phase2 sample pkl 的 `failed_ligand_coords` 或 processed base sample 的 `ligand.num_atoms` 得到 `all_ligand_atoms = [0, ..., num_atoms - 1]`.
- 参考掩码:
  - `oracle_mask_rgroup = target_rgroup`.
  - `oracle_mask_atom_indices = target_rgroup` 对应的完整 R 基原子集合.
  - `oracle_keep_atom_indices = all_ligand_atoms - oracle_mask_atom_indices`.
  - 语义: 人工扰动标签 / 阶段 4 参考掩码来源, 不是无偏定位真值.
- 自动预测掩码:
  - `predicted_mask_rgroup = predicted_dominant_valid_rgroup`.
  - `predicted_mask_atom_indices = predicted_mask_rgroup` 对应的完整 R 基原子集合.
  - `predicted_keep_atom_indices = all_ligand_atoms - predicted_mask_atom_indices`.
  - 语义: attribution-derived operational mask policy, 不是 ground truth.
- 随机掩码:
  - `random_mask_rgroup` 从同一配体的合法 R 基候选中选择.
  - `random_mask_atom_indices = random_mask_rgroup` 对应的完整 R 基原子集合.
  - `random_keep_atom_indices = all_ligand_atoms - random_mask_atom_indices`.
- 编辑掩码:
  - 三类掩码的编辑区域均为整个 R 基.
- 保留掩码:
  - 配体中除编辑掩码外的所有原子.
- anchor:
  - 对 oracle / predicted / random 分别记录对应 R 基的 `anchor_scaffold_atom_idx`, `anchor_rgroup_atom_idx`, `anchor_bond_idx`.
  - anchor 不默认加入自由编辑掩码.
- 必须记录:
  - `predicted_equals_oracle`.
  - `random_equals_oracle`.
  - `random_equals_predicted`.

## 6. Random size-matched 选择规则和 fallback

- 候选池:
  - 来自 processed base sample 的 `rgroups`.
  - 条件为 `is_valid_for_phase0 == true`, `is_single_anchor == true`, `atom_indices` 非空.
- 主规则:
  - 优先排除 `target_rgroup`.
  - 优先排除 `predicted_dominant_valid_rgroup`.
  - 以 oracle/reference mask 的 heavy atom count 为目标大小.
  - 候选按 `abs(candidate_heavy_atom_count - oracle_heavy_atom_count)` 升序排序.
  - 并列时使用固定 seed 和 `case_id` 派生的 deterministic random key 打散.
- fallback 规则:
  - fallback 1: 若排除 target + predicted 后为空, 改为只排除 target.
  - fallback 2: 若仍为空, 标记 `random_mask_available=false`, 不强行复用 oracle.
  - fallback 3: 若候选 R 基缺少 anchor 或原子集合, 标记不可用并写入 `random_mask_fallback_reason`.
- 当前 S2 核查:
  - 357 / 357 均有排除 target + predicted 后的随机候选.
  - 当前不预计触发不可用 fallback, 但实现必须保留 fallback 字段.

## 7. `phase4_mask_seed.csv` schema

### 7.1 基础字段

```text
case_id
base_sample_id
base_complex_id
base_split
derived_split
oracle_split
injection_mode
difficulty_bin
set_membership_s0
set_membership_s1
set_membership_s2
circularity_risk_level
```

### 7.2 标签与归因字段

```text
target_rgroup
target_atom_indices
predicted_dominant_valid_rgroup
top_valid_rgroups_json
target_score_ratio_valid
dominant_ratio_valid_rgroups
failure_type
recommended_action
predicted_equals_oracle
```

### 7.3 参考掩码字段

```text
oracle_mask_rgroup
oracle_mask_atom_indices
oracle_keep_atom_indices
oracle_anchor_scaffold_atom_idx
oracle_anchor_rgroup_atom_idx
oracle_anchor_bond_idx
oracle_mask_available
oracle_mask_reason
```

### 7.4 自动预测掩码字段

```text
predicted_mask_rgroup
predicted_mask_atom_indices
predicted_keep_atom_indices
predicted_anchor_scaffold_atom_idx
predicted_anchor_rgroup_atom_idx
predicted_anchor_bond_idx
predicted_mask_available
predicted_mask_reason
```

### 7.5 随机掩码字段

```text
random_mask_rgroup
random_mask_atom_indices
random_keep_atom_indices
random_anchor_scaffold_atom_idx
random_anchor_rgroup_atom_idx
random_anchor_bond_idx
random_mask_available
random_mask_policy
random_mask_fallback_reason
random_equals_oracle
random_equals_predicted
```

### 7.6 旧碰撞证据字段

```text
old_clash_pairs_json
protein_clash_hot_atoms_json
protein_clash_hot_residues_json
target_num_severe_pairs
non_target_num_severe_pairs
scaffold_num_severe_pairs
num_total_severe_pairs
max_clash_depth
total_clash_score
```

### 7.7 阶段 4 使用字段

```text
phase4_0_backend_feasibility_candidate
phase4_1_formal_loop_candidate
phase4_candidate_reason
phase4_exclusion_reason
```

## 8. 具体执行步骤

1. 新建 `configs/phase3_label_provenance_audit.yaml`.
   - 写入 phase2 benchmark, phase2 reports, processed root, phase2.5 reports, 输出目录和 random seed.
   - 显式写入 `do_not_mix_model_induced_into_construction_consistency: true`.
2. 新建 `src/clash2feedback/feedback/mask_seed.py`.
   - 实现只读加载 phase2 manifest / phase2 samples / processed base samples.
   - 实现 R 基定义恢复, mask 生成, random size-matched 选择, old clash hot atoms/residues 聚合.
   - 实现 S0 / S1 / S2 标记和 construction consistency row 生成.
3. 新建 `scripts/phase3_label_provenance_audit.py`.
   - 只做配置加载, 路径解析, 调用核心函数和写出报告.
   - 从仓库根目录可运行.
4. 写出 `reports/phase3_label_provenance_audit/`.
   - `summary.json`.
   - `phase2_label_provenance_audit.md`.
   - `circularity_risk_audit.md`.
   - `field_dependency_table.csv`.
   - `set_definition_report.csv`.
   - `construction_consistency_report.csv`.
   - `locator_stress_report_s0.csv`.
   - `locator_stress_report_s1.csv`.
   - `phase4_mask_seed.csv`.
   - `phase3_completion_audit.md`.
5. 同步 README.
   - `README.md`.
   - `configs/README.md`.
   - `scripts/README.md`.
   - `reports/README.md`.
   - `src/README.md`.
6. 添加测试.
   - `tests/test_phase3_mask_seed.py`.
   - `tests/test_phase3_label_provenance.py`.
7. 运行验证.
   - `python -m compileall src scripts`.
   - `python -m pytest tests/test_phase3_*.py`.
   - 必要时运行 `python -m pytest`.
8. 执行后核查禁止修改范围.
   - `git status --short`.
   - `git diff --name-only`.
   - 确认禁止路径没有被修改.

## 9. 预计新增文件列表

```text
configs/phase3_label_provenance_audit.yaml
scripts/phase3_label_provenance_audit.py
src/clash2feedback/feedback/mask_seed.py
reports/phase3_label_provenance_audit/summary.json
reports/phase3_label_provenance_audit/phase2_label_provenance_audit.md
reports/phase3_label_provenance_audit/circularity_risk_audit.md
reports/phase3_label_provenance_audit/field_dependency_table.csv
reports/phase3_label_provenance_audit/set_definition_report.csv
reports/phase3_label_provenance_audit/construction_consistency_report.csv
reports/phase3_label_provenance_audit/locator_stress_report_s0.csv
reports/phase3_label_provenance_audit/locator_stress_report_s1.csv
reports/phase3_label_provenance_audit/phase4_mask_seed.csv
reports/phase3_label_provenance_audit/phase3_completion_audit.md
tests/test_phase3_mask_seed.py
tests/test_phase3_label_provenance.py
```

## 10. 预计修改文件列表

```text
README.md
configs/README.md
scripts/README.md
reports/README.md
src/README.md
```

## 11. 测试计划

- 单元测试:
  - oracle / predicted / random mask atom indices 与 keep mask 互补且无交集.
  - anchor 只记录, 不进入 edit mask.
  - random size-matched 选择可复现.
  - fallback reason 在候选不足时可解释.
  - `predicted_dominant_valid_rgroup` 不被当作 ground truth.
  - phase2.5 无 `target_rgroup`, 不进入 construction consistency denominator.
- 集成测试:
  - 对真实 S2 生成 in-memory seed rows, 验证 oracle / predicted / random 均可映射.
  - 验证 S2 `circularity_risk_level=high`.
  - 验证 `phase4_mask_seed.csv` schema 完整.
  - 验证 construction consistency 报告不使用 independent localization accuracy 命名.
- 验证命令:

```bash
python -m compileall src scripts
python -m pytest tests/test_phase3_*.py
python -m pytest
```

## 12. 禁止修改范围核查方式

- 执行前记录:

```bash
git status --short
git branch --show-current
git rev-parse HEAD
```

- 执行后记录:

```bash
git status --short
git diff --name-only
```

- 若 `git diff --name-only` 命中以下路径, 必须停止并报告:

```text
reports/phase2_injection/*.csv
reports/phase2_injection/*.json
reports/phase2_injection/*.parquet
reports/phase2_injection/*.jsonl
reports/phase2_injection/*trace*
reports/phase2_5_model_induced_audit/*.csv
reports/phase2_5_model_induced_audit/*.json
reports/phase2_5_model_induced_audit/*.parquet
reports/phase2_5_model_induced_audit/*.jsonl
reports/phase2_5_model_induced_audit/*trace*
data/benchmarks/clashrepairbench_rg_artificial/v0_1/
runs/phase2_5_model_induced_audit/raw_candidates/
runs/phase2_5_model_induced_audit/standardized_candidates/
```

## 13. 冲突项

- 历史阶段 2 final report 中仍保留旧口径: “阶段 3 主 Top-1 / Top-3 分母”.
  - 处理方式: 不回写历史报告; 在阶段 3 新报告中明确降级为 construction consistency check.
  - 是否需要人工确认: 否, 因为总纲已明确新口径, 且不修改历史结果.
- phase2 sample pkl 不含完整 `rgroups` / `masks`.
  - 处理方式: 用 `base_sample_id` 回连 processed base sample 作为 R 基定义来源.
  - 是否需要人工确认: 否, 已抽查 S2 357 cases 均可映射; 执行时仍需做全量断言.

## 14. 阻塞项

- 当前无阻塞项.
- 若后续执行发现以下任一情况, 需先生成 `tmp/20260513/phase3-label-provenance-mask-seed-conflict-report.md`, 并停止冲突部分:
  - 任一 S2 case 无法恢复 oracle R 基原子集合.
  - 任一 S2 case 无法恢复 anchor.
  - 任一 S2 case 无法恢复 old clash evidence.
  - `predicted_dominant_valid_rgroup` 实际参与 acceptance gate 的新证据.
  - phase2.5 model-induced 样本被要求进入 construction consistency denominator.
  - 需要修改 phase2 / phase2.5 历史结果或 benchmark 数据才能推进.

## 15. 后续 /goal 执行建议

建议使用以下目标进入执行:

```text
/goal 在 /home/lyj/mnt/project/clash2feedback_gc 中, 严格按 tmp/20260513/phase3-label-provenance-mask-seed-codex-goal-exec-plan.md 执行阶段 3 label provenance audit, circularity risk audit, construction consistency check 和 phase4 mask seed generation. 只新增阶段 3 配置, 脚本, 可复用模块, 测试和 reports/phase3_label_provenance_audit/ 产物, 并同步必要 README. 不训练模型, 不调用生成器, 不修复分子, 不生成阶段 3 最终实验报告, 不修改 phase2 / phase2.5 历史结果或 data/benchmarks/clashrepairbench_rg_artificial/v0_1/, 不自动提交. 若发现高风险冲突, 先生成 tmp/20260513/phase3-label-provenance-mask-seed-conflict-report.md 并停止冲突部分等待人工确认.
```
