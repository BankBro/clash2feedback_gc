# Clash2Feedback-GC：第一篇论文实验方案

> 版本：2026-05-05 一致性修订版  
> 推荐定位：方法验证型短论文 / workshop 论文 / BIBM 风格短论文  
> 长期推荐版本：**冻结生成器 + operational mask policy + 规则适配器 + 可靠验证器**, 后续在阶段 5/6/7 再加入修复排序器、学习型纠错器和学习型反馈适配器。


## 统一实现约定

四个文档统一采用下面的工程口径，后续实现时以此为准。

| 项 | 统一口径 |
|---|---|
| 项目根目录 | `clash2feedback_gc/` |
| Python 包名 | `src/clash2feedback/` |
| 静态说明文档 | `docs/`，本文件和另外三个 Markdown 都放这里 |
| 实验报告 | `reports/`，只放运行后生成的表格、图、摘要，不放方案文档 |
| 运行产物 | `runs/`，放日志、模型 checkpoint、生成候选原始输出等较重产物 |
| 数据产物 | `data/`，放 raw、processed、splits、benchmarks、candidate pools |
| 命令行入口 | `scripts/phaseN_*.py` |
| 阶段 0 processed 版本 | `data/processed/v0_1/` |
| 阶段 0 split 版本 | `data/splits/v0_1/` |
| 人工失败基准 | `data/benchmarks/clashrepairbench_rg_artificial/v0_1/` |
| 候选池 | `data/candidate_pools/v0_1/` |

特别注意：`reports/` 不是文档目录；`docs/` 才是存放这四个 Markdown 方案文件的地方。



## 0. 一句话总结

第一篇论文不研究“配体实验上是否一定能很好结合蛋白”，也不主攻结合亲和力预测。

第一篇论文研究的是：

> **对结构基础生成模型产生的局部碰撞失败候选，能否通过结构化失败诊断反馈，提高局部修复成功率，并保持 scaffold 和非失败区域稳定。**

主指标应是：

```text
Reliable Repair Yield
```

而不是：

```text
Binding Success Rate
```

---

## 1. 第一篇论文的边界

### 1.1 做什么

第一篇做：

1. 构建取代基级局部碰撞修复数据；
2. 审计人工失败数据的标签来源和 attribution-derived mask policy；
3. 定义结构化修复协议；
4. 把协议翻译成冻结生成器可执行控制；
5. 生成局部修复候选；
6. 用可靠验证器判断旧碰撞是否修复；
7. 阶段 4.1 稳定后, 可在阶段 5 用排序器挑选候选。

### 1.2 不做什么

| 不做 | 原因 |
|---|---|
| 不证明实验结合成功 | 这需要实验亲和力、活性或共晶结构证据 |
| 不主攻结合亲和力预测 | 会偏离局部修复主线 |
| 不重新训练通用三维生成器 | 工程和资源风险高 |
| 不做完整强化学习 | 任务范围过大 |
| 不同时处理所有失败类型 | 第一篇只聚焦局部 R-group clash |
| 不把碰撞检测本身当主要创新 | 现有工具已能做检测和过滤 |

第一篇主任务是 `single-region R-group clash repair`. Multi-region clash, scaffold clash, global pose failure, covalent ligand, metal coordination 等情况第一版应识别并标记为 `unsupported` 或 `reject`, 不进入 single-R-group repair 主指标. 后续可通过 expand-mask, sequential repair, full resampling, multi-label critic 或 learned adapter 逐步处理.

### 1.3 BIBM 版收敛口径

若以 BIBM full paper 为目标, 第一版不主打完整 Clash2Feedback-GC 大框架, 而应收敛成 protein-ligand steric clash 定位与局部修复的小闭环:

```text
给定一个在 pocket 中发生局部 protein-ligand steric clash 的 failed ligand candidate,
用 attribution-derived operational mask policy 产生 predicted repair mask,
只修该局部区域,
并验证 old clash resolved, no new clash, scaffold preserved, non-edit region preserved.
```

BIBM 版最小实验包:

| 模块 | 最低要求 |
|---|---|
| benchmark | injected split + small natural / model-induced split |
| mask policy | phase2 label provenance audit + attribution-derived predicted mask policy |
| repair | local torsion / conformer repair, R-group resampling 可作为增强 |
| verifier | old clash resolved + no new clash + scaffold / non-edit RMSD |
| baselines | hard filter, full resampling, random mask, predicted mask, oracle mask |
| main metric | Reliable Repair Yield |

主趋势应围绕可靠修复率, scaffold 保持, 非编辑区保持, no-new-clash rate 和 cost per success 展开. Docking score 不作为主指标.

---

## 2. 第一篇核心实验问题

### RQ1：Phase2 supported set 的标签依赖和循环验证风险是什么？

