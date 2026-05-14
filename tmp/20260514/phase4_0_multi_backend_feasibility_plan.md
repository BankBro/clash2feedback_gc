# 阶段 4.0: 多后端参考掩码修复可行性与能力对比审计计划

> status: draft  
> doc_id: phase4-0-multi-backend-feasibility-plan  
> version: v1  
> created: 2026-05-14  
> updated: 2026-05-14  
> parent: none  
> supersedes: none  

## 1. 背景现状与目标

### 1.1 背景

阶段 4.0 的问题不是证明完整 Clash2Feedback-GC 闭环已经成立, 而是先用参考掩码, 即 oracle mask, 审计多个候选修复后端是否具备最基本的局部修复能力. 本阶段只回答: 给定正确修复区域时, 后端能否生成可读取, 可验证, 尽量局部, 并且不制造新严重碰撞的候选.

阶段 4.0 不训练模型, 不微调 DiffSBDD 或 DiffDec, 不改它们的原始去噪过程, 不做 Random / Predicted / Oracle 正式对照, 不把 `H_clash` 写成进入生成过程, 不使用 Vina / docking score 作为主指标, 不回写阶段 2, 阶段 2.5, 阶段 3 历史结果, 也不覆盖 `reports/phase3_label_provenance_audit/phase4_mask_seed.csv`.

### 1.2 现状

本地仓库状态已经做轻量核查:

- 当前分支: `20260514-043614-phase4-0`.
- 当前 commit: `ccba02bf6e17c46e89dfec3dd1e1f5e64e4c0842`.
- 本地 `main`: 同一 commit, `ccba02bf6e17c46e89dfec3dd1e1f5e64e4c0842`.
- `main` 已包含阶段 3 产物: `reports/phase3_label_provenance_audit/` 下存在 `summary.json`, `phase3_final_experiment_report.md`, `phase4_mask_seed.csv`, `random_mask_balance_summary.csv`, `construction_consistency_report.csv` 等文件.
- `phase4_mask_seed.csv`: 存在, 数据行数 357, 全部属于 S2 `supported_single_rgroup`, 全部 `phase4_0_backend_feasibility_candidate=True`.
- 关键字段状态: `oracle_mask_atom_indices`, `oracle_keep_atom_indices`, `oracle_anchor_scaffold_atom_idx`, `oracle_anchor_rgroup_atom_idx`, `old_clash_pairs_json` 均存在且 357 行非空.
- S2 分布: `easy_rotation=117`, `directed_clash=122`, `torsion_perturb=118`; `easy=239`, `medium=118`; `train=260`, `val=18`, `test=79`.
- oracle mask size: min 2, median 4, max 11.
- old clash pairs: min 1, median 3, max 21.
- `target_num_severe_pairs`: min 1, median 1, max 12.
- `max_clash_depth`: min 0.402, median 0.731, max 1.496.

外部后端状态:

- `external/DiffSBDD`: 已将 `origin` 切换为 `https://github.com/BankBro/DiffSBDD.git`, 当前仍在 detached HEAD, commit `5d0d38d16c8932a0339fd2ce3f67ade98bbdff27`.
- `external/DiffSBDD/checkpoints/crossdocked_fullatom_cond.ckpt`: 存在, 17861341 bytes. 阶段 2.5 记录显示 `diffsbdd` conda 环境和官方 `generate_ligands.py` smoke test 曾成功.
- `crossdocked_fullatom_joint.ckpt`, Binding MOAD checkpoint, CA checkpoint: 当前本地未发现.
- `external/DiffDec`: 已从 `https://github.com/BankBro/DiffDec.git` 克隆, 当前 commit `916ae14207b2783a90336bb8509374535c5791f9`, 分支 `master`.
- DiffDec conda 环境: 本地 `conda env list` 中未发现专用 DiffDec 环境.
- DiffDec checkpoint: 当前未发现 `external/DiffDec/ckpt/*.ckpt`.
- DiffDec 官方示例: 本轮未执行, 因为当前是计划优先, 且环境和 checkpoint 尚未就绪.

### 1.3 目标

本计划的交付目标是形成可执行的阶段 4.0 预检方案, 并在执行前冻结以下内容:

- 第一轮后端矩阵和后端计数口径.
- 3-5 个 preflight S2 case 的抽取规则和候选样本.
- 40 个正式小规模 S2 case 的分层抽取规则.
- 各后端的输入适配, 输出读取, 固定结构匹配, anchor integrity, keep compliance 和 verifier 接入方案.
- model inventory, adapter manifest, candidate manifest, verifier outcome 和 blocked backends 的输出契约.
- 哪些事情可以立即预检, 哪些事情需要先下载 checkpoint 或配置环境, 哪些事情需要用户确认.

## 2. 推荐方案概览

### 2.1 一句话方案

阶段 4.0 建议先做 `3-5 case preflight`, 后端优先级为规则型局部构象修复和 DiffSBDD CrossDocked full-atom conditional inpainting, 同步做 DiffSBDD joint checkpoint 和 DiffDec 环境/模型可用性预检. preflight 通过后再固定 40 个 S2 case, 每个 backend-model cell 每个样本最多输出 8 个候选.

