# Clash2Feedback-GC：docs 文档调整建议

> 版本：2026-05-08  
> 建议存放位置：`tmp/20260508-Clash2Feedback-GC_docs文档调整建议.md`  
> 用途：给 Codex 或人工编辑使用，指导对 `docs/` 下既有规划文档做局部修订。  
> 说明：本文不是最终 docs 正文，而是“修改说明 + 推荐补丁内容”。Codex 应阅读本文和 `docs/20260508-Clash2Feedback-GC_阶段1碰撞检测器与可靠验证器方案.md` 后，再修改 docs 下对应文档。

---

## 0. 需要阅读的文档

Codex 修改 docs 前请先阅读：

```text
docs/20260504-01-Clash2Feedback-GC_完整方案与升级路线.md
docs/20260504-02-Clash2Feedback-GC_第一篇论文实验方案.md
docs/20260504-03-Clash2Feedback-GC_总体实验递进路线.md
docs/20260505-Clash2Feedback-GC_阶段0工程方案.md
docs/20260508-Clash2Feedback-GC_阶段1碰撞检测器与可靠验证器方案.md
```

修改原则：

1. 不大段重写既有文档；
2. 优先局部补充和修正不准确口径；
3. 保持四份原文的统一工程目录约定；
4. 阶段 1 专门细节以 `20260508` 阶段 1 方案文档为准；
5. 不把运行 CSV / JSON 大段复制进 docs；
6. 不把临时分析日志写进 docs；
7. docs 中只写稳定边界、实验路线和方法口径。

---

## 1. `docs/20260504-03-Clash2Feedback-GC_总体实验递进路线.md`

### 1.1 需要调整的原因

当前文档中阶段 1 已经写了 clash detector、R-group score、verifier 初始条件和产出。但有四个点需要补强：

1. 阶段 1 通过标准里写了“对人工局部碰撞样本 R-group Top-1 / Top-3”，这更应该放在阶段 3，因为人工失败样本来自阶段 2；
2. 需要补充 receptor scope：`phase0_pocket8`、`pocket10_all_atoms`、`full_receptor_dynamic_shell`；
3. 需要补充 multi-region / scaffold / global pose failure 的分类和 reject 口径；
4. 需要说明 full receptor 不阻塞阶段 1–3，阶段 4/5/8 逐步引入。

### 1.2 建议修改位置：阶段 1 小节

在 `## 4. 阶段 1：碰撞检测器与可靠验证器` 内，建议新增一个小节：

```markdown
### 4.x receptor scope 口径

阶段 1 detector 必须显式记录 `receptor_scope`。当前 phase0 主数据的 CrossDocked / IF3 样本通常来自 `*_pocket10.pdb`，因此阶段 1 默认支持两种局部作用域：

| scope | 来源 | 用途 |
|---|---|---|
| `phase0_pocket8` | 阶段 0 从当前 `protein.pdb` 中按 ligand heavy atoms 周围 8 Å 提取的 pocket | old clash diagnosis 和 R-group attribution |
| `pocket10_all_atoms` | 当前 processed sample 中的 `protein` 全部原子；当前通常是数据源预裁剪的 pocket10 | repair candidate 的 local new clash check |

`full_receptor_dynamic_shell` 仅作为后续预留作用域：若后续补齐 full receptor，可围绕 repaired ligand 当前坐标动态提取 10–12 Å protein shell 做最终检查。full receptor 不作为阶段 1--3 的 hard dependency；阶段 4 可作为 shadow check，阶段 5 可进入 candidate label，阶段 8 建议作为 final full-receptor checked metric。
```

### 1.3 建议修改位置：阶段 1 通过标准

将当前 `### 4.6 阶段 1 通过标准` 中“人工局部碰撞样本 Top-1 / Top-3”改成两段。

推荐替换为：

