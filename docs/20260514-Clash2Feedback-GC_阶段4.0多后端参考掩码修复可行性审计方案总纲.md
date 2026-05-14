# Clash2Feedback-GC 阶段 4.0：多后端参考掩码修复可行性审计方案总纲

> 建议放置路径：`docs/20260514-Clash2Feedback-GC_阶段4.0多后端参考掩码修复可行性审计方案总纲.md`
> 文档定位：阶段 4.0 的方案总纲 / 上位约束
> 覆盖范围：仅阶段 4.0，即多后端参考掩码修复可行性审计。阶段 4.1 只作为后续入口条件简要说明，不在本文档中展开为执行方案。
> 重要说明：网页 ChatGPT 未在本地执行命令、未跑实验、未修改仓库。凡涉及真实路径、字段、行数、检查点、环境状态、样本统计和结果数值，均以本地 Codex 后续核查为准。若本文档与仓库事实冲突，必须先生成冲突报告，不得继续执行冲突部分。

---

## 0. 一句话定位

阶段 4.0 的核心问题是：

```text
给定正确修复区域时，不同修复后端到底能不能把局部碰撞失败候选修好？
```

阶段 4.0 只使用参考掩码，也就是人工扰动时对应的目标取代基区域。它不比较随机掩码、自动掩码和参考掩码谁更好，也不证明自动掩码的下游价值。

阶段 4.0 要先判断：

```text
如果直接告诉后端“这里就是应该修的区域”，
规则型修复、DiffSBDD、DiffDec 等后端是否能生成可读取、可验证、局部、可靠的修复候选？
```

只有当阶段 4.0 证明至少一个局部修复后端可用，后续阶段 4.1 才适合继续做随机掩码、自动掩码、参考掩码的正式对照。

---

## 1. 动机

### 1.1 为什么需要阶段 4.0

阶段 0–3 已经完成了数据底座、碰撞检测、人工局部碰撞注入、标签溯源和阶段 4 掩码种子生成。到阶段 4.0，项目第一次真正进入“尝试修复失败候选”的环节。

前面阶段主要回答：

```text
哪里发生碰撞？
哪个取代基是人工扰动目标？
旧碰撞证据在哪里？
阶段 4 应该修哪里、保留哪里、连接点在哪里？
```

阶段 4.0 要回答：

```text
在已经知道正确修复区域的情况下，不同后端是否真的有能力修？
```

这一步非常关键。因为如果参考掩码下都修不好，那么后续讨论自动掩码是否比随机掩码更好就没有意义。失败原因更可能是：

```text
修复后端不适配；
候选生成失败；
连接点接不回；
固定结构保持失败；
验证器输入映射失败；
后端本身没有局部修复能力。
```

所以阶段 4.0 是正式修复闭环前的必要前置审计。

### 1.2 为什么阶段 4.0 只用参考掩码

一个修复实验失败，可能来自三类因素：

```text
1. 修复区域找错了；
2. 修复后端本身修不好；
3. 验证器或输入适配有问题。
```

阶段 4.0 直接使用参考掩码，先排除“区域找错”的干扰。这样可以把问题收窄为：

```text
给对区域后，后端和适配链路是否可用？
```

如果参考掩码下可行，才进入阶段 4.1 做掩码策略对照；如果参考掩码下不可行，应先修后端或适配器，而不是责怪自动掩码。

### 1.3 为什么要比较多后端

阶段 4.0 不只看一个后端。原因是不同修复方式回答的问题不同：

| 后端 | 回答的问题 |
|---|---|
| 规则型固定拓扑局部构象修复 | 不换取代基，只靠旋转和扭转能不能修？ |
| DiffSBDD 局部补全 | 删除目标取代基，固定保留结构，让模型补回局部，能不能修？ |
| DiffDec 单取代基重采样 | 从同一连接点重新生成一个取代基，能不能修？ |
| DiffSBDD 全配体重新采样 | 直接重新生成完整配体，与局部修复相比有什么差异？ |

这能帮助判断：

```text
这类失败只是构象摆放问题？
还是需要重新补全局部片段？
还是需要重新生成取代基？
还是干脆全配体重采样更实际？
```

---

## 2. 本阶段最终目标

阶段 4.0 的最终目标是：

```text
在参考掩码已知的条件下，系统比较多种修复后端在局部碰撞修复任务中的接入能力、候选生成能力、连接点保持能力、旧碰撞消除能力、无新严重碰撞能力和可靠修复率。
```

阶段 4.0 完成后，应该能给出以下判断：

```text
1. 哪些后端能接入当前 Clash2Feedback-GC 数据格式？
2. 哪些后端能读取阶段 4 掩码种子并构造输入？
3. 哪些后端能生成候选？
4. 哪些候选能被统一读取和标准化？
5. 哪些候选能保持固定结构和连接点？
6. 哪些候选能消除旧碰撞且不引入新严重碰撞？
7. 哪个后端最适合作为后续阶段 4.1 的正式主后端？
8. 如果所有后端都不理想，主要瓶颈在哪里？
```

