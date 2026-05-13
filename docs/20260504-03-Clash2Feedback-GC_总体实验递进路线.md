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
\text{标签溯源与 mask seed 审计}
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
| 阶段 2 | 人工局部碰撞注入 | 构建带人工 target R-group 标签的 controlled repair substrate | 否 | 否 | ClashRepairBench-RG-artificial | `data/benchmarks/clashrepairbench_rg_artificial/v0_1/` |
| 阶段 2.5 | 模型诱导失败外部有效性审计 | 审计 frozen generation baseline 的真实 failure distribution, 判断阶段 2 artificial benchmark 覆盖的真实失败子分布 | 否 | 是, 仅 frozen inference | model-induced failure taxonomy / gap analysis | `reports/phase2_5_model_induced_audit/`, `runs/phase2_5_model_induced_audit/` |
| 阶段 3 | 标签溯源、循环验证风险审计与阶段 4 mask seed 生成 | 审计 phase2 标签来源和 attribution gate 依赖, 冻结 operational mask policy | 否 | 否 | provenance audit, construction consistency check, phase4 mask seed | `reports/phase3_label_provenance_audit/` |
| 阶段 4 | backend feasibility audit 与局部修复闭环 | 先验证 repair backend 可用, 再比较 Random / Predicted / Oracle mask 的 downstream repair utility | 否 | 是 | backend feasibility, formal repair loop | `runs/phase4_0_backend_feasibility/`、`reports/phase4_0_backend_feasibility/`、`runs/phase4_local_repair_loop/`、`reports/phase4_local_repair_loop/` |
| 阶段 5 | 候选池与修复排序器 | 训练排序器，从多个候选中选最可能成功的修复 | 是 | 是 | candidate pool、ranker | `data/candidate_pools/v0_1/`、`runs/phase5_ranker/` |
| 阶段 6 | 学习型纠错器 | 学习预测失败区域、碰撞热区和严重度 | 是 | 可选 | learned critic | `runs/phase6_critic/`、`reports/phase6_critic/` |
| 阶段 7 | 学习型反馈适配器 | 学习把修复协议转成生成器可执行控制 | 是 | 是 | learned adapter | `runs/phase7_adapter/`、`reports/phase7_adapter/` |
| 阶段 8 | 模型诱导失败集测试 | 验证方法不只适用于人工注入失败 | 是 | 是 | model-induced repair results | `data/benchmarks/model_induced/v0_1/`、`reports/phase8_model_induced/` |

长期第一篇完整版本可争取完成：

\[
\boxed{
\text{阶段 0--5}
+
\text{阶段 6--7 作为增强}
+
\text{阶段 8 小规模验证}
}
\]

当前短期执行优先级仍是：

1. 阶段 3: label provenance audit + circularity risk audit + phase4 mask seed generation.
2. 阶段 4.0: backend feasibility audit.
3. 阶段 4.1: Random / Predicted / Oracle formal repair loop.
4. 阶段 5/6/7: 只有在阶段 4.1 得到稳定 repair outcomes 后, 再推进 ranker, learned critic 和 learned adapter.

---

## 3. 阶段 0：环境与数据格式打通

### 3.1 目标

阶段 0 的目标是：

