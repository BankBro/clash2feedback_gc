#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import pickle
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from clash2feedback.chemistry.rgroup import build_ligand_masks, decompose_rgroups
from clash2feedback.chemistry.scaffold import get_murcko_scaffold_atom_indices
from clash2feedback.generation_audit.diffsbdd_runner import (
    availability_metadata,
    build_generation_command,
    check_diffsbdd_availability,
    checkpoint_metadata,
    command_json,
    run_generation_command,
)
from clash2feedback.generation_audit.gap_analysis import artificial_vs_model_induced_gap
from clash2feedback.generation_audit.ligand_validity import LIGAND_VALIDITY_COLUMNS, evaluate_generated_ligand
from clash2feedback.generation_audit.overlap import build_training_overlap_audit, summarize_overlap
from clash2feedback.generation_audit.read_generated import read_generated_sdf, standardize_generated_mol, write_sdf
from clash2feedback.generation_audit.reports import (
    BASE_SELECTION_COLUMNS,
    FAILURE_TAXONOMY_COLUMNS,
    GENERATION_MANIFEST_COLUMNS,
    MODEL_CLASH_COLUMNS,
    REPAIRABILITY_PROXY_COLUMNS,
    VISUAL_QC_COLUMNS,
    build_summary,
    empty_dataframe,
    select_base_pockets,
    write_completion_audit,
    write_phase2_5_audit,
    write_visual_qc_notes,
)
from clash2feedback.generation_audit.taxonomy import classify_failure_taxonomy, classify_repairability_proxy
from clash2feedback.geometry.clash import detect_clashes
from clash2feedback.geometry.rgroup_attribution import attribute_clashes_to_rgroups
from clash2feedback.io.read_ligand import mol_to_ligand_data
from clash2feedback.utils.config import load_yaml_config, resolve_repo_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run phase 2.5 model-induced failure audit.")
    parser.add_argument("--config", default="configs/phase2_5_model_induced_audit.yaml")
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--phase1-report-root", default=None)
    parser.add_argument("--phase2-benchmark-root", default=None)
    parser.add_argument("--run-root", default=None)
    parser.add_argument("--report-root", default=None)
    parser.add_argument("--compileall-result", default="not_recorded_yet")
    parser.add_argument("--pytest-result", default="not_recorded_yet")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = resolve_repo_path(args.config, repo_root=REPO_ROOT)
    config = load_yaml_config(config_path)
    inputs = config.get("inputs", {})
    outputs = config.get("outputs", {})
    manifest_path = resolve_repo_path(args.manifest or inputs.get("manifest", "data/processed/v0_1/manifest.parquet"), repo_root=REPO_ROOT)
    processed_root = resolve_repo_path(inputs.get("processed_root", "data/processed/v0_1"), repo_root=REPO_ROOT)
    splits_root = resolve_repo_path(inputs.get("splits_root", "data/splits/v0_1"), repo_root=REPO_ROOT)
    phase2_root = resolve_repo_path(
        args.phase2_benchmark_root or inputs.get("phase2_benchmark_root", "data/benchmarks/clashrepairbench_rg_artificial/v0_1"),
        repo_root=REPO_ROOT,
    )
    run_root = resolve_repo_path(args.run_root or outputs.get("run_root", "runs/phase2_5_model_induced_audit"), repo_root=REPO_ROOT)
    report_root = resolve_repo_path(args.report_root or outputs.get("report_root", "reports/phase2_5_model_induced_audit"), repo_root=REPO_ROOT)
    raw_root = run_root / "raw_candidates"
    std_root = run_root / "standardized_candidates"
    log_root = run_root / "logs"
    for path in (report_root, raw_root, std_root, log_root):
        path.mkdir(parents=True, exist_ok=True)

    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}", file=sys.stderr)
        return 2
    manifest = pd.read_parquet(manifest_path)
    split_files = {
        key: str(resolve_repo_path(value, repo_root=REPO_ROOT))
        for key, value in (config.get("overlap", {}).get("official_split_files", {}) or {}).items()
        if value
    }
    overlap_df = build_training_overlap_audit(
        manifest,
        processed_root=processed_root,
        splits_root=splits_root,
        official_split_files=split_files,
    )
    overlap_df.to_csv(report_root / "training_overlap_audit.csv", index=False)
    overlap_summary = summarize_overlap(overlap_df)
    with (report_root / "training_overlap_summary.json").open("w", encoding="utf-8") as f:
        json.dump(overlap_summary, f, ensure_ascii=False, indent=2)

    phase2_base_report = _read_csv_if_exists(report_root.parent / "phase2_injection" / "base_clean_filter_report.csv")
    if phase2_base_report.empty:
        phase2_base_report = _read_csv_if_exists(Path("reports/phase2_injection/base_clean_filter_report.csv"))
    selection_cfg = config.get("selection", {})
    base_selection = select_base_pockets(
        overlap_df,
        manifest,
        max_pockets=int(selection_cfg.get("max_pockets_v0", 10)),
        preferred_splits=list(selection_cfg.get("preferred_base_splits", ["val", "test"])),
        preferred_tiers=list(selection_cfg.get("preferred_overlap_tiers", ["T3_official_diffsbdd_test", "T4_external_unseen", "T_unknown"])),
        phase2_base_report=phase2_base_report,
    )
    base_selection.to_csv(report_root / "base_pocket_selection.csv", index=False)

    availability = check_diffsbdd_availability(config.get("baseline", {}), repo_root=REPO_ROOT)
    blocked_reasons = list(availability.blocked_reasons)
    if not overlap_summary.get("official_split_available", False):
        blocked_reasons.append("official_diffsbdd_or_pocket2mol_split_unavailable")
    baseline_cfg = config.get("baseline", {})
    external_setup_path = resolve_repo_path(
        baseline_cfg.get("external_setup_report", "reports/phase2_5_model_induced_audit/external_setup.json"),
        repo_root=REPO_ROOT,
    )
    external_setup = _read_json_if_exists(external_setup_path)
    checkpoint_meta = {
        **checkpoint_metadata(baseline_cfg, availability),
        **availability_metadata(availability),
    }

    outputs_df = _run_or_block_generation(
        config,
        manifest,
        base_selection,
        availability_ready=availability.ready,
        blocked_reasons=blocked_reasons,
        processed_root=processed_root,
        raw_root=raw_root,
        std_root=std_root,
        log_root=log_root,
    )
    generation_manifest = outputs_df["generation_manifest"]
    ligand_validity = outputs_df["ligand_validity"]
    clash_report = outputs_df["clash_report"]
    failure_taxonomy = outputs_df["failure_taxonomy"]
    repairability_proxy = outputs_df["repairability_proxy"]

    generation_manifest.to_parquet(report_root / "generation_manifest.parquet", index=False)
    ligand_validity.to_csv(report_root / "ligand_validity.csv", index=False)
    clash_report.to_csv(report_root / "model_induced_clash_report.csv", index=False)
    failure_taxonomy.to_csv(report_root / "failure_taxonomy.csv", index=False)
    repairability_proxy.to_csv(report_root / "repairability_proxy.csv", index=False)

    phase2_manifest = pd.read_parquet(phase2_root / "manifest.parquet") if (phase2_root / "manifest.parquet").exists() else pd.DataFrame()
    gap_df = artificial_vs_model_induced_gap(phase2_manifest, clash_report, failure_taxonomy, repairability_proxy)
    gap_df.to_csv(report_root / "artificial_vs_model_induced_gap.csv", index=False)
    visual_qc = _visual_qc_cases(generation_manifest, failure_taxonomy, repairability_proxy)
    visual_qc.to_csv(report_root / "visual_qc_cases.csv", index=False)
    write_visual_qc_notes(report_root / "visual_qc_notes.md", visual_qc, blocked_reasons)

    summary = build_summary(
        config=config,
        overlap_summary=overlap_summary,
        base_selection=base_selection,
        generation_manifest=generation_manifest,
        ligand_validity=ligand_validity,
        failure_taxonomy=failure_taxonomy,
        repairability_proxy=repairability_proxy,
        blocked_reasons=blocked_reasons,
        checkpoint_meta=checkpoint_meta,
        external_setup=external_setup,
    )
    with (report_root / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    write_phase2_5_audit(report_root / "phase2_5_audit.md", summary, blocked_reasons)
    commands = [
        f"conda run -n c2f_cpu python scripts/phase2_5_prepare_diffsbdd.py --config {args.config} --report-root {report_root.relative_to(REPO_ROOT)} --run-root {run_root.relative_to(REPO_ROOT)}",
        f"conda run -n c2f_cpu python scripts/phase2_5_training_overlap_audit.py --config {args.config} --manifest {manifest_path.relative_to(REPO_ROOT)} --output-root {report_root.relative_to(REPO_ROOT)}",
        f"conda run -n c2f_cpu python scripts/phase2_5_model_induced_audit.py --config {args.config} --manifest {manifest_path.relative_to(REPO_ROOT)} --phase1-report-root {args.phase1_report_root or inputs.get('phase1_report_root', 'reports/phase1_clash_detector')} --phase2-benchmark-root {phase2_root.relative_to(REPO_ROOT)} --run-root {run_root.relative_to(REPO_ROOT)} --report-root {report_root.relative_to(REPO_ROOT)}",
        "conda run -n c2f_cpu python -m compileall src scripts",
        "conda run -n c2f_cpu python -m pytest",
    ]
    checklist = _completion_checklist(report_root, summary, blocked_reasons)
    write_completion_audit(
        report_root / "phase2_5_completion_audit.md",
        checklist=checklist,
        commands=commands,
        summary=summary,
        blocked_reasons=blocked_reasons,
        compileall_result=args.compileall_result,
        pytest_result=args.pytest_result,
        file_status_lines=_git_status_lines(),
    )
    print(
        "phase2_5_model_induced_audit complete: "
        f"selected={summary['num_base_pockets_selected']} generated={summary['num_generated_total']} blocked={len(blocked_reasons)}"
    )
    return 0


def _run_or_block_generation(
    config: dict[str, Any],
    manifest: pd.DataFrame,
    base_selection: pd.DataFrame,
    *,
    availability_ready: bool,
    blocked_reasons: list[str],
    processed_root: Path,
    raw_root: Path,
    std_root: Path,
    log_root: Path,
) -> dict[str, pd.DataFrame]:
    if not availability_ready or not bool(config.get("baseline", {}).get("run_generation_when_available", True)):
        return {
            "generation_manifest": empty_dataframe(GENERATION_MANIFEST_COLUMNS),
            "ligand_validity": empty_dataframe(LIGAND_VALIDITY_COLUMNS),
            "clash_report": empty_dataframe(MODEL_CLASH_COLUMNS),
            "failure_taxonomy": empty_dataframe(FAILURE_TAXONOMY_COLUMNS),
            "repairability_proxy": empty_dataframe(REPAIRABILITY_PROXY_COLUMNS),
        }
    baseline_cfg = config.get("baseline", {})
    availability = check_diffsbdd_availability(baseline_cfg, repo_root=REPO_ROOT)
    checkpoint_meta = checkpoint_metadata(baseline_cfg, availability)
    manifest_by_id = manifest.set_index("sample_id", drop=False)
    generation_rows: list[dict[str, Any]] = []
    validity_rows: list[dict[str, Any]] = []
    clash_rows: list[dict[str, Any]] = []
    taxonomy_rows: list[dict[str, Any]] = []
    proxy_rows: list[dict[str, Any]] = []
    selected = base_selection[base_selection["selected_for_generation"] == True]  # noqa: E712
    for pocket_idx, (_, selection_row) in enumerate(selected.iterrows()):
        sample_id = str(selection_row["base_sample_id"])
        if sample_id not in manifest_by_id.index:
            blocked_reasons.append(f"selected_sample_missing_from_manifest:{sample_id}")
            continue
        manifest_row = manifest_by_id.loc[sample_id].to_dict()
        sample = _load_sample(manifest_row, processed_root)
        raw_protein = sample.get("paths", {}).get("raw_protein_path", "")
        raw_ligand = sample.get("paths", {}).get("raw_ligand_path", "")
        raw_output = raw_root / f"{sample_id}_raw.sdf"
        std_output = std_root / f"{sample_id}_standardized.sdf"
        command = build_generation_command(
            baseline_cfg=baseline_cfg,
            protein_path=raw_protein,
            reference_ligand_path=raw_ligand,
            output_path=raw_output,
            repo_root=REPO_ROOT,
        )
        cuda_device = pocket_idx % max(int(baseline_cfg.get("num_gpus", 1)), 1)
        run_result = run_generation_command(
            command,
            external_repo=resolve_repo_path(baseline_cfg.get("external_repo", "external/DiffSBDD"), repo_root=REPO_ROOT),
            log_path=log_root / f"{sample_id}.log",
            cuda_device=cuda_device,
        )
        if run_result["generation_status"] != "generated":
            blocked_reasons.append(f"generation_failed:{sample_id}:{run_result['log_path']}")
            continue
        raw_mols = read_generated_sdf(raw_output)
        standardized_mols = []
        standardized_status: list[str] = []
        for mol in raw_mols:
            standardized, status = standardize_generated_mol(mol, largest_fragment=True, sanitize=False)
            standardized_mols.append(standardized)
            standardized_status.append(status)
        write_sdf([mol for mol in standardized_mols if mol is not None], std_output)
        for mol_idx, raw_mol in enumerate(raw_mols, start=1):
            candidate_id = f"{sample_id}__cand_{mol_idx:04d}"
            for stage, mol, post_status in [
                ("raw_generated", raw_mol, "raw"),
                ("standardized_generated", standardized_mols[mol_idx - 1], standardized_status[mol_idx - 1]),
            ]:
                result = _audit_candidate(
                    candidate_id,
                    stage,
                    mol,
                    sample,
                    selection_row.to_dict(),
                    config,
                    postprocess_status=post_status,
                )
                validity_rows.append(result["validity"])
                if result["clash"] is not None:
                    clash_rows.append(result["clash"])
                taxonomy_rows.append(result["taxonomy"])
                proxy_rows.append(result["proxy"])
                generation_rows.append(
                    {
                        "candidate_id": candidate_id,
                        "base_sample_id": sample_id,
                        "base_complex_id": selection_row.get("base_complex_id", ""),
                        "base_split": selection_row.get("base_split", ""),
                        "target_id": selection_row.get("target_id", ""),
                        "split_group": selection_row.get("split_group", ""),
                        "overlap_tier": selection_row.get("overlap_tier", ""),
                        "external_validity_eligible": bool(selection_row.get("external_validity_eligible", False)),
                        **checkpoint_meta,
                        "seed": int(config.get("seed", 20260511)),
                        "n_samples": int(baseline_cfg.get("n_samples_per_pocket", 20)),
                        "cuda_device": cuda_device,
                        "generation_command": command_json(command),
                        "inference_config_json": json.dumps(baseline_cfg, ensure_ascii=False, sort_keys=True),
                        "raw_output_path": str(raw_output),
                        "standardized_output_path": str(std_output),
                        "generation_status": run_result["generation_status"],
                        "postprocess_stage": stage,
                        "postprocess_status": post_status,
                        "sanitize_flag": bool(baseline_cfg.get("sanitize", False)),
                        "relax_flag": bool(baseline_cfg.get("relax", False)),
                        "readable": bool(result["validity"]["rdkit_readable"]),
                        "ligand_valid": result["validity"]["ligand_validity_status"] == "valid",
                        "failure_taxonomy": result["taxonomy"]["failure_taxonomy"],
                        "repairability_proxy": result["proxy"]["repairability_proxy"],
                    }
                )
    return {
        "generation_manifest": pd.DataFrame(generation_rows, columns=GENERATION_MANIFEST_COLUMNS),
        "ligand_validity": pd.DataFrame(validity_rows, columns=LIGAND_VALIDITY_COLUMNS),
        "clash_report": pd.DataFrame(clash_rows, columns=MODEL_CLASH_COLUMNS),
        "failure_taxonomy": pd.DataFrame(taxonomy_rows, columns=FAILURE_TAXONOMY_COLUMNS),
        "repairability_proxy": pd.DataFrame(proxy_rows, columns=REPAIRABILITY_PROXY_COLUMNS),
    }


def _audit_candidate(
    candidate_id: str,
    stage: str,
    mol: Any | None,
    base_sample: dict[str, Any],
    selection_row: dict[str, Any],
    config: dict[str, Any],
    *,
    postprocess_status: str,
) -> dict[str, Any]:
    validity = evaluate_generated_ligand(
        candidate_id,
        mol,
        postprocess_stage=stage,
        config=config.get("ligand_validity", {}),
        largest_fragment_selected=stage == "standardized_generated",
        readable=mol is not None,
    )
    detector_cfg = config.get("detector", {})
    ligand_valid = validity["ligand_validity_status"] == "valid"
    generated_sample = _generated_sample(base_sample, mol, candidate_id) if mol is not None else None
    rgroup_attributable = bool(generated_sample and generated_sample.get("scaffold", {}).get("success") and generated_sample.get("rgroups"))
    clash_row = None
    attr: dict[str, Any] = {}
    if ligand_valid and generated_sample is not None:
        default_delta = float(detector_cfg.get("default_delta_angstrom", 0.4))
        severe = float(detector_cfg.get("severe_depth_threshold_angstrom", 0.4))
        report = detect_clashes(
            generated_sample,
            receptor_scope=str(detector_cfg.get("receptor_scope", "pocket10_all_atoms")),
            delta_angstrom=default_delta,
            severe_depth_threshold_angstrom=severe,
        )
        if rgroup_attributable:
            attr = attribute_clashes_to_rgroups(
                generated_sample,
                report,
                alpha=float(detector_cfg.get("rgroup_score_alpha", 0.5)),
                single_region_threshold=float(detector_cfg.get("single_region_dominant_ratio", 0.7)),
                ambiguous_threshold=float(detector_cfg.get("ambiguous_region_dominant_ratio", 0.5)),
            )
        sensitivity = _delta_sensitivity(generated_sample, detector_cfg)
        clash_row = {
            "candidate_id": candidate_id,
            "base_sample_id": selection_row.get("base_sample_id", ""),
            "postprocess_stage": stage,
            "receptor_scope": report.get("receptor_scope", ""),
            "delta_angstrom": default_delta,
            "num_clash_pairs": int(report.get("num_clash_pairs") or 0),
            "num_severe_clash_pairs": int(report.get("num_severe_clash_pairs") or 0),
            "total_clash_score": float(report.get("total_clash_score") or 0.0),
            "max_clash_depth": float(report.get("max_clash_depth") or 0.0),
            "mean_clash_depth": float(report.get("mean_clash_depth") or 0.0),
            "delta03_status": sensitivity.get("0.3", ""),
            "delta04_status": sensitivity.get("0.4", ""),
            "delta05_status": sensitivity.get("0.5", ""),
        }
    taxonomy = classify_failure_taxonomy(
        candidate_id=candidate_id,
        postprocess_stage=stage,
        generation_status="generated",
        postprocess_status=postprocess_status,
        ligand_valid=ligand_valid,
        ligand_validity_reason=str(validity.get("ligand_validity_reason") or ""),
        num_clash_pairs=int(clash_row.get("num_clash_pairs") if clash_row else 0),
        num_severe_clash_pairs=int(clash_row.get("num_severe_clash_pairs") if clash_row else 0),
        max_clash_depth=float(clash_row.get("max_clash_depth") if clash_row else 0.0),
        rgroup_attributable=rgroup_attributable,
        attribution_failure_type=str(attr.get("failure_type") or ""),
        dominant_valid_rgroup=str(attr.get("dominant_valid_rgroup") or ""),
        dominant_ratio_valid=float(attr.get("dominant_ratio_valid_rgroups") or 0.0),
        dominant_ratio_all=float(attr.get("dominant_ratio_all_regions") or 0.0),
        scaffold_score=float(attr.get("scaffold_score") or 0.0),
        unsupported_reasons=[],
        global_pose_max_depth_angstrom=float(detector_cfg.get("global_pose_max_depth_angstrom", 1.5)),
        global_pose_severe_pair_count=int(detector_cfg.get("global_pose_severe_pair_count", 20)),
    )
    proxy = classify_repairability_proxy(
        taxonomy,
        max_clash_depth=float(clash_row.get("max_clash_depth") if clash_row else 0.0),
        scaffold_score=float(attr.get("scaffold_score") or 0.0),
        local_max_depth=float(detector_cfg.get("global_pose_max_depth_angstrom", 1.5)),
    )
    return {"validity": validity, "clash": clash_row, "taxonomy": taxonomy, "proxy": proxy}


def _generated_sample(base_sample: dict[str, Any], mol: Any, candidate_id: str) -> dict[str, Any]:
    ligand = mol_to_ligand_data(mol, keep_molblock=True)
    scaffold = get_murcko_scaffold_atom_indices(mol)
    rgroups = decompose_rgroups(mol, scaffold)
    masks = build_ligand_masks(mol, scaffold, rgroups) if scaffold.success else {}
    sample = dict(base_sample)
    sample["sample_id"] = candidate_id
    sample["ligand"] = ligand.to_dict()
    sample["scaffold"] = scaffold.to_dict()
    sample["rgroups"] = [rgroup.to_dict() for rgroup in rgroups]
    sample["masks"] = masks
    return sample


def _delta_sensitivity(sample: dict[str, Any], detector_cfg: dict[str, Any]) -> dict[str, str]:
    severe = float(detector_cfg.get("severe_depth_threshold_angstrom", 0.4))
    result: dict[str, str] = {}
    for delta in detector_cfg.get("delta_sensitivity", [0.3, 0.4, 0.5]):
        report = detect_clashes(
            sample,
            receptor_scope=str(detector_cfg.get("receptor_scope", "pocket10_all_atoms")),
            delta_angstrom=float(delta),
            severe_depth_threshold_angstrom=severe,
        )
        result[f"{float(delta):.1f}"] = "severe" if int(report.get("num_severe_clash_pairs") or 0) > 0 else "no_severe"
    return result


def _load_sample(row: dict[str, Any], processed_root: Path) -> dict[str, Any]:
    value = row.get("processed_path")
    path = Path(str(value)) if value not in (None, "") and Path(str(value)).exists() else processed_root / "complexes" / f"{row.get('sample_id')}.pkl"
    with path.open("rb") as f:
        return pickle.load(f)


def _read_csv_if_exists(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _git_status_lines() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        return [f"git_status_failed: {result.stdout.strip()}"]
    return [line for line in result.stdout.splitlines() if line.strip()]


def _visual_qc_cases(generation_manifest: pd.DataFrame, failure_taxonomy: pd.DataFrame, repairability_proxy: pd.DataFrame) -> pd.DataFrame:
    if generation_manifest.empty:
        return empty_dataframe(VISUAL_QC_COLUMNS)
    derived_columns = [column for column in ["failure_taxonomy", "repairability_proxy"] if column in generation_manifest.columns]
    merged = generation_manifest.drop(columns=derived_columns).merge(failure_taxonomy, on=["candidate_id", "postprocess_stage"], how="left")
    merged = merged.merge(repairability_proxy, on=["candidate_id", "postprocess_stage"], how="left")
    parts = []
    for taxonomy in ["valid_no_severe_clash", "ligand_only_invalid", "postprocess_failed", "single_rgroup_clash", "global_pose_failure", "scaffold_clash", "rgroup_unattributable"]:
        part = merged[merged["failure_taxonomy"] == taxonomy].head(5)
        if not part.empty:
            parts.append(part)
    result = pd.concat(parts, ignore_index=True) if parts else merged.head(0)
    if result.empty:
        return empty_dataframe(VISUAL_QC_COLUMNS)
    result = result[["candidate_id", "postprocess_stage", "failure_taxonomy", "repairability_proxy", "raw_output_path", "standardized_output_path"]].copy()
    result["visual_qc_status"] = "pending_manual_review"
    result["notes"] = "auto-selected for phase2.5 visual QC"
    return result[VISUAL_QC_COLUMNS]


def _completion_checklist(report_root: Path, summary: dict[str, Any], blocked_reasons: list[str]) -> list[tuple[str, str, str]]:
    required = [
        "summary.json",
        "training_overlap_audit.csv",
        "training_overlap_summary.json",
        "base_pocket_selection.csv",
        "generation_manifest.parquet",
        "ligand_validity.csv",
        "model_induced_clash_report.csv",
        "failure_taxonomy.csv",
        "repairability_proxy.csv",
        "artificial_vs_model_induced_gap.csv",
        "visual_qc_cases.csv",
        "visual_qc_notes.md",
        "phase2_5_audit.md",
    ]
    checklist = [(f"report exists: {name}", "done" if (report_root / name).exists() else "missing", "") for name in required]
    repo_reasons = [reason for reason in blocked_reasons if reason.startswith(("diffsbdd_repo_", "checkpoint_"))]
    env_reasons = [reason for reason in blocked_reasons if reason.startswith(("diffsbdd_env_", "diffsbdd_cuda_"))]
    generation_reasons = [reason for reason in blocked_reasons if reason.startswith("generation_failed:")]
    split_reasons = [reason for reason in blocked_reasons if "official_diffsbdd_or_pocket2mol_split_unavailable" in reason]
    generated = int(summary.get("num_generated_total", 0) or 0)
    generation_status = "done" if generated > 0 else ("blocked" if repo_reasons or env_reasons or generation_reasons else "missing")
    checklist.extend(
        [
            ("training-overlap audit first", "done", "training_overlap_audit.csv is written before generation audit"),
            ("all generated samples recorded", "done", "generation_manifest is schema-valid and includes raw/standardized stages when generation succeeds"),
            ("DiffSBDD assets", "blocked" if repo_reasons else "done", "; ".join(repo_reasons)),
            ("DiffSBDD environment and GPU", "blocked" if env_reasons else "done", "; ".join(env_reasons)),
            ("DiffSBDD generation", generation_status, "; ".join(generation_reasons) if generation_reasons else f"unique_candidates={generated}"),
            ("official split provenance", "blocked" if split_reasons else "done", "; ".join(split_reasons)),
            ("no train/repair/tune/ranking", "done", "constraints are enforced by config and wrapper scope"),
            ("predicted dominant not oracle", "done", "taxonomy rows set predicted_dominant_is_oracle_ground_truth=false"),
            ("phase2_v0_1 unchanged", "done", "phase2 benchmark is read-only input"),
        ]
    )
    return checklist


if __name__ == "__main__":
    raise SystemExit(main())
