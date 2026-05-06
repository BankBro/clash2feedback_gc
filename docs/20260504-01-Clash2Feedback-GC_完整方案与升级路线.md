# Clash2Feedback-GC 完整方案与升级路线

> 版本：2026-05-05 一致性修订版  
> 建议方案名：**Clash2Feedback-GC：结构化生成器—纠错器通信驱动的蛋白质—配体局部碰撞修复框架**


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



## 0. 项目核心定位

Clash2Feedback-GC 的核心不是重新发明一个通用三维分子生成模型，也不是单纯判断蛋白质—配体有没有碰撞。

它研究的是：

> **当结构基础生成模型产生一个局部失败候选，例如某个取代基和蛋白质口袋发生空间碰撞时，能否定位失败区域，把碰撞诊断转化为生成器可执行的结构化反馈，并只修复出错的局部区域。**

流程可以概括为：

```text
生成候选
→ 发现局部碰撞
→ 定位失败区域
→ 生成修复协议
→ 适配成生成器控制
→ 局部再生成
→ 验证旧错误是否真正修好
```

本文不直接研究蛋白质—配体真实结合亲和力预测，也不声称修复后的候选一定实验上强结合。无严重碰撞只是合理结合姿态的必要条件，不是充分条件。

主指标不应叫：

```text
Binding Success Rate
```

而应叫：

```text
Reliable Repair Yield
```

即可靠修复率。

---

## 1. 最开始的问题

现有结构基础生成模型和分子对接方法可能产生局部物理失败，例如：

- 某个取代基伸进了蛋白原子已经占据的位置；
- 配体整体在口袋里，但局部片段和蛋白严重重叠；
- 生成分子整体看起来有利用价值，但某个局部区域导致 pose 不合理。

很多现有流程会这样处理：

```text
生成候选
→ 运行物理合理性检查
→ 有碰撞就过滤或丢弃
```

Clash2Feedback-GC 研究另一种流程：

```text
生成候选
→ 诊断哪里撞了
→ 判断哪些区域应保持
→ 把诊断转成生成器可执行控制
→ 只重画或扰动失败局部
→ 检查旧碰撞是否消除、新碰撞是否没有出现
```

科学问题可以写成：

> **对于结构基础生成中的局部碰撞失败候选，能否通过错误定位、结构化反馈、局部再生成和可靠验证，把一部分原本会被丢弃的候选救回来？**

---

## 2. 与“结合成功”的边界

需要明确区分三件事。

| 概念 | 含义 | 本文是否主攻 |
|---|---|---:|
| 真实实验结合成功 | 有实验亲和力、活性或共晶结构证据 | 否 |
| 结合亲和力预测 | 预测或优化 \(K_d\)、\(K_i\)、IC50、结合自由能 | 否 |
| 局部碰撞失败修复 | 修掉局部 protein-ligand clash，同时保持未失败区域 | 是 |

本文不声称：

- 无碰撞就等于强结合；
- 修复后候选一定实验上有效；
- 方法替代 docking、结合能计算或实验验证。

本文主张的是：

> 对于一个已经位于蛋白口袋中的局部失败候选，如果失败主要来自某个局部区域，结构化诊断反馈可以提高可靠修复率，并减少完全重新生成带来的结构漂移。

---

## 3. 为什么不是单纯碰撞检测

现有工具已经可以检测或过滤蛋白质—配体物理不合理姿态，例如检查：

- protein-ligand clash；
- ligand 内部几何；
- 键长、键角、芳香环平面性；
- 分子内外距离异常；
- docking pose 合理性。

所以本文不能把“检测碰撞”当成主要创新。

区别在于：

| 现有检查 / 过滤流程 | Clash2Feedback-GC |
|---|---|
| 判断有没有碰撞 | 判断哪里撞、哪个取代基撞、撞得多严重 |
| 有问题常直接丢弃 | 尝试局部修复失败候选 |
| 通常只给 pass / fail 或分数 | 给生成器可执行的修复协议 |
| 主要看最终结构是否合理 | 旧错误感知验证：旧碰撞是否真正消除 |
| 不一定保持原候选结构 | 固定 scaffold 和非失败区域 |

