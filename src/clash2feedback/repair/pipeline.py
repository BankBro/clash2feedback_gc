from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from clash2feedback.repair.case_selection import load_mask_seed, select_formal_cases, select_preflight_cases
from clash2feedback.repair.diffdec_adapter import build_diffdec_inventory, run_diffdec_case
from clash2feedback.repair.diffsbdd_adapter import (
    blocked_candidate_rows_for_backend,
    build_diffsbdd_inventory,
    run_diffsbdd_conditional_case,
    run_diffsbdd_full_resampling_case,
)
from clash2feedback.repair.phase4_inputs import adapter_input_row, load_phase4_case_inputs
from clash2feedback.repair.reporting import build_summary, write_phase4_reports
from clash2feedback.repair.rule_backend import run_rule_backend
from clash2feedback.utils.config import load_yaml_config, resolve_repo_path
from clash2feedback.verifier.phase4_adapter import evaluate_candidate_for_phase4


def run_phase4_0_preflight(config: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    return run_phase4_0(config, repo_root=repo_root, mode="preflight")


def run_phase4_0_formal(config: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    return run_phase4_0(config, repo_root=repo_root, mode="formal")


def run_phase4_0(config: dict[str, Any], *, repo_root: Path, mode: str) -> dict[str, Any]:
    if mode not in {"preflight", "formal"}:
        raise ValueError(f"Unsupported phase4.0 mode: {mode}")
    inputs = config.get("inputs", {})
    outputs = config.get("outputs", {})
    phase4_mask_seed = resolve_repo_path(inputs["phase4_mask_seed"], repo_root=repo_root)
    phase2_manifest = resolve_repo_path(inputs["phase2_manifest"], repo_root=repo_root)
    phase2_benchmark_root = resolve_repo_path(inputs["phase2_benchmark_root"], repo_root=repo_root)
    processed_root = resolve_repo_path(inputs["processed_root"], repo_root=repo_root)
    phase1_config_path = resolve_repo_path(inputs["phase1_config"], repo_root=repo_root)
    report_root = resolve_repo_path(outputs["report_root"], repo_root=repo_root)
    run_root = resolve_repo_path(outputs["run_root"], repo_root=repo_root)
    report_root.mkdir(parents=True, exist_ok=True)
    run_root.mkdir(parents=True, exist_ok=True)

    before_hash = _sha256(phase4_mask_seed)
    phase1_config = load_yaml_config(phase1_config_path)
    mask_seed = load_mask_seed(phase4_mask_seed)
    selected_cases = select_preflight_cases(mask_seed, config) if mode == "preflight" else select_formal_cases(mask_seed, config)
    case_inputs = load_phase4_case_inputs(
        selected_cases,
        phase2_manifest_path=phase2_manifest,
        phase2_benchmark_root=phase2_benchmark_root,
        processed_root=processed_root,
    )

    model_inventory = []
    model_inventory.append(_rule_inventory(config))
    model_inventory.extend(build_diffsbdd_inventory(config, repo_root=repo_root))
    model_inventory.extend(build_diffdec_inventory(config, repo_root=repo_root))

    adapter_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    k = int(config.get("candidate_budget", {}).get("k", 8))

    rule_cfg = config.get("backends", {}).get("rule_fixed_topology", {})
    if bool(rule_cfg.get("enabled", True)):
        for case_input in case_inputs:
            input_row, rows = run_rule_backend(
                case_input,
                backend_cfg=rule_cfg,
                verifier_config=phase1_config,
                run_root=run_root,
                k=k,
            )
            adapter_rows.append(input_row)
            candidate_rows.extend(rows)

    diffsbdd_cfg = config.get("backends", {}).get("diffsbdd_conditional_inpainting", {})
    diffsbdd_inventory = _inventory_by_model_key(model_inventory, "diffsbdd_conditional_inpainting")
    if bool(diffsbdd_cfg.get("enabled", False)):
        for case_input in case_inputs:
            input_rows, rows = run_diffsbdd_conditional_case(
                case_input,
                backend_cfg=diffsbdd_cfg,
                inventory_row=diffsbdd_inventory,
                repo_root=repo_root,
                run_root=run_root,
                k=k,
            )
            adapter_rows.extend(input_rows)
            candidate_rows.extend(rows)

    full_cfg = config.get("backends", {}).get("diffsbdd_full_resampling", {})
    full_inventory = _inventory_by_model_key(model_inventory, "diffsbdd_full_resampling")
    if mode == "formal" and bool(full_cfg.get("enabled", False)):
        for case_input in case_inputs:
            input_rows, rows = run_diffsbdd_full_resampling_case(
                case_input,
                backend_cfg=full_cfg,
                inventory_row=full_inventory,
                repo_root=repo_root,
                run_root=run_root,
                k=k,
            )
            adapter_rows.extend(input_rows)
            candidate_rows.extend(rows)

    diffdec_cfg = config.get("backends", {}).get("diffdec_single_rgroup", {})
    diffdec_inventory = _inventory_by_model_key(model_inventory, "diffdec_single_rgroup")
    if mode == "formal" and bool(diffdec_cfg.get("enabled", False)):
        for case_input in case_inputs:
            input_rows, rows = run_diffdec_case(
                case_input,
                backend_cfg=diffdec_cfg,
                inventory_row=diffdec_inventory,
                repo_root=repo_root,
                run_root=run_root,
                k=k,
            )
            adapter_rows.extend(input_rows)
            candidate_rows.extend(rows)

    for blocked_key in ["diffsbdd_joint_inpainting", "diffdec_single_rgroup"]:
        row = _inventory_by_model_key(model_inventory, blocked_key)
        if row and row.get("status") == "blocked" and not (mode == "formal" and blocked_key == "diffdec_single_rgroup" and bool(diffdec_cfg.get("enabled", False))):
            candidate_rows.extend(blocked_candidate_rows_for_backend(case_inputs, inventory_row=row))
            for case_input in case_inputs:
                adapter_rows.append(
                    adapter_input_row(
                        case_input,
                        backend_name=str(row.get("backend_name") or blocked_key),
                        backend_unit=str(row.get("backend_unit") or ""),
                        status="blocked",
                        blocked_reason=str(row.get("blocked_reason") or ""),
                        uses_h_clash_in_generation=False,
                    )
                )

    case_by_id = {case_input.case_id: case_input for case_input in case_inputs}
    verifier_rows = [
        evaluate_candidate_for_phase4(
            candidate,
            case_by_id[str(candidate["case_id"])],
            verifier_config=phase1_config,
            phase4_verifier_cfg=config.get("verifier", {}),
        )
        for candidate in candidate_rows
    ]

    after_hash = _sha256(phase4_mask_seed)
    summary = build_summary(
        selected_cases=selected_cases,
        model_inventory=model_inventory,
        candidate_manifest=candidate_rows,
        verifier_outcome=verifier_rows,
        mask_seed_sha256_before=before_hash,
        mask_seed_sha256_after=after_hash,
        mode=mode,
        expected_case_count=int(config.get("selection", {}).get("preflight_count" if mode == "preflight" else "small_scale_count", selected_cases.shape[0])),
    )
    paths = write_phase4_reports(
        report_root=report_root,
        selected_cases=selected_cases,
        model_inventory=model_inventory,
        adapter_input_manifest=adapter_rows,
        candidate_manifest=candidate_rows,
        verifier_outcome=verifier_rows,
        summary=summary,
        mode=mode,
    )
    return {"summary": summary, "summary_path": paths["summary"], "report_paths": paths}


def _rule_inventory(config: dict[str, Any]) -> dict[str, Any]:
    backend_cfg = config.get("backends", {}).get("rule_fixed_topology", {})
    return {
        "model_key": "rule_fixed_topology",
        "backend_name": str(backend_cfg.get("backend_name") or "rule_fixed_topology"),
        "backend_unit": str(backend_cfg.get("backend_unit") or "fixed_topology_local_conformer_repair"),
        "external_repo": "",
        "repo_commit": "",
        "expected_repo_commit": "",
        "checkpoint_path": "",
        "checkpoint_exists": False,
        "checkpoint_md5": "",
        "checkpoint_sha256": "",
        "checkpoint_file_size": 0,
        "conda_env": "",
        "env_status": "not_required",
        "env_check_output": "",
        "status": "ready",
        "blocked_reason": "",
        "uses_h_clash_in_generation": False,
    }


def _inventory_by_model_key(rows: list[dict[str, Any]], model_key: str) -> dict[str, Any]:
    for row in rows:
        if row.get("model_key") == model_key:
            return row
    return {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
