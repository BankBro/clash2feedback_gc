from __future__ import annotations

import hashlib
import json
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from clash2feedback.generation_audit import EXTERNAL_ELIGIBLE_TIERS


OVERLAP_COLUMNS = [
    "base_sample_id",
    "base_complex_id",
    "base_split",
    "target_id",
    "split_group",
    "source_dataset",
    "raw_protein_path",
    "raw_ligand_path",
    "original_protein_path",
    "original_pocket10_path",
    "original_ligand_path",
    "protein_sha256",
    "ligand_sha256",
    "canonical_smiles",
    "inchi_key",
    "crossdocked_pair_name",
    "diffsbdd_split_status",
    "exact_pair_overlap",
    "protein_file_overlap",
    "ligand_file_overlap",
    "same_target_overlap",
    "same_pocket_overlap",
    "ligand_exact_overlap",
    "ligand_similarity_max",
    "sequence_identity_to_train_max",
    "overlap_tier",
    "external_validity_eligible",
    "audit_decision",
    "audit_notes",
]


@dataclass(frozen=True)
class OfficialSplitNames:
    train: set[str]
    val: set[str]
    test: set[str]

    @property
    def available(self) -> bool:
        return bool(self.train or self.val or self.test)


def build_training_overlap_audit(
    manifest: pd.DataFrame,
    *,
    processed_root: Path,
    splits_root: Path,
    official_split_files: dict[str, str | Path] | None = None,
) -> pd.DataFrame:
    split_map = load_project_split_map(splits_root)
    official = load_official_split_names(official_split_files or {})
    train_targets = _target_set(official.train)
    rows: list[dict[str, Any]] = []
    for _, manifest_row in manifest.iterrows():
        row = manifest_row.to_dict()
        sample = load_processed_sample(row, processed_root)
        metadata = sample.get("metadata", {})
        paths = sample.get("paths", {})
        ligand = sample.get("ligand", {})
        sample_id = str(sample.get("sample_id") or row.get("sample_id") or "")
        original_ligand_path = str(metadata.get("original_ligand_path") or "")
        original_pocket10_path = str(metadata.get("original_pocket10_path") or "")
        original_protein_path = str(metadata.get("original_protein_path") or original_pocket10_path)
        pair_name = crossdocked_pair_name(original_ligand_path, original_pocket10_path)
        target_id = str(row.get("target_id") or metadata.get("target_id") or "")
        split_group = str(row.get("split_group") or metadata.get("split_group") or target_id)
        status = diffsbdd_split_status(pair_name, original_ligand_path, original_pocket10_path, official)
        exact_pair_overlap = status == "official_train_exact_pair"
        protein_file_overlap = original_pocket10_path in official.train or original_protein_path in official.train
        ligand_file_overlap = original_ligand_path in official.train
        same_target_overlap = bool(target_id and target_id in train_targets)
        same_pocket_overlap = bool(split_group and split_group in train_targets)
        tier = classify_overlap_tier(
            source_dataset=str(row.get("source") or metadata.get("dataset_name") or metadata.get("source") or ""),
            diffsbdd_split_status=status,
            exact_pair_overlap=exact_pair_overlap,
            protein_file_overlap=protein_file_overlap,
            ligand_file_overlap=ligand_file_overlap,
            same_target_overlap=same_target_overlap,
            same_pocket_overlap=same_pocket_overlap,
            official_split_available=official.available,
        )
        rows.append(
            {
                "base_sample_id": sample_id,
                "base_complex_id": str(sample.get("complex_id") or row.get("complex_id") or sample_id),
                "base_split": split_map.get(sample_id, str(row.get("split") or sample.get("metadata", {}).get("split") or "unknown")),
                "target_id": target_id,
                "split_group": split_group,
                "source_dataset": str(row.get("source") or metadata.get("dataset_name") or metadata.get("source") or ""),
                "raw_protein_path": str(paths.get("raw_protein_path") or row.get("protein_path") or ""),
                "raw_ligand_path": str(paths.get("raw_ligand_path") or row.get("ligand_path") or ""),
                "original_protein_path": original_protein_path,
                "original_pocket10_path": original_pocket10_path,
                "original_ligand_path": original_ligand_path,
                "protein_sha256": str(paths.get("protein_sha256") or _file_sha256(paths.get("raw_protein_path")) or ""),
                "ligand_sha256": str(paths.get("ligand_sha256") or _file_sha256(paths.get("raw_ligand_path")) or ""),
                "canonical_smiles": str(ligand.get("canonical_smiles") or ""),
                "inchi_key": str(ligand.get("inchi_key") or ""),
                "crossdocked_pair_name": pair_name,
                "diffsbdd_split_status": status,
                "exact_pair_overlap": bool(exact_pair_overlap),
                "protein_file_overlap": bool(protein_file_overlap),
                "ligand_file_overlap": bool(ligand_file_overlap),
                "same_target_overlap": bool(same_target_overlap),
                "same_pocket_overlap": bool(same_pocket_overlap),
                "ligand_exact_overlap": bool(ligand_file_overlap),
                "ligand_similarity_max": float("nan"),
                "sequence_identity_to_train_max": float("nan"),
                "overlap_tier": tier,
                "external_validity_eligible": bool(tier in EXTERNAL_ELIGIBLE_TIERS),
                "audit_decision": audit_decision(tier),
                "audit_notes": audit_notes(tier, official.available),
            }
        )
    return pd.DataFrame(rows, columns=OVERLAP_COLUMNS)