核心是：

```text
碰撞检测结果
→ 结构化修复反馈
→ 生成器可执行控制
→ 局部再生成
→ 旧错误感知验证
```

---

## 4. 总体框架

建议将系统写成四个模块：

\[
G_\theta + C_\phi + A_\psi + R
\]

| 模块 | 名称 | 作用 |
|---|---|---|
| \(G_\theta\) | 生成器 | 根据蛋白口袋和控制信号生成或局部再生成分子 |
| \(C_\phi\) | 纠错评价器 | 定位失败区域、估计严重度、评价修复候选 |
| \(A_\psi\) | 反馈适配器 | 把修复协议翻译成具体生成器可执行的输入 |
| \(R\) | 可靠验证器 | 判断旧错误是否消除、新错误是否没有出现 |

完整流程为：

\[
L_t
\rightarrow
C_\phi^{diag}
\rightarrow
\mathcal P_t^{repair}
\rightarrow
A_\psi
\rightarrow
u_t
\rightarrow
G_\theta
\rightarrow
\{L_{t+1}^{(i)}}\}_{i=1}^K
\rightarrow
C_\phi^{rank}
\rightarrow
R
\rightarrow
L_{t+1}^*
\]

人话版：

1. 输入当前失败候选 \(L_t\) 和蛋白口袋 \(P\)；
2. 纠错器定位哪里发生局部碰撞；
3. 生成结构化修复协议；
4. 反馈适配器把协议翻译成生成器能执行的控制；
5. 生成器只对失败局部区域进行再生成或扰动；
6. 得到多个修复候选；
7. 排序器挑出最有希望的候选；
8. 可靠验证器判断是否真正修复。

---

## 5. 不建议主打“大模型—小模型”

“大模型—小模型”不是最稳的论文表达，因为大小标准不清楚，也容易让创新点变成工程包装。

更稳的说法是：

\[
\text{生成器}
+
\text{纠错评价器}
+
\text{反馈适配器}
+
\text{可靠验证器}
\]

真正关键不是模型大小，而是：

\[
\boxed{
\text{失败诊断}
\rightarrow
\text{结构化修复协议}
\rightarrow
\text{生成器可执行控制}
\rightarrow
\text{局部再生成}
\rightarrow
\text{旧错误感知验证}
}
\]

---

## 6. 生成器无关性与适配边界

Clash2Feedback-GC 应该设计成：

```text
生成器无关的诊断与协议层
+
生成器相关的反馈适配器
```

下面这些部分应尽量不依赖具体生成器：

- 蛋白质—配体复合物读取；
- pocket 裁剪；
- scaffold 和 R-groups 拆分；
- anchor 识别；
- protein-ligand clash 诊断；
- 修复协议 \(\mathcal P_t^{repair}\)；
- 修复评价协议 \(\mathcal P_t^{eval}\)；
- 可靠验证器。

下面这些部分需要根据具体生成器适配：

- edit mask 如何表示；
- fixed atoms 如何传入；
- anchor 如何约束；
- inpainting region 如何构造；
- partial noising strength 如何设置；
- 生成候选如何解析回统一格式。

因此论文中不应声称：

> 可以零成本接入任意生成器。

更稳的表述是：

> 只要一个结构基础生成器支持蛋白口袋条件下的局部生成、固定区域或 inpainting，Clash2Feedback-GC 的修复协议就可以通过生成器特定适配器翻译成它的控制输入。

---

## 7. 生成器接入条件

适合接入的生成器最好满足：

| 条件 | 作用 |
|---|---|
| 支持蛋白口袋条件 | 修复必须发生在具体 pocket 中 |
| 输出三维配体 | 需要检查几何和碰撞 |
| 支持固定部分原子 | scaffold 和非失败区域不能乱动 |
| 支持局部编辑或 inpainting | 只修改失败区域 |
| 支持 anchor 或片段连接约束 | 新局部片段要接回骨架 |
| 支持多个候选采样 | 排序器需要候选池 |

第一版最稳的是使用冻结 DiffSBDD 类生成器作为主基座。后续可以尝试 PocketXMol、Diffleop、DiffDec 等更偏局部生成、scaffold decoration 或 fragment growing 的模型。

