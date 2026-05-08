# 阶段 0 人工可视化抽查记录

## 总体结论

- 检查样本数: 15.
- user_visual_scan_status: accepted_no_obvious_issue.
- pass: 15.
- fail: 0.
- uncertain: 0.
- requires_human_review: 0.
- 是否发现系统性错误: 用户已查看 `runs/phase0_visual_check` 下可视化结果, 反馈为没有明显问题; 15 个样本逐项记录为 pass; 未发现需要返回阶段 0 修复的系统性错误.
- 是否建议进入阶段 1 前继续修阶段 0: 不需要. 阶段 0 可关闭.

## 单样本记录

| complex_id | target_id | ligand_in_pocket | pocket_ok | scaffold_ok | rgroups_ok | anchors_ok | obvious_clash | result | notes |
|---|---|---|---|---|---|---|---|---|---|
| complex_crossdocked_000001 | CDGT2_BACCI_28_713_0 | pass | pass | pass | pass | pass | no | pass | user visual scan pass; assets: `runs/phase0_visual_check/complex_crossdocked_000001`; copy_status=protein_copied,ligand_copied; marker_status=scaffold_atoms=13,valid_rgroup_atoms=4,valid_anchor_connections=2,protein_vdw_atoms=119,ligand_vdw_atoms=23,visual_close_contacts=0; projection_status=projection_png_generated |
| complex_crossdocked_000002 | CDGT2_BACCI_28_713_0 | pass | pass | pass | pass | pass | no | pass | user visual scan pass; assets: `runs/phase0_visual_check/complex_crossdocked_000002`; copy_status=protein_copied,ligand_copied; marker_status=scaffold_atoms=13,valid_rgroup_atoms=4,valid_anchor_connections=2,protein_vdw_atoms=157,ligand_vdw_atoms=23,visual_close_contacts=0; projection_status=projection_png_generated |
| complex_crossdocked_000003 | CDGT2_BACCI_28_713_0 | pass | pass | pass | pass | pass | no | pass | user visual scan pass; assets: `runs/phase0_visual_check/complex_crossdocked_000003`; copy_status=protein_copied,ligand_copied; marker_status=scaffold_atoms=13,valid_rgroup_atoms=4,valid_anchor_connections=2,protein_vdw_atoms=165,ligand_vdw_atoms=23,visual_close_contacts=0; projection_status=projection_png_generated |
| complex_crossdocked_000004 | CDGT2_BACCI_28_713_0 | pass | pass | pass | pass | pass | no | pass | user visual scan pass; assets: `runs/phase0_visual_check/complex_crossdocked_000004`; copy_status=protein_copied,ligand_copied; marker_status=scaffold_atoms=13,valid_rgroup_atoms=4,valid_anchor_connections=2,protein_vdw_atoms=179,ligand_vdw_atoms=23,visual_close_contacts=0; projection_status=projection_png_generated |
| complex_crossdocked_000005 | CDGT2_BACCI_28_713_0 | pass | pass | pass | pass | pass | no | pass | user visual scan pass; assets: `runs/phase0_visual_check/complex_crossdocked_000005`; copy_status=protein_copied,ligand_copied; marker_status=scaffold_atoms=13,valid_rgroup_atoms=4,valid_anchor_connections=2,protein_vdw_atoms=151,ligand_vdw_atoms=23,visual_close_contacts=0; projection_status=projection_png_generated |
| complex_crossdocked_000006 | CDGT2_BACCI_28_713_0 | pass | pass | pass | pass | pass | no | pass | user visual scan pass; assets: `runs/phase0_visual_check/complex_crossdocked_000006`; copy_status=protein_copied,ligand_copied; marker_status=scaffold_atoms=13,valid_rgroup_atoms=4,valid_anchor_connections=2,protein_vdw_atoms=162,ligand_vdw_atoms=23,visual_close_contacts=0; projection_status=projection_png_generated |
| complex_crossdocked_000029 | ODP1_ECOLI_2_887_0 | pass | pass | pass | pass | pass | no | pass | user visual scan pass; assets: `runs/phase0_visual_check/complex_crossdocked_000029`; copy_status=protein_copied,ligand_copied; marker_status=scaffold_atoms=12,valid_rgroup_atoms=19,valid_anchor_connections=2,protein_vdw_atoms=481,ligand_vdw_atoms=34,visual_close_contacts=0; projection_status=projection_png_generated |
| complex_crossdocked_000026 | RIP1_MOMCH_24_270_0 | pass | pass | pass | pass | pass | no | pass | user visual scan pass; assets: `runs/phase0_visual_check/complex_crossdocked_000026`; copy_status=protein_copied,ligand_copied; marker_status=scaffold_atoms=13,valid_rgroup_atoms=4,valid_anchor_connections=2,protein_vdw_atoms=291,ligand_vdw_atoms=23,visual_close_contacts=0; projection_status=projection_png_generated |
| complex_diffsbdd_5ndu | complex_diffsbdd_5ndu | pass | pass | pass | pass | pass | no | pass | user visual scan pass; assets: `runs/phase0_visual_check/complex_diffsbdd_5ndu`; copy_status=protein_copied,ligand_copied; marker_status=scaffold_atoms=40,valid_rgroup_atoms=8,valid_anchor_connections=2,protein_vdw_atoms=274,ligand_vdw_atoms=49,visual_close_contacts=0; projection_status=projection_png_generated |
| complex_crossdocked_000048 | HEPB_PEDHD_25_772_0 | pass | pass | pass | pass | pass | no | pass | user visual scan pass; assets: `runs/phase0_visual_check/complex_crossdocked_000048`; copy_status=protein_copied,ligand_copied; marker_status=scaffold_atoms=13,valid_rgroup_atoms=9,valid_anchor_connections=3,protein_vdw_atoms=306,ligand_vdw_atoms=26,visual_close_contacts=0; projection_status=projection_png_generated |
| complex_crossdocked_000017 | RARA_HUMAN_173_420_0 | pass | pass | pass | pass | pass | no | pass | user visual scan pass; assets: `runs/phase0_visual_check/complex_crossdocked_000017`; copy_status=protein_copied,ligand_copied; marker_status=scaffold_atoms=23,valid_rgroup_atoms=11,valid_anchor_connections=3,protein_vdw_atoms=491,ligand_vdw_atoms=34,visual_close_contacts=0; projection_status=projection_png_generated |
| complex_crossdocked_000031 | SMYD2_HUMAN_2_433_0 | pass | pass | pass | pass | pass | no | pass | user visual scan pass; assets: `runs/phase0_visual_check/complex_crossdocked_000031`; copy_status=protein_copied,ligand_copied; marker_status=scaffold_atoms=20,valid_rgroup_atoms=13,valid_anchor_connections=3,protein_vdw_atoms=381,ligand_vdw_atoms=34,visual_close_contacts=0; projection_status=projection_png_generated |
| complex_crossdocked_000021 | IPPK_MOUSE_1_468_0 | pass | pass | pass | pass | pass | no | pass | user visual scan pass; assets: `runs/phase0_visual_check/complex_crossdocked_000021`; copy_status=protein_copied,ligand_copied; marker_status=scaffold_atoms=6,valid_rgroup_atoms=30,valid_anchor_connections=6,protein_vdw_atoms=349,ligand_vdw_atoms=36,visual_close_contacts=0; projection_status=projection_png_generated |
| complex_crossdocked_000007 | CDGT2_BACCI_28_713_0 | pass | pass | pass | pass | pass | no | pass | user visual scan pass; assets: `runs/phase0_visual_check/complex_crossdocked_000007`; copy_status=protein_copied,ligand_copied; marker_status=scaffold_atoms=13,valid_rgroup_atoms=4,valid_anchor_connections=2,protein_vdw_atoms=155,ligand_vdw_atoms=23,visual_close_contacts=0; projection_status=projection_png_generated |
| complex_crossdocked_000030 | ODP1_ECOLI_2_887_0 | pass | pass | pass | pass | pass | no | pass | user visual scan pass; assets: `runs/phase0_visual_check/complex_crossdocked_000030`; copy_status=protein_copied,ligand_copied; marker_status=scaffold_atoms=12,valid_rgroup_atoms=19,valid_anchor_connections=2,protein_vdw_atoms=482,ligand_vdw_atoms=34,visual_close_contacts=0; projection_status=projection_png_generated |

## 复现命令

如本机安装 PyMOL, 可在每个样本目录运行:

```bash
pymol -cq view.pml
```

如本机安装 ChimeraX, 可在每个样本目录运行:

```bash
chimerax view.cxc
```

`view.cxc` 和 `view.pml` 使用相对路径. 下载某个样本目录到本地后, 只要 `protein.pdb`, `ligand.sdf` 和脚本在同一目录, 即可直接打开.

推荐在 ChimeraX 中按顺序打开 `view_overview.cxc`, `view_clash.cxc`, `view_rgroup.cxc`, `view_ligand.cxc`.
`view_clash.cxc` 会叠加灰色 protein vdW sphere, royalblue ligand vdW sphere, 黑色 silhouette 轮廓和 close-contact 红色标记, 便于判断是否存在肉眼明显严重重叠; `view_rgroup.cxc` 和 `view_ligand.cxc` 会叠加 scaffold, valid R-group 和 valid anchor 标记层.

2026-05-07 用户已查看这些可视化结果, 反馈为没有明显问题; 上表已按人工初筛结果逐样本记录为 pass.