本阶段不以“全面优化药物性质”为目标。阶段 4.0 的主指标是：

```text
样本级可靠修复率
```

不是：

```text
结合成功率；
对接分数提升；
亲和力提升；
生成模型整体能力排名。
```

---

## 3. 阶段边界

### 3.1 阶段 4.0 做什么

阶段 4.0 做：

```text
1. 读取阶段 3 生成的 phase4_mask_seed.csv；
2. 只使用参考掩码；
3. 固定 5 个预检样本；
4. 固定 40 个正式小规模样本；
5. 每个后端、每个样本最多输出 K=8 个候选；
6. 接入规则型固定拓扑局部构象修复；
7. 接入 DiffSBDD CrossDocked 全原子条件模型局部补全；
8. 调研并预检 DiffSBDD CrossDocked 全原子联合模型局部补全；
9. 调研并尝试接入 DiffDec 单取代基重采样；
10. 接入 DiffSBDD CrossDocked 全原子条件模型全配体重新采样对照；
11. 对所有可运行后端生成的候选使用统一验证器评价；
12. 记录后端可用性、输入适配、候选生成、候选读取、固定结构匹配、连接点完整性、可靠修复结果和失败原因；
13. 输出阶段 4.0 后端可行性报告和进入阶段 4.1 的建议。
```

### 3.2 阶段 4.0 不做什么

阶段 4.0 不做：

```text
不训练模型；
不微调 DiffSBDD；
不微调 DiffDec；
不训练排序器；
不训练学习型纠错器；
不训练反馈适配器；
不做强化学习；
不修改 DiffSBDD / DiffDec 原始去噪过程；
不声称碰撞热区进入生成过程；
不做随机掩码、自动掩码、参考掩码正式对照；
不证明自动掩码的下游修复价值；
不证明定位器无偏准确；
不做多轮迭代修复；
不把 Vina 或 docking score 作为主指标；
不修改阶段 2、阶段 2.5、阶段 3 历史结果；
不覆盖 phase4_mask_seed.csv；
不提交外部源码、模型权重、大量候选 SDF 或日志缓存。
```

### 3.3 和阶段 4.1 的关系

阶段 4.1 不在本文档中展开。

阶段 4.0 只需要为阶段 4.1 给出入口判断：

```text
如果至少一个局部修复后端在参考掩码下产生非零且可解释的样本级可靠修复率，
并且候选生成、读取、验证链路稳定，
则可以进入阶段 4.1。
```

阶段 4.1 需要另行制定正式方案，再讨论：

```text
是否使用 S2 全量；
是否使用 40 case 扩展集；
主后端选谁；
随机掩码采几个；
predicted 和 oracle 相同时如何排表；
random mask size diff 如何做敏感性分析；
是否加入 hard filter 和 full resampling 基线。
```

---

## 4. 核心假设

### 4.1 可采用的假设

阶段 4.0 可以采用以下假设：

```text
1. phase4_mask_seed.csv 可以提供阶段 4.0 所需的参考掩码、保留掩码、连接点和旧碰撞证据；
2. 参考掩码对应的是人工扰动目标取代基，可作为后端可行性审计的输入；
3. 支持单取代基的 S2 集合可以作为 clean local repair substrate；
4. 如果给定正确参考掩码，至少一部分局部碰撞失败样本应可被局部修复；
5. 规则型修复、DiffSBDD 局部补全、DiffDec 取代基重采样适合从不同角度审计局部修复可行性；
6. 统一可靠验证器可以作为所有后端的最终裁判。
```

### 4.2 不允许采用的假设

阶段 4.0 不允许采用以下假设：

```text
1. 参考掩码下修好了，就证明自动掩码有效；
2. 参考掩码下修好了，就证明定位器准确；
3. 没有碰撞就一定是可靠修复；
4. Vina 分数提高就代表修复成功；
5. DiffSBDD / DiffDec 原版已经接收完整碰撞热区反馈；
6. 全配体重新采样生成无碰撞候选，就等价于局部修复成功；
7. 规则型方法能修 easy_rotation，就代表真实生成失败都能规则修复；
8. DiffDec 必须跑通，否则阶段 4.0 主线失败。
```

---

## 5. 事实依据与结果来源

### 5.1 已有项目口径

阶段 4.0 依赖以下已有项目口径：