### 2.2 核心流程

1. 冻结输入: 只读取 `reports/phase3_label_provenance_audit/phase4_mask_seed.csv`, 不覆盖该文件.
2. 生成选择表: 按 deterministic seed 选出 `selected_cases_preflight.csv` 和后续 `selected_cases.csv`.
3. 生成 adapter 输入: 每个 case 输出 failed ligand, protein pocket, oracle mask, keep atoms, anchor 和 old clash evidence.
4. 按 backend-model cell 生成候选: 每个样本最多保留 8 个候选, 记录 `proposal_count`, `generation_status`, `runtime_sec`, `failure_reason`.
5. 统一读取和匹配: RDKit 读取候选 SDF, 根据 backend 类型做 atom mapping, fixed structure matching, anchor 检查和 keep region 检查.
6. 统一验证: same-topology 候选直接调用 `verify_repair`; atom order 或 topology 变化候选先经过 mapping adapter, 无法映射则进入 `verifier_input_adapter_failed`.
7. 汇总报告: 输出 model inventory, backend preflight report, blocked backends, candidate manifest, verifier outcome, failure cases 和 summary JSON.

### 2.3 关键接口与数据

输入文件:

- `reports/phase3_label_provenance_audit/phase4_mask_seed.csv`.
- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/manifest.parquet`.
- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/samples/*.pkl`.
- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/ligands/*_failed.sdf`.
- `data/processed/v0_1/complexes/*.pkl`.
- `data/raw_complexes/*/protein.pdb` 和 `ligand.sdf`, 仅用于构造外部后端输入.

计划输出目录:

```text
reports/phase4_0_backend_feasibility/
  model_inventory.csv
  backend_preflight_report.md
  blocked_backends.md
  selected_cases_preflight.csv
  adapter_input_manifest.csv
  candidate_manifest.csv
  verifier_outcome.csv
  failure_cases.csv
  phase4_0_preflight_summary.json
runs/phase4_0_backend_feasibility/
  rule_only/
  diffsbdd_inpainting/
  diffdec/
  full_resampling/
  logs/
