# phase4-0-1-diffsbdd-conditional-repair Codex /goal 执行计划

## 1. 仓库事实核查

本计划仅基于本地只读核查生成. 本轮未执行实验, 未调用 DiffSBDD, 未生成候选, 未修改阶段历史结果.

已确认阶段 4.0.1 方案总纲存在:

```text
docs/20260517-Clash2Feedback-GC_阶段4.0.1-DiffSBDD条件局部补全修补方案总纲.md
```

首轮状态核查结果:

```text
git branch --show-current
20260517-061230-phase4-0-1-experiment

git rev-parse HEAD
a25c1d5cb526bc6094024c109ac73975bb5dae82

git status
On branch 20260517-061230-phase4-0-1-experiment
Untracked files:
  docs/20260517-Clash2Feedback-GC_阶段4.0.1-DiffSBDD条件局部补全修补方案总纲.md
nothing added to commit but untracked files present
```

核查结论:

- 当前分支: `20260517-061230-phase4-0-1-experiment`.
- 当前 commit: `a25c1d5cb526bc6094024c109ac73975bb5dae82`.
- 工作区是否干净: 否. 仅发现未跟踪的阶段 4.0.1 方案总纲文档.
- 阶段 4.0 final report 存在: `reports/phase4_0_backend_feasibility/phase4_0_final_experiment_report.md`.
- 阶段 4.0 主结果表存在: `backend_comparison.csv`, `backend_comparison_rates.csv`, `candidate_manifest.csv`, `verifier_outcome.csv`, `adapter_input_manifest.csv`.
- 阶段 4.0 收尾诊断补丁存在: `phase4_0_completion_audit.md`, `phase4_0_closeout_patch_audit.md`, `diffsbdd_center_sensitivity.csv`, `diffsbdd_center_sensitivity.md`.
- 阶段 3 mask seed 存在: `reports/phase3_label_provenance_audit/phase4_mask_seed.csv`.
- `phase4_mask_seed.csv` 当前未修改, SHA256 为 `18cea12cc4f92a8f21f6f9de83c2ba551556e35a19e9d781d3a98f79b99097cc`.
- `selected_cases.csv` 存在, 40 行, 40 个唯一 `case_id`.
- DiffSBDD conditional adapter 存在: `src/clash2feedback/repair/diffsbdd_adapter.py`.
- `external/DiffSBDD` 存在, 但不在 Git 跟踪文件中; 后续不得提交该目录, checkpoint 或大量候选.
- DiffSBDD local commit: `5d0d38d16c8932a0339fd2ce3f67ade98bbdff27`.
- DiffSBDD conditional checkpoint 存在: `external/DiffSBDD/checkpoints/crossdocked_fullatom_cond.ckpt`.
- conditional checkpoint MD5: `166b0c056b31ffdf31d489a63e91e05b`.
- conditional checkpoint SHA256: `07f86764bf569aafbc40a9c15fc02de8e2550437dd0f17f657eab3abe66c372c`.
- DiffSBDD 环境记录存在: `external/DiffSBDD/environment.yaml`, 且 `conda run -n diffsbdd ...` 核查为 `ready cuda=True`.
- 当前仓库已包含阶段 4.0 final report commit: `a25c1d5 phase4.0 final experiment report`.

阶段 4.0 DiffSBDD conditional 真实结果:

- overall: `diffsbdd_conditional_inpainting`, `selected_case_denominator=40`, `attempt_rows=80`, `proposal_count_sum=640`, `candidate_count_sum=624`, `failure_attempts=2`, `reliable_candidate_success_count=17`, `sample_reliable_success_count=9`.
- `center=ligand`: 40 attempts, 312 candidates, 1 execution failure, 5 reliable candidates, 4 reliable cases.
- `center=pocket`: 40 attempts, 312 candidates, 1 execution failure, 12 reliable candidates, 7 reliable cases.
- center 可从现有字段恢复: `adapter_input_manifest.center`, `candidate_manifest.candidate_source`, `candidate_manifest.generation_metadata.center`, `attempt_id`.
- `uses_h_clash_in_generation=False` 在 DiffSBDD conditional 的 adapter/candidate 记录中均成立.

