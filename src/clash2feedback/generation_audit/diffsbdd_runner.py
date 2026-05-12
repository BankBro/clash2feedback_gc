from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DiffSBDDAvailability:
    ready: bool
    blocked_reasons: list[str]
    checkpoint_md5: str
    checkpoint_sha256: str
    checkpoint_file_size: int
    external_repo_commit: str
    expected_repo_commit: str
    conda_env: str
    env_check_status: str
    env_check_output: str
    cuda_available: bool


def check_diffsbdd_availability(baseline_cfg: dict[str, Any], *, repo_root: Path) -> DiffSBDDAvailability:
    checkpoint_path = _resolve(baseline_cfg.get("checkpoint_path", ""), repo_root)
    external_repo = _resolve(baseline_cfg.get("external_repo", "external/DiffSBDD"), repo_root)
    expected_repo_commit = str(baseline_cfg.get("external_repo_commit") or "")
    conda_env = str(baseline_cfg.get("conda_env") or "")
    reasons: list[str] = []
    external_repo_commit = ""
    if not external_repo.exists():
        reasons.append(f"diffsbdd_repo_missing:{external_repo}")
    elif not (external_repo / "generate_ligands.py").exists():
        reasons.append(f"diffsbdd_generate_ligands_missing:{external_repo / 'generate_ligands.py'}")
    else:
        external_repo_commit = _git_commit(external_repo)
        if expected_repo_commit and external_repo_commit and external_repo_commit != expected_repo_commit:
            reasons.append(f"diffsbdd_repo_commit_mismatch:{external_repo_commit}!={expected_repo_commit}")
    if not checkpoint_path.exists():
        reasons.append(f"checkpoint_missing:{checkpoint_path}")
    checkpoint_md5 = md5_file(checkpoint_path) if checkpoint_path.exists() else ""
    checkpoint_sha256 = sha256_file(checkpoint_path) if checkpoint_path.exists() else ""
    checkpoint_file_size = int(checkpoint_path.stat().st_size) if checkpoint_path.exists() else 0
    env_check_status, env_check_output, cuda_available = _check_python_environment(conda_env)
    if conda_env and env_check_status != "ready":
        reasons.append(f"diffsbdd_env_not_ready:{conda_env}:{env_check_status}")
    if conda_env and env_check_status == "ready" and not cuda_available:
        reasons.append(f"diffsbdd_cuda_unavailable:{conda_env}")
    return DiffSBDDAvailability(
        ready=not reasons,
        blocked_reasons=reasons,
        checkpoint_md5=checkpoint_md5,
        checkpoint_sha256=checkpoint_sha256,
        checkpoint_file_size=checkpoint_file_size,
        external_repo_commit=external_repo_commit,
        expected_repo_commit=expected_repo_commit,
        conda_env=conda_env,
        env_check_status=env_check_status,
        env_check_output=env_check_output,
        cuda_available=cuda_available,
    )


def build_generation_command(
    *,
    baseline_cfg: dict[str, Any],
    protein_path: str | Path,
    reference_ligand_path: str | Path,
    output_path: str | Path,
    repo_root: Path,
) -> list[str]:
    checkpoint_path = _resolve(baseline_cfg.get("checkpoint_path", ""), repo_root)
    python_executable = str(baseline_cfg.get("python_executable") or "python")
    command = []
    conda_env = str(baseline_cfg.get("conda_env") or "")
    if conda_env:
        command.extend(["conda", "run", "--no-capture-output", "-n", conda_env])
    command.extend(
        [
        python_executable,
        "generate_ligands.py",
        str(checkpoint_path),
        "--pdbfile",
        str(protein_path),
        "--outfile",
        str(output_path),
        "--ref_ligand",
        str(reference_ligand_path),
        "--n_samples",
        str(int(baseline_cfg.get("n_samples_per_pocket", 20))),
        ]
    )
    if bool(baseline_cfg.get("sanitize", False)):
        command.append("--sanitize")
    if bool(baseline_cfg.get("relax", False)):
        command.append("--relax")
    return command


def run_generation_command(
    command: list[str],
    *,
    external_repo: str | Path,
    log_path: str | Path,
    cuda_device: int,
) -> dict[str, Any]:
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(cuda_device)
    log = Path(log_path)
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as f:
        f.write("$ " + " ".join(command) + "\n")
        result = subprocess.run(
            command,
            cwd=str(external_repo),
            env=env,
            text=True,
            stdout=f,
            stderr=subprocess.STDOUT,
            check=False,
        )
    return {
        "returncode": int(result.returncode),
        "generation_status": "generated" if result.returncode == 0 else "generation_failed",
        "log_path": str(log),
    }


def checkpoint_metadata(baseline_cfg: dict[str, Any], availability: DiffSBDDAvailability) -> dict[str, Any]:
    return {
        "model_name": str(baseline_cfg.get("model_name", "DiffSBDD")),
        "checkpoint_name": str(baseline_cfg.get("checkpoint_name", "")),
        "checkpoint_path": str(baseline_cfg.get("checkpoint_path", "")),
        "checkpoint_md5": availability.checkpoint_md5,
        "checkpoint_sha256": availability.checkpoint_sha256,
        "checkpoint_file_size": int(availability.checkpoint_file_size),
    }


def availability_metadata(availability: DiffSBDDAvailability) -> dict[str, Any]:
    return {
        "external_repo_commit": availability.external_repo_commit,
        "expected_repo_commit": availability.expected_repo_commit,
        "conda_env": availability.conda_env,
        "env_check_status": availability.env_check_status,
        "env_check_output": availability.env_check_output,
        "cuda_available": availability.cuda_available,
        "checkpoint_md5": availability.checkpoint_md5,
        "checkpoint_sha256": availability.checkpoint_sha256,
        "checkpoint_file_size": availability.checkpoint_file_size,
    }


def command_json(command: list[str]) -> str:
    return json.dumps(command, ensure_ascii=False)


def md5_file(path: str | Path) -> str:
    return _digest(path, "md5")


def sha256_file(path: str | Path) -> str:
    return _digest(path, "sha256")


def _digest(path: str | Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve(path_value: Any, repo_root: Path) -> Path:
    path = Path(str(path_value))
    return path if path.is_absolute() else (repo_root / path).resolve()


def _git_commit(repo: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _check_python_environment(conda_env: str) -> tuple[str, str, bool]:
    if not conda_env:
        return "not_configured", "", False
    code = (
        "import importlib, torch\n"
        "mods=['rdkit','pytorch_lightning','openbabel','torch_scatter']\n"
        "for name in mods:\n"
        "    importlib.import_module(name)\n"
        "print('cuda_available=' + str(torch.cuda.is_available()))\n"
        "print('torch=' + str(torch.__version__))\n"
    )
    try:
        result = subprocess.run(
            ["conda", "run", "-n", conda_env, "python", "-c", code],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=90,
        )
    except subprocess.TimeoutExpired as exc:
        return "timeout", str(exc), False
    output = result.stdout.strip()
    if result.returncode != 0:
        return "failed", output, False
    return "ready", output, "cuda_available=True" in output