```

后续正式 40 case 小规模实验额外输出:

```text
reports/phase4_0_backend_feasibility/selected_cases.csv
reports/phase4_0_backend_feasibility/phase4_0_small_scale_summary.json
```

### 2.4 边界条件与不变式

- 本阶段只使用 oracle mask.
- 本阶段不训练, 不微调, 不改 DiffSBDD / DiffDec 原始去噪过程.
- DiffSBDD / DiffDec plain backend 只能表述为 candidate inpainting backend 或 local constrained resampling backend.
- `old_clash_resolved` 和 `no_new_severe_clash` 由本项目 verifier 或 verifier adapter 判断, 不是后端生成过程的内置目标.
- 每个 backend-model cell 每个样本最终最多 8 个候选, 内部可尝试更多 proposal, 但必须记录 `proposal_count`.
- DiffDec 必须调研和尝试预检, 但 DiffDec blocked 不阻塞规则型和 DiffSBDD 主线.
- checkpoint, 外部源码和大量候选 SDF/log 不提交 Git.

## 3. 专题设计

### 3.1 专题清单与边界

专题 A: 样本选择与冻结输入.  
专题 B: 规则型局部构象修复.  
专题 C: DiffSBDD inpainting 与 full resampling.  
专题 D: DiffDec 单取代基重采样.  
专题 E: 统一 verifier adapter 与失败分类.  

### 3.2 专题 A: 样本选择与冻结输入

**(1)** 当前状态与采纳版本

v1 draft. 阶段 4.0 输入可用, 不需要伪造或重建 `phase4_mask_seed.csv`.

**(2)** 当前设计

预检样本选择:

- 从 357 个 S2 case 中选择 3-5 个.
- 优先 `base_split in {val, test}`.
- oracle mask size 优先 3-6.
- `target_num_severe_pairs <= 3`.
- `max_clash_depth` 优先 0.55-1.10, 避免过浅或极深.
- 覆盖 `easy_rotation`, `directed_clash`, `torsion_perturb`.
- 至少包含 1 个 medium case, 如 val/test medium 不足, 可从 train medium 中补 1 个, 并标记为 `preflight_train_medium_coverage`.

当前轻量核查给出的候选 preflight cases:

| case_id | base_sample_id | split | mode | difficulty | mask_size | severe_pairs | max_depth | note |
|---|---|---|---|---|---:|---:|---:|---|
| `case_001001` | `complex_crossdocked_000023` | test | directed_clash | easy | 5 | 1 | 0.720 | directed val/test 首选 |
| `case_001243` | `complex_crossdocked_000025` | test | easy_rotation | easy | 5 | 1 | 0.691 | easy rotation 首选 |
| `case_000982` | `complex_crossdocked_000022` | test | torsion_perturb | easy | 5 | 1 | 0.743 | torsion 首选 |
| `case_001238` | `complex_crossdocked_000025` | test | directed_clash | medium | 5 | 1 | 1.162 | val/test medium 覆盖, 深度略高但仍在 S2 范围 |
| `case_000703` | `complex_crossdocked_000019` | train | easy_rotation | medium | 4 | 1 | 0.643 | 如需 medium 且非 directed, 用作补充 |

正式 40 个 S2 case 选择:

- 固定随机种子: `20260514`.
- 输出 `reports/phase4_0_backend_feasibility/selected_cases.csv`.
- 先按 `injection_mode x difficulty_bin x base_split` 分层, 空桶回退到 `injection_mode x difficulty_bin`, 再回退到 `injection_mode`.
- 目标 backend feasibility 小规模矩阵建议使用近似全 S2 分布:
  - injection mode: `directed_clash=14`, `easy_rotation=13`, `torsion_perturb=13`.
  - difficulty: `easy=27`, `medium=13`.
  - base split: `train=29`, `test=9`, `val=2`, 除非用户要求 val/test-only.
- 对每个候选计算派生字段: `oracle_mask_size`, `random_mask_size_diff`, `max_clash_depth_bin`, `target_num_severe_pairs_bin`.
- 用 `sha256(f"{seed}:{case_id}")` 作为稳定 tie-breaker.
- 对同一个 `base_sample_id` 设置软上限 3 个 case. 若分层覆盖不足, 明确记录放宽原因.

**(3)** 历史版本演进

- v1: 当前版本, 以阶段 3 已冻结的 S2 `phase4_mask_seed.csv` 作为唯一输入.

**(4)** 实验记录

| baseline | profile | impl | metric | result | note |
|---|---|---|---|---|---|
| input audit | S2 mask seed | read-only local check | rows=357, required fields complete | pass | 只验证输入可用性, 不执行修复实验 |

**(5)** 风险与兼容性

- val/test medium case 很少, 若 40 case 要覆盖 medium 的多种 injection mode, 需要引入 train case.
- 多个 case 可来自同一 base complex, 需要 soft cap 避免 40 case 被少数 scaffold 主导.
- `phase4_mask_seed.csv` 中 `random_mask_size_diff` 只用于分层记录, 阶段 4.0 不做 Random / Predicted / Oracle 正式对照.

**(6)** 未决问题与下一步

- 是否要求正式 40 case val/test-only. 默认不要求, 按 S2 全量分布抽样.
- 预检前需要生成 `selected_cases_preflight.csv`, 但本计划文档不直接执行生成候选.

### 3.3 专题 B: 规则型局部构象修复

**(1)** 当前状态与采纳版本

v1 draft. 规则型后端是第一轮必须完成的硬后端, 不依赖外部 checkpoint.

**(2)** 当前设计

输入:

- failed ligand topology and coords: 优先读取 `*_failed.sdf`, 也可从 phase2 sample 的 `failed_ligand_coords` 和 base ligand topology 重建.
- protein sample: base processed sample, ligand coords 替换为 failed coords.
- oracle edit atoms: `oracle_mask_atom_indices`.
- keep atoms: `oracle_keep_atom_indices`.
- anchor: `oracle_anchor_scaffold_atom_idx`, `oracle_anchor_rgroup_atom_idx`, `oracle_anchor_bond_idx`.
- old clash evidence: `old_clash_pairs_json`.

适用样本:

- 单 anchor R-group.
- anchor bond 存在且 bond order 可解析.
- target R-group 子图连通, 且移动 target 子图不需要移动 scaffold.
- RDKit 可读取 failed SDF, 且 ligand atom order 可与 phase2/base sample 对齐.

候选生成:

- 固定 scaffold 和非目标区域.
- 只移动 oracle mask 对应 target R-group.
- anchor rotation: 以 scaffold anchor atom 到 rgroup anchor atom 的连接键为旋转轴, 旋转 target R-group 整体.
- internal torsion: 从 base sample 的 `rgroups[*].rotatable_bond_indices` 或 RDKit rotatable bond SMARTS 中识别 target R-group 内部可旋转键, 只旋转远离 anchor 的 distal component.
- hybrid: 先做 anchor rotation, 再做内部 torsion 的小规模组合.
- 每个样本内部最多评估例如 64-256 个 proposals, 最终按 verifier 相关分数和去重规则保留最多 8 个 candidates.
- 记录 `proposal_count`, `candidate_source in {anchor_rotation, internal_torsion, hybrid}`, `angles_deg`, `torsion_bond`, `dedup_reason`.

防止 clean pose 泄漏:

- 生成器只使用 failed pose, topology, oracle mask, anchor 和 protein clash detector.
- 不读取 original clean coords 作为优化目标, 不按 original RMSD 排序.
- original clean coords 只允许在后处理审计中计算 `original_similarity_flag`, 用于发现意外近似复制, 不作为候选选择标准.

接入 verifier:

- rule backend 保持原始 ligand atom order 和 atom count, 可直接调用 `verify_repair(sample, failed_coords, repaired_coords, edit_region=oracle_mask_rgroup, config=phase1_config, old_clash_report=old_report)`.
- 额外记录 anchor bond length, anchor atom displacement, edit-only displacement fraction.

**(3)** 历史版本演进

- v1: 固定拓扑 torsion/rotation 搜索, 不做力场全局优化, 不做 pocket-aware minimization.

**(4)** 实验记录

| baseline | profile | impl | metric | result | note |
|---|---|---|---|---|---|
| rule backend | plan only | no generation | adapter design ready | pending | 需下一步 preflight 执行 |

**(5)** 风险与兼容性

- 部分 target R-group 可能没有有效内部 rotatable bond, 只能做 anchor rotation.
- 如果 anchor bond 本身不是合理旋转轴, rigid rotation 可能破坏局部几何, 需要 bond length/chirality gate.
- rule backend 固定拓扑, 不适合需要替换原子类型或改变取代基大小的 case.

**(6)** 未决问题与下一步

- 实现前先在 3-5 case 上输出 adapter manifest 和 dry-run proposal count.
- 确认是否加入轻量 MMFF/UFF ligand-only relaxation. 默认不加入, 避免 keep region 漂移.

### 3.4 专题 C: DiffSBDD inpainting 与 full resampling

**(1)** 当前状态与采纳版本

v1 draft. DiffSBDD CrossDocked full-atom conditional checkpoint 当前可作为优先预检对象. CrossDocked full-atom joint checkpoint 当前本地缺失, 需要下载后再确认能否用于 `inpaint.py`.

**(2)** 当前设计

DiffSBDD local inpainting 输入构造:

- 删除 `oracle_mask_atom_indices` 对应 target R-group.
- 将 `oracle_keep_atom_indices` 对应原子写成 `fix_atoms.sdf`, 坐标来自 failed ligand, atom order 保留原 base order 子序列.
- `ref_ligand`: 第一轮使用 failed ligand SDF 定义 pocket, 因为它反映待修复 failed pose 的 pocket 位置. 可在补充对照中比较 original ligand SDF, 但不能作为默认以免引入 clean pose 泄漏.
- `pdbfile`: 使用对应 raw protein/pocket PDB.
- `add_n_nodes`: 第一轮使用 target R-group heavy atom count, 即 oracle mask 中 heavy atom 数.
- `center`: 第一轮同时 dry-run `ligand` 和 `pocket` 的 input manifest, 正式 preflight 优先 `center=pocket` 或小样本并行比较. 原因是 `center=ligand` 会围绕 keep substructure COM 初始化, 对大 scaffold + 小缺口可能偏离真实出口.
- `n_samples=8`, `timesteps` 先使用官方示例默认或保守 50, preflight 只跑小样本.

条件模型:

- `crossdocked_fullatom_cond.ckpt` 当前存在.
- DiffSBDD README 明确 `inpaint.py` 示例使用 conditional full-atom checkpoint.
- 预期可优先跑 `inpaint.py`, 但仍需在阶段 4.0 preflight 中实测 model load, input adapter 和 output readability.

联合模型:

- `crossdocked_fullatom_joint.ckpt` 当前本地缺失.
- 代码预读显示 `inpaint.py` 直接调用 `model.ddpm.inpaint(ligand, pocket, lig_fixed, center=...)`. conditional DDPM 的签名支持该调用, joint `EnVariationalDiffusion.inpaint` 需要 `lig_fixed` 和 `pocket_fixed`, 且不支持 `center` 参数.
- 因此当前判断是: `crossdocked_fullatom_joint.ckpt` 直接跑原版 `inpaint.py` 可能失败, 需要下载 checkpoint 后做 smoke test. 若失败, 可在本项目 wrapper 中调用 joint model 的 inpaint 接口并固定 pocket, 但不得修改 DiffSBDD 原始去噪过程.

输出检查:

- RDKit 读取 SDF, 统计 readable rate.
- fixed structure matching: 优先用 keep substructure MCS/子结构匹配, 再用 element + coordinate nearest 做一致性检查.
- 连接点检查: candidate 中必须有从 mapped scaffold anchor 到 generated edit region 的连接, 且不能出现多余 keep-edit attachments.
- 若 output atom order 不是 base order, 通过 mapping adapter 计算 scaffold RMSD, keep RMSD, anchor integrity 和 edit compliance.
- 无法映射的候选记录为 `fixed_structure_match_failed`, 不进入 reliable repair yield 分母的 success.

DiffSBDD full resampling baseline:

- 使用同一个 protein pocket.
- 不使用 oracle mask, 不写 `fix_atoms.sdf`.
- 使用 `generate_ligands.py` 和 `crossdocked_fullatom_cond.ckpt`.
- `ref_ligand` 默认使用 failed ligand SDF 定义 pocket.
- `num_nodes_lig` 可设为原 failed ligand heavy atom数, 保持候选规模可比.
- 每个样本输出最多 8 个候选.
- 它不是局部修复方法, 在报告中单独标为 `full_resampling_control`.
- scaffold RMSD, non-edit RMSD 和 old pair tracking 需要 MCS/scaffold adapter. 若无法映射原 scaffold, 记录 `scaffold_match_failed`; old clash resolved 可补充使用 old clash protein atom/residue hot region 是否仍有 severe clash, 但不可与 same-topology pair-resolved 指标混同.

**(3)** 历史版本演进

- v1: 只使用 frozen DiffSBDD 推理, 不做 guided denoising, 不做 training.

**(4)** 实验记录

| baseline | profile | impl | metric | result | note |
|---|---|---|---|---|---|
| DiffSBDD cond | phase2.5 setup | official generate_ligands smoke | status=ok in prior setup report | pass | 证明 de novo generation 环境曾可用, 不等于阶段 4.0 inpainting 已通过 |
| DiffSBDD inpaint | plan only | input adapter | cond ckpt present, joint ckpt missing | pending | 需下一步 inpaint smoke |

**(5)** 风险与兼容性

- `fix_atoms.sdf` 固定的是坐标和类型, 但最终 RDKit bond inference 可能改变拓扑或原子顺序.
- DiffSBDD 不保证生成取代基一定接回 anchor, 需要 verifier adapter 严格判定.
- joint checkpoint 直接跑 `inpaint.py` 的兼容性存疑.
- full resampling 的指标不可伪装成局部修复指标.

**(6)** 未决问题与下一步

- 是否允许下载 `crossdocked_fullatom_joint.ckpt`.
- 是否同时下载 Binding MOAD / CA checkpoint 作为资源允许项. 默认不下载, 除非用户确认.

### 3.5 专题 D: DiffDec 单取代基重采样

**(1)** 当前状态与采纳版本

v1 draft. DiffDec 是第一轮必须调研并尝试预检的后端, 但不阻塞规则型和 DiffSBDD 主线. 当前源码已在 `external/DiffDec`, 但环境和 checkpoint 未就绪.

**(2)** 当前设计

本地状态:

- source repo: `https://github.com/BankBro/DiffDec.git`.
- local path: `external/DiffDec/`.
- commit: `916ae14207b2783a90336bb8509374535c5791f9`.
- key script: `sample_single_for_specific_context.py`.
- checkpoint URL 来源: README 指向 Zenodo record `10527451`, 但本地未下载.
- conda env: 未发现.

