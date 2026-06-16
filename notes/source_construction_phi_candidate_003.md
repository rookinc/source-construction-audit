# Source construction phi candidate 003

Status: source_construction_phi_candidate_recorded

## Result

- audit_pass: `False`
- verdict: `phi_candidate_failed`
- ledger_002_pass: `True`
- row_count: `24`
- row_count_is_24: `True`
- component_count: `3`
- component_count_is_4: `False`
- component_sizes_are_6: `False`
- each_component_has_all_six_roles_once: `False`
- each_component_is_transition_cycle: `False`
- phi_has_four_levels_once: `False`
- row_phi_partition_is_6_each: `False`
- phi_matches_form_index_partition: `False`
- row_order_used_for_phi: `False`
- form_index_used_only_for_evaluation: `True`
- answer_label_leakage_remains_open: `True`
- native_closure: `False`
- gap_a_closure: `False`
- required_phrases_present: `True`
- forbidden_phrases_absent: `True`

## Statement

Artifact 003 records a source-construction assignment phi. It derives native transition components from from_A/from_B/from_C to to_A/to_B/to_C, computes capture_count from slot_delta_mod15 and fiber_delta_mod60, and uses edge_role plus TI.fiber_delta_mod60 as the filling discriminant. form_index is used only for evaluation. answer-label leakage remains open. This is not native closure, not full role-labeled shared_B universe derivation, and not Gap A closure.

## Phi rule

- Build native transition components from from_A/from_B/from_C to to_A/to_B/to_C.
- Compute capture_count inside each component using slot_delta_mod15 > fiber_delta_mod60.
- capture_count 0 -> edge.
- capture_count 1 -> hinge.
- capture_count 2 with TI.fiber_delta_mod60 3 -> closed_face.
- capture_count 2 with TI.fiber_delta_mod60 1 -> filled_cell.

## Components

- component 0: rows=[0, 1, 2, 3, 4, 5], phi=edge, reason=capture_count=0, forms={0: 6}, match=True
- component 1: rows=[6, 7, 8, 9, 10, 11], phi=hinge, reason=capture_count=1, forms={1: 6}, match=True
- component 2: rows=[12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23], phi=unknown, reason=no rule matched, forms={2: 6, 3: 6}, match=False

## Boundary

This is an exact phi candidate on the 24-row register, not native closure and not Gap A closure. form_index is used only for evaluation. answer-label leakage remains open until the source construction provenance of the fields themselves is audited more deeply.
