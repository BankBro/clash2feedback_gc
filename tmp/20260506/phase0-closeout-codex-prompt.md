# 20260506 Phase 0 Closeout Codex Prompt

请继续在 GitHub 仓库 `BankBro/clash2feedback_gc` 的分支 `20260505-180108-phase0-implementation` 上完成阶段 0 的收尾实验和最终检查。

当前任务范围只包括阶段 0。不要进入阶段 1，不要实现正式 `vdW clash detector`，不要实现 `repair verifier`，不要做人为 clash 注入，不要接 DiffSBDD / TargetDiff / Pocket2Mol / PocketXMol 等生成器，不要引入 PyTorch / CUDA / 生成器权重。

本轮目标不是扩大数据集，而是对已经完成的阶段 0 结果做最终确认、风险记录、偏差说明、`balanced subset` 派生、人工可视化抽查，并形成可以进入阶段 1 前的最终阶段 0 收尾报告。

---

## 一、开始前先检查状态

请先执行并记录：

```bash
git status
git log --oneline -5
```

确认当前分支是：

```text
20260505-180108-phase0-implementation
```

如果工作区不干净，先说明有哪些未提交修改，不要覆盖已有修改。

---

## 二、优先阅读这些文件

请按顺序阅读：

1. `README.md`
2. `tmp/20260506/phase0-web-chatgpt-context.md`
3. `tmp/20260506/phase0-final-summary.md`
4. `docs/20260505-Clash2Feedback-GC_阶段0工程方案.md`
5. `docs/20260504-03-Clash2Feedback-GC_总体实验递进路线.md`
6. `docs/20260504-01-Clash2Feedback-GC_完整方案与升级路线.md`
7. `docs/20260504-02-Clash2Feedback-GC_第一篇论文实验方案.md`
8. `configs/phase0.yaml`
9. `scripts/phase0_prepare_diffsbdd_examples.py`
10. `scripts/phase0_prepare_crossdocked_subset.py`
11. `scripts/phase0_build_processed.py`
12. `scripts/phase0_check_dataset.py`
13. `scripts/phase0_make_splits.py`
14. `src/clash2feedback/data/prepare_raw_complexes.py`
15. `src/clash2feedback/data/build_processed_dataset.py`
16. `src/clash2feedback/data/check_dataset.py`
17. `src/clash2feedback/data/split_dataset.py`
18. `src/clash2feedback/chemistry/rgroup.py`
19. `src/clash2feedback/geometry/basic_clash_screen.py`
20. `tests/`

阅读后先用中文简要确认当前阶段 0 状态：

- 阶段 0 工程底座已完成；
- DiffSBDD official example smoke 已复现；
- IF3 / CrossDocked pocket10 数据已自动获取并整理；
- 当前 `phase0 usable clean` 样本数为 51；
- `pytest` 为 17 passed；
- 当前仍需要完成阶段 0 收尾：target-balanced benchmark manifest、人工可视化抽查、偏差说明和最终收尾报告。

---

## 三、当前阶段 0 结果的评价口径

请在最终报告中采用下面口径，不要夸大：

1. 阶段 0 可以认为“工程验收通过”。
2. 51 个 clean samples 不需要删除。
3. 51 个 clean samples 应作为：

```text
phase0_clean_pool_v0_1
```

4. 后续阶段 1–3 的 mini-loop 不建议直接使用全部 51 个，而应派生一个更均衡的小集合：

```text
phase0_balanced_30_v0_1
```

5. 当前 target 分布不均，不是阶段 0 失败，但对后续实验是潜在偏差。
6. `ligand-only scaffold/R-group` 预筛是合理的任务特化预筛，但会引入选择偏差，必须在报告中声明。
7. `basic_clash_screen` 只表示 `obvious severe clash sanity gate` 通过，不等价于正式 `vdW clash detector`。
8. `pocket10` 是 pocket-level protein structure，不是 full receptor，应在报告中说明。
9. 进入阶段 1 前必须补人工可视化抽查，不要直接进入阶段 1。

