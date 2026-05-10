# Clash2Feedback-GC docs 文档调整建议：对齐阶段 2 最终落地方案

> 日期：2026-05-10  
> 建议仓库路径：`tmp/20260510/20260510-Clash2Feedback-GC_docs文档调整建议.md`  
> 目的：让 Codex 根据阶段 2 最终落地方案，检查并更新 `docs/` 目录下已有方案文档，避免旧表述与最终实施策略冲突。  
> 关联新增文档：`docs/20260510-Clash2Feedback-GC_阶段2人工局部碰撞注入最终落地方案.md`

---

## 0. 总体判断

`docs/` 目录下已有文档需要更新。

主要原因：旧文档对阶段 2 已经有“人工局部碰撞注入”的初步描述，但还没有完整纳入我们最新确定的细节：

```text
1. 阶段 2 不调用生成器、不做 repair、不做 whole complex minimization；
2. injected pose 是 controlled synthetic failed pose，不是真实稳定结合构象；
3. 只能围绕合法 rotatable single bond 或合法内部 torsion 扰动；
4. 必须加入 RDKit sanitize / rotatable bond / ligand internal clash / optional MMFF-UFF energy delta；
5. 必须区分 target_rgroup、predicted_dominant_rgroup 和 oracle_split；
6. 不能用 predicted_dominant == target 作为样本保留条件；
7. 必须加入 supported / reject / invalid_conformer / unsupported / duplicate_removed 等 split；
8. 必须加入 anti-leakage、去重、difficulty bins、visual QC 和 manifest/report schema；
9. 阶段 3 的 Top-1 / Top-3 应只基于 supported_single_rgroup 主集，reject/unsupported 单独统计。
```

---

## 1. 建议新增 docs 文档

新增：

```text
docs/20260510-Clash2Feedback-GC_阶段2人工局部碰撞注入最终落地方案.md
```

作用：作为阶段 2 的唯一最终实施文档，供 Codex 和后续人工实验使用。

该文档应覆盖：

```text
阶段 2 目标和边界；
target / non-target R-group / anchor 定义；
base clean pose 过滤；
injection modes；
ligand-only 合理性检查；
protein-ligand failure 接受条件；
split 设计；
anti-leakage；
deduplication；
difficulty bins；
manifest schema；
reports schema；
代码文件清单；
config 示例；
unit tests；
运行命令；
验收标准；
Codex 自检循环要求。
```

---

## 2. 需要更新的 docs 文件总表

| 文件 | 是否需要更新 | 优先级 | 主要原因 |
|---|---:|---:|---|
| `docs/20260504-03-Clash2Feedback-GC_总体实验递进路线.md` | 是 | P0 | 阶段 2 / 3 描述需要对齐最终 split、验收和指标。 |
| `docs/20260504-02-Clash2Feedback-GC_第一篇论文实验方案.md` | 是 | P0 | 人工注入、保留条件、BIBM 小闭环和实验边界需要更新。 |
| `docs/20260504-01-Clash2Feedback-GC_完整方案与升级路线.md` | 是 | P1 | 数据集设计、人工失败集、完整路线中的阶段 2 语义需要同步。 |
| `docs/20260508-Clash2Feedback-GC_阶段1碰撞检测器与可靠验证器方案.md` | 是 | P1 | 阶段 1 与阶段 2 接口、full receptor 边界、人工注入表述需要更新。 |
| `docs/20260505-Clash2Feedback-GC_阶段0工程方案.md` | 可选 | P2 | 可补充 orig_atom_idx、rotatable bond、split inheritance 对阶段 2 的重要性。 |

---

## 3. 更新 `docs/20260504-03-Clash2Feedback-GC_总体实验递进路线.md`

### 3.1 更新阶段 2 名称和目标

当前阶段 2 的核心仍是对的：人工局部碰撞注入，不训练模型、不调用生成器，产出 `ClashRepairBench-RG-artificial`。

建议将阶段 2 小节替换或扩展为：

