# 阶段 0 ChimeraX 批量出图初筛记录

## 1. 状态

- assets_root: `runs/phase0_visual_check`.
- render tasks: 48.
- status counts: {'rendered': 48}.
- contact sheets: {'written': 4}.
- 这些 PNG 只用于人工初筛, 不替代阶段 1 正式 clash detector.
- `clear_*` 图片来自按当前样本坐标和当前视图用途自动选择的 ligand-centered 少遮挡视角.
- 每个 `sample_id + view` 默认生成 `3 x 4` contact sheet, 单图保持渲染分辨率用于放大检查.

## 2. 初筛方法

- 先扫 `overview_contact_sheet.png`: ligand 是否在 pocket 内.
- 再扫 `clash_contact_sheet.png`: 是否有肉眼明显严重重叠或红色 close-contact 标记.
- 再扫 `rgroup_contact_sheet.png` 和 `ligand_contact_sheet.png`: scaffold, valid R-group, anchor 标记是否合理.
- contact sheet 用于快速筛查; 可疑视角再打开对应 `clear_*.png` 单图或本地 ChimeraX 旋转精查.
- `rgroup_*` 和 `ligand_*` 会缩小 scaffold/R-group marker, 避免 marker 本身遮住 ligand 拆分关系.
- 默认角度会先以 ligand 为中心; `overview` 偏向口袋入口无遮挡, `clash` 偏向接触界面可见, `rgroup` 偏向 anchor/R-group 连接无遮挡, `ligand` 偏向配体投影展开.
- 非 ligand-only 图片会在渲染后做 PNG 方向校正, 尽量让 protein pocket 位于 ligand 下方, 改善画面重心.
- 可疑样本再下载对应 `complex_xxx/` 目录到本地 ChimeraX 旋转精查.

## 3. 拼图索引

| sample_id | view | status | num_images | contact_sheet |
|---|---|---|---|---|
| complex_crossdocked_000001 | clash | written | 12 | `runs/phase0_visual_check/complex_crossdocked_000001/images/clash_contact_sheet.png` |
| complex_crossdocked_000001 | ligand | written | 12 | `runs/phase0_visual_check/complex_crossdocked_000001/images/ligand_contact_sheet.png` |
| complex_crossdocked_000001 | overview | written | 12 | `runs/phase0_visual_check/complex_crossdocked_000001/images/overview_contact_sheet.png` |
| complex_crossdocked_000001 | rgroup | written | 12 | `runs/phase0_visual_check/complex_crossdocked_000001/images/rgroup_contact_sheet.png` |

## 4. 单图索引

| sample_id | view | angle | status | image |
|---|---|---|---|---|
| complex_crossdocked_000001 | overview | clear_01 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/overview_clear_01.png` |
| complex_crossdocked_000001 | overview | clear_02 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/overview_clear_02.png` |
| complex_crossdocked_000001 | overview | clear_03 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/overview_clear_03.png` |
| complex_crossdocked_000001 | overview | clear_04 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/overview_clear_04.png` |
| complex_crossdocked_000001 | overview | clear_05 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/overview_clear_05.png` |
| complex_crossdocked_000001 | overview | clear_06 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/overview_clear_06.png` |
| complex_crossdocked_000001 | overview | clear_07 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/overview_clear_07.png` |
| complex_crossdocked_000001 | overview | clear_08 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/overview_clear_08.png` |
| complex_crossdocked_000001 | overview | clear_09 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/overview_clear_09.png` |
| complex_crossdocked_000001 | overview | clear_10 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/overview_clear_10.png` |
| complex_crossdocked_000001 | overview | clear_11 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/overview_clear_11.png` |
| complex_crossdocked_000001 | overview | clear_12 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/overview_clear_12.png` |
| complex_crossdocked_000001 | clash | clear_01 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/clash_clear_01.png` |
| complex_crossdocked_000001 | clash | clear_02 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/clash_clear_02.png` |
| complex_crossdocked_000001 | clash | clear_03 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/clash_clear_03.png` |
| complex_crossdocked_000001 | clash | clear_04 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/clash_clear_04.png` |
| complex_crossdocked_000001 | clash | clear_05 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/clash_clear_05.png` |
| complex_crossdocked_000001 | clash | clear_06 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/clash_clear_06.png` |
| complex_crossdocked_000001 | clash | clear_07 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/clash_clear_07.png` |
| complex_crossdocked_000001 | clash | clear_08 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/clash_clear_08.png` |
| complex_crossdocked_000001 | clash | clear_09 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/clash_clear_09.png` |
| complex_crossdocked_000001 | clash | clear_10 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/clash_clear_10.png` |
| complex_crossdocked_000001 | clash | clear_11 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/clash_clear_11.png` |
| complex_crossdocked_000001 | clash | clear_12 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/clash_clear_12.png` |
| complex_crossdocked_000001 | rgroup | clear_01 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/rgroup_clear_01.png` |
| complex_crossdocked_000001 | rgroup | clear_02 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/rgroup_clear_02.png` |
| complex_crossdocked_000001 | rgroup | clear_03 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/rgroup_clear_03.png` |
| complex_crossdocked_000001 | rgroup | clear_04 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/rgroup_clear_04.png` |
| complex_crossdocked_000001 | rgroup | clear_05 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/rgroup_clear_05.png` |
| complex_crossdocked_000001 | rgroup | clear_06 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/rgroup_clear_06.png` |
| complex_crossdocked_000001 | rgroup | clear_07 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/rgroup_clear_07.png` |
| complex_crossdocked_000001 | rgroup | clear_08 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/rgroup_clear_08.png` |
| complex_crossdocked_000001 | rgroup | clear_09 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/rgroup_clear_09.png` |
| complex_crossdocked_000001 | rgroup | clear_10 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/rgroup_clear_10.png` |
| complex_crossdocked_000001 | rgroup | clear_11 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/rgroup_clear_11.png` |
| complex_crossdocked_000001 | rgroup | clear_12 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/rgroup_clear_12.png` |
| complex_crossdocked_000001 | ligand | clear_01 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/ligand_clear_01.png` |
| complex_crossdocked_000001 | ligand | clear_02 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/ligand_clear_02.png` |
| complex_crossdocked_000001 | ligand | clear_03 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/ligand_clear_03.png` |
| complex_crossdocked_000001 | ligand | clear_04 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/ligand_clear_04.png` |
| complex_crossdocked_000001 | ligand | clear_05 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/ligand_clear_05.png` |
| complex_crossdocked_000001 | ligand | clear_06 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/ligand_clear_06.png` |
| complex_crossdocked_000001 | ligand | clear_07 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/ligand_clear_07.png` |
| complex_crossdocked_000001 | ligand | clear_08 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/ligand_clear_08.png` |
| complex_crossdocked_000001 | ligand | clear_09 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/ligand_clear_09.png` |
| complex_crossdocked_000001 | ligand | clear_10 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/ligand_clear_10.png` |
| complex_crossdocked_000001 | ligand | clear_11 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/ligand_clear_11.png` |
| complex_crossdocked_000001 | ligand | clear_12 | rendered | `runs/phase0_visual_check/complex_crossdocked_000001/images/ligand_clear_12.png` |