## 2. 字段和实现映射

- 阶段 4.0.1 `selected_cases.csv` 直接复用阶段 4.0 的 40 行, 不重新选择样本, 不改变 denominator.
- `case_id`, `base_sample_id`, `base_split`, `injection_mode`, `difficulty_bin`, `oracle_mask_size`, `oracle_keep_size`, `target_num_severe_pairs`, `max_clash_depth` 原样继承.
- reference/oracle mask 从 `oracle_mask_atom_indices` 读取.
- keep mask 从 `oracle_keep_atom_indices` 读取.
- anchor 字段从 `oracle_anchor_scaffold_atom_idx`, `oracle_anchor_rgroup_atom_idx`, `oracle_anchor_bond_idx` 读取.
- `Phase4CaseInput` 已封装 mask, keep, anchor, failed ligand, protein 和 processed sample 路径.
- `write_keep_submol_sdf()` 已能基于 keep atoms 写出 `fix_atoms.sdf`; `add_n_nodes` 当前使用 mask 原子数.
- DiffSBDD conditional center 由 `build_inpaint_command(..., center="pocket")` 传入 `--center pocket`.
- 阶段 4.0.1 config 中 `centers` 固定为 `["pocket"]`, 不再跑 `center=ligand`.
- K=8/16/32 同时映射到 backend `n_samples` 和 pipeline `candidate_budget.k`; 每个 K 是单轮候选预算, 不是多轮修复.
- `candidate_manifest` 需要新增或派生 `candidate_budget_k`, 并保留 `proposal_count`, `candidate_count`, `runtime_sec`, `uses_h_clash_in_generation`.
- `verifier_outcome` 继续记录阶段 4.0 的 10 项 reliable repair 标准: `candidate_readable`, `ligand_valid`, `fixed_structure_match_success`, `old_clash_resolved`, `no_new_severe_clash`, `scaffold_stable`, `keep_region_stable`, `anchor_integrity`, `edit_compliance`, `pocket_retention`.
- 当前 `phase4_adapter.py` 已支持 fixed structure match, keep region RMSD, variable topology mapping, generated atoms 识别和布尔 `anchor_integrity`.
- 当前字段不足以完整支持 anchor-aware filtering: 缺 `anchor_candidate_idx`, `anchor_match_success`, `generated_fragment_connected_to_anchor`, `generated_fragment_attachment_count`, `candidate_single_fragment`, `candidate_extra_fragment_count`, `anchor_bond_like_distance`, `anchor_reconnect_status`, `anchor_reconnect_reason`.
- 当前字段不足以完整支持 local reconnect check: 缺 `local_reconnect_pass`, `local_reconnect_failure_reason`, `num_generated_components`, `num_anchor_neighbors`, `num_extra_attachments`, `floating_fragment_detected`.
- 需要新增 generated fragment 诊断字段: `target_mask_heavy_atom_count`, `generated_fragment_heavy_atom_count`, `generated_fragment_size_diff`, `generated_fragment_elements`, `target_mask_elements`, `generated_element_mismatch_count`, `generated_size_status`.
- 新增诊断字段只用于筛选, 审计和 failure funnel, 不替代 reliable repair 10 项标准.

可靠修复标准必须保持不变:

- 不是生成出来就算成功.
- 不是没有新碰撞就算成功.
- 不是 `old_clash_resolved` 单独成立就算成功.
- 不得放宽可靠修复标准来制造提升.
- anchor-aware filtering 和 local reconnect check 是新增诊断/筛选, 不替代 reliable repair 标准.

## 3. 具体执行步骤规划

### 3.1 实现准备