```text
1. docs/ 中已有方案文档采用 日期-Clash2Feedback-GC_阶段N主题方案总纲.md 的命名格式；
2. 项目总体路线中，阶段 4 的定位是先做后端可行性审计，再做正式局部修复闭环；
3. 阶段 1 的可靠验证器负责判断旧碰撞是否消除、无新严重碰撞、骨架稳定、非编辑区域稳定、坐标合法、编辑遵循和口袋保持；
4. 阶段 2 的 supported_single_rgroup 是受控的 clean local repair substrate，不是无偏定位 benchmark；
5. 阶段 3 的 phase4_mask_seed.csv 是阶段 4 输入来源；
6. docs/external_baselines.md 中，DiffSBDD / DiffDec 原版只能作为候选补全或局部受约束重采样后端，不能写成完整碰撞反馈引导去噪。
```

### 5.2 本地 Codex 必须核查的事实

以下内容必须由本地 Codex 在真实仓库中核查，不能由本方案直接当作已完成事实：

```text
1. 当前分支和 commit；
2. main 是否已经合入阶段 3 产物；
3. reports/phase3_label_provenance_audit/phase4_mask_seed.csv 是否存在；
4. phase4_mask_seed.csv 行数；
5. phase4_0_backend_feasibility_candidate 是否存在且可用；
6. oracle_mask_atom_indices / oracle_keep_atom_indices / oracle_anchor_* 字段是否齐全；
7. old_clash_pairs_json 是否存在且可解析；
8. protein_clash_hot_atoms_json / protein_clash_hot_residues_json 是否存在；
9. S2 样本数和分布；
10. injection_mode / difficulty_bin / base_split / oracle_mask_size / max_clash_depth / target_num_severe_pairs 的真实分布；
11. data/benchmarks/clashrepairbench_rg_artificial/v0_1/ 下样本文件是否可读取；
12. reports/phase1_clash_detector/ 下验证器配置和报告是否可读取；
13. verify_repair 是否只支持同拓扑同原子顺序候选；
14. 是否需要新增阶段 4 verifier adapter；
15. external/DiffSBDD 是否存在；
16. DiffSBDD 条件模型检查点是否存在、大小和哈希是否匹配；
17. DiffSBDD 条件模型是否能运行 inpaint.py；
18. DiffSBDD 联合模型是否存在并能用于局部补全；
19. external/DiffDec 是否存在；
20. DiffDec 环境、检查点、官方示例是否可用；
21. Open Babel、RDKit、conda 环境是否可用；
22. 外部源码和检查点是否被正确忽略、不进入 Git 提交。
```

如上述关键事实与方案不一致，应按冲突处理规则执行。

---

## 6. 输入设计

### 6.1 核心输入

阶段 4.0 的核心输入为：

```text
reports/phase3_label_provenance_audit/phase4_mask_seed.csv
```

本地 Codex 必须核查该表是否包含阶段 4.0 所需字段。

建议重点读取字段：

```text
case_id
base_sample_id
base_split
injection_mode
difficulty_bin

oracle_mask_atom_indices
oracle_keep_atom_indices
oracle_anchor_scaffold_atom_idx
oracle_anchor_rgroup_atom_idx
oracle_anchor_bond_idx

old_clash_pairs_json
protein_clash_hot_atoms_json
protein_clash_hot_residues_json

target_num_severe_pairs
max_clash_depth
total_clash_score

phase4_0_backend_feasibility_candidate
```

若字段名与方案不同但语义一致，Codex 应在执行计划中给出字段映射。

若关键字段缺失，必须生成冲突报告或阻塞报告。

### 6.2 其他输入

本地 Codex 需要核查并读取：

```text
data/benchmarks/clashrepairbench_rg_artificial/v0_1/manifest.parquet
data/benchmarks/clashrepairbench_rg_artificial/v0_1/samples/*.pkl
data/benchmarks/clashrepairbench_rg_artificial/v0_1/ligands/*_failed.sdf

data/processed/v0_1/complexes/*.pkl
data/raw_complexes/*/protein.pdb
data/raw_complexes/*/ligand.sdf

configs/phase1_clash_detector.yaml
src/clash2feedback/verifier/repair_verifier.py
src/clash2feedback/geometry/clash.py
src/clash2feedback/geometry/rgroup_attribution.py

docs/external_baselines.md
external/README.md
external/DiffSBDD/
external/DiffDec/
```

所有路径必须以本地实际仓库为准。

---

## 7. 样本设计

### 7.1 预检样本

预检样本数固定为：

```text
5 个 S2 case
```

预检不是统计实验，只用于确认：

```text
输入能不能构造；
后端能不能运行；
候选能不能生成；
候选能不能读取；
候选能不能进入验证器；
失败原因能不能记录。
```

预检样本选择原则：

```text
优先 val/test；
覆盖 easy_rotation、torsion_perturb、directed_clash；
至少包含 1 个 medium case；
参考掩码大小适中；
target_num_severe_pairs 不极端；
max_clash_depth 不极端；
允许少量 base_sample_id 重复，但必须记录 selection_reason。
```

输出：

```text
reports/phase4_0_backend_feasibility/selected_cases_preflight.csv
```

### 7.2 正式小规模样本