阶段 2 的 `target_rgroup` 是人工扰动标签, 但 `supported_single_rgroup` 是经过 detector / attribution / target-dominance gates 过滤后的 clean local repair substrate. 因此第一篇不能把 supported 主集上的 Top-1 / Top-3 写成无偏 locator accuracy, 必须先回答 label provenance 和 circularity risk.

### RQ2：Predicted mask policy 是否有 downstream repair utility？

阶段 4 的 predicted mask 来自现有 `detect_clashes()` + `attribute_clashes_to_rgroups()` 和 `dominant_valid_rgroup` / `top_valid_rgroups`. 它是 operational mask policy, 不是 ground truth.

核心比较是:

```text
Random mask + same backend + same candidate budget
Predicted mask + same backend + same candidate budget
Oracle mask + same backend + same candidate budget
```

要回答:

> Predicted mask repair 是否比 size-matched Random mask repair 更容易产生 reliable repaired candidates?

### RQ3：Local repair 是否比 full resampling 更能保持局部性？

比较局部受约束修复和 full-ligand resampling:

```text
old clash resolved
no new severe clash
scaffold RMSD
non-mask RMSD
anchor consistency
fixed-region preservation
```

### RQ4：若实现 guided sampling, clash heatmap 是否能提高候选生成效率？

RQ4 只有在实现 clash penalty / hot region guidance 并改采样过程后, 才能作为主实验. 在 plain DiffDec / DiffSBDD backend 下, `H_clash` 只能进入 verifier / selector / adapter 输入, 不能声称直接指导 diffusion denoising.

---

## 3. 实验总流程

第一篇完整流程：

\[
L_f
\rightarrow
\text{phase3 provenance audit / mask seed}
\rightarrow
\mathcal P_t^{repair}
\rightarrow
A_{rule}
\rightarrow
u_t
\rightarrow
G_{\theta_0}
\rightarrow
\{L_r^{(i)}}\}_{i=1}^K
\rightarrow
\text{verifier / optional selector}
\rightarrow
R
\rightarrow
\text{success / fail}
\]

| 模块 | 第一篇处理方式 |
|---|---|
| \(G_{\theta_0}\) | 冻结结构基础生成器，第一版建议 DiffSBDD |
| phase3 audit | label provenance audit, circularity risk audit, construction consistency check, phase4 mask seed generation |
| predicted mask policy | attribution-derived operational mask policy, 不是 ground truth |
| \(C_\phi^{diag}\) | 后续阶段 6 的 learned diagnostic head, 不属于当前阶段 3 / 4.0 |
| \(C_\phi^{rank}\) | 后续阶段 5, 需在阶段 4.1 有稳定候选结果后再训练 |
| \(A_{rule}\) | 必须有，作为强基线 |
| \(A_\psi\) | 后续阶段 7 增强实验 |
| \(R\) | 规则 + 物理几何验证器 |
| 生成器微调 | 不做 |
| 强化学习 | 不做 |

---

## 4. 数据集设计

建议构建：

> **ClashRepairBench-RG：取代基级蛋白质—配体局部碰撞修复基准**

其中 RG 指 R-group。

| 数据 | 统一保存位置 | 用途 |
|---|---|---|
| clean complexes | `data/processed/v0_1/` | 从原始复合物筛出的干净基础样本 |
| 人工注入局部碰撞样本 | `data/benchmarks/clashrepairbench_rg_artificial/v0_1/` | controlled local repair substrate, 用于标签溯源、mask seed 和局部修复评估 |
| 生成器诱导失败样本 | `data/benchmarks/model_induced/v0_1/` | 验证真实生成失败场景下能否修复 |
| 修复候选池 | `data/candidate_pools/v0_1/` | 训练排序器和反馈适配器 |

模型诱导失败相关实验拆成两层: 阶段 2.5 是 model-induced failure audit, 只做 all generated samples taxonomy 和 phase2 coverage proxy; 阶段 8 才做 model-induced repair evaluation 和 repair outcome. 当前阶段 2.5 最终报告显示, frozen DiffSBDD de novo complete-ligand audit 中 `single_rgroup_clash` 很少, 仅 `1 / 200` unique candidates. 因此 BIBM 版应把阶段 2 artificial `supported_single_rgroup` 表述为 controlled local-repair testbed, 不能声称真实 de novo failures 主要是 R-group clash, 也不能把阶段 2.5 写成 repair success evidence.

---

## 5. 数据来源选择

推荐路线：

```text
DiffSBDD example：测试读入和接口
CrossDocked 小子集：阶段 0 和第一版主数据
PDBBind / RCSB PDB 少量样本：外部真实性检查，可选
```

### 为什么主数据建议用 CrossDocked 小子集

| 原因 | 说明 |
|---|---|
| 与结构基础生成模型常用格式接近 | 方便后续接 DiffSBDD / Pocket2Mol 系列处理方式 |
| 有蛋白和配体三维坐标 | 可直接做 pocket、clash 和局部修复 |
| 数据量足够 | 方便筛出 clean complex |
| 第一版可控 | 不需要一开始处理全量 |

但需要强调：