---

## 四、需要重点说明的潜在风险

请在最终报告中明确列出并解释这些风险。

### 1. target 分布不均

当前 51 个 clean 样本中，SMYD2 和 CDGT2 占比较高。需要说明：

- 这不是阶段 0 工程错误；
- 但如果后续直接用全部 51 个样本，实验结果可能主要反映少数 target；
- 因此建议派生 target-balanced subset。

### 2. 流式扫描顺序偏差

当前 IF3 archive 是流式扫描并凑够 50 个 clean 后停止。需要说明：

- 流式扫描合理，因为节省磁盘和时间；
- 但顺序扫描可能受 archive 文件顺序影响；
- 后续重新采样时建议使用 `target-aware streaming selection`。

### 3. ligand-only scaffold/R-group 预筛偏差

当前预筛会偏向：

- 可 Murcko scaffold 拆分的配体；
- 至少有 2 个 valid R-groups 的配体；
- 单锚点 R-group 较清楚的配体。

需要说明：

- 这对 Clash2Feedback-GC 的 R-group 局部修复任务是合理的；
- 但它不是无偏 CrossDocked 子集；
- 后续论文或报告中应称为 `task-specific clean subset`，而不是 `unbiased CrossDocked subset`。

### 4. basic_clash_screen 的边界

需要说明：

- 当前 `basic_clash_screen` 只过滤明显严重原始重叠；
- 它不使用元素相关范德华半径；
- 它不计算正式 clash depth；
- 它不输出 R-group clash score；
- 它不能替代阶段 1 的正式 clash detector。

### 5. pocket10 的边界

需要说明：

- 当前 IF3 archive 使用 pocket10；
- pocket10 是 ligand 周围约 10 Å 的蛋白口袋子结构；
- 它不是完整蛋白；
- 对阶段 0 和局部 clash 修复任务通常足够；
- 如果后续生成器或外部验证需要 full receptor，需要另行处理。

---

## 五、生成 `phase0_balanced_30_v0_1`

请新增或完善一个脚本，用于从 51 个 clean samples 中派生 target-balanced 小 benchmark。

建议脚本：

```text
scripts/phase0_make_balanced_manifest.py
```

输入：

```text
--manifest data/processed/v0_1/manifest.parquet
--visual-check reports/phase0/visual_check_list.csv
--output data/splits/v0_1/phase0_balanced_30.txt
--summary tmp/20260506/phase0-balanced30-summary.md
--max-samples 30
--min-samples 20
--max-per-target 5
--seed 20260504
```

如果 `reports/phase0/visual_check_list.csv` 不存在，则先运行 `phase0_check_dataset.py` 生成。

选择规则建议：

1. 只从 `phase0_usable = true` 的样本中选；
2. 优先按 `target_id` / `split_group` 分桶；
3. 每个 target 最多选择 4–5 个；
4. 尽量覆盖更多 target；
5. 优先选择人工可视化检查 pass 的样本；
6. 如果没有人工检查结果，优先选择 visual_check_list 中 priority 高的样本用于检查，不要直接假设通过；
7. 尽量覆盖 ligand heavy atoms、pocket atoms、valid R-groups 的不同范围；
8. 不破坏原 manifest，不删除 51 个 clean pool；
9. 输出只是一个派生清单，不替代原始 phase0 clean pool。

输出：

```text
data/splits/v0_1/phase0_balanced_30.txt
tmp/20260506/phase0-balanced30-summary.md
```

summary 至少包含：

- clean pool 总数；
- balanced subset 数量；
- target 分布；
- 每个 target 选择数量；
- ligand heavy atoms 分布；
- pocket atoms 分布；
- valid R-groups 分布；
- 是否覆盖至少 6 个 target；
- 是否满足每个 target 最多 4–5 个；
- 是否使用了人工检查结果；
- 如果不能达到 20–30 个，解释原因。

