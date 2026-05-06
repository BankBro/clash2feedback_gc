from __future__ import annotations

import csv
import json
import re
import shutil
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from clash2feedback.chemistry.rgroup import decompose_rgroups
from clash2feedback.chemistry.sanitize import check_ligand_validity
from clash2feedback.chemistry.scaffold import get_murcko_scaffold_atom_indices, validate_scaffold
from clash2feedback.io.read_ligand import read_ligand_sdf
from clash2feedback.utils.files import ensure_dir


USER_AGENT = "clash2feedback-phase0/0.1"

DIFFSBDD_EXAMPLES = [
    {
        "complex_id": "complex_diffsbdd_3rfm",
        "pdb_id": "3rfm",
        "ligand_id": "CFF",
        "protein_url": "https://raw.githubusercontent.com/arneschneuing/DiffSBDD/main/example/3rfm.pdb",
        "ligand_url": "https://raw.githubusercontent.com/arneschneuing/DiffSBDD/main/example/3rfm_B_CFF.sdf",
    },
    {
        "complex_id": "complex_diffsbdd_5ndu",
        "pdb_id": "5ndu",
        "ligand_id": "8V2",
        "protein_url": "https://raw.githubusercontent.com/arneschneuing/DiffSBDD/main/example/5ndu.pdb",
        "ligand_url": "https://raw.githubusercontent.com/arneschneuing/DiffSBDD/main/example/5ndu_C_8V2.sdf",
    },
]

THU_CROSSDOCKED_REPO = "THU-ATOM/crossdocked"
IF3_CROSSDOCKED_REPO = "Yukk1Zz/if3-crossdocked2020"
IF3_ARCHIVE_NAME = "crossdocked_pocket10.tar.gz"
HF_MIRROR_BASE = "https://hf-mirror.com"
HF_CANONICAL_BASE = "https://huggingface.co"


@dataclass(frozen=True)
class CrossDockedPair:
    source_root: str
    target_dir: str
    receptor_path: str
    pocket10_path: str
    ligand_sdf_path: str
    ligand_pdb_path: str | None = None
    source_base_url: str | None = None

    @property
    def target_id(self) -> str:
        return self.target_dir

    @property
    def target_name(self) -> str:
        return _target_name_from_dir(self.target_dir)

    @property
    def receptor_pdb_id(self) -> str | None:
        return _pdb_id_from_name(Path(self.receptor_path).name)

    @property
    def ligand_id(self) -> str | None:
        return _ligand_id_from_name(Path(self.ligand_sdf_path).name)


