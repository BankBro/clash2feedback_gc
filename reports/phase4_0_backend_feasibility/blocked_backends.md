# Phase 4.0 Blocked Backends

## 1. Scope

- 本文件记录当前 phase4.0 inventory 中不可执行或不进入主线的后端.
- 阻塞后端不影响已执行后端进入统一 verifier 分母.

## 2. Blocked Inventory

| backend_name | backend_unit | status | blocked_reason |
|---|---|---|---|
| diffsbdd_joint_inpainting | crossdocked_fullatom_joint_local_completion | blocked | official_inpaint_entrypoint_incompatible_with_joint_checkpoint:center_argument |

## 3. Constraints

- checkpoint/env 状态以当前 `model_inventory.csv` 为准.
- 未修改 DiffSBDD 或 DiffDec 原始源码.
- 未把 `H_clash` 写入任何生成过程.
