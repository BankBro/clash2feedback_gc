from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from clash2feedback.repair.phase4_inputs import Phase4CaseInput, adapter_input_row, read_first_mol


def build_diffdec_inventory(config: dict[str, Any], *, repo_root: Path) -> list[dict[str, Any]]:
    backend_cfg = config.get("backends", {}).get("diffdec_single_rgroup", {})
    if not backend_cfg:
        return []
    external_repo = _resolve(backend_cfg.get("external_repo", ""), repo_root)
    checkpoint = _resolve(backend_cfg.get("checkpoint_path", ""), repo_root)
    blocked: list[str] = []
    if not external_repo.exists():
        blocked.append(f"external_repo_missing:{external_repo}")
    if not (external_repo / "sample_single_for_specific_context.py").exists():
        blocked.append(f"entrypoint_missing:{external_repo / 'sample_single_for_specific_context.py'}")
    if not checkpoint.exists():
        blocked.append(f"checkpoint_missing:{checkpoint}")
    env_status, env_output = _check_conda_env(str(backend_cfg.get("conda_env") or ""))
    if env_status != "ready":
        blocked.append(f"conda_env_not_ready:{env_status}")
    return [
        {
            "model_key": "diffdec_single_rgroup",
            "backend_name": str(backend_cfg.get("backend_name") or "diffdec_single_rgroup"),
            "backend_unit": str(backend_cfg.get("backend_unit") or "single_substituent_local_completion"),
            "external_repo": str(external_repo),
            "repo_commit": _git_commit(external_repo) if external_repo.exists() else "",
            "expected_repo_commit": "",
            "checkpoint_path": str(checkpoint),
            "checkpoint_exists": bool(checkpoint.exists()),
            "checkpoint_md5": _digest(checkpoint, "md5") if checkpoint.exists() else "",
            "checkpoint_sha256": _digest(checkpoint, "sha256") if checkpoint.exists() else "",
            "checkpoint_file_size": int(checkpoint.stat().st_size) if checkpoint.exists() else 0,
            "conda_env": str(backend_cfg.get("conda_env") or ""),
            "env_status": env_status,
            "env_check_output": env_output,
            "status": "blocked" if blocked else "ready",
            "blocked_reason": ";".join(blocked),
            "uses_h_clash_in_generation": False,
        }
    ]


