# Phase 4.0.1 Closeout Audit

## 1. Audit Scope

本次 closeout audit 只检查阶段 4.0.1 的 anchor reconnect 诊断表完整性和 `local_reconnect_pass_count` 的可追溯性.

本次没有重跑完整 DiffSBDD 生成, 没有覆盖阶段 4.0 历史结果, 没有修改 `phase4_mask_seed.csv`, 没有放宽 reliable repair 10 项标准, 没有声称 `H_clash` 进入 DiffSBDD 生成过程.

## 2. Main Finding

`reports/phase4_0_1_diffsbdd_conditional_repair/diffsbdd_anchor_reconnect_audit.csv` 不是空文件.

本地当前 HEAD `b16726b223a17842f0dde25d3bbf8a84ea03c5aa` 中:

- 文件大小: 1,400,543 bytes.
- 行数: 2,188 行, 包含 1 行表头和 2,187 条记录.
- `diffsbdd_candidate_manifest.csv`: 2,188 行.
- `diffsbdd_verifier_outcome.csv`: 2,188 行.
- `diffsbdd_budget_curve.csv`: 4 行, 包含 1 行表头和 K=8/16/32 三行预算统计.

历史提交中该表也不是空文件:

| commit | blob size bytes | line count |
|---|---:|---:|
| `6b9d7a28ba720c6c2a8f5381370e56f1fe118ffd` | 1,400,543 | 2,188 |
| `65ccfa6e2ea5103f13a8417365c8e1bea51e13b8` | 1,400,543 | 2,188 |
| `b16726b223a17842f0dde25d3bbf8a84ea03c5aa` | 1,400,543 | 2,188 |

因此, “远端文件为空”与仓库 Git blob 和本地 checkout 的事实不一致. 更可能的解释是网页端 CSV 预览或读取方式误判, 而不是阶段 4.0.1 诊断表漏写.

## 3. Row-Level Traceability

候选, verifier 和 anchor reconnect audit 的记录数一致:

| file | rows including header | data rows |
|---|---:|---:|
| `diffsbdd_candidate_manifest.csv` | 2,188 | 2,187 |
| `diffsbdd_verifier_outcome.csv` | 2,188 | 2,187 |
| `diffsbdd_anchor_reconnect_audit.csv` | 2,188 | 2,187 |

按 K 预算分布:

| candidate_budget_k | audit rows | verifier rows | local_reconnect_pass rows | reliable candidates |
|---:|---:|---:|---:|---:|
| 8 | 313 | 313 | 0 | 10 |
| 16 | 625 | 625 | 0 | 14 |
| 32 | 1,249 | 1,249 | 0 | 24 |

每个预算多出的 1 行是 execution failure 记录:

| candidate_budget_k | case_id | failure_stage | failure_reason | candidate_count | proposal_count |
|---:|---|---|---|---:|---:|
| 8 | `case_002599` | `execution` | `returncode_1` | 0 | 8 |
| 16 | `case_002599` | `execution` | `returncode_1` | 0 | 16 |
| 32 | `case_002599` | `execution` | `returncode_1` | 0 | 32 |

`diffsbdd_budget_curve.csv` 的 `candidate_count_sum` 使用 attempt-level `candidate_count`, 因此分别是 312, 624, 1248. `local_reconnect_pass_count` 来自 `diffsbdd_verifier_outcome.csv` 中候选级 `local_reconnect_pass` 字段求和, 三档均为 0. 这与 `diffsbdd_anchor_reconnect_audit.csv` 中候选级 `local_reconnect_pass=False` 的记录一致.

## 4. Code Path Audit

`src/clash2feedback/repair/phase4_0_1.py` 的诊断链路如下:

- 第 72 行初始化 `diagnostics_rows`.
- 第 100 到 104 行将每个 case 的 `result["diagnostics_rows"]` 汇总进全局 `diagnostics_rows`.
- 第 224 到 243 行对每个 candidate 调用 `analyze_candidate_fragment()`, 再调用 `anchor_aware_filter_row()`, 并把 diagnostics 同步写入 verifier outcome 的诊断字段.
- 第 350 行将 `_frame(diagnostics_rows)` 写出为 `diffsbdd_anchor_reconnect_audit.csv`.
- 第 437 和 445 行在 budget curve 中从 verifier rows 汇总 `local_reconnect_pass_count` 和 `local_reconnect_pass_rate`.

因此, `local_reconnect_pass_count=0` 可追溯到候选级 diagnostics 和 verifier 字段, 不是凭空生成的聚合数字.

## 5. Report-Only Check

`report-only` 模式在 `src/clash2feedback/repair/phase4_0_1.py` 第 145 到 163 行读取已有:

- `diffsbdd_candidate_manifest.csv`
- `diffsbdd_verifier_outcome.csv`
- `diffsbdd_anchor_reconnect_audit.csv`

随后调用 `_write_formal_reports()` 重写汇总. 如果 `diffsbdd_anchor_reconnect_audit.csv` 是零字节空文件, `pd.read_csv()` 会直接失败, 不会静默生成完整 budget curve. 如果是仅有表头无记录, 则会产生空 diagnostics rows, 但当前 Git blob 和本地文件均不是该状态.

本次 closeout audit 没有发现 report-only 把原始诊断表覆盖为空的证据.

## 6. Runs Availability

本地 `runs/phase4_0_1_diffsbdd_conditional_repair/` 仍存在, 包含 2,596 个本地运行文件, 主要为候选 SDF 和日志. 这些文件已被 `runs/.gitignore` 忽略, 不提交 Git.

由于 `diffsbdd_anchor_reconnect_audit.csv` 已完整存在, 本次没有从 `runs/` 重建诊断表.

## 7. Interpretation Impact

阶段 4.0.1 的核心结果不需要因为该项检查而推翻:

- K=8: 7/40 reliable cases, 10 reliable candidates.
- K=16: 7/40 reliable cases, 14 reliable candidates.
- K=32: 10/40 reliable cases, 24 reliable candidates.

但最终报告应保持边界:

- `local_reconnect_pass=0` 是候选级诊断结果, 不替代 reliable repair 10 项标准.
- local reconnect 诊断更适合作为 anchor reconnect failure 分析和后续筛选依据, 不应反向推翻已经按阶段 4.0 10 项标准判定的 reliable candidates.
- 当前 per-candidate audit 表完整, 因此可以引用候选级 reconnect failure reason.

主要候选级 local reconnect failure reason:

| reason | count |
|---|---:|
| `not_connected_to_anchor` | 1,037 |
| `floating_fragment` | 519 |
| `extra_attachments=4` | 102 |
| `extra_attachments=5` | 99 |
| `extra_attachments=3` | 87 |
| `extra_attachments=6` | 72 |
| `extra_attachments=2` | 59 |
| `extra_attachments=7` | 49 |
| `extra_attachments=8` | 43 |
| `extra_attachments=1` | 40 |

## 8. Closeout Decision

本次 closeout audit 结论:

- `diffsbdd_anchor_reconnect_audit.csv` 不为空.
- `diffsbdd_candidate_manifest.csv` 和 `diffsbdd_verifier_outcome.csv` 不为空.
- `local_reconnect_pass_count=0` 可追溯到候选级 diagnostics/verifier 字段.
- 本地 runs 仍可用于必要时重建, 但当前无需重建.
- 无需修改 `diffsbdd_anchor_reconnect_audit.csv`.
- 可以继续进入阶段 4.0.1 final report 编写, 但 final report 应引用本 closeout audit 并明确 local reconnect 是新增诊断/筛选项, 不替代 reliable repair 标准.