注意：

- `data/splits/v0_1/phase0_balanced_30.txt` 如果 `.gitignore` 忽略，不强行提交；
- 需要把关键统计写入 `tmp/*.md`，可提交轻量 Markdown 摘要。

---

## 六、人工可视化抽查由你协助完成

请不要只生成清单就结束。本轮需要你尽可能完成或辅助完成人工可视化抽查。

目标：

- 至少检查 5 个 high-priority 样本；
- 更稳妥地检查 8–10 个样本；
- 优先检查 `reports/phase0/visual_check_list.csv` 中推荐的 high-priority 样本；
- 当前已知前 5 个 high-priority 样本为：
  - `complex_crossdocked_000001`
  - `complex_crossdocked_000002`
  - `complex_crossdocked_000003`
  - `complex_crossdocked_000004`
  - `complex_crossdocked_000005`

请优先尝试以下方式：

1. 如果本地有 PyMOL，生成并运行 headless PyMOL 脚本，输出 PNG；
2. 如果本地有 ChimeraX，生成并运行 ChimeraX 脚本，输出 PNG；
3. 如果没有这些工具，生成可复现的 PyMOL / ChimeraX 脚本和检查说明；
4. 如果可以用 Python 生成基础三维投影图，也可以生成简单截图辅助判断；
5. 如果你无法真正查看或判断图像，不要伪造“人工检查通过”，应标记为 `requires_human_review`；
6. 如果你可以根据生成的图片或可视化输出进行判断，请记录判断依据。

建议新增脚本：

```text
scripts/phase0_generate_visual_check_assets.py
```

功能：

- 读取 `reports/phase0/visual_check_list.csv`；
- 读取 selected sample 的 processed pkl；
- 找到 `protein_path`、`ligand_path`、scaffold atom indices、R-group atom indices、anchor atom indices；
- 生成可视化辅助文件；
- 输出到 `runs/phase0_visual_check/` 或 `reports/phase0/visual_check_assets/`；
- 生成 `tmp/20260506/phase0-visual-check-notes.md` 模板或结果。

注意目录：

- 如果是运行生成的图片和脚本，放 `reports/phase0/visual_check_assets/` 或 `runs/phase0_visual_check/`；
- 大量 PNG 不提交 Git；
- 可提交 `tmp/20260506/phase0-visual-check-notes.md` 作为轻量总结。

人工可视化检查至少要看这些项目：

1. ligand 是否在 pocket 中；
2. pocket 是否围绕 ligand；
3. scaffold 是否合理；
4. R-groups 是否是合理取代基；
5. anchors 是否在 scaffold 和 R-group 的连接处；
6. 是否有肉眼可见的严重重叠；
7. 是否应该纳入 `phase0_balanced_30`。

请生成或填写：

```text
tmp/20260506/phase0-visual-check-notes.md
```

格式建议：

```markdown
# 阶段 0 人工可视化抽查记录

## 总体结论

- 检查样本数:
- pass:
- fail:
- uncertain:
- requires_human_review:
- 是否发现系统性错误:
- 是否建议进入阶段 1 前继续修阶段 0:

## 单样本记录

| complex_id | target_id | ligand_in_pocket | pocket_ok | scaffold_ok | rgroups_ok | anchors_ok | obvious_clash | result | notes |
|---|---|---|---|---|---|---|---|---|---|
```

判断标准：

- pass：ligand 在 pocket 中，pocket 合理，scaffold/R-groups/anchors 没明显错误，无肉眼明显严重重叠；
- fail：ligand 不在 pocket、pocket 明显错、scaffold/R-groups/anchors 系统错误、明显严重重叠；
- uncertain：图像或索引不够清楚；
- requires_human_review：你无法实际查看图像或无法做视觉判断。

重要：如果你无法实际完成视觉判断，不要假装完成。要如实写 `requires_human_review`，并给出用户可手动打开的文件和命令。

---

