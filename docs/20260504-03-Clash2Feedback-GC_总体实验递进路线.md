# Clash2Feedback-GC：总体实验递进路线

> 版本：2026-05-05 一致性修订版  
> 目的：明确从阶段 0 到第一篇论文完整实验的推进顺序、每一步目标、产出、通过标准和统一目录位置。


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



## 0. 总体原则

不要一开始训练模型，也不要一开始跑完整生成器修复闭环。

第一步应该先建立确定性的实验底座：

\[
\boxed{
\text{小数据集}
\rightarrow
\text{数据格式打通}
\rightarrow
\text{碰撞检测器}
\rightarrow
\text{人工局部碰撞注入}
\rightarrow
\text{规则版定位与验证}
}
\]

原因是：如果还不能稳定判断 protein 和 ligand 是否同坐标系、pocket 是否正常、配体是否合法、scaffold 和 R-groups 是否可拆、哪里发生碰撞，那么后面训练纠错器、排序器和反馈适配器都会不可靠。

---

## 1. 论文关注重点

Clash2Feedback-GC 关注的是：

> **局部蛋白质—配体碰撞失败候选的诊断、结构化反馈、局部再生成和可靠验证。**

它不是：

- 结合亲和力预测；
- 实验结合成功证明；
- 新通用三维生成模型；
- 单纯碰撞检测工具；
- 无碰撞分子筛选器。

更准确的任务是：

\[
(P,L_f)
\rightarrow
\text{定位失败 R-group}
\rightarrow
\mathcal P_t^{repair}
\rightarrow
\text{局部修复}
\rightarrow
\text{可靠验证}
\]

其中 \(L_f\) 是局部碰撞失败候选。

主指标是：

```text
Reliable Repair Yield
```

不是：

```text
Binding Success Rate
```

---

## 2. 总体阶段划分

| 阶段 | 名称 | 核心目标 | 是否训练模型 | 是否调用生成器 | 主要产出 | 统一保存位置 |
|---|---|---|---:|---:|---|---|
| 阶段 0 | 环境与数据格式打通 | 统一 protein、ligand、pocket、scaffold、R-groups、anchors 数据格式 | 否 | 否 | processed clean complexes | `data/processed/v0_1/` |
| 阶段 1 | 碰撞检测器与可靠验证器 | 判断哪里发生碰撞、修复后是否真正成功 | 否 | 否 | clash detector、repair verifier | `src/clash2feedback/geometry/`、`src/clash2feedback/verifier/`、`reports/phase1_clash_detector/` |
| 阶段 2 | 人工局部碰撞注入 | 构建带真实失败区域标签的数据 | 否 | 否 | ClashRepairBench-RG-artificial | `data/benchmarks/clashrepairbench_rg_artificial/v0_1/` |
| 阶段 3 | 规则版定位与反馈 | 验证规则 locator 能否找对失败 R-group | 否 | 否 | 规则定位结果表 | `reports/phase3_rule_locator/` |
| 阶段 4 | 冻结生成器最小修复闭环 | 验证局部再生成是否能救回部分失败候选 | 否 | 是 | Random / Mask / Feedback / Oracle 对照 | `runs/phase4_rule_repair/`、`reports/phase4_rule_repair/` |
| 阶段 5 | 候选池与修复排序器 | 训练排序器，从多个候选中选最可能成功的修复 | 是 | 是 | candidate pool、ranker | `data/candidate_pools/v0_1/`、`runs/phase5_ranker/` |
| 阶段 6 | 学习型纠错器 | 学习预测失败区域、碰撞热区和严重度 | 是 | 可选 | learned critic | `runs/phase6_critic/`、`reports/phase6_critic/` |
| 阶段 7 | 学习型反馈适配器 | 学习把修复协议转成生成器可执行控制 | 是 | 是 | learned adapter | `runs/phase7_adapter/`、`reports/phase7_adapter/` |
| 阶段 8 | 模型诱导失败集测试 | 验证方法不只适用于人工注入失败 | 是 | 是 | model-induced repair results | `data/benchmarks/model_induced/v0_1/`、`reports/phase8_model_induced/` |

