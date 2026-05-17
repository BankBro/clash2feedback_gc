# External Baselines

## 1. 目的

本文档记录 Clash2Feedback-GC 使用过或计划使用的外部 frozen baseline 的长期可复现信息。

外部仓库和 checkpoint 默认放在 `external/` 下, 但这些重资产不提交 Git。后续阅读仓库时, 应先从本文档确认外部代码来源, commit, checkpoint 和关键入口文件。

## 2. DiffSBDD

### 2.1 Source Provenance

```text
Model: DiffSBDD
Source repo: https://github.com/BankBro/DiffSBDD.git
Upstream source: https://github.com/arneschneuing/DiffSBDD.git
Pinned commit: 5d0d38d16c8932a0339fd2ce3f67ade98bbdff27
Local path: external/DiffSBDD/
Primary entrypoint: external/DiffSBDD/generate_ligands.py
Inpainting entrypoint: external/DiffSBDD/inpaint.py
Conda environment: diffsbdd
Mode in this project: frozen inference only
```

Phase 4.0.1 GPU inpainting 使用 Clash2Feedback-GC 外部补丁分支, 不合入 DiffSBDD 原始 `main`:

```text
Branch: clash2feedback_gc
Base commit: 5d0d38d16c8932a0339fd2ce3f67ade98bbdff27
Patch commit: a3d49bba85d6426120759cd7b1b856d9b84471f2
Patch scope: external/DiffSBDD/inpaint.py moves lig_mask to CPU before batch_to_list in molecule-building post-processing.
Denoising change: no
Reason: the original GPU path moves generated x and atom_type tensors to CPU, but leaves lig_mask on CUDA, causing a CPU/CUDA tensor indexing error before SDF writing.
Historical branch name used during Phase 4.0.1 run: 20260517-080227-phase4-0-1-gpu-inpaint-fix
```

关键源码路径:

```text
external/DiffSBDD/generate_ligands.py
external/DiffSBDD/lightning_modules.py::LigandPocketDDPM.generate_ligands
external/DiffSBDD/analysis/molecule_builder.py::build_molecule
external/DiffSBDD/analysis/molecule_builder.py::process_molecule
external/DiffSBDD/utils.py::write_sdf_file
```

### 2.2 Checkpoint Provenance

```text
Primary checkpoint name: crossdocked_fullatom_cond.ckpt
Primary checkpoint URL: https://zenodo.org/records/8183747/files/crossdocked_fullatom_cond.ckpt?download=1
Primary local path: external/DiffSBDD/checkpoints/crossdocked_fullatom_cond.ckpt
Primary MD5: 166b0c056b31ffdf31d489a63e91e05b
Primary SHA256: 07f86764bf569aafbc40a9c15fc02de8e2550437dd0f17f657eab3abe66c372c
Primary file size: 17861341 bytes
Additional local checkpoints downloaded for phase4.0 inventory:
  - crossdocked_fullatom_joint.ckpt: MD5 f9291871ccf820d273607e4fb816cafc, SHA256 4e0f8727c7e4c9d8c8963927ac218a9b6f777104c396f0f8c7aa4a0b88e598bd
  - crossdocked_ca_cond.ckpt: MD5 e29520a99ceefe244f08d0429312bf15, SHA256 cc96a8cbb52c94db638a9d56c7b381bc7e517418fbed6cd7e1bf1df488e5ff20
  - crossdocked_ca_joint.ckpt: MD5 64ec4c3405afb847dc8fbb7a0e33c25b, SHA256 b66cf6b6e61300c561c8d4c4418cb0e5474ed18a95524942460acb58449615f9
  - moad_ca_cond.ckpt: MD5 487759042e9386c3afe22a0ae4cad898, SHA256 ef5d62a07a031b9d2032f5ebf0835d9244706e71bb621fd36d9b305fec58e58f
  - moad_ca_joint.ckpt: MD5 d51ef07cd6d0d3ebfb430dcf65f23de7, SHA256 0b0fd3c9483afbe48f6717d3aa88fb216669c3f6e625646500f4db15331fd13c
  - moad_fullatom_cond.ckpt: MD5 49e0c0a3ca7468bd8998e353308e6cec, SHA256 58bd5f6c532e64a727f92779c6d3d7f274e5df7b0d345e4900a99dd341192561
  - moad_fullatom_joint.ckpt: MD5 d1294c7c81bb6016d5d712ce24f071a2, SHA256 b16aebaab0a71ee0295c990fbea50cfca23aadf410fc263c646483653e99f494
```

