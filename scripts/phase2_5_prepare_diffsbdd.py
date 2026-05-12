#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from clash2feedback.generation_audit.diffsbdd_runner import md5_file, sha256_file
from clash2feedback.utils.config import load_yaml_config, resolve_repo_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare the external DiffSBDD frozen-inference baseline for phase 2.5.")
    parser.add_argument("--config", default="configs/phase2_5_model_induced_audit.yaml")
    parser.add_argument("--report-root", default=None)
    parser.add_argument("--run-root", default=None)
    parser.add_argument("--skip-env-create", action="store_true")
    parser.add_argument("--skip-smoke-test", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = resolve_repo_path(args.config, repo_root=REPO_ROOT)
    config = load_yaml_config(config_path)
    baseline = config.get("baseline", {})
    outputs = config.get("outputs", {})
    report_root = resolve_repo_path(args.report_root or outputs.get("report_root", "reports/phase2_5_model_induced_audit"), repo_root=REPO_ROOT)
    run_root = resolve_repo_path(args.run_root or outputs.get("run_root", "runs/phase2_5_model_induced_audit"), repo_root=REPO_ROOT)
    log_root = run_root / "logs"
    report_root.mkdir(parents=True, exist_ok=True)
    log_root.mkdir(parents=True, exist_ok=True)
    log_path = log_root / "phase2_5_prepare_diffsbdd.log"

    external_repo = resolve_repo_path(baseline.get("external_repo", "external/DiffSBDD"), repo_root=REPO_ROOT)
    checkpoint_path = resolve_repo_path(baseline.get("checkpoint_path", "external/DiffSBDD/checkpoints/crossdocked_fullatom_cond.ckpt"), repo_root=REPO_ROOT)
    repo_url = str(baseline.get("external_repo_url", "https://github.com/arneschneuing/DiffSBDD.git"))
    repo_commit = str(baseline.get("external_repo_commit", ""))
    checkpoint_url = str(baseline.get("checkpoint_url", ""))
    conda_env = str(baseline.get("conda_env", "diffsbdd"))

    commands: list[dict[str, Any]] = []
    blocked_reasons: list[str] = []

    if external_repo.exists():
        commands.append({"command": ["git", "clone", repo_url, str(external_repo)], "status": "skipped_existing_repo"})
    else:
        external_repo.parent.mkdir(parents=True, exist_ok=True)
        commands.append(_run(["git", "clone", repo_url, str(external_repo)], log_path=log_path))
    if repo_commit and external_repo.exists():
        commands.append(_run(["git", "-C", str(external_repo), "checkout", repo_commit], log_path=log_path))

    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    if checkpoint_path.exists() and checkpoint_path.stat().st_size > 0:
        commands.append({"command": ["wget", "-O", str(checkpoint_path), checkpoint_url], "status": "skipped_existing_checkpoint"})
    elif checkpoint_url:
        wget_result = _run(["wget", "-O", str(checkpoint_path), checkpoint_url], log_path=log_path)
        commands.append(wget_result)
        if wget_result["returncode"] != 0:
            commands.append(_run(["curl", "-L", "-o", str(checkpoint_path), checkpoint_url], log_path=log_path))
    else:
        blocked_reasons.append("checkpoint_url_missing")

    env_existed_before = _conda_env_exists(conda_env)
    if not env_existed_before and not args.skip_env_create:
        env_yaml = external_repo / "environment.yaml"
        if env_yaml.exists():
            commands.append(_run(["conda", "env", "create", "-f", str(env_yaml), "-n", conda_env], log_path=log_path))
        else:
            blocked_reasons.append(f"diffsbdd_environment_yaml_missing:{env_yaml}")
    elif not env_existed_before and args.skip_env_create:
        blocked_reasons.append(f"diffsbdd_env_missing:{conda_env}")

    env_check = _run(
        [
            "conda",
            "run",
            "-n",
            conda_env,
            "python",
            "-c",
            (
                "import importlib, torch\n"
                "mods=['rdkit','pytorch_lightning','openbabel','torch_scatter']\n"
                "for name in mods:\n"
                "    importlib.import_module(name)\n"
                "print('cuda_available=' + str(torch.cuda.is_available()))\n"
                "print('torch=' + str(torch.__version__))\n"
            ),
        ],
        log_path=log_path,
    )
    commands.append(env_check)
    if env_check["returncode"] != 0 and "pkg_resources" in str(env_check.get("output_tail", "")):
        commands.append(_run(["conda", "install", "-n", conda_env, "-y", "-c", "conda-forge", "setuptools<81"], log_path=log_path))
        env_check = _run(
            [
                "conda",
                "run",
                "-n",
                conda_env,
                "python",
                "-c",
                (
                    "import importlib, torch\n"
                    "mods=['rdkit','pytorch_lightning','openbabel','torch_scatter']\n"
                    "for name in mods:\n"
                    "    importlib.import_module(name)\n"
                    "print('cuda_available=' + str(torch.cuda.is_available()))\n"
                    "print('torch=' + str(torch.__version__))\n"
                ),
            ],
            log_path=log_path,
        )
        commands.append(env_check)
    env_ready = env_check["returncode"] == 0
    cuda_available = "cuda_available=True" in str(env_check.get("output_tail", ""))
    if not env_ready:
        blocked_reasons.append(f"diffsbdd_env_check_failed:{conda_env}")
    elif not cuda_available:
        blocked_reasons.append(f"diffsbdd_cuda_unavailable:{conda_env}")

    smoke_test: dict[str, Any] = {"status": "skipped"}
    if env_ready and cuda_available and not args.skip_smoke_test and external_repo.exists() and checkpoint_path.exists():
        smoke_out = run_root / "diffsbdd_smoke_3rfm.sdf"
        smoke_test = _run(
            [
                "conda",
                "run",
                "--no-capture-output",
                "-n",
                conda_env,
                "python",
                "generate_ligands.py",
                str(checkpoint_path),
                "--pdbfile",
                "example/3rfm.pdb",
                "--outfile",
                str(smoke_out),
                "--ref_ligand",
                "example/3rfm_B_CFF.sdf",
                "--n_samples",
                "1",
            ],
            cwd=external_repo,
            log_path=log_path,
        )
        smoke_test["output_path"] = str(smoke_out)
        commands.append(smoke_test)
        if smoke_test["returncode"] != 0:
            blocked_reasons.append(f"diffsbdd_smoke_test_failed:{log_path}")

    repo_actual_commit = _git_stdout(["git", "-C", str(external_repo), "rev-parse", "HEAD"]) if external_repo.exists() else ""
    if repo_commit and repo_actual_commit and repo_actual_commit != repo_commit:
        blocked_reasons.append(f"diffsbdd_repo_commit_mismatch:{repo_actual_commit}!={repo_commit}")
    if not checkpoint_path.exists():
        blocked_reasons.append(f"checkpoint_missing:{checkpoint_path}")

    gpu_info = _command_stdout(["nvidia-smi", "--query-gpu=index,name,driver_version,memory.total,memory.free", "--format=csv,noheader"])
    official_split_search = _search_split_candidates(external_repo)
    setup = {
        "schema_version": "phase2_5_external_setup_v0_1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": str(config_path.relative_to(REPO_ROOT)),
        "external_repo_path": str(external_repo),
        "external_repo_url": repo_url,
        "external_repo_commit": repo_actual_commit,
        "expected_external_repo_commit": repo_commit,
        "checkpoint_name": str(baseline.get("checkpoint_name", "")),
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_url": checkpoint_url,
        "checkpoint_md5": md5_file(checkpoint_path) if checkpoint_path.exists() else "",
        "checkpoint_sha256": sha256_file(checkpoint_path) if checkpoint_path.exists() else "",
        "checkpoint_file_size": int(checkpoint_path.stat().st_size) if checkpoint_path.exists() else 0,
        "conda_env": conda_env,
        "env_existed_before": env_existed_before,
        "env_check_status": "ready" if env_ready else "failed",
        "cuda_available": cuda_available,
        "gpu_info": gpu_info,
        "official_split_search": official_split_search,
        "smoke_test": smoke_test,
        "commands": commands,
        "blocked_reasons": blocked_reasons,
        "log_path": str(log_path),
    }
    output_path = resolve_repo_path(baseline.get("external_setup_report", report_root / "external_setup.json"), repo_root=REPO_ROOT)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(setup, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"phase2_5_prepare_diffsbdd complete: env_ready={env_ready} cuda={cuda_available} blocked={len(blocked_reasons)}")
    print(f"external_setup_report={output_path}")
    return 0 if not blocked_reasons else 1


def _run(command: list[str], *, log_path: Path, cwd: Path | None = None) -> dict[str, Any]:
    with log_path.open("a", encoding="utf-8") as log:
        log.write("\n$ " + " ".join(command) + "\n")
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd else str(REPO_ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        log.write(result.stdout)
    return {
        "command": command,
        "cwd": str(cwd or REPO_ROOT),
        "returncode": int(result.returncode),
        "status": "ok" if result.returncode == 0 else "failed",
        "output_tail": result.stdout[-4000:],
    }


def _conda_env_exists(env_name: str) -> bool:
    result = subprocess.run(["conda", "env", "list", "--json"], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if result.returncode != 0:
        return False
    data = json.loads(result.stdout)
    return any(Path(path).name == env_name for path in data.get("envs", []))


def _git_stdout(command: list[str]) -> str:
    result = subprocess.run(command, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def _command_stdout(command: list[str]) -> str:
    result = subprocess.run(command, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    return result.stdout.strip()


def _search_split_candidates(external_repo: Path) -> list[str]:
    roots = [external_repo, REPO_ROOT / "data" / "splits", REPO_ROOT / "data" / "cache" / "crossdocked_downloads"]
    matches: list[str] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if len(matches) >= 100:
                return matches
            if not path.is_file():
                continue
            name = path.name.lower()
            if "split" in name or name in {"train.txt", "val.txt", "test.txt"} or name.endswith(("_train.txt", "_val.txt", "_test.txt")):
                matches.append(str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path))
    return matches


if __name__ == "__main__":
    raise SystemExit(main())