> CrossDocked 是候选数据源，不是完全无碰撞真值库。

因为很多样本来自 docking 姿态，可能已有局部碰撞或几何异常。因此必须自己筛选 clean complex。

---

## 6. clean complex 过滤标准

构建基准前，先筛 clean complex。

建议条件：

| 条件 | 建议 |
|---|---|
| protein 和 ligand 成对 | 必须来自同一个 complex |
| 坐标系一致 | ligand 周围 6–8 Å 内有 pocket atoms |
| ligand 合法 | RDKit sanitize 通过 |
| ligand 有三维坐标 | SDF 中有 conformer |
| ligand 重原子数 | 15–60 |
| 原始严重碰撞 | 无明显 severe protein-ligand clash |
| scaffold 可拆 | Murcko scaffold 成功 |
| R-groups 可拆 | 至少 2 个 R-groups |
| anchor | 第一版优先单锚点 R-group |
| 特殊情况 | 共价配体、金属配合物、多片段盐、macrocycle 先排除 |

阶段 0 先从 40–50 个候选 complex 中筛出至少 20 个 clean complex. 20–30 是第一批最低目标, 不是 clean pool 上限. 如果 clean pool target 分布不均, 保留完整 clean pool, 同时派生 target-balanced subset 作为阶段 1-3 mini-loop 的轻量 benchmark.

第一篇最小可跑通版本可以扩大到：

| 数据 | 数量 |
|---|---:|
| clean complexes | 80–120 个 |
| 人工失败样本 | 300–600 个 |
| 模型诱导失败样本 | 50–100 个 |

阶段 2.5 应预留两张报告表: `Phase2.5 model-induced failure taxonomy` 和 `Artificial vs model-induced distribution gap`. 字段包括 `ligand_only_invalid`, `valid_no_severe_clash`, `single_rgroup_clash`, `multi_region_clash`, `scaffold_clash`, `global_pose_failure`, `rgroup_unattributable`, `local_rgroup_repair_possible`.

投稿版本可进一步扩大，但不建议一开始追求大规模。

---

## 7. scaffold 与 R-groups 拆分

我们把配体人为拆成：

\[
L=S+\mathcal R
\]

其中：

| 部分 | 含义 |
|---|---|
| \(S\) | scaffold，配体核心骨架 |
| \(\mathcal R\) | R-groups，接在骨架上的取代基集合 |
| anchor | R-group 接回 scaffold 的连接点 |

注意：

- scaffold 不是天然唯一的；
- 第一版固定使用 Murcko scaffold；
- R-groups 可以有多个；
- 第一版优先处理单锚点 R-group；
- 多锚点 linker 可以作为后续扩展。

拆分目标不是做完美药物化学定义，而是服务局部修复：

> 找出哪个局部取代基发生碰撞，并只修改它。

---

## 8. 人工局部碰撞注入

人工注入失败样本用于构建 controlled local repair substrate. `target_rgroup` 是人工扰动标签, 但 `supported_single_rgroup` 会经过 detector / attribution / target-dominance gates 过滤, 因而不能直接当作 independent locator benchmark。

### 方式一：围绕 anchor bond 旋转

对取代基 \(R_k\) 围绕 scaffold-R-group 连接键旋转：

\[
\theta \in \{60^\circ,120^\circ,180^\circ,240^\circ,300^\circ}\}
\]

保持：

- scaffold 不动；
- 连接键不断；
- R-group 内部几何不变；
- 只改变局部空间占位。

这是第一版最稳的注入方式。

注意: anchor bond rotation 构造的是 controlled synthetic failed pose, 用于建立标签来源清楚的局部碰撞样本, 主要服务 detector, provenance audit, mask seed 和 verifier 的早期验证. 它不应被表述为真实热力学稳定结合构象.

第一版 rotation / torsion injection 之后, 必须做 ligand-only 合理性检查: RDKit sanitize pass, anchor bond 是合法 rotatable single bond, ligand internal severe clash = 0, anchor integrity pass, chirality preserved, 可选记录 RDKit MMFF / UFF energy delta. MMFF / UFF 仅作为 ligand-only energy filter, 不作为生成或修复方法, 也不用于 whole complex minimization。

第一版 rotation injection 只允许围绕化学上可旋转的 single bond 进行. 以下情况应排除或标记 unsupported:

- ring bond；
- double bond；
- amide-like bond；
- 强共轭受限 bond；
- 多锚点 linker；
- 旋转后 ligand internal severe clash；
- 旋转后 scaffold 或非目标 R-group 明显漂移；
- 旋转后变成 multi-region clash。

### 方式二：局部构象扰动

扰动失败取代基内部可旋转键，但固定 scaffold 和 anchor。

### 方式三：合法片段替换

用相似大小或稍大的片段替换原 R-group，更接近“取代基太大导致 clash”的情况，但工程复杂，建议作为增强。

### 人工失败集分层

人工失败样本建议分层保存和报告:

| split | 构造方式 | 用途 |
|---|---|---|
| `easy_rotation` | single R-group anchor bond rotation | detector debug, provenance audit 和基础 substrate |
| `torsion_perturb` | 目标 R-group 内部 rotatable bond 扰动 | 更接近局部构象错误 |
| `directed_clash` | 朝 protein hotspot 方向定向扰动 | 构造 mild / medium / severe 难度 |
| `fragment_replace` | phase2b 暂缓 | 更接近“取代基太大导致 clash” |
| `hard_multi_region` | phase2b 暂缓 | stress test / reject test |

第一篇主结果可以聚焦 `single-region dominant` 样本; hard split 应单独报告, 不应混入主指标.

---

## 9. 人工失败样本保留条件

人工失败样本主集 `supported_single_rgroup` 必须满足：

\[
\text{LigandValid}=1
\]

\[
\text{LigandInternalValid}=1
\]

\[
\text{AnchorIntegrity}=1
\]

\[
\text{EnergyDeltaOK}=1\ \text{或 unavailable-recorded}
\]

\[
\text{ScaffoldStable}=1
\]

\[
\text{LocalClash}=1
\]

\[
\text{SingleRegionDominant}=1
\]

建议阈值：

| 条件 | 阈值建议 |
|---|---:|
| scaffold RMSD | < 0.3 Å |
| 非扰动区域 RMSD | < 0.5 Å |
| 目标 R-group clash score / 总 clash score | > 0.7 |
| 分子内部严重碰撞 | 无 |
| protein-ligand severe clash | 至少 1 个 |
| R-group 重原子数 | 2–15 |

人工失败集不只保存 supported / hard split, 还应保存 `invalid_conformer`, `near_miss_contact`, `duplicate_removed` 和 `unsupported`, 这些不进入主评估集, 但必须统计原因。阶段 2 benchmark construction 不得使用 predicted dominant R-group 是否等于 target R-group 作为唯一保留条件, 所有 injected variants 必须继承 base complex split。

阶段 2 标签使用边界:

- `target_rgroup` 是人工选择并扰动的 R-group.
- `supported_single_rgroup` 是经过 ligand quality, detector, attribution, `target_score_ratio_valid`, non-target / scaffold no-severe 和 max-depth gates 后的 clean local repair subset.
- `target_score_ratio_valid` 来自 attribution-derived valid R-group scores.
- supported 主集上的 Top-1 / Top-3 只能作为 construction consistency check, 不能作为论文主贡献的 independent localization benchmark.

---

## 10. 碰撞定义和标签

对配体原子 \(a_i\) 和蛋白原子 \(p_j\)，定义碰撞深度：

\[
c_{ij}
=
\max
\left(
0,
 r_i^{vdW}+r_j^{vdW}-\delta-d(a_i,p_j)
\right)
\]

其中：

- \(r_i^{vdW}\)：配体原子范德华半径；
- \(r_j^{vdW}\)：蛋白原子范德华半径；
- \(d(a_i,p_j)\)：原子间距离；
- \(\delta\)：容忍余量，建议初始设为 0.4 Å。

原始碰撞集合：

\[
E^{old}=\{(a_i,p_j):c_{ij}>0}\}
\]

R-group 级碰撞分数：

\[
Score(R_k)
=
\sum_{a_i\in R_k}
\sum_{p_j\in P}
c_{ij}^2
\]

尺寸归一化：

\[
Score_\alpha(R_k)
=
\frac{Score(R_k)}{|R_k|^\alpha}
\]

建议：

\[
\alpha=0.5
\]

人工注入标签和 predicted mask 必须分开定义：

\[
M_{injected}=\text{target\_rgroup}
\]

\[
M_{pred}=\arg\max_k Score_\alpha(R_k)
\]

其中 `M_injected` / `target_rgroup` 是人工注入时被扰动的 R-group. `M_pred` 只是 attribution-derived operational mask policy 的输出, 不是 independent ground truth. `Score_alpha` 不能定义 independent ground truth.

在 `supported_single_rgroup` 上, `M_pred` 与 `target_rgroup` 的一致性只能作为 construction consistency check. 因为该 split 已经过 detector / attribution / `target_score_ratio_valid` gate 过滤, 不能作为 independent locator benchmark.

---

## 11. 修复建议协议

第一篇使用精简协议：

\[
\mathcal P_t^{repair}
=
(
M_t,
C_t^{keep},
H_t^{clash},
s_t,
\rho_t,
\tau_t,
K_t,
A_t
)
\]

| 字段 | 含义 |
|---|---|
| \(M_t\) | 预测失败 R-group |
| \(C_t^{keep}\) | scaffold + 非失败 R-groups |
| \(H_t^{clash}\) | 蛋白侧旧碰撞热区 |
| \(s_t\) | 碰撞严重度 |
| \(\rho_t\) | 修复模式 |
| \(\tau_t\) | 修复强度 |
| \(K_t\) | 候选数 |
| \(A_t\) | anchor 信息 |