oracle mask 转 DiffDec 输入:

- 从 failed ligand 中删除 `oracle_mask_atom_indices`.
- 保留 scaffold + 非目标 R-group, 写为 `fixed_context.sdf` 或 DiffDec 所需 `scaffold_file`.
- 在 `oracle_anchor_scaffold_atom_idx` 处添加 `*` dummy exit, 生成带单出口的 scaffold smiles.
- `sample_single_for_specific_context.py` 的 `update_scaffold()` 明确在发现多个 `*` 时抛出异常, 因此官方 single 脚本只支持单出口.
- S2 是 supported single R-group, 目标 R-group 单 anchor, 理论上符合 single 脚本入口. 但保留上下文可能包含多个非目标取代基, 需要实测 RDKit substructure match 是否稳定.
- `protein_file`: 使用同 case 的 protein pocket PDB.
- `scaffold_file`: 使用带 3D conformer 的 fixed context SDF.
- `scaffold_smiles_file`: 写一行带 `*` 的 scaffold smiles.

取代基大小控制:

- 源码预读显示官方 specific-context single 脚本将 dummy R-group 写成 `Chem.MolFromSmiles('C')`, 数据集解析时 `parse_rgroup()` 会补齐到 10 个 R-group slots, `model_single.sample_chain()` 默认取 `data['rgroup_mask'].sum()` 作为生成大小.
- 官方 CLI 未暴露 `rgroup_size` 参数.
- 因此当前不能声称能精确控制生成取代基大小. 预检必须记录实际 generated R-group heavy atom count.
- 如果官方示例跑通但大小不可控, 可在本项目 wrapper 中用 `sample_fn(data)` 传入 oracle target heavy atom count 做补充试验. 这属于 wrapper 级适配, 不修改 DiffDec 原始去噪过程.