```markdown
### 4.6 阶段 1 通过标准

阶段 1 自身不以人工注入样本上的 R-group Top-1 / Top-3 作为关闭条件，因为人工失败样本来自阶段 2，规则定位评估属于阶段 3。

阶段 1 关闭条件：

| 指标 | 要求 |
|---|---:|
| 51 个 clean pool 样本可检测 | 100% |
| `phase0_balanced_30_v0_1` 可检测 | 100% |
| 支持 `phase0_pocket8` 和 `pocket10_all_atoms` | 是 |
| 输出 pair-level clash report | 是 |
| 输出 R-group attribution report | 是 |
| 输出 failure type counts | 是 |
| `δ = 0.3, 0.4, 0.5` sensitivity 已完成 | 是 |
| clean pool severe false positive | 尽量接近 0，若非 0 需逐例解释 |
| verifier clean-vs-clean smoke test | 100% 或逐例解释 |
| `python -m compileall src scripts` 和 `pytest` | 通过 |

人工注入样本上的规则定位通过标准移动到阶段 3：

| 指标 | 最低要求 |
|---|---:|
| dominant ratio 平均值 | > 0.75 |
| R-group Top-1 | > 70% |
| R-group Top-3 | > 90% |
```

### 1.4 建议新增 failure type 分类

在阶段 1 小节中新增：

```markdown
### 4.x failure type 分类

阶段 1 不只输出是否有 clash，还应输出 `failure_type`：

| 条件 | failure_type | 第一版动作 |
|---|---|---|
| 无 severe clash | `no_clash` | no repair needed |
| 单个 valid R-group 主导，dominant ratio ≥ 0.7 | `single_rgroup_clash` | local R-group repair |
| 0.5 ≤ dominant ratio < 0.7 | `ambiguous_region_clash` | reject 或 hard split |
| 多个 R-groups 明显贡献 clash | `multi_region_clash` | 第一版 reject，后续 expand-mask / sequential repair |
| scaffold score 最高 | `scaffold_clash` | reject |
| ligand 多区域整体偏移 | `global_pose_failure` | full resampling 或 reject |
| covalent / metal / unsupported chemistry | `unsupported_chemistry` | reject |

第一篇主指标聚焦 `single_rgroup_clash`。其他类型应识别、统计和单独报告，不进入 single-R-group repair 主指标。
```

### 1.5 阶段 2 小节补充

在阶段 2 注入方式后补充：

```markdown
连接键旋转构造的是 controlled synthetic failed pose，不应表述为真实稳定结合构象。第一版只应围绕化学上可旋转的 single bond 做 rotation，并过滤 ligand internal severe clash、高能不合理构象、multi-region clash 和 scaffold drift。后续可扩展 torsion perturbation、clash-directed perturbation、fragment replacement 和 model-induced failures。
```

---

## 2. `docs/20260504-02-Clash2Feedback-GC_第一篇论文实验方案.md`

### 2.1 需要调整的原因

当前文档已经写了人工注入三种方式、碰撞定义、可靠验证器和第一篇只聚焦局部 R-group clash。需要进一步强调：

1. anchor rotation 是 controlled synthetic failed pose，不是稳定结合构象；
2. 人工失败集应分层，不能只靠最简单的旋转；
3. multi-region / scaffold / global pose failure 应识别并 reject 或单独报告；
4. 评价指标可以增加 pocket-level 与 full-receptor checked 两套口径；
5. full receptor 不作为早期 hard dependency，但最终模型诱导失败测试应尽量纳入。

### 2.2 建议修改位置：人工局部碰撞注入

在 `## 8. 人工局部碰撞注入` 下，“方式一：围绕 anchor bond 旋转”后补充：

```markdown
注意：anchor bond rotation 构造的是 controlled synthetic failed pose，用于建立标签清楚的局部碰撞样本，主要服务 detector、locator 和 verifier 的早期验证。它不应被表述为真实热力学稳定结合构象。

第一版 rotation injection 只允许围绕化学上可旋转的 single bond 进行。以下情况应排除或标记 unsupported：

- ring bond；
- double bond；
- amide-like bond；
- 强共轭受限 bond；
- 多锚点 linker；
- 旋转后 ligand internal severe clash；
- 旋转后 scaffold 或非目标 R-group 明显漂移；
- 旋转后变成 multi-region clash。
```