正式小规模样本数固定为：

```text
40 个 S2 case
```

候选预算固定为：

```text
每个后端单元、每个样本最多 K=8 个候选。
```

建议分层目标：

```text
injection_mode:
  directed_clash = 14
  easy_rotation = 13
  torsion_perturb = 13

difficulty_bin:
  easy = 27
  medium = 13

base_split:
  按 S2 全量分布近似抽样，并在报告中按 train / val / test 分层输出。
```

注意：

```text
40 个样本是后端可行性审计集合，不是 held-out 泛化测试集。
```

输出：

```text
reports/phase4_0_backend_feasibility/selected_cases.csv
```

必须记录：

```text
case_id
base_sample_id
base_split
injection_mode
difficulty_bin
oracle_mask_size
random_mask_size_diff
target_num_severe_pairs
max_clash_depth
selection_seed
selection_reason
```

---

## 8. 后端矩阵

阶段 4.0 采用：

```text
四类后端；
五个第一轮后端单元。
```

### 8.1 四类后端

| 类别 | 后端 | 作用 |
|---|---|---|
| 规则型修复 | 固定拓扑局部构象修复 | 判断只靠旋转和扭转能否修好 |
| DiffSBDD 局部补全 | 删除目标取代基，固定保留区域，让模型补全局部 | 测试生成式局部补全能力 |
| DiffDec 单取代基重采样 | 固定保留结构，从连接点重新生成取代基 | 测试取代基级重采样能力 |
| DiffSBDD 全配体重新采样 | 不做局部修复，重新生成完整配体 | 作为“直接重来”的全局对照 |

### 8.2 五个后端单元

| 后端单元 | 第一轮状态 | 阻塞规则 |
|---|---|---|
| 规则型固定拓扑局部构象修复 | 必做 | 阻塞阶段 4.0 主线 |
| DiffSBDD CrossDocked 全原子条件模型局部补全 | 必做 | 阻塞阶段 4.0 主线 |
| DiffSBDD CrossDocked 全原子联合模型局部补全 | 必须调研和预检 | 若检查点或接口阻塞，不阻塞主线 |
| DiffDec 单取代基模型 | 必须调研和尝试预检 | 若环境或检查点阻塞，不阻塞主线 |
| DiffSBDD CrossDocked 全原子条件模型全配体重新采样 | 必做 | 阻塞阶段 4.0 主线 |

资源允许项：

```text
DiffSBDD Binding MOAD 全原子模型；
DiffSBDD 碳α模型；
DiffDec 多取代基模型。
```

这些只作为扩展，不作为第一轮硬要求。

---

## 9. 修复轮次设计

阶段 4.0 采用：

```text
单轮多候选修复设计。
```

也就是：

```text
每个失败样本；
每个后端；
给定一个参考掩码；
执行一次修复调用或一次构象搜索；
最多输出 K=8 个候选；
统一验证器判断这 8 个候选中是否至少有 1 个可靠修复成功。
```

阶段 4.0 不做：

```text
失败后再次诊断；
失败后扩大掩码；
失败后切换后端；
失败后做第二轮、第三轮修复；
多轮闭环策略。
```

多轮修复留到后续阶段。

---

## 10. 后端一：规则型固定拓扑局部构象修复

### 10.1 定位

规则型修复是阶段 4.0 的强可解释基线。

它回答：

```text
如果不重新生成取代基，只靠局部旋转和扭转，是否已经能修好部分局部碰撞失败？
```

### 10.2 原理

规则型修复不改变分子拓扑：

```text
不新增原子；
不删除原子；
不替换取代基；
不改变键连接；
不调用生成模型。
```

它只移动参考掩码对应的目标取代基，固定骨架和非目标区域。

### 10.3 输入

```text
failed ligand topology and coords；
protein sample；
oracle_mask_atom_indices；
oracle_keep_atom_indices；
oracle_anchor_scaffold_atom_idx；
oracle_anchor_rgroup_atom_idx；
oracle_anchor_bond_idx；
old_clash_pairs_json。
```

Codex 必须核查这些字段是否存在、能否映射到 SDF / pkl 中真实原子顺序。

### 10.4 候选生成动作

#### 动作一：连接键旋转

以：

```text
scaffold anchor atom → rgroup anchor atom
```

这条连接键为旋转轴，整体旋转目标取代基。

建议角度：

```text
±15°、±30°、±45°、±60°、±90°、±120°、180°。
```

#### 动作二：内部扭转角搜索

识别目标取代基内部可旋转单键，只旋转远离骨架的一侧原子集合。

建议角度：

```text
±30°、±60°、±90°、±120°、180°。
```

如果内部可旋转键很多，优先选择与旧碰撞原子距离最近的 2–3 条。

#### 动作三：混合搜索

先做连接键旋转，保留预评分较好的若干构象，再做内部扭转角搜索。

### 10.5 候选预算