输出检查:

- 官方脚本通过 `obabel` 将 xyz 转 SDF, 需要确认 RDKit 可读率.
- 检查 generated R-group 是否接回 anchor, 是否只有一个 attachment, 是否保留 fixed context.
- 若输出 molecule atom order 变化, 用 fixed context 子结构匹配和 anchor mapping 进入 verifier adapter.

**(3)** 历史版本演进

- v1: 先跑官方 single specific-context 示例, 再跑本项目 3-5 case preflight.

**(4)** 实验记录

| baseline | profile | impl | metric | result | note |
|---|---|---|---|---|---|
| DiffDec source | local clone | read-only/source preflight | source exists, no checkpoint/env | pending | 未执行官方示例 |

**(5)** 风险与兼容性

- DiffDec 环境可能与现有 `c2f_cpu` / `diffsbdd` 冲突, 建议单独 conda env.
- checkpoint 较大, 下载前需要用户确认.
- 官方 single 脚本不保证目标取代基大小可控.
- 输出 SDF 由 Open Babel 推断 bond, 可能出现 valence, anchor 或 connectivity 问题.

**(6)** 未决问题与下一步

- 用户确认后再创建/验证 DiffDec conda env, 下载 `diffdec_single.ckpt`, 跑官方 example.
- 若官方 example blocked, 写入 `reports/phase4_0_backend_feasibility/blocked_backends.md`, 并继续推进规则型和 DiffSBDD.