第一篇建议至少完成：

\[
\boxed{
\text{阶段 0--5 必须完成}
+
\text{阶段 6--7 作为主方法增强}
+
\text{阶段 8 做小规模验证}
}
\]

---

## 3. 阶段 0：环境与数据格式打通

### 3.1 目标

阶段 0 的目标是：

> 让蛋白质—配体复合物可以被稳定读取、处理、保存和检查，为后续碰撞检测、人工注入、规则定位和生成修复打基础。

输入：

\[
(P,L)
\]

输出：

\[
(P,L,S,\mathcal R,\text{pocket atoms},\text{anchors})
\]

其中：

| 符号 | 含义 |
|---|---|
| \(P\) | 蛋白质原子或蛋白口袋 |
| \(L\) | 配体 |
| \(S\) | scaffold，配体骨架 |
| \(\mathcal R\) | R-groups，取代基集合 |
| anchors | 每个 R-group 接回 scaffold 的连接点 |

### 3.2 阶段 0 做什么

阶段 0 做：

1. 读取 `protein.pdb` / `protein.cif`；
2. 读取 `ligand.sdf`；
3. 用 RDKit 检查配体合法性；
4. 检查 protein 和 ligand 是否同坐标系；
5. 提取配体周围 6–8 Å pocket；
6. 提取 scaffold；
7. 拆分 R-groups；
8. 记录 anchors；
9. 保存 processed sample；
10. 做基础 sanity check。

### 3.3 阶段 0 不做什么

阶段 0 不做：

- 不训练纠错器；
- 不训练排序器；
- 不调用生成器修复；
- 不做人为碰撞注入；
- 不实现完整可靠验证器；
- 不处理所有复杂化学情况。

阶段 0 可以做 **sanity-level clash screening**，用于过滤原始样本中的明显严重碰撞。

正式 clash detector 和 repair verifier 放到阶段 1。

### 3.4 起始数据规模

| 数据 | 建议数量 |
|---|---:|
| 原始候选 complex | 40–50 个 |
| 第一批 clean complex 最低目标 | 20–30 个 |
| 每个 complex 可拆 R-group | 至少 2 个 |

20–30 是第一批阶段 0 最低目标, 不是 clean pool 上限. 若实际 clean pool 超过该数量且 target 分布不均, 保留完整 clean pool, 同时派生 target-balanced subset 供阶段 1-3 mini-loop 使用. 当前口径为 `phase0_clean_pool_v0_1` 保留 51 个 clean samples, `phase0_balanced_30_v0_1` 为 up to 30 samples, actual n = 28.

### 3.5 阶段 0 产出

```text
data/processed/v0_1/complexes/*.pkl
data/processed/v0_1/manifest.parquet
data/processed/v0_1/schema.json
data/splits/v0_1/train.txt
data/splits/v0_1/val.txt
data/splits/v0_1/test.txt
reports/phase0/dataset_check.csv
reports/phase0/failed_cases.csv
reports/phase0/summary.json
```

每个 processed 样本至少保存：

| 字段 | 含义 |
|---|---|
| protein atoms | 蛋白原子类型、残基、坐标 |
| ligand atoms | 配体原子类型和坐标 |
| ligand bonds | 配体键、键级、芳香性 |
| pocket atoms | 配体周围 6–8 Å 蛋白口袋原子 |
| scaffold atoms | 骨架原子集合 |
| R-groups | 取代基集合 |
| anchors | 每个取代基连接点 |
| masks | scaffold mask、R-group mask、pocket mask |
| sanity | 合法性检查结果 |

### 3.6 阶段 0 通过标准

| 指标 | 要求 |
|---|---:|
| clean complex 数量 | ≥ 20 |
| ligand sanitize 通过 | 100% |
| pocket 非空 | 100% |
| scaffold 成功 | 100% |
| 至少 2 个 R-groups | 100% |
| anchors 可记录 | 100% |
| processed 文件可重新读取 | 100% |

如果 clean pool target 分布不均, 阶段 0 收尾还应记录 target distribution summary, 并生成不替代 clean pool 的 target-balanced 派生清单.