def prepare_diffsbdd_examples(
    output_root: str | Path,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    root = Path(output_root)
    prepared: list[dict[str, Any]] = []
    if not dry_run:
        ensure_dir(root)

    for example in DIFFSBDD_EXAMPLES:
        complex_id = str(example["complex_id"])
        complex_dir = root / complex_id
        protein_path = complex_dir / "protein.pdb"
        ligand_path = complex_dir / "ligand.sdf"
        metadata_path = complex_dir / "metadata.json"
        if not dry_run:
            ensure_dir(complex_dir)
            _download_url(str(example["protein_url"]), protein_path, force=force)
            _download_url(str(example["ligand_url"]), ligand_path, force=force)
            _write_json(metadata_path, _diffsbdd_metadata(example))

        prepared.append(
            {
                "complex_id": complex_id,
                "protein_path": str(protein_path),
                "ligand_path": str(ligand_path),
                "metadata_path": str(metadata_path),
                "dry_run": dry_run,
            }
        )
    return prepared


def prepare_crossdocked_subset(
    *,
    output_root: str | Path,
    max_candidates: int = 50,
    download_root: str | Path | None = None,
    crossdocked_root: str | Path | None = None,
    auto_download: bool = False,
    protein_source: str = "pocket10",
    force: bool = False,
    dry_run: bool = False,
    prefilter_ligands: bool = True,
    tmp_root: str | Path = "tmp",
) -> dict[str, Any]:
    if protein_source not in {"pocket10", "full_receptor"}:
        raise ValueError("--protein-source must be pocket10 or full_receptor")
    if not auto_download and crossdocked_root is None:
        raise ValueError("Use --auto-download or pass --crossdocked-root")

    attempts: list[dict[str, Any]] = []
    if auto_download:
        if download_root is None:
            raise ValueError("--download-root is required with --auto-download")
        try:
            base_url, tree, source_attempts = _load_hf_tree_prefer_mirror(THU_CROSSDOCKED_REPO)
            attempts.extend(source_attempts)
            pairs = _discover_pairs_from_hf_tree(tree, base_url=base_url)
            result = _prepare_pairs(
                pairs,
                output_root=Path(output_root),
                max_candidates=max_candidates,
                download_root=Path(download_root),
                protein_source=protein_source,
                force=force,
                dry_run=dry_run,
                prefilter_ligands=prefilter_ligands,
                source_mode="auto_download",
            )
            result["download_attempts"] = attempts
            return result
        except Exception as exc:
            attempts.append({"source": THU_CROSSDOCKED_REPO, "status": "failed", "error": str(exc)})
            report_path = write_crossdocked_download_failure_report(attempts, tmp_root=tmp_root)
            raise RuntimeError(f"CrossDocked auto-download failed; report={report_path}") from exc

    pairs = _discover_pairs_from_local_root(Path(crossdocked_root))
    return _prepare_pairs(
        pairs,
        output_root=Path(output_root),
        max_candidates=max_candidates,
        download_root=Path(download_root) if download_root is not None else None,
        protein_source=protein_source,
        force=force,
        dry_run=dry_run,
        prefilter_ligands=prefilter_ligands,
        source_mode="local_root",
    )


def prepare_if3_crossdocked_archive_subset(
    *,
    output_root: str | Path,
    download_root: str | Path,
    max_candidates: int = 50,
    force: bool = False,
    dry_run: bool = False,
    prefilter_ligands: bool = True,
    tmp_root: str | Path = "tmp",
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    try:
        base_url, attempts = _choose_hf_dataset_base(IF3_CROSSDOCKED_REPO)
        archive_url = _hf_resolve_url(base_url, IF3_CROSSDOCKED_REPO, IF3_ARCHIVE_NAME)
        output = Path(output_root)
        cache_root = Path(download_root) / IF3_CROSSDOCKED_REPO / "crossdocked_pocket10"
        prepared, skipped = _stream_if3_archive_to_raw_complexes(
            archive_url,
            output_root=output,
            cache_root=cache_root,
            max_candidates=max_candidates,
            force=force,
            dry_run=dry_run,
            prefilter_ligands=prefilter_ligands,
        )
        if not dry_run:
            _write_prepare_report(Path(download_root) / "if3_crossdocked_archive_prepare_report.csv", prepared, skipped)
        return {
            "source_mode": "if3_archive",
            "source_url": archive_url,
            "num_discovered_pairs": len(prepared) + len(skipped),
            "num_prepared": len(prepared),
            "num_skipped_by_prefilter": len(skipped),
            "prepared": prepared,
            "skipped": skipped,
            "download_attempts": attempts,
        }
    except Exception as exc:
        attempts.append({"source": IF3_CROSSDOCKED_REPO, "status": "failed", "error": str(exc)})
        report_path = write_crossdocked_download_failure_report(attempts, tmp_root=tmp_root)
        raise RuntimeError(f"IF3 CrossDocked archive preparation failed; report={report_path}") from exc


def write_crossdocked_download_failure_report(
    attempts: list[dict[str, Any]],
    *,
    tmp_root: str | Path = "tmp",
) -> Path:
    tmp_dir = ensure_dir(tmp_root)
    date = datetime.now(UTC).strftime("%Y%m%d")
    path = tmp_dir / f"{date}-crossdocked-download-failed.md"
    lines = [
        "# CrossDocked 小子集自动获取失败",
        "",
        "## 1. 尝试过的数据源",
        "",
    ]
    for attempt in attempts:
        lines.append(
            f"- source: {attempt.get('source')}; url: {attempt.get('url')}; "
            f"status: {attempt.get('status')}; error: {attempt.get('error', '')}"
        )
    lines.extend(
        [
            "",
            "## 2. 阻塞原因",
            "",
            "当前环境未能通过公开入口自动获取可整理的 CrossDocked 小子集.",
            "",
            "## 3. 需要用户提供",
            "",
            "- 可访问的 CrossDocked pocket10 目录, 或包含 paired receptor/pocket PDB 与 ligand SDF 的本地目录.",
            "- 推荐放置路径: `data/cache/crossdocked_downloads/manual/`.",
            "",
            "## 4. 后续命令",
            "",
            "```bash",
            "conda run -n c2f_cpu python scripts/phase0_prepare_crossdocked_subset.py \\",
            "  --crossdocked-root data/cache/crossdocked_downloads/manual \\",
            "  --output-root data/raw_complexes \\",
            "  --max-candidates 50",
            "```",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _prepare_pairs(
    pairs: list[CrossDockedPair],
    *,
    output_root: Path,
    max_candidates: int,
    download_root: Path | None,
    protein_source: str,
    force: bool,
    dry_run: bool,
    prefilter_ligands: bool,
    source_mode: str,
) -> dict[str, Any]:
    if not pairs:
        raise ValueError("No paired CrossDocked protein-ligand files were discovered")
    selected: list[tuple[CrossDockedPair, Path | None, str | None]] = []
    skipped: list[dict[str, Any]] = []
    if not dry_run:
        ensure_dir(output_root)
        if download_root is not None:
            ensure_dir(download_root)
        if force:
            for existing in output_root.glob("complex_crossdocked_*"):
                if existing.is_dir():
                    shutil.rmtree(existing)

    for pair in pairs:
        if len(selected) >= max_candidates:
            break
        try:
            ligand_cache = _materialize_pair_file(pair, pair.ligand_sdf_path, download_root, force=force, dry_run=dry_run)
        except Exception as exc:
            skipped.append(
                {
                    "target_dir": pair.target_dir,
                    "ligand_sdf_path": pair.ligand_sdf_path,
                    "failure_reason": f"ligand_download_failed:{exc}",
                }
            )
            continue
        prefilter_reason = None
        if prefilter_ligands and not dry_run and ligand_cache is not None:
            prefilter_reason = _ligand_prefilter_failure(ligand_cache)
        if prefilter_reason is not None:
            skipped.append(
                {
                    "target_dir": pair.target_dir,
                    "ligand_sdf_path": pair.ligand_sdf_path,
                    "failure_reason": prefilter_reason,
                }
            )
            continue
        selected.append((pair, ligand_cache, prefilter_reason))

    prepared: list[dict[str, Any]] = []
    for index, (pair, ligand_cache, _) in enumerate(selected, start=1):
        complex_id = f"complex_crossdocked_{index:06d}"
        complex_dir = output_root / complex_id
        protein_rel = pair.pocket10_path if protein_source == "pocket10" else pair.receptor_path
        try:
            protein_cache = _materialize_pair_file(pair, protein_rel, download_root, force=force, dry_run=dry_run)
        except Exception as exc:
            skipped.append(
                {
                    "target_dir": pair.target_dir,
                    "ligand_sdf_path": pair.ligand_sdf_path,
                    "failure_reason": f"protein_download_failed:{exc}",
                }
            )
            continue
        protein_path = complex_dir / "protein.pdb"
        ligand_path = complex_dir / "ligand.sdf"
        metadata_path = complex_dir / "metadata.json"
        if not dry_run:
            ensure_dir(complex_dir)
            if protein_cache is None or ligand_cache is None:
                raise ValueError(f"Missing materialized files for {complex_id}")
            _copy_file(protein_cache, protein_path, force=force)
            _copy_file(ligand_cache, ligand_path, force=force)
            _write_json(metadata_path, _crossdocked_metadata(pair, complex_id, protein_rel, protein_source))
        prepared.append(
            {
                "complex_id": complex_id,
                "target_dir": pair.target_dir,
                "protein_source": protein_source,
                "protein_path": str(protein_path),
                "ligand_path": str(ligand_path),
                "metadata_path": str(metadata_path),
            }
        )

    if download_root is not None and not dry_run:
        _write_prepare_report(download_root / "crossdocked_prepare_report.csv", prepared, skipped)

    return {
        "source_mode": source_mode,
        "num_discovered_pairs": len(pairs),
        "num_prepared": len(prepared),
        "num_skipped_by_prefilter": len(skipped),
        "prepared": prepared,
        "skipped": skipped,
    }


def _stream_if3_archive_to_raw_complexes(
    archive_url: str,
    *,
    output_root: Path,
    cache_root: Path,
    max_candidates: int,
    force: bool,
    dry_run: bool,
    prefilter_ligands: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not dry_run:
        ensure_dir(output_root)
        ensure_dir(cache_root)
        if force:
            for existing in output_root.glob("complex_crossdocked_*"):
                if existing.is_dir():
                    shutil.rmtree(existing)

    request = urllib.request.Request(archive_url, headers={"User-Agent": USER_AGENT})
    prepared: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    states: dict[str, dict[str, Any]] = {}
    seen_prepared: set[str] = set()
    with urllib.request.urlopen(request, timeout=180) as response:
        with tarfile.open(fileobj=response, mode="r|gz") as archive:
            for member in archive:
                if len(prepared) >= max_candidates:
                    break
                rel_path = _if3_archive_relative_path(member.name)
                if rel_path is None or not member.isfile():
                    continue
                pair_key, kind = _if3_pair_key_and_kind(rel_path)
                if pair_key is None or kind is None:
                    continue

                cache_path = cache_root / rel_path
                if not dry_run and (force or not cache_path.exists()):
                    _extract_archive_member(archive, member, cache_path)
                state = states.setdefault(pair_key, {"rel_path": rel_path, "target_dir": rel_path.split("/")[0]})
                state[kind] = cache_path
                state[f"{kind}_rel_path"] = rel_path

                if kind == "sdf" and prefilter_ligands and not dry_run:
                    reason = _ligand_prefilter_failure(cache_path)
                    if reason is not None:
                        state["failure_reason"] = reason
                        skipped.append(
                            {
                                "target_dir": state["target_dir"],
                                "ligand_sdf_path": rel_path,
                                "failure_reason": reason,
                            }
                        )
                if (
                    pair_key not in seen_prepared
                    and "failure_reason" not in state
                    and "sdf" in state
                    and "pocket10" in state
                ):
                    complex_id = f"complex_crossdocked_{len(prepared) + 1:06d}"
                    if not dry_run:
                        _write_archive_prepared_complex(output_root, complex_id, state, archive_url)
                    prepared.append(
                        {
                            "complex_id": complex_id,
                            "target_dir": state["target_dir"],
                            "protein_source": "pocket10",
                            "protein_path": str(output_root / complex_id / "protein.pdb"),
                            "ligand_path": str(output_root / complex_id / "ligand.sdf"),
                            "metadata_path": str(output_root / complex_id / "metadata.json"),
                        }
                    )
                    seen_prepared.add(pair_key)
    return prepared, skipped


def _if3_archive_relative_path(member_name: str) -> str | None:
    normalized = member_name.lstrip("./")
    prefix = "crossdocked_pocket10/"
    if not normalized.startswith(prefix):
        return None
    rel_path = normalized[len(prefix) :]
    return rel_path if "/" in rel_path else None


def _if3_pair_key_and_kind(rel_path: str) -> tuple[str | None, str | None]:
    if rel_path.endswith("_pocket10.pdb"):
        return rel_path[: -len("_pocket10.pdb")], "pocket10"
    if rel_path.endswith(".sdf"):
        return rel_path[: -len(".sdf")], "sdf"
    return None, None


def _extract_archive_member(archive: tarfile.TarFile, member: tarfile.TarInfo, output_path: Path) -> None:
    ensure_dir(output_path.parent)
    source = archive.extractfile(member)
    if source is None:
        raise ValueError(f"Unable to extract archive member: {member.name}")
    tmp_path = output_path.with_name(output_path.name + ".tmp")
    with source, tmp_path.open("wb") as f:
        shutil.copyfileobj(source, f)
    tmp_path.replace(output_path)


def _write_archive_prepared_complex(
    output_root: Path,
    complex_id: str,
    state: dict[str, Any],
    archive_url: str,
) -> None:
    complex_dir = ensure_dir(output_root / complex_id)
    protein_path = complex_dir / "protein.pdb"
    ligand_path = complex_dir / "ligand.sdf"
    _copy_file(Path(state["pocket10"]), protein_path, force=True)
    _copy_file(Path(state["sdf"]), ligand_path, force=True)
    metadata = _archive_crossdocked_metadata(
        complex_id,
        target_dir=str(state["target_dir"]),
        protein_rel=str(state["pocket10_rel_path"]),
        ligand_rel=str(state["sdf_rel_path"]),
        archive_url=archive_url,
    )
    _write_json(complex_dir / "metadata.json", metadata)


def _archive_crossdocked_metadata(
    complex_id: str,
    *,
    target_dir: str,
    protein_rel: str,
    ligand_rel: str,
    archive_url: str,
) -> dict[str, Any]:
    target_name = _target_name_from_dir(target_dir)
    pdb_id = _pdb_id_from_name(Path(protein_rel).name)
    ligand_id = _ligand_id_from_name(Path(ligand_rel).name)
    return {
        "complex_id": complex_id,
        "source": "crossdocked_subset",
        "source_url": f"{HF_CANONICAL_BASE}/datasets/{IF3_CROSSDOCKED_REPO}",
        "source_repo": IF3_CROSSDOCKED_REPO,
        "archive_source_url": archive_url,
        "protein_source": "pocket10",
        "protein_source_url": f"{archive_url}#{protein_rel}",
        "ligand_source_url": f"{archive_url}#{ligand_rel}",
        "original_protein_path": protein_rel,
        "original_pocket10_path": protein_rel,
        "original_ligand_path": ligand_rel,
        "pdb_id": pdb_id,
        "ligand_id": ligand_id,
        "uniprot_id": None,
        "target_id": target_dir,
        "target_name": target_name,
        "protein_family": None,
        "cluster": None,
        "split_group": target_dir,
        "split_group_source": "target_id",
        "notes": "IF3 CrossDocked2020 pocket10 archive subset prepared for phase0 strict filtering",
    }


def _target_name_from_dir(target_dir: str) -> str:
    parts = target_dir.split("_")
    name_parts: list[str] = []
    for part in parts:
        if part.isdigit():
            break
        name_parts.append(part)
    return "_".join(name_parts) or target_dir


def _pdb_id_from_name(name: str) -> str | None:
    match = re.match(r"^([0-9A-Za-z]{4})_", name)
    return match.group(1).lower() if match else None


def _ligand_id_from_name(name: str) -> str | None:
    match = re.search(r"_([0-9A-Za-z]{3})_lig_", name)
    return match.group(1).upper() if match else None


def _discover_pairs_from_hf_tree(tree: list[dict[str, Any]], *, base_url: str) -> list[CrossDockedPair]:
    files = sorted(item["path"] for item in tree if item.get("type") == "file")
    grouped = _group_crossdocked_files(files)
    pairs = _pairs_from_grouped_files(grouped, source_root=THU_CROSSDOCKED_REPO, source_base_url=base_url)
    if not pairs:
        raise ValueError("HF tree did not contain paired receptor/pocket/ligand SDF files")
    return pairs


def _discover_pairs_from_local_root(root: Path) -> list[CrossDockedPair]:
    if not root.exists():
        raise FileNotFoundError(f"CrossDocked root does not exist: {root}")
    files = [str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()]
    grouped = _group_crossdocked_files(files)
    pairs = _pairs_from_grouped_files(grouped, source_root=str(root), source_base_url=None)
    if not pairs:
        raise ValueError(f"No paired receptor/pocket/ligand SDF files found under {root}")
    return pairs


def _group_crossdocked_files(files: list[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for file_path in files:
        path = Path(file_path)
        parent = str(path.parent)
        if parent in {"", "."}:
            continue
        grouped.setdefault(parent, []).append(file_path)
    return grouped


def _pairs_from_grouped_files(
    grouped: dict[str, list[str]],
    *,
    source_root: str,
    source_base_url: str | None,
) -> list[CrossDockedPair]:
    pairs: list[CrossDockedPair] = []
    for directory, files in sorted(grouped.items()):
        sdfs = sorted(path for path in files if path.endswith(".sdf"))
        receptors = sorted(path for path in files if path.endswith("_rec.pdb"))
        ligand_pdbs = sorted(path for path in files if path.endswith("_lig.pdb"))
        file_set = set(files)
        for sdf in sdfs:
            pocket = str(Path(sdf).with_suffix("")) + "_pocket10.pdb"
            receptor = _match_receptor(sdf, receptors)
            if receptor is None or pocket not in file_set:
                continue
            ligand_pdb = _match_ligand_pdb(sdf, ligand_pdbs)
            pairs.append(
                CrossDockedPair(
                    source_root=source_root,
                    target_dir=Path(directory).name,
                    receptor_path=receptor,
                    pocket10_path=pocket,
                    ligand_sdf_path=sdf,
                    ligand_pdb_path=ligand_pdb,
                    source_base_url=source_base_url,
                )
            )
    return pairs


def _match_receptor(sdf_path: str, receptors: list[str]) -> str | None:
    sdf_name = Path(sdf_path).name
    for receptor in receptors:
        stem = Path(receptor).stem
        if sdf_name.startswith(stem + "_"):
            return receptor
    return receptors[0] if len(receptors) == 1 else None


def _match_ligand_pdb(sdf_path: str, ligand_pdbs: list[str]) -> str | None:
    sdf_name = Path(sdf_path).name
    match = re.search(r"([0-9A-Za-z]{4}_[^_]+_lig)", sdf_name)
    if not match:
        return None
    expected = match.group(1) + ".pdb"
    for ligand_pdb in ligand_pdbs:
        if Path(ligand_pdb).name == expected:
            return ligand_pdb
    return None


def _materialize_pair_file(
    pair: CrossDockedPair,
    relative_path: str,
    download_root: Path | None,
    *,
    force: bool,
    dry_run: bool,
) -> Path | None:
    if pair.source_base_url is None:
        path = Path(pair.source_root) / relative_path
        return path if not dry_run else None
    if download_root is None:
        raise ValueError("download_root is required for HF-backed pairs")
    cache_path = download_root / THU_CROSSDOCKED_REPO / relative_path
    if dry_run:
        return None
    _download_url(_hf_resolve_url(pair.source_base_url, THU_CROSSDOCKED_REPO, relative_path), cache_path, force=False)
    return cache_path


def _ligand_prefilter_failure(ligand_path: Path) -> str | None:
    try:
        mol = read_ligand_sdf(ligand_path, sanitize=False, remove_hs=False)
        validity = check_ligand_validity(mol)
    except Exception as exc:
        return f"ligand_prefilter_read_failed:{exc}"
    if not validity["ok"]:
        return str(validity["fatal_errors"][0])
    scaffold = get_murcko_scaffold_atom_indices(mol)
    scaffold_check = validate_scaffold(mol, scaffold)
    if not scaffold_check["ok"]:
        return str(scaffold_check["fatal_errors"][0])
    rgroups = decompose_rgroups(mol, scaffold)
    num_valid_rgroups = sum(1 for rgroup in rgroups if rgroup.is_valid_for_phase0)
    if num_valid_rgroups < 2:
        return "not_enough_valid_rgroups"
    return None


def _diffsbdd_metadata(example: dict[str, Any]) -> dict[str, Any]:
    complex_id = str(example["complex_id"])
    return {
        "complex_id": complex_id,
        "source": "diffsbdd_example",
        "pdb_id": example["pdb_id"],
        "ligand_id": example["ligand_id"],
        "protein_source_url": example["protein_url"],
        "ligand_source_url": example["ligand_url"],
        "split_group": complex_id,
        "split_group_source": "complex_id",
        "notes": "DiffSBDD official example for phase0 smoke",
    }


def _crossdocked_metadata(
    pair: CrossDockedPair,
    complex_id: str,
    protein_rel: str,
    protein_source: str,
) -> dict[str, Any]:
    source_url = (
        f"{pair.source_base_url}/datasets/{THU_CROSSDOCKED_REPO}"
        if pair.source_base_url
        else str(Path(pair.source_root).resolve())
    )
    protein_url = _source_file_url(pair, protein_rel)
    ligand_url = _source_file_url(pair, pair.ligand_sdf_path)
    split_group = pair.target_id or pair.receptor_pdb_id or complex_id
    split_group_source = "target_id" if pair.target_id else "pdb_id" if pair.receptor_pdb_id else "complex_id"
    return {
        "complex_id": complex_id,
        "source": "crossdocked_subset",
        "source_url": source_url,
        "source_repo": THU_CROSSDOCKED_REPO if pair.source_base_url else None,
        "protein_source": protein_source,
        "protein_source_url": protein_url,
        "ligand_source_url": ligand_url,
        "original_protein_path": protein_rel,
        "original_receptor_path": pair.receptor_path,
        "original_pocket10_path": pair.pocket10_path,
        "original_ligand_path": pair.ligand_sdf_path,
        "pdb_id": pair.receptor_pdb_id,
        "ligand_id": pair.ligand_id,
        "uniprot_id": None,
        "target_id": pair.target_id,
        "target_name": pair.target_name,
        "protein_family": None,
        "cluster": None,
        "split_group": split_group,
        "split_group_source": split_group_source,
        "notes": "CrossDocked subset prepared for phase0 strict filtering",
    }


def _source_file_url(pair: CrossDockedPair, relative_path: str) -> str:
    if pair.source_base_url is None:
        return str(Path(pair.source_root) / relative_path)
    return _hf_resolve_url(pair.source_base_url, THU_CROSSDOCKED_REPO, relative_path)


def _load_hf_tree_prefer_mirror(repo_id: str) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    attempts: list[dict[str, Any]] = []
    for base_url in (HF_MIRROR_BASE, HF_CANONICAL_BASE):
        api_url = f"{base_url}/api/datasets/{repo_id}/tree/main?recursive=1"
        try:
            tree = _request_json(api_url)
            attempts.append({"source": repo_id, "url": api_url, "status": "ok"})
            return base_url, tree, attempts
        except Exception as exc:
            attempts.append({"source": repo_id, "url": api_url, "status": "failed", "error": str(exc)})
    raise RuntimeError(f"Unable to read HF dataset tree for {repo_id}")


def _choose_hf_dataset_base(repo_id: str) -> tuple[str, list[dict[str, Any]]]:
    attempts: list[dict[str, Any]] = []
    for base_url in (HF_MIRROR_BASE, HF_CANONICAL_BASE):
        api_url = f"{base_url}/api/datasets/{repo_id}/tree/main"
        try:
            _request_json(api_url)
            attempts.append({"source": repo_id, "url": api_url, "status": "ok"})
            return base_url, attempts
        except Exception as exc:
            attempts.append({"source": repo_id, "url": api_url, "status": "failed", "error": str(exc)})
    raise RuntimeError(f"Unable to access HF dataset metadata for {repo_id}")


def _request_json(url: str, *, timeout: int = 60) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _download_url(url: str, output_path: Path, *, force: bool = False, timeout: int = 120, retries: int = 3) -> None:
    if output_path.exists() and not force:
        return
    ensure_dir(output_path.parent)
    tmp_path = output_path.with_name(output_path.name + ".tmp")
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response, tmp_path.open("wb") as f:
                shutil.copyfileobj(response, f)
            tmp_path.replace(output_path)
            return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if tmp_path.exists():
                tmp_path.unlink()
            if attempt < retries:
                time.sleep(float(attempt))
    raise RuntimeError(f"Download failed: {url}; error={last_error}")


def _hf_resolve_url(base_url: str, repo_id: str, path: str) -> str:
    quoted = urllib.parse.quote(path, safe="/")
    return f"{base_url.rstrip('/')}/datasets/{repo_id}/resolve/main/{quoted}"


def _copy_file(source: Path, destination: Path, *, force: bool) -> None:
    if destination.exists() and not force:
        return
    ensure_dir(destination.parent)
    shutil.copyfile(source, destination)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_prepare_report(path: Path, prepared: list[dict[str, Any]], skipped: list[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    rows: list[dict[str, Any]] = []
    for row in prepared:
        rows.append({"status": "prepared", **row})
    for row in skipped:
        rows.append({"status": "skipped", **row})
    if not rows:
        path.write_text("status\n", encoding="utf-8")
        return
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