### 3.6 专题 E: 统一 verifier adapter 与失败分类

**(1)** 当前状态与采纳版本

v1 draft. 现有 `verify_repair()` 支持 same-topology, same-atom-order 候选. DiffSBDD 和 DiffDec 可能改变 atom order 或 topology, 因此需要 phase4 verifier adapter, 但不改变阶段 1 verifier 的历史结果.

**(2)** 当前设计

same-topology 候选:

- 规则型后端直接保留 atom count/order.
- 直接调用 `verify_repair()`.
- `edit_region` 使用 `oracle_mask_rgroup`, 例如 `R1`.

atom order 或 topology 变化候选:

- 读取候选 SDF 为 RDKit Mol.
- 用 fixed context 或 scaffold substructure 做 `candidate_to_base_atom_idx` mapping.
- 对 mapped keep atoms 计算 keep RMSD, scaffold RMSD, anchor atom displacement.
- 对 unmapped candidate atoms 视为 edit/new region.
- 若 fixed substructure 无法唯一或高置信匹配, 标记 `fixed_structure_match_failed`.
- 若 mapping 成功, 构造 adapter-level verifier row. old clash resolved 对局部修复优先按 mapped old ligand atom pairs 判断; 若 edit atoms无法对应原 old ligand atom, 使用 old clash protein atom/residue hot region 的 severe clash 清除作为补充字段, 并在报告中分开命名.

anchor integrity 定义:

- anchor scaffold atom 可映射到 candidate.
- anchor scaffold atom 坐标相对 failed pose 位移不超过 keep 阈值.
- candidate 中存在且仅存在一个从 mapped anchor scaffold atom 到 generated edit region 的 attachment.
- attachment bond length 在元素组合合理范围内, 第一版可用 0.9-1.9 Å 的保守 gate, 后续替换为共价半径阈值.
- 不存在 generated edit region 到其他 keep atom 的额外 attachment.

keep compliance 定义:

- `oracle_keep_atom_indices` 对应 heavy atoms 可映射.
- scaffold RMSD < 0.5 Å.
- keep/non-edit RMSD < 0.8 Å.
- keep atom 中位移 > 0.1 Å 的比例 <= 20%.
- fixed context 拓扑在 mapped keep subgraph 内不发生断裂或新增内部键.

统一指标:

- 接入能力: `backend_available`, `model_load_success`, `input_adapter_success`, `candidate_generation_success`, `candidate_readable_rate`, `backend_failure_rate`, `timeout_count`.
- 修复能力: `old_clash_resolved`, `no_new_severe_clash`, `reliable_repair_yield`, `ligand_validity`, `scaffold_rmsd`, `keep_region_rmsd`, `anchor_integrity`, `edit_compliance`, `keep_compliance`, `candidate_generation_success_rate`, `cost_per_success`.
- 可选辅助: docking/Vina 只写 supplementary, 不进入主成功定义.

失败分类:

- setup: `backend_source_missing`, `env_missing`, `checkpoint_missing`, `gpu_unavailable`.
- model: `model_load_failed`, `checkpoint_incompatible`, `cuda_oom`.
- input: `sample_input_missing`, `sdf_read_failed`, `mask_anchor_invalid`, `adapter_input_failed`.
- generation: `official_script_failed`, `generation_timeout`, `no_candidate_generated`.
- output: `candidate_unreadable`, `candidate_invalid`, `fixed_structure_match_failed`, `anchor_integrity_failed`, `keep_compliance_failed`.
- verifier: `old_clash_not_resolved`, `new_severe_clash`, `scaffold_drift`, `non_edit_drift`, `edit_noncompliance`, `pocket_not_retained`.
- reporting: 每个 blocked backend 必须写 blocked reason, first failing command, local path, expected remediation.

**(3)** 历史版本演进

- v1: 保持阶段 1 `verify_repair()` 为原始 same-order verifier, 为阶段 4 增加 adapter 层, 不回改阶段 1 结果.

**(4)** 实验记录

| baseline | profile | impl | metric | result | note |
|---|---|---|---|---|---|
| verifier contract | phase1 existing | `verify_repair()` | same-order contract known | pass | 需要新增 adapter 支持 variable topology |

**(5)** 风险与兼容性

- variable-topology 后端无法完整复用 old pair tracking, 需要在表中区分 exact pair resolved 和 hot-region resolved.
- MCS 多解会导致 keep RMSD 不稳定, 需要记录 mapping confidence.
- full resampling 不是局部修复, 不应参与局部 repair yield 的同口径成功率, 只能作为 control.

**(6)** 未决问题与下一步

- 预检阶段先实现最小 adapter, 只要求报告 mapping 成功率和失败原因.
- 40 case 前再决定是否把 variable-topology adapter 纳入正式 `reliable_repair_yield` 主分母.

## 4. 集成验证与落地

### 4.1 集成验证与回归

建议先执行的本地命令清单, 只作为计划, 不代表本轮已全部执行:

```bash
git status
git branch --show-current
git rev-parse HEAD
git show --quiet --format='%H %ci %s' main
ls reports/phase3_label_provenance_audit/
python - <<'PY'
import csv
from pathlib import Path
p = Path("reports/phase3_label_provenance_audit/phase4_mask_seed.csv")
rows = list(csv.DictReader(p.open(encoding="utf-8")))
print(len(rows), rows[0].keys())
PY
python -m compileall src scripts
python -m pytest tests/test_phase3_*.py
test -n "$(find tests -maxdepth 1 -name 'test_phase4_*.py' -print -quit)" && python -m pytest tests/test_phase4_*.py || true
git -C external/DiffSBDD remote -v
git -C external/DiffSBDD rev-parse HEAD
find external/DiffSBDD/checkpoints -maxdepth 1 -type f -printf '%f %s\n'
conda run -n diffsbdd python -c "import torch, rdkit, pytorch_lightning; print(torch.cuda.is_available())"
git -C external/DiffDec remote -v
git -C external/DiffDec rev-parse HEAD
find external/DiffDec -maxdepth 2 -type f -name '*.ckpt' -printf '%p %s\n'
conda env list
```

DiffSBDD conditional inpaint smoke test计划:

```bash
conda run --no-capture-output -n diffsbdd python external/DiffSBDD/inpaint.py \
  external/DiffSBDD/checkpoints/crossdocked_fullatom_cond.ckpt \
  --pdbfile <case_protein.pdb> \
  --outfile runs/phase4_0_backend_feasibility/diffsbdd_inpainting/<case_id>/cond_inpaint.sdf \
  --ref_ligand <failed_ligand.sdf> \
  --fix_atoms <fix_atoms.sdf> \
  --center pocket \
  --add_n_nodes <oracle_mask_heavy_atom_count> \
  --n_samples 8
```

DiffDec official example smoke test计划:

```bash
conda env create -f external/DiffDec/environment.yaml -n diffdec
mkdir -p external/DiffDec/ckpt
# 下载 checkpoint 到 external/DiffDec/ckpt/, 下载前需用户确认.
conda run --no-capture-output -n diffdec python external/DiffDec/sample_single_for_specific_context.py \
  --scaffold_smiles_file external/DiffDec/data/examples/scaf.smi \
  --protein_file external/DiffDec/data/examples/protein.pdb \
  --scaffold_file external/DiffDec/data/examples/scaf.sdf \
  --task_name exp \
  --data_dir external/DiffDec/data/examples \
  --checkpoint external/DiffDec/ckpt/diffdec_single.ckpt \
  --samples_dir runs/phase4_0_backend_feasibility/diffdec/official_example \
  --n_samples 1 \
  --device cuda:0
```

阶段 4.0 必答问题逐条状态:

| id | 问题 | 当前回答 |
|---:|---|---|
| 1 | 当前分支, commit, main 是否包含阶段 3 产物 | 当前分支 `20260514-043614-phase4-0`, commit `ccba02bf6e17c46e89dfec3dd1e1f5e64e4c0842`, 本地 `main` 同 commit 且包含阶段 3 产物 |
| 2 | `phase4_mask_seed.csv` 是否可用 | 可用, 数据行 357, 必要 oracle/anchor/old clash 字段齐全且非空 |
| 3 | 40 个正式样本如何分层抽取 | 固定 seed `20260514`, 按 injection mode, difficulty, base_split, mask size, random mask size diff, clash depth, severe pair 数分层, 输出 `selected_cases.csv` |
| 4 | 3-5 个预检样本如何抽取 | 优先 val/test, 中等 mask size, 不极端 clash depth, 少 severe pair, 覆盖三种 injection mode, 候选见专题 A |
| 5 | 规则型局部构象修复如何实现 | 固定 keep region, 围绕 anchor bond 做 rigid rotation, 对 target R-group 内部 rotatable bonds 做 torsion search, 最多保留 8 个候选 |
| 6 | DiffSBDD 局部补全如何构造输入 | 删除 oracle mask, keep atoms 写 `fix_atoms.sdf`, failed ligand 作为 `ref_ligand`, protein PDB 作为 pocket, `add_n_nodes` 用 target heavy atom count |
| 7 | DiffSBDD 条件和联合模型是否都能用于 inpaint | 条件模型有 checkpoint, 预期可优先测; 联合 checkpoint 缺失且原版 `inpaint.py` 代码签名可能不兼容, 必须下载后实测 |
| 8 | DiffSBDD 全配体重新采样如何作为对照 | 用同一 protein pocket 和 failed ligand 定义 pocket, `generate_ligands.py`, 不使用 oracle mask, 每样本 8 个, 标为 full resampling control |
| 9 | DiffDec 环境和 checkpoint 状态 | 源码已克隆到 fork commit, conda env 未发现, checkpoint 未发现 |
| 10 | DiffDec 官方示例是否能跑 | 本轮计划优先未跑; 需环境和 checkpoint 后执行官方 example, 失败则写 blocked |
| 11 | DiffDec 单取代基输入如何由 oracle mask 构造 | 删除 target R-group, fixed context 写 SDF, anchor scaffold atom 加 `*` 出口, 写 scaffold smiles 和 protein file |
| 12 | DiffDec 是否能控制生成取代基大小 | 官方 specific-context CLI 未暴露 size 参数, 当前不能声称可精确控制, 必须记录实际 heavy atom count |
| 13 | 多后端输出如何统一进入 verifier | same-order 直接 `verify_repair`, variable topology 先过 mapping adapter 再计算统一指标 |
| 14 | 输出原子顺序变化时如何做固定结构匹配 | fixed context/scaffold MCS + element/coordinate consistency, 生成 `candidate_to_base_atom_idx` mapping |
| 15 | anchor integrity 如何定义 | scaffold anchor 可映射, 坐标稳定, 且只有一个合理 attachment 到 edit region, 无额外 attachment |
| 16 | keep compliance 如何定义 | keep atoms 可映射, scaffold RMSD < 0.5 Å, keep RMSD < 0.8 Å, outside displacement fraction <= 20%, keep topology 不破坏 |
| 17 | 各后端失败如何分类 | setup, model, input, generation, output, verifier, reporting 七类, 细分见专题 E |
| 18 | 哪些后端第一轮必须完成 | rule local repair, DiffSBDD local inpainting cond, DiffSBDD local inpainting joint, DiffDec single substituent, DiffSBDD cond full resampling control |
| 19 | 哪些是资源允许项 | DiffSBDD Binding MOAD full atom, DiffDec multi substituent, DiffSBDD CA coarse reference |
| 20 | 哪些情况需要写 blocked_backends.md | 环境缺失, checkpoint 缺失, model load 失败, 官方脚本失败, adapter 不可构造, 输出不可读, timeout/OOM 且无法在预检预算内恢复 |
| 21 | 预检通过后如何推进 40 样本实验 | 冻结 selected_cases.csv 和 backend-model matrix, 每 cell 每样本 8 candidate, 统一 verifier outcome 和 summary, 不进入 4.1 Random/Predicted/Oracle 正式对照 |

