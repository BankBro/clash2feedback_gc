# Clash2Feedback-GC：第一篇论文实验方案

> 版本：2026-05-05 一致性修订版  
> 推荐定位：方法验证型短论文 / workshop 论文 / BIBM 风格短论文  
> 推荐版本：**冻结生成器 + 学习型纠错器 + 规则 / 轻量学习反馈适配器 + 修复排序器 + 可靠验证器**


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
2. 训练或评估失败区域定位器；
3. 定义结构化修复协议；
4. 把协议翻译成冻结生成器可执行控制；
5. 生成局部修复候选；
6. 用排序器挑选候选；
7. 用可靠验证器判断旧碰撞是否修复。

### 1.2 不做什么

| 不做 | 原因 |
|---|---|
| 不证明实验结合成功 | 这需要实验亲和力、活性或共晶结构证据 |
| 不主攻结合亲和力预测 | 会偏离局部修复主线 |
| 不重新训练通用三维生成器 | 工程和资源风险高 |
| 不做完整强化学习 | 任务范围过大 |
| 不同时处理所有失败类型 | 第一篇只聚焦局部 R-group clash |
| 不把碰撞检测本身当主要创新 | 现有工具已能做检测和过滤 |

---

## 2. 第一篇核心实验问题

### 问题一：纠错器能不能找对失败区域？

输入：

\[
(P,L_f)
\]

输出：

\[
M_t
\]

其中：

| 符号 | 含义 |
|---|---|
| \(P\) | 蛋白质口袋 |
| \(L_f\) | 局部碰撞失败候选配体 |
| \(M_t\) | 预测失败区域，通常是某个 R-group |

要回答：

> 模型能不能定位哪个局部取代基导致了 protein-ligand clash？

### 问题二：结构化反馈是否比单纯 mask 更有用？

比较：

```text
只告诉生成器：改哪里
```

和：

```text
告诉生成器：改哪里、保留哪里、旧碰撞热区在哪里、撞得多严重、该小修还是大修
```

也就是比较：

\[
\text{Clash2Mask}
\quad vs \quad
\text{Clash2Feedback-GC}
\]

### 问题三：学习型反馈适配器是否优于固定规则？

比较：

\[
A_{rule}(\mathcal P_t^{repair})
\]

和：

\[
A_\psi(\mathcal P_t^{repair})
\]

看学习型适配器是否能更好地选择：

\[
u_t=(\mathcal M_t^{edit},\mathcal M_t^{fix},\rho_t,\tau_t,K_t)
\]

### 问题四：排序器是否能减少抽卡？

生成器一次产生 \(K\) 个候选，排序器预测哪个最像可靠修复：

\[
C_\phi^{rank}(P,L_f,L_r,\mathcal B_t)
\rightarrow
\hat U
\]

要回答：

> 在相同候选预算下，排序器能不能把真正修好的候选排到前面？

---

## 3. 实验总流程

第一篇完整流程：

\[
L_f
\rightarrow
C_\phi^{diag}
\rightarrow
\mathcal P_t^{repair}
\rightarrow
A_\psi
\rightarrow
u_t
\rightarrow
G_{\theta_0}
\rightarrow
\{L_r^{(i)}}\}_{i=1}^K
\rightarrow
C_\phi^{rank}
\rightarrow
R
\rightarrow
\text{success / fail}
\]

| 模块 | 第一篇处理方式 |
|---|---|
| \(G_{\theta_0}\) | 冻结结构基础生成器，第一版建议 DiffSBDD |
| \(C_\phi^{diag}\) | 训练或与规则定位对比 |
| \(C_\phi^{rank}\) | 训练 |
| \(A_{rule}\) | 必须有，作为强基线 |
| \(A_\psi\) | 建议做，作为增强实验 |
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
| 人工注入局部碰撞样本 | `data/benchmarks/clashrepairbench_rg_artificial/v0_1/` | 训练和评估失败区域定位，标签清楚 |
| 生成器诱导失败样本 | `data/benchmarks/model_induced/v0_1/` | 验证真实生成失败场景下能否修复 |
| 修复候选池 | `data/candidate_pools/v0_1/` | 训练排序器和反馈适配器 |

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

阶段 0 先从 40–50 个候选 complex 中筛出 20–30 个 clean complex。

第一篇最小可跑通版本可以扩大到：

| 数据 | 数量 |
|---|---:|
| clean complexes | 80–120 个 |
| 人工失败样本 | 300–600 个 |
| 模型诱导失败样本 | 50–100 个 |

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

人工注入失败样本用于训练和评估诊断器，因为真实失败区域已知。

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

### 方式二：局部构象扰动

扰动失败取代基内部可旋转键，但固定 scaffold 和 anchor。

### 方式三：合法片段替换

用相似大小或稍大的片段替换原 R-group，更接近“取代基太大导致 clash”的情况，但工程复杂，建议作为增强。

---

## 9. 人工失败样本保留条件

人工失败样本必须满足：