> 让蛋白质—配体复合物可以被稳定读取、处理、保存和检查，为后续碰撞检测、人工注入、标签溯源和生成修复打基础。

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
src/clash2feedback/geometry/vdw.py
src/clash2feedback/geometry/clash.py
src/clash2feedback/geometry/rgroup_attribution.py
src/clash2feedback/geometry/clash_types.py
src/clash2feedback/verifier/repair_verifier.py
reports/phase1_clash_detector/
```

### 4.6 Receptor scope 口径

阶段 1 detector 必须显式记录 `receptor_scope`. 当前 phase0 主数据的 CrossDocked / IF3 样本通常来自 `*_pocket10.pdb`, 因此阶段 1 默认支持两种局部作用域:

| scope | 来源 | 用途 |
|---|---|---|
| `phase0_pocket8` | 阶段 0 从当前 `protein.pdb` 中按 ligand heavy atoms 周围 8 Å 提取的 pocket | old clash diagnosis 和 R-group attribution |
| `pocket10_all_atoms` | 当前 processed sample 中的 `protein` 全部原子; 当前通常是数据源预裁剪的 pocket10 | repair candidate 的 local new clash check |

`full_receptor_dynamic_shell` 仅作为后续预留作用域. 若后续补齐 full receptor, 可围绕 repaired ligand 当前坐标动态提取 10-12 Å protein shell 做最终检查. Full receptor 不作为阶段 1-3 的 hard dependency; 阶段 4 可作为 shadow check, 阶段 5 可进入 candidate label, 阶段 8 建议作为 final full-receptor checked metric.

### 4.7 Failure type 分类

阶段 1 不只输出是否有 clash, 还应输出 `failure_type`:

| 条件 | failure_type | 第一版动作 |
|---|---|---|
| 无 severe clash | `no_clash` | no repair needed |
| 单个 valid R-group 主导, dominant ratio >= 0.7 | `single_rgroup_clash` | local R-group repair |
| 0.5 <= dominant ratio < 0.7 | `ambiguous_region_clash` | reject 或 hard split |
| 多个 R-groups 明显贡献 clash | `multi_region_clash` | 第一版 reject, 后续 expand-mask / sequential repair |
| scaffold score 最高 | `scaffold_clash` | reject |
| ligand 多区域整体偏移 | `global_pose_failure` | full resampling 或 reject |
| covalent / metal / unsupported chemistry | `unsupported_chemistry` | reject |

第一篇主指标聚焦 `single_rgroup_clash`. 其他类型应识别, 统计和单独报告, 不进入 single-R-group repair 主指标.

### 4.8 阶段 1 通过标准

阶段 1 自身不以人工注入样本上的 R-group Top-1 / Top-3 作为关闭条件, 因为人工失败样本来自阶段 2. 阶段 3 会把这些指标降级为 construction consistency check, 并同步审计循环验证风险.

阶段 1 关闭条件:

| 指标 | 最低要求 |
|---|---:|
| 51 个 clean pool 样本可检测 | 100% |
| `phase0_balanced_30_v0_1` 可检测 | 100% |
| 支持 `phase0_pocket8` 和 `pocket10_all_atoms` | 是 |
| 输出 pair-level clash report | 是 |
| 输出 R-group attribution report | 是 |
| 输出 failure type counts | 是 |
| `δ = 0.3, 0.4, 0.5` sensitivity 已完成 | 是 |
| clean pool severe false positive | 尽量接近 0, 若非 0 需逐例解释 |
| verifier clean-vs-clean smoke test | 100% 或逐例解释 |
| `python -m compileall src scripts` 和 `pytest` | 通过 |

人工注入样本上的 Top-1 / Top-3 不再作为阶段 3 independent locator benchmark:

| 项 | 阶段 3 新口径 |
|---|---|
| dominant ratio | construction consistency / data health observation |
| R-group Top-1 | construction consistency check |
| R-group Top-3 | construction consistency check |

---

## 5. 阶段 2：人工局部碰撞注入

### 5.1 目标

阶段 2 构建带真实 target R-group 标签的 controlled synthetic failed pose benchmark。它从阶段 1 验收过的 clean protein-ligand pose 出发，只扰动一个合法 target R-group，构造 ligand 自身合理、但 target R-group 与 protein 发生 severe clash 的失败样本。

阶段 2 不训练模型、不调用生成器、不做 repair、不做 whole protein-ligand complex minimization。其目标是造数据，而不是证明修复成功。最终执行口径详见 `docs/20260510-Clash2Feedback-GC_阶段2人工局部碰撞注入最终落地方案.md`。

### 5.2 输入

来自阶段 0 的 clean complex：

\[
(P,L,S,\mathcal R,anchors)
\]

### 5.3 注入方式

第一版按优先级实现三种受控扰动：

1. `easy_rotation`：围绕合法 scaffold-R-group anchor bond 旋转 target R-group；
2. `torsion_perturb`：扰动 target R-group 内部可旋转键，固定 scaffold 和 anchor；
3. `directed_clash`：朝 protein hotspot 方向定向扰动，用于构造 mild / medium / severe 难度。

要求：

- scaffold 不动；
- 连接键不断；
- R-group 内部几何基本不变；
- 只改变局部空间占位。

连接键旋转构造的是 controlled synthetic failed pose, 不应表述为真实稳定结合构象. 第一版只应围绕化学上可旋转的 single bond 或合法内部 torsion 做扰动, 并过滤 ligand internal severe clash, 高能不合理构象, multi-region clash 和 scaffold drift. `fragment_replace`, `hard_multi_region` 和 bulky replacement 暂缓到 phase2b。

### 5.4 保留样本条件

| 条件 | 阈值 / 要求 |
|---|---:|
| RDKit sanitize | pass |
| anchor bond | 合法 rotatable single bond |
| ligand internal severe clash | 0 |
| anchor integrity | pass |
| scaffold RMSD | < 0.3 Å |
| 非扰动区域 RMSD | < 0.5 Å |
| target score ratio valid | >= 0.7 |
| protein-ligand severe clash | 至少 1 个 |
| scaffold severe pairs | 0 |
| non-target severe pairs | 0 |
| max clash depth | 第一版建议 <= 1.5 Å |

RDKit MMFF / UFF 只能作为 ligand-only energy delta 粗筛, 不用于优化 protein-ligand complex。

### 5.5 阶段 2 split

阶段 2 产出分层：

| split | 用途 |
|---|---|
| `supported_single_rgroup` | 阶段 3 label provenance audit / construction consistency check, 阶段 4 clean local repair substrate |
| `ambiguous_region` | hard / reject split |
| `multi_region` | reject split |
| `scaffold_clash` | reject split |
| `global_pose_failure` | reject split |
| `near_miss_contact` | 不进主集 |
| `invalid_conformer` | ligand 自身不合理, 丢弃但统计 |
| `unsupported` | 化学或 mask 不支持 |
| `duplicate_removed` | 重复样本, 不进主集 |

### 5.6 阶段 2 产出

```text
data/benchmarks/clashrepairbench_rg_artificial/v0_1/
  manifest.parquet
  schema.json
  samples/
  ligands/