### 4.2 发布与回退

第一轮 backend matrix 计数口径:

- backend family 口径: 4 类. `rule_local`, `DiffSBDD_inpainting`, `DiffDec_single`, `DiffSBDD_full_resampling_control`.
- backend-model cell 口径: 5 个. `rule_local`, `diffsbdd_inpaint_crossdocked_fullatom_cond`, `diffsbdd_inpaint_crossdocked_fullatom_joint`, `diffdec_single`, `diffsbdd_full_resampling_crossdocked_fullatom_cond`.
- 报告和 CSV 建议以 backend-model cell 为行, 同时保留 `backend_family` 字段, 避免 "必测后端 4 个" 与 "实际矩阵 5 行" 冲突.

可立即做 3-5 样本 preflight 的条件:

- 可以立即做: 规则型后端 input adapter dry-run 和小规模候选生成.
- 可以优先做: DiffSBDD conditional inpainting input adapter 和 smoke generation, 因为 env/checkpoint 已有历史可用证据.
- 需要先准备: DiffSBDD joint checkpoint 下载.
- 当前阻塞: DiffDec env/checkpoint/official example.
- 不需要先合入阶段 3 到 main: 本地 `main` 已包含阶段 3 产物.
- 需要用户确认: 下载新增 checkpoint, 创建 DiffDec env, 执行真实 candidate generation preflight, 以及是否要求正式 40 case val/test-only.

回退策略:

- 如果 DiffDec blocked, 记录 blocked 原因, 继续 rule + DiffSBDD conditional + full resampling 主线.
- 如果 DiffSBDD joint 直接 `inpaint.py` blocked, 记录 direct-script blocked, 再决定是否允许本项目 wrapper 调用 joint inpaint 接口.
- 如果 variable-topology adapter 映射失败率高, 阶段 4.0 先报告接入失败率, 不把失败候选硬算为 reliable repair.

## 5. 参考

### 5.1 参考资料

- `docs/20260504-03-Clash2Feedback-GC_总体实验递进路线.md`.
- `docs/20260504-02-Clash2Feedback-GC_第一篇论文实验方案.md`.
- `docs/20260513-Clash2Feedback-GC_阶段3标签溯源循环风险审计与阶段4掩码种子生成方案总纲.md`.
- `docs/external_baselines.md`.
- `external/DiffSBDD/README.md`.
- `external/DiffSBDD/inpaint.py`.
- `external/DiffSBDD/generate_ligands.py`.
- `external/DiffDec/README.md`.
- `external/DiffDec/sample_single_for_specific_context.py`.
- `src/clash2feedback/verifier/repair_verifier.py`.
- `configs/phase1_clash_detector.yaml`.

### 5.2 相关文档与实验附件

- 本计划文档: `tmp/20260514/phase4_0_multi_backend_feasibility_plan.md`.
- 后续 preflight 报告目录: `reports/phase4_0_backend_feasibility/`.
- 后续 preflight 运行目录: `runs/phase4_0_backend_feasibility/`.
- 阻塞记录: `reports/phase4_0_backend_feasibility/blocked_backends.md`.
