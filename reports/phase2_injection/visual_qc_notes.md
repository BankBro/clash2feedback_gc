# Phase 2 Visual QC Notes

- status: sampled_visual_qc_passed_with_minor_caveats
- 自动结构 gates 已完成; 32 个抽样 case 的 ChimeraX contact sheets 已完成用户人工粗看和 4 个只读子 agent 独立复核, 未发现阻断问题.
- 当前清单包含 32 个 case; 已补充 7 个 `supported_single_rgroup + torsion_perturb` case, 覆盖 target R-group `R1` 到 `R7`.
- 路径基准: `data/benchmarks/clashrepairbench_rg_artificial/v0_1/`.
- 可复核工具: PyMOL, ChimeraX 或 RDKit/Mol* 可视化原始 ligand SDF, failed ligand SDF 和 sample pkl.
- 判读项: target R-group 是否移动, scaffold 是否稳定, non-target R-groups 是否稳定, clash 是否位于 target 区域, invalid/global/near_miss 分类是否合理.

## 1. Conclusion

- sampled_visual_qc_status: `sampled_visual_qc_passed_with_minor_caveats`.
- reviewed cases: 32.
- reviewed contact sheets: 128.
- supported_single_rgroup: pass; 17 cases cover `easy_rotation`, `directed_clash` and `torsion_perturb`.
- invalid_conformer: pass with caveat; no ligand-protein severe pair, but current views do not explicitly highlight ligand internal self-clash.
- global_pose_failure: pass; deep ligand-protein clashes are visually consistent with hard/global failure labels.
- ambiguous_region: pass with caveat; `case_000717` and `case_000718` have less informative `overlay_surface`, but other views support ambiguous-region labels.
- near_miss_contact: pass with caveat; no severe VDW pair is available by definition, so `clash_pair_vdw` is background-only.
- duplicate caveat: invalid visual QC includes two duplicate visual pairs, `case_000019`/`case_000029` and `case_000057`/`case_000070`; these are rejected invalid samples and do not affect supported main-set quality.

## 2. Cases

- case_000041: supported_single_rgroup, sampled_visual_qc_passed_with_minor_caveats
- case_000048: supported_single_rgroup, sampled_visual_qc_passed_with_minor_caveats
- case_000059: supported_single_rgroup, sampled_visual_qc_passed_with_minor_caveats
- case_000095: supported_single_rgroup, sampled_visual_qc_passed_with_minor_caveats
- case_000102: supported_single_rgroup, sampled_visual_qc_passed_with_minor_caveats
- case_000109: supported_single_rgroup, sampled_visual_qc_passed_with_minor_caveats
- case_000120: supported_single_rgroup, sampled_visual_qc_passed_with_minor_caveats
- case_000163: supported_single_rgroup, sampled_visual_qc_passed_with_minor_caveats
- case_000202: supported_single_rgroup, sampled_visual_qc_passed_with_minor_caveats
- case_000210: supported_single_rgroup, sampled_visual_qc_passed_with_minor_caveats
- case_000921: global_pose_failure, sampled_visual_qc_passed_with_minor_caveats
- case_000957: global_pose_failure, sampled_visual_qc_passed_with_minor_caveats
- case_001029: global_pose_failure, sampled_visual_qc_passed_with_minor_caveats
- case_000717: ambiguous_region, sampled_visual_qc_passed_with_minor_caveats
- case_000718: ambiguous_region, sampled_visual_qc_passed_with_minor_caveats
- case_000019: invalid_conformer, sampled_visual_qc_passed_with_minor_caveats
- case_000029: invalid_conformer, sampled_visual_qc_passed_with_minor_caveats
- case_000057: invalid_conformer, sampled_visual_qc_passed_with_minor_caveats
- case_000070: invalid_conformer, sampled_visual_qc_passed_with_minor_caveats
- case_000093: invalid_conformer, sampled_visual_qc_passed_with_minor_caveats
- case_000001: near_miss_contact, sampled_visual_qc_passed_with_minor_caveats
- case_000002: near_miss_contact, sampled_visual_qc_passed_with_minor_caveats
- case_000003: near_miss_contact, sampled_visual_qc_passed_with_minor_caveats
- case_000004: near_miss_contact, sampled_visual_qc_passed_with_minor_caveats
- case_000005: near_miss_contact, sampled_visual_qc_passed_with_minor_caveats
- case_000996: supported_single_rgroup, torsion_perturb, sampled_visual_qc_passed_with_minor_caveats
- case_000818: supported_single_rgroup, torsion_perturb, sampled_visual_qc_passed_with_minor_caveats
- case_000834: supported_single_rgroup, torsion_perturb, sampled_visual_qc_passed_with_minor_caveats
- case_000852: supported_single_rgroup, torsion_perturb, sampled_visual_qc_passed_with_minor_caveats
- case_001266: supported_single_rgroup, torsion_perturb, sampled_visual_qc_passed_with_minor_caveats
- case_000980: supported_single_rgroup, torsion_perturb, sampled_visual_qc_passed_with_minor_caveats
- case_002562: supported_single_rgroup, torsion_perturb, sampled_visual_qc_passed_with_minor_caveats