reports/phase2_injection/
  summary.json
  injection_attempts.csv
  phase2_completion_audit.md
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

标签使用边界:

- `target_rgroup` 是人工扰动时选定并实际扰动的 R-group.
- `supported_single_rgroup` 不是无偏 locator benchmark. 它是经过 ligand quality, detector, R-group attribution, `target_score_ratio_valid >= 0.7`, non-target / scaffold no-severe 和 max-depth gates 过滤后的 clean local repair substrate.
- `target_score_ratio_valid` 来自 attribution-derived valid R-group scores. 因此后续在该主集上复用同一 attribution 规则计算 Top-1 / Top-3, 只能作为 construction consistency check, 不能作为 independent localization accuracy.

### 5.7 阶段 2.5 模型诱导失败外部有效性审计

阶段 2.5 使用 frozen DiffSBDD baseline 做 model-induced failure external validity audit. 它先对 phase0/phase1 clean pockets 做 training-overlap audit, 再在可解释的 base pockets 上生成 candidates, 并对 all generated samples 做 ligand validity, protein-ligand clash, R-group attribution, failure taxonomy, repairability proxy 和 artificial-vs-model-induced gap analysis.

阶段 2.5 不训练模型, 不做 repair, 不调参, 不做 baseline ranking, 不回改 `phase2_v0_1`. Generated ligand 没有人工 `target_rgroup`; predicted dominant R-group 只能作为 candidate local repair region, 不能作为 oracle ground truth, 也不进入阶段 3 construction consistency denominator.

如果 DiffSBDD 仓库, checkpoint, official split, GPU 或数据缺失, 阶段 2.5 必须明确写 blocked 原因, 不编造 generation / taxonomy 结果. 阶段 2.5 不阻塞阶段 3; 阶段 2.5 的 model-induced samples 不进入阶段 3 的 construction consistency denominator.

---

## 6. 阶段 3：标签溯源、循环验证风险审计与阶段 4 mask seed 生成

### 6.1 目标

阶段 3 仍叫阶段 3, 但不再承担 independent locator benchmark 职责. 阶段 3 的目标是:

1. 审计 `phase2_v0_1` 中 `target_rgroup` 和 `supported_single_rgroup` 的标签来源.
2. 明确 detector / attribution / target-dominance gates 对 supported 主集的影响.
3. 报告 circularity risk, 避免把同一套 attribution gate 筛出的样本再用于无偏证明同一 locator.
4. 冻结现有 `detect_clashes()` + `attribute_clashes_to_rgroups()` 作为阶段 4 的 predicted mask policy.
5. 生成阶段 4 需要的 oracle / predicted / random masks.

### 6.2 标签边界

阶段 2 的 `target_rgroup` 是人工扰动标签:

```text
人工选择 target R-group
→ 对该 R-group 做 controlled perturbation
→ 保存 target_rgroup
```

但 `supported_single_rgroup` 是经过自动 gates 后得到的 clean local repair substrate:

```text
ligand quality
→ protein-ligand clash detector
→ R-group attribution
→ target_score_ratio_valid >= 0.7
→ non-target / scaffold no-severe
→ max_depth gate
→ supported_single_rgroup
```

