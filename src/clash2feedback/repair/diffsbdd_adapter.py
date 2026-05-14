from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from clash2feedback.repair.phase4_inputs import Phase4CaseInput, adapter_input_row, read_first_mol, write_keep_submol_sdf


def build_diffsbdd_inventory(config: dict[str, Any], *, repo_root: Path) -> list[dict[str, Any]]:
    backends = config.get("backends", {})
    rows = []
    cond = backends.get("diffsbdd_conditional_inpainting", {})
    if cond:
        rows.append(_inventory_row(cond, repo_root=repo_root, model_key="diffsbdd_conditional_inpainting"))
    full = backends.get("diffsbdd_full_resampling", {})
    if full:
        rows.append(_inventory_row(full, repo_root=repo_root, model_key="diffsbdd_full_resampling"))
    joint = backends.get("diffsbdd_joint_inpainting", {})
    if joint:
        rows.append(_inventory_row(joint, repo_root=repo_root, model_key="diffsbdd_joint_inpainting"))
    return rows


def run_diffsbdd_conditional_case(
    case_input: Phase4CaseInput,
    *,
    backend_cfg: dict[str, Any],
    inventory_row: dict[str, Any],
    repo_root: Path,
    run_root: str | Path,
    k: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    backend_name = str(backend_cfg.get("backend_name", "diffsbdd_conditional_inpainting"))
    backend_unit = str(backend_cfg.get("backend_unit", "crossdocked_fullatom_conditional_local_completion"))
    centers = list(backend_cfg.get("centers", ["ligand"]))
    run_dir = Path(run_root) / "diffsbdd_inpainting" / case_input.case_id
    run_dir.mkdir(parents=True, exist_ok=True)
    fix_atoms_path = run_dir / "fix_atoms.sdf"

    input_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    try:
        fix_meta = write_keep_submol_sdf(case_input, fix_atoms_path)
        adapter_status = "prepared"
        adapter_failure = ""
    except Exception as exc:
        fix_meta = {"fix_atoms_sdf": str(fix_atoms_path), "fixed_atom_count": 0, "add_n_nodes": len(case_input.mask_atom_indices)}
        adapter_status = "failed"
        adapter_failure = f"{type(exc).__name__}:{exc}"

    for center in centers:
        command = build_inpaint_command(
            backend_cfg,
            case_input=case_input,
            repo_root=repo_root,
            fix_atoms_sdf=fix_atoms_path,
            output_sdf=run_dir / f"diffsbdd_{center}_raw.sdf",
            center=str(center),
        )
        input_rows.append(
            adapter_input_row(
                case_input,
                backend_name=backend_name,
                backend_unit=backend_unit,
                status=adapter_status if str(inventory_row.get("status")) != "blocked" else "blocked",
                fix_atoms_sdf=str(fix_atoms_path),
                fixed_atom_count=fix_meta.get("fixed_atom_count", 0),
                add_n_nodes=fix_meta.get("add_n_nodes", len(case_input.mask_atom_indices)),
                center=str(center),
                command_json=json.dumps(command, ensure_ascii=False),
                uses_h_clash_in_generation=bool(backend_cfg.get("uses_h_clash_in_generation", False)),
                adapter_failure_reason=adapter_failure,
            )
        )
        if adapter_status != "prepared":
            candidate_rows.append(
                _failure_candidate_row(
                    case_input,
                    backend_name=backend_name,
                    backend_unit=backend_unit,
                    center=str(center),
                    proposal_count=0,
                    runtime_sec=0.0,
                    failure_stage="adapter",
                    failure_reason=adapter_failure,
                )
            )
            continue
        if str(inventory_row.get("status")) == "blocked":
            candidate_rows.append(
                _failure_candidate_row(
                    case_input,
                    backend_name=backend_name,
                    backend_unit=backend_unit,
                    center=str(center),
                    proposal_count=0,
                    runtime_sec=0.0,
                    failure_stage="model_inventory",
                    failure_reason=str(inventory_row.get("blocked_reason") or "diffsbdd_conditional_blocked"),
                )
            )
            continue
        if not bool(backend_cfg.get("execute", True)):
            candidate_rows.append(
                _failure_candidate_row(
                    case_input,
                    backend_name=backend_name,
                    backend_unit=backend_unit,
                    center=str(center),
                    proposal_count=0,
                    runtime_sec=0.0,
                    failure_stage="execution",
                    failure_reason="execution_disabled",
                )
            )
            continue
        candidate_rows.extend(
            _run_inpaint_command(
                case_input,
                backend_cfg=backend_cfg,
                backend_name=backend_name,
                backend_unit=backend_unit,
                center=str(center),
                command=command,
                run_dir=run_dir,
                repo_root=repo_root,
                k=k,
            )
        )
    return input_rows, candidate_rows


def run_diffsbdd_full_resampling_case(
    case_input: Phase4CaseInput,
    *,
    backend_cfg: dict[str, Any],
    inventory_row: dict[str, Any],
    repo_root: Path,
    run_root: str | Path,
    k: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    backend_name = str(backend_cfg.get("backend_name", "diffsbdd_full_resampling"))
    backend_unit = str(backend_cfg.get("backend_unit", "crossdocked_fullatom_conditional_full_ligand_resampling"))
    run_dir = Path(run_root) / "full_resampling" / case_input.case_id
    run_dir.mkdir(parents=True, exist_ok=True)
    output_sdf = run_dir / "diffsbdd_full_resampling_raw.sdf"
    command = build_full_resampling_command(
        backend_cfg,
        case_input=case_input,
        repo_root=repo_root,
        output_sdf=output_sdf,
    )
    input_rows = [
        adapter_input_row(
            case_input,
            backend_name=backend_name,
            backend_unit=backend_unit,
            status="prepared" if str(inventory_row.get("status")) != "blocked" else "blocked",
            command_json=json.dumps(command, ensure_ascii=False),
            add_n_nodes=0,
            center="full_ligand",
            uses_h_clash_in_generation=bool(backend_cfg.get("uses_h_clash_in_generation", False)),
        )
    ]
    if str(inventory_row.get("status")) == "blocked":
        return input_rows, [
            _failure_candidate_row(
                case_input,
                backend_name=backend_name,
                backend_unit=backend_unit,
                center="full_ligand",
                proposal_count=0,
                runtime_sec=0.0,
                failure_stage="model_inventory",
                failure_reason=str(inventory_row.get("blocked_reason") or "diffsbdd_full_resampling_blocked"),
            )
        ]
    if not bool(backend_cfg.get("execute", True)):
        return input_rows, [
            _failure_candidate_row(
                case_input,
                backend_name=backend_name,
                backend_unit=backend_unit,
                center="full_ligand",
                proposal_count=0,
                runtime_sec=0.0,
                failure_stage="execution",
                failure_reason="execution_disabled",
            )
        ]
    rows = _run_generation_command(
        case_input,
        backend_cfg=backend_cfg,
        backend_name=backend_name,
        backend_unit=backend_unit,
        center="full_ligand",
        command=command,
        run_dir=run_dir,
        repo_root=repo_root,
        output_sdf=output_sdf,
        k=k,
    )
    return input_rows, rows


def blocked_candidate_rows_for_backend(
    case_inputs: list[Phase4CaseInput],
    *,
    inventory_row: dict[str, Any],
) -> list[dict[str, Any]]:
    backend_name = str(inventory_row.get("backend_name") or inventory_row.get("model_key") or "")
    backend_unit = str(inventory_row.get("backend_unit") or "")
    return [
        _failure_candidate_row(
            case_input,
            backend_name=backend_name,
            backend_unit=backend_unit,
            center="",
            proposal_count=0,
            runtime_sec=0.0,
            failure_stage="model_inventory",
            failure_reason=str(inventory_row.get("blocked_reason") or "backend_blocked"),
        )
        for case_input in case_inputs
    ]


def build_inpaint_command(
    backend_cfg: dict[str, Any],
    *,
    case_input: Phase4CaseInput,
    repo_root: Path,
    fix_atoms_sdf: str | Path,
    output_sdf: str | Path,
    center: str,
) -> list[str]:
    checkpoint = _resolve(backend_cfg.get("checkpoint_path", ""), repo_root)
    command: list[str] = []
    conda_env = str(backend_cfg.get("conda_env") or "")
    if conda_env:
        command.extend(["conda", "run", "--no-capture-output", "-n", conda_env])
    command.extend(
        [
            str(backend_cfg.get("python_executable") or "python"),
            "inpaint.py",
            str(checkpoint),
            "--pdbfile",
            str(case_input.raw_protein_path),
            "--ref_ligand",
            str(case_input.failed_ligand_sdf),
            "--fix_atoms",
            str(fix_atoms_sdf),
            "--center",
            str(center),
            "--outfile",
            str(output_sdf),
            "--n_samples",
            str(int(backend_cfg.get("n_samples", 8))),
            "--add_n_nodes",
            str(len(case_input.mask_atom_indices)),
            "--resamplings",
            str(int(backend_cfg.get("resamplings", 1))),
            "--timesteps",
            str(int(backend_cfg.get("timesteps", 50))),
        ]
    )
    if bool(backend_cfg.get("sanitize", False)):
        command.append("--sanitize")
    if bool(backend_cfg.get("relax", False)):
        command.append("--relax")
    return command


def build_full_resampling_command(
    backend_cfg: dict[str, Any],
    *,
    case_input: Phase4CaseInput,
    repo_root: Path,
    output_sdf: str | Path,
) -> list[str]:
    checkpoint = _resolve(backend_cfg.get("checkpoint_path", ""), repo_root)
    command: list[str] = []
    conda_env = str(backend_cfg.get("conda_env") or "")
    if conda_env:
        command.extend(["conda", "run", "--no-capture-output", "-n", conda_env])
    command.extend(
        [
            str(backend_cfg.get("python_executable") or "python"),
            "generate_ligands.py",
            str(checkpoint),
            "--pdbfile",
            str(case_input.raw_protein_path),
            "--ref_ligand",
            str(case_input.failed_ligand_sdf),
            "--outfile",
            str(output_sdf),
            "--n_samples",
            str(int(backend_cfg.get("n_samples", 8))),
            "--batch_size",
            str(int(backend_cfg.get("batch_size", backend_cfg.get("n_samples", 8)))),
            "--resamplings",
            str(int(backend_cfg.get("resamplings", 1))),
            "--jump_length",
            str(int(backend_cfg.get("jump_length", 1))),
        ]
    )
    if backend_cfg.get("timesteps") is not None:
        command.extend(["--timesteps", str(int(backend_cfg.get("timesteps")))])
    if bool(backend_cfg.get("use_failed_ligand_atom_count", True)):
        command.extend(["--num_nodes_lig", str(_failed_ligand_atom_count(case_input))])
    if bool(backend_cfg.get("sanitize", False)):
        command.append("--sanitize")
    if bool(backend_cfg.get("relax", False)):
        command.append("--relax")
    if bool(backend_cfg.get("all_frags", False)):
        command.append("--all_frags")
    return command


def _run_inpaint_command(
    case_input: Phase4CaseInput,
    *,
    backend_cfg: dict[str, Any],
    backend_name: str,
    backend_unit: str,
    center: str,
    command: list[str],
    run_dir: Path,
    repo_root: Path,
    k: int,
) -> list[dict[str, Any]]:
    external_repo = _resolve(backend_cfg.get("external_repo", "external/DiffSBDD"), repo_root)
    output_sdf = run_dir / f"diffsbdd_{center}_raw.sdf"
    log_path = run_dir / f"diffsbdd_{center}.log"
    timeout_sec = int(backend_cfg.get("timeout_sec", 180))
    start = time.perf_counter()
    env = os.environ.copy()
    if "cuda_visible_devices" in backend_cfg:
        env["CUDA_VISIBLE_DEVICES"] = str(backend_cfg.get("cuda_visible_devices") or "")
    try:
        with log_path.open("w", encoding="utf-8") as log:
            log.write("$ " + " ".join(command) + "\n")
            completed = subprocess.run(
                command,
                cwd=str(external_repo),
                env=env,
                text=True,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=timeout_sec,
            )
        runtime_sec = time.perf_counter() - start
    except subprocess.TimeoutExpired:
        runtime_sec = time.perf_counter() - start
        with log_path.open("a", encoding="utf-8") as log:
            log.write(f"\nTIMEOUT after {timeout_sec} sec\n")
        return [
            _failure_candidate_row(
                case_input,
                backend_name=backend_name,
                backend_unit=backend_unit,
                center=center,
                proposal_count=int(backend_cfg.get("n_samples", 8)),
                runtime_sec=runtime_sec,
                failure_stage="execution",
                failure_reason=f"timeout_after_{timeout_sec}_sec",
                log_path=log_path,
            )
        ]

    if completed.returncode != 0:
        return [
            _failure_candidate_row(
                case_input,
                backend_name=backend_name,
                backend_unit=backend_unit,
                center=center,
                proposal_count=int(backend_cfg.get("n_samples", 8)),
                runtime_sec=runtime_sec,
                failure_stage="execution",
                failure_reason=f"returncode_{completed.returncode}",
                log_path=log_path,
            )
        ]
    return _split_sdf_candidates(
        case_input,
        output_sdf=output_sdf,
        backend_name=backend_name,
        backend_unit=backend_unit,
        center=center,
        proposal_count=int(backend_cfg.get("n_samples", 8)),
        runtime_sec=runtime_sec,
        log_path=log_path,
        k=k,
    )


def _run_generation_command(
    case_input: Phase4CaseInput,
    *,
    backend_cfg: dict[str, Any],
    backend_name: str,
    backend_unit: str,
    center: str,
    command: list[str],
    run_dir: Path,
    repo_root: Path,
    output_sdf: Path,
    k: int,
) -> list[dict[str, Any]]:
    external_repo = _resolve(backend_cfg.get("external_repo", "external/DiffSBDD"), repo_root)
    log_path = run_dir / "diffsbdd_full_resampling.log"
    timeout_sec = int(backend_cfg.get("timeout_sec", 180))
    start = time.perf_counter()
    env = os.environ.copy()
    if "cuda_visible_devices" in backend_cfg:
        env["CUDA_VISIBLE_DEVICES"] = str(backend_cfg.get("cuda_visible_devices") or "")
    try:
        with log_path.open("w", encoding="utf-8") as log:
            log.write("$ " + " ".join(command) + "\n")
            completed = subprocess.run(
                command,
                cwd=str(external_repo),
                env=env,
                text=True,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=timeout_sec,
            )
        runtime_sec = time.perf_counter() - start
    except subprocess.TimeoutExpired:
        runtime_sec = time.perf_counter() - start
        with log_path.open("a", encoding="utf-8") as log:
            log.write(f"\nTIMEOUT after {timeout_sec} sec\n")
        return [
            _failure_candidate_row(
                case_input,
                backend_name=backend_name,
                backend_unit=backend_unit,
                center=center,
                proposal_count=int(backend_cfg.get("n_samples", 8)),
                runtime_sec=runtime_sec,
                failure_stage="execution",
                failure_reason=f"timeout_after_{timeout_sec}_sec",
                log_path=log_path,
            )
        ]
    if completed.returncode != 0:
        return [
            _failure_candidate_row(
                case_input,
                backend_name=backend_name,
                backend_unit=backend_unit,
                center=center,
                proposal_count=int(backend_cfg.get("n_samples", 8)),
                runtime_sec=runtime_sec,
                failure_stage="execution",
                failure_reason=f"returncode_{completed.returncode}",
                log_path=log_path,
            )
        ]
    return _split_sdf_candidates(
        case_input,
        output_sdf=output_sdf,
        backend_name=backend_name,
        backend_unit=backend_unit,
        center=center,
        proposal_count=int(backend_cfg.get("n_samples", 8)),
        runtime_sec=runtime_sec,
        log_path=log_path,
        k=k,
    )


def _split_sdf_candidates(
    case_input: Phase4CaseInput,
    *,
    output_sdf: Path,
    backend_name: str,
    backend_unit: str,
    center: str,
    proposal_count: int,
    runtime_sec: float,
    log_path: Path,
    k: int,
) -> list[dict[str, Any]]:
    from rdkit import Chem

    if not output_sdf.exists():
        return [
            _failure_candidate_row(
                case_input,
                backend_name=backend_name,
                backend_unit=backend_unit,
                center=center,
                proposal_count=proposal_count,
                runtime_sec=runtime_sec,
                failure_stage="output_read",
                failure_reason="output_sdf_missing",
                log_path=log_path,
            )
        ]
    supplier = Chem.SDMolSupplier(str(output_sdf), sanitize=False, removeHs=False)
    mols = [mol for mol in supplier if mol is not None]
    if not mols:
        return [
            _failure_candidate_row(
                case_input,
                backend_name=backend_name,
                backend_unit=backend_unit,
                center=center,
                proposal_count=proposal_count,
                runtime_sec=runtime_sec,
                failure_stage="output_read",
                failure_reason="no_readable_molecules_in_output_sdf",
                log_path=log_path,
            )
        ]
    rows = []
    selected = mols[: max(int(k), 0)]
    for index, mol in enumerate(selected, start=1):
        candidate_path = output_sdf.with_name(f"diffsbdd_{center}_candidate_{index:03d}.sdf")
        writer = Chem.SDWriter(str(candidate_path))
        writer.write(mol)
        writer.close()
        rows.append(
            {
                "backend_name": backend_name,
                "backend_unit": backend_unit,
                "case_id": case_input.case_id,
                "base_sample_id": case_input.base_sample_id,
                "attempt_id": f"{backend_name}:{center}:{case_input.case_id}",
                "candidate_id": f"{backend_name}:{center}:{case_input.case_id}:{index:03d}",
                "candidate_index": int(index),
                "candidate_path": str(candidate_path),
                "candidate_source": f"diffsbdd_inpaint_center_{center}",
                "proposal_count": int(proposal_count),
                "candidate_count": int(len(selected)),
                "runtime_sec": float(runtime_sec),
                "failure_stage": "",
                "failure_reason": "",
                "same_topology": False,
                "requires_fixed_structure_match": True,
                "uses_h_clash_in_generation": False,
                "generation_metadata": {"center": center, "raw_output_sdf": str(output_sdf), "log_path": str(log_path)},
            }
        )
    return rows


def _failure_candidate_row(
    case_input: Phase4CaseInput,
    *,
    backend_name: str,
    backend_unit: str,
    center: str,
    proposal_count: int,
    runtime_sec: float,
    failure_stage: str,
    failure_reason: str,
    log_path: str | Path = "",
) -> dict[str, Any]:
    return {
        "backend_name": backend_name,
        "backend_unit": backend_unit,
        "case_id": case_input.case_id,
        "base_sample_id": case_input.base_sample_id,
        "attempt_id": f"{backend_name}:{center}:{case_input.case_id}" if center else f"{backend_name}:{case_input.case_id}",
        "candidate_id": "",
        "candidate_index": 0,
        "candidate_path": "",
        "candidate_source": f"diffsbdd_inpaint_center_{center}" if center else backend_name,
        "proposal_count": int(proposal_count),
        "candidate_count": 0,
        "runtime_sec": float(runtime_sec),
        "failure_stage": failure_stage,
        "failure_reason": failure_reason,
        "same_topology": False,
        "requires_fixed_structure_match": True,
        "uses_h_clash_in_generation": False,
        "generation_metadata": {"center": center, "log_path": str(log_path) if log_path else ""},
    }


def _inventory_row(backend_cfg: dict[str, Any], *, repo_root: Path, model_key: str) -> dict[str, Any]:
    external_repo = _resolve(backend_cfg.get("external_repo", ""), repo_root)
    checkpoint = _resolve(backend_cfg.get("checkpoint_path", ""), repo_root)
    blocked: list[str] = []
    if not external_repo.exists():
        blocked.append(f"external_repo_missing:{external_repo}")
    if model_key in {"diffsbdd_conditional_inpainting", "diffsbdd_joint_inpainting"} and not (external_repo / "inpaint.py").exists():
        blocked.append(f"inpaint_entrypoint_missing:{external_repo / 'inpaint.py'}")
    if model_key == "diffsbdd_full_resampling" and not (external_repo / "generate_ligands.py").exists():
        blocked.append(f"generate_ligands_entrypoint_missing:{external_repo / 'generate_ligands.py'}")
    if not bool(backend_cfg.get("adapter_supported", True)):
        blocked.append(str(backend_cfg.get("adapter_blocked_reason") or "adapter_not_supported"))
    if not checkpoint.exists():
        blocked.append(f"checkpoint_missing:{checkpoint}")
    repo_commit = _git_commit(external_repo) if external_repo.exists() else ""
    expected_commit = str(backend_cfg.get("expected_repo_commit") or "")
    if expected_commit and repo_commit and repo_commit != expected_commit:
        blocked.append(f"repo_commit_mismatch:{repo_commit}!={expected_commit}")
    md5 = _digest(checkpoint, "md5") if checkpoint.exists() else ""
    sha256 = _digest(checkpoint, "sha256") if checkpoint.exists() else ""
    expected_md5 = str(backend_cfg.get("expected_checkpoint_md5") or "")
    expected_sha256 = str(backend_cfg.get("expected_checkpoint_sha256") or "")
    if expected_md5 and md5 and md5 != expected_md5:
        blocked.append(f"checkpoint_md5_mismatch:{md5}!={expected_md5}")
    if expected_sha256 and sha256 and sha256 != expected_sha256:
        blocked.append(f"checkpoint_sha256_mismatch:{sha256}!={expected_sha256}")
    env_status, env_output = _check_conda_env(str(backend_cfg.get("conda_env") or ""))
    if env_status != "ready":
        blocked.append(f"conda_env_not_ready:{env_status}")
    return {
        "model_key": model_key,
        "backend_name": str(backend_cfg.get("backend_name") or model_key),
        "backend_unit": str(backend_cfg.get("backend_unit") or ""),
        "external_repo": str(external_repo),
        "repo_commit": repo_commit,
        "expected_repo_commit": expected_commit,
        "checkpoint_path": str(checkpoint),
        "checkpoint_exists": bool(checkpoint.exists()),
        "checkpoint_md5": md5,
        "checkpoint_sha256": sha256,
        "checkpoint_file_size": int(checkpoint.stat().st_size) if checkpoint.exists() else 0,
        "conda_env": str(backend_cfg.get("conda_env") or ""),
        "env_status": env_status,
        "env_check_output": env_output,
        "status": "blocked" if blocked else "ready",
        "blocked_reason": ";".join(blocked),
        "uses_h_clash_in_generation": bool(backend_cfg.get("uses_h_clash_in_generation", False)),
    }


def _failed_ligand_atom_count(case_input: Phase4CaseInput) -> int:
    mol = read_first_mol(case_input.failed_ligand_sdf, sanitize=False)
    return int(mol.GetNumAtoms())


def _check_conda_env(conda_env: str) -> tuple[str, str]:
    if not conda_env:
        return "not_configured", ""
    command = [
        "conda",
        "run",
        "-n",
        conda_env,
        "python",
        "-c",
        "import torch, rdkit, pytorch_lightning, Bio; print('ready cuda=' + str(torch.cuda.is_available()))",
    ]
    try:
        completed = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=60)
    except Exception as exc:
        return "check_failed", f"{type(exc).__name__}:{exc}"
    if completed.returncode != 0:
        return "failed", completed.stdout.strip()
    return "ready", completed.stdout.strip()


def _git_commit(path: Path) -> str:
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(path), text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _digest(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve(path_value: Any, repo_root: Path) -> Path:
    path = Path(str(path_value))
    return path if path.is_absolute() else (repo_root / path).resolve()
