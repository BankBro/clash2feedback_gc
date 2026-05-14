# 阶段 4.0 backend feasibility 实验报告

> status: completed
> task: phase4-0-backend-feasibility
> date: 2026-05-14
> branch: `20260514-043614-phase4-0`
> scope: 参考掩码下的多后端局部修复可行性审计

## 1. 实验目的

本次阶段 4.0 实验不是 Random / Predicted / Oracle mask policy 的正式对照, 而是先回答一个更基础的问题:

- 在阶段 3 冻结的 `phase4_mask_seed.csv` 参考掩码下, 哪些 repair backend 能稳定接入输入适配, 生成候选, 并通过统一 verifier adapter.
- 生成式后端的 candidate 是否能满足局部修复所需的 fixed scaffold match, anchor integrity, old clash resolved 和 no new severe clash.
- 哪些后端应进入后续阶段 4.1, 哪些后端需要先修输入适配或环境问题.

硬约束:

- 不训练模型.
- 不微调模型.
- 不修改 DiffSBDD / DiffDec 原始源码或去噪过程.
- 不把 `H_clash` 输入 DiffSBDD / DiffDec 生成过程.
- 不修改阶段 2 / 2.5 / 3 历史结果.
- 不覆盖 `reports/phase3_label_provenance_audit/phase4_mask_seed.csv`.

## 2. 实验输入和 case 选择

主输入:

```text
reports/phase3_label_provenance_audit/phase4_mask_seed.csv
```

正式实验选择 40 个 S2 case, seed 固定为 `20260514`, tie-breaker 使用 `sha256(f"{seed}:{case_id}")`, 并限制 `base_sample_id` 软上限为 3.

实际分层结果:

| field | counts |
|---|---|
| `injection_mode` | `directed_clash=14`, `easy_rotation=13`, `torsion_perturb=13` |
| `difficulty_bin` | `easy=27`, `medium=13` |
| `base_split` | `train=29`, `test=9`, `val=2` |
| max cases per `base_sample_id` | 3 |

输出:

```text
reports/phase4_0_backend_feasibility/selected_cases.csv
```

## 3. 本次纳入的后端

### 3.1 可执行后端

- `rule_fixed_topology`: 固定拓扑局部构象搜索, 每 case 最多输出 K=8.
- `diffsbdd_conditional_inpainting`: DiffSBDD CrossDocked full-atom conditional local completion, 分别尝试 `center=ligand` 和 `center=pocket`.
- `diffsbdd_full_resampling`: DiffSBDD CrossDocked full-atom conditional full-ligand resampling, 作为全配体重采样对照.
- `diffdec_single_rgroup`: DiffDec single substituent scaffold decoration, 使用 `DiffDec` conda 环境和 `diffdec_single.ckpt`, 运行参数包含 `--device cuda:0`.

### 3.2 blocked 后端

- `diffsbdd_joint_inpainting`: `crossdocked_fullatom_joint.ckpt` 已下载并进入 inventory, 但官方 `inpaint.py` 入口与 joint checkpoint 不兼容, 阻塞原因为 `official_inpaint_entrypoint_incompatible_with_joint_checkpoint:center_argument`.

## 4. reliable repair candidate 定义

`reliable repair candidate` 是单个候选分子层面的成功标记. 候选不是生成出来就算成功, 必须同时满足:

- SDF 可被 RDKit 读取.
- fixed scaffold / keep region 能在候选中匹配.
- anchor integrity 通过, 即新片段正确接回原 anchor, 没有断开或乱接.
- old severe clash 被解决.
- 没有引入新的 severe protein-ligand clash.

`sample_reliable_success_count` 是 case 层面的成功数, 即某个 case 至少有一个 reliable repair candidate.

## 5. 核心结果

正式 40 case backend comparison:

| backend | attempts | candidates | failed attempts | reliable candidates | reliable cases |
|---|---:|---:|---:|---:|---:|
| `rule_fixed_topology` | 40 | 320 | 0 | 227 | 38 |
| `diffsbdd_conditional_inpainting` | 80 | 624 | 2 | 17 | 9 |
| `diffsbdd_full_resampling` | 40 | 320 | 0 | 0 | 0 |
| `diffdec_single_rgroup` | 40 | 312 | 1 | 0 | 0 |
| `diffsbdd_joint_inpainting` | 40 | 0 | 40 | 0 | 0 |

对应文件:

```text
reports/phase4_0_backend_feasibility/backend_comparison.csv
reports/phase4_0_backend_feasibility/phase4_0_small_scale_summary.json
reports/phase4_0_backend_feasibility/phase4_0_completion_audit.md
```

## 6. 结果解释

### 6.1 rule backend

规则型固定拓扑局部构象搜索是当前最稳的阶段 4.0 后端.

- 40/40 case 均可执行.
- 320 个候选中 227 个达到 reliable repair candidate.
- 40 个 case 中 38 个至少有一个 reliable candidate.

解释:

- 该后端保留原拓扑和原 atom order, 与阶段 1 verifier 的 same-topology 假设最匹配.
- 它不生成新片段, 主要通过局部构象搜索解除旧碰撞, 所以 fixed scaffold 和 anchor integrity 天然更稳定.

### 6.2 DiffSBDD conditional inpainting

DiffSBDD 条件局部补全可以跑通, 且有非零可靠修复结果, 但成功率明显低于 rule backend.

- 80 次 attempt 来自 40 case × 2 个 center.
- 2 次 execution failure, 都发生在 `case_002599` 的 ligand/pocket center.
- 624 个候选中 17 个达到 reliable repair candidate.
- 9/40 case 至少有一个 reliable candidate.

解释:

- 生成式 inpainting 能产生可读候选并匹配 fixed scaffold, 但 anchor integrity 成功数较低.
- 这说明当前 wrapper 可以作为 feasibility backend, 但若要进入更强的后续实验, 需要提升 anchor-aware 接回能力或后处理筛选.

### 6.3 DiffSBDD full resampling

全配体重采样可以稳定生成, 但在局部可靠修复口径下不成功.

- 40/40 case 执行成功.
- 320 个候选全部可生成.
- reliable candidate 为 0.

解释:

- 该后端不固定 keep region, 也不保证原 scaffold/anchor 保留.
- 它适合作为全局生成对照, 不能按当前标准声明为局部修复成功.

### 6.4 DiffDec single R-group

DiffDec 单取代基后端已经完成专用环境, checkpoint 和 GPU formal run, 但当前适配口径下没有 reliable repair success.

- 40 次 attempt, 1 次 execution failure.
- 312 个候选进入 verifier.
- reliable candidate 为 0.
- 失败 case 为 `case_002599`, 原因是 protein 中存在 `CL`, DiffDec 官方 atom vocabulary 不支持, 抛出 `KeyError: 'CL'`.

解释:

- DiffDec 可以用 `cuda:0` 跑正式样本, 环境/checkpoint 不再是阻塞项.
- 当前主要问题是输入适配和 anchor / scaffold 可靠性, 以及部分 protein atom vocabulary 兼容性.

### 6.5 DiffSBDD joint

joint checkpoint 已下载, 但不应误报为可执行成功.

- `model_inventory.csv` 已记录 checkpoint 存在和 checksum.
- 官方 `inpaint.py` 入口与 joint checkpoint 不兼容, 全部 40 case 作为 blocked denominator rows 记录.

## 7. 实验结论

阶段 4.0 的结论:

1. 当前可以进入阶段 4.1 候选的后端优先是 `rule_fixed_topology`.
2. `diffsbdd_conditional_inpainting` 有非零可靠修复结果, 值得作为生成式局部修复候选继续改进 adapter 和筛选.
3. `diffsbdd_full_resampling` 可以作为全配体生成对照, 但不应作为局部修复主后端.
4. `diffdec_single_rgroup` 环境和 checkpoint 已跑通, 但当前 0 reliable success, 需要先处理 anchor/scaffold 适配和 atom vocabulary 兼容性.
5. `diffsbdd_joint_inpainting` 当前是接口不兼容 blocked, 不阻塞阶段 4.1 讨论.

## 8. 建议提交给远端 GitHub 的文件

为了让网页版 ChatGPT 能分析本次实验, 建议提交:

- 阶段 4.0 代码和配置:
  - `configs/phase4_0_backend_feasibility.yaml`
  - `scripts/phase4_0_backend_feasibility.py`
  - `src/clash2feedback/repair/`
  - `src/clash2feedback/verifier/phase4_adapter.py`
  - `tests/test_phase4_backend_feasibility.py`
- 阶段 4.0 报告:
  - `reports/phase4_0_backend_feasibility/*.csv`
  - `reports/phase4_0_backend_feasibility/*.json`
  - `reports/phase4_0_backend_feasibility/*.md`
- 复盘和方案上下文:
  - `tmp/20260514/phase4-0-backend-feasibility-expt-report.md`
  - `docs/20260514-Clash2Feedback-GC_阶段4.0多后端参考掩码修复可行性审计方案总纲.md`
  - `docs/external_baselines.md`
  - 相关 `README.md`

不建议提交:

- `runs/phase4_0_backend_feasibility/`: 运行候选 SDF 和日志较重, 对远端分析不是必需.
- `external/DiffSBDD/` 和 `external/DiffDec/`: 外部源码和 checkpoint 默认不提交, provenance 已写入文档和 `model_inventory.csv`.
- checkpoint 文件: 体积大, 且已有 URL/hash/provenance.

## 9. 验证记录

已执行:

```bash
conda run -n c2f_cpu python -m compileall src scripts
conda run -n c2f_cpu python -m pytest tests/test_phase4_backend_feasibility.py -q
conda run -n c2f_cpu python -m pytest -q
```

结果:

- `tests/test_phase4_backend_feasibility.py`: 8 passed.
- 全量测试: 128 passed.
- `phase4_mask_seed.csv` SHA256 未变:

```text
18cea12cc4f92a8f21f6f9de83c2ba551556e35a19e9d781d3a98f79b99097cc
```