---

## 4. 阶段 1：碰撞检测器与可靠验证器

### 4.1 目标

阶段 1 实现项目最基础的判断标准：

1. 失败候选是否存在 protein-ligand clash；
2. 哪些原子对发生碰撞；
3. 哪个 R-group 贡献主要碰撞；
4. 修复候选是否消除了旧碰撞；
5. 修复是否引入新碰撞。

### 4.2 原子级碰撞定义

对配体原子 \(a_i\) 和蛋白原子 \(p_j\)：

\[
c_{ij}
=
\max
\left(
0,
 r_i^{vdW}+r_j^{vdW}-\delta-d(a_i,p_j)
\right)
\]

建议初始设置：

\[
\delta=0.4\text{ Å}
\]

原始碰撞集合：

\[
E^{clash}=\{(a_i,p_j):c_{ij}>0}\}
\]

总碰撞分数：

\[
S_{clash}=\sum_{(a_i,p_j)\in E^{clash}}c_{ij}^2
\]

### 4.3 R-group 级碰撞分数

\[
Score(R_k)
=
\sum_{a_i\in R_k}
\sum_{p_j\in P}
c_{ij}^2
\]

归一化：

\[
Score_\alpha(R_k)
=
\frac{Score(R_k)}{|R_k|^\alpha}
\]

建议：

\[
\alpha=0.5
\]

规则定位：

\[
\hat M=
\arg\max_k Score_\alpha(R_k)
\]

### 4.4 可靠验证器初始条件

候选 \(L_r\) 通过验证，当且仅当：

| 条件 | 建议初始阈值 |
|---|---:|
| 原碰撞消除 | 原始 clash score 降到 10% 以下 |
| 无新严重碰撞 | 新 severe clash 数量为 0 或低于阈值 |
| scaffold 保持 | scaffold RMSD < 0.5 Å |
| 非编辑区域保持 | non-edit RMSD < 0.8 Å |
| 分子自身合法 | RDKit sanitize 通过 |
| 几何合理 | 自定义几何检查或 PoseBusters 风格检查通过 |
| 修改局部性 | 主要变化发生在 edit mask 内 |
| 配体仍在 pocket | 修复后仍位于蛋白口袋中 |

### 4.5 阶段 1 产出

```text
src/clash2feedback/geometry/clash.py
src/clash2feedback/geometry/heatmap.py
src/clash2feedback/verifier/repair_verifier.py
reports/phase1_clash_detector/
```

### 4.6 阶段 1 通过标准

对人工局部碰撞样本，规则定位应满足：

| 指标 | 最低要求 |
|---|---:|
| dominant ratio 平均值 | > 0.75 |
| R-group Top-1 | > 70% |
| R-group Top-3 | > 90% |

如果达不到，不要继续接生成器，应回到阶段 0/2 检查数据拆分和人工注入。

---

## 5. 阶段 2：人工局部碰撞注入

### 5.1 目标

构建带真实失败区域标签的数据集，用于验证规则定位器和训练纠错器。

### 5.2 输入

来自阶段 0 的 clean complex：

\[
(P,L,S,\mathcal R,anchors)
\]

### 5.3 注入方式

第一版优先使用连接键旋转：

\[
\theta \in \{60^\circ,120^\circ,180^\circ,240^\circ,300^\circ}\}
\]

要求：

- scaffold 不动；
- 连接键不断；
- R-group 内部几何基本不变；
- 只改变局部空间占位。

### 5.4 保留样本条件

| 条件 | 阈值 |
|---|---:|
| scaffold RMSD | < 0.3 Å |
| 非扰动区域 RMSD | < 0.5 Å |
| 目标 R-group clash score / 总 clash score | > 0.7 |
| 分子内部严重碰撞 | 无 |
| protein-ligand severe clash | 至少 1 个 |

### 5.5 阶段 2 产出

```text
data/benchmarks/clashrepairbench_rg_artificial/v0_1/
  samples/
    sample_000001.pkl
    sample_000002.pkl
  manifest.parquet
reports/phase2_injection/
  injection_report.csv
  summary.json
```

