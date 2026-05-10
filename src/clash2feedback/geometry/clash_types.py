from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ClashPair:
    ligand_atom_idx: int
    protein_atom_idx: int
    protein_atom_position: int | None
    ligand_element: str
    protein_element: str
    distance: float
    vdw_sum: float
    clash_depth: float
    is_severe: bool
    ligand_region: str
    protein_residue_key: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ClashReport:
    sample_id: str
    receptor_scope: str
    delta_angstrom: float
    severe_depth_threshold_angstrom: float
    num_clash_pairs: int
    num_severe_clash_pairs: int
    total_clash_score: float
    max_clash_depth: float
    mean_clash_depth: float = 0.0
    clash_pairs: list[ClashPair] = field(default_factory=list)
    unsupported_reasons: list[str] = field(default_factory=list)
    analysis_status: str = "ok"

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["clash_pairs"] = [pair.to_dict() for pair in self.clash_pairs]
        return result
