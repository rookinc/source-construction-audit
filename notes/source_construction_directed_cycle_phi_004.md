# Source construction directed cycle phi 004

Status: source_construction_directed_cycle_phi_recorded

## Result

- audit_pass: `True`
- verdict: `directed_cycle_phi_exact_on_24_row_register`
- ledger_002_pass: `True`
- row_count: `24`
- row_count_is_24: `True`
- successor_ambiguity_count: `0`
- successor_ambiguity_count_is_0: `True`
- broken_path_count: `0`
- broken_path_count_is_0: `True`
- directed_cycle_count: `4`
- directed_cycle_count_is_4: `True`
- cycle_sizes_are_6: `True`
- each_cycle_has_all_six_roles_once: `True`
- each_cycle_has_role_successor_order: `True`
- all_rows_assigned: `True`
- phi_has_four_levels_once: `True`
- phi_row_partition_is_6_each: `True`
- phi_matches_form_index_partition: `True`
- row_order_used_for_phi: `False`
- form_index_used_only_for_evaluation: `True`
- answer_label_leakage_remains_open: `True`
- native_closure: `False`
- gap_a_closure: `False`
- required_phrases_present: `True`
- forbidden_phrases_absent: `True`

## Statement

Artifact 004 records a directed role-successor cycle source-construction assignment phi. Rows are grouped by native transition continuity row.to_ABC = next_row.from_ABC and role order WX->XY->YZ->ZT->TI->IW->WX, not by row order. phi is computed from slot_delta_mod15, fiber_delta_mod60, and edge_role. form_index is used only for evaluation. answer-label leakage remains open. This is not native closure, not full role-labeled shared_B universe derivation, and not Gap A closure.

## Phi rule

- Group rows by directed role-successor cycle: WX -> XY -> YZ -> ZT -> TI -> IW -> WX.
- Require native continuity: row.to_ABC equals next_row.from_ABC.
- Compute capture_count using slot_delta_mod15 > fiber_delta_mod60.
- capture_count 0 -> edge.
- capture_count 1 -> hinge.
- capture_count 2 with TI.fiber_delta_mod60 3 -> closed_face.
- capture_count 2 with TI.fiber_delta_mod60 1 -> filled_cell.

## Components

- component 0: rows=[0, 1, 2, 3, 4, 5], roles=WX XY YZ ZT TI IW, phi=edge, reason=capture_count=0, forms={0: 6}, match=True
- component 1: rows=[6, 7, 8, 9, 10, 11], roles=WX XY YZ ZT TI IW, phi=hinge, reason=capture_count=1, forms={1: 6}, match=True
- component 2: rows=[12, 13, 14, 15, 16, 17], roles=WX XY YZ ZT TI IW, phi=closed_face, reason=capture_count=2 and TI.fiber_delta_mod60=3, forms={2: 6}, match=True
- component 3: rows=[18, 19, 20, 21, 22, 23], roles=WX XY YZ ZT TI IW, phi=filled_cell, reason=capture_count=2 and TI.fiber_delta_mod60=1, forms={3: 6}, match=True

## Boundary

This is an exact source-construction assignment phi on the 24-row register, not native closure and not Gap A closure. form_index is used only for evaluation. answer-label leakage remains open until the source provenance and independence of the fields used by phi are audited more deeply.