每个样本包含：

| 字段 | 含义 |
|---|---|
| sample_id | 样本编号 |
| base_complex_id | 原始 clean complex |
| ligand_original | 原始配体 |
| ligand_failed | 人工失败配体 |
| true_failed_rgroup | 真实失败 R-group |
| old_clash_pairs | 原始碰撞原子对 |
| protein_clash_heatmap | 蛋白侧碰撞热区 |
| clash_severity | 碰撞严重度 |
| dominant_ratio | 单区域主导程度 |

---

## 6. 阶段 3：规则版 Clash2Feedback

### 6.1 目标

不训练模型，先验证：

> 规则定位器是否能从人工失败样本中找对失败 R-group？

### 6.2 规则反馈

输入：

\[
(P,L_f,\mathcal R)
\]

输出：

\[
F_t=(M_t,E_t^{old},C_t^{keep},H_t^{clash},s_t,\tau_t)
\]

其中：

\[
M_t=\arg\max_k Score_\alpha(R_k)
\]

\[
C_t^{keep}=S\cup(\mathcal R\setminus M_t)
\]

### 6.3 阶段 3 产出

```text
reports/phase3_rule_locator/
  rule_locator_results.csv
  summary.json
scripts/phase3_rule_locator.py
```

### 6.4 评估指标和通过标准

| 指标 | 含义 | 最低要求 |
|---|---|---:|
| R-group Top-1 Accuracy | 预测失败 R-group 是否正确 | > 70% |
| R-group Top-3 Accuracy | 真实失败 R-group 是否在前三 | > 90% |
| dominant ratio 平均值 | 单区域主导程度 | > 0.75 |
| Atom-level F1 | 失败原子级定位质量 | 观察 |
| Heatmap AUPRC | 蛋白碰撞热区质量 | 观察 |
| Severity MAE | 严重度误差 | 观察 |

---

## 7. 阶段 4：冻结生成器最小修复闭环

### 7.1 目标

验证闭环是否能跑通：

\[
\text{失败定位}
\rightarrow
\text{局部重画}
\rightarrow
\text{可靠验证}
\]

此阶段仍然不训练纠错器和排序器。

### 7.2 修复模式

第一版先做固定拓扑局部再生成：

\[
L_f
\rightarrow
\text{局部部分加噪}
\rightarrow
\text{去噪}
\rightarrow
L_r
\]

保持：

- 分子二维拓扑不变；
- scaffold 固定；
- 非失败 R-groups 固定；
- 只扰动失败 R-group。

如果生成器接口支持，再尝试 R-group inpainting：

\[
C_t^{keep}+\text{masked R-group}
\rightarrow
\text{new local group}
\]

### 7.3 第一批闭环配置

| 项 | 建议值 |
|---|---:|
| 人工失败样本 | 30–50 个 |
| 每个样本候选数 | \(K=8\) |
| 最大轮数 | \(T_{max}=1\) |
| 修复模式 | low-noise / mid-noise / high-noise |

### 7.4 最小对照

| 方法 | 含义 |
|---|---|
| Random mask | 随机选 R-group 重画 |
| Clash2Mask-rule | 只使用规则定位的 \(M_t\) |
| Clash2Feedback-rule | 使用 \(M_t+C_t^{keep}+s_t+\tau_t\) |
| Oracle mask | 使用真实失败 R-group |

### 7.5 阶段 4 产出

```text
runs/phase4_rule_repair/
  raw_candidates/
  logs/
reports/phase4_rule_repair/
  rule_repair_results.csv
  summary.json
scripts/phase4_rule_repair.py
```

### 7.6 通过标准

期望趋势：

\[
\text{Random mask}
<
\text{Clash2Mask-rule}
<
\text{Clash2Feedback-rule}
<
\text{Oracle}
\]

至少应在以下指标上出现方向性趋势：

| 指标 | 期望 |
|---|---|
| Old Clash Resolved Rate | Clash2Feedback 更高 |
| Reliable Repair Yield | Clash2Feedback 更高 |
| Non-edit RMSD | Clash2Feedback 更低 |
| New Clash Rate | Clash2Feedback 更低 |

