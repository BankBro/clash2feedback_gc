from __future__ import annotations

import copy
import hashlib
import json
import math
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import pandas as pd

from clash2feedback.repair.diffsbdd_adapter import build_diffsbdd_inventory, run_diffsbdd_conditional_case
from clash2feedback.repair.diffsbdd_anchor_filter import anchor_aware_filter_row
from clash2feedback.repair.fragment_diagnostics import analyze_candidate_fragment
from clash2feedback.repair.phase4_inputs import load_phase4_case_inputs
from clash2feedback.utils.config import load_yaml_config, resolve_repo_path
from clash2feedback.verifier.phase4_adapter import RELIABLE_REPAIR_FIELDS, evaluate_candidate_for_phase4


def run_phase4_0_1(
    config: dict[str, Any],
    *,
    repo_root: Path,
    mode: str,
    budget_k: int | None = None,
) -> dict[str, Any]:
    if mode not in {"preflight", "formal", "report-only"}:
        raise ValueError(f"Unsupported phase4.0.1 mode: {mode}")
    if mode == "report-only":
        return write_report_only(config, repo_root=repo_root)

    inputs = config.get("inputs", {})
    outputs = config.get("outputs", {})
    report_root = resolve_repo_path(outputs["report_root"], repo_root=repo_root)
    run_root = resolve_repo_path(outputs["run_root"], repo_root=repo_root)
    report_root.mkdir(parents=True, exist_ok=True)
    run_root.mkdir(parents=True, exist_ok=True)

    selected_all = pd.read_csv(resolve_repo_path(inputs["phase4_0_selected_cases"], repo_root=repo_root))
    if mode == "preflight":
        selected_cases = _select_preflight_cases(selected_all, config)
        budgets = [int(budget_k or config.get("experiment", {}).get("preflight_budget_k", 8))]
    else:
        selected_cases = selected_all.copy()
        expected = int(config.get("selection", {}).get("expected_formal_case_count", 40))
        if selected_cases.shape[0] != expected:
            raise ValueError(f"Expected {expected} formal cases, got {selected_cases.shape[0]}")
        budgets = [int(budget_k)] if budget_k is not None else [int(item) for item in config.get("experiment", {}).get("formal_budget_ks", [8, 16, 32])]

    phase4_mask_seed = resolve_repo_path(inputs["phase4_mask_seed"], repo_root=repo_root)
    phase1_config = load_yaml_config(resolve_repo_path(inputs["phase1_config"], repo_root=repo_root))
    case_inputs = load_phase4_case_inputs(
        selected_cases,
        phase2_manifest_path=resolve_repo_path(inputs["phase2_manifest"], repo_root=repo_root),
        phase2_benchmark_root=resolve_repo_path(inputs["phase2_benchmark_root"], repo_root=repo_root),
        processed_root=resolve_repo_path(inputs["processed_root"], repo_root=repo_root),
    )
    case_by_id = {case_input.case_id: case_input for case_input in case_inputs}

    before_hash = _sha256(phase4_mask_seed)
    model_inventory = build_diffsbdd_inventory(config, repo_root=repo_root)
    inventory_row = _inventory_by_model_key(model_inventory, "diffsbdd_conditional_inpainting")
    if not inventory_row:
        raise ValueError("Missing diffsbdd_conditional_inpainting inventory row")

    adapter_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    verifier_rows: list[dict[str, Any]] = []
    diagnostics_rows: list[dict[str, Any]] = []

    for current_k in budgets:
        backend_cfg = _backend_config_for_budget(config, current_k)
        current_run_root = run_root / ("preflight" if mode == "preflight" else f"k{current_k}")
        devices = _cuda_devices(backend_cfg)
        max_workers = max(1, len(devices))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for index, case_input in enumerate(case_inputs):
                device = devices[index % len(devices)]
                futures.append(
                    executor.submit(
                        _run_case_budget,
                        case_input,
                        backend_cfg=backend_cfg,
                        inventory_row=inventory_row,
                        repo_root=repo_root,
                        run_root=current_run_root,
                        budget_k=current_k,
                        mode=mode,
                        phase1_config=phase1_config,
                        diagnostics_config=config.get("diagnostics", {}),
                        cuda_visible_devices=device,
                    )
                )
            results = [future.result() for future in as_completed(futures)]
        results.sort(key=lambda item: item["selection_rank"])
        for result in results:
            adapter_rows.extend(result["adapter_rows"])
            candidate_rows.extend(result["candidate_rows"])
            verifier_rows.extend(result["verifier_rows"])
            diagnostics_rows.extend(result["diagnostics_rows"])

    after_hash = _sha256(phase4_mask_seed)
    summary = _build_summary(
        config=config,
        mode=mode,
        selected_cases=selected_cases,
        budgets=budgets,
        model_inventory=model_inventory,
        candidate_rows=candidate_rows,
        verifier_rows=verifier_rows,
        mask_seed_sha256_before=before_hash,
        mask_seed_sha256_after=after_hash,
    )
    if mode == "preflight":
        paths = _write_preflight_reports(
            report_root=report_root,
            selected_cases=selected_cases,
            model_inventory=model_inventory,
            adapter_rows=adapter_rows,
            candidate_rows=candidate_rows,
            verifier_rows=verifier_rows,
            diagnostics_rows=diagnostics_rows,
            summary=summary,
        )
    else:
        paths = _write_formal_reports(
            config=config,
            repo_root=repo_root,
            report_root=report_root,
            selected_cases=selected_cases,
            model_inventory=model_inventory,
            adapter_rows=adapter_rows,
            candidate_rows=candidate_rows,
            verifier_rows=verifier_rows,
            diagnostics_rows=diagnostics_rows,
            summary=summary,
        )
    return {"summary": summary, "report_paths": paths}