每个样本内部最多尝试：

```text
64–256 个 proposal
```

最终最多输出：

```text
8 个候选
```

必须记录：

```text
proposal_count；
candidate_count；
candidate_source；
angles_deg；
torsion_bond；
dedup_reason；
runtime_sec。
```

内部 proposal 多不等于多轮修复。规则型方法仍然属于一轮构象搜索。

### 10.6 防止 clean pose 泄漏

规则型方法允许使用：

```text
failed pose；
ligand topology；
oracle mask；
anchor；
protein clash detector。
```

禁止使用：

```text
original clean coords 作为候选；
original clean coords 作为优化目标；
按 original clean pose RMSD 排序。
```

### 10.7 成功与失败解释

规则型方法若成功，说明该样本主要是构象摆放问题。

规则型方法若失败但 DiffSBDD / DiffDec 成功，说明该样本可能需要局部补全或取代基重采样。

规则型方法若在 `easy_rotation` 上很强，必须按 `injection_mode` 分层报告，避免误读为真实生成失败都能靠规则逆转。

---

## 11. 后端二：DiffSBDD 局部补全

### 11.1 定位

DiffSBDD 局部补全用于回答：

```text
删除发生碰撞的目标取代基，固定剩余分子结构后，DiffSBDD 能不能在蛋白口袋中补出一个可靠的新局部片段？
```

### 11.2 原理

DiffSBDD 原版局部补全不是直接接收阶段 3 的原子掩码，而是接收：

```text
protein.pdb；
ref_ligand.sdf；
fix_atoms.sdf；
add_n_nodes；
center；
n_samples。
```

阶段 4.0 中应按如下方式构造：

```text
失败配体
→ 删除 oracle_mask_atom_indices 对应目标取代基
→ 保留 oracle_keep_atom_indices 对应结构
→ 写成 fix_atoms.sdf
→ 使用 failed_ligand.sdf 作为 ref_ligand 定义 pocket
→ add_n_nodes = 目标取代基重原子数
→ 调用 inpaint.py 生成 8 个候选
```

### 11.3 模型版本

第一优先：

```text
DiffSBDD CrossDocked 全原子条件模型
```

需要调研：

```text
DiffSBDD CrossDocked 全原子联合模型
```

联合模型当前必须按本地事实核查，不能提前假设可直接运行原版 `inpaint.py`。

### 11.4 center 参数

预检中应比较：

```text
center = ligand
center = pocket
```

正式小规模实验默认值由预检决定。

注意：

```text
center=ligand 可能围绕保留结构整体中心初始化，新片段可能偏离目标连接点；
center=pocket 可能更全局化，也可能偏离局部补全目标。
```

### 11.5 输出检查

DiffSBDD 输出候选后必须检查：

```text
候选是否可读取；
固定结构是否能在候选中匹配；
连接点是否完整；
新片段是否接回骨架；
是否有多余连接；
是否产生游离碎片；
骨架和保留区域是否保持。
```

如果固定结构匹配失败或连接点失败，该候选不能算可靠修复。

### 11.6 风险

```text
固定结构可能匹配失败；
输出原子顺序可能改变；
RDKit / OpenBabel 推断键可能改变拓扑；
新片段可能没有接回 anchor；
旧碰撞可能没有消除；
旧碰撞消除后可能产生新严重碰撞；
联合模型可能不兼容原版 inpaint.py。
```

---

## 12. 后端三：DiffDec 单取代基重采样

### 12.1 定位

DiffDec 单取代基重采样用于回答：

```text
剪掉发生碰撞的目标取代基，从同一个连接点重新生成一个取代基，是否能修好局部碰撞？
```

### 12.2 原理

输入构造：

```text
失败配体
→ 删除 oracle_mask_atom_indices 对应目标取代基
→ 保留骨架 + 非目标取代基
→ 在 oracle_anchor_scaffold_atom_idx 处添加 * 出口标记
→ 生成 fixed_context.sdf
→ 生成带 * 的 scaffold smiles
→ 调用 DiffDec 单取代基模型生成新取代基
```

### 12.3 当前状态核查

Codex 必须核查：

```text
external/DiffDec 是否存在；
DiffDec commit；
DiffDec conda 环境是否存在；
DiffDec checkpoint 是否存在；
DiffDec 官方示例是否能运行；
DiffDec 输出 SDF 是否可读取。
```

DiffDec 的原则：

```text
必须调研；
必须尝试配置；
必须尝试官方示例；
必须写清楚能否接入；
若失败，写 blocked_backends.md；
但不阻塞规则型和 DiffSBDD 条件模型主线。
```

### 12.4 取代基大小控制

第一轮不能声称 DiffDec 一定能精确控制取代基大小。

必须记录：

```text
target_rgroup_heavy_atom_count；
generated_rgroup_heavy_atom_count；
size_diff。
```