## 七、补充 target distribution summary

请生成或更新：

```text
tmp/20260506/phase0-target-distribution-summary.md
```

内容包括：

1. 51 个 clean pool 的 target 分布；
2. 前两个 target 占比；
3. balanced subset 的 target 分布；
4. 是否仍然存在单 target 过度集中；
5. 后续阶段应如何使用 balanced subset；
6. 是否建议后续采样使用 target-aware streaming selection。

---

## 八、补充 ligand-only prefilter bias summary

请生成或更新：

```text
tmp/20260506/phase0-prefilter-bias-notes.md
```

内容包括：

1. IF3 archive 流式扫描 paired candidates 数；
2. ligand-only 预筛跳过数；
3. 整理为 raw complex 的数量；
4. 预筛标准；
5. 为什么这个预筛对本项目合理；
6. 它带来的选择偏差；
7. 后续报告和论文中应该如何表述；
8. 是否建议后续统计 `prefilter_reason_counts_by_target`。

建议表述：

> 当前 CrossDocked clean set 经过 ligand-only scaffold/R-group 预筛，因此是面向 R-group 局部碰撞修复任务的 task-specific clean subset，不代表完整 CrossDocked 分布。

---

## 九、检查并按需更新 `docs/` 下的 Markdown 文档

请在阶段 0 收尾完成后，检查 `docs/` 下现有四个 Markdown 文档是否需要做最小必要更新：

1. `docs/20260504-01-Clash2Feedback-GC_完整方案与升级路线.md`
2. `docs/20260504-02-Clash2Feedback-GC_第一篇论文实验方案.md`
3. `docs/20260504-03-Clash2Feedback-GC_总体实验递进路线.md`
4. `docs/20260505-Clash2Feedback-GC_阶段0工程方案.md`

检查重点：

- 是否仍把阶段 0 clean 数量写成只能是 20–30，是否需要改成“20–30 是第一批最低目标，不是上限；当前 clean pool 为 51”；
- 是否需要补充 `phase0_clean_pool_v0_1` 和 `phase0_balanced_30_v0_1` 的区分；
- 是否需要补充 target 分布不均和 target-balanced benchmark 的说明；
- 是否需要补充 ligand-only scaffold/R-group 预筛会引入 task-specific 选择偏差；
- 是否需要补充 `basic_clash_screen` 只是阶段 0 sanity gate，不是正式 vdW clash detector；
- 是否需要补充当前 IF3 archive / pocket10 数据来源与边界；
- 是否需要补充人工可视化抽查作为进入阶段 1 前的阶段 0 收尾要求；
- 是否需要更新目录结构或文件名，确保与当前仓库实际结构一致。

更新原则：

- 只做最小必要修改；
- 不重写整个文档；
- 不引入阶段 1 实现细节；
- 不把运行产物 CSV/JSON 内容大段复制进 docs；
- 详细实验复盘仍放在 `tmp/*.md`；
- `docs/` 只保留稳定的设计口径、边界、目录规范和阶段 0 验收说明；
- 如果判断某个文档不需要修改，请在最终回复里说明原因。

---

## 十、补充最终阶段 0 收尾报告

请生成或更新：

```text
tmp/20260506/phase0-closeout-summary.md
```

必须包含：

1. Codex 实验结果评价；
2. 阶段 0 当前是否完成；
3. 51 个 clean pool 是否保留；
4. 是否生成 `phase0_balanced_30`；
5. target 分布不均是否是问题；
6. ligand-only 预筛是否是问题；
7. `basic_clash_screen` 的边界；
8. `pocket10` 的边界；
9. 人工可视化抽查结果；
10. `docs/` 下 Markdown 是否已检查、哪些文件已更新、哪些未更新；
11. 仍然存在的风险；
12. 后续阶段零外的事项提醒，但不要进入阶段 1 实现细节；
13. 最终是否建议进入阶段 1。

推荐结论格式：

- 如果人工可视化抽查通过：

