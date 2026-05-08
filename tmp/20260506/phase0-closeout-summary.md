# 阶段 0 收尾复盘

## 1. Codex 实验结果评价

本轮只做阶段 0 收尾, 未进入阶段 1, 未实现正式 `vdW clash detector`, 未实现 `repair verifier`, 未做人为 clash 注入, 未接 DiffSBDD / TargetDiff / Pocket2Mol / PocketXMol 等生成器.

阶段 0 工程底座已经完成: DiffSBDD official example smoke 可复现, IF3 / CrossDocked pocket10 数据已自动获取并整理, strict filter 后保留 51 个 phase0 usable clean samples.

## 2. 当前是否完成

阶段 0 工程验收通过. 51 个 clean samples 保留为:

```text
phase0_clean_pool_v0_1
```

该 clean pool 不删除. 但由于 target 分布不均, 后续阶段 1-3 mini-loop 不建议直接使用全部 51 个作为唯一 benchmark.

## 3. balanced subset

已生成:

```text
phase0_balanced_30_v0_1
```

输出清单为:

```text
data/splits/v0_1/phase0_balanced_30.txt
```

该文件是运行产物, 默认不提交 Git. 关键统计写入 `tmp/20260506/phase0-balanced30-summary.md`.

- requested_max_samples = 30.
- actual_samples = 28.
- max_per_target = 5.
- 未满 30 的原因是当前只有 8 个 target, 且严格执行 target cap 后无法满 30.
- 选择 28 是为了优先保证 target diversity, 而不是最大化样本数.

## 4. target 分布风险

51 个 clean pool 中 SMYD2 和 CDGT2 占比较高, 前两个 target 合计 33 / 51, 约 64.7%. 这不是阶段 0 工程错误, 但会影响后续小规模实验的代表性.

处理方式:

- 保留 51 个 clean pool.
- 阶段 1-3 mini-loop 优先使用 `phase0_balanced_30_v0_1`.
- 后续重新采样时使用 target-aware streaming selection.

## 5. ligand-only 预筛风险

当前 IF3 archive 使用 ligand-only scaffold/R-group 预筛后再整理 raw complex. 该策略对 R-group 局部修复任务合理, 但会引入 task-specific 选择偏差.

后续报告中应明确: 当前 CrossDocked clean set 是 `task-specific clean subset`, 不是 `unbiased CrossDocked subset`.

## 6. basic_clash_screen 边界

`basic_clash_screen` 只表示阶段 0 的 obvious severe clash sanity gate 通过. 它不使用元素相关范德华半径, 不计算正式 clash depth, 不输出 R-group clash score, 不能替代阶段 1 的正式 clash detector.

## 7. pocket10 边界

当前 IF3 archive 使用 `*_pocket10.pdb`, 即 ligand 周围约 10 Å 的 pocket-level protein structure. 它不是完整 receptor. 阶段 0 又从该局部结构中提取 8 Å pocket. 对阶段 0 和局部 clash 修复任务通常足够; 若后续生成器或外部验证需要 full receptor, 需要另行处理.

## 8. 人工可视化抽查

已生成 15 个样本的可视化辅助资产, 并将已有 visual check 样本目录整理为可下载的便携包. 每个样本目录包含:

```text
protein.pdb
ligand.sdf
view.cxc
view_overview.cxc
view_clash.cxc
view_rgroup.cxc
view_ligand.cxc
view.pml
projection.png
scaffold_atoms.pdb
valid_rgroup_atoms.pdb
valid_anchors.bild
protein_pocket_vdw_atoms.pdb
ligand_vdw_atoms.pdb
close_contacts.bild
```

`view.cxc` 和 `view.pml` 均使用相对路径. 推荐用户下载单个 `complex_xxx/` 目录到本地后, 在该目录依次运行 `chimerax view_overview.cxc`, `chimerax view_clash.cxc`, `chimerax view_rgroup.cxc`, `chimerax view_ligand.cxc`.

- `view_overview.cxc`: protein cartoon + semi-transparent surface + ligand sticks, 用于看 ligand 是否位于 pocket.
- `view_clash.cxc`: protein/ligand sticks + 半透明 vdW sphere + close-contact 红色标记, 用于肉眼检查明显严重重叠.
- `view_rgroup.cxc`: 透明 protein 背景 + ligand sticks + scaffold/R-group/anchor 标记层.
- `view_ligand.cxc`: 隐藏 protein, 只看 ligand 的 scaffold/R-group/anchor 拆分.

```text
runs/phase0_visual_check/
```

已写入:

```text
tmp/20260506/phase0-visual-check-notes.md
```

2026-05-07 用户已查看 `runs/phase0_visual_check` 下可视化结果, 反馈为没有明显问题. 当前 visual check 状态为 `accepted_no_obvious_issue`; `tmp/20260507/phase0-visual-check-notes.md` 已将 15 个样本逐项记录为 pass. 计数为 pass=15, fail=0, uncertain=0, requires_human_review=0.

因此, 阶段 0 工程和人工初筛均已满足进入阶段 1 的要求. 仍需在后续报告中说明这些图片只用于人工初筛, 不替代阶段 1 正式 clash detector.

## 9. docs 检查

已检查 docs 下四份方案文档. 本轮最小更新方向:

- 阶段 0 工程方案补充 protein / target / pocket 术语口径.
- 阶段 0 工程方案补充 `phase0_clean_pool_v0_1` 和 `phase0_balanced_30_v0_1` 的区分.
- 总体递进路线和论文实验方案补充 clean pool 与 balanced subset 的使用边界.
- 完整方案与升级路线补充 task-specific clean subset 和 basic clash screen 边界.

详细实验复盘保留在 `tmp/YYYYMMDD/*.md`, 不把运行 CSV/JSON 大段复制进 docs.

## 10. 最终建议

阶段 0 工程和数据处理闭环可以关闭. 下一步进入阶段 1, 正式实现 clash detector 和 reliable repair verifier, 并在文档中保留 task-specific clean subset, pocket10 和 basic clash screen 的边界声明.