修复模式：

\[
\rho_t
\in
\{
\text{low-noise},
\text{mid-noise},
\text{high-noise},
\text{inpaint},
\text{expand-mask},
\text{reject}
\}
\]

---

## 12. 反馈适配器

### 12.1 规则版反馈适配器

规则版作为强基线。

设严重度归一化：

\[
\tilde s_t=\frac{s_t}{|M_t|+\epsilon}
\]

在验证集上计算分位数：

\[
q_{33},q_{66},q_{90}
\]

规则：

| 条件 | 动作 |
|---|---|
| \(\tilde s_t < q_{33}\) | low-noise |
| \(q_{33}\leq \tilde s_t < q_{66}\) | mid-noise |
| \(q_{66}\leq \tilde s_t < q_{90}\) | high-noise |
| \(\tilde s_t \geq q_{90}\) 且单区域主导 | inpaint 或 expand-mask |
| 多区域严重碰撞 | reject |
| scaffold 本身严重 clash | reject |

### 12.2 学习型反馈适配器

学习型反馈适配器属于后续阶段 7. 当前阶段 3 不训练 learned diagnostic head, 阶段 4.0 也不把 learned adapter 作为必做项. 只有阶段 4.1 的 Random / Predicted / Oracle repair loop 产出稳定 candidate outcomes 后, 才适合推进排序器和学习型适配器.

长期输入：

\[
x_t=(M_t,H_t^{clash},s_t,\text{R-group features},\text{dominant ratio})
\]

输出：

\[
A_\psi(x_t)\rightarrow p(\rho_t),\hat\tau_t,\hat K_t
\]

第一篇可以简化为分类：

\[
\rho_t\in
\{\text{low},\text{mid},\text{high},\text{inpaint},\text{expand},\text{reject}}\}
\]

监督标签构造：

1. 对每个失败样本枚举控制集合 \(\mathcal U\)；
2. 每个控制生成 \(K_0\) 个候选；
3. 用验证器计算每个控制的平均修复价值；
4. 选择修复价值最高且编辑成本最低的控制作为标签。

\[
u^*=\arg\max_{u\in\mathcal U}\bar U(u)
\]

---

## 13. 局部再生成实现

第一版建议准备两档实现。

### 13.1 固定拓扑局部再生成

特点：

- 分子二维拓扑不变；
- scaffold 和非失败区域固定；
- 只对失败 R-group 的三维坐标或构象做局部加噪—去噪；
- 适合轻中度 clash。

这是第一篇主实现，工程风险低。

### 13.2 R-group inpainting

特点：

- 删除或遮住失败 R-group；
- 固定 scaffold、非失败 R-groups 和 anchor；
- 重新生成局部片段；
- 可允许原子数变化。

这是增强实现。如果生成器接口不稳定，不作为唯一主实现。

---

## 14. 生成器选择

第一篇建议：

| 角色 | 推荐 |
|---|---|
| 主生成器 | DiffSBDD |
| 可迁移性小实验 | PocketXMol / Diffleop / DiffDec，选一个即可 |
| full resampling baseline | TargetDiff / Pocket2Mol / VoxBind，选一个即可 |

但第一篇不建议做大规模多生成器对比。

论文表述要稳：

> 第一版使用 DiffSBDD 作为冻结生成器基座；Clash2Feedback-GC 的诊断协议和验证器尽量与生成器解耦，具体生成器通过反馈适配器接收 fixed atoms、editable mask、anchor、repair strength 等控制。

DiffDec / DiffSBDD plain backend 在未改 sampling / denoising loop 时, 只能表述为 local constrained resampling 或 candidate inpainting backend. `H_clash`, old-clash-resolved 和 no-new-clash 主要由 verifier / selector / adapter 使用. 只有实现 clash penalty / hot region guidance 并修改采样过程后, 才能声称 `H_clash` 进入生成过程。

---

## 15. 可靠验证器

候选 \(L_r\) 通过验证，当且仅当满足：

| 条件 | 建议阈值 |
|---|---:|
| 原碰撞消除 | 原始 clash score 降到 10% 以下 |
| 无新严重碰撞 | severe new clash 数量为 0 或低于阈值 |
| scaffold 保持 | scaffold RMSD < 0.5 Å |
| 非编辑区域保持 | non-edit RMSD < 0.8 Å |
| 配体几何合法 | RDKit / PoseBusters 风格检查通过 |
| 修改局部性 | edit region 外修改比例 < 20% |
| 配体仍在 pocket | pocket contact 保持合理 |
| docking score 未明显恶化 | 可选，不作为主指标 |

成功条件不要写成“结合成功”，而应写成：

```text
Reliable Repair = old clash resolved + no new clash + geometry valid + keep region stable
```

若 full receptor 可用, 建议报告两套可靠修复率:

| 指标 | 含义 |
|---|---|
| `pocket-level Reliable Repair Yield` | 在 phase0 pocket8 / pocket10 局部 receptor 下通过 reliable repair verifier |
| `full-receptor checked Reliable Repair Yield` | 在 pocket-level 通过后, 再在 full receptor dynamic shell 下无新 severe clash |

当前 pocket10 数据可支持 pocket-level 修复验证; full receptor checked 结果取决于是否能获取并对齐完整蛋白结构.

---

## 16. 对照方法

| 方法 | 具体做法 | 目的 |
|---|---|---|
| Drop | 失败候选直接丢弃 | 说明传统流程浪费候选 |
| Full resampling | 同一 pocket 重新生成完整分子 | 比较完全重来和局部修复 |
| Random mask | size-matched 随机选 R-group 重画 | mask policy 下游价值的负对照 |
| Predicted mask | attribution-derived operational mask policy | 评估 predicted mask 是否优于 random |
| Structured predicted protocol | predicted mask + keep / anchor / severity / rule adapter | 评估结构化控制是否带来额外收益 |
| Learned critic + rule adapter | 后续阶段 6 学习型纠错器 + 规则适配器 | 后续增强, 不属于当前阶段 3 / 4.0 |
| Learned critic + learned adapter | 后续阶段 6/7 学习型纠错器 + 学习型适配器 | 后续增强, 不属于当前阶段 3 / 4.0 |
| Full method + ranker | 后续阶段 5/6/7 完整方法 | 阶段 4.1 稳定后再推进 |
| Oracle mask / protocol | 人工 `target_rgroup` 对应区域 + 最优控制 | 上限, 不是 predicted mask 的 ground truth 替代物 |

期望趋势：

\[
\text{Random mask}
<
\text{Predicted mask}
<
\text{Structured predicted protocol}
 \leq
\text{Oracle}
\]

长期阶段 5/6/7 后, 可再扩展为:

\[
\text{Structured predicted protocol}
<
\text{Learned critic + adapter}
<
\text{Full method}
<
\text{Oracle}
\]

---

## 17. 消融实验

### 17.1 协议字段消融

| 消融 | 保留信息 | 目的 |
|---|---|---|
| Mask only | \(M_t\) | 只有编辑区域是否不够 |
| Mask + Keep | \(M_t,C_t^{keep}\) | 保持约束是否减少结构漂移 |
| + Severity | 加 \(s_t,\tau_t\) | 自适应强度是否有用 |
| + Clash Heatmap | 加 \(H_t^{clash}\) | 旧错误感知是否有用 |
| + Repair Mode | 加 \(\rho_t\) | 修复动作选择是否有用 |
| Full Protocol | 全部 | 完整协议效果 |

### 17.2 模块消融

| 消融 | 目的 |
|---|---|
| 不训练纠错器, 用 operational mask policy | 后续阶段 6 对比 learned diagnostic head 是否提升 |
| 不训练适配器, 用规则适配器 | 后续阶段 7 看适配器是否可学习 |
| 不用排序器, 随机选候选 | 后续阶段 5 看排序器是否减少候选预算 |
| 排序器不输入反馈 | 看结构化反馈是否进入评价 |
| 排序器只输入候选结构 | 防止退化成普通分子筛选器 |

---

## 18. 评价指标

### 18.1 诊断指标

| 指标 | 含义 |
|---|---|
| R-group Top-1 / Top-3 construction consistency | 仅在 phase2 supported 主集上检查 attribution 与构造标签的一致性, 不作为 independent locator accuracy |
| Predicted mask coverage | operational mask policy 可输出 repair mask 的比例 |
| Circularity risk level | 评估集 gate 与 attribution policy 共享依赖的风险 |
| Atom-level F1 | 失败原子级定位质量 |
| Heatmap AUPRC | 蛋白碰撞热区预测质量 |
| Severity MAE | 严重度预测误差 |

### 18.2 修复指标

| 指标 | 含义 |
|---|---|
| Old Clash Resolved Rate | 原碰撞消除率 |
| No New Clash Rate | 无新严重碰撞率 |
| Reliable Repair Yield | 可靠修复率，主指标 |
| Geometry Valid Rate | 几何合法率 |
| Scaffold RMSD | scaffold 保持情况 |
| Non-edit RMSD | 非编辑区域保持情况 |
| Edit Compliance | 是否主要修改指定区域 |
| Keep Compliance | 固定区域是否保持 |
| Average Candidates to Success | 成功平均需要多少候选 |

### 18.3 排序指标

| 指标 | 含义 |
|---|---|
| Top-1 Repair Hit | 排名第一候选是否通过验证 |
| Top-3 Repair Hit | 前三是否有通过验证候选 |
| PR-AUC | 成功样本稀少时更重要 |
| NDCG | 排序质量 |

---

## 19. 推荐实验表格

### 表 1：数据集统计