```markdown
## 5. 阶段 2：人工局部碰撞注入

### 5.1 目标

阶段 2 构建带真实 target R-group 标签的 controlled synthetic failed pose benchmark。它从阶段 1 验收过的 clean protein-ligand pose 出发，只扰动一个合法 target R-group，构造 ligand 自身合理、但 target R-group 与 protein 发生 severe clash 的失败样本。

阶段 2 不训练模型、不调用生成器、不做 repair、不做 whole protein-ligand complex minimization。其目标是造数据，而不是证明修复成功。
```

### 3.2 更新注入方式

旧表述有 `anchor bond rotation`，建议扩展为：

```markdown
### 5.3 注入方式

第一版按优先级实现：

1. `easy_rotation`：围绕合法 scaffold-R-group anchor bond 旋转 target R-group；
2. `torsion_perturb`：扰动 target R-group 内部可旋转键，固定 scaffold 和 anchor；
3. `directed_clash`：朝 protein hotspot 方向定向扰动，用于构造 mild / medium / severe 难度。

`fragment_replace`、`hard_multi_region` 和 bulky replacement 暂缓到 phase2b。
```

### 3.3 更新保留条件

将旧保留条件扩展为：

```markdown
### 5.4 保留样本条件

主集 `supported_single_rgroup` 必须满足：

| 条件 | 阈值 / 要求 |
|---|---:|
| RDKit sanitize | pass |
| anchor bond | 合法 rotatable single bond |
| ligand internal severe clash | 0 |
| anchor integrity | pass |
| scaffold RMSD | < 0.3 Å |
| non-target R-group RMSD | < 0.5 Å |
| target severe clash pairs | >= 1 |
| target score ratio valid | >= 0.7 |
| scaffold severe pairs | 0 |
| non-target severe pairs | 0 |
| max clash depth | 不极端，第一版建议 <= 1.5 Å |

可选使用 RDKit MMFF / UFF 做 ligand-only energy delta 粗筛。该能量检查仅用于过滤 ligand 自身极端不合理构象，不用于优化 protein-ligand complex。
```

### 3.4 新增 split 设计

加入：

```markdown
### 5.5 阶段 2 split

阶段 2 产出分层：

| split | 用途 |
|---|---|
| `supported_single_rgroup` | 阶段 3 Top-1 / Top-3 主评估 |
| `ambiguous_region` | hard / reject split |
| `multi_region` | reject split |
| `scaffold_clash` | reject split |
| `global_pose_failure` | reject split |
| `near_miss_contact` | 不进主集 |
| `invalid_conformer` | ligand 自身不合理，丢弃但统计 |
| `unsupported` | 化学或 mask 不支持 |
| `duplicate_removed` | 重复样本，不进主集 |
```

### 3.5 更新阶段 3 指标口径

阶段 3 小节应明确：

```markdown
阶段 3 的 Top-1 / Top-3 主指标只在 `supported_single_rgroup` synthetic failures 上计算。`ambiguous_region`、`multi_region`、`scaffold_clash`、`global_pose_failure` 和 `unsupported` 不混入 Top-1 / Top-3 主指标，而是单独报告 RejectRecall、UnsupportedRecall 和 FalseLocalRepair。
```

---

## 4. 更新 `docs/20260504-02-Clash2Feedback-GC_第一篇论文实验方案.md`

### 4.1 更新人工注入边界

在“人工局部碰撞注入”小节补充：

```markdown
注意：anchor bond rotation 构造的是 controlled synthetic failed pose，用于建立标签清楚的局部碰撞样本。它不应被表述为真实热力学稳定结合构象。阶段 2 不对 protein-ligand complex 做强 minimization，因为这可能消除人工注入的 protein-ligand clash，使 failed-pose 标签失效。
```

### 4.2 更新 ligand validity gates

将旧的“高能不合理构象”表述具体化：

```markdown
第一版 rotation / torsion injection 之后，必须做 ligand-only 合理性检查：

- RDKit sanitize pass；
- anchor bond 是合法 rotatable single bond；
- 不旋转 ring bond、double bond、aromatic bond、amide-like bond 或强共轭受限 bond；
- ligand internal severe clash = 0；
- anchor integrity pass；
- chirality preserved；
- 可选：RDKit MMFF / UFF energy delta 粗筛。

MMFF / UFF 仅作为 ligand-only energy filter，不作为生成或修复方法，也不用于 whole complex minimization。
```