### 2.3 建议新增人工失败集分层

在 `## 8` 或 `## 9` 后新增：

```markdown
### 人工失败集分层

人工失败样本建议分层保存和报告：

| split | 构造方式 | 用途 |
|---|---|---|
| `easy_rotation` | single R-group anchor bond rotation | detector / locator debug 和基础主集 |
| `torsion_perturb` | 目标 R-group 内部 rotatable bond 扰动 | 更接近局部构象错误 |
| `directed_clash` | 朝 protein hotspot 方向定向扰动 | 构造 mild / medium / severe 难度 |
| `fragment_replace` | 合法 R-group 替换 | 更接近“取代基太大导致 clash” |
| `hard_multi_region` | 多 R-group 或模糊失败区域 | stress test / reject test |

第一篇主结果可以聚焦 `single-region dominant` 样本；hard split 应单独报告，不应混入主指标。
```

### 2.4 建议修改可靠验证器指标

在 `## 15. 可靠验证器` 或评价指标中补充：

```markdown
若 full receptor 可用，建议报告两套可靠修复率：

| 指标 | 含义 |
|---|---|
| `pocket-level Reliable Repair Yield` | 在 phase0 pocket8 / pocket10 局部 receptor 下通过 reliable repair verifier |
| `full-receptor checked Reliable Repair Yield` | 在 pocket-level 通过后，再在 full receptor dynamic shell 下无新 severe clash |

当前 pocket10 数据可支持 pocket-level 修复验证；full receptor checked 结果取决于是否能获取并对齐完整蛋白结构。
```

### 2.5 建议补充 unsupported/reject 口径

在 `## 1. 第一篇论文的边界` 或 `## 12. 反馈适配器` 中补充：

```markdown
第一篇主任务是 single-region R-group clash repair。multi-region clash、scaffold clash、global pose failure、covalent ligand、metal coordination 等情况第一版应识别并标记为 `unsupported` 或 `reject`，不进入 single-R-group repair 主指标。后续可通过 expand-mask、sequential repair、full resampling、multi-label critic 或 learned adapter 逐步处理。
```

---

## 3. `docs/20260505-Clash2Feedback-GC_阶段0工程方案.md`

### 3.1 需要调整的原因

当前阶段 0 文档已经补充了 protein / target / pocket 术语，并写明 CrossDocked / IF3 使用 pocket10、阶段 0 再提取 8 Å pocket。需要小幅补充：

1. `receptor` 术语；
2. full receptor 后续 metadata 口径；
3. 阶段 0 不强制 full receptor；
4. `protein.pdb` 可能是 pocket-level receptor，不应在后续报告误写成 full receptor。

### 3.2 建议修改位置：1.1 protein、target 和 pocket 的术语口径

在术语表中增加一行：

```markdown
| receptor / 受体 | 在 protein-ligand 语境中接纳 ligand 的蛋白结构 | 工程中通常指当前样本用作 ligand 环境的蛋白坐标；可以是 full receptor，也可以是数据源预裁剪的 pocket10 局部 receptor |
```

在术语说明后补充：

```markdown
本项目中 `receptor` 和 `protein.pdb` 在多数工程上下文中指同一个坐标输入，但需要注意：`protein.pdb` 不一定是完整蛋白。当前 IF3 / CrossDocked pocket10 主数据中，`protein.pdb` 是 ligand 周围约 10 Å 的局部 receptor。后续若补充 full receptor，应在 metadata 中单独记录 `full_receptor_path`、`protein_scope` 和 `full_receptor_alignment_status`，不要混淆 pocket-level 和 full-receptor-level 验证结果。
```

### 3.3 建议修改位置：processed sample / metadata 字段

在 metadata 建议字段中补充可选字段：

```python
"protein_scope": "pocket10" | "full_receptor" | "unknown",
"full_receptor_path": str | None,
"full_receptor_alignment_status": str | None,
```

并说明：