- 新增阶段 4.0.1 config, 只启用 `diffsbdd_conditional_inpainting`.
- 新增阶段入口脚本, 从仓库根目录运行, 支持 preflight, formal 和 report-only 模式.
- 复用阶段 4.0 的 case loader, DiffSBDD command builder 和 phase4 verifier.
- 新增 anchor/filter/reconnect/fragment diagnostics 小模块, 避免把复杂逻辑塞入 CLI.
- 新增报告 writer, 所有结果写入 `reports/phase4_0_1_diffsbdd_conditional_repair/`.
- 新增运行目录布局, 所有候选和日志写入 `runs/phase4_0_1_diffsbdd_conditional_repair/`.

### 3.2 5 case preflight 选择

preflight 固定从阶段 4.0 的 40 case 中选择, 不引入新 case. 建议样本:

- `case_001300`: 阶段 4.0 DiffSBDD conditional 成功 case, ligand 和 pocket 均成功, 用于 sanity.
- `case_000509`: `center=pocket` 成功但 `center=ligand` 失败, 用于验证主设置.
- `case_001316`: pocket 下所有候选 anchor failure, 用于 anchor-aware filtering.
- `case_002080`: pocket 下 old clash 未解决, 用于 old clash failure funnel.
- `case_001704`: pocket 下 old clash/no new severe 均失败, 用于 verifier failure path.

如果后续实现时发现这些 case 的运行输入文件缺失, 不得替换为新 denominator; 只能从阶段 4.0 的 40 case 中按同类失败模式替换, 并在 `preflight_cases.csv` 记录替换原因.

### 3.3 40 case 正式复测

- 正式复测直接复用 `reports/phase4_0_backend_feasibility/selected_cases.csv`.
- 不读取阶段 3 全量 357 重新抽样.
- 不重跑 `rule_fixed_topology`, `diffdec_single_rgroup`, `diffsbdd_full_resampling`, `diffsbdd_joint_inpainting`.
- 主设置固定 `center=pocket`.
- K 预算曲线按 `K=8`, `K=16`, `K=32` 分三组运行.
- 每个 K 使用独立 run 子目录, 避免覆盖 raw candidates 或 standardized candidates.

### 3.4 anchor-aware filtering

- 对每个候选先尝试读取 SDF, 识别 keep atoms 与 generated atoms.
- 检查候选是否为单主片段, 是否出现额外孤立小片段.
- 检查 scaffold anchor atom 是否可映射到候选.
- 检查 generated fragment 是否连接到 anchor.
- 统计 attachment 数, extra attachment 数和 anchor 近邻.
- 计算 anchor 到 generated fragment 的 bond-like distance 或连接状态.
- 输出 anchor/reconnect audit 表.
- 筛选结果可以影响候选进入后续统计的诊断分层, 但 final reliable success 仍以 10 项标准为准.

### 3.5 local reconnect check

- 基于 RDKit molecule graph 和 phase4 mapping 结果判断 generated fragment 是否接回固定结构.
- 检查 scaffold anchor atom 是否仍在候选中.
- 检查 generated fragment 是否与 scaffold 有单一主连接.
- 标记 multiple attachment, floating fragment, extra isolated component.
- 输出失败原因枚举, 例如 `anchor_not_mapped`, `generated_fragment_empty`, `floating_fragment`, `multiple_attachments`, `distance_too_large`, `component_split`.

### 3.6 generated fragment diagnostics

- 比较 target mask heavy atom count 和 generated fragment heavy atom count.
- 比较 target mask elements 和 generated fragment elements.
- 统计 element mismatch count.
- 标记 `generated_size_status`: `matched`, `smaller`, `larger`, `empty`, `unknown`.
- 这些字段用于解释 DiffSBDD generated_atom_count_mismatch / element mismatch, 不直接定义成功.

### 3.7 failure funnel 和比较表

