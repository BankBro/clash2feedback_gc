# Phase 4.0.1a Reconnect Rule Field Consistency Audit

## 1. Scope

- 本审计不查看图片, 不新增图片, 不重跑 DiffSBDD, 不重新生成候选.
- 只检查当前 CSV 字段是否能推出已写入的 `reconnect_category` 和 `reconnect_category_reason`.
- 审计函数直接调用 `src/clash2feedback/repair/reconnect_calibration.py::classify_reconnect_row`.

## 2. Audited Files

| file | rows | category_counts |
|---|---:|---|
| `diffsbdd_reconnect_reclassified.csv` | 2187 | `{'invalid_reconnect': 1855, 'multi_attachment_out_of_scope': 332}` |
| `clean_positive_reconnect_check.csv` | 40 | `{'single_anchor_reconnect_pass': 40}` |
| `rule_positive_reconnect_check.csv` | 227 | `{'single_anchor_reconnect_pass': 227}` |
| `synthetic_negative_reconnect_check.csv` | 4 | `{'invalid_reconnect': 3, 'multi_attachment_out_of_scope': 1}` |
| `visual_qc_reconnect_cases.csv` | 25 | `{'multi_attachment_out_of_scope': 8, 'invalid_reconnect': 11, 'single_anchor_reconnect_pass': 6}` |

## 3. Results

- total_rows_checked: 2483.
- exact_rule_output_mismatches: 0.
- semantic_invariant_violations: 0.
- multi-fragment or non-single-fragment rows checked: 1237.

### 3.1 Exact Mismatches

- None.

### 3.2 Semantic Violations

- None.

## 4. Key Invariants Checked

- `ligand_valid=false` rows must be `invalid_reconnect`.
- `candidate_total_fragment_count > 1` or `candidate_single_fragment=false` rows must be `invalid_reconnect`.
- `multi_attachment_out_of_scope` rows must remain readable, RDKit-sanitize-valid, single-fragment candidates with an extra attachment, multiple generated attachments, or multiple anchor neighbors signal.
- `single_anchor_reconnect_pass` rows must be readable, RDKit-sanitize-valid, single-fragment, connected to anchor, `num_anchor_neighbors == 1`, `num_extra_attachments == 0`, and no floating fragment.
- `invalid_reconnect` rows must have at least one invalid signal or be the explicit fallback `unclassified_reconnect_failure`.

## 5. Conclusion

- Result: field consistency audit passed. Current CSV reconnect outputs are consistent with the implemented rule order and required semantic invariants.
- This audit does not provide additional visual evidence; it only validates field/rule consistency.