如果官方脚本能跑但大小不可控，可后续实现包装器，通过采样函数传入目标取代基大小。该包装器属于输入适配，不属于修改原始去噪过程。

### 12.5 风险

```text
环境配置失败；
检查点下载失败；
官方脚本只支持单出口；
固定结构带多个非目标取代基时子结构匹配失败；
生成大小不可控；
Open Babel 推断键失败；
新取代基没有接回 anchor；
候选化学合法性差。
```

---

## 13. 后端四：DiffSBDD 全配体重新采样对照

### 13.1 定位

DiffSBDD 全配体重新采样不是局部修复方法，而是全局对照。

它回答：

```text
为什么不直接丢掉失败候选，重新生成一个完整配体？
```

### 13.2 方法

```text
使用同一个 protein pocket；
不使用 oracle mask；
不固定保留区域；
调用 DiffSBDD generate_ligands.py；
每个样本生成最多 8 个候选；
用统一验证器和适配器评价。
```

### 13.3 评价重点

它可能生成无碰撞候选，但要重点看：

```text
是否保留原骨架；
是否保留非编辑区域；
是否和原失败候选相似；
是否只是换了一个分子；
每个成功候选成本是多少。
```

如果它旧碰撞消除率高，但骨架和保留区域漂移大，不能把它解释成局部修复成功。

---

## 14. 统一验证器与评分标准

### 14.1 为什么不能只看没有碰撞

只看“没有碰撞”不够，因为可能出现：

```text
整个配体飞出口袋；
骨架被改没了；
保留区域漂移；
新片段没有接回连接点；
旧碰撞没了但产生新严重碰撞；
候选分子化学上不合法；
全配体重新采样换了一个完全不同的分子。
```

因此阶段 4.0 必须使用统一可靠修复标准。

### 14.2 候选级可靠修复定义

一个候选被判定为可靠修复成功，当且仅当：

```text
candidate_readable = true；
ligand_valid = true；
old_clash_resolved = true；
no_new_severe_clash = true；
scaffold_stable = true；
keep_region_stable = true；
anchor_integrity = true；
edit_compliance = true；
pocket_retention = true。
```

对于 DiffSBDD / DiffDec 这类可能改变拓扑或原子顺序的后端，还必须满足：

```text
fixed_structure_match_success = true。
```

### 14.3 推荐阈值

Codex 应核查阶段 1 配置。若无冲突，阶段 4.0 建议沿用：

| 指标 | 建议阈值 |
|---|---:|
| 旧碰撞分数 | 修复后 ≤ 修复前 10% |
| 旧严重碰撞对 | 原严重碰撞对不再保留 |
| 新严重碰撞数 | 0 |
| scaffold 均方根偏差 | < 0.5 Å |
| keep / non-edit 区域均方根偏差 | < 0.8 Å |
| 编辑区外明显移动比例 | ≤ 20% |
| anchor | 必须存在且连接合理 |
| 配体合法性 | 必须通过基础检查 |

### 14.4 样本级主指标

阶段 4.0 主指标是：

```text
样本级可靠修复率
```

定义：

```text
某后端在 40 个样本中，至少有 1 个候选通过可靠修复的样本数 / 40。
```

### 14.5 分母口径

以下情况都不能从样本级主指标分母中剔除：

```text
后端没生成候选；
候选不可读；
固定结构匹配失败；
连接点失败；
验证器适配失败；
候选全部非法；
候选全部未消除旧碰撞；
候选全部产生新严重碰撞。
```

这些都算作：

```text
该后端在该样本上未可靠修复成功。
```

候选级指标可以单独统计失败阶段，但不能改变样本级主指标分母。

### 14.6 其他指标

接入能力指标：

```text
backend_available；
model_load_success；
input_adapter_success；
candidate_generation_success；
candidate_readable_rate；
backend_failure_rate；
timeout_count；
runtime_sec。
```

修复能力指标：

```text
old_clash_resolved；
no_new_severe_clash；
ligand_validity；
scaffold_rmsd；
keep_region_rmsd；
anchor_integrity；
edit_compliance；
keep_compliance；
reliable_repair_yield；
cost_per_success。
```

可选指标：

```text
Vina / docking score；
QED；
SA；
LogP。
```

这些只能作为辅助观察，不能作为主指标。

---

## 15. 预期产物

### 15.1 报告产物

阶段 4.0 报告输出目录：

```text
reports/phase4_0_backend_feasibility/
```

建议输出：

```text
model_inventory.csv
backend_preflight_report.md
blocked_backends.md
selected_cases_preflight.csv
selected_cases.csv
adapter_input_manifest.csv
candidate_manifest.csv
verifier_outcome.csv
backend_comparison.csv
failure_cases.csv
phase4_0_preflight_summary.json
phase4_0_small_scale_summary.json
phase4_0_completion_audit.md
```

### 15.2 运行产物

