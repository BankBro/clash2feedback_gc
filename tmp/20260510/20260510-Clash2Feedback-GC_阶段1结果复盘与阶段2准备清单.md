# Clash2Feedback-GC 阶段 1 结果复盘与阶段 2 准备清单

## 1. 阶段 1 结论

阶段 1 可以验收并关闭. 当前实现已经完成正式 protein-ligand vdW clash detector, R-group attribution, failure type 分类, repair verifier skeleton, clean calibration 和 verifier smoke test.

当前阶段 1 结果:

| 项 | 结果 |
|---|---:|
| clean pool 样本数 | 51 |
| balanced subset 样本数 | 28 |
| 默认 `delta` | 0.4 Å |
| sensitivity | 0.3, 0.4, 0.5 Å |
| 默认 receptor scope | `phase0_pocket8`, `pocket10_all_atoms` |
| `delta = 0.4` clean pool severe false positive | 0 |
| `delta = 0.4` balanced subset severe false positive | 0 |
| verifier clean-vs-clean smoke | 28 / 28 pass |

这些结果说明阶段 1 裁判系统能在阶段 0 clean 数据上稳定运行, 且默认阈值下没有 severe false positive. 这支持进入阶段 2 controlled synthetic failed pose benchmark.

## 2. 结果边界

阶段 1 结果不能被解读为:

- 已验证真实 failed pose 的碰撞召回率.
- 已验证规则 locator 的 R-group Top-1 / Top-3.
- 已验证生成器修复能力.
- 已验证真实 repair candidate 的可靠性.
- 已完成 full-receptor checked repair.

阶段 1 的 `geometry_valid` 当前是 coordinate-level smoke check, 主要检查坐标 shape 和 finite. RDKit sanitize, 键长, 价态, ligand internal clash 和 fragment connectivity 是阶段 2/4 的升级项.

## 3. 阈值解释

阶段 1 使用:

\[
c_{ij}=\max(0,r_i^{vdW}+r_j^{vdW}-\delta-d_{ij})
\]

也就是先定义 raw vdW overlap:

\[
o_{ij}=r_i^{vdW}+r_j^{vdW}-d_{ij}
\]

再计算:

\[
c_{ij}=\max(0,o_{ij}-\delta)
\]

默认 `delta = 0.4 Å`, `severe_depth_threshold = 0.4 Å`. 因此:

```text
clash pair: raw vdW overlap > 0.4 Å
severe clash: raw vdW overlap >= 0.8 Å
```

`delta = 0.4` 当前适合作为阶段 2/3 主阈值: 它比 `0.5` 更严格, 又不像 `0.3` 那样在 clean calibration 中触发 severe false positive.

## 4. 阶段 1 已补强内容

进入阶段 2 前, 阶段 1 增加了以下补强:

- verifier 输出 old/new clash pair tracking, 区分旧碰撞残留和新碰撞产生.
- attribution 输出 all-region dominant ratio 与 valid-R-group dominant ratio, 避免阶段 3 指标混淆.
- detector 输出 `analysis_status`, unsupported atom / covalent / metal / mask 不再静默变成普通 `no_clash`.
- reports 增加 per-scope summary, strict delta false-positive case report, non-severe contact stats 和 scope comparison.
- docs 明确 zero severe false positive 不等于 zero close contact, 也不等于统计意义上的 false-positive rate 为 0.

## 5. 阶段 2 准备清单

阶段 2 应构建 controlled synthetic failed pose benchmark. 每个 failed pose 建议记录:

- `target_rgroup`
- `injection_type`
- original clean ligand coords
- failed ligand coords
- failed clash report
- old clash pairs
- expected failure type
- dominant ratio all regions
- dominant ratio valid R-groups
- scaffold RMSD
- non-target R-group RMSD
- ligand internal clash check
- reject / unsupported reason

阶段 2 主集只纳入:

- original clean pose 在 `delta = 0.4` 下无 severe clash.
- target R-group 在 failed pose 中产生 severe clash.
- target R-group 主导, 且 `dominant_ratio_valid_rgroups` 足够高.
- scaffold 和非目标区域保持稳定.
- ligand internal severe clash 被过滤.
- unsupported chemistry / unsupported mask 被过滤或单独进入 reject split.

## 6. 阶段 2 构造优先级

建议优先级:

| 优先级 | split | 说明 |
|---|---|---|
| 1 | `directed_clash` | 朝 protein hotspot 定向扰动, 最容易构造明确 positive case |
| 2 | `torsion_perturb` | 扰动目标 R-group 可旋转键, 更接近局部构象错误 |
| 3 | `easy_rotation` | anchor bond rotation baseline, 需要严格过滤漂移和 multi-region case |
| 4 | `fragment_replace` | 更接近“取代基太大”, 但化学变量更多, 放在增强阶段 |
| 5 | `hard_multi_region` | reject / stress test, 不进入 single-R-group 主指标 |

## 7. 阶段 3 指标准备

阶段 3 规则 locator 的主指标只在 supported single-R-group synthetic failures 上计算:

- Coverage.
- Top-1, reject 算 miss.
- Top-1 covered.
- Top-3 rank.
- Top-3 operational.
- dominant ratio valid 平均值.

Reject / unsupported / scaffold / multi-region / global pose failure 必须单独报告:

- Reject recall.
- Unsupported recall.
- False local repair.

不要把 unsupported 或 reject case 混入 Top-1 / Top-3 主指标, 也不要在阶段 2 构造时只用 predicted `dominant_region` 作为唯一保留条件, 否则会污染阶段 3 评价.

## 8. 给网页版 ChatGPT 的阅读索引

网页版 ChatGPT 只能看到 GitHub 仓库时, 建议优先阅读以下文件:

- `README.md`: 项目总体结构和阶段 1 脚本入口.
- `docs/20260508-Clash2Feedback-GC_阶段1碰撞检测器与可靠验证器方案.md`: 阶段 1 的正式设计边界, 阈值定义, 输出表和验收口径.
- `tmp/20260510/20260510-Clash2Feedback-GC_阶段1结果复盘与阶段2准备清单.md`: 本次实验结果复盘和阶段 2 准备建议.
- `tmp/20260510/20260510-Clash2Feedback-GC_阶段1修补清单与文档更新建议.md`: 本轮修补来源和优先级说明.
- `configs/phase1_clash_detector.yaml`: 阶段 1 默认参数, receptor scope 和 sensitivity 配置.
- `scripts/phase1_check_clashes.py`: 报告生成入口.
- `src/clash2feedback/geometry/clash.py`: protein-ligand vdW clash detector.
- `src/clash2feedback/geometry/rgroup_attribution.py`: R-group attribution 和 failure type 分类.
- `src/clash2feedback/verifier/repair_verifier.py`: repair verifier skeleton 和 old/new clash pair tracking.
- `tests/test_clash_detector.py`, `tests/test_rgroup_attribution.py`, `tests/test_repair_verifier.py`, `tests/test_phase1_report_extensions.py`: 阶段 1 行为和报告扩展测试.

## 9. 本次建议提交的数据文件

本次只建议提交小型结果表和 summary, 不提交 raw PDB/SDF, processed pkl, 大型 cache, checkpoint, runs 图片或完整 processed 数据.

建议提交的阶段 1 结果文件:

- `reports/phase1_clash_detector/summary.json`: 阶段 1 核心结论.
- `reports/phase1_clash_detector/clean_clash_report.csv`: clean pool 默认阈值检测结果.
- `reports/phase1_clash_detector/balanced_clash_report.csv`: balanced subset 默认阈值检测结果.
- `reports/phase1_clash_detector/threshold_sensitivity.csv`: `delta = 0.3, 0.4, 0.5` 敏感性统计.
- `reports/phase1_clash_detector/rgroup_attribution_report.csv`: R-group attribution 明细.
- `reports/phase1_clash_detector/failure_type_counts.csv`: failure type 汇总.
- `reports/phase1_clash_detector/verifier_smoke_report.csv`: clean-vs-clean verifier smoke 结果.
- `reports/phase1_clash_detector/unsupported_cases.csv`: unsupported case 表, 当前只有表头.
- `reports/phase1_clash_detector/vdw_radius_table.json`: vdW 半径表.
- `reports/phase1_clash_detector/strict_delta_false_positive_cases.csv`: 严格阈值下的 case-level 诊断.
- `reports/phase1_clash_detector/nonsevere_contact_stats.csv`: non-severe close contact 统计.
- `reports/phase1_clash_detector/scope_comparison.csv`: `phase0_pocket8` 与 `pocket10_all_atoms` 对比.

这些文件足够支持网页端分析阶段 1 是否可关闭, `delta = 0.4 Å` 是否合理, 以及阶段 2 benchmark 应如何设计.