---

## 8. 阶段 5：候选池与修复排序器

### 8.1 目标

证明排序器能减少“抽卡”，提高相同候选预算下的修复命中率。

### 8.2 候选池构建

对每个失败样本，枚举多个控制：

\[
u\in\{\text{low-noise},\text{mid-noise},\text{high-noise},\text{inpaint},\text{expand-mask}}\}
\]

每个控制生成：

\[
K_0=8
\]

保存字段：

```text
failed_sample_id
repair_candidate_id
control_mode
tau
edit_mask
keep_mask
candidate_sdf
old_clash_resolved
new_clash_count
scaffold_rmsd
non_edit_rmsd
geometry_valid
repair_label
repair_utility
```

### 8.3 排序器输入

排序器输入必须包含：

\[
(P,L_f,L_r,\mathcal B_t)
\]

其中 \(\mathcal B_t\) 至少包含：

\[
(M_t,C_t^{keep},H_t^{clash},s_t,\tau_t)
\]

不要只输入 \(L_r\)，否则会退化成普通分子筛选器。

### 8.4 阶段 5 产出

```text
data/candidate_pools/v0_1/
  train.parquet
  val.parquet
  test.parquet
runs/phase5_ranker/
  checkpoints/
  logs/
reports/phase5_ranker/
  ranker_results.csv
  summary.json
scripts/phase5_build_candidate_pool.py
scripts/phase5_train_ranker.py
```

### 8.5 评估

| 排序方式 | 目的 |
|---|---|
| Random candidate | 随机选 |
| Clash score only | 只看碰撞分数 |
| Docking score | 如果有 docking |
| Ranker without feedback | 不输入反馈 |
| Full repair ranker | 完整排序器 |

| 指标 | 含义 |
|---|---|
| Top-1 Repair Hit | 排名第一是否修复成功 |
| Top-3 Repair Hit | 前三是否有成功候选 |
| PR-AUC | 成功样本稀少时更重要 |
| Average Candidates to Success | 平均需要检查几个候选 |

---

## 9. 阶段 6：学习型纠错器

### 9.1 目标

训练模型预测：

\[
(P,L_f)
\rightarrow
(\hat M,\hat H^{clash},\hat s)
\]

即：

- 失败 R-group；
- 蛋白碰撞热区；
- 碰撞严重度。

### 9.2 输入图

| 节点 | 特征 |
|---|---|
| 配体原子 | 元素、芳香性、杂化、形式电荷、所属 R-group、范德华半径 |
| 蛋白原子 | 元素、残基类型、主链/侧链、范德华半径 |
| 边 | 共价键、空间近邻边、protein-ligand 近邻边 |
| 坐标 | 三维坐标 |

空间边建议：

\[
d_{ij}<6\text{ Å}
\]

或：

\[
d_{ij}<8\text{ Å}
\]

### 9.3 损失

\[
\mathcal L_{diag}
=
\lambda_M\mathcal L_{mask}
+
\lambda_H\mathcal L_{heat}
+
\lambda_s\mathcal L_{severity}
\]

其中：

\[
\mathcal L_{mask}=\text{CE}(\hat M,M^*)
\]

\[
\mathcal L_{heat}=\text{MSE}(\hat H,H^{clash})
\]

\[
\mathcal L_{severity}=\text{Huber}(\hat s,s)
\]

### 9.4 阶段 6 产出

```text
runs/phase6_critic/
  checkpoints/
  logs/
reports/phase6_critic/
  critic_results.csv
  summary.json
scripts/phase6_train_critic.py
```

### 9.5 通过标准

| 指标 | 要求 |
|---|---|
| R-group Top-1 | 接近或超过规则版 |
| Heatmap AUPRC | 高于简单距离 baseline |
| Severity MAE | 明显低于均值预测 |
| 下游修复率 | 不低于规则版定位 |

如果学习型纠错器不如规则版，不要硬把它作为主方法。

---

## 10. 阶段 7：学习型反馈适配器

### 10.1 目标

学习：

\[
\mathcal P_t^{repair}\rightarrow u_t
\]