### 4.3 更新人工失败样本保留条件

旧条件：

```text
LigandValid = 1
ScaffoldStable = 1
LocalClash = 1
SingleRegionDominant = 1
```

建议改成：

```text
LigandValid = 1
LigandInternalValid = 1
AnchorIntegrity = 1
EnergyDeltaOK = 1 或 unavailable-recorded
ScaffoldStable = 1
NonTargetStable = 1
LocalClash = 1
SingleRegionDominant = 1
```

### 4.4 更新人工失败集分层

补充 `invalid_conformer`、`near_miss_contact` 和 `duplicate_removed`：

```markdown
人工失败集不只保存 supported / hard split，还应保存：

- `invalid_conformer`：旋转后 ligand 自身不合理；
- `near_miss_contact`：接近 protein 但未达到 severe clash；
- `duplicate_removed`：重复 clash pattern 样本；
- `unsupported`：当前 chemistry / mask 不支持。

这些不进入主评估集，但必须统计原因。
```

### 4.5 更新 BIBM 叙事

如果该文档用于 BIBM 版论文，应补充：

```markdown
BIBM 版阶段 2 的人工 injected split 只用于构造带真值的 locator / repair benchmark。它不声称 injected poses 是真实稳定结合构象。真实或生成模型诱导失败需要作为 natural/model-induced split 在后续阶段补充。
```

---

## 5. 更新 `docs/20260504-01-Clash2Feedback-GC_完整方案与升级路线.md`

### 5.1 更新数据集设计

在 `ClashRepairBench-RG` 数据集部分加入：

```markdown
人工注入局部碰撞集应按如下 split 保存：

| split | 含义 |
|---|---|
| `supported_single_rgroup` | target R-group 单区域主导，主评估集 |
| `ambiguous_region` | target 有 clash，但区域不够单一 |
| `multi_region` | 多个 R-groups 同时 severe |
| `scaffold_clash` | scaffold 发生 severe clash |
| `global_pose_failure` | 多区域整体失败 |
| `near_miss_contact` | 接近但未 severe |
| `invalid_conformer` | ligand 自身构象不合理 |
| `unsupported` | 化学或 mask 不支持 |
| `duplicate_removed` | 重复样本 |
```

### 5.2 更新边界说明

补充：

```markdown
人工注入样本是 controlled synthetic failed poses，不是热力学稳定结合构象。它们用于提供明确 target R-group 标签，以验证 detector、locator 和 verifier。真实生成失败场景应由 model-induced / natural failure split 在后续阶段验证。
```

### 5.3 更新 full receptor 边界

补充：

```markdown
阶段 2 仍是 pocket-level synthetic failed pose benchmark。full receptor 不作为阶段 2 hard gate。若后续有 full receptor，可在阶段 4/5/8 做 shadow check 或 final full-receptor checked metric。
```

### 5.4 更新防泄漏说明

补充：

```markdown
阶段 2 benchmark construction 不得使用 predicted dominant R-group 是否等于 target R-group 作为唯一保留条件，否则阶段 3 locator evaluation 会产生构造泄漏。所有 injected variants 必须继承 base complex 的 split。
```

---

## 6. 更新 `docs/20260508-Clash2Feedback-GC_阶段1碰撞检测器与可靠验证器方案.md`

### 6.1 更新“与阶段 2–4 的接口”

在阶段 2 接口部分补充：

```markdown
阶段 2 调用阶段 1 detector / attribution 的用途是：

- 判断人工扰动后是否产生 protein-ligand severe clash；
- 记录 target / non-target / scaffold clash scores；
- 记录 predicted dominant region，但不把 predicted dominant == target 作为唯一保留条件；
- 根据 oracle target、non-target severe count、scaffold severe count 等字段分配 `supported_single_rgroup`、`ambiguous_region`、`multi_region`、`scaffold_clash`、`invalid_conformer`、`unsupported` 等 split。
```

### 6.2 更新 docs 强调内容

已有文档中“人工 rotation injection 构造的是 controlled synthetic failed pose，不应表述为真实稳定结合构象”是正确的，但建议加强：

