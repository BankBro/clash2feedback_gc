# 发给 Codex 的阶段 2 实施 Prompt

你现在在本地服务器项目目录 `clash2feedback_gc/` 中工作。请严格基于以下两个文档实施阶段 2：

1. `docs/20260510-Clash2Feedback-GC_阶段2人工局部碰撞注入最终落地方案.md`
2. `tmp/20260510/20260510-Clash2Feedback-GC_docs文档调整建议.md`

你的任务是结合当前仓库实际情况，完成阶段 2 controlled synthetic failed pose benchmark 的代码落地、测试、报告生成和实验验证，并更新必要 docs。

---

## 一、最高优先级目标

实现阶段 2：

> 从 phase0/phase1 clean base pose 出发，选择合法 single-anchor target R-group，通过 easy rotation / torsion perturb / directed clash 构造 protein-ligand severe clash；用 RDKit 和几何规则过滤 ligand 自身不合理构象；用阶段 1 detector / attribution 标注 target、non-target、scaffold clash；严格防止数据泄漏、标签泄漏、atom index 错位和重复样本灌水；最终产出 supported / reject / invalid / unsupported 分层 benchmark。

阶段 2 不训练模型、不调用生成器、不做 repair、不做 whole protein-ligand complex minimization。

---

## 二、必须先启动最高等级子 agent / 自检流程

请立即启动一个最高等级的新子 agent 或等价自检流程，命名为：

```text
phase2_completion_auditor
```

该子 agent / 自检流程必须做以下循环：

```text
1. 逐条读取 docs/20260510-Clash2Feedback-GC_阶段2人工局部碰撞注入最终落地方案.md；
2. 把文档中的每一个代码、配置、测试、报告、数据、docs 要求拆成 checklist；
3. 检查当前仓库实际状态；
4. 标记每一项为 done / partial / missing / blocked；
5. 对 partial / missing 项制定修复计划并执行；
6. 执行后再次检查；
7. 不断重复，直到所有非 blocked 项全部 done；
8. 如果 blocked，必须写明阻塞原因、所需数据/依赖/权限，以及临时替代方案。
```

最终必须生成：

```text
reports/phase2_injection/phase2_completion_audit.md
```

该文件必须包含：

```text
- 全量 checklist 状态；
- 已完成项；
- 尚未完成项；
- blocked 项及原因；
- 修改了哪些代码文件；
- 新增了哪些测试；
- 生成了哪些 reports；
- 实际运行命令；
- compileall / pytest 结果；
- phase2 summary.json 摘要；
- visual QC 抽查状态。
```

---

## 三、代码落地要求

优先复用当前阶段 1 detector / attribution / verifier，不要重复造阶段 1 逻辑。

建议新增或补齐：

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

如果仓库已有同名或相关文件，请优先扩展已有实现。

---

## 四、必须实现的关键 gate

### 1. Base clean pose gate

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

### 2. Ligand-only validity gate

```text
RDKit sanitize pass
rotatable anchor bond valid
not ring / double / aromatic / amide-like bond
anchor integrity pass
bond length sanity pass
ligand internal severe clash = 0
chirality preserved
optional MMFF / UFF energy_delta recorded
```

MMFF / UFF 只能作为 ligand-only filter，不能做 whole protein-ligand complex minimization。

### 3. Protein-ligand failure gate

```text
delta = 0.4 Å as primary
delta sensitivity = 0.3 / 0.4 / 0.5
target_num_severe_pairs >= 1
target_score_ratio_valid >= 0.7
scaffold_severe_pair_count = 0
non_target_severe_pair_count = 0
max_clash_depth <= 1.5 Å by default
```

---

## 五、必须实现的 split

```text
supported_single_rgroup
ambiguous_region
multi_region
scaffold_clash
global_pose_failure
near_miss_contact
invalid_conformer
unsupported
duplicate_removed
```

要求：