运行产物输出目录：

```text
runs/phase4_0_backend_feasibility/
  rule_only/
  diffsbdd_inpainting/
  diffdec/
  full_resampling/
  logs/
```

注意：

```text
外部源码、检查点、大量候选 SDF、日志缓存不提交 Git。
```

### 15.3 计划和冲突报告

Codex 计划输出：

```text
tmp/20260514/phase4-0-backend-feasibility-codex-goal-exec-plan.md
```

如有冲突：

```text
tmp/20260514/phase4-0-backend-feasibility-conflict-report.md
```

---

## 16. 执行顺序建议

### 16.1 阶段 4.0-A：仓库事实核查与模型清单

目标：

```text
确认阶段 3 输入可用；
确认阶段 1 验证器可用；
确认外部后端状态；
确认哪些后端能立即预检，哪些后端阻塞。
```

产出：

```text
model_inventory.csv
backend_preflight_report.md
blocked_backends.md
```

### 16.2 阶段 4.0-B：输入适配审计

目标：

```text
把 phase4_mask_seed.csv 中的参考掩码转成各后端输入。
```

产出：

```text
adapter_input_manifest.csv
selected_cases_preflight.csv
```

### 16.3 阶段 4.0-C：5 个样本预检

优先预检：

```text
规则型局部构象修复；
DiffSBDD 条件模型局部补全；
DiffSBDD 条件模型全配体重新采样。
```

同时调研：

```text
DiffSBDD 联合模型；
DiffDec 单取代基模型。
```

### 16.4 阶段 4.0-D：40 个样本正式小规模对比

只有预检通过后再做。

目标：

```text
比较可运行后端在参考掩码条件下的修复能力。
```

产出：

```text
phase4_0_small_scale_summary.json
phase4_0_completion_audit.md
```

---

## 17. 硬约束

阶段 4.0 必须遵守：

```text
1. 不训练模型；
2. 不微调模型；
3. 不修改 DiffSBDD / DiffDec 原始去噪过程；
4. 不声称 H_clash 或碰撞热区进入生成过程；
5. 只用参考掩码；
6. 不做随机掩码、自动掩码、参考掩码正式对照；
7. 不做多轮迭代修复；
8. 不把 Vina / docking score 作为主指标；
9. 不修改阶段 2、阶段 2.5、阶段 3 历史结果；
10. 不覆盖 phase4_mask_seed.csv；
11. 候选无法读取、映射失败、连接点失败、后端失败都不能从主指标分母中剔除；
12. 外部源码、模型权重、大量候选 SDF 和日志缓存不提交 Git；
13. 若方案与仓库事实冲突，先生成冲突报告。
```

---

## 18. 禁止修改范围

阶段 4.0 执行中禁止修改：

```text
reports/phase2_injection/*
reports/phase2_5_model_induced_audit/*
reports/phase3_label_provenance_audit/phase4_mask_seed.csv
reports/phase3_label_provenance_audit/summary.json
reports/phase3_label_provenance_audit/phase3_final_experiment_report.md

data/benchmarks/clashrepairbench_rg_artificial/v0_1/manifest.parquet
data/benchmarks/clashrepairbench_rg_artificial/v0_1/samples/*
data/benchmarks/clashrepairbench_rg_artificial/v0_1/ligands/*
```

允许读取这些文件，但不得回写、重命名、覆盖或重生成。

允许新增或修改的范围由 Codex 在 `/plan` 中结合仓库事实提出。建议新增范围包括：

```text
configs/phase4_0_backend_feasibility.yaml
scripts/phase4_0_backend_feasibility.py
src/clash2feedback/generation/*
src/clash2feedback/verifier/phase4_adapter.py
reports/phase4_0_backend_feasibility/*
runs/phase4_0_backend_feasibility/*
tmp/20260514/*
```

---

## 19. 风险与局限

| 风险 | 说明 | 处理 |
|---|---|---|
| 参考掩码下也修不好 | 后端能力不足或输入适配失败 | 不进入 4.1，先修后端或换后端 |
| DiffSBDD 输出无法接回 anchor | 原版补全不保证连接 | 连接点失败，计为候选失败 |
| DiffSBDD 联合模型不兼容 inpaint | 接口可能不同 | 记录 blocked，不阻塞条件模型 |
| DiffDec 环境或检查点不可用 | 本地未配置 | 必须调研并写 blocked，不阻塞主线 |
| DiffDec 取代基大小不可控 | 官方脚本可能不支持 | 记录实际大小，后续包装器 |
| 规则型方法在 easy_rotation 上过强 | 可能反向恢复人工扰动 | 按 injection_mode 分层解释 |
| 全配体重采样无碰撞但漂移大 | 不是局部修复 | 单独作为全局对照 |
| 输出原子顺序变化 | 不能直接按原索引比 RMSD | 使用固定结构匹配和映射适配器 |
| 只看无碰撞导致假成功 | 可能飞出口袋或破坏骨架 | 必须通过完整可靠验证器 |
| 40 case 含 train 样本 | 不是 held-out 泛化测试 | 明确写成 backend feasibility audit |
| 多后端成本不一致 | 规则型 proposal 便宜，生成式候选贵 | 统一最终 K=8，并记录 proposal_count 和 cost_per_success |