- `diffsbdd_failure_funnel.csv` 按 K 分组统计 attempted cases, execution success, generated candidates, readable, ligand valid, fixed match, anchor match, reconnect pass, 10 项可靠标准和 final reliable success.
- `diffsbdd_budget_curve.csv` 按 K 记录 `proposal_count_sum`, `candidate_count_sum`, `reliable_candidate_success_count`, `sample_reliable_success_count`, `cost_per_reliable_case`, `runtime_sec`.
- `diffsbdd_case_level_summary.csv` 每 case 每 K 一行, 记录是否至少有一个 reliable candidate 和主要失败阶段.
- `phase4_0_vs_4_0_1_comparison.csv` 同时包含阶段 4.0 overall 9/40 和 center=pocket 7/40, 避免将双 center 历史结果与 pocket-only 新结果混淆.
- 临时实验汇报写入 `tmp/20260517/phase4-0-1-diffsbdd-conditional-repair-expt-report.md`, 不生成正式 final report.

## 4. 预计新增和修改文件

预计新增:

- `configs/phase4_0_1_diffsbdd_conditional_repair.yaml`.
- `scripts/phase4_0_1_diffsbdd_conditional_repair.py`.
- `src/clash2feedback/repair/diffsbdd_anchor_filter.py`.
- `src/clash2feedback/repair/reconnect_check.py`.
- `src/clash2feedback/repair/fragment_diagnostics.py`.
- `tests/test_phase4_0_1_diffsbdd_conditional.py`.

可能小幅修改:

- `src/clash2feedback/verifier/phase4_adapter.py`: 仅允许为候选诊断字段透传或合并提供接口, 不修改 `RELIABLE_REPAIR_FIELDS`.
- `src/clash2feedback/repair/diffsbdd_adapter.py`: 仅允许增加 `candidate_budget_k` 和阶段 4.0.1 所需 metadata, 不改变阶段 4.0 已有行为.
- 相关 `README.md`: 若新增脚本, 配置, 报告目录或模块改变项目结构/使用方式, 按 AGENTS 规则做简洁同步.

预计新增报告目录:

```text
reports/phase4_0_1_diffsbdd_conditional_repair/
  selected_cases.csv
  preflight_cases.csv
  phase4_0_1_summary.json
  diffsbdd_budget_curve.csv
  diffsbdd_failure_funnel.csv
  diffsbdd_anchor_reconnect_audit.csv
  diffsbdd_candidate_manifest.csv
  diffsbdd_verifier_outcome.csv
  diffsbdd_failure_cases.csv
  diffsbdd_case_level_summary.csv
  phase4_0_vs_4_0_1_comparison.csv
  phase4_0_1_completion_audit.md
```

预计新增运行目录:

```text
runs/phase4_0_1_diffsbdd_conditional_repair/preflight/
runs/phase4_0_1_diffsbdd_conditional_repair/k8/
runs/phase4_0_1_diffsbdd_conditional_repair/k16/
runs/phase4_0_1_diffsbdd_conditional_repair/k32/
runs/phase4_0_1_diffsbdd_conditional_repair/logs/
runs/phase4_0_1_diffsbdd_conditional_repair/raw_candidates/
runs/phase4_0_1_diffsbdd_conditional_repair/standardized_candidates/
```

只读文件:

- `docs/20260517-Clash2Feedback-GC_阶段4.0.1-DiffSBDD条件局部补全修补方案总纲.md`.
- `reports/phase4_0_backend_feasibility/*`.
- `reports/phase3_label_provenance_audit/phase4_mask_seed.csv`.
- `reports/phase3_label_provenance_audit/summary.json`.
- `reports/phase3_label_provenance_audit/phase3_final_experiment_report.md`.
- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/*`.
- `external/DiffSBDD/*`.

禁止修改:

- `reports/phase2_injection/`.
- `reports/phase2_5_model_induced_audit/`.
- `reports/phase3_label_provenance_audit/phase4_mask_seed.csv`.
- `reports/phase4_0_backend_feasibility/phase4_0_final_experiment_report.md`.
- `reports/phase4_0_backend_feasibility/backend_comparison.csv`.
- `reports/phase4_0_backend_feasibility/backend_comparison_rates.csv`.
- `reports/phase4_0_backend_feasibility/candidate_manifest.csv`.
- `reports/phase4_0_backend_feasibility/verifier_outcome.csv`.
- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/`.
- `external/DiffSBDD/`.

## 5. 测试计划

基础检查:

```bash
python -m compileall src scripts
```

阶段测试:

```bash
pytest tests/test_phase4_0_1_diffsbdd_conditional.py -q
pytest tests/test_phase4_backend_feasibility.py -q
```

全量测试:

```bash
pytest -q
```

如果全量测试受环境或外部依赖影响无法运行, 必须在 completion audit 和临时实验汇报中记录原因, 不得写成已通过.

新增测试覆盖:

- 阶段 4.0.1 config 只启用 DiffSBDD conditional, 且 `centers=["pocket"]`.
- K=8/16/32 能正确传入 `--n_samples` 和 `candidate_budget.k`.
- `candidate_manifest` 正确记录 `candidate_budget_k`.
- anchor-aware filtering 单元测试: anchor mapped, generated fragment connected, extra fragment, multiple attachment.
- local reconnect check 单元测试: pass, floating fragment, anchor missing, multiple attachment.
- generated fragment diagnostics 测试: size match, size mismatch, element mismatch.
- 报告 schema 测试: budget curve, failure funnel, anchor reconnect audit, comparison 表字段完整.
- reliable repair 10 项标准未改变.
- 禁止修改范围核查脚本或测试, 确认历史结果和 benchmark 没有 diff.

## 6. 禁止修改范围核查方式

执行前后均记录:

```bash
git status --porcelain=v1
git diff --name-only
```

逐项核查:

- 确认没有修改 `reports/phase2_injection/`: `git status --porcelain=v1 -- reports/phase2_injection`.
- 确认没有修改 `reports/phase2_5_model_induced_audit/`: `git status --porcelain=v1 -- reports/phase2_5_model_induced_audit`.
- 确认没有修改 `phase4_mask_seed.csv`: `git status --porcelain=v1 -- reports/phase3_label_provenance_audit/phase4_mask_seed.csv`, 并复核 SHA256.
- 确认没有修改 `phase4_0_final_experiment_report.md`: `git status --porcelain=v1 -- reports/phase4_0_backend_feasibility/phase4_0_final_experiment_report.md`.
- 确认没有覆盖 `backend_comparison.csv`: `git status --porcelain=v1 -- reports/phase4_0_backend_feasibility/backend_comparison.csv`.
- 确认没有覆盖 `candidate_manifest.csv`: `git status --porcelain=v1 -- reports/phase4_0_backend_feasibility/candidate_manifest.csv`.
- 确认没有覆盖 `verifier_outcome.csv`: `git status --porcelain=v1 -- reports/phase4_0_backend_feasibility/verifier_outcome.csv`.
- 确认没有修改 benchmark: `git status --porcelain=v1 -- data/benchmarks/clashrepairbench_rg_artificial/v0_1`.
- 确认没有提交 external/checkpoint/cache: `git status --porcelain=v1 -- external/DiffSBDD external/DiffDec runs`.
- 确认大量候选 SDF 和日志仅留在 `runs/phase4_0_1_diffsbdd_conditional_repair/`, 且不纳入 Git.

## 7. 冲突项

已发现高风险冲突: 无.

低风险事实差异:

- 当前工作区不干净, 因为阶段 4.0.1 方案文档为未跟踪文件. 该文件正是用户要求先放入 `docs/` 的方案总纲, 不影响计划.
- `tmp/20260517/` 在核查时不存在, 后续生成计划和临时汇报时创建.
- `reports/phase4_0_1_diffsbdd_conditional_repair/` 和 `runs/phase4_0_1_diffsbdd_conditional_repair/` 当前不存在, 属于后续 /goal 预期新增目录.

潜在冲突:

- 如果后续实现发现新增 local reconnect check 与现有 `anchor_integrity` 口径不一致, 不得直接改 reliable repair 10 项标准; 应将 reconnect 作为诊断字段, 并在 completion audit 说明.
- 如果 K=8 的 pocket-only 结果低于阶段 4.0 center=pocket 历史结果, 需先排查随机性, 环境和 adapter 差异, 不得覆盖阶段 4.0 结果.
- 如果需要修改 DiffSBDD 原始源码或去噪过程才能实现目标, 必须停止并人工确认.

是否需要人工确认:

- 当前计划阶段不需要.
- 出现高风险实验口径, 历史结果, denominator, mask 来源, DiffSBDD backend 定义, reliable 标准或是否修改历史结果相关冲突时, 必须等待人工确认.

是否已生成 conflict-report:

- 否. 当前未发现需要生成 conflict report 的高风险冲突.

## 8. 阻塞项

当前未阻塞:

- DiffSBDD checkpoint 不缺失.
- DiffSBDD 环境可用.
- `center` 字段可恢复.
- `selected_cases` 可复用.
- anchor 字段存在.
- external/DiffSBDD 可访问.

潜在阻塞:

- `phase4_adapter.py` 当前不完整支持新增诊断字段透传, 需要实现时小幅扩展.
- anchor-aware filtering 和 local reconnect check 需要严谨处理 variable topology mapping, 否则可能与现有 verifier adapter 口径不一致.
- K=16/32 可能受 GPU 时长或 timeout 影响, 需要在 summary 中记录 `runtime_sec` 和 execution failure.
- 原版 DiffSBDD 不支持强 anchor 约束, 因此本阶段只能做输入适配和后处理筛选, 不能声称模型生成过程理解了 anchor 或 H_clash.

遇到以下任一情况必须停下:

- selected cases 无法复用.
- center 字段无法恢复.
- anchor 字段缺失.
- K 候选预算无法传入.
- 需要修改 reliable repair 10 项标准.
- 需要修改阶段 4.0 历史结果.
- 需要修改 DiffSBDD 原始去噪过程.

## 9. 后续 /goal 执行建议

可以先执行:

- 创建 config, script, 诊断模块和新增测试.
- 运行 compileall 和不调用 DiffSBDD 的单元测试.
- 生成 `selected_cases.csv` 和 `preflight_cases.csv` 的复制/派生逻辑.

必须等待用户确认或停下的步骤:

- 任何高风险冲突.
- 修改 reliable repair 标准.
- 修改阶段 4.0 历史结果.
- 修改 DiffSBDD 原始源码或去噪过程.
- 将阶段 4.0.1 结果写成阶段 4.1 结论.

5 case preflight 建议:

- 使用 `case_001300`, `case_000509`, `case_001316`, `case_002080`, `case_001704`.
- preflight 只验证 schema, K, center=pocket, adapter, filter, reconnect, verifier, report writer 和禁止覆盖保护.
- preflight 通过后才进入 40 case formal.

进入 40 case 正式复测条件:

- compileall 通过.
- 新增单元测试通过.
- preflight 输出完整, 且没有覆盖阶段 4.0/3 历史结果.
- `candidate_budget_k`, anchor/reconnect diagnostics, reliable 10 项标准字段均可写出.

结果解释建议:

- 如果 K=32 仍无明显提升, 关闭本阶段为负结果或限制性结果, 结论写成 DiffSBDD conditional 当前不适合作为阶段 4.1 生成式主后端.
- 如果 K=16/32 明显提升, 结论写成候选预算和后处理筛选改善了可用候选 yield, 不写成 H_clash 或模型主动理解反馈进入生成过程.
- 无论结果如何, 阶段完成后只生成临时实验汇报: `tmp/20260517/phase4-0-1-diffsbdd-conditional-repair-expt-report.md`.
- 不生成正式 final report. 正式报告等待网页 ChatGPT 分析临时汇报后另行决定.
- 后续是否进入阶段 4.0.2 DiffDec adapter 建议保留为独立决策; 本阶段不实现 DiffDec.

