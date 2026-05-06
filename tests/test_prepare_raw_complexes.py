from clash2feedback.data.prepare_raw_complexes import (
    _discover_pairs_from_hf_tree,
    _if3_archive_relative_path,
    _if3_pair_key_and_kind,
)


def test_discover_pairs_from_hf_tree_uses_confirmed_pocket_and_ligand_pairing() -> None:
    tree = [
        {"type": "file", "path": "README.md"},
        {"type": "file", "path": "crossdocked_test/ABL2_HUMAN_274_551_0/4xli_B_rec.pdb"},
        {
            "type": "file",
            "path": "crossdocked_test/ABL2_HUMAN_274_551_0/"
            "4xli_B_rec_4xli_1n1_lig_tt_min_0.sdf",
        },
        {
            "type": "file",
            "path": "crossdocked_test/ABL2_HUMAN_274_551_0/"
            "4xli_B_rec_4xli_1n1_lig_tt_min_0_pocket10.pdb",
        },
        {"type": "file", "path": "crossdocked_test/ABL2_HUMAN_274_551_0/4xli_1n1_lig.pdb"},
        {"type": "file", "path": "crossdocked_test/BAD_TARGET_0/orphan.sdf"},
    ]

    pairs = _discover_pairs_from_hf_tree(tree, base_url="https://hf-mirror.com")

    assert len(pairs) == 1
    assert pairs[0].target_id == "ABL2_HUMAN_274_551_0"
    assert pairs[0].target_name == "ABL2_HUMAN"
    assert pairs[0].receptor_pdb_id == "4xli"
    assert pairs[0].ligand_id == "1N1"
    assert pairs[0].pocket10_path.endswith("_pocket10.pdb")


def test_if3_archive_path_helpers_normalize_pair_keys() -> None:
    rel = _if3_archive_relative_path(
        "./crossdocked_pocket10/SYH_THET8_1_421_0/"
        "1ady_A_rec_1ady_ham_lig_tt_docked_1_pocket10.pdb"
    )

    assert rel == "SYH_THET8_1_421_0/1ady_A_rec_1ady_ham_lig_tt_docked_1_pocket10.pdb"
    key, kind = _if3_pair_key_and_kind(rel)
    assert key == "SYH_THET8_1_421_0/1ady_A_rec_1ady_ham_lig_tt_docked_1"
    assert kind == "pocket10"