第一篇不要同时对比太多生成器，否则论文会从“反馈修复框架”变成“生成模型大评测”。

---

## 8. 两套通信协议

建议把反馈写成两套协议：

\[
\mathcal B_t =
(
\mathcal P_t^{repair},
\mathcal P_t^{eval}
)
\]

其中：

- \(\mathcal P_t^{repair}\)：告诉生成器怎么修；
- \(\mathcal P_t^{eval}\)：告诉验证器怎么判断修没修好。

---

## 9. 修复建议协议

第一篇建议使用精简但足够表达局部修复的信息：

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
| \(M_t\) | 失败区域，通常是某个 R-group |
| \(C_t^{keep}\) | 必须保持的 scaffold 和非失败 R-groups |
| \(H_t^{clash}\) | 蛋白侧旧碰撞热区 |
| \(s_t\) | 碰撞严重度 |
| \(\rho_t\) | 修复动作类型 |
| \(\tau_t\) | 修复强度或加噪强度 |
| \(K_t\) | 本轮候选数 |
| \(A_t\) | anchor 信息，新局部片段接回骨架的位置 |

修复动作可以先定义为：

\[
\rho_t
\in
\{
\text{小幅构象修复},
\text{中等局部扰动},
\text{强局部扰动},
\text{完整重画取代基},
\text{扩大重画区域},
\text{放弃局部修复}
\}
\]

---

## 10. 修复评价协议

\[
\mathcal P_t^{eval}
=
(
Q_{old},
Q_{new},
Q_{keep},
Q_{geom},
Q_{pocket},
Q_{cost}
)
\]

| 项 | 判断内容 |
|---|---|
| \(Q_{old}\) | 原碰撞是否消除 |
| \(Q_{new}\) | 是否没有产生新严重碰撞 |
| \(Q_{keep}\) | scaffold 和非编辑区域是否保持 |
| \(Q_{geom}\) | 配体自身几何是否合法 |
| \(Q_{pocket}\) | 配体是否仍在蛋白口袋中 |
| \(Q_{cost}\) | 修改范围是否合理 |

可靠修复定义为：

\[
R(P,L_f,L_r,\mathcal P_t^{eval})=1
\]

当且仅当：

- 旧碰撞被消除；
- 没有新严重碰撞；
- scaffold 保持稳定；
- 非编辑区域保持稳定；
- 配体自身几何合法；
- 配体仍位于 pocket 中；
- 修改主要发生在指定 edit region 内。

---

## 11. scaffold、R-groups 与 anchor

本文采用一种人为定义的分子拆分方式：

\[
L = S + \mathcal R
\]

| 记号 | 含义 |
|---|---|
| \(S\) | scaffold，配体核心骨架 |
| \(\mathcal R\) | R-groups，接在骨架上的取代基集合 |
| anchor | R-group 与 scaffold 的连接位置 |

需要强调：

- scaffold 不是天然唯一的，取决于拆分规则；
- 第一版固定使用 Murcko scaffold 作为主规则；
- R-groups 可以有多个；
- 第一版优先处理单锚点 R-group；
- 多锚点 linker、macrocycle、共价配体、金属配合物先标记为 unsupported。

拆分的目的不是做完整药物化学定义，而是服务局部修复任务：

> 判断哪个局部片段撞了蛋白，并只修改这个片段。

---

## 12. 分层升级路线

| 层级 | 名称 | 生成器是否训练 | 纠错器是否训练 | 适配器是否训练 | 作用 |
|---|---|---:|---:|---:|---|
| Level 0 | 规则版反馈修复 | 否 | 否 | 否 | 强基线，证明任务可行 |
| Level 1 | 学习型纠错器 | 否 | 是 | 否 | 学习定位失败区域和严重度 |
| Level 2 | 学习型反馈适配器 | 否 | 是 | 是 | 学习选择修复模式和强度 |
| Level 3 | 几何引导采样 | 否 | 是 | 是 | 用旧碰撞热区引导生成避让 |
| Level 4 | 反馈编码器微调 | 轻量训练 | 是 | 是 | 让生成器直接利用反馈协议 |
| Level 5 | 偏好学习协同 | 部分训练 | 是 | 是 | 用修复成败偏好优化生成器 |
| Level 6 | 强化学习策略 | 是 | 是 | 是 | 学习多轮修复策略 |