def load_processed_sample(row: dict[str, Any], processed_root: Path) -> dict[str, Any]:
    path_value = row.get("processed_path")
    if path_value not in (None, "") and Path(str(path_value)).exists():
        path = Path(str(path_value))
    else:
        sample_id = str(row.get("sample_id") or row.get("complex_id"))
        path = processed_root / "complexes" / f"{sample_id}.pkl"
    with path.open("rb") as f:
        return pickle.load(f)


def load_project_split_map(splits_root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for split in ("train", "val", "test"):
        path = splits_root / f"{split}.txt"
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            sample_id = line.strip()
            if sample_id:
                result[sample_id] = split
    return result


def load_official_split_names(files: dict[str, str | Path]) -> OfficialSplitNames:
    return OfficialSplitNames(
        train=_load_name_file(files.get("train")),
        val=_load_name_file(files.get("val")),
        test=_load_name_file(files.get("test")),
    )


def classify_overlap_tier(
    *,
    source_dataset: str,
    diffsbdd_split_status: str,
    exact_pair_overlap: bool,
    protein_file_overlap: bool,
    ligand_file_overlap: bool,
    same_target_overlap: bool,
    same_pocket_overlap: bool,
    official_split_available: bool,
) -> str:
    if exact_pair_overlap or diffsbdd_split_status == "official_train_exact_pair":
        return "T0_exact_pair_seen"
    if protein_file_overlap or ligand_file_overlap or same_target_overlap or same_pocket_overlap:
        return "T1_same_pocket_or_target_seen"
    if diffsbdd_split_status == "official_test_exact_pair":
        return "T3_official_diffsbdd_test"
    if official_split_available and "crossdocked" not in source_dataset.lower():
        return "T4_external_unseen"
    return "T_unknown"


def diffsbdd_split_status(
    pair_name: str,
    original_ligand_path: str,
    original_pocket10_path: str,
    official: OfficialSplitNames,
) -> str:
    candidates = {value for value in (pair_name, original_ligand_path, original_pocket10_path) if value}
    if candidates & official.train:
        return "official_train_exact_pair"
    if candidates & official.val:
        return "official_val_exact_pair"
    if candidates & official.test:
        return "official_test_exact_pair"
    if official.available:
        return "not_found_in_official_split_files"
    return "official_split_unavailable"


def crossdocked_pair_name(original_ligand_path: str, original_pocket10_path: str) -> str:
    if original_ligand_path:
        return original_ligand_path
    return original_pocket10_path


def audit_decision(tier: str) -> str:
    if tier == "T0_exact_pair_seen":
        return "same_source_smoke_only"
    if tier == "T1_same_pocket_or_target_seen":
        return "same_source_debug_only"
    if tier == "T2_ligand_or_scaffold_similar_seen":
        return "cautious_secondary_analysis"
    if tier in EXTERNAL_ELIGIBLE_TIERS:
        return "external_main_candidate"
    return "conservative_secondary_analysis"


def audit_notes(tier: str, official_split_available: bool) -> str:
    if tier == "T_unknown" and not official_split_available:
        return "Official DiffSBDD/Pocket2Mol split files unavailable; conclusion must remain conservative."
    if tier in {"T0_exact_pair_seen", "T1_same_pocket_or_target_seen"}:
        return "Training overlap risk; exclude from external-validity main conclusion."
    return ""


def summarize_overlap(audit_df: pd.DataFrame) -> dict[str, Any]:
    tier_counts = audit_df["overlap_tier"].value_counts(dropna=False).to_dict() if not audit_df.empty else {}
    return {
        "schema_version": "phase2_5_v0_1",
        "num_pockets_audited": int(len(audit_df)),
        "tier_counts": {str(key): int(value) for key, value in tier_counts.items()},
        "external_validity_subset_size": int(audit_df["external_validity_eligible"].sum()) if "external_validity_eligible" in audit_df else 0,
        "same_source_debug_subset_size": int((~audit_df["external_validity_eligible"]).sum()) if "external_validity_eligible" in audit_df else 0,
        "official_split_available": bool(
            audit_df["diffsbdd_split_status"].ne("official_split_unavailable").any()
        ) if "diffsbdd_split_status" in audit_df else False,
    }


def _load_name_file(path_value: str | Path | None) -> set[str]:
    if path_value in (None, ""):
        return set()
    path = Path(path_value)
    if not path.exists():
        return set()
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return _flatten_names(data)
    if path.suffix.lower() in {".csv", ".tsv"}:
        sep = "\t" if path.suffix.lower() == ".tsv" else ","
        df = pd.read_csv(path, sep=sep)
        names: set[str] = set()
        for column in df.columns:
            names.update(str(value).strip() for value in df[column].dropna().tolist() if str(value).strip())
        return names
    if path.suffix.lower() == ".pt":
        try:
            import torch
        except ImportError:
            return set()
        data = torch.load(path, map_location="cpu")
        return _flatten_names(data)
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def _flatten_names(data: Any) -> set[str]:
    names: set[str] = set()
    if isinstance(data, str):
        names.add(data)
    elif isinstance(data, dict):
        for value in data.values():
            names.update(_flatten_names(value))
    elif isinstance(data, list | tuple | set):
        for value in data:
            names.update(_flatten_names(value))
    return {name.strip() for name in names if name.strip()}


def _target_set(names: set[str]) -> set[str]:
    return {name.split("/", 1)[0] for name in names if "/" in name}


def _file_sha256(path_value: Any) -> str | None:
    if path_value in (None, ""):
        return None
    path = Path(str(path_value))
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