| Split | clean complexes | 人工失败样本 | 模型诱导失败样本 | 平均 R-group 数 | 平均 clash score |
|---|---:|---:|---:|---:|---:|
| Train |  |  |  |  |  |
| Val |  |  |  |  |  |
| Test-artificial |  |  |  |  |  |
| Test-model-induced |  |  |  |  |  |

### 表 2：标签溯源与 mask policy consistency

| 方法 / 审计项 | Top-1 consistency | Top-3 consistency | Circularity risk | Mask seed coverage | 备注 |
|---|---:|---:|---:|---:|---:|
| Rule attribution policy |  |  |  |  | construction consistency only |
| Learned critic |  |  |  |  | 阶段 6 后续项, 若实现需另设无泄漏评估 |

### 表 3：人工失败集修复

| 方法 | Old Resolved ↑ | No New Clash ↑ | Reliable Repair ↑ | Scaffold RMSD ↓ | Avg Candidates ↓ |
|---|---:|---:|---:|---:|---:|
| Full resampling |  |  |  |  |  |
| Random mask |  |  |  |  |  |
| Predicted mask |  |  |  |  |  |
| Structured predicted protocol |  |  |  |  |  |
| Learned critic + rule adapter |  |  |  |  | 后续阶段 6 |
| Learned critic + learned adapter |  |  |  |  | 后续阶段 7 |
| Full method + ranker |  |  |  |  | 后续阶段 5/6/7 |
| Oracle |  |  |  |  |  |

### 表 4：模型诱导失败集修复

| 方法 | Old Resolved ↑ | No New Clash ↑ | Reliable Repair ↑ | Geometry Valid ↑ | Avg Candidates ↓ |
|---|---:|---:|---:|---:|---:|
| Full resampling |  |  |  |  |  |
| Random mask |  |  |  |  |  |
| Predicted mask |  |  |  |  |  |
| Structured predicted protocol |  |  |  |  |  |
| Full method |  |  |  |  |  |

---

## 20. 反馈遵循实验

这个实验证明生成器不是“碰巧修好”，而是确实按反馈修改。

### 编辑区域遵循率

\[
\text{EditCompliance}
=
\mathbb I[
\text{changed atoms mostly inside }\mathcal M_t^{edit}
]
\]

### 保持区域遵循率

\[
\text{KeepCompliance}
=
\mathbb I[
\mathrm{RMSD}(C_t^{keep})<\epsilon
]
\]

### 严重度响应曲线

检查：

\[
s_t \uparrow
\Rightarrow
\tau_t \uparrow
\Rightarrow
\text{EditMagnitude} \uparrow
\]

### 反事实反馈

| 反馈 | 期望现象 |
|---|---|
| 正确 mask | 修复率较高 |
| 错误 mask | 修复率下降 |
| 去掉 keep | 非失败区域漂移增加 |
| 低 \(\tau_t\) | 修改幅度小 |
| 高 \(\tau_t\) | 修改幅度大 |
| 去掉 heatmap | 只有在实现 clash-guided sampling 后才作为生成过程消融; plain backend 下只能作为 verifier / selector / adapter 消融 |

---

## 21. 训练和评估步骤

| 步骤 | 输入 | 输出 | 统一保存位置 |
|---|---|---|---|
| Step 1：准备 clean complexes | raw complexes | \((P,L,S,\mathcal R,anchors,pocket)\) | `data/processed/v0_1/` |
| Step 2：人工注入失败 | clean complexes | \((P,L_f,M_{injected},E^{old},H^{clash},s)\) | `data/benchmarks/clashrepairbench_rg_artificial/v0_1/` |
| Step 3：标签溯源与 mask seed | artificial samples | provenance audit, circularity risk, phase4 masks | `reports/phase3_label_provenance_audit/` |
| Step 4：backend feasibility + formal repair loop | failed samples | repair candidates | `runs/phase4_0_backend_feasibility/`, `runs/phase4_local_repair_loop/` |
| Step 5：验证器打标签 | repair candidates | labels / utilities | `data/candidate_pools/v0_1/` |
| Step 6：训练排序器 | candidate pools | ranker | `runs/phase5_ranker/`, 阶段 4.1 稳定后推进 |
| Step 7：训练适配器 | candidate pools | adapter | `runs/phase7_adapter/`, 阶段 4.1 稳定后推进 |
| Step 8：最终测试 | artificial + model-induced | evaluation reports | `reports/phase8_model_induced/` |

---

## 22. 统一项目目录结构