第一篇建议做到：

\[
\boxed{
\text{Level 1}
+
\text{部分 Level 2}
}
\]

也就是：

- 冻结生成器；
- 训练纠错器诊断头；
- 训练修复排序器；
- 规则适配器作为强基线；
- 学习型适配器作为增强实验；
- 不做生成器微调；
- 不做完整强化学习。

---

## 13. 数据集设计

建议构建：

> **ClashRepairBench-RG：取代基级蛋白质—配体局部碰撞修复基准**

其中 RG 表示 R-group。

数据包括两部分：

| 数据 | 统一保存位置 | 用途 |
|---|---|---|
| 人工注入局部碰撞集 | `data/benchmarks/clashrepairbench_rg_artificial/v0_1/` | 有真实失败区域标签，用于训练和评估诊断头 |
| 生成器诱导失败集 | `data/benchmarks/model_induced/v0_1/` | 更接近真实生成失败，用于最终验证 |

---

## 14. 数据来源与清洗原则

第一版推荐数据路线：

```text
DiffSBDD example
→ CrossDocked 小子集
→ 可选 PDBBind / RCSB PDB 外部检查
```

CrossDocked 是候选数据源，不是完全干净的无碰撞真值库。它包含大量 docking 姿态，可能存在局部碰撞或几何异常。因此在构建基准之前，必须先筛选 clean complex。

阶段 0 小规模数据应表述为 task-specific clean subset. 如果使用 ligand-only scaffold/R-group 预筛, 它适合本项目的 R-group 局部修复任务, 但不是无偏 CrossDocked 子集. 如果 clean pool target 分布不均, 应保留完整 clean pool, 同时派生 target-balanced subset 供后续 mini-loop 使用。

clean complex 建议满足：

- protein 和 ligand 来自同一个 complex；
- 坐标系一致；
- ligand 在 pocket 附近；
- RDKit sanitize 通过；
- ligand 有三维坐标；
- pocket 非空；
- 原始 protein-ligand 没有严重碰撞；
- 能拆出 scaffold 和至少 2 个 R-groups；
- 第一版排除共价配体、金属配合物、多片段盐、macrocycle。

这里的基础严重碰撞筛查只作为阶段 0 sanity gate, 不能替代阶段 1 的正式 vdW clash detector 和 repair verifier。

---

## 15. 纠错器、适配器和验证器

### 15.1 纠错器

纠错器不只是二分类器，建议包含：

\[
C_\phi=
(
C_\phi^{diag},
C_\phi^{advice},
C_\phi^{rank}
)
\]

| 子模块 | 输入 | 输出 | 作用 |
|---|---|---|---|
| 诊断头 | \(P,L_f\) | 失败区域、热区、严重度 | 找错 |
| 建议头 | 诊断结果 | 修复动作和强度 | 给建议 |
| 排序头 | 失败候选和修复候选 | 修复价值分数 | 选候选 |

第一篇可以简化：

- 诊断头预测失败 R-group、蛋白碰撞热区、严重度；
- 排序头预测候选是否可靠修复；
- 建议头可以先由规则适配器或轻量分类器承担。

### 15.2 反馈适配器

反馈适配器负责：

\[
A_\psi(\mathcal P_t^{repair})
\rightarrow
u_t
\]

其中 \(u_t\) 是具体生成器能执行的控制，例如：

| 控制 | 含义 |
|---|---|
| editable mask | 哪些原子或局部区域允许修改 |
| fixed mask | 哪些原子必须保持 |
| anchor constraint | 新片段从哪里接回 scaffold |
| repair mode | partial noising 或 inpainting |
| repair strength | 加噪步数、采样强度或重画强度 |
| candidate number | 生成候选数 |

### 15.3 可靠验证器

可靠验证器是最终裁判，不由纠错器自己说了算。

候选 \(L_r\) 通过验证，当且仅当：