---

## 20. 完成标准

阶段 4.0 完成时，应满足：

```text
[ ] 已核查当前分支、commit、git status；
[ ] 已核查 main / 当前分支是否包含阶段 3 产物；
[ ] 已核查 phase4_mask_seed.csv 可用性和关键字段；
[ ] 已生成 model_inventory.csv；
[ ] 已生成 selected_cases_preflight.csv；
[ ] 已生成 selected_cases.csv；
[ ] 已完成规则型局部构象修复预检；
[ ] 已完成 DiffSBDD 条件模型局部补全预检；
[ ] 已完成 DiffSBDD 条件模型全配体重新采样预检；
[ ] 已调研 DiffSBDD 联合模型并记录状态；
[ ] 已调研 DiffDec 单取代基模型并记录状态；
[ ] blocked 后端已写入 blocked_backends.md；
[ ] 所有可运行后端均输出 candidate_manifest.csv；
[ ] 所有候选均经过统一验证器或记录适配失败原因；
[ ] 已输出 verifier_outcome.csv；
[ ] 已输出 backend_comparison.csv；
[ ] 已输出 failure_cases.csv；
[ ] 已输出 phase4_0_preflight_summary.json；
[ ] 已输出 phase4_0_small_scale_summary.json；
[ ] 已输出 phase4_0_completion_audit.md；
[ ] 未修改禁止修改范围内的历史文件；
[ ] compileall / pytest 通过，或清楚说明无法运行原因。
```

进入阶段 4.1 的建议条件：

```text
至少一个局部修复后端在参考掩码下有非零且可解释的样本级可靠修复率；
候选生成、读取、验证链路稳定；
固定结构匹配和连接点不是大面积失败；
失败原因可分类；
报告中能明确推荐阶段 4.1 主后端。
```

如果参考掩码下所有后端都无法产生可靠修复候选，阶段 4.0 的结论应是：

```text
当前瓶颈在修复后端或输入输出适配，不应进入阶段 4.1 正式掩码对照。
```

---

## 21. 冲突处理规则

如果本方案与仓库事实不一致，以仓库事实为准。Codex 不得强行修改历史结果以匹配方案。

若发现冲突，必须先生成：

```text
tmp/20260514/phase4-0-backend-feasibility-conflict-report.md
```

报告包含：

```text
冲突项；
方案文档表述；
仓库实际情况；
涉及文件；
影响范围；
建议处理方式；
是否需要人工确认。
```

低风险差异可在计划中提出适配：

```text
字段名不同但语义一致；
路径名不同但文件存在；
报告文件名不同但内容可映射；
schema 多了无害字段。
```

高风险冲突必须等待人工确认：

```text
phase4_mask_seed.csv 缺失；
关键掩码字段缺失；
参考掩码来源与方案不一致；
阶段 3 数字与报告冲突；
需要修改阶段 2 / 3 历史结果才能推进；
验证器成功标准与阶段 1 口径冲突；
DiffSBDD / DiffDec 接入口径与 external_baselines 冲突；
实验主结论口径需要改变。
```

---

## 22. 本地 Codex 后续计划要求

本文件不替代本地 Codex 执行计划。

本地 Codex 必须先进入 `/plan` 模式，只规划不执行，并生成：

```text
tmp/20260514/phase4-0-backend-feasibility-codex-goal-exec-plan.md
```

执行计划必须包含：

```text
仓库事实核查；
字段/实现映射；
具体执行步骤；
预计新增和修改文件；
测试计划；
禁止修改范围核查方式；
冲突项；
阻塞项；
后续 /goal 执行建议。
```

若发现方案与仓库事实冲突，先生成：

```text
tmp/20260514/phase4-0-backend-feasibility-conflict-report.md
```

不要继续执行冲突部分。

---

## 23. 最终总结

阶段 4.0 的核心不是证明自动掩码准确，也不是证明生成模型整体更强，而是验证：

```text
在已知正确修复区域的条件下，局部蛋白质—配体碰撞失败候选是否能够被不同修复后端可靠救回。
```

本阶段最重要的结论应围绕：

```text
哪个后端能接入；
哪个后端能生成候选；
哪个后端能保持固定结构和连接点；
哪个后端能消除旧碰撞且没有新严重碰撞；
哪个后端值得进入阶段 4.1。
```

一句话：

> **阶段 4.0 先证明“给对区域能不能修”；阶段 4.1 再另行讨论“自动选区域是否比随机选区域更有用”。**