```markdown
阶段 2 不做 whole protein-ligand complex minimization。RDKit MMFF / UFF 可作为 ligand-only energy delta filter，用于排除 ligand 自身极端不合理的构象，但不用于消除人工注入的 protein-ligand clash。
```

### 6.3 更新 verifier 与 phase2 的关系

补充：

```markdown
阶段 2 不验证生成器修复，但应准备 verifier preflight：

- no-repair negative：synthetic failed → synthetic failed，应 fail；
- oracle repair：synthetic failed → original clean，应 pass；
- wrong-region repair：synthetic failed → wrong region moved，应 fail。

这用于确认阶段 1 verifier 能处理阶段 2 的 failed pose，但不等同于阶段 4 真实 repair candidate 验证。
```

---

## 7. 可选更新 `docs/20260505-Clash2Feedback-GC_阶段0工程方案.md`

阶段 0 文档基本不需要大改，但建议补充三个阶段 2 相关字段的重要性。

### 7.1 强调 `orig_atom_idx`

在 ligand 读取部分补充：

```markdown
读取 ligand 后必须记录 `orig_atom_idx`，并在后续 scaffold/R-group/mask/anchor 中始终映射回原始 heavy atom index。阶段 2 会依赖该字段保证人工扰动、SDF round-trip 和 clash attribution 的 atom index 一致。
```

### 7.2 强调 rotatable bond 信息

在 ligand bonds 字段中补充：

```markdown
`is_rotatable` 字段不仅用于后续修复，也用于阶段 2 判断 anchor bond 或 target R-group 内部 torsion 是否可合法扰动。
```

### 7.3 强调 split inheritance

在 split 部分补充：

```markdown
后续阶段 2 的所有人工注入样本必须继承 base complex 的 split。不得将同一个 base complex 的不同 injected variants 拆到 train / val / test 不同集合中。
```

---

## 8. 建议 docs 新旧内容替换优先级

### P0：必须改

```text
docs/20260504-03-Clash2Feedback-GC_总体实验递进路线.md
docs/20260504-02-Clash2Feedback-GC_第一篇论文实验方案.md
```

原因：这两个文档直接指导阶段 2/3/论文实验，如果旧口径不更新，会影响 Codex 实施和后续写作。

### P1：建议改

```text
docs/20260504-01-Clash2Feedback-GC_完整方案与升级路线.md
docs/20260508-Clash2Feedback-GC_阶段1碰撞检测器与可靠验证器方案.md
```

原因：完整路线和阶段 1 接口需要同步阶段 2 的最终约束。

### P2：可选改

```text
docs/20260505-Clash2Feedback-GC_阶段0工程方案.md
```

原因：阶段 0 已经基本正确，只需补充 index / rotatable / split inheritance 的重要性。

---

## 9. Codex 更新 docs 的执行要求

Codex 应执行：

```text
1. 读取 docs/20260510-Clash2Feedback-GC_阶段2人工局部碰撞注入最终落地方案.md；
2. 读取本 docs 调整建议；
3. 检查 docs/ 下已有文档是否已经包含上述新口径；
4. 对缺失或冲突内容进行最小必要更新；
5. 避免重复粘贴过长内容；
6. 在旧文档中加入“详见阶段 2 最终落地方案文档”的交叉引用；
7. 更新后运行 markdown 基础检查，确认公式和表格不破；
8. 最终生成 docs 更新总结。
```

建议 Codex 生成：

```text
tmp/20260510/20260510-docs_update_summary.md
```

内容包括：

```text
- 修改了哪些 docs 文件；
- 每个文件改了哪些小节；
- 是否存在仍未对齐的旧表述；
- 是否需要人工确认。
```

---

## 10. 最终建议

docs 更新目标不是把所有文档都重写，而是让旧文档与阶段 2 最终落地方案保持一致。

最关键的统一口径是：

```text
阶段 2 是 controlled synthetic failed pose benchmark construction；
不是生成模型；
不是修复；
不是稳定结合构象证明；
只保留 ligand 自身合理、target R-group protein-ligand severe clash 明确的 supported 主集；
invalid / reject / unsupported / duplicate 必须单独报告；
不能用 predicted dominant 是否等于 target 来筛主集；
所有 injected variants 必须继承 base split。
```
