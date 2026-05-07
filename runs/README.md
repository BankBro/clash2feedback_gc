# runs

## 1. 目录说明

本目录存放较重运行产物, 例如日志, checkpoint, 生成候选和可视化辅助资产. 这些文件默认不提交 Git.

## 2. 阶段 0 产物

- `phase0_visual_check/`: 阶段 0 人工可视化抽查辅助资产, 默认抽样 15 个样本, 包括 `protein.pdb`, `ligand.sdf`, projection PNG, PyMOL 脚本, ChimeraX 多视图脚本, 批量渲染图片和 scaffold/R-group/anchor 标记层.

每个样本目录都是可下载的便携检查包. 将单个 `complex_xxx/` 目录下载到本地后, 在该目录运行:

```bash
chimerax view_overview.cxc
chimerax view_clash.cxc
chimerax view_rgroup.cxc
chimerax view_ligand.cxc
```

其中 `view_overview.cxc` 用于看 ligand 是否在 pocket 中, `view_clash.cxc` 用较淡的 protein sticks, 清晰的橙色 ligand sticks, royalblue ligand vdW sphere, 灰色 protein vdW sphere, 黑色 silhouette 轮廓和红色 close-contact 标记检查肉眼明显严重重叠, `view_rgroup.cxc` 用蛋白透明背景检查 scaffold, valid R-group 和 valid anchor, `view_ligand.cxc` 隐藏蛋白只看 ligand 拆分.

服务器已安装 ChimeraX 时, 可先批量生成初筛 PNG:

```bash
python scripts/phase0_render_visual_check_images.py --assets-root runs/phase0_visual_check
```

默认每个样本生成 `overview`, `clash`, `rgroup`, `ligand` 四类视图, 每类包含 `clear_01` 到 `clear_12` 十二个少遮挡视角, 并生成对应的 `overview_contact_sheet.png`, `clash_contact_sheet.png`, `rgroup_contact_sheet.png`, `ligand_contact_sheet.png`. contact sheet 使用 `3 x 4` 排布, 单图默认保持 `1800 x 1400`, 拼图不降采样, 便于先扫整体再放大看细节. 每个 clear 视角都会先聚焦 ligand, 再按视图用途单独评分: `overview` 优先避免 protein surface 挡住 ligand, `clash` 优先展示 protein-ligand 近距离接触界面, `rgroup` 优先展示 scaffold/R-group/anchor 连接, `ligand` 优先展开 ligand 投影. `rgroup` 和 `ligand` 视图会缩小 scaffold/R-group marker, 避免 marker 球遮住 ligand 拆分关系. 非 ligand-only 图片会在渲染后识别 ligand 彩色区域和 protein 灰色区域, 自动旋转 PNG, 尽量让 protein pocket 落在 ligand 下方. 图片写入各样本目录的 `images/`, 无界面脚本写入 `headless_scripts/`, 汇总索引写入 `phase0_visual_check/render_manifest.csv`. clear-view 模式默认每张图单独启动一次 ChimeraX, 速度较慢但更稳定.

轻量结论写入 `tmp/YYYYMMDD/*.md`; 运行生成的大图, raw 结构副本和脚本留在本目录本地使用, 默认不提交 Git.