def run_diffdec_case(
    case_input: Phase4CaseInput,
    *,
    backend_cfg: dict[str, Any],
    inventory_row: dict[str, Any],
    repo_root: Path,
    run_root: str | Path,
    k: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    backend_name = str(backend_cfg.get("backend_name", "diffdec_single_rgroup"))
    backend_unit = str(backend_cfg.get("backend_unit", "single_substituent_local_completion"))
    run_dir = Path(run_root) / "diffdec_single_rgroup" / case_input.case_id
    data_dir = run_dir / "data"
    samples_dir = run_dir / "samples"
    run_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    samples_dir.mkdir(parents=True, exist_ok=True)

    input_rows: list[dict[str, Any]] = []
    if str(inventory_row.get("status")) == "blocked":
        input_rows.append(
            adapter_input_row(
                case_input,
                backend_name=backend_name,
                backend_unit=backend_unit,
                status="blocked",
                blocked_reason=str(inventory_row.get("blocked_reason") or ""),
                uses_h_clash_in_generation=False,
            )
        )
        return input_rows, [
            _candidate_row(
                case_input,
                backend_name=backend_name,
                backend_unit=backend_unit,
                candidate_index=0,
                candidate_path="",
                proposal_count=0,
                candidate_count=0,
                runtime_sec=0.0,
                failure_stage="model_inventory",
                failure_reason=str(inventory_row.get("blocked_reason") or "diffdec_blocked"),
            )
        ]

    try:
        scaffold_meta = write_diffdec_scaffold_inputs(
            case_input,
            scaffold_file=run_dir / "fixed_context.sdf",
            scaffold_smiles_file=run_dir / "fixed_context.smi",
        )
        adapter_status = "prepared"
        adapter_failure = ""
    except Exception as exc:
        scaffold_meta = {}
        adapter_status = "failed"
        adapter_failure = f"{type(exc).__name__}:{exc}"

    command = build_diffdec_command(
        backend_cfg,
        repo_root=repo_root,
        scaffold_smiles_file=run_dir / "fixed_context.smi",
        protein_file=case_input.raw_protein_path,
        scaffold_file=run_dir / "fixed_context.sdf",
        task_name=case_input.case_id,
        data_dir=data_dir,
        samples_dir=samples_dir,
    )
    input_rows.append(
        adapter_input_row(
            case_input,
            backend_name=backend_name,
            backend_unit=backend_unit,
            status=adapter_status,
            scaffold_file=str(run_dir / "fixed_context.sdf"),
            scaffold_smiles_file=str(run_dir / "fixed_context.smi"),
            fixed_atom_count=scaffold_meta.get("fixed_atom_count", 0),
            command_json=json.dumps(command, ensure_ascii=False),
            uses_h_clash_in_generation=False,
            adapter_failure_reason=adapter_failure,
        )
    )
    if adapter_status != "prepared":
        return input_rows, [
            _candidate_row(
                case_input,
                backend_name=backend_name,
                backend_unit=backend_unit,
                candidate_index=0,
                candidate_path="",
                proposal_count=0,
                candidate_count=0,
                runtime_sec=0.0,
                failure_stage="adapter",
                failure_reason=adapter_failure,
            )
        ]
    if not bool(backend_cfg.get("execute", True)):
        return input_rows, [
            _candidate_row(
                case_input,
                backend_name=backend_name,
                backend_unit=backend_unit,
                candidate_index=0,
                candidate_path="",
                proposal_count=0,
                candidate_count=0,
                runtime_sec=0.0,
                failure_stage="execution",
                failure_reason="execution_disabled",
            )
        ]
    return input_rows, _run_diffdec_command(
        case_input,
        backend_cfg=backend_cfg,
        backend_name=backend_name,
        backend_unit=backend_unit,
        command=command,
        external_repo=_resolve(backend_cfg.get("external_repo", ""), repo_root),
        samples_dir=samples_dir,
        checkpoint=_resolve(backend_cfg.get("checkpoint_path", ""), repo_root),
        log_path=run_dir / "diffdec_single_rgroup.log",
        k=k,
    )


def build_diffdec_command(
    backend_cfg: dict[str, Any],
    *,
    repo_root: Path,
    scaffold_smiles_file: str | Path,
    protein_file: str | Path,
    scaffold_file: str | Path,
    task_name: str,
    data_dir: str | Path,
    samples_dir: str | Path,
) -> list[str]:
    checkpoint = _resolve(backend_cfg.get("checkpoint_path", ""), repo_root)
    command: list[str] = []
    conda_env = str(backend_cfg.get("conda_env") or "")
    if conda_env:
        command.extend(["conda", "run", "--no-capture-output", "-n", conda_env])
    command.extend(
        [
            str(backend_cfg.get("python_executable") or "python"),
            "sample_single_for_specific_context.py",
            "--scaffold_smiles_file",
            str(scaffold_smiles_file),
            "--protein_file",
            str(protein_file),
            "--scaffold_file",
            str(scaffold_file),
            "--task_name",
            str(task_name),
            "--data_dir",
            str(data_dir),
            "--checkpoint",
            str(checkpoint),
            "--samples_dir",
            str(samples_dir),
            "--n_samples",
            str(int(backend_cfg.get("n_samples", 8))),
            "--device",
            str(backend_cfg.get("device") or "cpu"),
        ]
    )
    return command


def write_diffdec_scaffold_inputs(
    case_input: Phase4CaseInput,
    *,
    scaffold_file: str | Path,
    scaffold_smiles_file: str | Path,
) -> dict[str, Any]:
    from rdkit import Chem

    mol = read_first_mol(case_input.failed_ligand_sdf, sanitize=False)
    keep = set(case_input.keep_atom_indices)
    editable = set(case_input.mask_atom_indices)
    if keep & editable:
        raise ValueError(f"Mask/keep overlap for {case_input.case_id}")
    if len(keep) + len(editable) != mol.GetNumAtoms():
        raise ValueError(f"Mask/keep does not cover all ligand atoms for {case_input.case_id}")
    if case_input.anchor_scaffold_atom_idx not in keep:
        raise ValueError(f"Anchor scaffold atom is not in keep atoms for {case_input.case_id}")

    old_to_new = {old_idx: new_idx for new_idx, old_idx in enumerate(sorted(keep))}
    rw_mol = Chem.RWMol(mol)
    for atom_idx in sorted(editable, reverse=True):
        rw_mol.RemoveAtom(int(atom_idx))
    fixed = rw_mol.GetMol()
    fixed.UpdatePropertyCache(strict=False)

    scaffold_path = Path(scaffold_file)
    scaffold_path.parent.mkdir(parents=True, exist_ok=True)
    writer = Chem.SDWriter(str(scaffold_path))
    writer.SetKekulize(False)
    writer.write(fixed)
    writer.close()

    dummy_rw = Chem.RWMol(fixed)
    dummy_idx = dummy_rw.AddAtom(Chem.Atom("*"))
    dummy_rw.AddBond(int(old_to_new[case_input.anchor_scaffold_atom_idx]), int(dummy_idx), Chem.BondType.SINGLE)
    dummy_mol = dummy_rw.GetMol()
    dummy_mol.UpdatePropertyCache(strict=False)
    smiles = Chem.MolToSmiles(dummy_mol, canonical=True, isomericSmiles=False)
    smiles_path = Path(scaffold_smiles_file)
    smiles_path.parent.mkdir(parents=True, exist_ok=True)
    smiles_path.write_text(smiles + "\n", encoding="utf-8")
    return {
        "scaffold_file": str(scaffold_path),
        "scaffold_smiles_file": str(smiles_path),
        "scaffold_smiles": smiles,
        "fixed_atom_count": int(fixed.GetNumAtoms()),
    }


def _run_diffdec_command(
    case_input: Phase4CaseInput,
    *,
    backend_cfg: dict[str, Any],
    backend_name: str,
    backend_unit: str,
    command: list[str],
    external_repo: Path,
    samples_dir: Path,
    checkpoint: Path,
    log_path: Path,
    k: int,
) -> list[dict[str, Any]]:
    timeout_sec = int(backend_cfg.get("timeout_sec", 300))
    start = time.perf_counter()
    env = os.environ.copy()
    for key in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]:
        env.pop(key, None)
    env["WANDB_DISABLED"] = "true"
    env["WANDB_MODE"] = "offline"
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
            _candidate_row(
                case_input,
                backend_name=backend_name,
                backend_unit=backend_unit,
                candidate_index=0,
                candidate_path="",
                proposal_count=int(backend_cfg.get("n_samples", 8)),
                candidate_count=0,
                runtime_sec=runtime_sec,
                failure_stage="execution",
                failure_reason=f"timeout_after_{timeout_sec}_sec",
            )
        ]
    if completed.returncode != 0:
        return [
            _candidate_row(
                case_input,
                backend_name=backend_name,
                backend_unit=backend_unit,
                candidate_index=0,
                candidate_path="",
                proposal_count=int(backend_cfg.get("n_samples", 8)),
                candidate_count=0,
                runtime_sec=runtime_sec,
                failure_stage="execution",
                failure_reason=f"returncode_{completed.returncode}",
            )
        ]
    return _diffdec_candidate_rows(
        case_input,
        backend_name=backend_name,
        backend_unit=backend_unit,
        samples_dir=samples_dir,
        checkpoint=checkpoint,
        proposal_count=int(backend_cfg.get("n_samples", 8)),
        runtime_sec=runtime_sec,
        k=k,
    )