也就是根据失败类型选择：

```text
小修 / 中修 / 大修 / inpainting / expand-mask / reject
```

### 10.2 标签构造

对每个失败样本，枚举控制集合：

\[
\mathcal U=\{u_1,u_2,\dots,u_m}\}
\]

每个控制生成候选并验证，得到平均修复价值：

\[
\bar U(u)
=
\frac{1}{K}
\sum_{i=1}^K
U(P,L_f,L_r^{(i)},\mathcal B_t)
\]

选择最优控制：

\[
u^*=\arg\max_{u\in\mathcal U}\bar U(u)
\]

如果多个控制都能修复，选择修改成本最低的。

### 10.3 阶段 7 产出

```text
runs/phase7_adapter/
  checkpoints/
  logs/
reports/phase7_adapter/
  adapter_results.csv
  summary.json
scripts/phase7_train_adapter.py
```

### 10.4 评估

| 方法 | 目的 |
|---|---|
| Rule adapter | 固定规则 |
| Learned adapter | 学习型适配器 |
| Oracle adapter | 最优控制上限 |

| 指标 | 含义 |
|---|---|
| Reliable Repair Yield | 可靠修复率 |
| Avg Candidates to Success | 成功平均候选数 |
| Reject Precision | 判断不可修是否准确 |
| EditCost | 是否避免过度修改 |

---

## 11. 阶段 8：模型诱导失败集测试

### 11.1 目标

验证方法不只适用于人工注入失败，也能处理真实生成模型产生的局部失败候选。

### 11.2 构造方式

1. 用冻结生成器在测试 pocket 上生成候选；
2. 用验证器筛出存在 protein-ligand clash 的候选；
3. 只保留局部 R-group 主导的失败样本：

\[
\frac{Score(M_t)}{Score_{total}}>0.7
\]

4. 排除 scaffold 整体错位和分子自身非法样本；
5. 用规则定位或学习型纠错器产生 \(M_t\)；
6. 使用完整 Clash2Feedback-GC 流程尝试修复。

### 11.3 阶段 8 产出

```text
data/benchmarks/model_induced/v0_1/
  samples/
  manifest.parquet
runs/phase8_model_induced/
  raw_candidates/
  logs/
reports/phase8_model_induced/
  model_induced_results.csv
  summary.json
scripts/phase8_model_induced_eval.py
```

### 11.4 评估指标

| 指标 | 含义 |
|---|---|
| Old Clash Resolved Rate | 原碰撞消除率 |
| No New Clash Rate | 无新碰撞率 |
| Reliable Repair Yield | 可靠修复率 |
| Geometry Valid Rate | 几何合法率 |
| Avg Candidates to Success | 平均候选数 |

---

## 12. 推荐 Mini-Loop 执行顺序

### Mini-Loop 0：不调用生成器

目标：验证数据、拆分、检测、注入、定位。

```text
20 个 clean complexes
→ scaffold / R-group 拆分
→ 每个 complex 注入 3–5 个局部 clash
→ 生成 60–100 个失败样本
→ 规则 locator 定位失败 R-group
→ 计算 Top-1 / Top-3
```

通过标准：

| 指标 | 目标 |
|---|---:|
| 有效人工失败样本比例 | > 50% |
| 单区域主导比例 | > 70% |
| 规则 locator Top-1 | > 70% |
| 规则 locator Top-3 | > 90% |

### Mini-Loop 1：调用生成器但不训练模型

目标：验证局部修复是否可能。

```text
选择 30–50 个人工失败样本
→ Random mask / Clash2Mask / Clash2Feedback / Oracle
→ 每个样本 K=8
→ T_max=1
→ 用验证器判断修复是否成功
```

期望趋势：

\[
\text{Random mask}<\text{Clash2Mask}<\text{Clash2Feedback}<\text{Oracle}
\]

### Mini-Loop 2：候选池和排序器

目标：证明排序器能减少抽卡。

```text
每个失败样本枚举 low / mid / high / inpaint / expand
→ 每种 K=8
→ 得到候选池
→ 验证器打标签
→ 训练 ranker
→ 比较 random / clash-only / full-ranker
```