```text
clash2feedback_gc/
  README.md
  pyproject.toml
  environment.yml

  docs/
    20260504-01-Clash2Feedback-GC_完整方案与升级路线.md
    20260504-02-Clash2Feedback-GC_第一篇论文实验方案.md
    20260504-03-Clash2Feedback-GC_总体实验递进路线.md
    20260505-Clash2Feedback-GC_阶段0工程方案.md

  configs/
    phase0.yaml
    phase1.yaml
    phase2_injection.yaml
    phase3.yaml
    phase4.yaml
    phase5.yaml
    phase6.yaml
    phase7.yaml
    phase8.yaml

  data/
    raw_complexes/
      complex_000001/
        protein.pdb
        ligand.sdf
        metadata.json
    processed/
      v0_1/
        complexes/
          complex_000001.pkl
        manifest.parquet
        schema.json
    splits/
      v0_1/
        train.txt
        val.txt
        test.txt
        split_report.csv
    benchmarks/
      clashrepairbench_rg_artificial/
        v0_1/
          samples/
          manifest.parquet
      model_induced/
        v0_1/
          samples/
          manifest.parquet
    candidate_pools/
      v0_1/
        train.parquet
        val.parquet
        test.parquet
    cache/

  reports/
    phase0/
    phase1_clash_detector/
    phase2_injection/
    phase3_label_provenance_audit/
    phase4_0_backend_feasibility/
    phase4_local_repair_loop/
    phase5_ranker/
    phase6_critic/
    phase7_adapter/
    phase8_model_induced/

  runs/
    phase4_0_backend_feasibility/
    phase4_local_repair_loop/
    phase5_ranker/
    phase6_critic/
    phase7_adapter/
    phase8_model_induced/

  src/
    clash2feedback/
      __init__.py
      data/
      io/
      chemistry/
      pocket/
      geometry/
      perturb/
      feedback/
      generation/
      verifier/
      models/
      utils/

  scripts/
    phase0_build_processed.py
    phase0_check_dataset.py
    phase0_make_splits.py
    phase1_check_clashes.py
    phase2_inject_artificial_clashes.py
    phase3_label_provenance_audit.py
    phase4_backend_feasibility.py
    phase4_local_repair_loop.py
    phase5_build_candidate_pool.py
    phase5_train_ranker.py
    phase6_train_critic.py
    phase7_train_adapter.py
    phase8_model_induced_eval.py
```


---

## 23. 最小可发表实验包

必须完成：

1. clean complex 过滤和 processed 数据；
2. 人工注入局部碰撞数据集；
3. phase2 label provenance audit, circularity risk audit 和 phase4 mask seed；
4. 阶段 4.0 backend feasibility audit；
5. Random mask、Predicted mask、Structured predicted protocol、Oracle 对比；
6. 协议字段消融；
7. 模型诱导失败集上的小规模验证；
8. 3–5 个可视化案例。

阶段 4.1 得到稳定 repair outcomes 后, 再推进：

1. 排序器 top-k 实验；
2. 学习型诊断头；
3. 学习型反馈适配器；
4. 候选预算曲线 \(K=8,16,32\)；
5. 更系统的失败案例分析。

不建议第一篇做：

- 生成器微调；
- 完整强化学习；
- 多生成器大规模对比；
- 处理所有失败类型；
- 把亲和力提升作为主指标。

---

## 24. 第一篇最终主张

最稳主张：

\[
\boxed{\text{结构化失败诊断反馈可以把部分局部碰撞失败候选救回来。}}
\]

完整表述：

> Clash2Feedback-GC 先审计 controlled repair substrate 的标签来源和循环验证风险, 再冻结 attribution-derived operational mask policy, 通过同一 repair backend 和同一 candidate budget 下的 Random / Predicted / Oracle mask 对照评估 downstream repair utility。第一篇实验重点证明: 在 controlled local R-group collision repair substrate 上, predicted mask policy 和结构化修复协议是否比随机 mask 和完全重新生成更能提高可靠修复率, 同时保持 scaffold 和非失败区域稳定。

---

## 25. 当前最应该先做

第一篇正式实验之前，先完成阶段 0：

```text
读取 protein / ligand
→ RDKit 检查 ligand
→ 裁剪 pocket
→ 拆 scaffold / R-groups / anchors
→ 保存 processed sample
→ 做基础 sanity check
```

不要一开始训练纠错器，也不要一开始接 DiffSBDD 修复。先把数据底座打稳。

---

## 26. 参考资料

1. Schneuing et al., **Structure-based drug design with equivariant diffusion models**, *Nature Computational Science*, 2024.  
   https://www.nature.com/articles/s43588-024-00737-x

2. DiffSBDD GitHub repository.  
   https://github.com/arneschneuing/DiffSBDD

3. Francoeur et al., **Three-Dimensional Convolutional Neural Networks and a Cross-Docked Dataset for Structure-Based Drug Design**, *Journal of Chemical Information and Modeling*, 2020.  
   https://pmc.ncbi.nlm.nih.gov/articles/PMC8902699/

4. Buttenschoen et al., **PoseBusters: AI-based docking methods fail to generate physically valid poses or generalise to novel sequences**, *Chemical Science*, 2024.  
   https://pubs.rsc.org/en/content/articlelanding/2024/sc/d3sc04185a

5. Harris et al., **PoseCheck: Generative Models for 3D Structure-Based Drug Design Produce Ligands with Poor Physical Validity and Bioactivity**, 2023.  
   https://arxiv.org/abs/2308.07413