| 条件 | 建议指标 |
|---|---|
| 原碰撞消除 | old clash score 降到原来的 10% 以下 |
| 无新严重碰撞 | new severe clash 数为 0 或低于阈值 |
| scaffold 保持 | scaffold RMSD < 0.5 Å |
| 非编辑区域保持 | non-edit RMSD < 0.8 Å |
| ligand 几何合法 | RDKit / PoseBusters 风格检查通过 |
| 局部性 | 主要修改发生在 edit mask 内 |
| pocket 保持 | 修复后 ligand 仍在 pocket 中 |
| 相互作用不明显恶化 | 可选，不能作为第一篇主指标 |

---

## 16. 第一篇论文建议主线

第一篇最稳版本：

\[
\boxed{
\text{冻结生成器}
+
\text{学习型纠错器}
+
\text{结构化修复协议}
+
\text{规则 / 学习型反馈适配器}
+
\text{修复排序器}
+
\text{可靠验证器}
}
\]

不建议第一篇做：

- 完整重新训练三维生成模型；
- 完整强化学习；
- 端到端生成器—纠错器在线训练；
- 同时处理所有失败类型；
- 大规模多生成器对比；
- 主张实验结合成功或亲和力显著提升。

第一篇要证明的是：

> 在局部碰撞失败候选上，结构化诊断反馈比随机 mask、单纯 clash mask 和完全重新生成更能提高可靠修复率，并更好保持 scaffold 和非失败区域。

---

## 17. 对照方法和主要指标

### 17.1 对照方法

| 方法 | 作用 |
|---|---|
| Drop failed candidates | 失败直接丢弃 |
| Full resampling | 完整重新生成分子 |
| Random mask regeneration | 随机选区域重画 |
| Clash2Mask | 只使用失败区域 mask |
| Clash2Feedback-rule | 规则定位 + 结构化协议 + 规则适配器 |
| Learned critic + rule adapter | 学习型纠错器 + 规则适配器 |
| Learned critic + learned adapter | 学习型纠错器 + 学习型适配器 |
| Full method + ranker | 完整方法 |
| Oracle protocol | 真实失败区域和最优控制上限 |

### 17.2 主要指标

| 指标 | 含义 |
|---|---|
| R-group Top-1 Accuracy | 是否找对失败取代基 |
| Old Clash Resolved Rate | 旧碰撞消除率 |
| No New Clash Rate | 无新严重碰撞率 |
| Reliable Repair Yield | 可靠修复率，主指标 |
| Geometry Valid Rate | 分子几何合法率 |
| Scaffold RMSD | scaffold 是否保持 |
| Non-edit RMSD | 非编辑区域是否保持 |
| Edit Compliance | 修改是否主要发生在 edit region |
| Keep Compliance | fixed region 是否稳定 |
| Top-1 / Top-3 Repair Hit | 排序器是否把成功候选排在前面 |

---

## 18. 统一项目目录结构

以下目录结构是四个文档共同采用的实现口径。


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


### 目录职责说明

| 目录 | 职责 |
|---|---|
| `docs/` | 静态方案文档，包含这四个 Markdown 文件 |
| `data/raw_complexes/` | 原始 protein / ligand / metadata，不随意修改 |
| `data/processed/` | 阶段 0 processed clean complexes |
| `data/splits/` | train / val / test 划分 |
| `data/benchmarks/` | 阶段 2 和阶段 8 构造出的失败样本基准 |
| `data/candidate_pools/` | 阶段 5 训练排序器用的候选池表 |
| `reports/` | 每个阶段生成的统计表、图、summary，不存方案文档 |
| `runs/` | 训练日志、生成候选、checkpoint 等较重运行产物 |
| `src/clash2feedback/` | 可复用 Python 包代码 |
| `scripts/` | 每个阶段的命令行入口 |

---

## 19. 与已有工作的区别

### 与 DiffSBDD 类生成器的区别

DiffSBDD 等结构基础生成器解决的是：

> 给定蛋白口袋和生成条件后，如何生成三维分子或局部结构。

Clash2Feedback-GC 解决的是：