def _diffdec_candidate_rows(
    case_input: Phase4CaseInput,
    *,
    backend_name: str,
    backend_unit: str,
    samples_dir: Path,
    checkpoint: Path,
    proposal_count: int,
    runtime_sec: float,
    k: int,
) -> list[dict[str, Any]]:
    experiment_name = checkpoint.name.replace(".ckpt", "")
    output_dir = samples_dir / experiment_name / "0"
    candidate_paths = sorted(output_dir.glob("*_.sdf"), key=lambda path: path.name)
    candidate_paths = [path for path in candidate_paths if path.name[0].isdigit()]
    if not candidate_paths:
        return [
            _candidate_row(
                case_input,
                backend_name=backend_name,
                backend_unit=backend_unit,
                candidate_index=0,
                candidate_path="",
                proposal_count=proposal_count,
                candidate_count=0,
                runtime_sec=runtime_sec,
                failure_stage="output_read",
                failure_reason=f"output_sdf_missing:{output_dir}",
            )
        ]
    selected = candidate_paths[: max(int(k), 0)]
    return [
        _candidate_row(
            case_input,
            backend_name=backend_name,
            backend_unit=backend_unit,
            candidate_index=index,
            candidate_path=str(path),
            proposal_count=proposal_count,
            candidate_count=len(selected),
            runtime_sec=runtime_sec,
            failure_stage="",
            failure_reason="",
        )
        for index, path in enumerate(selected, start=1)
    ]


def _candidate_row(
    case_input: Phase4CaseInput,
    *,
    backend_name: str,
    backend_unit: str,
    candidate_index: int,
    candidate_path: str,
    proposal_count: int,
    candidate_count: int,
    runtime_sec: float,
    failure_stage: str,
    failure_reason: str,
) -> dict[str, Any]:
    return {
        "backend_name": backend_name,
        "backend_unit": backend_unit,
        "case_id": case_input.case_id,
        "base_sample_id": case_input.base_sample_id,
        "attempt_id": f"{backend_name}:{case_input.case_id}",
        "candidate_id": f"{backend_name}:{case_input.case_id}:{candidate_index:03d}" if candidate_path else "",
        "candidate_index": int(candidate_index),
        "candidate_path": candidate_path,
        "candidate_source": "diffdec_single_rgroup",
        "proposal_count": int(proposal_count),
        "candidate_count": int(candidate_count),
        "runtime_sec": float(runtime_sec),
        "failure_stage": failure_stage,
        "failure_reason": failure_reason,
        "same_topology": False,
        "requires_fixed_structure_match": True,
        "uses_h_clash_in_generation": False,
        "generation_metadata": {},
    }


def _check_conda_env(conda_env: str) -> tuple[str, str]:
    if not conda_env:
        return "not_configured", ""
    command = ["conda", "run", "-n", conda_env, "python", "-c", "print('ready')"]
    try:
        completed = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=30)
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