其中 `target_score_ratio_valid` 来自 attribution-derived valid R-group scores. 因此, 在 `supported_single_rgroup` 上继续用同一套 attribution 规则计算 Top-1 / Top-3, 只能说明构造过程内部一致, 不能说明 locator 的无偏泛化定位能力.

### 6.3 阶段 3 产出

```text
reports/phase3_label_provenance_audit/
  phase2_label_provenance_audit.md
  circularity_risk_audit.md
  construction_consistency_report.csv
  locator_stress_report_s0.csv
  locator_stress_report_s1.csv
  phase4_mask_seed.csv
  summary.json
  phase3_completion_audit.md
scripts/phase3_label_provenance_audit.py
```

### 6.4 Construction Consistency Check

阶段 3 可以在 `supported_single_rgroup` 上报告 Top-1 / Top-3, 但表述必须改为 construction consistency check:

| 项 | 口径 |
|---|---|
| Top-1 / Top-3 | construction consistency check, 非 independent localization benchmark |
| Coverage | operational policy 覆盖率 |
| Circularity risk | 明确 gate 与评估方法共享 detector / attribution 的程度 |
| Phase4 mask seed completeness | oracle / predicted / random masks 是否可用于阶段 4 |
| Stress split | reject / unsupported / ambiguous 等分流和敏感性分析 |

旧的通过标准需要降级:

```text
R-group Top-1 > 70%
R-group Top-3 > 90%
dominant ratio valid mean > 0.75
```

这些数字可作为内部构造一致性和数据健康度观察项, 不作为阶段 3 关闭条件或论文主 claim.

---

## 7. 阶段 4：backend feasibility audit 与局部修复闭环

### 7.1 目标

阶段 4 的核心 claim 是 downstream repair utility:

```text
在同一 repair backend 和同一 candidate budget 下,
Predicted mask repair 是否优于 size-matched Random mask repair,
并接近 Oracle mask repair.
```

阶段 4 的 predicted mask 来自现有 `detect_clashes()` + `attribute_clashes_to_rgroups()` 和 `dominant_valid_rgroup` / `top_valid_rgroups`. 它是 operational mask policy, 不是 ground truth, 也不是 verifier.

### 7.2 阶段 4.0 backend feasibility audit

正式闭环前先用 oracle mask 检查后端是否可用:

```text
reports/phase4_0_backend_feasibility/
  backend_feasibility_summary.json
  backend_feasibility_cases.csv
  backend_candidate_manifest.csv
  verifier_outcome.csv
  blocked_backends.md
  phase4_0_completion_audit.md
runs/phase4_0_backend_feasibility/
  diffdec/
  diffsbdd_inpainting/
  rule_only/
  full_resampling/
  logs/
```

重点问题是:

```text
给正确 oracle mask, 后端能否稳定生成候选,
接回 anchor, 保持 scaffold / keep region,
并通过 reliable repair verifier?
```

DiffDec / DiffSBDD plain backend 在此阶段只能表述为 local constrained resampling 或 candidate inpainting backend. 除非实现 clash penalty / hot region guidance 并修改 sampling / denoising loop, 否则不得声称 `H_clash` 直接进入生成过程或完整 feedback-guided denoising.

### 7.3 阶段 4.1 Random / Predicted / Oracle formal repair loop

后端通过 feasibility audit 后, 再做正式对照:

| 方法 | 口径 |
|---|---|
| Random mask | size-matched random R-group mask |
| Predicted mask | operational mask policy 输出的 repair mask |
| Oracle mask | 人工 `target_rgroup` 对应 mask, 只作为上限 |

成功标准由 verifier 判断, 不能由 locator 自证:

```text
old clash resolved
no new severe clash
ligand validity
scaffold RMSD
non-mask RMSD
anchor consistency
fixed-region preservation
```

阶段 4.1 产出:

```text
reports/phase4_local_repair_loop/
  summary.json
  repair_candidate_manifest.csv
  repair_outcome.csv
  verifier_report.csv
  baseline_comparison.csv
  locality_metrics.csv
  failure_cases.csv
  phase4_completion_audit.md
runs/phase4_local_repair_loop/
  raw_candidates/
  standardized_candidates/
  logs/
```

### 7.4 阶段 4.2 可选 clash-guided denoising prototype

如果要证明 `H_clash` / hot region feedback 进入生成过程, 需要实现 guided sampling:

```text
clash penalty
hot region guidance
sampling / denoising loop patch
```

在未实现这些机制前, 文档只能说 `H_clash` 参与 verifier / selector / adapter 输入, 不能说它直接指导 diffusion denoising.

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
\mathcal L_{mask}=\text{CE}(\hat M,M_{label})
\]

其中 \(M_{label}\) 必须来自阶段 3 审计后的标签口径. 对 phase2 artificial supported set, 可用 `target_rgroup` 作为人工注入标签; 对 attribution-derived policy, 只能作为 construction consistency 或后续无泄漏评估的候选标签, 不能把 `Score_\alpha` 定义成 independent ground truth.

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
| R-group Top-1 / Top-3 | 仅在无泄漏或明确标注 construction-consistency 的设置下报告 |
| Heatmap AUPRC | 高于简单距离 baseline |
| Severity MAE | 明显低于均值预测 |
| 下游修复率 | 不低于 operational mask policy baseline |

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

阶段 2.5 只审计 model-induced failures 的分布, 不做 repair; 阶段 8 才评估 model-induced failures 上的完整修复流程和 Reliable Repair Yield.

### 11.2 构造方式

1. 用冻结生成器在测试 pocket 上生成候选；
2. 用验证器筛出存在 protein-ligand clash 的候选；
3. 只保留局部 R-group 主导的失败样本：

\[
\frac{Score(M_t)}{Score_{total}}>0.7
\]

4. 排除 scaffold 整体错位和分子自身非法样本；
5. 用 operational mask policy 或学习型纠错器产生 \(M_t\)；
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

目标：验证数据、拆分、检测、注入、标签溯源和阶段 4 mask seed。

```text
20 个 clean complexes
→ scaffold / R-group 拆分
→ 每个 complex 注入 3–5 个局部 clash
→ 生成 60–100 个失败样本
→ 审计 supported_single_rgroup 的 gate 依赖
→ 生成 phase4_mask_seed.csv
→ 将 Top-1 / Top-3 降级为 construction consistency check
```

通过标准：

| 指标 | 目标 |
|---|---:|
| 有效人工失败样本比例 | > 50% |
| 单区域主导比例 | > 70% |
| phase2 label provenance audit | 完成 |
| circularity risk level | 明确 |
| phase4_mask_seed.csv | 生成 |
| supported set Top-1 / Top-3 | 仅报告 construction consistency, 不设 independent locator 关闭线 |

### Mini-Loop 1：调用生成器但不训练模型

目标：先验证 backend feasibility, 再比较 mask policy 的下游修复价值。

```text
选择 30–50 个人工失败样本
→ 阶段 4.0 用 Oracle mask 做 backend feasibility audit
→ 阶段 4.1 比较 Random mask / Predicted mask / Oracle mask
→ 每个样本 K=8
→ T_max=1
→ 用验证器判断修复是否成功
```

期望趋势：

\[
\text{Random mask}<\text{Predicted mask}<\text{Oracle mask}
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

### 决策点 2：阶段 3 标签溯源是否清楚？

如果 label provenance 清楚且 circularity risk 已被明确标记：

> 冻结现有 attribution 作为阶段 4 operational mask policy, 进入 backend feasibility audit。

如果 gate 依赖, label provenance 或 mask seed 不清楚：

> 先修阶段 2 构造记录、碰撞定义和 R-group attribution 审计, 不要把 Top-1 / Top-3 写成独立定位能力。

### 决策点 3：冻结生成器是否能稳定保持 keep 区域？

如果不能：

\[
\text{full R-group inpainting}
\rightarrow
\text{fixed-topology partial noising}
\]

先做固定拓扑局部姿态修复。

### 决策点 4：Predicted mask 是否强于 Random mask？

如果 Predicted mask repair 不能优于 size-matched Random mask repair, 需要先排查：

- keep 区域保持实验；
- verifier 是否过严或过松；
- backend 是否无法尊重 mask / anchor / keep region；
- predicted mask policy 是否过窄或过宽；
- candidate budget 是否不足。

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

正式碰撞检测器、人工注入和标签溯源 / mask seed 审计放到阶段 1–3。

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
\text{标签溯源与 mask seed}
\rightarrow
\text{backend feasibility 与修复闭环}
\rightarrow
\text{排序器}
\rightarrow
\text{学习型纠错器}
\rightarrow
\text{学习型适配器}
}
\]

这样每一步失败时都能定位问题来源，不会把数据、验证器、生成器接口和学习模型全部混在一起。