> 对已经失败的局部碰撞候选，如何定位错误、生成反馈、控制局部再生成，并验证旧错误是否被修复。

### 与 PoseBusters / PoseCheck 等检查工具的区别

这些工具更像验证和诊断工具，可以指出结构是否物理合理。

Clash2Feedback-GC 进一步问：

> 检查出问题以后，如何把问题转成生成器能执行的修复控制？

### 与 docking filtering 的区别

```text
姿态不好 → 过滤掉
```

而 Clash2Feedback-GC 是：

```text
局部姿态失败 → 诊断局部错误 → 修复局部区域 → 验证是否救回
```

### 与亲和力优化的区别

亲和力优化关注结合能或活性提升。Clash2Feedback-GC 第一篇关注结构合理性层面的局部修复，不把亲和力提升作为主指标。

---

## 20. 论文贡献建议

建议写成四点：

1. **提出局部碰撞失败候选修复任务**  
   将结构基础生成中的局部失败候选从“直接丢弃对象”重新定义为“可诊断、可反馈、可局部修复对象”。

2. **提出结构化修复协议和评价协议**  
   明确告诉生成器改哪里、保留哪里、避开哪里、改多大，并告诉系统如何判断旧错误是否被修掉。

3. **提出生成器—纠错器通信机制**  
   用反馈适配器把诊断协议翻译成具体生成器可执行的局部再生成控制。

4. **提出旧错误感知的可靠修复验证**  
   主指标不是普通生成质量，而是旧碰撞是否消除、新碰撞是否避免、非失败区域是否保持。

---

## 21. 最推荐的第一篇论文版本

英文标题建议：

> **Clash2Feedback-GC: Structured Generator–Critic Communication for Local Protein–Ligand Clash Repair**

中文标题建议：

> **Clash2Feedback-GC：结构化生成器—纠错器通信驱动的蛋白质—配体局部碰撞修复**

第一篇主张：

> Clash2Feedback-GC 通过学习型纠错器定位失败取代基，通过反馈适配器将修复协议翻译成冻结三维生成器可执行的局部控制，并通过排序器和可靠验证器判断旧错误是否真正消除。实验重点证明，在局部取代基碰撞失败样本上，结构化反馈比随机 mask、单纯 mask 和完全重新生成更能提高可靠修复率，同时保持 scaffold 和非失败区域稳定。

---

## 22. 最后建议

当前方案最稳的主线是：

\[
\boxed{\text{纠错器不是只打分，而是输出修复协议}}
\]

\[
\boxed{\text{生成器不是天然理解协议，而是通过适配器执行协议}}
\]

\[
\boxed{\text{成功不是模型自己说正确，而是可靠验证器确认旧错误被修复}}
\]

第一篇不要追求完整端到端协同训练。更现实的路线是：

1. 先定义任务和协议；
2. 先完成阶段 0 数据底座；
3. 实现碰撞检测器和可靠验证器；
4. 构建人工局部碰撞数据；
5. 用冻结生成器证明结构化反馈比 mask 更有效；
6. 再训练纠错器、排序器和轻量适配器。

---

## 23. 参考资料

1. Schneuing et al., “Structure-based drug design with equivariant diffusion models”, *Nature Computational Science*, 2024.  
   https://www.nature.com/articles/s43588-024-00737-x

2. DiffSBDD GitHub repository.  
   https://github.com/arneschneuing/DiffSBDD

3. Francoeur et al., “Three-Dimensional Convolutional Neural Networks and a Cross-Docked Dataset for Structure-Based Drug Design”, *Journal of Chemical Information and Modeling*, 2020.  
   https://pmc.ncbi.nlm.nih.gov/articles/PMC8902699/

4. Buttenschoen et al., “PoseBusters: AI-based docking methods fail to generate physically valid poses or generalise to novel sequences”, *Chemical Science*, 2024.  
   https://pubs.rsc.org/en/content/articlelanding/2024/sc/d3sc04185a

5. Harris et al., “PoseCheck: Generative Models for 3D Structure-Based Drug Design Produce Ligands with Poor Physical Validity and Bioactivity”, 2023.  
   https://arxiv.org/abs/2308.07413