\[
\text{LigandValid}=1
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

真实失败区域：

\[
M^*=\arg\max_k Score_\alpha(R_k)
\]

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

输入：

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

---

## 16. 对照方法

| 方法 | 具体做法 | 目的 |
|---|---|---|
| Drop | 失败候选直接丢弃 | 说明传统流程浪费候选 |
| Full resampling | 同一 pocket 重新生成完整分子 | 比较完全重来和局部修复 |
| Random mask | 随机选一个 R-group 重画 | 证明定位有用 |
| Clash2Mask-rule | 规则定位失败 R-group，只给 mask | 证明不只是 mask |
| Clash2Feedback-rule | 规则定位 + keep + severity + rule adapter | 证明结构化协议有用 |
| Learned critic + rule adapter | 学习型纠错器 + 规则适配器 | 证明纠错器有用 |
| Learned critic + learned adapter | 学习型纠错器 + 学习型适配器 | 证明适配器可学习 |
| Full method + ranker | 完整方法 | 主方法 |
| Oracle feedback | 真实失败区域 + 最优控制 | 上限 |

期望趋势：

\[
\text{Random mask}
<
\text{Clash2Mask}
<
\text{Clash2Feedback-rule}
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
| 不训练纠错器，用规则定位 | 看学习型纠错器是否提升 |
| 不训练适配器，用规则适配器 | 看适配器是否可学习 |
| 不用排序器，随机选候选 | 看排序器是否减少抽卡 |
| 排序器不输入反馈 | 看结构化反馈是否进入评价 |
| 排序器只输入候选结构 | 防止退化成普通分子筛选器 |

---

## 18. 评价指标

### 18.1 诊断指标

| 指标 | 含义 |
|---|---|
| R-group Top-1 Accuracy | 预测失败 R-group 是否正确 |
| R-group Top-3 Accuracy | 真实失败 R-group 是否在前三 |
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

### 表 2：失败区域定位

| 方法 | R-group Top-1 | R-group Top-3 | Atom F1 | Heatmap AUPRC | Severity MAE |
|---|---:|---:|---:|---:|---:|
| Rule locator |  |  |  |  |  |
| Learned critic |  |  |  |  |  |

### 表 3：人工失败集修复

| 方法 | Old Resolved ↑ | No New Clash ↑ | Reliable Repair ↑ | Scaffold RMSD ↓ | Avg Candidates ↓ |
|---|---:|---:|---:|---:|---:|
| Full resampling |  |  |  |  |  |
| Random mask |  |  |  |  |  |
| Clash2Mask-rule |  |  |  |  |  |
| Clash2Feedback-rule |  |  |  |  |  |
| Learned critic + rule adapter |  |  |  |  |  |
| Learned critic + learned adapter |  |  |  |  |  |
| Full method + ranker |  |  |  |  |  |
| Oracle |  |  |  |  |  |

### 表 4：模型诱导失败集修复

| 方法 | Old Resolved ↑ | No New Clash ↑ | Reliable Repair ↑ | Geometry Valid ↑ | Avg Candidates ↓ |
|---|---:|---:|---:|---:|---:|
| Full resampling |  |  |  |  |  |
| Random mask |  |  |  |  |  |
| Clash2Mask-rule |  |  |  |  |  |
| Clash2Feedback-rule |  |  |  |  |  |
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
| 去掉 heatmap | 旧碰撞残留或邻近新碰撞增加 |

---

## 21. 训练和评估步骤

| 步骤 | 输入 | 输出 | 统一保存位置 |
|---|---|---|---|
| Step 1：准备 clean complexes | raw complexes | \((P,L,S,\mathcal R,anchors,pocket)\) | `data/processed/v0_1/` |
| Step 2：人工注入失败 | clean complexes | \((P,L_f,M^*,E^{old},H^{clash},s)\) | `data/benchmarks/clashrepairbench_rg_artificial/v0_1/` |
| Step 3：训练或评估诊断头 | artificial samples | \((\hat M,\hat H,\hat s)\) | `reports/phase6_critic/` 和 `runs/phase6_critic/` |
| Step 4：规则适配器生成候选 | failed samples | repair candidates | `runs/phase4_rule_repair/` |
| Step 5：验证器打标签 | repair candidates | labels / utilities | `data/candidate_pools/v0_1/` |
| Step 6：训练排序器 | candidate pools | ranker | `runs/phase5_ranker/` |
| Step 7：训练适配器 | candidate pools | adapter | `runs/phase7_adapter/` |
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
    phase2.yaml
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
    phase3_rule_locator/
    phase4_rule_repair/
    phase5_ranker/
    phase6_critic/
    phase7_adapter/
    phase8_model_induced/

  runs/
    phase4_rule_repair/
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
    phase3_rule_locator.py
    phase4_rule_repair.py
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
3. 规则定位和学习型定位对比；
4. Random mask、Clash2Mask、Clash2Feedback-rule、Full method、Oracle 对比；
5. 排序器 top-k 实验；
6. 协议字段消融；
7. 模型诱导失败集上的小规模验证；
8. 3–5 个可视化案例。

强烈建议完成：

1. 学习型反馈适配器；
2. 反事实反馈实验；
3. 候选预算曲线 \(K=8,16,32\)；
4. 失败案例分析。

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

> Clash2Feedback-GC 通过学习型纠错器定位失败取代基，通过反馈适配器将修复建议协议翻译成冻结三维生成器可执行的局部重画控制，并通过修复排序器和可靠验证器判断旧错误是否真正消除。第一篇实验重点证明：在局部 R-group 碰撞失败样本上，结构化反馈比随机 mask、单纯 clash mask 和完全重新生成更能提高可靠修复率，同时保持 scaffold 和非失败区域稳定。

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