通过标准：

| 指标 | 目标 |
|---|---:|
| Full ranker Top-1 Hit | 高于 random |
| Full ranker Top-3 Hit | 高于 clash-only |
| Ranker without feedback | 低于 full ranker |

### Mini-Loop 3：学习型适配器

目标：证明通信机制可学习。

```text
对每个失败样本枚举多个修复控制
→ 选择验证器表现最好的控制作为标签
→ 训练 adapter
→ 对比 rule adapter / learned adapter / oracle adapter
```

通过标准：

| 指标 | 目标 |
|---|---:|
| learned adapter | 不低于 rule adapter |
| learned adapter | 尽量靠近 oracle adapter |
| 平均候选数 | 下降 |
| reject precision | 有意义 |

---

## 13. 推荐代码结构

以下代码结构与阶段 0 工程方案完全一致。


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


### 关键说明

- 根目录统一为 `clash2feedback_gc/`。
- Python 包统一为 `src/clash2feedback/`，不要把包名写成 `clash2feedback_gc`。
- 静态文档统一放入 `docs/`。
- 实验结果报告统一放入 `reports/`。
- 训练和生成的重运行产物统一放入 `runs/`。
- 不再使用 `outputs/` 作为顶层目录，避免和 `reports/`、`runs/` 混淆。
- 不再在 `src/` 里放 `experiments/` 作为入口，所有阶段入口统一放在 `scripts/phaseN_*.py`。

---

## 14. 关键决策点

### 决策点 1：阶段 0 数据是否干净？

如果 clean complex 数量不足，先不要做人为注入和模型训练。

排查：

- ligand 是否能被 RDKit 解析；
- pocket 是否非空；
- 原始样本是否已有严重碰撞；
- scaffold 和 R-groups 是否拆分失败。

### 决策点 2：规则定位是否有效？

如果规则 Top-1 很高：

> 学习型纠错器可以作为增强。

如果规则 Top-1 很低：

> 先修数据、碰撞定义和 R-group 拆分，不要急着训练模型。

### 决策点 3：冻结生成器是否能稳定保持 keep 区域？

如果不能：

\[
\text{full R-group inpainting}
\rightarrow
\text{fixed-topology partial noising}
\]

先做固定拓扑局部姿态修复。

### 决策点 4：Clash2Feedback 是否强于 Clash2Mask？

如果只比 mask 强一点点，需要强化：

- keep 区域保持实验；
- severity-response 曲线；
- 旧碰撞热区验证；
- 排序器是否利用反馈信息。

### 决策点 5：学习型 adapter 是否强于规则 adapter？

如果没有明显强于规则版，可以不把它放主方法。

论文可以写成：

> 规则反馈协议 + 学习型定位器 + 修复排序器。

学习型 adapter 作为探索性实验。

---

## 15. 当前最应该做的 7 件事

现在应该先做阶段 0，而不是训练模型。

推荐顺序：

1. 建立 raw complex 目录结构；
2. 实现 protein / ligand 读取；
3. 实现 ligand sanity check；
4. 实现 pocket extraction；
5. 实现 scaffold / R-group / anchor 拆分；
6. 保存 processed sample 和 manifest；
7. 做基础原始碰撞 sanity check，筛出 clean complex。

正式碰撞检测器、人工注入和规则 locator 放到阶段 1–3。

---

## 16. 最终建议

当前实验入口应该是：

\[
\boxed{
\text{阶段 0：环境与数据格式打通}
}
\]

而不是：

```text
训练纠错器
```

也不是：

```text
训练生成模型
```

最合理推进顺序：

\[
\boxed{
\text{数据底座}
\rightarrow
\text{碰撞检测器}
\rightarrow
\text{人工失败数据}
\rightarrow
\text{规则定位}
\rightarrow
\text{冻结生成器闭环}
\rightarrow
\text{排序器}
\rightarrow
\text{学习型纠错器}
\rightarrow
\text{学习型适配器}
}
\]

这样每一步失败时都能定位问题来源，不会把数据、验证器、生成器接口和学习模型全部混在一起。