def write_report_only(config: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    report_root = resolve_repo_path(config["outputs"]["report_root"], repo_root=repo_root)
    selected_cases = pd.read_csv(report_root / "selected_cases.csv")
    candidate_rows = pd.read_csv(report_root / "diffsbdd_candidate_manifest.csv").to_dict("records")
    verifier_rows = pd.read_csv(report_root / "diffsbdd_verifier_outcome.csv").to_dict("records")
    diagnostics_rows = pd.read_csv(report_root / "diffsbdd_anchor_reconnect_audit.csv").to_dict("records")
    summary = json.loads((report_root / "phase4_0_1_summary.json").read_text(encoding="utf-8"))
    paths = _write_formal_reports(
        config=config,
        repo_root=repo_root,
        report_root=report_root,
        selected_cases=selected_cases,
        model_inventory=pd.read_csv(report_root / "model_inventory.csv").to_dict("records"),
        adapter_rows=pd.read_csv(report_root / "adapter_input_manifest.csv").to_dict("records"),
        candidate_rows=candidate_rows,
        verifier_rows=verifier_rows,
        diagnostics_rows=diagnostics_rows,
        summary=summary,
    )
    return {"summary": summary, "report_paths": paths}


def _select_preflight_cases(selected_all: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    requested = list(config.get("selection", {}).get("preflight_cases", []))
    by_case = {str(row["case_id"]): row for _, row in selected_all.iterrows()}
    rows = []
    for rank, item in enumerate(requested, start=1):
        case_id = str(item.get("case_id") or "")
        if case_id not in by_case:
            raise ValueError(f"Configured preflight case is missing from phase4.0 selected_cases: {case_id}")
        row = by_case[case_id].copy()
        row["preflight_rank"] = rank
        row["preflight_selection_reason"] = str(item.get("selection_reason") or "phase4_0_1_preflight_case")
        rows.append(row)
    result = pd.DataFrame(rows)
    if result.shape[0] != 5:
        raise ValueError(f"Expected 5 preflight cases, got {result.shape[0]}")
    return result


def _backend_config_for_budget(config: dict[str, Any], budget_k: int) -> dict[str, Any]:
    backend_cfg = copy.deepcopy(config.get("backends", {}).get("diffsbdd_conditional_inpainting", {}))
    backend_cfg["centers"] = [str(config.get("experiment", {}).get("center", "pocket"))]
    backend_cfg["n_samples"] = int(budget_k)
    return backend_cfg


def _run_case_budget(
    case_input: Any,
    *,
    backend_cfg: dict[str, Any],
    inventory_row: dict[str, Any],
    repo_root: Path,
    run_root: Path,
    budget_k: int,
    mode: str,
    phase1_config: dict[str, Any],
    diagnostics_config: dict[str, Any],
    cuda_visible_devices: str,
) -> dict[str, Any]:
    case_backend_cfg = copy.deepcopy(backend_cfg)
    case_backend_cfg["cuda_visible_devices"] = str(cuda_visible_devices)
    input_rows, rows = run_diffsbdd_conditional_case(
        case_input,
        backend_cfg=case_backend_cfg,
        inventory_row=inventory_row,
        repo_root=repo_root,
        run_root=run_root,
        k=budget_k,
    )
    for row in input_rows:
        _annotate_row(row, mode=mode, budget_k=budget_k)
        row["cuda_visible_devices"] = str(cuda_visible_devices)
    for row in rows:
        _annotate_row(row, mode=mode, budget_k=budget_k)
        row["cuda_visible_devices"] = str(cuda_visible_devices)

    verifier_rows: list[dict[str, Any]] = []
    diagnostics_rows: list[dict[str, Any]] = []
    for candidate in rows:
        outcome = evaluate_candidate_for_phase4(
            candidate,
            case_input,
            verifier_config=phase1_config,
            phase4_verifier_cfg=diagnostics_config,
        )
        _annotate_row(outcome, mode=mode, budget_k=budget_k)
        outcome["cuda_visible_devices"] = str(cuda_visible_devices)
        diagnostics = analyze_candidate_fragment(
            candidate,
            case_input,
            tolerance=float(diagnostics_config.get("fixed_structure_match_tolerance_angstrom", 0.35)),
        )
        diagnostics.update(anchor_aware_filter_row(diagnostics))
        _annotate_row(diagnostics, mode=mode, budget_k=budget_k)
        diagnostics["cuda_visible_devices"] = str(cuda_visible_devices)
        outcome.update(_diagnostic_fields_for_verifier(diagnostics))
        verifier_rows.append(outcome)
        diagnostics_rows.append(diagnostics)
    return {
        "selection_rank": int(case_input.selected_row.get("selection_rank") or case_input.selected_row.get("preflight_rank") or 0),
        "adapter_rows": input_rows,
        "candidate_rows": rows,
        "verifier_rows": verifier_rows,
        "diagnostics_rows": diagnostics_rows,
    }


def _cuda_devices(backend_cfg: dict[str, Any]) -> list[str]:
    value = backend_cfg.get("cuda_visible_devices")
    if isinstance(value, list):
        devices = [str(item) for item in value if str(item) != ""]
    elif value is None:
        devices = [""]
    else:
        devices = [str(value)]
    return devices or [""]


def _annotate_row(row: dict[str, Any], *, mode: str, budget_k: int) -> None:
    row["phase4_0_1_mode"] = mode
    row["candidate_budget_k"] = int(budget_k)
    row.setdefault("center", _extract_center(row))


def _diagnostic_fields_for_verifier(diagnostics: dict[str, Any]) -> dict[str, Any]:
    skip = {"backend_name", "case_id", "base_sample_id", "attempt_id", "candidate_id", "candidate_index", "candidate_path"}
    return {key: value for key, value in diagnostics.items() if key not in skip}


def _write_preflight_reports(
    *,
    report_root: Path,
    selected_cases: pd.DataFrame,
    model_inventory: list[dict[str, Any]],
    adapter_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    verifier_rows: list[dict[str, Any]],
    diagnostics_rows: list[dict[str, Any]],
    summary: dict[str, Any],
) -> dict[str, Path]:
    paths = {
        "preflight_cases": report_root / "preflight_cases.csv",
        "model_inventory": report_root / "model_inventory.csv",
        "adapter_input_manifest_preflight": report_root / "adapter_input_manifest_preflight.csv",
        "candidate_manifest_preflight": report_root / "diffsbdd_candidate_manifest_preflight.csv",
        "verifier_outcome_preflight": report_root / "diffsbdd_verifier_outcome_preflight.csv",
        "anchor_reconnect_audit_preflight": report_root / "diffsbdd_anchor_reconnect_audit_preflight.csv",
        "summary_preflight": report_root / "phase4_0_1_preflight_summary.json",
    }
    selected_cases.to_csv(paths["preflight_cases"], index=False)
    _frame(model_inventory).to_csv(paths["model_inventory"], index=False)
    _frame(adapter_rows).to_csv(paths["adapter_input_manifest_preflight"], index=False)
    _frame(candidate_rows).to_csv(paths["candidate_manifest_preflight"], index=False)
    _frame(verifier_rows).to_csv(paths["verifier_outcome_preflight"], index=False)
    _frame(diagnostics_rows).to_csv(paths["anchor_reconnect_audit_preflight"], index=False)
    paths["summary_preflight"].write_text(json.dumps(_jsonable(summary), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return paths


def _write_formal_reports(
    *,
    config: dict[str, Any],
    repo_root: Path,
    report_root: Path,
    selected_cases: pd.DataFrame,
    model_inventory: list[dict[str, Any]],
    adapter_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    verifier_rows: list[dict[str, Any]],
    diagnostics_rows: list[dict[str, Any]],
    summary: dict[str, Any],
) -> dict[str, Path]:
    budget_curve = _budget_curve(selected_cases, candidate_rows, verifier_rows)
    failure_funnel = _failure_funnel(selected_cases, candidate_rows, verifier_rows)
    case_summary = _case_level_summary(selected_cases, candidate_rows, verifier_rows)
    failure_cases = _failure_cases(verifier_rows)
    comparison = _comparison(config, repo_root, selected_cases, budget_curve, verifier_rows)
    completion_audit = _completion_audit_markdown(summary, budget_curve, comparison)
    expt_report = _expt_report_markdown(summary, budget_curve, failure_funnel, comparison)
    paths = {
        "selected_cases": report_root / "selected_cases.csv",
        "preflight_cases": report_root / "preflight_cases.csv",
        "model_inventory": report_root / "model_inventory.csv",
        "adapter_input_manifest": report_root / "adapter_input_manifest.csv",
        "candidate_manifest": report_root / "diffsbdd_candidate_manifest.csv",
        "verifier_outcome": report_root / "diffsbdd_verifier_outcome.csv",
        "anchor_reconnect_audit": report_root / "diffsbdd_anchor_reconnect_audit.csv",
        "summary": report_root / "phase4_0_1_summary.json",
        "budget_curve": report_root / "diffsbdd_budget_curve.csv",
        "failure_funnel": report_root / "diffsbdd_failure_funnel.csv",
        "failure_cases": report_root / "diffsbdd_failure_cases.csv",
        "case_level_summary": report_root / "diffsbdd_case_level_summary.csv",
        "comparison": report_root / "phase4_0_vs_4_0_1_comparison.csv",
        "completion_audit": report_root / "phase4_0_1_completion_audit.md",
        "expt_report": resolve_repo_path(config["outputs"]["expt_report"], repo_root=repo_root),
    }
    preflight_path = report_root / "preflight_cases.csv"
    selected_cases.to_csv(paths["selected_cases"], index=False)
    if not preflight_path.exists():
        _select_preflight_cases(selected_cases, config).to_csv(paths["preflight_cases"], index=False)
    _frame(model_inventory).to_csv(paths["model_inventory"], index=False)
    _frame(adapter_rows).to_csv(paths["adapter_input_manifest"], index=False)
    _frame(candidate_rows).to_csv(paths["candidate_manifest"], index=False)
    _frame(verifier_rows).to_csv(paths["verifier_outcome"], index=False)
    _frame(diagnostics_rows).to_csv(paths["anchor_reconnect_audit"], index=False)
    paths["summary"].write_text(json.dumps(_jsonable(summary), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    budget_curve.to_csv(paths["budget_curve"], index=False)
    failure_funnel.to_csv(paths["failure_funnel"], index=False)
    failure_cases.to_csv(paths["failure_cases"], index=False)
    case_summary.to_csv(paths["case_level_summary"], index=False)
    comparison.to_csv(paths["comparison"], index=False)
    paths["completion_audit"].write_text(completion_audit, encoding="utf-8")
    paths["expt_report"].parent.mkdir(parents=True, exist_ok=True)
    paths["expt_report"].write_text(expt_report, encoding="utf-8")
    return paths


def _build_summary(
    *,
    config: dict[str, Any],
    mode: str,
    selected_cases: pd.DataFrame,
    budgets: list[int],
    model_inventory: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    verifier_rows: list[dict[str, Any]],
    mask_seed_sha256_before: str,
    mask_seed_sha256_after: str,
) -> dict[str, Any]:
    candidate_df = pd.DataFrame(candidate_rows)
    verifier_df = pd.DataFrame(verifier_rows)
    budget_summary = []
    for budget_k in budgets:
        c = candidate_df[candidate_df.get("candidate_budget_k", pd.Series(dtype=int)).astype(str) == str(budget_k)] if not candidate_df.empty else pd.DataFrame()
        v = verifier_df[verifier_df.get("candidate_budget_k", pd.Series(dtype=int)).astype(str) == str(budget_k)] if not verifier_df.empty else pd.DataFrame()
        attempts = c.drop_duplicates(["candidate_budget_k", "attempt_id"]) if not c.empty else pd.DataFrame()
        reliable_mask = _bool_series(v, "reliable_repair_success") if not v.empty else pd.Series(dtype=bool)
        budget_summary.append(
            {
                "candidate_budget_k": int(budget_k),
                "attempt_rows": int(attempts.shape[0]),
                "proposal_count_sum": _sum_int(attempts, "proposal_count"),
                "candidate_count_sum": _sum_int(attempts, "candidate_count"),
                "reliable_candidate_success_count": int(reliable_mask.sum()) if not v.empty else 0,
                "sample_reliable_success_count": int(v.loc[reliable_mask, "case_id"].nunique()) if not v.empty and "case_id" in v else 0,
            }
        )
    return {
        "schema_version": "phase4_0_1_diffsbdd_conditional_repair_v0_1",
        "mode": mode,
        "selected_case_count": int(selected_cases.shape[0]),
        "selected_case_ids": selected_cases["case_id"].astype(str).tolist(),
        "candidate_budget_ks": budgets,
        "center": str(config.get("experiment", {}).get("center", "pocket")),
        "backend_name": "diffsbdd_conditional_inpainting",
        "training_or_finetuning_performed": False,
        "h_clash_used_in_diffsbdd_generation": False,
        "diffsbdd_original_denoising_modified": False,
        "cuda_visible_devices": str(config.get("backends", {}).get("diffsbdd_conditional_inpainting", {}).get("cuda_visible_devices", "")),
        "reliable_repair_fields": RELIABLE_REPAIR_FIELDS,
        "phase4_mask_seed_sha256_before": mask_seed_sha256_before,
        "phase4_mask_seed_sha256_after": mask_seed_sha256_after,
        "phase4_mask_seed_unchanged": mask_seed_sha256_before == mask_seed_sha256_after,
        "model_inventory": model_inventory,
        "budget_summary": budget_summary,
    }


def _budget_curve(selected_cases: pd.DataFrame, candidate_rows: list[dict[str, Any]], verifier_rows: list[dict[str, Any]]) -> pd.DataFrame:
    candidate_df = pd.DataFrame(candidate_rows)
    verifier_df = pd.DataFrame(verifier_rows)
    rows = []
    for budget_k in sorted(candidate_df["candidate_budget_k"].dropna().astype(int).unique().tolist()) if not candidate_df.empty else []:
        c = candidate_df[candidate_df["candidate_budget_k"].astype(int) == budget_k].copy()
        v = verifier_df[verifier_df["candidate_budget_k"].astype(int) == budget_k].copy() if not verifier_df.empty else pd.DataFrame()
        attempts = c.drop_duplicates(["candidate_budget_k", "attempt_id"])
        candidate_count_sum = _sum_int(attempts, "candidate_count")
        proposal_count_sum = _sum_int(attempts, "proposal_count")
        reliable_mask = _bool_series(v, "reliable_repair_success") if not v.empty else pd.Series(dtype=bool)
        sample_success = int(v.loc[reliable_mask, "case_id"].nunique()) if not v.empty else 0
        rows.append(
            {
                "candidate_budget_k": budget_k,
                "selected_case_denominator": int(selected_cases.shape[0]),
                "attempt_rows": int(attempts.shape[0]),
                "proposal_count_sum": proposal_count_sum,
                "candidate_count_sum": candidate_count_sum,
                "execution_failure_count": int((_str_series(attempts, "failure_stage") == "execution").sum()) if not attempts.empty else 0,
                "candidate_readable_count": int(_bool_series(v, "candidate_readable").sum()) if not v.empty else 0,
                "fixed_structure_match_success_count": int(_bool_series(v, "fixed_structure_match_success").sum()) if not v.empty else 0,
                "anchor_integrity_success_count": int(_bool_series(v, "anchor_integrity").sum()) if not v.empty else 0,
                "local_reconnect_pass_count": int(_bool_series(v, "local_reconnect_pass").sum()) if not v.empty else 0,
                "old_clash_resolved_count": int(_bool_series(v, "old_clash_resolved").sum()) if not v.empty else 0,
                "no_new_severe_clash_count": int(_bool_series(v, "no_new_severe_clash").sum()) if not v.empty else 0,
                "reliable_candidate_success_count": int(reliable_mask.sum()) if not v.empty else 0,
                "sample_reliable_success_count": sample_success,
                "sample_reliable_repair_yield": _rate(sample_success, int(selected_cases.shape[0])),
                "reliable_candidate_rate": _rate(int(reliable_mask.sum()) if not v.empty else 0, candidate_count_sum),
                "anchor_integrity_rate": _rate(int(_bool_series(v, "anchor_integrity").sum()) if not v.empty else 0, candidate_count_sum),
                "local_reconnect_pass_rate": _rate(int(_bool_series(v, "local_reconnect_pass").sum()) if not v.empty else 0, candidate_count_sum),
                "old_clash_resolved_rate": _rate(int(_bool_series(v, "old_clash_resolved").sum()) if not v.empty else 0, candidate_count_sum),
                "no_new_severe_clash_rate": _rate(int(_bool_series(v, "no_new_severe_clash").sum()) if not v.empty else 0, candidate_count_sum),
                "runtime_sec_sum": float(pd.to_numeric(attempts.get("runtime_sec", pd.Series(dtype=float)), errors="coerce").fillna(0.0).sum()) if not attempts.empty else 0.0,
                "cost_per_reliable_case": _mean(proposal_count_sum, sample_success),
            }
        )
    return pd.DataFrame(rows)


def _failure_funnel(selected_cases: pd.DataFrame, candidate_rows: list[dict[str, Any]], verifier_rows: list[dict[str, Any]]) -> pd.DataFrame:
    candidate_df = pd.DataFrame(candidate_rows)
    verifier_df = pd.DataFrame(verifier_rows)
    rows = []
    if candidate_df.empty:
        return pd.DataFrame()
    for budget_k in sorted(candidate_df["candidate_budget_k"].dropna().astype(int).unique().tolist()):
        c = candidate_df[candidate_df["candidate_budget_k"].astype(int) == budget_k].copy()
        v = verifier_df[verifier_df["candidate_budget_k"].astype(int) == budget_k].copy() if not verifier_df.empty else pd.DataFrame()
        attempts = c.drop_duplicates(["candidate_budget_k", "attempt_id"])
        candidate_denominator = _sum_int(attempts, "candidate_count")
        steps = [
            ("attempted_cases", int(selected_cases.shape[0]), int(selected_cases.shape[0])),
            ("execution_success", int((pd.to_numeric(attempts.get("candidate_count", pd.Series(dtype=int)), errors="coerce").fillna(0).astype(int) > 0).sum()), int(selected_cases.shape[0])),
            ("generated_candidates", candidate_denominator, candidate_denominator),
            ("candidate_readable", int(_bool_series(v, "candidate_readable").sum()) if not v.empty else 0, candidate_denominator),
            ("ligand_valid", int(_bool_series(v, "ligand_valid").sum()) if not v.empty else 0, candidate_denominator),
            ("fixed_structure_match_success", int(_bool_series(v, "fixed_structure_match_success").sum()) if not v.empty else 0, candidate_denominator),
            ("anchor_match_success", int(_bool_series(v, "anchor_match_success").sum()) if not v.empty else 0, candidate_denominator),
            ("local_reconnect_pass", int(_bool_series(v, "local_reconnect_pass").sum()) if not v.empty else 0, candidate_denominator),
            ("anchor_integrity", int(_bool_series(v, "anchor_integrity").sum()) if not v.empty else 0, candidate_denominator),
            ("old_clash_resolved", int(_bool_series(v, "old_clash_resolved").sum()) if not v.empty else 0, candidate_denominator),
            ("no_new_severe_clash", int(_bool_series(v, "no_new_severe_clash").sum()) if not v.empty else 0, candidate_denominator),
            ("scaffold_stable", int(_bool_series(v, "scaffold_stable").sum()) if not v.empty else 0, candidate_denominator),
            ("keep_region_stable", int(_bool_series(v, "keep_region_stable").sum()) if not v.empty else 0, candidate_denominator),
            ("edit_compliance", int(_bool_series(v, "edit_compliance").sum()) if not v.empty else 0, candidate_denominator),
            ("pocket_retention", int(_bool_series(v, "pocket_retention").sum()) if not v.empty else 0, candidate_denominator),
            ("reliable_repair_success", int(_bool_series(v, "reliable_repair_success").sum()) if not v.empty else 0, candidate_denominator),
        ]
        for step, count, denominator in steps:
            rows.append(
                {
                    "candidate_budget_k": budget_k,
                    "funnel_step": step,
                    "count": count,
                    "denominator": denominator,
                    "rate": _rate(count, denominator),
                }
            )
    return pd.DataFrame(rows)


def _case_level_summary(selected_cases: pd.DataFrame, candidate_rows: list[dict[str, Any]], verifier_rows: list[dict[str, Any]]) -> pd.DataFrame:
    candidate_df = pd.DataFrame(candidate_rows)
    verifier_df = pd.DataFrame(verifier_rows)
    rows = []
    if candidate_df.empty:
        return pd.DataFrame()
    budgets = sorted(candidate_df["candidate_budget_k"].dropna().astype(int).unique().tolist())
    for budget_k in budgets:
        c_budget = candidate_df[candidate_df["candidate_budget_k"].astype(int) == budget_k]
        v_budget = verifier_df[verifier_df["candidate_budget_k"].astype(int) == budget_k] if not verifier_df.empty else pd.DataFrame()
        for _, selected in selected_cases.iterrows():
            case_id = str(selected["case_id"])
            c = c_budget[c_budget["case_id"].astype(str) == case_id]
            v = v_budget[v_budget["case_id"].astype(str) == case_id] if not v_budget.empty else pd.DataFrame()
            reliable = _bool_series(v, "reliable_repair_success") if not v.empty else pd.Series(dtype=bool)
            rows.append(
                {
                    "candidate_budget_k": budget_k,
                    "case_id": case_id,
                    "base_sample_id": selected.get("base_sample_id", ""),
                    "candidate_count": _sum_int(c.drop_duplicates(["candidate_budget_k", "attempt_id"]), "candidate_count"),
                    "reliable_candidate_count": int(reliable.sum()) if not v.empty else 0,
                    "sample_reliable_success": bool(reliable.any()) if not v.empty else False,
                    "anchor_integrity_count": int(_bool_series(v, "anchor_integrity").sum()) if not v.empty else 0,
                    "local_reconnect_pass_count": int(_bool_series(v, "local_reconnect_pass").sum()) if not v.empty else 0,
                    "old_clash_resolved_count": int(_bool_series(v, "old_clash_resolved").sum()) if not v.empty else 0,
                    "no_new_severe_clash_count": int(_bool_series(v, "no_new_severe_clash").sum()) if not v.empty else 0,
                    "top_failure_reason": _top_reason(v.get("failure_reason", pd.Series(dtype=str)).fillna("").tolist()) if not v.empty else "",
                }
            )
    return pd.DataFrame(rows)


def _failure_cases(verifier_rows: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(verifier_rows)
    if df.empty:
        return df
    return df.loc[~_bool_series(df, "reliable_repair_success")].copy()


def _comparison(
    config: dict[str, Any],
    repo_root: Path,
    selected_cases: pd.DataFrame,
    budget_curve: pd.DataFrame,
    verifier_rows: list[dict[str, Any]],
) -> pd.DataFrame:
    inputs = config.get("inputs", {})
    rates = pd.read_csv(resolve_repo_path(inputs["phase4_0_backend_comparison_rates"], repo_root=repo_root))
    comparison = pd.read_csv(resolve_repo_path(inputs["phase4_0_backend_comparison"], repo_root=repo_root))
    center = pd.read_csv(resolve_repo_path(inputs["phase4_0_center_sensitivity"], repo_root=repo_root))
    old_verifier = pd.read_csv(resolve_repo_path(inputs["phase4_0_verifier_outcome"], repo_root=repo_root))
    cond_rates = rates[rates["backend_name"] == "diffsbdd_conditional_inpainting"].iloc[0]
    cond_cmp = comparison[comparison["backend_name"] == "diffsbdd_conditional_inpainting"].iloc[0]
    old_cond = old_verifier[old_verifier["backend_name"] == "diffsbdd_conditional_inpainting"]
    pocket = center[center["center"] == "pocket"].iloc[0]
    rows = []
    metrics = [
        "sample_reliable_success_count",
        "sample_reliable_repair_yield",
        "reliable_candidate_success_count",
        "reliable_candidate_rate",
        "anchor_integrity_rate",
        "local_reconnect_pass_rate",
        "old_clash_resolved_rate",
        "no_new_severe_clash_rate",
        "cost_per_reliable_case",
        "runtime_sec_sum",
    ]
    old_overall = {
        "sample_reliable_success_count": float(cond_cmp["sample_reliable_success_count"]),
        "sample_reliable_repair_yield": float(cond_rates["sample_reliable_repair_yield"]),
        "reliable_candidate_success_count": float(cond_cmp["reliable_candidate_success_count"]),
        "reliable_candidate_rate": float(cond_rates["reliable_candidate_rate"]),
        "anchor_integrity_rate": float(cond_rates["anchor_integrity_rate"]),
        "local_reconnect_pass_rate": math.nan,
        "old_clash_resolved_rate": _rate(int(_bool_series(old_cond, "old_clash_resolved").sum()), int(cond_cmp["candidate_count_sum"])),
        "no_new_severe_clash_rate": _rate(int(_bool_series(old_cond, "no_new_severe_clash").sum()), int(cond_cmp["candidate_count_sum"])),
        "cost_per_reliable_case": _float_or_nan(cond_rates["cost_per_reliable_case"]),
        "runtime_sec_sum": math.nan,
    }
    old_pocket_candidate_count = int(pocket["candidate_count"])
    old_pocket = {
        "sample_reliable_success_count": float(pocket["sample_reliable_success_count"]),
        "sample_reliable_repair_yield": _rate(int(pocket["sample_reliable_success_count"]), int(selected_cases.shape[0])),
        "reliable_candidate_success_count": float(pocket["reliable_candidate_success_count"]),
        "reliable_candidate_rate": _rate(int(pocket["reliable_candidate_success_count"]), old_pocket_candidate_count),
        "anchor_integrity_rate": _rate(int(pocket["anchor_integrity_success_count"]), old_pocket_candidate_count),
        "local_reconnect_pass_rate": math.nan,
        "old_clash_resolved_rate": _rate(int(pocket["old_clash_resolved_count"]), old_pocket_candidate_count),
        "no_new_severe_clash_rate": _rate(int(pocket["no_new_severe_clash_count"]), old_pocket_candidate_count),
        "cost_per_reliable_case": math.nan,
        "runtime_sec_sum": math.nan,
    }
    by_budget = {int(row["candidate_budget_k"]): row for _, row in budget_curve.iterrows()}
    for metric in metrics:
        output = {
            "metric": metric,
            "phase4_0_diffsbdd_conditional_overall": old_overall.get(metric, math.nan),
            "phase4_0_diffsbdd_conditional_center_pocket": old_pocket.get(metric, math.nan),
        }
        for budget_k in [8, 16, 32]:
            value = by_budget.get(budget_k, {}).get(metric, math.nan)
            output[f"phase4_0_1_k{budget_k}"] = value
            output[f"delta_k{budget_k}_vs_phase4_0_overall"] = _delta(value, old_overall.get(metric, math.nan))
            output[f"delta_k{budget_k}_vs_phase4_0_pocket"] = _delta(value, old_pocket.get(metric, math.nan))
        rows.append(output)
    return pd.DataFrame(rows)


def _completion_audit_markdown(summary: dict[str, Any], budget_curve: pd.DataFrame, comparison: pd.DataFrame) -> str:
    lines = [
        "# Phase 4.0.1 DiffSBDD Conditional Repair Completion Audit",
        "",
        "## 1. Scope",
        "",
        "- 本阶段只运行 `diffsbdd_conditional_inpainting`.",
        f"- center: `{summary.get('center')}`.",
        f"- selected cases: {summary.get('selected_case_count')}.",
        f"- candidate budgets: {summary.get('candidate_budget_ks')}.",
        "- no training or finetuning was performed.",
        "- DiffSBDD original denoising loop was not modified.",
        "- `H_clash` was not passed into DiffSBDD generation.",
        f"- phase4_mask_seed unchanged: {summary.get('phase4_mask_seed_unchanged')}.",
        "",
        "## 2. Budget Curve",
        "",
        _markdown_table(budget_curve),
        "",
        "## 3. Guardrails",
        "",
        "- reliable repair candidate 继续沿用阶段 4.0 的 10 项标准.",
        "- anchor-aware filtering 和 local reconnect check 是新增诊断/筛选, 不替代 reliable repair 标准.",
        "- 阶段 4.0 历史结果未作为写入目标.",
    ]
    return "\n".join(lines) + "\n"


def _expt_report_markdown(
    summary: dict[str, Any],
    budget_curve: pd.DataFrame,
    failure_funnel: pd.DataFrame,
    comparison: pd.DataFrame,
) -> str:
    lines = [
        "# 阶段 4.0.1 DiffSBDD conditional repair 临时实验汇报",
        "",
        "## 1. 实验边界",
        "",
        "- 本文件是临时实验汇报, 不是正式 final report.",
        "- 本阶段只做 DiffSBDD conditional inpainting 修补.",
        f"- 样本数: {summary.get('selected_case_count')}, 复用阶段 4.0 selected cases.",
        f"- 主设置: center=`{summary.get('center')}`.",
        f"- K 预算: {summary.get('candidate_budget_ks')}.",
        "- 未训练或微调 DiffSBDD, 未修改 DiffSBDD 原始去噪过程, 未声称 `H_clash` 进入生成过程.",
        "- reliable repair candidate 继续沿用阶段 4.0 的 10 项标准.",
        "",
        "## 2. 预算曲线",
        "",
        _markdown_table(budget_curve),
        "",
        "## 3. Failure Funnel",
        "",
        _markdown_table(failure_funnel),
        "",
        "## 4. 阶段 4.0 对比",
        "",
        _markdown_table(comparison),
        "",
        "## 5. 验证状态",
        "",
        "- compileall / pytest / 禁止修改范围核查由 Codex 在完成阶段审计时补充.",
    ]
    return "\n".join(lines) + "\n"


def _frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame([{key: _cell(value) for key, value in row.items()} for row in rows])


def _cell(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple, set)):
        return json.dumps(_jsonable(value), ensure_ascii=False, sort_keys=True)
    return value


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inventory_by_model_key(rows: list[dict[str, Any]], model_key: str) -> dict[str, Any]:
    for row in rows:
        if row.get("model_key") == model_key:
            return row
    return {}


def _sum_int(df: pd.DataFrame, column: str) -> int:
    if df.empty or column not in df:
        return 0
    return int(pd.to_numeric(df[column], errors="coerce").fillna(0).astype(int).sum())


def _bool_series(df: pd.DataFrame, column: str) -> pd.Series:
    if df.empty or column not in df:
        return pd.Series([False] * len(df), index=df.index, dtype=bool)
    return df[column].map(_as_bool).fillna(False).astype(bool)


def _str_series(df: pd.DataFrame, column: str) -> pd.Series:
    if df.empty or column not in df:
        return pd.Series([""] * len(df), index=df.index, dtype=str)
    return df[column].fillna("").astype(str)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not pd.isna(value):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _rate(numerator: int, denominator: int) -> float:
    return float(numerator / denominator) if denominator else float("nan")


def _mean(total: int, denominator: int) -> float:
    return float(total / denominator) if denominator else float("nan")


def _delta(value: Any, baseline: Any) -> float:
    value_float = _float_or_nan(value)
    baseline_float = _float_or_nan(baseline)
    if math.isnan(value_float) or math.isnan(baseline_float):
        return float("nan")
    return value_float - baseline_float


def _float_or_nan(value: Any) -> float:
    try:
        if pd.isna(value) or str(value) == "NA":
            return float("nan")
        return float(value)
    except Exception:
        return float("nan")


def _top_reason(values: list[Any]) -> str:
    cleaned = [str(value) for value in values if str(value).strip()]
    if not cleaned:
        return ""
    return Counter(cleaned).most_common(1)[0][0]


def _extract_center(row: dict[str, Any]) -> str:
    if row.get("center"):
        return str(row["center"])
    metadata = row.get("generation_metadata")
    if isinstance(metadata, str) and metadata:
        try:
            parsed = json.loads(metadata)
            if parsed.get("center"):
                return str(parsed["center"])
        except Exception:
            pass
    for key in ["candidate_source", "attempt_id"]:
        value = str(row.get(key) or "")
        if "pocket" in value:
            return "pocket"
        if "ligand" in value:
            return "ligand"
    return ""


def _markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "NA"
    display = df.copy()
    for column in display.columns:
        display[column] = display[column].map(_markdown_cell)
    columns = list(display.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in display.iterrows():
        lines.append("| " + " | ".join(str(row[column]) for column in columns) + " |")
    return "\n".join(lines)


def _markdown_cell(value: Any) -> str:
    if isinstance(value, float):
        if math.isnan(value):
            return "NA"
        return f"{value:.6f}"
    return str(value)


def guard_status(config: dict[str, Any], *, repo_root: Path) -> str:
    paths = [str(path) for path in config.get("guards", {}).get("forbidden_diff_paths", [])]
    command = ["git", "status", "--porcelain=v1", "--", *paths]
    completed = subprocess.run(command, cwd=str(repo_root), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    return completed.stdout.strip()
