# 阶段 0 人工可视化抽查记录

## 总体结论

- 检查样本数: 10.
- pass: 0.
- fail: 0.
- uncertain: 0.
- requires_human_review: 10.
- 是否发现系统性错误: 未发现可由自动脚本确认的系统性错误; 仍需人工查看图片或分子可视化软件确认.
- 是否建议进入阶段 1 前继续修阶段 0: 若人工抽查未完成, 不建议把数据质量签字视为完成.

## 单样本记录

| complex_id | target_id | ligand_in_pocket | pocket_ok | scaffold_ok | rgroups_ok | anchors_ok | obvious_clash | result | notes |
|---|---|---|---|---|---|---|---|---|---|
| complex_crossdocked_000001 | CDGT2_BACCI_28_713_0 | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires human review; assets: `runs/phase0_visual_check/complex_crossdocked_000001`; copy_status=protein_copied,ligand_copied; projection_status=projection_png_generated |
| complex_crossdocked_000002 | CDGT2_BACCI_28_713_0 | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires human review; assets: `runs/phase0_visual_check/complex_crossdocked_000002`; copy_status=protein_copied,ligand_copied; projection_status=projection_png_generated |
| complex_crossdocked_000003 | CDGT2_BACCI_28_713_0 | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires human review; assets: `runs/phase0_visual_check/complex_crossdocked_000003`; copy_status=protein_copied,ligand_copied; projection_status=projection_png_generated |
| complex_crossdocked_000004 | CDGT2_BACCI_28_713_0 | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires human review; assets: `runs/phase0_visual_check/complex_crossdocked_000004`; copy_status=protein_copied,ligand_copied; projection_status=projection_png_generated |
| complex_crossdocked_000005 | CDGT2_BACCI_28_713_0 | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires human review; assets: `runs/phase0_visual_check/complex_crossdocked_000005`; copy_status=protein_copied,ligand_copied; projection_status=projection_png_generated |
| complex_crossdocked_000006 | CDGT2_BACCI_28_713_0 | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires human review; assets: `runs/phase0_visual_check/complex_crossdocked_000006`; copy_status=protein_copied,ligand_copied; projection_status=projection_png_generated |
| complex_crossdocked_000029 | ODP1_ECOLI_2_887_0 | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires human review; assets: `runs/phase0_visual_check/complex_crossdocked_000029`; copy_status=protein_copied,ligand_copied; projection_status=projection_png_generated |
| complex_crossdocked_000026 | RIP1_MOMCH_24_270_0 | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires human review; assets: `runs/phase0_visual_check/complex_crossdocked_000026`; copy_status=protein_copied,ligand_copied; projection_status=projection_png_generated |
| complex_diffsbdd_5ndu | complex_diffsbdd_5ndu | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires human review; assets: `runs/phase0_visual_check/complex_diffsbdd_5ndu`; copy_status=protein_copied,ligand_copied; projection_status=projection_png_generated |
| complex_crossdocked_000048 | HEPB_PEDHD_25_772_0 | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires_human_review | requires human review; assets: `runs/phase0_visual_check/complex_crossdocked_000048`; copy_status=protein_copied,ligand_copied; projection_status=projection_png_generated |

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

当前记录没有把自动生成图片解释为人工 pass; 需要研究者实际查看后再把状态改为 pass / fail / uncertain.