### 2.3 Output Contract Used By Clash2Feedback-GC

DiffSBDD core model samples ligand atom types and 3D coordinates conditioned on a protein pocket.

```text
protein pocket -> ligand atom types + 3D coordinates
```

DiffSBDD then builds RDKit molecules and writes SDF files:

```text
atom types + 3D coordinates -> inferred bonds -> RDKit molecule -> SDF
```

In Phase 2.5, Clash2Feedback-GC consumes DiffSBDD's generated SDF files, not the internal point-cloud tensors. The Phase 2.5 `raw_generated` stage means the SDF written by DiffSBDD `generate_ligands.py`.

### 2.4 Rebuild Commands

Prepare or refresh the external DiffSBDD dependency through the project wrapper:

```bash
conda run -n c2f_cpu python scripts/phase2_5_prepare_diffsbdd.py \
  --config configs/phase2_5_model_induced_audit.yaml \
  --report-root reports/phase2_5_model_induced_audit \
  --run-root runs/phase2_5_model_induced_audit
```

The wrapper clones or checks `external/DiffSBDD/`, pins the commit, checks the checkpoint, verifies the `diffsbdd` environment and writes actual setup provenance to:

```text
reports/phase2_5_model_induced_audit/external_setup.json
```

## 3. Candidate Local Repair Backends

### 3.1 DiffSBDD

```text
status: verified_for_phase2_5_frozen_de_novo_audit
role:
  - de novo audit baseline
  - full resampling baseline candidate
  - candidate inpainting backend to be evaluated in phase4_0
limitation:
  - 原生 DiffSBDD 不直接接收完整 Clash2Feedback feedback.
  - H_clash / old-clash-resolved / no-new-clash 主要由 verifier / selector 使用.
  - 若要在生成过程中避开 old clash heatmap, 需要 guided sampling patch.
```

### 3.2 DiffDec

```text
status: verified_for_phase4_0_frozen_single_rgroup_inference
source repo: https://github.com/BankBro/DiffDec.git
pinned commit: 916ae14207b2783a90336bb8509374535c5791f9
local path: external/DiffDec/
primary entrypoints:
  - external/DiffDec/sample_single_for_specific_context.py
  - external/DiffDec/sample_multi.py
conda environment: DiffDec
checkpoint status: downloaded_and_verified_for_phase4_0
single checkpoint: external/DiffDec/ckpt/diffdec_single.ckpt
single checkpoint MD5: 9be531ec26376d8282c69d6c58630324
single checkpoint SHA256: 59776b4049ff6bcc068ae0a551a1271a48f164ff8b7bec6e6f8d6846c635129b
multi checkpoint: external/DiffDec/ckpt/diffdec_multi.ckpt
multi checkpoint MD5: 5c345e172ee6f1ab55a81d91515baa4a
multi checkpoint SHA256: bae7c56a61eb3454cf69dd6febdb6dd93b91e7fd6dc0851fd0854a3dd0356591
role:
  - scaffold decoration / R-group generation candidate backend
  - 阶段 4.0 backend feasibility audit 第一优先核查对象之一
limitation:
  - 原版 DiffDec 应按 anchor-aware R-group resampling / local constrained generation 评估.
  - 不保证避开旧 clash.
  - 不原生接收 H_clash / severity / no-new-clash 约束.
  - 在未修改 sampling / denoising loop 前, 不得写成完整 feedback-guided denoising.
```

阶段 4 文档中, DiffSBDD / DiffDec plain backend 统一表述为 `local constrained resampling` 或 candidate backend. 只有实现 clash penalty / hot region guidance 并改采样过程后, 才能声称 `H_clash` 进入生成过程.

## 4. 维护规则

- 新增外部 baseline 时, 在本文档增加 source repo, pinned commit, local path, checkpoint provenance 和关键代码路径。
- 外部源码, checkpoint 和生成缓存保留在 `external/` 或 `runs/`, 默认不提交 Git。
- 外部源码非必要不修改; 必须修补阻塞 bug 或兼容性问题时, 补丁统一提交到对应外部仓库的 `clash2feedback_gc` 分支, 并保持外部方法原有算法原理和语义不变。
- 单次实验的实际命令, GPU 状态, smoke test 和结果摘要写入 `reports/`, 不写入本文档。