```markdown
阶段 0 不强制 full receptor。若后续阶段 4/5/8 为部分样本补充 full receptor，应保证 full receptor 与 pocket10 / ligand 坐标系一致，并将对齐状态写入 metadata 或后续报告。
```

---

## 4. `docs/20260504-01-Clash2Feedback-GC_完整方案与升级路线.md`

### 4.1 需要调整的原因

完整方案已有“第一篇不同时处理所有失败类型”“multi-anchor / macrocycle / covalent / metal unsupported”等口径。需要补充：

1. single-region 主任务与 multi-region 后续扩展；
2. repair/eval protocol 记录 receptor_scope；
3. full receptor 引入阶段；
4. reject 是系统能力，不是单纯失败。

### 4.2 建议新增内容：single-region 与 multi-region

在“scaffold、R-groups 与 anchor”或“分层升级路线”附近补充：

```markdown
第一篇主任务聚焦 `single-region R-group clash repair`。也就是说，主要碰撞贡献应集中在一个 valid single-anchor R-group 上。对于 multi-region clash、scaffold clash、global pose failure 等情况，第一版应识别并输出 `reject` 或 `unsupported`，而不是强行局部修复。

后续扩展路线包括：

| 失败类型 | 后续处理方式 |
|---|---|
| ambiguous / multi-region clash | expand-mask repair、top-k R-group edit、sequential repair |
| scaffold clash | reject 或 full resampling |
| global pose failure | full resampling 或 docking-level correction |
| covalent / metal / multi-anchor linker | 特殊 chemistry module 或 unsupported |
```

### 4.3 建议修改修复协议和评价协议

在 \(\mathcal P_t^{repair}\) 和 \(\mathcal P_t^{eval}\) 字段表中补充：

```markdown
| receptor_scope | 当前诊断和验证使用的 protein/receptor 作用域，如 `phase0_pocket8`、`pocket10_all_atoms`、`full_receptor_dynamic_shell` |
| failure_type | `single_rgroup_clash`、`multi_region_clash`、`scaffold_clash`、`global_pose_failure`、`unsupported_chemistry` 等 |
```

在可靠验证器描述中补充：

```markdown
在 pocket10 数据上，可靠验证器默认只能声称 pocket-level reliable repair。若 full receptor 可用，应在 full receptor dynamic shell 下额外检查 no new severe clash，并单独报告 full-receptor checked reliable repair。
```

---

## 5. 是否需要调整 README

用户当前要求调整 docs 下文档，因此 README 可先不改。若后续需要，README 可以只加一句：

```markdown
阶段 1 方案详见 `docs/20260508-Clash2Feedback-GC_阶段1碰撞检测器与可靠验证器方案.md`。阶段 1 默认使用 pocket-level receptor scope；full receptor check 为后续阶段可选扩展。
```

---

## 6. 修改后的检查清单

Codex 修改 docs 后，请检查：

```text
[ ] docs 中不再把阶段 1 的关闭标准写成依赖人工注入 Top-1 / Top-3
[ ] docs 中明确 phase0_pocket8 与 pocket10_all_atoms 的区别
[ ] docs 中明确 full receptor 不阻塞阶段 1–3
[ ] docs 中明确 full receptor 从阶段 4/5/8 逐步引入
[ ] docs 中明确 unified δ=0.4 是阶段 1 默认，pair-specific δ 是后续扩展
[ ] docs 中明确 multi-region / scaffold / global pose failure 第一版 reject 或 unsupported
[ ] docs 中明确 anchor rotation 是 controlled synthetic failed pose，不是稳定结合构象
[ ] docs 中明确人工 benchmark 可以分层：easy_rotation / torsion_perturb / directed_clash / fragment_replace / hard_multi_region
[ ] docs 中明确 pocket-level repair 和 full-receptor checked repair 是两个不同口径
[ ] 四份 docs 的目录约定仍然一致
```

---

## 7. 建议提交说明

如果 Codex 完成 docs 修改，commit message 可用：

```text
Clarify phase1 detector scope and benchmark boundaries
```

或中文：

```text
Clarify phase1 receptor scope, verifier, and injection benchmark boundaries
```