```text
阶段 0 工程和数据质量收尾均已完成。保留 51 个 clean samples 作为 phase0_clean_pool_v0_1，同时使用 phase0_balanced_30_v0_1 作为阶段 1–3 mini-loop 的轻量 benchmark。阶段 1 可以在 balanced subset 上启动，但 basic_clash_screen 不应替代正式 vdW clash detector。
```

- 如果人工可视化抽查无法完成：

```text
阶段 0 工程已完成，但数据质量签字尚未完成。需要用户或研究者使用生成的 visual check assets 完成 5–10 个样本的人工抽查后，再进入阶段 1。
```

- 如果人工抽查发现系统性错误：

```text
阶段 0 不能进入阶段 1。应先修复 scaffold/R-group/anchor/pocket 处理逻辑并重跑 phase0。
```

---

## 十一、运行测试和检查

完成所有修改后执行：

```bash
python -m compileall src scripts
conda run -n c2f_cpu pytest
```

如果 `c2f_cpu` 不存在，先读取 `README.md` 和 `environment.yml`，使用已有环境或说明缺失，不要随意引入 PyTorch / CUDA。

然后执行或确认：

```bash
conda run -n c2f_cpu python scripts/phase0_check_dataset.py
conda run -n c2f_cpu python scripts/phase0_make_splits.py
```

如果新增了 balanced manifest 脚本，执行：

```bash
conda run -n c2f_cpu python scripts/phase0_make_balanced_manifest.py   --manifest data/processed/v0_1/manifest.parquet   --visual-check reports/phase0/visual_check_list.csv   --output data/splits/v0_1/phase0_balanced_30.txt   --summary tmp/20260506/phase0-balanced30-summary.md   --max-samples 30   --min-samples 20   --max-per-target 5   --seed 20260504
```

如果新增了 visual check assets 脚本，执行：

```bash
conda run -n c2f_cpu python scripts/phase0_generate_visual_check_assets.py   --visual-check reports/phase0/visual_check_list.csv   --manifest data/processed/v0_1/manifest.parquet   --num-samples 10   --output-root reports/phase0/visual_check_assets   --notes tmp/20260506/phase0-visual-check-notes.md
```

---

## 十二、Git 提交规则

提交前必须检查：

```bash
git status
```

不要提交：

- raw PDB/SDF/CIF；
- data/cache 下的大文件；
- processed pkl；
- manifest.parquet；
- reports/phase0/*.csv；
- reports/phase0/*.json；
- 大量 PNG；
- checkpoint；
- runs 下大型产物；
- HF cache；
- tar.gz / zip 数据包。

可以提交：

- 新增脚本；
- 修改后的 README / docs；
- 配置文件；
- 测试文件；
- tmp/*.md 轻量总结；
- 小型模板文件。

如果 `reports/phase0/visual_check_assets` 里生成了脚本或少量模板，可以视情况提交；大量图片不要提交。

建议 commit message：

```text
Complete phase 0 closeout checks and balanced benchmark manifest
```

---

## 十三、最终回复格式

完成后请用中文回复：

1. 本轮改了哪些文件；
2. 新增了哪些脚本；
3. 是否保留 51 个 clean pool；
4. `phase0_balanced_30` 是否生成，数量是多少，target 分布如何；
5. 人工可视化抽查是否完成；
6. 如果完成，pass / fail / uncertain / requires_human_review 数量；
7. 是否发现 scaffold / R-group / anchor / pocket 系统性错误；
8. target 分布不均的处理建议；
9. ligand-only 预筛偏差说明；
10. `basic_clash_screen` 的边界说明；
11. `docs/` 下 Markdown 是否已检查，是否有更新；
12. 阶段 0 是否建议最终关闭；
13. 是否可以进入阶段 1；
14. pytest 结果；
15. git status；
16. commit hash，如果已提交。

再次强调：不要进入阶段 1。本轮只完成阶段 0 收尾实验。