```text
supported_single_rgroup 才进入阶段 3 Top-1 / Top-3 主评估；
ambiguous / multi / scaffold / global 进入 reject split；
invalid_conformer 必须报告，不能静默丢弃；
unsupported 必须报告，不能静默丢弃；
duplicate_removed 必须报告，不能灌水进入主集。
```

---

## 六、必须防止泄漏

严格执行：

```text
1. 不得使用 predicted_dominant_rgroup == target_rgroup 作为唯一保留条件；
2. target_rgroup 是人工扰动真值；
3. predicted_dominant_rgroup 只记录，不用于主过滤；
4. 所有 injected variants 必须继承 base complex split；
5. 同一 base complex 不得跨 train / val / test；
6. heavy atom index mapping 必须保持稳定；
7. AddHs 只能用于 energy check，不得污染主 heavy atom index。
```

---

## 七、必须生成的数据和报告

Benchmark：

```text
data/benchmarks/clashrepairbench_rg_artificial/v0_1/
  manifest.parquet
  schema.json
  samples/*.pkl
  ligands/*_original.sdf
  ligands/*_failed.sdf
```

Reports：

```text
reports/phase2_injection/
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
  phase2_completion_audit.md
```

---

## 八、必须更新 docs

根据：

```text
tmp/20260510/20260510-Clash2Feedback-GC_docs文档调整建议.md
```

检查并更新：

```text
docs/20260504-03-Clash2Feedback-GC_总体实验递进路线.md
docs/20260504-02-Clash2Feedback-GC_第一篇论文实验方案.md
docs/20260504-01-Clash2Feedback-GC_完整方案与升级路线.md
docs/20260508-Clash2Feedback-GC_阶段1碰撞检测器与可靠验证器方案.md
```

可选更新：

```text
docs/20260505-Clash2Feedback-GC_阶段0工程方案.md
```

最终生成：

```text
tmp/20260510/20260510-docs_update_summary.md
```

---

## 九、必须运行的验证命令

至少运行：

```bash
python -m compileall src scripts
pytest
```

然后运行阶段 2 脚本，例如：

```bash
python scripts/phase2_inject_artificial_clashes.py \
  --config configs/phase2_injection.yaml \
  --manifest data/processed/v0_1/manifest.parquet \
  --phase1-report-root reports/phase1_clash_detector \
  --output-root data/benchmarks/clashrepairbench_rg_artificial/v0_1 \
  --report-root reports/phase2_injection
```

如果数据路径或 CLI 与当前仓库不同，请根据实际情况适配，但必须在 audit 文件中写明实际命令。

---

## 十、完成标准

只有当以下条件满足，才能认为阶段 2 完成：

```text
[ ] configs/phase2_injection.yaml 存在；
[ ] phase2 脚本可运行；
[ ] 所有 phase2 单元测试通过；
[ ] compileall 通过；
[ ] pytest 通过；
[ ] manifest.parquet 可读取；
[ ] samples/*.pkl 可读取；
[ ] reports/phase2_injection/ 全部生成；
[ ] supported_single_rgroup cases > 0；
[ ] accepted samples 全部 ligand_valid = true；
[ ] accepted samples 全部 ligand_internal_severe_clash = 0；
[ ] supported 主集全部 target severe clash >= 1；
[ ] supported 主集全部 non-target severe = 0；
[ ] supported 主集全部 scaffold severe = 0；
[ ] 所有 injected samples 继承 base split；
[ ] predicted_dominant 没有作为样本保留条件；
[ ] invalid / reject / unsupported / duplicate 均有原因统计；
[ ] visual QC 抽查状态已记录；
[ ] phase2_completion_audit.md 完整记录最终状态。
```

完成后，请给出：

```text
1. 修改文件列表；
2. 新增文件列表；
3. 测试结果；
4. 阶段 2 summary 摘要；
5. 未完成或 blocked 项；
6. 下一步阶段 3 preflight 建议。
```
