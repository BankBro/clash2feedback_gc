# Rule Backend Diagnostic

## 1. Role

`rule_fixed_topology` 是固定拓扑局部构象搜索. 它保留原分子拓扑和 atom order, 通过 anchor axis rotation 和内部 torsion proposal 在参考掩码区域内搜索可逆构象.

它的阶段 4.0 定位是构象型强基线和可逆性 sanity check, 不是生成式局部修复主方法.

## 2. Why 38/40 Is Plausible

- 阶段 2 人工失败样本由 `easy_rotation`, `torsion_perturb`, `directed_clash` 等受控局部扰动构造.
- 规则型后端的搜索空间与上述构造方式高度相关, 因而能把大量局部碰撞恢复到无旧严重碰撞且无新严重碰撞的构象.
- same-topology 候选天然更容易满足 fixed structure match, keep region stable 和 anchor integrity.

## 3. Why It Is Not A Generative Main Method

- 它不生成新片段, 不改变取代基组成, 也不学习生成式修复策略.
- 它与阶段 2 的人工扰动方式同源, 因此高成功率不能外推为生成式局部补全已经完成.
- 后续生成式主线仍应围绕 DiffSBDD conditional adapter, DiffDec adapter 或新的局部生成基座模型继续修补.

## 4. Proposal Cost

- selected case denominator: 40.
- proposal_count_sum: 1200.
- candidate_count_sum: 320.
- reliable_candidate_success_count: 227.
- sample_reliable_success_count: 38.
- 每个 case 最多保留 K=8 个候选, 但内部 proposal search 成本不能被 K=8 掩盖. 本次内部 proposal_count_sum = 1200, 最终候选数 = 320.

## 5. Stratified Sample Success

### 5.1 By Injection Mode

| group | selected_cases | reliable_cases | sample_success_rate |
| --- | --- | --- | --- |
| directed_clash | 14 | 14 | 1.000000 |
| easy_rotation | 13 | 11 | 0.846154 |
| torsion_perturb | 13 | 13 | 1.000000 |

### 5.2 By Difficulty Bin

| group | selected_cases | reliable_cases | sample_success_rate |
| --- | --- | --- | --- |
| easy | 27 | 26 | 0.962963 |
| medium | 13 | 12 | 0.923077 |

## 6. Report Wording

最终报告应写成: `rule_fixed_topology` 证明当前受控人工局部碰撞样本存在大量构象可逆失败, 适合作为 sanity check 和强基线. 不应写成生成式局部修复主线已经完成, 也不建议直接把它作为阶段 4.1 生成式主方法.
